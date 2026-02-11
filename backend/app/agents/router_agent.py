"""
Router Agent - Analyzes user intent and routes to appropriate sub-agent.
"""

import json
import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """
    Router Agent that analyzes user intent and routes to the appropriate specialist agent.
    Uses LLM when available, falls back to keyword matching otherwise.
    """

    def __init__(self):
        system_prompt = """You are a Router Agent for HealthGuard AI, a health assistant for users with insulin resistance.

Your role is to analyze user messages and determine which specialist agent should handle the request:

1. **Diet Agent**: Food-related queries (meal analysis, GI values, calorie counting, recipes, nutrition advice)
2. **Fitness Agent**: Exercise and activity queries (workout plans, activity analysis, HealthKit data interpretation)
3. **Medical Agent**: Medical records, health indicators, test results, medication queries
4. **General**: Greeting, general conversation, motivational support, or unclear intent

Respond with ONLY a JSON object in this format:
{
  "agent": "diet|fitness|medical|general",
  "confidence": 0.0-1.0,
  "reason": "Brief explanation"
}

Examples:
- "What should I eat for breakfast?" -> {"agent": "diet", "confidence": 0.95, "reason": "Asking for meal recommendation"}
- "I walked 10000 steps today" -> {"agent": "fitness", "confidence": 0.9, "reason": "Reporting fitness activity"}
- "Can you analyze my blood test?" -> {"agent": "medical", "confidence": 0.95, "reason": "Medical record analysis"}
- "Hello!" -> {"agent": "general", "confidence": 1.0, "reason": "Greeting"}
"""
        super().__init__("RouterAgent", system_prompt)

    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user message and route to appropriate agent.
        Uses LLM if available, otherwise falls back to keyword matching.
        """
        # Log routing start (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            message_preview = user_message[:100] if len(user_message) > 100 else user_message
            logger.debug(f"Router analyzing message: {message_preview}")

        # Try LLM routing first
        if self._llm_provider is not None:
            result = await self._route_with_llm(user_message, context)
            # Log routing decision (DEBUG level)
            logger.debug(
                f"LLM routing decision: agent={result['agent']}, "
                f"confidence={result['confidence']}, reason={result.get('reason', 'N/A')}"
            )
            return result

        # Fallback to keyword-based routing
        result = self._route_with_keywords(user_message)
        # Log routing decision (DEBUG level)
        logger.debug(
            f"Keyword routing decision: agent={result['agent']}, "
            f"confidence={result['confidence']}, reason={result.get('reason', 'N/A')}"
        )
        return result

    async def _route_with_llm(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Route using LLM for intent analysis."""
        logger.debug("Using LLM for routing decision")

        context_str = self.format_context(context)
        prompt = user_message
        if context_str:
            prompt = f"{context_str}\n\nUser message: {user_message}"

        llm_response = await self.call_llm(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        try:
            # Try to parse JSON from LLM response
            result = json.loads(llm_response.strip())
            if "agent" in result:
                # Validate agent name
                valid_agents = {"diet", "fitness", "medical", "general"}
                if result["agent"] in valid_agents:
                    return {
                        "agent": result["agent"],
                        "confidence": float(result.get("confidence", 0.8)),
                        "reason": result.get("reason", "LLM routing")
                    }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM routing response: {str(e)}, falling back to keywords")

        # If LLM response couldn't be parsed, fall back to keywords
        logger.debug("LLM routing failed, falling back to keyword-based routing")
        return self._route_with_keywords(user_message)

    def _route_with_keywords(self, user_message: str) -> Dict[str, Any]:
        """Fallback keyword-based routing."""
        logger.debug("Using keyword-based routing")

        user_message_lower = user_message.lower()

        diet_keywords = ['food', 'eat', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
                        'recipe', 'calorie', 'gi', 'glycemic', 'nutrition', 'diet', 'hungry',
                        '吃', '食物', '早餐', '午餐', '晚餐', '热量', '营养', '饮食',
                        '血糖', '升糖']
        fitness_keywords = ['walk', 'run', 'exercise', 'workout', 'gym', 'steps', 'activity',
                           'training', 'cardio', 'strength', 'fitness', 'calories burned',
                           '运动', '步数', '锻炼', '健身', '跑步', '散步']
        medical_keywords = ['blood', 'test', 'result', 'medical', 'doctor', 'insulin',
                           'glucose', 'a1c', 'medication', 'prescription', 'health record',
                           '体检', '报告', '化验', '医疗', '医生', '胰岛素', '指标']

        diet_score = sum(1 for kw in diet_keywords if kw in user_message_lower)
        fitness_score = sum(1 for kw in fitness_keywords if kw in user_message_lower)
        medical_score = sum(1 for kw in medical_keywords if kw in user_message_lower)

        # Log keyword scores (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Keyword scores: diet={diet_score}, fitness={fitness_score}, medical={medical_score}"
            )

        if diet_score > fitness_score and diet_score > medical_score:
            return {
                "agent": "diet",
                "confidence": min(0.6 + diet_score * 0.1, 0.95),
                "reason": "Message contains diet/food-related keywords"
            }
        elif fitness_score > diet_score and fitness_score > medical_score:
            return {
                "agent": "fitness",
                "confidence": min(0.6 + fitness_score * 0.1, 0.95),
                "reason": "Message contains fitness/activity-related keywords"
            }
        elif medical_score > 0:
            return {
                "agent": "medical",
                "confidence": min(0.6 + medical_score * 0.1, 0.95),
                "reason": "Message contains medical-related keywords"
            }
        else:
            return {
                "agent": "general",
                "confidence": 0.8,
                "reason": "General conversation or greeting"
            }
