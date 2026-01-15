"""Chat Orchestrator Agent - manages conversational flow and coordinates other agents."""

import asyncio
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any
from enum import Enum
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging for this module
logger = logging.getLogger(__name__)

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType, agent_registry
from agents.intake_agent import PortfolioIntakeAgent
from agents.research_agent import ResearchAgent
from agents.extraction_agent import ExtractionAgent
from agents.deep_research_agent import DeepResearchAgent
from agents.classification_agent import ClassificationAgent
from models.unified_models import (
    ProcessingSession, ChatResponse, PortfolioItem, DocumentSource, 
    ExtractionResult, PortfolioAnalysis, CategorizationSession,
    FundCategorization, CategoryQuestion, CategoryResponse
)
# Temporarily disable tracing imports


class ConversationStage(str, Enum):
    """Stages of the conversation flow."""
    GREETING = "greeting"
    FILE_UPLOADED = "file_uploaded"
    PORTFOLIO_PROCESSED = "portfolio_processed"
    
    # New categorization workflow stages
    CATEGORIZATION_STARTED = "categorization_started"
    DEEP_RESEARCH_STARTED = "deep_research_started"
    DEEP_RESEARCH_COMPLETED = "deep_research_completed"
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_COMPLETED = "classification_completed"
    USER_REVIEW_NEEDED = "user_review_needed"
    CATEGORIZATION_REVIEW = "categorization_review"
    CATEGORIZATION_COMPLETE = "categorization_complete"
    
    # Legacy stages (for backward compatibility)
    RESEARCH_STARTED = "research_started"
    RESEARCH_COMPLETED = "research_completed"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    ANALYSIS_READY = "analysis_ready"
    RECOMMENDATIONS = "recommendations"
    COMPLETE = "complete"


class ChatOrchestrator(BaseAgent):
    """Main orchestrator that manages conversation flow and coordinates other agents."""
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.CHAT_ORCHESTRATOR, session_id)
        self.conversation_stage = ConversationStage.GREETING
        self.processing_session: Optional[ProcessingSession] = None
        self.categorization_session: Optional[CategorizationSession] = None
        self.agent_instances: Dict[AgentType, BaseAgent] = {}
        
        # Workflow mode: "legacy" or "categorization"
        self.workflow_mode = "categorization"  # Default to new workflow
        
        logger.info(f"🎭 ChatOrchestrator created for session: {session_id}")
        
    async def _setup(self) -> None:
        """Initialize the chat orchestrator and sub-agents."""
        logger.info(f"🎭 Setting up ChatOrchestrator for session: {self.session_id}")
        
        # Create processing session with context file type
        file_type = self.context.file_type if self.context and self.context.file_type else "csv"
        self.processing_session = ProcessingSession(
            session_id=self.session_id,
            file_type=file_type,
            input_file_path=self.context.input_file_path if self.context else None
        )
        logger.info(f"🎭 Created processing session for {self.session_id}: file_type={file_type}")
        
        # Initialize sub-agents based on workflow mode
        logger.info(f"🎭 Initializing sub-agents for session: {self.session_id} (mode: {self.workflow_mode})")
        
        # Common agents
        self.agent_instances = {
            AgentType.INTAKE: PortfolioIntakeAgent(self.session_id)
        }
        
        # Add workflow-specific agents
        if self.workflow_mode == "categorization":
            # New categorization workflow agents
            self.agent_instances.update({
                "DEEP_RESEARCH": DeepResearchAgent(self.session_id),  # Custom type for now
                "CLASSIFICATION": ClassificationAgent(self.session_id)   # Custom type for now
            })
        else:
            # Legacy workflow agents
            self.agent_instances.update({
                AgentType.RESEARCH: ResearchAgent(self.session_id),
                AgentType.EXTRACTION: ExtractionAgent(self.session_id)
            })
        
        # Initialize all agents
        for agent_type, agent in self.agent_instances.items():
            logger.info(f"🎭 Initializing {agent_type} agent for session: {self.session_id}")
            await agent.initialize(self.context)
            agent_registry.register_agent(agent)
        
        self.set_confidence_score("orchestration", 0.95)
        logger.info(f"🎭 ChatOrchestrator setup complete for session: {self.session_id}")
        
    async def _cleanup(self) -> None:
        """Cleanup all sub-agents."""
        for agent in self.agent_instances.values():
            await agent.shutdown()
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Process messages and coordinate conversation flow."""
        logger.info(f"🎭 ChatOrchestrator.process() called for session {self.session_id} with message type: {message.type}")
        logger.info(f"🎭 Message data: {message.data}")
        
        # Handle different message types
        if message.type == MessageType.REQUEST_ACTION:
            logger.info(f"🎭 Handling REQUEST_ACTION for session {self.session_id}")
            async for response in self._handle_user_action(message):
                logger.info(f"🎭 Yielding response from _handle_user_action: {response.type}")
                yield response
                
        elif message.type == MessageType.DATA_PROCESSED:
            logger.info(f"🎭 Handling DATA_PROCESSED for session {self.session_id}")
            async for response in self._handle_agent_completion(message):
                yield response
                
        elif message.type == MessageType.STATUS_UPDATE:
            logger.info(f"🎭 Handling STATUS_UPDATE for session {self.session_id}")
            async for response in self._handle_status_update(message):
                yield response
                
        elif message.type == MessageType.ERROR:
            logger.info(f"🎭 Handling ERROR for session {self.session_id}")
            async for response in self._handle_error(message):
                yield response
        
        logger.info(f"🎭 ChatOrchestrator.process() completed for session {self.session_id}")
    
    async def _handle_user_action(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle user-initiated actions."""
        action = message.data.get("action")
        
        if action == "upload_file":
            async for response in self._handle_file_upload(message):
                yield response
                
        elif action == "start_research":
            async for response in self._start_research_phase():
                yield response
                
        elif action == "start_extraction":
            async for response in self._start_extraction_phase():
                yield response
        
        # New categorization workflow actions
        elif action == "start_categorization":
            async for response in self._start_categorization_workflow(message):
                yield response
        
        elif action == "start_processing":
            # Determine workflow and start appropriate process
            if self.workflow_mode == "categorization":
                async for response in self._start_categorization_workflow(message):
                    yield response
            else:
                async for response in self._start_research_phase():
                    yield response
        
        elif action == "answer_question":
            async for response in self._handle_categorization_answer(message):
                yield response
        
        elif action == "override_classification":
            async for response in self._handle_classification_override(message):
                yield response
        
        elif action == "approve_classifications":
            async for response in self._handle_classifications_approval(message):
                yield response
                
        elif action == "chat_message":
            async for response in self._handle_chat_message(message):
                yield response
    
    async def _handle_file_upload(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle file upload and initiate processing."""
        logger.info(f"🎭 _handle_file_upload called for session {self.session_id}")
        
        file_path = message.data.get("file_path")
        file_type = message.data.get("file_type", "csv")
        
        logger.info(f"🎭 File upload details - path: {file_path}, type: {file_type}")
        
        if not file_path:
            logger.error(f"🎭 No file path provided for session {self.session_id}")
            yield await self.emit_error("No file path provided")
            return
        
        # Update processing session
        if self.processing_session:
            logger.info(f"🎭 Updating processing session for {self.session_id}")
            self.processing_session.input_file_path = file_path
            self.processing_session.file_type = file_type
            self.processing_session.update_progress("file_uploaded", 0.1, "processing")
        else:
            logger.error(f"🎭 No processing session found for {self.session_id}")
        
        # Generate welcome message based on file type
        logger.info(f"🎭 Generating welcome message for file type: {file_type}")
        welcome_msg = await self._generate_welcome_message(file_type)
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": welcome_msg,
                "message_type": "info",
                "suggested_actions": [
                    {"action": "start_processing", "label": "Yes, process my portfolio"},
                    {"action": "analyze_file", "label": "Show me what you found first"}
                ]
            }
        )
        
        # Start intake processing
        logger.info(f"🎭 Starting intake processing for session {self.session_id}")
        intake_agent = self.agent_instances[AgentType.INTAKE]
        intake_message = self.create_message(
            message_type=MessageType.REQUEST_ACTION,
            recipient=AgentType.INTAKE,
            data={"file_path": file_path}
        )
        
        logger.info(f"🎭 Calling intake_agent.handle_message for session {self.session_id}")
        async for response in intake_agent.handle_message(intake_message):
            logger.info(f"🎭 Received response from intake agent: {response.type}")
            yield response
            
        logger.info(f"🎭 _handle_file_upload completed for session {self.session_id}")
    
    async def _handle_agent_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion messages from sub-agents."""
        sender = message.sender
        
        if sender == AgentType.INTAKE:
            async for response in self._handle_intake_completion(message):
                yield response
                
        elif sender == AgentType.RESEARCH:
            async for response in self._handle_research_completion(message):
                yield response
                
        elif sender == AgentType.EXTRACTION:
            async for response in self._handle_extraction_completion(message):
                yield response
    
    async def _handle_intake_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion of portfolio intake."""
        if "portfolio_items" in message.data:
            portfolio_data = message.data["portfolio_items"]
            confidence = message.data.get("confidence_score", 0.0)
            
            # Update processing session
            if self.processing_session:
                self.processing_session.portfolio_items = [PortfolioItem(**item) for item in portfolio_data]
                self.processing_session.update_progress("portfolio_parsed", 0.3, "processed")
            
            # Generate chat response
            chat_msg = await self._generate_portfolio_summary(portfolio_data, confidence)
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": chat_msg,
                    "message_type": "success",
                    "data": {
                        "portfolio_items": portfolio_data,
                        "total_funds": len(portfolio_data),
                        "confidence": confidence
                    },
                    "suggested_actions": [
                        {"action": "start_research", "label": "Find fund prospectuses"},
                        {"action": "modify_selection", "label": "Modify fund selection"}
                    ]
                }
            )
            
            # Auto-start research phase
            await asyncio.sleep(1)  # Brief pause for user to read
            async for response in self._start_research_phase():
                yield response
    
    async def _handle_research_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion of document research."""
        if "document_sources" in message.data:
            document_data = message.data["document_sources"]
            research_summary = message.data.get("research_summary", {})
            
            # Update processing session
            if self.processing_session:
                self.processing_session.update_progress("research_completed", 0.6, "processed")
            
            # Generate chat response
            chat_msg = await self._generate_research_summary(document_data, research_summary)
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": chat_msg,
                    "message_type": "success",
                    "data": {
                        "documents_found": len(document_data),
                        "research_summary": research_summary
                    },
                    "suggested_actions": [
                        {"action": "start_extraction", "label": "Extract fund data"},
                        {"action": "review_documents", "label": "Review found documents"}
                    ]
                }
            )
            
            # Auto-start extraction phase if documents found
            if document_data:
                await asyncio.sleep(1)
                async for response in self._start_extraction_phase():
                    yield response
    
    async def _handle_extraction_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion of data extraction."""
        if "extraction_results" in message.data:
            extraction_data = message.data["extraction_results"]
            extraction_summary = message.data.get("extraction_summary", {})
            
            # Update processing session
            if self.processing_session:
                # Store extraction results
                for result_data in extraction_data:
                    result = ExtractionResult(**result_data)
                    ticker = result.source.ticker
                    self.processing_session.add_fund_data(ticker, result.extracted_data)
                
                self.processing_session.update_progress("extraction_completed", 0.9, "completed")
            
            # Generate chat response
            chat_msg = await self._generate_extraction_summary(extraction_data, extraction_summary)
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": chat_msg,
                    "message_type": "success",
                    "data": {
                        "extraction_results": extraction_data,
                        "extraction_summary": extraction_summary
                    },
                    "suggested_actions": [
                        {"action": "view_results", "label": "View detailed results"},
                        {"action": "analyze_portfolio", "label": "Analyze portfolio"},
                        {"action": "export_data", "label": "Export data"}
                    ]
                }
            )
            
            # Generate final analysis
            async for response in self._generate_final_analysis():
                yield response
    
    async def _handle_status_update(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle status updates from sub-agents."""
        # Forward status updates to user
        yield self.create_message(
            message_type=MessageType.STATUS_UPDATE,
            recipient=None,
            data=message.data
        )
    
    async def _handle_error(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle errors from sub-agents."""
        error_msg = f"⚠️ {message.data.get('error', 'An error occurred')} in {message.sender} agent."
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": error_msg,
                "message_type": "error",
                "data": message.data
            }
        )
    
    async def _handle_chat_message(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle direct chat messages from user."""
        user_message = message.data.get("message", "")
        
        # Add to chat history
        if self.processing_session:
            self.processing_session.add_chat_message("user", user_message)
        
        # Generate contextual response based on current stage
        response_msg = await self._generate_contextual_response(user_message)
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": response_msg,
                "message_type": "info"
            }
        )
    
    async def _start_research_phase(self) -> AsyncGenerator[AgentMessage, None]:
        """Start the research phase."""
        if not self.processing_session or not self.processing_session.portfolio_items:
            yield await self.emit_error("No portfolio data available for research")
            return
        
        # Update stage
        self.conversation_stage = ConversationStage.RESEARCH_STARTED
        
        # Send message to research agent
        research_agent = self.agent_instances[AgentType.RESEARCH]
        research_message = self.create_message(
            message_type=MessageType.DATA_PROCESSED,
            recipient=AgentType.RESEARCH,
            data={
                "portfolio_items": [item.model_dump() for item in self.processing_session.portfolio_items]
            }
        )
        
        async for response in research_agent.handle_message(research_message):
            yield response
    
    async def _start_extraction_phase(self) -> AsyncGenerator[AgentMessage, None]:
        """Start the extraction phase."""
        # Get the most recent research results
        # This would normally be stored in session state
        yield self.create_message(
            message_type=MessageType.STATUS_UPDATE,
            recipient=None,
            data={
                "message": "🔧 Starting fund data extraction...",
                "stage": "extraction_starting"
            }
        )
    
    async def _generate_welcome_message(self, file_type: str) -> str:
        """Generate welcome message based on file type."""
        if file_type == "csv":
            return ("👋 Welcome! I can see you've uploaded a portfolio CSV file. "
                   "I'll analyze your portfolio, find the latest fund prospectuses, "
                   "and extract detailed fund information for you. Ready to get started?")
        elif file_type == "pdf":
            return ("📄 Great! You've uploaded a PDF document. "
                   "I'll extract fund information and provide detailed analysis. "
                   "Shall I begin processing?")
        else:
            return ("👋 Hello! I'm your AI fund onboarding assistant. "
                   "I can help you analyze portfolios and extract fund data. "
                   "What would you like to do today?")
    
    async def _generate_portfolio_summary(self, portfolio_items: List[Dict], confidence: float) -> str:
        """Generate summary of portfolio processing."""
        total_funds = len(portfolio_items)
        
        # Analyze portfolio composition
        asset_classes = set()
        tickers = []
        for item in portfolio_items:
            if item.get("asset_class"):
                asset_classes.add(item["asset_class"])
            if item.get("ticker"):
                tickers.append(item["ticker"])
        
        summary_parts = [
            f"✅ **Portfolio Analysis Complete!** Found {total_funds} funds with {confidence*100:.0f}% confidence."
        ]
        
        if asset_classes:
            summary_parts.append(f"📊 **Asset Classes:** {', '.join(asset_classes)}")
        
        if tickers:
            summary_parts.append(f"🎯 **Funds:** {', '.join(tickers[:5])}")
            if len(tickers) > 5:
                summary_parts.append(f" and {len(tickers)-5} more")
        
        summary_parts.append("🔍 **Next Step:** I'll now search for the latest fund prospectuses and extract detailed information.")
        
        return " ".join(summary_parts)
    
    async def _generate_research_summary(self, documents: List[Dict], research_summary: Dict) -> str:
        """Generate summary of research results."""
        docs_found = len(documents)
        total_researched = research_summary.get("total_researched", 0)
        success_rate = research_summary.get("success_rate", 0) * 100
        
        summary_parts = [
            f"🔍 **Research Complete!** Found prospectuses for {docs_found} out of {total_researched} funds ({success_rate:.0f}% success rate)."
        ]
        
        if docs_found > 0:
            tickers = [doc.get("ticker", "Unknown") for doc in documents[:5]]
            summary_parts.append(f"📋 **Documents Found:** {', '.join(tickers)}")
            if len(documents) > 5:
                summary_parts.append(f" and {len(documents)-5} more")
        
        summary_parts.append("⚡ **Next:** Extracting detailed fund data using AI...")
        
        return " ".join(summary_parts)
    
    async def _generate_extraction_summary(self, results: List[Dict], extraction_summary: Dict) -> str:
        """Generate summary of extraction results."""
        successful = extraction_summary.get("successful_extractions", 0)
        total = extraction_summary.get("total_processed", 0)
        success_rate = extraction_summary.get("success_rate", 0) * 100
        
        summary_parts = [
            f"🎉 **Extraction Complete!** Successfully extracted data from {successful} out of {total} documents ({success_rate:.0f}% success rate)."
        ]
        
        if successful > 0:
            # Show sample of extracted funds
            fund_names = []
            for result in results[:3]:
                extracted_data = result.get("extracted_data", {})
                name = extracted_data.get("fund_name", "Unknown Fund")
                confidence = int(result.get("confidence_score", 0) * 100)
                fund_names.append(f"{name} ({confidence}%)")
            
            if fund_names:
                summary_parts.append(f"📊 **Sample Results:** {', '.join(fund_names)}")
        
        summary_parts.append("🎯 **Ready for Analysis!** View detailed results and insights below.")
        
        return " ".join(summary_parts)
    
    async def _generate_final_analysis(self) -> AsyncGenerator[AgentMessage, None]:
        """Generate final portfolio analysis and recommendations."""
        if not self.processing_session:
            return
        
        # Calculate portfolio metrics
        portfolio_analysis = self._calculate_portfolio_analysis()
        
        # Generate insights
        insights = await self._generate_insights(portfolio_analysis)
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": insights,
                "message_type": "success",
                "data": {
                    "portfolio_analysis": portfolio_analysis.model_dump() if portfolio_analysis else None,
                    "stage": "analysis_complete"
                }
            }
        )
    
    def _calculate_portfolio_analysis(self) -> Optional[PortfolioAnalysis]:
        """Calculate portfolio analysis metrics."""
        if not self.processing_session or not self.processing_session.fund_extractions:
            return None
        
        funds = list(self.processing_session.fund_extractions.values())
        
        # Calculate basic metrics
        total_funds = len(funds)
        expense_ratios = [f.expense_ratio for f in funds if f.expense_ratio is not None]
        avg_expense_ratio = sum(expense_ratios) / len(expense_ratios) if expense_ratios else None
        
        # Calculate confidence metrics
        confidences = [f.confidence_score for f in funds if hasattr(f, 'confidence_score')]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return PortfolioAnalysis(
            total_funds=total_funds,
            total_allocation=100.0,  # Placeholder
            average_expense_ratio=avg_expense_ratio,
            overall_confidence=overall_confidence,
            data_completeness=overall_confidence  # Simplified
        )
    
    async def _generate_insights(self, analysis: Optional[PortfolioAnalysis]) -> str:
        """Generate portfolio insights and recommendations."""
        if not analysis:
            return "📊 Analysis complete! Your fund data has been successfully extracted and is ready for review."
        
        insights = [
            f"📈 **Portfolio Overview:** {analysis.total_funds} funds analyzed with {analysis.overall_confidence*100:.0f}% confidence."
        ]
        
        if analysis.average_expense_ratio:
            insights.append(f"💰 **Average Expense Ratio:** {analysis.average_expense_ratio:.2f}%")
            
            if analysis.average_expense_ratio < 0.5:
                insights.append("✨ Great news! Your portfolio has low-cost funds.")
            elif analysis.average_expense_ratio > 1.0:
                insights.append("⚠️ Consider reviewing expense ratios - some funds may be costly.")
        
        insights.append("📋 **Next Steps:** Explore the detailed results, compare fund performance, or export your data!")
        
        return " ".join(insights)
    
    async def _generate_contextual_response(self, user_message: str) -> str:
        """Generate contextual response based on conversation stage."""
        user_msg_lower = user_message.lower()
        
        # Simple keyword-based responses (could be enhanced with LLM)
        if any(word in user_msg_lower for word in ["help", "what", "how"]):
            return ("I can help you analyze portfolios and extract fund data! "
                   "Upload a CSV portfolio file and I'll find the fund prospectuses, "
                   "extract detailed information, and provide insights.")
        
        elif any(word in user_msg_lower for word in ["thanks", "thank you"]):
            return "You're welcome! Let me know if you need anything else. 😊"
        
        elif "status" in user_msg_lower:
            stage_messages = {
                ConversationStage.GREETING: "Ready to process your portfolio!",
                ConversationStage.PORTFOLIO_PROCESSED: "Portfolio analyzed, searching for documents...",
                ConversationStage.RESEARCH_COMPLETED: "Documents found, extracting data...",
                ConversationStage.EXTRACTION_COMPLETED: "Data extraction complete!"
            }
            return stage_messages.get(self.conversation_stage, "Processing your request...")
        
        else:
            return ("I understand you're asking about your portfolio analysis. "
                   "Is there something specific you'd like to know about the fund data or process?")
    
    # ========== NEW CATEGORIZATION WORKFLOW METHODS ==========
    
    async def _start_categorization_workflow(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Start the new categorization workflow."""
        logger.info(f"🎭 Starting categorization workflow for session {self.session_id}")
        
        # Ensure we have portfolio data
        if not self.processing_session or not self.processing_session.portfolio_items:
            yield await self.emit_error("No portfolio data available to categorize")
            return
        
        # Initialize categorization session
        self.categorization_session = CategorizationSession(
            session_id=self.session_id,
            portfolio_items=self.processing_session.portfolio_items,
            total_funds=len(self.processing_session.portfolio_items),
            current_stage="researching"
        )
        
        # Update conversation stage
        self.conversation_stage = ConversationStage.CATEGORIZATION_STARTED
        
        # Send initial message
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": f"🎯 Great! I'll analyze and categorize your {len(self.processing_session.portfolio_items)} fund holdings. Let me start by researching each fund in depth to understand their characteristics.",
                "message_type": "info"
            }
        )
        
        # Start deep research phase
        async for response in self._start_deep_research_phase():
            yield response
    
    async def _start_deep_research_phase(self) -> AsyncGenerator[AgentMessage, None]:
        """Start deep research phase of categorization workflow."""
        logger.info(f"🎭 Starting deep research phase for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.DEEP_RESEARCH_STARTED
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": "🔍 Starting comprehensive research on your funds...",
                "message_type": "info"
            }
        )
        
        # Send portfolio data to deep research agent
        deep_research_agent = self.agent_instances["DEEP_RESEARCH"]
        research_message = self.create_message(
            message_type=MessageType.DATA_PROCESSED,
            recipient="DEEP_RESEARCH",
            data={
                "portfolio_items": [item.model_dump() for item in self.processing_session.portfolio_items]
            }
        )
        
        # Process with deep research agent
        async for response in deep_research_agent.handle_message(research_message):
            # Forward status updates to user
            if response.type == MessageType.STATUS_UPDATE:
                yield response
            elif response.type == MessageType.DATA_PROCESSED:
                # Research completed, start classification
                async for classification_response in self._handle_research_completion(response):
                    yield classification_response
    
    async def _handle_research_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion of deep research phase."""
        logger.info(f"🎭 Research completed for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.DEEP_RESEARCH_COMPLETED
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": "✅ Research completed! Now I'll classify your funds into asset categories...",
                "message_type": "success"
            }
        )
        
        # Start classification phase
        async for response in self._start_classification_phase(message):
            yield response
    
    async def _start_classification_phase(self, research_message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Start classification phase of categorization workflow."""
        logger.info(f"🎭 Starting classification phase for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.CLASSIFICATION_STARTED
        
        # Send research data to classification agent
        classification_agent = self.agent_instances["CLASSIFICATION"]
        
        # Process with classification agent
        async for response in classification_agent.handle_message(research_message):
            # Forward status updates to user
            if response.type == MessageType.STATUS_UPDATE:
                yield response
            elif response.type == MessageType.DATA_PROCESSED:
                # Classification completed
                async for completion_response in self._handle_classification_completion(response):
                    yield completion_response
    
    async def _handle_classification_completion(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle completion of classification phase."""
        logger.info(f"🎭 Classification completed for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.CLASSIFICATION_COMPLETED
        
        categorization_data = message.data.get("categorization_data", {})
        summary = categorization_data.get("summary", {})
        
        # Update categorization session with results
        if self.categorization_session:
            classifications = categorization_data.get("classifications", [])
            for classification_dict in classifications:
                fund_categorization = FundCategorization(**classification_dict)
                self.categorization_session.add_fund_categorization(fund_categorization)
        
        # Determine next action based on confidence levels
        needs_review = summary.get("requires_user_input", 0)
        avg_confidence = summary.get("average_confidence", 0.0)
        
        if needs_review > 0 or avg_confidence < 0.8:
            # Need user review
            self.conversation_stage = ConversationStage.USER_REVIEW_NEEDED
            
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": f"📊 I've analyzed your funds! I found {needs_review} funds that need your input for accurate categorization. Let me show you the results and ask for your guidance where needed.",
                    "message_type": "info"
                }
            )
            
            # Start user review process
            async for response in self._start_user_review_process(categorization_data):
                yield response
        else:
            # All classifications are high confidence
            self.conversation_stage = ConversationStage.CATEGORIZATION_COMPLETE
            
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": f"🎉 Excellent! I've successfully categorized all {summary['total_funds']} funds with high confidence. Here are your results:",
                    "message_type": "success"
                }
            )
            
            # Send final results
            yield self._create_categorization_results_message(categorization_data)
    
    async def _start_user_review_process(self, categorization_data: Dict[str, Any]) -> AsyncGenerator[AgentMessage, None]:
        """Start interactive user review process."""
        logger.info(f"🎭 Starting user review process for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.CATEGORIZATION_REVIEW
        
        interaction_needed = categorization_data.get("interaction_needed", [])
        
        if not interaction_needed:
            # No specific interactions needed, show summary
            yield self._create_categorization_results_message(categorization_data)
            return
        
        # Update categorization session
        if self.categorization_session:
            self.categorization_session.funds_needing_input = [item["ticker"] for item in interaction_needed]
            self.categorization_session.current_fund_index = 0
        
        # Start with first fund needing review
        first_fund = interaction_needed[0]
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": f"Let's start with **{first_fund['ticker']}** ({first_fund['fund_name']}). I need your help with the following:",
                "message_type": "info"
            }
        )
        
        # Create and send first question
        async for response in self._send_next_categorization_question():
            yield response
    
    async def _send_next_categorization_question(self) -> AsyncGenerator[AgentMessage, None]:
        """Send the next categorization question to the user."""
        
        if not self.categorization_session:
            yield await self.emit_error("No categorization session available")
            return
        
        current_ticker = self.categorization_session.get_next_fund_needing_input()
        
        if not current_ticker:
            # No more funds need input, complete the process
            yield self.create_message(
                message_type=MessageType.CHAT_RESPONSE,
                recipient=None,
                data={
                    "message": "🎉 That's all the input I needed! Your portfolio categorization is now complete.",
                    "message_type": "success"
                }
            )
            
            # Send final results
            categorization_data = {
                "classifications": [c.to_dict() for c in self.categorization_session.fund_categorizations.values()],
                "summary": self.categorization_session.get_summary()
            }
            yield self._create_categorization_results_message(categorization_data)
            return
        
        # Get fund categorization
        fund_categorization = self.categorization_session.get_fund_categorization(current_ticker)
        
        if not fund_categorization:
            yield await self.emit_error(f"No categorization found for {current_ticker}")
            return
        
        # Generate questions for this fund
        from agents.classification_agent import ClassificationResult
        
        # Create temporary classification result for question generation
        temp_classification = ClassificationResult(
            ticker=fund_categorization.ticker,
            fund_name=fund_categorization.fund_name,
            asset_class=fund_categorization.asset_class,
            asset_class_confidence=fund_categorization.asset_class_confidence,
            equity_region=fund_categorization.equity_region,
            equity_style=fund_categorization.equity_style,
            equity_size=fund_categorization.equity_size,
            fixed_income_type=fund_categorization.fixed_income_type,
            fixed_income_duration=fund_categorization.fixed_income_duration,
            research_sources=fund_categorization.research_sources,
            key_data_points={},
            classification_method=fund_categorization.classification_method,
            reasoning=fund_categorization.reasoning,
            alternative_classifications=fund_categorization.alternative_classifications
        )
        
        # Generate questions (simplified for now)
        classification_agent = self.agent_instances["CLASSIFICATION"]
        questions = classification_agent._generate_questions(temp_classification)
        
        if not questions:
            # No questions needed, move to next fund
            self.categorization_session.mark_current_fund_complete()
            async for response in self._send_next_categorization_question():
                yield response
            return
        
        # Send first question
        question = questions[0]
        
        question_obj = CategoryQuestion(
            question_id=f"{current_ticker}_{question['type']}",
            ticker=current_ticker,
            fund_name=fund_categorization.fund_name,
            question_type=question["type"],
            question_text=question["question"],
            options=question["options"],
            current_classification=fund_categorization.to_dict(),
            confidence_score=fund_categorization.asset_class_confidence,
            reasoning=fund_categorization.reasoning
        )
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data=question_obj.to_chat_message()
        )
    
    async def _handle_categorization_answer(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle user's answer to categorization question."""
        logger.info(f"🎭 Handling categorization answer for session {self.session_id}")
        
        question_id = message.data.get("question_id")
        selected_value = message.data.get("selected_value")
        custom_value = message.data.get("custom_value")
        ticker = message.data.get("ticker")
        
        if not all([question_id, selected_value, ticker]):
            yield await self.emit_error("Missing required answer data")
            return
        
        # Create response object
        response_obj = CategoryResponse(
            question_id=question_id,
            ticker=ticker,
            selected_value=selected_value,
            custom_value=custom_value,
            response_time=1.0  # Placeholder
        )
        
        # Update fund categorization based on answer
        if self.categorization_session:
            fund_categorization = self.categorization_session.get_fund_categorization(ticker)
            if fund_categorization:
                # Apply the answer to the categorization
                final_value = response_obj.get_final_value()
                question_type = question_id.split("_", 1)[-1]
                
                if question_type == "asset_class":
                    fund_categorization.asset_class = final_value
                    fund_categorization.manual_override = True
                    fund_categorization.override_reason = "User provided answer"
                elif question_type == "equity_region":
                    fund_categorization.equity_region = final_value
                elif question_type == "equity_style":
                    fund_categorization.equity_style = final_value
                elif question_type == "equity_size":
                    fund_categorization.equity_size = final_value
                elif question_type == "fixed_income_type":
                    fund_categorization.fixed_income_type = final_value
                elif question_type == "fixed_income_duration":
                    fund_categorization.fixed_income_duration = final_value
                
                # Update in session
                self.categorization_session.add_fund_categorization(fund_categorization)
        
        # Acknowledge the answer
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": f"✅ Thank you! I've updated {ticker} with your selection.",
                "message_type": "success"
            }
        )
        
        # Move to next question or next fund
        async for response in self._send_next_categorization_question():
            yield response
    
    async def _handle_classification_override(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle user override of fund classification."""
        logger.info(f"🎭 Handling classification override for session {self.session_id}")
        
        ticker = message.data.get("ticker")
        new_asset_class = message.data.get("asset_class")
        reason = message.data.get("reason", "User override")
        
        if not all([ticker, new_asset_class]):
            yield await self.emit_error("Missing required override data")
            return
        
        # Update fund categorization
        if self.categorization_session:
            fund_categorization = self.categorization_session.get_fund_categorization(ticker)
            if fund_categorization:
                fund_categorization.apply_override(
                    new_asset_class=new_asset_class,
                    reason=reason,
                    override_by="user",
                    **message.data.get("sub_categories", {})
                )
                self.categorization_session.add_fund_categorization(fund_categorization)
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": f"✅ Updated {ticker} classification to {new_asset_class}",
                "message_type": "success"
            }
        )
    
    async def _handle_classifications_approval(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Handle user approval of all classifications."""
        logger.info(f"🎭 Handling classifications approval for session {self.session_id}")
        
        self.conversation_stage = ConversationStage.CATEGORIZATION_COMPLETE
        
        yield self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "message": "🎉 Perfect! Your portfolio categorization is now complete. Here's your final summary:",
                "message_type": "success"
            }
        )
        
        # Send final results
        if self.categorization_session:
            categorization_data = {
                "classifications": [c.to_dict() for c in self.categorization_session.fund_categorizations.values()],
                "summary": self.categorization_session.get_summary()
            }
            yield self._create_categorization_results_message(categorization_data)
    
    def _create_categorization_results_message(self, categorization_data: Dict[str, Any]) -> AgentMessage:
        """Create final categorization results message."""
        
        return self.create_message(
            message_type=MessageType.CHAT_RESPONSE,
            recipient=None,
            data={
                "type": "categorization_complete",
                "message": "📊 Categorization Results",
                "message_type": "success",
                "categorization_data": categorization_data,
                "suggested_actions": [
                    {"action": "export_results", "label": "Export to CSV"},
                    {"action": "view_analysis", "label": "View Portfolio Analysis"},
                    {"action": "start_new", "label": "Process Another Portfolio"}
                ]
            }
        )