"""Base agent class for the Intelligent Fund Onboarding System."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import uuid
from datetime import datetime

from pydantic import BaseModel

# Temporarily disable tracing imports to debug
TRACING_AVAILABLE = False


class AgentType(str, Enum):
    """Types of agents in the system."""
    INTAKE = "intake"
    RESEARCH = "research"
    EXTRACTION = "extraction"
    CATEGORIZATION = "categorization"
    VALIDATION = "validation"
    CHAT_ORCHESTRATOR = "chat_orchestrator"


class MessageType(str, Enum):
    """Types of messages between agents."""
    STATUS_UPDATE = "status_update"
    DATA_PROCESSED = "data_processed"
    REQUEST_ACTION = "request_action"
    VALIDATION_RESULT = "validation_result"
    CHAT_RESPONSE = "chat_response"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Message structure for inter-agent communication."""
    type: MessageType
    sender: AgentType
    recipient: Optional[AgentType]
    data: Dict[str, Any]
    session_id: str
    timestamp: datetime = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())


class AgentContext(BaseModel):
    """Context shared across all agents in a session."""
    session_id: str
    user_id: Optional[str] = None
    input_file_path: Optional[str] = None
    file_type: Optional[str] = None
    portfolio_data: Optional[Dict] = None
    portfolio_items: List = []  # Add this field for portfolio items
    fund_data: Optional[Dict] = None
    chat_history: List[Dict] = []
    confidence_scores: Dict[str, float] = {}
    processing_stage: str = "idle"
    preferences: Dict[str, Any] = {}


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, agent_type: AgentType, session_id: str):
        self.agent_type = agent_type
        self.session_id = session_id
        self.context: Optional[AgentContext] = None
        self.message_handlers: Dict[MessageType, callable] = {}
        self.is_active = False
        
    async def initialize(self, context: AgentContext) -> None:
        """Initialize the agent with session context."""
        self.context = context
        self.is_active = True
        
        if TRACING_AVAILABLE:
            log_event("agent_initialized", 
                     agent_type=self.agent_type.value,
                     session_id=self.session_id)
        
        await self._setup()
        
    async def shutdown(self) -> None:
        """Shutdown the agent and cleanup resources."""
        if TRACING_AVAILABLE:
            log_event("agent_shutdown", 
                     agent_type=self.agent_type.value,
                     session_id=self.session_id)
        
        self.is_active = False
        await self._cleanup()
        
    @abstractmethod
    async def _setup(self) -> None:
        """Agent-specific setup logic."""
        pass
        
    @abstractmethod
    async def _cleanup(self) -> None:
        """Agent-specific cleanup logic."""
        pass
        
    @abstractmethod
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Process incoming messages and yield responses."""
        yield AgentMessage(
            type=MessageType.STATUS_UPDATE,
            sender=self.agent_type,
            recipient=None,
            data={"status": "processing", "message": f"{self.agent_type} processing message"},
            session_id=self.session_id
        )
        
    def register_message_handler(self, message_type: MessageType, handler: callable):
        """Register a handler for specific message types."""
        self.message_handlers[message_type] = handler
        
    async def handle_message(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle incoming messages using registered handlers or default process method."""
        if message.type in self.message_handlers:
            handler = self.message_handlers[message.type]
            async for response in handler(message):
                yield response
        else:
            async for response in self.process(message):
                yield response
                
    def create_message(self, 
                      message_type: MessageType, 
                      recipient: Optional[AgentType], 
                      data: Dict[str, Any]) -> AgentMessage:
        """Create a new message from this agent."""
        return AgentMessage(
            type=message_type,
            sender=self.agent_type,
            recipient=recipient,
            data=data,
            session_id=self.session_id
        )
        
    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update the shared context with new data."""
        if self.context:
            for key, value in updates.items():
                if hasattr(self.context, key):
                    setattr(self.context, key, value)
                    
    def get_confidence_score(self, operation: str) -> float:
        """Get confidence score for a specific operation."""
        if self.context and operation in self.context.confidence_scores:
            return self.context.confidence_scores[operation]
        return 0.0
        
    def set_confidence_score(self, operation: str, score: float) -> None:
        """Set confidence score for a specific operation."""
        if self.context:
            self.context.confidence_scores[operation] = max(0.0, min(1.0, score))
            
    async def emit_status(self, status: str, details: Dict[str, Any] = None) -> AgentMessage:
        """Emit a status update message."""
        data = {"status": status, "agent": self.agent_type.value}
        if details:
            data.update(details)
        
        if TRACING_AVAILABLE:
            log_event("status_update", 
                     agent_type=self.agent_type.value,
                     status=status,
                     details=details or {})
            
        return self.create_message(
            message_type=MessageType.STATUS_UPDATE,
            recipient=None,
            data=data
        )
        
    async def emit_error(self, error: str, details: Dict[str, Any] = None) -> AgentMessage:
        """Emit an error message."""
        data = {"error": error, "agent": self.agent_type.value}
        if details:
            data.update(details)
        
        if TRACING_AVAILABLE:
            log_event("agent_error", 
                     agent_type=self.agent_type.value,
                     error=error,
                     details=details or {})
            
        return self.create_message(
            message_type=MessageType.ERROR,
            recipient=None,
            data=data
        )


class AgentCapability(BaseModel):
    """Describes what an agent can do."""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    confidence_threshold: float = 0.5
    requires_human_review: bool = False


class AgentRegistry:
    """Registry to manage agent instances and capabilities."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}  # session_id -> agent
        self.capabilities: Dict[AgentType, List[AgentCapability]] = {}
        
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        key = f"{agent.session_id}_{agent.agent_type.value}"
        self.agents[key] = agent
        
    def get_agent(self, session_id: str, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent instance."""
        key = f"{session_id}_{agent_type.value}"
        return self.agents.get(key)
        
    def register_capability(self, agent_type: AgentType, capability: AgentCapability) -> None:
        """Register a capability for an agent type."""
        if agent_type not in self.capabilities:
            self.capabilities[agent_type] = []
        self.capabilities[agent_type].append(capability)
        
    def get_capabilities(self, agent_type: AgentType) -> List[AgentCapability]:
        """Get capabilities for an agent type."""
        return self.capabilities.get(agent_type, [])
        
    async def shutdown_session(self, session_id: str) -> None:
        """Shutdown all agents for a session."""
        to_remove = []
        for key, agent in self.agents.items():
            if agent.session_id == session_id:
                await agent.shutdown()
                to_remove.append(key)
                
        for key in to_remove:
            del self.agents[key]


# Global agent registry instance
agent_registry = AgentRegistry()