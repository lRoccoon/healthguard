"""
Router Agent - Analyzes user intent and routes to appropriate sub-agent.
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class RouterAgent(BaseAgent):
    """
    Router Agent that analyzes user intent and routes to the appropriate specialist agent.
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
        
        Args:
            user_message: User's message
            context: Optional context
            
        Returns:
            Routing decision with target agent
        """
        # For now, use simple keyword matching (will be replaced with LLM in Phase 3)
        user_message_lower = user_message.lower()
        
        # Diet-related keywords
        diet_keywords = ['food', 'eat', 'meal', 'breakfast', 'lunch', 'dinner', 'snack', 
                        'recipe', 'calorie', 'gi', 'glycemic', 'nutrition', 'diet', 'hungry']
        
        # Fitness-related keywords
        fitness_keywords = ['walk', 'run', 'exercise', 'workout', 'gym', 'steps', 'activity',
                           'training', 'cardio', 'strength', 'fitness', 'calories burned']
        
        # Medical-related keywords
        medical_keywords = ['blood', 'test', 'result', 'medical', 'doctor', 'insulin', 
                           'glucose', 'a1c', 'medication', 'prescription', 'health record']
        
        # Check for matches
        diet_score = sum(1 for kw in diet_keywords if kw in user_message_lower)
        fitness_score = sum(1 for kw in fitness_keywords if kw in user_message_lower)
        medical_score = sum(1 for kw in medical_keywords if kw in user_message_lower)
        
        # Determine routing
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
