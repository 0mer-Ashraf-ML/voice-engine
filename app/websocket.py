from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import uuid
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.call_connections: Dict[str, str] = {}  # call_id -> connection_id
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from call connections
        call_id = None
        for cid, conn_id in self.call_connections.items():
            if conn_id == connection_id:
                call_id = cid
                break
        
        if call_id:
            del self.call_connections[call_id]
    
    async def send_personal_message(self, message: str, connection_id: str):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(message)
    
    async def send_call_message(self, message: dict, call_id: str):
        """Send message to specific call session"""
        if call_id in self.call_connections:
            connection_id = self.call_connections[call_id]
            await self.send_personal_message(json.dumps(message), connection_id)
    
    def register_call(self, call_id: str, connection_id: str):
        """Register a call with a WebSocket connection"""
        self.call_connections[call_id] = connection_id
    
    async def broadcast_call_status(self, call_id: str, status: str, data: dict = None):
        """Broadcast call status update"""
        message = {
            "type": "status-update",
            "call_id": call_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        }
        await self.send_call_message(message, call_id)
    
    async def broadcast_transcript(self, call_id: str, transcript: str, is_user: bool = True):
        """Broadcast transcript update"""
        message = {
            "type": "transcript",
            "call_id": call_id,
            "transcript": transcript,
            "is_user": is_user,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_call_message(message, call_id)

manager = ConnectionManager()