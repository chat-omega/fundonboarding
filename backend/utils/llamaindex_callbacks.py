"""LlamaIndex callbacks for LangSmith integration."""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# Check for LangSmith availability
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

# Check for LlamaIndex callbacks availability
try:
    from llama_index.core.callbacks import BaseCallbackHandler, CBEventType, EventPayload
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    BaseCallbackHandler = None
    CBEventType = None
    EventPayload = None

# Only define the callback handler if both are available
if LANGSMITH_AVAILABLE and LLAMAINDEX_AVAILABLE:
    class LangSmithCallbackHandler(BaseCallbackHandler):
        """LangSmith callback handler for LlamaIndex operations."""
        
        def __init__(self):
            self.enabled = False
            self.client = None
            
            if self._is_configured():
                try:
                    self.client = Client()
                    self.enabled = True
                    print("✅ LangSmith LlamaIndex callbacks enabled")
                except Exception as e:
                    print(f"⚠️ Failed to initialize LangSmith client for callbacks: {e}")
                    self.enabled = False
            
            super().__init__(
                event_starts_to_ignore=[],
                event_ends_to_ignore=[]
            )
        
        def _is_configured(self) -> bool:
            """Check if LangSmith is properly configured."""
            required_vars = [
                'LANGCHAIN_TRACING_V2',
                'LANGCHAIN_API_KEY',
                'LANGCHAIN_PROJECT'
            ]
            
            for var in required_vars:
                if not os.getenv(var):
                    return False
            
            return os.getenv('LANGCHAIN_TRACING_V2', '').lower() == 'true'
        
        def on_event_start(
            self,
            event_type: CBEventType,
            payload: Optional[Dict[str, Any]] = None,
            event_id: str = "",
            parent_id: str = "",
            **kwargs: Any,
        ) -> str:
            """Called when an event starts."""
            if not self.enabled:
                return event_id
            
            try:
                # Map LlamaIndex event types to LangSmith runs
                run_type = self._map_event_to_run_type(event_type)
                run_name = self._get_run_name(event_type, payload)
                
                inputs = {
                    "event_type": str(event_type),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                # Add payload data
                if payload:
                    # Filter out non-serializable data
                    filtered_payload = self._filter_payload(payload)
                    inputs.update(filtered_payload)
                
                # Create run
                run = self.client.create_run(
                    name=run_name,
                    run_type=run_type,
                    inputs=inputs,
                    project_name=os.getenv('LANGCHAIN_PROJECT', 'fund-onboarding-agents'),
                    parent_run_id=parent_id if parent_id else None,
                    run_id=event_id if event_id else None
                )
                
                return str(run.id)
                
            except Exception as e:
                print(f"Error in LangSmith callback start: {e}")
                return event_id
        
        def on_event_end(
            self,
            event_type: CBEventType,
            payload: Optional[Dict[str, Any]] = None,
            event_id: str = "",
            **kwargs: Any,
        ) -> None:
            """Called when an event ends."""
            if not self.enabled:
                return
            
            try:
                outputs = {}
                
                if payload:
                    filtered_payload = self._filter_payload(payload)
                    outputs.update(filtered_payload)
                
                # Update the run
                self.client.update_run(
                    run_id=event_id,
                    outputs=outputs,
                    end_time=datetime.utcnow()
                )
                
            except Exception as e:
                print(f"Error in LangSmith callback end: {e}")
        
        def start_trace(self, trace_id: Optional[str] = None) -> None:
            """Start a new trace."""
            pass
        
        def end_trace(
            self,
            trace_id: Optional[str] = None,
            trace_map: Optional[Dict[str, List[str]]] = None,
        ) -> None:
            """End a trace."""
            pass
        
        def _map_event_to_run_type(self, event_type: CBEventType) -> str:
            """Map LlamaIndex event types to LangSmith run types."""
            mapping = {
                CBEventType.CHUNKING: "tool",
                CBEventType.NODE_PARSING: "tool",
                CBEventType.EMBEDDING: "llm",
                CBEventType.LLM: "llm",
                CBEventType.QUERY: "chain",
                CBEventType.RETRIEVE: "retriever",
                CBEventType.SYNTHESIZE: "chain",
                CBEventType.TREE: "chain",
                CBEventType.SUB_QUESTION: "chain",
            }
            return mapping.get(event_type, "tool")
        
        def _get_run_name(self, event_type: CBEventType, payload: Optional[Dict[str, Any]]) -> str:
            """Generate a descriptive run name."""
            base_name = str(event_type).split('.')[-1].lower()
            
            if payload:
                # Try to add context from payload
                if 'query_str' in payload:
                    return f"{base_name}_query"
                elif 'prompt' in payload:
                    return f"{base_name}_prompt"
                elif 'chunks' in payload:
                    return f"{base_name}_chunks"
            
            return base_name
        
        def _filter_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Filter payload to remove non-serializable items."""
            filtered = {}
            
            for key, value in payload.items():
                try:
                    # Only include serializable types
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        # Limit string length for readability
                        if isinstance(value, str) and len(value) > 1000:
                            filtered[key] = value[:1000] + "..."
                        elif isinstance(value, list) and len(value) > 10:
                            filtered[key] = value[:10] + ["..."]
                        else:
                            filtered[key] = value
                    elif hasattr(value, '__dict__'):
                        # Try to serialize object dict
                        filtered[key] = str(type(value).__name__)
                    else:
                        filtered[key] = str(type(value).__name__)
                        
                except Exception:
                    # Skip problematic fields
                    continue
            
            return filtered

else:
    # Create dummy class if dependencies not available
    class LangSmithCallbackHandler:
        def __init__(self):
            self.enabled = False


def setup_llamaindex_callbacks():
    """Set up LlamaIndex callbacks for LangSmith tracing."""
    if not LANGSMITH_AVAILABLE or not LLAMAINDEX_AVAILABLE:
        print("⚠️ LangSmith or LlamaIndex callbacks not available - skipping setup")
        return None
    
    try:
        from llama_index.core import Settings
        from llama_index.core.callbacks import CallbackManager
        
        # Create callback handler
        langsmith_handler = LangSmithCallbackHandler()
        
        if langsmith_handler.enabled:
            # Set up callback manager
            callback_manager = CallbackManager([langsmith_handler])
            Settings.callback_manager = callback_manager
            print("✅ LlamaIndex callbacks configured for LangSmith")
        else:
            print("⚠️ LangSmith callbacks not enabled - configuration issue")
        
        return langsmith_handler
        
    except Exception as e:
        print(f"⚠️ Failed to setup LlamaIndex callbacks: {e}")
        return None