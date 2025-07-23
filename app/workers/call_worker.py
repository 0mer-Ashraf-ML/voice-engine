import asyncio
import uuid
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.call import Call
from app.models.assistant import Assistant
from app.services.call_service import CallService
from app.services.usage_service import UsageService
from app.integrations.llm import LLMIntegration
from app.integrations.elevenlabs import ElevenLabsIntegration
from app.integrations.deepgram import DeepgramIntegration
from app.websocket import manager

async def process_call_task(call_id: str, audio_data: str = None):
    """Process voice call with LLM, TTS, and STT"""
    db = SessionLocal()
    
    try:
        call_service = CallService(db)
        call = call_service.get_call(uuid.UUID(call_id), None)
        
        if not call:
            raise ValueError(f"Call {call_id} not found")
        
        # Get assistant
        assistant = db.query(Assistant).filter(
            Assistant.id == call.assistant_id
        ).first()
        
        if not assistant:
            raise ValueError(f"Assistant not found for call {call_id}")
        
        # Update call status
        call_service.update_call(
            call_id=uuid.UUID(call_id),
            organization_id=call.organization_id,
            call_data={"status": "processing"}
        )
        
        # Process with integrations
        result = await _process_call_with_ai(call, assistant, audio_data)
        
        # Update call with results
        call_service.update_call(
            call_id=uuid.UUID(call_id),
            organization_id=call.organization_id,
            call_data={
                "status": "completed",
                "transcript": result.get("transcript"),
                "cost_usd": result.get("total_cost", 0),
                "cost_breakdown": result.get("cost_breakdown", {})
            }
        )
        
        # Track usage
        if result.get("usage_data"):
            usage_service = UsageService(db)
            usage_service.track_call_usage(
                call_id=uuid.UUID(call_id),
                organization_id=call.organization_id,
                usage_data=result["usage_data"]
            )
        
        return {"status": "completed", "call_id": call_id}
        
    except Exception as e:
        # Mark call as failed
        if 'call_service' in locals() and 'call' in locals():
            call_service.update_call(
                call_id=uuid.UUID(call_id),
                organization_id=call.organization_id,
                call_data={"status": "failed", "end_reason": str(e)}
            )
        
        raise e
        
    finally:
        db.close()

async def _process_call_with_ai(call: Call, assistant: Assistant, audio_data: str = None):
    """Internal function to process call with AI integrations"""
    
    llm_integration = LLMIntegration()
    tts_integration = ElevenLabsIntegration()
    stt_integration = DeepgramIntegration()
    
    total_cost = 0.0
    cost_breakdown = {}
    usage_data = {}
    transcript = ""
    
    try:
        # Step 1: Speech-to-Text (if audio provided)
        if audio_data:
            stt_result = await stt_integration.speech_to_text(
                audio_data=audio_data.encode(),
                model=assistant.transcriber_model
            )
            
            if stt_result.get("success"):
                transcript = stt_result["transcript"]
                
                # Calculate STT cost
                audio_duration = len(audio_data) / 1000  # Approximate duration
                stt_cost = stt_integration.calculate_cost(audio_duration, assistant.transcriber_model)
                total_cost += stt_cost
                cost_breakdown["stt"] = stt_cost
                
                usage_data["stt"] = {
                    "quantity": audio_duration,
                    "unit": "seconds",
                    "unit_cost": stt_cost / audio_duration if audio_duration > 0 else 0,
                    "total_cost": stt_cost,
                    "provider": "deepgram",
                    "model_name": assistant.transcriber_model
                }
        
        # Step 2: LLM Processing
        messages = [
            {"role": "system", "content": assistant.system_prompt or "You are a helpful assistant."}
        ]
        
        if transcript:
            messages.append({"role": "user", "content": transcript})
        elif assistant.first_message:
            messages.append({"role": "assistant", "content": assistant.first_message})
        
        llm_result = await llm_integration.generate_response(
            provider=assistant.model_provider,
            messages=messages,
            model=assistant.model_name, 
            temperature=assistant.model_temperature,
            max_tokens=assistant.model_max_tokens,
            tools=assistant.tools if hasattr(assistant, 'tools') else None
        )
        
        response_text = ""
        if llm_result.get("success"):
            response_text = llm_result["response"]
            
            # Calculate LLM cost (simplified)
            if llm_result.get("usage"):
                tokens_used = llm_result["usage"].get("total_tokens", 0)
                llm_cost = tokens_used * 0.00002  # Approximate cost per token
                total_cost += llm_cost
                cost_breakdown["llm"] = llm_cost
                
                usage_data["llm"] = {
                    "quantity": tokens_used,
                    "unit": "tokens",
                    "unit_cost": 0.00002,
                    "total_cost": llm_cost,
                    "provider": assistant.model_provider,
                    "model_name": assistant.model_name
                }
        
        # Step 3: Text-to-Speech
        if response_text:
            tts_result = await tts_integration.text_to_speech(
                text=response_text,
                voice_id=assistant.voice_id,
                voice_settings=assistant.voice_settings
            )
            
            if tts_result.get("success"):
                # Calculate TTS cost
                char_count = len(response_text)
                tts_cost = tts_integration.calculate_cost(char_count)
                total_cost += tts_cost
                cost_breakdown["tts"] = tts_cost
                
                usage_data["tts"] = {
                    "quantity": char_count,
                    "unit": "characters",
                    "unit_cost": tts_cost / char_count if char_count > 0 else 0,
                    "total_cost": tts_cost,
                    "provider": "elevenlabs",
                    "model_name": "eleven_turbo_v2"
                }
        
        return {
            "transcript": transcript,
            "response": response_text,
            "total_cost": total_cost,
            "cost_breakdown": cost_breakdown,
            "usage_data": usage_data
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "transcript": transcript,
            "total_cost": total_cost,
            "cost_breakdown": cost_breakdown
        }

async def end_call_task(call_id: str, end_reason: str = "completed"):
    """End call and perform cleanup"""
    db = SessionLocal()
    
    try:
        call_service = CallService(db)
        call = call_service.end_call(
            call_id=uuid.UUID(call_id),
            organization_id=None,  # Will be validated in service
            end_reason=end_reason
        )
        
        if call:
            # Send webhook notification
            from app.workers.webhook_worker import send_webhook_task
            await send_webhook_task(
                call_id=call_id,
                event_type="call.ended",
                data={
                    "call_id": call_id,
                    "status": call.status,
                    "end_reason": end_reason,
                    "duration_seconds": call.duration_seconds,
                    "cost_usd": call.cost_usd
                }
            )
        
        return {"status": "ended", "call_id": call_id}
        
    except Exception as e:
        raise e
        
    finally:
        db.close()

def cleanup_old_calls_task():
    """Clean up old call data (older than 90 days)"""
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # Delete old calls
        deleted_count = db.query(Call).filter(
            Call.created_at < cutoff_date,
            Call.status.in_(["completed", "failed"])
        ).delete()
        
        db.commit()
        
        return {"deleted_calls": deleted_count}
        
    except Exception as e:
        db.rollback()
        raise e
        
    finally:
        db.close()