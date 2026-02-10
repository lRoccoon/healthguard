"""
Fitness Agent - Handles activity analysis and exercise recommendations.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent


class FitnessAgent(BaseAgent):
    """
    Fitness Agent specialized in activity analysis and exercise planning for insulin resistance.
    """

    def __init__(self):
        system_prompt = """You are a Fitness Agent for HealthGuard AI, specializing in exercise for insulin resistance (IR).

Your expertise includes:
- Analyzing HealthKit data (steps, heart rate, active energy)
- Evaluating exercise intensity and duration
- Providing personalized workout recommendations
- Encouraging consistent physical activity

Key principles for IR exercise:
1. Aim for 150+ minutes/week of moderate activity
2. Combination of aerobic + resistance training is ideal
3. Post-meal walks are highly effective for glucose control
4. Consistency > intensity (regular moderate exercise > occasional intense)
5. Monitor heart rate: target 50-70% max HR for moderate activity
6. Avoid excessive cardio without resistance training

Activity targets:
- Steps: 8,000-10,000 per day
- Active energy: 400-600 kcal per day
- Exercise minutes: 30-60 per day

When analyzing activity:
- Celebrate progress, even small wins
- Provide specific, achievable next steps
- Consider user's fitness level and constraints
- Emphasize the metabolic benefits for IR

Always be encouraging and positive!
"""
        super().__init__("FitnessAgent", system_prompt)

    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process fitness-related request.
        
        Args:
            user_message: User's message about fitness
            context: Context including HealthKit data
            
        Returns:
            Analysis and recommendations
        """
        # Analyze activity data
        analysis = await self._analyze_activity(user_message, context)
        
        # Generate recommendations
        recommendations = await self._generate_exercise_plan(analysis, context)
        
        # Format response
        response = self._format_response(analysis, recommendations)
        
        return {
            "agent": "fitness",
            "response": response,
            "analysis": analysis,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }

    async def _analyze_activity(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze activity data from message or context."""
        # Extract health data if available
        health_data = context.get("health_data", {}) if context else {}
        
        steps = health_data.get("steps", 0)
        active_energy = health_data.get("active_energy", 0)
        exercise_minutes = health_data.get("exercise_minutes", 0)
        
        # Evaluate performance
        steps_status = "优秀" if steps >= 10000 else "良好" if steps >= 8000 else "需改进"
        energy_status = "优秀" if active_energy >= 500 else "良好" if active_energy >= 400 else "需改进"
        
        return {
            "steps": steps,
            "steps_status": steps_status,
            "active_energy": active_energy,
            "energy_status": energy_status,
            "exercise_minutes": exercise_minutes,
            "overall_assessment": "继续保持" if steps >= 8000 else "加油努力"
        }

    async def _generate_exercise_plan(
        self,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> list:
        """Generate exercise recommendations."""
        recommendations = []
        
        if analysis["steps"] < 8000:
            recommendations.append("尝试增加步数：饭后散步15-20分钟对降低血糖特别有效")
        
        if analysis["exercise_minutes"] < 30:
            recommendations.append("每天至少30分钟中等强度运动（快走、游泳、骑车）")
        
        recommendations.extend([
            "结合力量训练：每周2-3次，增强胰岛素敏感性",
            "保持规律：运动的一致性比强度更重要",
            "监控心率：保持在50-70%最大心率范围内"
        ])
        
        return recommendations

    def _format_response(
        self,
        analysis: Dict[str, Any],
        recommendations: list
    ) -> str:
        """Format response for user."""
        response = f"""## 运动分析

**步数**: {analysis['steps']} 步 ({analysis['steps_status']})
**活动能量**: {analysis['active_energy']} 千卡 ({analysis['energy_status']})
**运动时长**: {analysis['exercise_minutes']} 分钟

**总体评估**: {analysis['overall_assessment']}

## 运动建议

"""
        for i, rec in enumerate(recommendations, 1):
            response += f"{i}. {rec}\n"
        
        response += "\n🏃 运动是改善胰岛素抵抗的最佳天然药物！每一步都很重要！\n"
        response += "\n_注意：Phase 3 将添加基于 Apple Health 的实时数据分析。_"
        
        return response
