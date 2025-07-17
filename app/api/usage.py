from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.usage import UsageRecord
from app.schemas.usage import UsageRecordResponse, UsageSummaryResponse, UsageStatsResponse
from app.services.usage_service import UsageService
import uuid

router = APIRouter()

@router.get("/records", response_model=List[UsageRecordResponse])
async def list_usage_records(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    usage_type: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    billing_period: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UsageService(db)
    records = service.list_usage_records(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
        usage_type=usage_type,
        provider=provider,
        billing_period=billing_period,
        start_date=start_date,
        end_date=end_date
    )
    return [UsageRecordResponse.model_validate(record) for record in records]

@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    billing_period: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UsageService(db)
    
    if not billing_period:
        # Default to current month
        billing_period = datetime.now().strftime("%Y-%m")
    
    summary = service.get_usage_summary(
        organization_id=current_user.organization_id,
        billing_period=billing_period
    )
    
    return summary

@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UsageService(db)
    stats = service.get_usage_stats(
        organization_id=current_user.organization_id
    )
    
    return stats

@router.get("/costs/forecast")
async def get_cost_forecast(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UsageService(db)
    forecast = service.get_cost_forecast(
        organization_id=current_user.organization_id,
        days=days
    )
    
    return forecast

@router.post("/records", status_code=status.HTTP_201_CREATED)
async def create_usage_record(
    usage_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This endpoint is typically used by internal systems
    service = UsageService(db)
    record = service.create_usage_record(
        organization_id=current_user.organization_id,
        usage_data=usage_data
    )
    
    return UsageRecordResponse.model_validate(record)

@router.get("/export")
async def export_usage_data(
    format: str = Query("csv", pattern="^(csv|json|xlsx)$"),
    billing_period: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UsageService(db)
    export_data = service.export_usage_data(
        organization_id=current_user.organization_id,
        format=format,
        billing_period=billing_period,
        start_date=start_date,
        end_date=end_date
    )
    
    return export_data