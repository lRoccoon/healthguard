"""
Medical Agent - Handles medical records analysis and health trend tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent


class MedicalAgent(BaseAgent):
    """
    Medical Agent specialized in medical record analysis and health indicator tracking.
    """

    def __init__(self):
        system_prompt = """You are a Medical Agent for HealthGuard AI, specializing in insulin resistance (IR) health monitoring.

Your expertise includes:
- OCR and extraction of medical test results
- Analyzing key IR indicators (fasting insulin, HOMA-IR, A1C, glucose, lipids)
- Tracking health trends over time
- Providing context and explanations (NOT medical advice)

Key IR indicators:
1. **Fasting Insulin**: Normal <25 mIU/L, IR >25
2. **HOMA-IR**: Normal <2, IR >2.5
3. **HbA1c**: Normal <5.7%, Prediabetes 5.7-6.4%, Diabetes ≥6.5%
4. **Fasting Glucose**: Normal <100 mg/dL, Prediabetes 100-125, Diabetes ≥126
5. **Triglycerides**: Normal <150 mg/dL
6. **HDL**: Should be >40 mg/dL (men), >50 mg/dL (women)

When analyzing records:
- Extract all numerical values with units
- Compare to normal ranges
- Identify trends (improving/stable/worsening)
- Note any concerning values
- Suggest monitoring frequency
- Recommend discussing with healthcare provider

IMPORTANT: Always include disclaimer that this is informational only, not medical advice.
"""
        super().__init__("MedicalAgent", system_prompt)

    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process medical-related request.
        
        Args:
            user_message: User's message about medical data
            context: Context including previous records
            
        Returns:
            Analysis and insights
        """
        # Analyze medical data
        analysis = await self._analyze_medical_data(user_message, context)
        
        # Generate insights
        insights = await self._generate_insights(analysis, context)
        
        # Format response
        response = self._format_response(analysis, insights)
        
        return {
            "agent": "medical",
            "response": response,
            "analysis": analysis,
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }

    async def _analyze_medical_data(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze medical data from message or uploaded files."""
        # Placeholder implementation
        # In Phase 3, this will use OCR (pytesseract, pdf2image) for document processing
        
        return {
            "extracted_data": {
                "空腹胰岛素": "待提取",
                "HOMA-IR": "待计算",
                "糖化血红蛋白 (A1C)": "待提取",
                "空腹血糖": "待提取"
            },
            "data_source": "用户上传的医疗记录",
            "extraction_confidence": 0.0
        }

    async def _generate_insights(
        self,
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> list:
        """Generate health insights from medical data."""
        return [
            "定期监测空腹胰岛素和 HOMA-IR 指标",
            "注意空腹血糖的变化趋势",
            "保持健康的生活方式有助于改善指标",
            "建议与医生讨论任何异常结果"
        ]

    def _format_response(
        self,
        analysis: Dict[str, Any],
        insights: list
    ) -> str:
        """Format response for user."""
        response = f"""## 医疗记录分析

**数据来源**: {analysis['data_source']}

### 提取的指标
"""
        for key, value in analysis["extracted_data"].items():
            response += f"- **{key}**: {value}\n"
        
        response += "\n### 健康洞察\n\n"
        for i, insight in enumerate(insights, 1):
            response += f"{i}. {insight}\n"
        
        response += """
---

⚠️ **重要提示**: 此分析仅供参考，不构成医疗建议。请务必与您的医疗保健提供者讨论您的检查结果和治疗方案。

_注意：Phase 3 将实现 OCR 功能，自动提取医疗报告中的数据。_
"""
        return response
