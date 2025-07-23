import httpx
from typing import Dict, Any, List, Optional
from app.config import settings
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

class BaseTelephonyProvider:
    def __init__(self):
        pass
    
    async def make_call(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def purchase_phone_number(self, area_code: str) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def release_phone_number(self, number_id: str) -> bool:
        raise NotImplementedError

class TwilioIntegration(BaseTelephonyProvider):
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        
        if self.account_sid and self.auth_token:
            self.client = TwilioClient(self.account_sid, self.auth_token)
        else:
            self.client = None
    
    async def make_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str,
        status_callback_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not self.client:
            return {"error": "Twilio credentials not configured"}
        
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=webhook_url,
                status_callback=status_callback_url,
                **kwargs
            )
            
            return {
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "to": call.to,
                "from": call.from_,
                "provider": "twilio"
            }
            
        except TwilioException as e:
            return {"error": f"Twilio error: {str(e)}"}
        except Exception as e:
            return {"error": f"Call failed: {str(e)}"}
    
    async def purchase_phone_number(self, area_code: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        
        try:
            # Search for available numbers
            available_numbers = self.client.available_phone_numbers("US").local.list(
                area_code=area_code,
                limit=1
            )
            
            if not available_numbers:
                return None
            
            # Purchase the first available number
            number = available_numbers[0]
            purchased_number = self.client.incoming_phone_numbers.create(
                phone_number=number.phone_number
            )
            
            return {
                "phone_number": purchased_number.phone_number,
                "country_code": "+1",
                "formatted_number": purchased_number.friendly_name,
                "sid": purchased_number.sid,
                "config": {
                    "voice_url": None,
                    "status_callback": None
                }
            }
            
        except TwilioException as e:
            print(f"Twilio purchase error: {str(e)}")
            return None
        except Exception as e:
            print(f"Purchase failed: {str(e)}")
            return None
    
    async def release_phone_number(self, number_sid: str) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.incoming_phone_numbers(number_sid).delete()
            return True
        except TwilioException:
            return False
        except Exception:
            return False
    
    def search_available_numbers(
        self, 
        area_code: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        
        try:
            numbers = self.client.available_phone_numbers("US").local.list(
                area_code=area_code,
                limit=limit
            )
            
            return [
                {
                    "phone_number": num.phone_number,
                    "friendly_name": num.friendly_name,
                    "locality": num.locality,
                    "region": num.region,
                    "capabilities": {
                        "voice": num.capabilities.get("voice", False),
                        "sms": num.capabilities.get("SMS", False),
                        "mms": num.capabilities.get("MMS", False)
                    }
                }
                for num in numbers
            ]
            
        except TwilioException:
            return []
        except Exception:
            return []
    
    async def update_phone_number_webhook(
        self, 
        number_sid: str, 
        voice_url: str,
        status_callback_url: Optional[str] = None
    ) -> bool:
        if not self.client:
            return False
        
        try:
            self.client.incoming_phone_numbers(number_sid).update(
                voice_url=voice_url,
                status_callback=status_callback_url
            )
            return True
        except TwilioException:
            return False
        except Exception:
            return False
    
    def generate_twiml_response(
        self, 
        message: str,
        voice: str = "alice",
        language: str = "en-US"
    ) -> str:
        """Generate TwiML response for voice calls"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}" language="{language}">{message}</Say>
</Response>"""
    
    def generate_twiml_gather(
        self,
        prompt: str,
        action_url: str,
        timeout: int = 5,
        num_digits: int = 1
    ) -> str:
        """Generate TwiML for gathering user input"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather action="{action_url}" timeout="{timeout}" numDigits="{num_digits}">
        <Say>{prompt}</Say>
    </Gather>
</Response>"""


class TelephonyIntegration:
    def __init__(self):
        self.providers = {
            "twilio": TwilioIntegration()
        }
    
    async def make_call(
        self,
        provider: str,
        **kwargs
    ) -> Dict[str, Any]:
        if provider not in self.providers:
            return {"error": f"Unsupported telephony provider: {provider}"}
        
        return await self.providers[provider].make_call(**kwargs)
    
    async def purchase_phone_number(
        self,
        provider: str,
        area_code: str
    ) -> Optional[Dict[str, Any]]:
        if provider not in self.providers:
            return None
        
        return await self.providers[provider].purchase_phone_number(area_code)
    
    async def release_phone_number(
        self,
        provider: str,
        number_id: str
    ) -> bool:
        if provider not in self.providers:
            return False
        
        return await self.providers[provider].release_phone_number(number_id)
    
    def get_supported_providers(self) -> List[str]:
        return list(self.providers.keys())