"""LangSmith tracing utilities for agent monitoring."""

import os
import time
import functools
from typing import Any, Dict, Optional, Callable, AsyncGenerator
from datetime import datetime
import json

try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("LangSmith not available - tracing disabled")


class LangSmithTracer:
    """LangSmith tracer for agent operations."""
    
    def __init__(self):
        self.enabled = False
        self.client = None
        
        if LANGSMITH_AVAILABLE and self._is_configured():
            try:
                self.client = Client()
                self.enabled = True
                print("✅ LangSmith tracing enabled")
            except Exception as e:
                print(f"⚠️ Failed to initialize LangSmith client: {e}")
                self.enabled = False
        else:
            print("⚠️ LangSmith not configured - tracing disabled")
    
    def _is_configured(self) -> bool:
        """Check if LangSmith is properly configured."""
        required_vars = [
            'LANGCHAIN_TRACING_V2',
            'LANGCHAIN_API_KEY',
            'LANGCHAIN_PROJECT'
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                print(f"Missing environment variable: {var}")
                return False
        
        return os.getenv('LANGCHAIN_TRACING_V2', '').lower() == 'true'
    
    def trace_agent_method(self, agent_type: str, method_name: str):
        """Decorator to trace agent methods."""
        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                run_name = f"{agent_type}.{method_name}"
                
                # Extract agent instance and session info
                agent_instance = args[0] if args else None
                session_id = getattr(agent_instance, 'session_id', 'unknown')
                
                inputs = {
                    "agent_type": agent_type,
                    "method": method_name,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    processing_time = time.time() - start_time
                    
                    # Log successful operation
                    self._log_operation(run_name, inputs, {
                        "status": "completed",
                        "processing_time_seconds": processing_time,
                        "result_type": type(result).__name__
                    }, start_time)
                    
                    return result
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    
                    # Log error
                    self._log_operation(run_name, inputs, {
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "processing_time_seconds": processing_time
                    }, start_time)
                    
                    raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                run_name = f"{agent_type}.{method_name}"
                
                agent_instance = args[0] if args else None
                session_id = getattr(agent_instance, 'session_id', 'unknown')
                
                inputs = {
                    "agent_type": agent_type,
                    "method": method_name,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    processing_time = time.time() - start_time
                    
                    # Log successful operation
                    self._log_operation(run_name, inputs, {
                        "status": "completed",
                        "processing_time_seconds": processing_time,
                        "result_type": type(result).__name__
                    }, start_time)
                    
                    return result
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    
                    # Log error
                    self._log_operation(run_name, inputs, {
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "processing_time_seconds": processing_time
                    }, start_time)
                    
                    raise
            
            # Return appropriate wrapper based on function type
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def _log_operation(self, run_name: str, inputs: Dict, outputs: Dict, start_time: float):
        """Log an operation to LangSmith."""
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name=run_name,
                run_type="chain",
                inputs=inputs,
                outputs=outputs,
                start_time=datetime.utcfromtimestamp(start_time),
                end_time=datetime.utcnow(),
                project_name=os.getenv('LANGCHAIN_PROJECT', 'fund-onboarding-agents')
            )
        except Exception as e:
            print(f"Failed to log to LangSmith: {e}")
    
    def log_agent_event(self, agent_type: str, event_type: str, data: Dict[str, Any]):
        """Log an agent event to LangSmith."""
        if not self.enabled:
            return
        
        try:
            event_name = f"{agent_type}.{event_type}"
            
            inputs = {
                "agent_type": agent_type,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                **data
            }
            
            self.client.create_run(
                name=event_name,
                run_type="tool",
                inputs=inputs,
                outputs={"status": "logged"},
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                project_name=os.getenv('LANGCHAIN_PROJECT', 'fund-onboarding-agents')
            )
                
        except Exception as e:
            print(f"Failed to log event to LangSmith: {e}")


# Global tracer instance
tracer = LangSmithTracer()


def trace_agent(agent_type: str):
    """Class decorator to trace all methods of an agent."""
    def class_decorator(cls):
        # Temporarily disable method-level tracing to debug issues
        # Only keep event logging
        return cls
    
    return class_decorator


def trace_method(method_name: str = None):
    """Method decorator for individual method tracing."""
    def decorator(func: Callable) -> Callable:
        if not tracer.enabled:
            return func
        
        name = method_name or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            agent_type = getattr(self, 'agent_type', type(self).__name__)
            return await tracer.trace_agent_method(agent_type, name)(func)(self, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            agent_type = getattr(self, 'agent_type', type(self).__name__)
            return tracer.trace_agent_method(agent_type, name)(func)(self, *args, **kwargs)
        
        # Return appropriate wrapper
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_event(event_type: str, **data):
    """Utility function to log events from within agent methods."""
    def get_agent_context():
        import inspect
        frame = inspect.currentframe()
        try:
            # Walk up the stack to find agent instance
            for _ in range(10):  # Limit depth
                frame = frame.f_back
                if not frame:
                    break
                
                local_self = frame.f_locals.get('self')
                if local_self and hasattr(local_self, 'agent_type'):
                    return str(local_self.agent_type)
                    
            return "unknown_agent"
        finally:
            del frame
    
    agent_type = get_agent_context()
    tracer.log_agent_event(agent_type, event_type, data)