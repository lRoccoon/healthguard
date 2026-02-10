"""
Medical Agent - Handles medical records analysis and health trend tracking.
Uses multimodal LLM for image understanding (replaces traditional OCR).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_agent import BaseAgent


class MedicalAgent(BaseAgent):
    """
    Medical Agent specialized in medical record analysis and health indicator tracking.
    Uses multimodal LLM to understand medical report images directly.
    """

    def __init__(self):
        system_prompt = """You are a Medical Agent for HealthGuard AI, specializing in insulin resistance (IR) health monitoring.

Your expertise includes:
- Reading and extracting data from medical test result images
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

When analyzing records (text or images):
- Extract all numerical values with units
- Compare to normal ranges
- Identify trends (improving/stable/worsening)
- Note any concerning values
- Suggest monitoring frequency
- Recommend discussing with healthcare provider

Always respond in the same language as the user's message.
IMPORTANT: Always include disclaimer that this is informational only, not medical advice.
"""
        super().__init__("MedicalAgent", system_prompt)

    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process medical-related request, optionally with images.
        Uses multimodal LLM for image understanding when images are provided.
        """
        image_base64_list = (context or {}).get("image_base64_list")

        if self._llm_provider is not None:
            return await self._process_with_llm(user_message, context, image_base64_list)

        # Fallback to placeholder
        analysis = await self._analyze_medical_data(user_message, context)
        insights = await self._generate_insights(analysis, context)
        response = self._format_response(analysis, insights)

        return {
            "agent": "medical",
            "response": response,
            "analysis": analysis,
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }

    async def _process_with_llm(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]],
        image_base64_list: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Process using multimodal LLM for medical image understanding."""
        context_str = self.format_context(context)
        prompt = user_message
        if context_str:
            prompt = f"{context_str}\n\n{user_message}"

        if image_base64_list:
            prompt += (
                "\n\n[User has attached medical report image(s). "
                "Please read and extract data from the image(s), analyze the results, "
                "and provide health insights.]"
            )

        llm_response = await self.call_llm(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for medical analysis accuracy
            image_base64_list=image_base64_list,
        )

        return {
            "agent": "medical",
            "response": llm_response,
            "has_image": bool(image_base64_list),
            "timestamp": datetime.now().isoformat()
        }

    async def _analyze_medical_data(
        self,
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze medical data from message (fallback without LLM)."""
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
        """Format response for user (fallback)."""
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

_提示：配置 LLM API 后可自动识别和分析医疗报告图片。_
"""
        return response
