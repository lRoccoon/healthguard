"""
Unit tests for the agent system.
Tests BaseAgent, RouterAgent, DietAgent, FitnessAgent, MedicalAgent, and Orchestrator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.base_agent import BaseAgent
from app.agents.router_agent import RouterAgent
from app.agents.diet_agent import DietAgent
from app.agents.fitness_agent import FitnessAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.orchestrator import AgentOrchestrator
from app.llm.base import LLMProvider, LLMMessage, LLMResponse
from app.core import MemoryManager


class ConcreteAgent(BaseAgent):
    """Concrete agent for testing BaseAgent."""
    async def process_request(self, user_message, context=None):
        return {"agent": "test", "response": user_message}


class TestBaseAgent:
    """Tests for BaseAgent."""

    def test_init(self):
        agent = ConcreteAgent("TestAgent", "test prompt")
        assert agent.name == "TestAgent"
        assert agent.system_prompt == "test prompt"
        assert agent._llm_provider is None

    def test_set_llm_provider(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        mock_provider = MagicMock(spec=LLMProvider)
        agent.set_llm_provider(mock_provider, "chat")
        assert agent._llm_provider is mock_provider
        assert agent._api_mode == "chat"

    def test_format_context_empty(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        assert agent.format_context(None) == ""
        assert agent.format_context({}) == ""

    def test_format_context_with_data(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        context = {
            "user_history": "some history",
            "preferences": "low carb",
            "health_data": "steps: 10000"
        }
        result = agent.format_context(context)
        assert "some history" in result
        assert "low carb" in result
        assert "steps: 10000" in result

    @pytest.mark.asyncio
    async def test_call_llm_no_provider(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert "LLM not configured" in result

    @pytest.mark.asyncio
    async def test_call_llm_with_provider_chat_mode(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="LLM response", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert result == "LLM response"
        mock_provider.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_with_provider_responses_mode(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.responses = AsyncMock(
            return_value=LLMResponse(content="Responses API result", model="test")
        )
        agent.set_llm_provider(mock_provider, "responses")

        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert result == "Responses API result"
        mock_provider.responses.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_with_images(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Food analysis", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        images = [{"data": "base64data", "media_type": "image/jpeg"}]
        result = await agent.call_llm(
            [{"role": "user", "content": "What food is this?"}],
            image_base64_list=images
        )
        assert result == "Food analysis"
        # Verify the message passed to provider has multimodal content
        call_args = mock_provider.chat_completion.call_args
        messages = call_args[0][0]
        assert isinstance(messages[0].content, list)  # multimodal content

    @pytest.mark.asyncio
    async def test_call_llm_error_handling(self):
        agent = ConcreteAgent("TestAgent", "prompt")
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.side_effect = Exception("API error")
        agent.set_llm_provider(mock_provider, "chat")

        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert "LLM call failed" in result


class TestRouterAgent:
    """Tests for RouterAgent."""

    def test_init(self):
        router = RouterAgent()
        assert router.name == "RouterAgent"

    @pytest.mark.asyncio
    async def test_keyword_routing_diet(self):
        router = RouterAgent()
        result = await router.process_request("What should I eat for breakfast?")
        assert result["agent"] == "diet"

    @pytest.mark.asyncio
    async def test_keyword_routing_fitness(self):
        router = RouterAgent()
        result = await router.process_request("I walked 10000 steps today")
        assert result["agent"] == "fitness"

    @pytest.mark.asyncio
    async def test_keyword_routing_medical(self):
        router = RouterAgent()
        result = await router.process_request("My blood test results")
        assert result["agent"] == "medical"

    @pytest.mark.asyncio
    async def test_keyword_routing_general(self):
        router = RouterAgent()
        result = await router.process_request("Hello!")
        assert result["agent"] == "general"

    @pytest.mark.asyncio
    async def test_keyword_routing_chinese_diet(self):
        router = RouterAgent()
        result = await router.process_request("我早餐吃了什么?")
        assert result["agent"] == "diet"

    @pytest.mark.asyncio
    async def test_keyword_routing_chinese_fitness(self):
        router = RouterAgent()
        result = await router.process_request("今天运动了多少步数?")
        assert result["agent"] == "fitness"

    @pytest.mark.asyncio
    async def test_keyword_routing_chinese_medical(self):
        router = RouterAgent()
        result = await router.process_request("帮我看看体检报告")
        assert result["agent"] == "medical"

    @pytest.mark.asyncio
    async def test_llm_routing(self):
        router = RouterAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content='{"agent": "diet", "confidence": 0.9, "reason": "food question"}',
            model="test"
        )
        router.set_llm_provider(mock_provider, "chat")

        result = await router.process_request("What's a good meal?")
        assert result["agent"] == "diet"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_llm_routing_fallback_on_bad_json(self):
        router = RouterAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Invalid JSON response", model="test"
        )
        router.set_llm_provider(mock_provider, "chat")

        # Should fallback to keyword routing
        result = await router.process_request("Hello!")
        assert result["agent"] == "general"


class TestDietAgent:
    """Tests for DietAgent."""

    @pytest.mark.asyncio
    async def test_fallback_response(self):
        agent = DietAgent()
        result = await agent.process_request("I ate rice")
        assert result["agent"] == "diet"
        assert "饮食分析" in result["response"]

    @pytest.mark.asyncio
    async def test_llm_response(self):
        agent = DietAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Rice analysis: High GI, consider switching to brown rice.",
            model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        result = await agent.process_request("I ate rice")
        assert result["agent"] == "diet"
        assert "Rice analysis" in result["response"]

    @pytest.mark.asyncio
    async def test_image_analysis(self):
        agent = DietAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="I see a plate of sushi.", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        context = {
            "image_base64_list": [{"data": "img_data", "media_type": "image/jpeg"}]
        }
        result = await agent.process_request("What food is this?", context)
        assert result["agent"] == "diet"
        assert result.get("has_image") is True


class TestFitnessAgent:
    """Tests for FitnessAgent."""

    @pytest.mark.asyncio
    async def test_fallback_response(self):
        agent = FitnessAgent()
        result = await agent.process_request("I walked a lot today")
        assert result["agent"] == "fitness"
        assert "运动分析" in result["response"]

    @pytest.mark.asyncio
    async def test_with_health_data_context(self):
        agent = FitnessAgent()
        context = {
            "health_data": {
                "steps": 12000,
                "active_energy": 550,
                "exercise_minutes": 45
            }
        }
        result = await agent.process_request("How was my activity?", context)
        assert "优秀" in result["response"]  # 12000 steps = 优秀

    @pytest.mark.asyncio
    async def test_llm_response(self):
        agent = FitnessAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Great job on your 12000 steps!", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        result = await agent.process_request("I walked 12000 steps")
        assert "Great job" in result["response"]


class TestMedicalAgent:
    """Tests for MedicalAgent."""

    @pytest.mark.asyncio
    async def test_fallback_response(self):
        agent = MedicalAgent()
        result = await agent.process_request("My blood test results")
        assert result["agent"] == "medical"
        assert "医疗记录分析" in result["response"]
        assert "重要提示" in result["response"]

    @pytest.mark.asyncio
    async def test_llm_response(self):
        agent = MedicalAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Your HbA1c is 5.6%, which is normal.", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        result = await agent.process_request("Analyze my A1C result")
        assert "HbA1c" in result["response"]

    @pytest.mark.asyncio
    async def test_image_analysis(self):
        agent = MedicalAgent()
        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.chat_completion.return_value = LLMResponse(
            content="Medical report analysis from image.", model="test"
        )
        agent.set_llm_provider(mock_provider, "chat")

        context = {
            "image_base64_list": [{"data": "report_img", "media_type": "image/png"}]
        }
        result = await agent.process_request("请帮我分析这张报告", context)
        assert result["has_image"] is True


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.fixture
    def mock_memory_manager(self):
        mm = AsyncMock(spec=MemoryManager)
        mm.get_user_context.return_value = "Test user context"
        return mm

    @pytest.mark.asyncio
    async def test_process_message_general(self, mock_memory_manager):
        orchestrator = AgentOrchestrator(mock_memory_manager)
        result = await orchestrator.process_message("你好", "user123")
        assert result["agent"] == "general"
        assert "HealthGuard" in result["response"]

    @pytest.mark.asyncio
    async def test_process_message_diet(self, mock_memory_manager):
        orchestrator = AgentOrchestrator(mock_memory_manager)
        result = await orchestrator.process_message(
            "What should I eat for breakfast?", "user123"
        )
        assert result["routing"]["agent"] == "diet"

    @pytest.mark.asyncio
    async def test_process_message_with_llm(self, mock_memory_manager):
        mock_provider = AsyncMock(spec=LLMProvider)
        # Router response
        mock_provider.chat_completion.side_effect = [
            LLMResponse(
                content='{"agent": "diet", "confidence": 0.9, "reason": "food"}',
                model="test"
            ),
            LLMResponse(
                content="Healthy breakfast options include oatmeal.",
                model="test"
            ),
        ]

        orchestrator = AgentOrchestrator(
            mock_memory_manager, llm_provider=mock_provider
        )
        result = await orchestrator.process_message(
            "早餐吃什么好？", "user123"
        )
        assert result["routing"]["agent"] == "diet"

    @pytest.mark.asyncio
    async def test_process_message_with_images(self, mock_memory_manager):
        orchestrator = AgentOrchestrator(mock_memory_manager)
        context = {
            "image_base64_list": [{"data": "img", "media_type": "image/jpeg"}]
        }
        result = await orchestrator.process_message(
            "What food is this?", "user123", additional_context=context
        )
        # Should route to diet based on keywords
        assert result["routing"]["agent"] == "diet"
