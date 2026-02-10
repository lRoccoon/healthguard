"""
Diet Agent - Handles food analysis, GI values, and dietary recommendations.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent


class DietAgent(BaseAgent):
    """
    Diet Agent specialized in food analysis and dietary recommendations for insulin resistance.
    """

    def __init__(self):
        system_prompt = """You are a Diet Agent for HealthGuard AI, specializing in nutrition for insulin resistance (IR).

Your expertise includes:
- Analyzing meals for calorie content and macronutrients
- Evaluating Glycemic Index (GI) and Glycemic Load (GL) of foods
- Assessing meal appropriateness for insulin resistance management
- Providing low-GI food recommendations
- Creating balanced meal plans

Key principles for IR diet:
1. Prioritize LOW GI foods (GI < 55): vegetables, legumes, whole grains, lean proteins
2. AVOID HIGH GI foods (GI > 70): white bread, white rice, sugary drinks, processed snacks
3. Balanced macros: 40% carbs (complex), 30% protein, 30% healthy fats
4. Emphasize fiber-rich foods (slows glucose absorption)
5. Portion control is essential
6. Frequent small meals > few large meals

When analyzing food:
- Estimate calories if not provided
- Categorize GI value (Low/Medium/High)
- Assess IR-friendliness (Excellent/Good/Fair/Poor/Avoid)
- Provide specific, actionable recommendations
- Be encouraging but honest

Always end with practical next steps and encouragement.
"""
        super().__init__("DietAgent", system_prompt)

    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process food-related request.
        
        Args:
            user_message: User's message about food
            context: Context including user history
            
        Returns:
            Analysis and recommendations
        """
        # Extract food information from message
        analysis = await self._analyze_food(user_message, context)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(analysis, context)
        
        # Format response
        response = self._format_response(analysis, recommendations)
        
        return {
            "agent": "diet",
            "response": response,
            "analysis": analysis,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }

    async def _analyze_food(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze food mentioned in message."""
        # Placeholder implementation
        # In Phase 3, this will use LLM + image recognition for food photos
        
        return {
            "food_name": "用户提到的食物",
            "estimated_calories": "待分析",
            "gi_category": "待评估",
            "ir_assessment": "需要更多信息",
            "confidence": 0.5
        }

    async def _generate_recommendations(
        self,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> list:
        """Generate dietary recommendations."""
        # Placeholder recommendations
        return [
            "选择低GI食物，如全谷物、蔬菜和瘦肉蛋白",
            "避免精制碳水化合物和含糖饮料",
            "注意份量控制，少食多餐",
            "增加膳食纤维摄入，有助于稳定血糖"
        ]

    def _format_response(
        self,
        analysis: Dict[str, Any],
        recommendations: list
    ) -> str:
        """Format response for user."""
        response = f"""## 饮食分析

**食物**: {analysis['food_name']}
**估计热量**: {analysis['estimated_calories']}
**GI类别**: {analysis['gi_category']}
**IR适合度**: {analysis['ir_assessment']}

## 建议

"""
        for i, rec in enumerate(recommendations, 1):
            response += f"{i}. {rec}\n"
        
        response += "\n💪 记住：每一个健康的选择都在帮助你控制胰岛素抵抗！继续保持！\n"
        response += "\n_注意：Phase 3 将集成真实的食物数据库和图像识别功能。_"
        
        return response
