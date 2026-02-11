"""
Agent Orchestrator - Coordinates between Router Agent and Specialist Agents.
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from .router_agent import RouterAgent
from .diet_agent import DietAgent
from .fitness_agent import FitnessAgent
from .medical_agent import MedicalAgent
from ..core import MemoryManager
from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the multi-agent system.
    Routes user requests to appropriate specialist agents.
    Injects LLM provider into all agents when available.
    """

    def __init__(self, memory_manager: MemoryManager,
                 llm_provider: Optional[LLMProvider] = None,
                 api_mode: str = "chat"):
        """
        Initialize orchestrator with agent instances.
        
        Args:
            memory_manager: MemoryManager instance for user context
            llm_provider: Optional LLM provider for all agents
            api_mode: "chat" or "responses" API mode
        """
        self.memory_manager = memory_manager
        self.router = RouterAgent()
        self.diet_agent = DietAgent()
        self.fitness_agent = FitnessAgent()
        self.medical_agent = MedicalAgent()

        # Inject LLM provider into all agents
        if llm_provider:
            for agent in [self.router, self.diet_agent,
                          self.fitness_agent, self.medical_agent]:
                agent.set_llm_provider(llm_provider, api_mode)

    async def process_message(
        self,
        user_message: str,
        user_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user message through the agent system.

        Args:
            user_message: User's message
            user_id: User identifier
            additional_context: Optional additional context (e.g., health data, images)

        Returns:
            Response from appropriate agent
        """
        # Log message processing start (INFO level)
        logger.info(
            f"Processing message from user {user_id}: {user_message[:100]}"
        )

        try:
            # Get user context from memory
            user_context = await self.memory_manager.get_user_context(days_back=7)

            # Combine with additional context
            context = {
                "user_history": user_context,
                **(additional_context or {})
            }

            # Route to appropriate agent
            routing = await self.router.process_request(user_message, context)

            agent_type = routing["agent"]

            # Log routing decision (INFO level)
            logger.info(
                f"Delegating to {agent_type} agent (confidence={routing.get('confidence', 'N/A')})"
            )

            # Get response from specialist agent
            if agent_type == "diet":
                response = await self.diet_agent.process_request(user_message, context)
            elif agent_type == "fitness":
                response = await self.fitness_agent.process_request(user_message, context)
            elif agent_type == "medical":
                response = await self.medical_agent.process_request(user_message, context)
            else:  # general
                response = await self._handle_general(user_message, context)

            # Add routing info to response
            response["routing"] = routing

            # Log completion (INFO level)
            logger.info(
                f"Message processing completed: agent={agent_type}, "
                f"response_length={len(str(response.get('response', '')))} chars"
            )

            return response
        except Exception as e:
            logger.error(
                f"Message processing failed for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {"user_id": user_id, "error": str(e)}}
            )
            raise

    async def process_message_stream(
        self,
        user_message: str,
        user_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message through the agent system with streaming output.

        Args:
            user_message: User's message
            user_id: User identifier
            additional_context: Optional additional context (e.g., health data, images)

        Yields:
            Dict[str, Any]: Events with types: routing, content, done, or error
        """
        # Log stream processing start (INFO level)
        logger.info(
            f"Processing message stream from user {user_id}: {user_message[:100]}"
        )

        try:
            # Get user context from memory (blocking - must complete before streaming)
            user_context = await self.memory_manager.get_user_context(days_back=7)

            # Combine with additional context
            context = {
                "user_history": user_context,
                **(additional_context or {})
            }

            # Route to appropriate agent (blocking - must complete before streaming)
            routing = await self.router.process_request(user_message, context)
            agent_type = routing["agent"]

            # Log routing decision (INFO level)
            logger.info(
                f"Stream delegating to {agent_type} agent (confidence={routing.get('confidence', 'N/A')})"
            )

            # Yield routing event
            yield {
                "type": "routing",
                "agent": agent_type,
                "confidence": routing.get("confidence"),
                "reason": routing.get("reason", "")
            }

            # Stream response from specialist agent
            if agent_type == "diet":
                agent = self.diet_agent
            elif agent_type == "fitness":
                agent = self.fitness_agent
            elif agent_type == "medical":
                agent = self.medical_agent
            else:  # general
                # For general messages, yield the complete response as content
                try:
                    general_response = await self._handle_general(user_message, context)
                    yield {
                        "type": "content",
                        "content": general_response["response"]
                    }
                    yield {"type": "done"}
                    logger.info(f"Stream processing completed: agent=general")
                except Exception as gen_e:
                    logger.error(f"General response failed: {str(gen_e)}", exc_info=True)
                    yield {"type": "error", "error": str(gen_e)}
                return

            # Stream tokens from specialist agent
            accumulated_content = ""
            try:
                async for token in agent.process_request_stream(user_message, context):
                    accumulated_content += token
                    yield {
                        "type": "content",
                        "content": token
                    }
            except Exception as stream_e:
                logger.error(
                    f"Stream from {agent_type} agent failed: {str(stream_e)}",
                    exc_info=True
                )
                yield {"type": "error", "error": str(stream_e)}
                return

            # Yield done event
            yield {"type": "done"}

            # Log completion (INFO level)
            logger.info(
                f"Stream processing completed: agent={agent_type}, "
                f"content_length={len(accumulated_content)} chars"
            )

        except Exception as e:
            logger.error(
                f"Stream processing failed for user {user_id}: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {"user_id": user_id, "error": str(e)}}
            )
            # Yield error event
            yield {
                "type": "error",
                "error": str(e)
            }

    async def _handle_general(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general conversation."""
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ['hello', 'hi', '你好', '您好', 'hey']):
            response_text = """你好！👋 我是 HealthGuard AI，你的个人健康助理。

我可以帮助你：
- 🍽️ 分析食物和提供饮食建议（支持图片识别）
- 🏃 追踪运动数据和制定健康计划  
- 📋 解读医疗记录和监测健康指标（支持报告图片识别）

请告诉我你需要什么帮助！"""
        else:
            response_text = """我在这里帮助你管理胰岛素抵抗！

你可以：
- 告诉我你吃了什么，或发送食物照片，我来分析营养
- 分享你的运动数据，获取鼓励和建议
- 上传医疗记录图片，了解你的健康趋势

有什么我可以帮助你的吗？"""
        
        return {
            "agent": "general",
            "response": response_text,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
