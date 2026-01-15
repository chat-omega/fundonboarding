"""Unified API router for the Intelligent Fund Onboarding System."""

import asyncio
import uuid
import logging
from typing import Dict, AsyncGenerator
from pathlib import Path
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Configure logging for this module
logger = logging.getLogger(__name__)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.chat_orchestrator import ChatOrchestrator
from agents.base_agent import AgentMessage, MessageType, agent_registry, AgentContext
from models.unified_models import ProcessingSession, ChatResponse


# Request/Response models
class ChatMessage(BaseModel):
    message: str
    session_id: str
    metadata: Dict = {}


class FileUploadRequest(BaseModel):
    session_id: str
    file_type: str = "csv"


class ProcessingRequest(BaseModel):
    session_id: str
    action: str
    data: Dict = {}


# Router instance
router = APIRouter(prefix="/api/onboarding", tags=["Fund Onboarding"])

# Session storage (in production, use Redis/database)
active_sessions: Dict[str, ChatOrchestrator] = {}
session_data: Dict[str, ProcessingSession] = {}


@router.post("/session/create")
async def create_session():
    """Create a new onboarding session."""
    session_id = str(uuid.uuid4())
    logger.info(f"📋 Creating new onboarding session: {session_id}")
    
    try:
        # Create orchestrator instance
        logger.info(f"📋 Initializing ChatOrchestrator for session: {session_id}")
        orchestrator = ChatOrchestrator(session_id)
        
        # Initialize with basic context
        context = AgentContext(
            session_id=session_id,
            processing_stage="idle"
        )
        
        await orchestrator.initialize(context)
        logger.info(f"📋 ChatOrchestrator initialized successfully for session: {session_id}")
        
        # Store session
        active_sessions[session_id] = orchestrator
        session_data[session_id] = ProcessingSession(
            session_id=session_id,
            file_type="csv"  # Default to csv
        )
        
        logger.info(f"📋 Session created successfully: {session_id}")
        return {
            "session_id": session_id,
            "status": "created",
            "message": "Session created successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to create session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/upload")
async def upload_portfolio_file(
    session_id: str,
    file: UploadFile = File(...)
):
    """Upload portfolio file (CSV/Excel/PDF)."""
    logger.info(f"📤 Upload request for session {session_id}, file: {file.filename}")
    
    if session_id not in active_sessions:
        logger.error(f"❌ Upload failed - Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file type
    allowed_extensions = {'.csv', '.xlsx', '.xls', '.pdf'}
    file_suffix = Path(file.filename).suffix.lower()
    
    if file_suffix not in allowed_extensions:
        logger.error(f"❌ Upload failed - Invalid file type {file_suffix} for {file.filename}")
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Try to upload to S3 first
        try:
            import sys
            sys.path.append('..')
            from utils.s3_storage import get_s3_storage
            
            s3_storage = get_s3_storage()
            if s3_storage:
                try:
                    s3_url = await s3_storage.upload_file(
                        file_content=content,
                        filename=file.filename,
                        content_type=file.content_type
                    )
                    
                    logger.info(f"📤 File uploaded to S3: {file.filename} ({file_size} bytes)")
                    
                    # Update session with S3 URL
                    if session_id in session_data:
                        session_data[session_id].input_file_path = s3_url
                        session_data[session_id].file_type = file_suffix[1:]  # Remove dot
                        logger.info(f"📤 Session {session_id} updated with S3 file: {s3_url}")
                    
                    return {
                        "session_id": session_id,
                        "file_path": s3_url,  # Return S3 URL
                        "filename": file.filename,
                        "size": file_size,
                        "file_type": file_suffix[1:],
                        "storage": "s3"
                    }
                    
                except Exception as s3_error:
                    logger.warning(f"⚠️ S3 upload failed, falling back to local storage: {str(s3_error)}")
        except ImportError:
            logger.warning("⚠️ S3 storage not available, using local storage")
        
        # Fallback to local storage
        upload_dir = Path("/app/data/uploads") if Path("/app/data/uploads").parent.exists() else Path("../../data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📤 Upload directory: {upload_dir.absolute()}")
        
        # Save uploaded file locally
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = upload_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"📤 File saved locally: {file_path} ({file_size} bytes)")
        
        # Update session with local path
        if session_id in session_data:
            session_data[session_id].input_file_path = str(file_path)
            session_data[session_id].file_type = file_suffix[1:]  # Remove dot
            logger.info(f"📤 Session {session_id} updated with local file: {file_path}")
        
        return {
            "session_id": session_id,
            "file_path": str(file_path),
            "filename": file.filename,
            "size": file_size,
            "file_type": file_suffix[1:],
            "storage": "local"
        }
        
    except Exception as e:
        logger.error(f"❌ File upload failed for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/process")
async def start_processing(request: ProcessingRequest):
    """Start processing uploaded file."""
    logger.info(f"🔄 Processing request for session {request.session_id}, action: {request.action}")
    
    if request.session_id not in active_sessions:
        logger.error(f"❌ Processing failed - Session not found: {request.session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = active_sessions[request.session_id]
    session = session_data.get(request.session_id)
    
    if not session or not session.input_file_path:
        logger.error(f"❌ Processing failed - No file uploaded for session: {request.session_id}")
        raise HTTPException(status_code=400, detail="No file uploaded for this session")
    
    logger.info(f"🔄 Found file for processing: {session.input_file_path} (type: {session.file_type})")
    
    try:
        # Create processing message
        message = AgentMessage(
            type=MessageType.REQUEST_ACTION,
            sender=None,
            recipient=None,
            data={
                "action": "upload_file",
                "file_path": session.input_file_path,
                "file_type": session.file_type
            },
            session_id=request.session_id
        )
        logger.info(f"🔄 Created processing message for session {request.session_id}")
        
        # Start processing (async) - THIS IS THE CRITICAL PART
        logger.info(f"🔄 Starting async processing task for session {request.session_id}")
        task = asyncio.create_task(orchestrator.handle_message(message).__anext__())
        logger.info(f"🔄 Async processing task created for session {request.session_id}: {task}")
        
        return {
            "session_id": request.session_id,
            "status": "processing_started",
            "message": "Processing started. Use /stream endpoint for real-time updates."
        }
        
    except Exception as e:
        logger.error(f"❌ Processing failed for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/stream/{session_id}")
async def stream_updates(session_id: str):
    """Stream real-time updates for a session."""
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = active_sessions[session_id]
    
    async def event_generator():
        """Generate SSE events from agent messages."""
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({
                    "session_id": session_id,
                    "status": "connected"
                })
            }
            
            # This is a simplified version - in practice, you'd want to set up
            # a proper message queue or pub/sub system for real-time updates
            session = session_data.get(session_id)
            if session:
                # Send current session state
                yield {
                    "event": "session_state",
                    "data": json.dumps({
                        "stage": session.stage,
                        "progress": session.progress,
                        "status": session.status
                    })
                }
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": str(asyncio.get_event_loop().time())})
                }
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())


@router.post("/chat")
async def send_chat_message(message_request: ChatMessage):
    """Send a chat message and get response."""
    
    if message_request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = active_sessions[message_request.session_id]
    
    try:
        # Create chat message
        agent_message = AgentMessage(
            type=MessageType.REQUEST_ACTION,
            sender=None,
            recipient=None,
            data={
                "action": "chat_message",
                "message": message_request.message,
                "metadata": message_request.metadata
            },
            session_id=message_request.session_id
        )
        
        # Get response from orchestrator
        responses = []
        async for response in orchestrator.handle_message(agent_message):
            if response.type == MessageType.CHAT_RESPONSE:
                responses.append(response.data)
        
        if responses:
            return responses[0]  # Return first response
        else:
            return {
                "message": "I received your message. Processing...",
                "message_type": "info",
                "session_id": message_request.session_id
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status and data."""
    
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_data[session_id]
    
    return {
        "session_id": session_id,
        "stage": session.stage,
        "progress": session.progress,
        "status": session.status,
        "portfolio_items_count": len(session.portfolio_items),
        "fund_extractions_count": len(session.fund_extractions),
        "chat_history_length": len(session.chat_history),
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@router.get("/session/{session_id}/portfolio")
async def get_portfolio_data(session_id: str):
    """Get processed portfolio data."""
    
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_data[session_id]
    
    return {
        "session_id": session_id,
        "portfolio_items": [item.model_dump() for item in session.portfolio_items],
        "portfolio_analysis": session.portfolio_analysis.model_dump() if session.portfolio_analysis else None
    }


@router.get("/session/{session_id}/funds")
async def get_fund_data(session_id: str):
    """Get extracted fund data."""
    
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_data[session_id]
    
    return {
        "session_id": session_id,
        "fund_extractions": {
            ticker: fund.model_dump() 
            for ticker, fund in session.fund_extractions.items()
        }
    }


@router.get("/session/{session_id}/chat")
async def get_chat_history(session_id: str):
    """Get chat conversation history."""
    
    if session_id not in session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_data[session_id]
    
    return {
        "session_id": session_id,
        "chat_history": session.chat_history
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and cleanup resources."""
    
    # Cleanup orchestrator
    if session_id in active_sessions:
        orchestrator = active_sessions[session_id]
        await orchestrator.shutdown()
        del active_sessions[session_id]
    
    # Cleanup session data
    if session_id in session_data:
        del session_data[session_id]
    
    # Cleanup from registry
    await agent_registry.shutdown_session(session_id)
    
    return {
        "session_id": session_id,
        "status": "deleted"
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "message": "Intelligent Fund Onboarding API is running"
    }


# Enhanced streaming endpoint with proper message handling
@router.get("/enhanced-stream/{session_id}")
async def enhanced_stream(session_id: str):
    """Enhanced streaming with proper agent message handling."""
    logger.info(f"🌊 Enhanced streaming request for session: {session_id}")
    
    if session_id not in active_sessions:
        logger.error(f"❌ Enhanced streaming failed - Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = active_sessions[session_id]
    logger.info(f"🌊 Found orchestrator for session {session_id}: {type(orchestrator)}")
    
    async def enhanced_event_generator():
        """Generate events from actual agent messages."""
        try:
            # Send connection confirmation
            logger.info(f"🌊 Sending connection event for session {session_id}")
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Start processing if file is uploaded
            session = session_data.get(session_id)
            logger.info(f"🌊 Session status for {session_id}: {session.status if session else 'None'}")
            logger.info(f"🌊 Session file path for {session_id}: {session.input_file_path if session else 'None'}")
            
            if session and session.input_file_path and session.status == "idle":
                logger.info(f"🌊 Starting processing via streaming for session {session_id}")
                # Trigger processing
                process_message = AgentMessage(
                    type=MessageType.REQUEST_ACTION,
                    sender=None,
                    recipient=None,
                    data={
                        "action": "upload_file",
                        "file_path": session.input_file_path,
                        "file_type": session.file_type
                    },
                    session_id=session_id
                )
                logger.info(f"🌊 Created process message: {process_message.data}")
                
                # Stream responses - THIS IS THE CRITICAL PART
                logger.info(f"🌊 Starting to iterate over orchestrator.handle_message responses...")
                async for response in orchestrator.handle_message(process_message):
                    logger.info(f"🌊 Received response from orchestrator: {response.type.value}")
                    event_data = {
                        "type": response.type.value,
                        "data": response.data,
                        "timestamp": response.timestamp.isoformat() if response.timestamp else None
                    }
                    logger.info(f"🌊 Sending event data: {event_data}")
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.1)
                    
                logger.info(f"🌊 Finished processing messages for session {session_id}")
            else:
                logger.warning(f"🌊 Cannot start processing for session {session_id}: session={session is not None}, file_path={session.input_file_path if session else 'N/A'}, status={session.status if session else 'N/A'}")
            
            # Keep alive
            logger.info(f"🌊 Starting keep-alive heartbeats for session {session_id}")
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                
        except asyncio.CancelledError:
            logger.info(f"🌊 Streaming cancelled for session {session_id}")
            pass
        except Exception as e:
            logger.error(f"❌ Enhanced streaming error for session {session_id}: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        enhanced_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Test endpoint with sample data
@router.post("/test-sample")
async def test_with_sample_data():
    """Test the system with sample portfolio data."""
    session_id = str(uuid.uuid4())
    
    # Use the existing sample CSV
    sample_file_path = "/home/ec2-user/omega-mvp/sample_model_portfolios_table.csv"
    
    if not Path(sample_file_path).exists():
        raise HTTPException(status_code=404, detail="Sample file not found")
    
    # Create session
    orchestrator = ChatOrchestrator(session_id)
    context = AgentContext(
        session_id=session_id,
        input_file_path=sample_file_path,
        file_type="csv"
    )
    
    await orchestrator.initialize(context)
    
    # Store session
    active_sessions[session_id] = orchestrator
    session_data[session_id] = ProcessingSession(
        session_id=session_id,
        input_file_path=sample_file_path,
        file_type="csv"
    )
    
    return {
        "session_id": session_id,
        "sample_file": sample_file_path,
        "message": "Test session created with sample data. Use /enhanced-stream endpoint to see processing."
    }