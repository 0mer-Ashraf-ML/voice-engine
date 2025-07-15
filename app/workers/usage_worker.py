import uuid
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.usage import UsageRecord
from app.models.call import Call
from app.models.organization import Organization
from app.services.usage_service import UsageService
from sqlalchemy import func

async def track_usage_task(
    organization_id: str,
    usage_type: str,
    quantity: float,
    unit: str,
    unit_cost: float,
    provider: str = None,
    model_name: str = None,
    call_id: str = None,
    metadata: dict = None
):
    """Track usage for billing purposes"""
    db = SessionLocal()
    
    try:
        usage_service = UsageService(db)
        
        usage_data = {
            "usage_type": usage_type,
            "quantity": quantity,
            "unit": unit,
            "unit_cost": unit_cost,
            "total_cost": quantity * unit_cost,
            "provider": provider,
            "model_name": model_name,
            "metadata": metadata or {}
        }
        
        if call_id:
            usage_data["call_id"] = uuid.UUID(call_id)
        
        usage_record = usage_service.create_usage_record(
            organization_id=uuid.UUID(organization_id),
            usage_data=usage_data
        )
        
        return {
            "status": "tracked",
            "usage_record_id": str(usage_record.id),
            "total_cost": usage_record.total_cost
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

def calculate_costs_task():
    """Calculate and aggregate costs for all organizations"""
    db = SessionLocal()
    
    try:
        # Get current month
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get all organizations
        organizations = db.query(Organization).filter(
            Organization.is_active == True
        ).all()
        
        results = []
        
        for org in organizations:
            # Calculate monthly costs
            monthly_records = db.query(UsageRecord).filter(
                UsageRecord.organization_id == org.id,
                UsageRecord.billing_period == current_month
            ).all()
            
            total_cost = sum(record.total_cost for record in monthly_records)
            
            results.append({
                "organization_id": str(org.id),
                "organization_name": org.name,
                "monthly_cost": total_cost,
                "record_count": len(monthly_records)
            })
        
        return {
            "status": "completed",
            "billing_period": current_month,
            "organizations_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

def generate_monthly_invoices_task():
    """Generate monthly invoices for all organizations"""
    db = SessionLocal()
    
    try:
        from app.integrations.stripe import StripeIntegration
        stripe_integration = StripeIntegration()
        
        # Get last month
        last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        
        # Get organizations with usage last month
        organizations_with_usage = db.query(
            UsageRecord.organization_id,
            func.sum(UsageRecord.total_cost).label('total_cost')
        ).filter(
            UsageRecord.billing_period == last_month,
            UsageRecord.is_billed == False
        ).group_by(UsageRecord.organization_id).all()
        
        results = []
        
        for org_usage in organizations_with_usage:
            org = db.query(Organization).filter(
                Organization.id == org_usage.organization_id
            ).first()
            
            if not org or not org.stripe_customer_id:
                continue
            
            # Create invoice items for usage
            invoice_result = stripe_integration.create_invoice_item(
                customer_id=org.stripe_customer_id,
                amount=int(org_usage.total_cost * 100),  # Convert to cents
                description=f"Usage charges for {last_month}"
            )
            
            if invoice_result.get("success"):
                # Create and send invoice
                invoice = stripe_integration.create_invoice(
                    customer_id=org.stripe_customer_id
                )
                
                if invoice.get("success"):
                    # Mark usage records as billed
                    db.query(UsageRecord).filter(
                        UsageRecord.organization_id == org_usage.organization_id,
                        UsageRecord.billing_period == last_month
                    ).update({"is_billed": True})
                    
                    results.append({
                        "organization_id": str(org.id),
                        "invoice_id": invoice["invoice"].id,
                        "amount": org_usage.total_cost
                    })
        
        db.commit()
        
        return {
            "status": "completed",
            "billing_period": last_month,
            "invoices_created": len(results),
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

def cleanup_old_usage_records_task():
    """Clean up old usage records (older than 2 years)"""
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=730)  # 2 years
        
        # Delete old billed usage records
        deleted_count = db.query(UsageRecord).filter(
            UsageRecord.created_at < cutoff_date,
            UsageRecord.is_billed == True
        ).delete()
        
        db.commit()
        
        return {"deleted_records": deleted_count}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

async def send_usage_alert_task(organization_id: str, threshold_type: str, current_usage: float):
    """Send usage threshold alerts"""
    db = SessionLocal()
    
    try:
        org = db.query(Organization).filter(
            Organization.id == uuid.UUID(organization_id)
        ).first()
        
        if not org:
            return {"status": "error", "error": "Organization not found"}
        
        # Here you would implement notification logic
        # For example: send email, webhook, push notification, etc.
        
        return {
            "status": "sent",
            "organization": org.name,
            "threshold_type": threshold_type,
            "current_usage": current_usage
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

def get_usage_stats(organization_id: str) -> dict:
    """Get real-time usage statistics"""
    db = SessionLocal()
    
    try:
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get current month usage
        monthly_records = db.query(UsageRecord).filter(
            UsageRecord.organization_id == uuid.UUID(organization_id),
            UsageRecord.billing_period == current_month
        ).all()
        
        # Calculate totals by type
        usage_by_type = {}
        total_cost = 0
        
        for record in monthly_records:
            if record.usage_type not in usage_by_type:
                usage_by_type[record.usage_type] = {
                    "quantity": 0,
                    "cost": 0
                }
            
            usage_by_type[record.usage_type]["quantity"] += record.quantity
            usage_by_type[record.usage_type]["cost"] += record.total_cost
            total_cost += record.total_cost
        
        # Get call count for current month
        call_count = db.query(Call).filter(
            Call.organization_id == uuid.UUID(organization_id),
            func.date_trunc('month', Call.created_at) == datetime.now().replace(day=1).date()
        ).count()
        
        return {
            "organization_id": organization_id,
            "billing_period": current_month,
            "total_cost": total_cost,
            "total_calls": call_count,
            "usage_by_type": usage_by_type,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}
        
    finally:
        db.close()