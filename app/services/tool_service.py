from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate
from datetime import datetime, timezone
import uuid
import httpx
import asyncio

class ToolService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_tools(
        self, 
        organization_id: uuid.UUID, 
        limit: int = 100, 
        offset: int = 0,
        tool_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Tool]:
        query = self.db.query(Tool).filter(
            Tool.organization_id == organization_id
        )
        
        if tool_type:
            query = query.filter(Tool.type == tool_type)
        
        if is_active is not None:
            query = query.filter(Tool.is_active == is_active)
        
        return query.offset(offset).limit(limit).all()
    
    def create_tool(
        self, 
        organization_id: uuid.UUID, 
        tool_data: ToolCreate
    ) -> Tool:
        tool = Tool(
            organization_id=organization_id,
            **tool_data.model_dump()
        )
        
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        
        return tool
    
    def get_tool(
        self, 
        tool_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> Optional[Tool]:
        return self.db.query(Tool).filter(
            Tool.id == tool_id,
            Tool.organization_id == organization_id
        ).first()
    
    def update_tool(
        self,
        tool_id: uuid.UUID,
        organization_id: uuid.UUID,
        tool_data: ToolUpdate
    ) -> Optional[Tool]:
        tool = self.get_tool(tool_id, organization_id)
        
        if not tool:
            return None
        
        update_data = tool_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tool, field, value)
        
        tool.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(tool)
        
        return tool
    
    def delete_tool(
        self, 
        tool_id: uuid.UUID, 
        organization_id: uuid.UUID
    ) -> bool:
        tool = self.get_tool(tool_id, organization_id)
        
        if not tool:
            return False
        
        self.db.delete(tool)
        self.db.commit()
        
        return True
    
    async def test_tool(
        self,
        tool_id: uuid.UUID,
        organization_id: uuid.UUID,
        test_data: dict = {}
    ) -> Optional[dict]:
        tool = self.get_tool(tool_id, organization_id)
        
        if not tool:
            return None
        
        if tool.type == "webhook":
            return await self._test_webhook(tool, test_data)
        elif tool.type == "function":
            return await self._test_function(tool, test_data)
        else:
            return {"error": "Unsupported tool type"}
    
    async def _test_webhook(self, tool: Tool, test_data: dict) -> dict:
        if not tool.webhook_url:
            return {"error": "No webhook URL configured"}
        
        try:
            headers = tool.webhook_headers or {}
            headers["Content-Type"] = "application/json"
            
            async with httpx.AsyncClient(timeout=tool.webhook_timeout) as client:
                response = await client.request(
                    method=tool.webhook_method,
                    url=tool.webhook_url,
                    json=test_data,
                    headers=headers
                )
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_body": response.text,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout",
                "timeout_seconds": tool.webhook_timeout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_function(self, tool: Tool, test_data: dict) -> dict:
        if not tool.function_schema:
            return {"error": "No function schema configured"}
        
        # Validate test_data against function schema
        try:
            schema = tool.function_schema
            required_params = schema.get("parameters", {}).get("required", [])
            
            missing_params = [param for param in required_params if param not in test_data]
            if missing_params:
                return {
                    "success": False,
                    "error": f"Missing required parameters: {missing_params}"
                }
            
            return {
                "success": True,
                "message": "Function schema validation passed",
                "schema": schema,
                "test_data": test_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Schema validation failed: {str(e)}"
            }
    
    async def execute_tool(
        self,
        tool_id: uuid.UUID,
        organization_id: uuid.UUID,
        execution_data: dict,
        call_id: Optional[uuid.UUID] = None
    ) -> dict:
        tool = self.get_tool(tool_id, organization_id)
        
        if not tool or not tool.is_active:
            return {"error": "Tool not found or inactive"}
        
        # Add call context to execution data
        if call_id:
            execution_data["call_id"] = str(call_id)
            execution_data["organization_id"] = str(organization_id)
        
        # Execute with retry logic
        for attempt in range(tool.retry_attempts):
            try:
                if tool.type == "webhook":
                    result = await self._execute_webhook(tool, execution_data)
                elif tool.type == "function":
                    result = await self._execute_function(tool, execution_data)
                else:
                    result = {"error": "Unsupported tool type"}
                
                if result.get("success"):
                    return result
                
            except Exception as e:
                if attempt == tool.retry_attempts - 1:  # Last attempt
                    return {"error": f"Tool execution failed after {tool.retry_attempts} attempts: {str(e)}"}
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {"error": "Tool execution failed"}
    
    async def _execute_webhook(self, tool: Tool, data: dict) -> dict:
        headers = tool.webhook_headers or {}
        headers["Content-Type"] = "application/json"
        
        async with httpx.AsyncClient(timeout=tool.webhook_timeout) as client:
            response = await client.request(
                method=tool.webhook_method,
                url=tool.webhook_url,
                json=data,
                headers=headers
            )
            
            if response.status_code < 400:
                return {
                    "success": True,
                    "result": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
    
    async def _execute_function(self, tool: Tool, data: dict) -> dict:
        # For function tools, we return the structured data for the LLM to process
        return {
            "success": True,
            "function_name": tool.function_schema.get("name"),
            "parameters": data,
            "result": "Function call prepared for LLM processing"
        }