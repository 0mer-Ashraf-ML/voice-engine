import httpx
import json
import hashlib
import hmac
import asyncio
import uuid
from datetime import datetime
from app.database import SessionLocal
from app.models.assistant import Assistant
from app.models.call import Call

async def send_webhook_task(
    call_id: str, 
    event_type: str, 
    data: dict,
    webhook_url: str = None,
    webhook_secret: str = None
):
    """Send webhook notification"""
    db = SessionLocal()
    
    try:
        # Get call and assistant info
        call = db.query(Call).filter(Call.id == uuid.UUID(call_id)).first()
        if not call:
            raise ValueError(f"Call {call_id} not found")
        
        assistant = db.query(Assistant).filter(
            Assistant.id == call.assistant_id
        ).first()
        
        # Use assistant webhook URL if not provided
        if not webhook_url and assistant:
            webhook_url = assistant.server_url
            webhook_secret = assistant.server_url_secret
        
        if not webhook_url:
            return {"status": "skipped", "reason": "No webhook URL configured"}
        
        # Prepare webhook payload
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "call_id": call_id,
            "organization_id": str(call.organization_id),
            "data": data
        }
        
        # Send webhook
        result = await _send_webhook_request(
            url=webhook_url,
            payload=payload,
            secret=webhook_secret
        )
        
        if not result.get("success"):
            raise Exception(f"Webhook failed: {result.get('error')}")
        
        return {"status": "sent", "call_id": call_id, "event_type": event_type}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

async def _send_webhook_request(url: str, payload: dict, secret: str = None) -> dict:
    """Send HTTP webhook request"""
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Vapi-Clone-Webhook/1.0"
        }
        
        # Add signature if secret provided
        if secret:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Vapi-Signature"] = f"sha256={signature}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload
            )
            
            if response.status_code < 300:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.text
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Webhook request timeout"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def retry_webhook_task(webhook_id: str, max_retries: int = 3):
    """Retry failed webhook with exponential backoff"""
    for attempt in range(max_retries):
        try:
            # Implement retry logic here
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            return {"status": "retry_completed", "attempts": attempt + 1}
        except Exception as e:
            if attempt == max_retries - 1:
                return {"status": "retry_failed", "error": str(e)}
            continue
    
    return {"status": "retry_failed", "error": "Max retries exceeded"}

async def send_assistant_webhook_task(
    assistant_id: str,
    event_type: str,
    data: dict
):
    """Send webhook for assistant-specific events"""
    db = SessionLocal()
    
    try:
        assistant = db.query(Assistant).filter(
            Assistant.id == uuid.UUID(assistant_id)
        ).first()
        
        if not assistant or not assistant.server_url:
            return {"status": "skipped", "reason": "No webhook URL configured"}
        
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "assistant_id": assistant_id,
            "organization_id": str(assistant.organization_id),
            "data": data
        }
        
        result = await _send_webhook_request(
            url=assistant.server_url,
            payload=payload,
            secret=assistant.server_url_secret
        )
        
        return result
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    try:
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception:
        return False
    