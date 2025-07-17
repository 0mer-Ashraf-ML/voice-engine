from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.phone_number import PhoneNumber
from app.schemas.phone_number import PhoneNumberCreate, PhoneNumberUpdate
from app.integrations.telephony import TwilioIntegration
from datetime import datetime, timezone
import uuid
import re

class PhoneService:
    def __init__(self, db: Session):
        self.db = db
        self.twilio = TwilioIntegration()
    
    def list_phone_numbers(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        provider: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[PhoneNumber]:
        query = self.db.query(PhoneNumber).filter(
            PhoneNumber.organization_id == organization_id
        )
        
        if provider:
            query = query.filter(PhoneNumber.provider == provider)
        
        if is_active is not None:
            query = query.filter(PhoneNumber.is_active == is_active)
        
        return query.offset(offset).limit(limit).all()
    
    def create_phone_number(
        self, 
        organization_id: uuid.UUID, 
        phone_data: PhoneNumberCreate
    ) -> PhoneNumber:
        # Format phone number
        formatted_number = self._format_phone_number(
            phone_data.phone_number, 
            phone_data.country_code
        )
        
        phone_number = PhoneNumber(
            organization_id=organization_id,
            formatted_number=formatted_number,
            provider_id=f"manual_{uuid.uuid4()}",  # Manual entry
            **phone_data.model_dump()
        )
        
        self.db.add(phone_number)
        self.db.commit()
        self.db.refresh(phone_number)
        
        return phone_number
    
    def get_phone_number(
        self, 
        phone_number_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[PhoneNumber]:
        return self.db.query(PhoneNumber).filter(
            PhoneNumber.id == phone_number_id,
            PhoneNumber.organization_id == organization_id
        ).first()
    
    def update_phone_number(
        self,
        phone_number_id: uuid.UUID,
        organization_id: uuid.UUID,
        phone_data: PhoneNumberUpdate
    ) -> Optional[PhoneNumber]:
        phone_number = self.get_phone_number(phone_number_id, organization_id)
        
        if not phone_number:
            return None
        
        update_data = phone_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(phone_number, field, value)
        
        phone_number.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(phone_number)
        
        return phone_number
    
    def delete_phone_number(
        self, 
        phone_number_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        phone_number = self.get_phone_number(phone_number_id, organization_id)
        
        if not phone_number:
            return False
        
        # Release number from provider if needed
        if phone_number.provider == "twilio" and phone_number.provider_id:
            try:
                self.twilio.release_phone_number(phone_number.provider_id)
            except Exception as e:
                print(f"Error releasing Twilio number: {e}")
        
        self.db.delete(phone_number)
        self.db.commit()
        
        return True
    
    def purchase_phone_number(
        self,
        organization_id: uuid.UUID,
        area_code: str,
        provider: str = "twilio"
    ) -> Optional[PhoneNumber]:
        if provider == "twilio":
            try:
                # Purchase number from Twilio
                twilio_number = self.twilio.purchase_phone_number(area_code)
                
                if not twilio_number:
                    return None
                
                # Create phone number record
                phone_number = PhoneNumber(
                    organization_id=organization_id,
                    phone_number=twilio_number["phone_number"],
                    country_code=twilio_number["country_code"],
                    area_code=area_code,
                    formatted_number=twilio_number["formatted_number"],
                    provider="twilio",
                    provider_id=twilio_number["sid"],
                    provider_config=twilio_number.get("config", {}),
                    name=f"Twilio {area_code}"
                )
                
                self.db.add(phone_number)
                self.db.commit()
                self.db.refresh(phone_number)
                
                return phone_number
                
            except Exception as e:
                print(f"Error purchasing Twilio number: {e}")
                return None
        
        return None
    
    def _format_phone_number(self, phone_number: str, country_code: str) -> str:
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', phone_number)
        
        # Add country code if not present
        if not digits_only.startswith(country_code.replace('+', '')):
            digits_only = country_code.replace('+', '') + digits_only
        
        # Format as +1 (555) 123-4567 for US numbers
        if country_code == '+1' and len(digits_only) == 11:
            return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        
        # Default format
        return f"+{digits_only}"
    
    def get_available_numbers(
        self,
        area_code: str,
        provider: str = "twilio",
        limit: int = 10
    ) -> List[dict]:
        if provider == "twilio":
            return self.twilio.search_available_numbers(area_code, limit)
        
        return []