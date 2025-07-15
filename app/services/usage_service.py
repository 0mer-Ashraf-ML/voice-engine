from sqlalchemy.orm import Session, func
from sqlalchemy import and_, extract
from typing import Optional, List
from datetime import datetime, date, timedelta
from app.models.usage import UsageRecord
from app.models.call import Call
from app.schemas.usage import UsageSummaryResponse, UsageStatsResponse
import uuid
import csv
import json
import io

class UsageService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_usage_records(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        usage_type: Optional[str] = None,
        provider: Optional[str] = None,
        billing_period: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[UsageRecord]:
        query = self.db.query(UsageRecord).filter(
            UsageRecord.organization_id == organization_id
        )
        
        if usage_type:
            query = query.filter(UsageRecord.usage_type == usage_type)
        
        if provider:
            query = query.filter(UsageRecord.provider == provider)
        
        if billing_period:
            query = query.filter(UsageRecord.billing_period == billing_period)
        
        if start_date:
            query = query.filter(UsageRecord.created_at >= start_date)
        
        if end_date:
            query = query.filter(UsageRecord.created_at <= end_date)
        
        return query.order_by(UsageRecord.created_at.desc()).offset(offset).limit(limit).all()
    
    def create_usage_record(
        self,
        organization_id: uuid.UUID,
        usage_data: dict
    ) -> UsageRecord:
        # Set billing period if not provided
        if "billing_period" not in usage_data:
            usage_data["billing_period"] = datetime.now().strftime("%Y-%m")
        
        usage_record = UsageRecord(
            organization_id=organization_id,
            **usage_data
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record
    
    def get_usage_summary(
        self,
        organization_id: uuid.UUID,
        billing_period: str
    ) -> UsageSummaryResponse:
        records = self.db.query(UsageRecord).filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.billing_period == billing_period
        ).all()
        
        total_cost = sum(record.total_cost for record in records)
        
        # Calculate breakdown by usage type
        breakdown = {}
        for record in records:
            if record.usage_type not in breakdown:
                breakdown[record.usage_type] = 0
            breakdown[record.usage_type] += record.total_cost
        
        # Get call statistics for the period
        year, month = billing_period.split("-")
        calls = self.db.query(Call).filter(
            Call.organization_id == organization_id,
            extract('year', Call.created_at) == int(year),
            extract('month', Call.created_at) == int(month)
        ).all()

        total_calls = len(calls)
        total_minutes = sum([(call.duration_seconds or 0) / 60 for call in calls])
        
        return UsageSummaryResponse(
            organization_id=organization_id,
            billing_period=billing_period,
            total_cost=total_cost,
            breakdown=breakdown,
            total_calls=total_calls,
            total_minutes=total_minutes
        )
    
    def get_usage_stats(
        self,
        organization_id: uuid.UUID
    ) -> UsageStatsResponse:
        today = datetime.now().date()
        current_month = today.strftime("%Y-%m")
        last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        
        # Today's stats
        today_records = self.db.query(UsageRecord).filter(
            UsageRecord.organization_id == organization_id,
            func.date(UsageRecord.created_at) == today
        ).all()
        
        today_calls = self.db.query(Call).filter(
            Call.organization_id == organization_id,
            func.date(Call.created_at) == today
        ).all()
        
        today_summary = UsageSummaryResponse(
            organization_id=organization_id,
            billing_period=today.strftime("%Y-%m-%d"),
            total_cost=sum(r.total_cost for r in today_records),
            breakdown={},
            total_calls=len(today_calls),
            total_minutes=sum([(call.duration_seconds or 0) / 60 for call in today_calls])
        )
        
        # This month's stats
        this_month_summary = self.get_usage_summary(organization_id, current_month)
        
        # Last month's stats
        last_month_summary = self.get_usage_summary(organization_id, last_month)
        
        return UsageStatsResponse(
            today=today_summary,
            this_month=this_month_summary,
            last_month=last_month_summary
        )
    
    def get_cost_forecast(
        self,
        organization_id: uuid.UUID,
        days: int = 30
    ) -> dict:
        # Get usage data from last 30 days
        start_date = datetime.now() - timedelta(days=30)
        
        records = self.db.query(UsageRecord).filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.created_at >= start_date
        ).all()
        
        if not records:
            return {
                "forecast_period_days": days,
                "predicted_cost": 0.0,
                "daily_average": 0.0,
                "confidence": "low"
            }
        
        # Calculate daily average
        total_cost = sum(record.total_cost for record in records)
        daily_average = total_cost / 30
        
        # Forecast for next period
        predicted_cost = daily_average * days
        
        # Simple confidence calculation based on data consistency
        daily_costs = {}
        for record in records:
            day = record.created_at.date()
            if day not in daily_costs:
                daily_costs[day] = 0
            daily_costs[day] += record.total_cost
        
        # Calculate variance to determine confidence
        daily_values = list(daily_costs.values())
        if len(daily_values) > 1:
            variance = sum((x - daily_average) ** 2 for x in daily_values) / len(daily_values)
            confidence = "high" if variance < daily_average * 0.5 else "medium" if variance < daily_average else "low"
        else:
            confidence = "low"
        
        return {
            "forecast_period_days": days,
            "predicted_cost": round(predicted_cost, 2),
            "daily_average": round(daily_average, 2),
            "confidence": confidence,
            "based_on_days": len(daily_costs)
        }
    
    def export_usage_data(
        self,
        organization_id: uuid.UUID,
        format: str = "csv",
        billing_period: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        records = self.list_usage_records(
            organization_id=organization_id,
            limit=10000,  # Large limit for export
            billing_period=billing_period,
            start_date=start_date,
            end_date=end_date
        )
        
        if format == "csv":
            return self._export_csv(records)
        elif format == "json":
            return self._export_json(records)
        else:
            raise ValueError("Unsupported export format")
    
    def _export_csv(self, records: List[UsageRecord]) -> dict:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Date", "Usage Type", "Quantity", "Unit", "Unit Cost", 
            "Total Cost", "Provider", "Model", "Billing Period"
        ])
        
        # Data
        for record in records:
            writer.writerow([
                record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                record.usage_type,
                record.quantity,
                record.unit,
                record.unit_cost,
                record.total_cost,
                record.provider or "",
                record.model_name or "",
                record.billing_period
            ])
        
        return {
            "format": "csv",
            "content": output.getvalue(),
            "filename": f"usage_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    
    def _export_json(self, records: List[UsageRecord]) -> dict:
        data = []
        for record in records:
            data.append({
                "id": str(record.id),
                "date": record.created_at.isoformat(),
                "usage_type": record.usage_type,
                "quantity": record.quantity,
                "unit": record.unit,
                "unit_cost": record.unit_cost,
                "total_cost": record.total_cost,
                "provider": record.provider,
                "model_name": record.model_name,
                "billing_period": record.billing_period,
                "metadata": record.metadata
            })
        
        return {
            "format": "json",
            "content": json.dumps(data, indent=2),
            "filename": f"usage_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    
    def track_call_usage(
        self,
        call_id: uuid.UUID,
        organization_id: uuid.UUID,
        usage_data: dict
    ) -> List[UsageRecord]:
        """Track usage for a specific call"""
        records = []
        
        for usage_type, data in usage_data.items():
            record = self.create_usage_record(
                organization_id=organization_id,
                usage_data={
                    "call_id": call_id,
                    "usage_type": usage_type,
                    "quantity": data.get("quantity", 0),
                    "unit": data.get("unit", "units"),
                    "unit_cost": data.get("unit_cost", 0),
                    "total_cost": data.get("total_cost", 0),
                    "provider": data.get("provider"),
                    "model_name": data.get("model_name"),
                    "metadata": data.get("metadata", {})
                }
            )
            records.append(record)
        
        return records