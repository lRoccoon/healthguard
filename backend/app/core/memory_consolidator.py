"""
Memory Consolidation - Analyzes chat sessions and generates persistent memories.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import json
from ..storage import StorageInterface
from ..llm.factory import create_llm_provider


class MemoryConsolidator:
    """
    Analyzes chat conversations and generates structured memories.
    Creates both MEMORY.md (user-level persistent memories) and daily memory files.
    """

    def __init__(self, storage: StorageInterface, user_id: str, llm_provider=None):
        """
        Initialize memory consolidator.

        Args:
            storage: Storage implementation
            user_id: User identifier
            llm_provider: Optional LLM provider for AI-powered analysis
        """
        self.storage = storage
        self.user_id = user_id
        self.llm_provider = llm_provider
        self.base_path = f"users/{user_id}"

    def _get_memory_path(self) -> str:
        """Get path for main MEMORY.md file."""
        return f"{self.base_path}/MEMORY.md"

    def _get_daily_memory_path(self, target_date: date) -> str:
        """Get path for daily memory file."""
        return f"{self.base_path}/memory/{target_date.isoformat()}.md"

    async def analyze_session(self, session_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a chat session to extract insights and memories.

        Args:
            session_messages: List of messages in the session

        Returns:
            Dict with extracted insights (topics, key_points, action_items, health_data)
        """
        if not self.llm_provider:
            # Fallback: simple keyword-based analysis
            return self._simple_analysis(session_messages)

        # Build conversation text
        conversation_text = ""
        for msg in session_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n\n"

        # Use LLM to extract insights
        analysis_prompt = f"""Analyze this health conversation and extract key information:

{conversation_text}

Extract:
1. Main topics discussed (comma-separated)
2. Key health insights or findings
3. Action items or recommendations
4. Any health metrics mentioned (blood sugar, weight, exercise, etc.)

Format as JSON:
{{
  "topics": ["topic1", "topic2"],
  "key_insights": ["insight1", "insight2"],
  "action_items": ["action1", "action2"],
  "health_metrics": {{"metric": "value"}}
}}"""

        try:
            # Call LLM for analysis
            messages = [
                {"role": "system", "content": "You are a health data analyzer. Extract structured information from conversations."},
                {"role": "user", "content": analysis_prompt}
            ]

            response = await self.llm_provider.chat_completion(
                messages=messages,
                temperature=0.3
            )

            # Parse JSON response
            analysis = json.loads(response)
            return analysis
        except Exception as e:
            print(f"LLM analysis failed: {e}, falling back to simple analysis")
            return self._simple_analysis(session_messages)

    def _simple_analysis(self, session_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simple keyword-based analysis without LLM.

        Args:
            session_messages: List of messages

        Returns:
            Basic analysis dict
        """
        topics = set()
        health_keywords = ["diet", "food", "exercise", "blood sugar", "glucose", "insulin", "weight", "fitness"]

        for msg in session_messages:
            content = msg.get("content", "").lower()
            for keyword in health_keywords:
                if keyword in content:
                    topics.add(keyword)

        return {
            "topics": list(topics),
            "key_insights": ["Conversation analyzed"],
            "action_items": [],
            "health_metrics": {}
        }

    async def consolidate_daily_memory(self, target_date: date) -> bool:
        """
        Consolidate all sessions from a specific date into a daily memory file.

        Args:
            target_date: Date to consolidate

        Returns:
            bool: True if successful
        """
        # Get all sessions from this date
        chat_path = f"{self.base_path}/raw_chats"
        files = await self.storage.list(chat_path, pattern="*.json")

        daily_sessions = []
        for file_path in files:
            content = await self.storage.load(file_path)
            if content:
                messages = json.loads(content.decode('utf-8'))
                # Check if any message is from target date
                for msg in messages:
                    timestamp_str = msg.get("timestamp", "")
                    try:
                        msg_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).date()
                        if msg_date == target_date:
                            daily_sessions.append(messages)
                            break
                    except Exception:
                        pass

        if not daily_sessions:
            return False

        # Analyze each session
        all_insights = []
        for session in daily_sessions:
            analysis = await self.analyze_session(session)
            all_insights.append(analysis)

        # Generate daily memory markdown
        memory_content = f"# Daily Memory - {target_date.isoformat()}\n\n"
        memory_content += f"Generated: {datetime.now().isoformat()}\n\n"

        # Aggregate topics
        all_topics = set()
        for insight in all_insights:
            all_topics.update(insight.get("topics", []))

        if all_topics:
            memory_content += "## Topics Discussed\n"
            for topic in sorted(all_topics):
                memory_content += f"- {topic}\n"
            memory_content += "\n"

        # Aggregate insights
        memory_content += "## Key Insights\n"
        for i, insight in enumerate(all_insights, 1):
            if insight.get("key_insights"):
                memory_content += f"\n### Session {i}\n"
                for point in insight["key_insights"]:
                    memory_content += f"- {point}\n"
        memory_content += "\n"

        # Action items
        all_actions = []
        for insight in all_insights:
            all_actions.extend(insight.get("action_items", []))

        if all_actions:
            memory_content += "## Action Items\n"
            for action in all_actions:
                memory_content += f"- [ ] {action}\n"
            memory_content += "\n"

        # Health metrics
        memory_content += "## Health Metrics\n"
        for insight in all_insights:
            metrics = insight.get("health_metrics", {})
            for metric, value in metrics.items():
                memory_content += f"- **{metric}**: {value}\n"
        memory_content += "\n"

        # Save daily memory
        path = self._get_daily_memory_path(target_date)
        return await self.storage.save(path, memory_content)

    async def update_main_memory(self, new_insights: Dict[str, Any]) -> bool:
        """
        Update the main MEMORY.md file with new insights.

        Args:
            new_insights: New insights to add

        Returns:
            bool: True if successful
        """
        path = self._get_memory_path()

        # Load existing memory or create new
        existing_content = ""
        if await self.storage.exists(path):
            content_bytes = await self.storage.load(path)
            if content_bytes:
                existing_content = content_bytes.decode('utf-8')

        # If no existing memory, create header
        if not existing_content:
            existing_content = f"# Memory - User {self.user_id}\n\n"
            existing_content += f"Last updated: {datetime.now().isoformat()}\n\n"
            existing_content += "## Health Profile\n\n"
            existing_content += "## Important Insights\n\n"
            existing_content += "## Preferences\n\n"
            existing_content += "## Goals\n\n"

        # Append new insights
        new_section = f"\n## Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        if new_insights.get("topics"):
            new_section += "**Topics**: " + ", ".join(new_insights["topics"]) + "\n\n"

        if new_insights.get("key_insights"):
            new_section += "**Key Points**:\n"
            for insight in new_insights["key_insights"]:
                new_section += f"- {insight}\n"
            new_section += "\n"

        updated_content = existing_content + new_section

        # Save updated memory
        return await self.storage.save(path, updated_content)

    async def load_recent_memories(self, days: int = 7) -> str:
        """
        Load recent memory files for agent context.

        Args:
            days: Number of days to look back

        Returns:
            str: Concatenated memory content
        """
        memory_content = ""
        today = date.today()

        # Load main MEMORY.md
        main_path = self._get_memory_path()
        if await self.storage.exists(main_path):
            content_bytes = await self.storage.load(main_path)
            if content_bytes:
                memory_content += content_bytes.decode('utf-8') + "\n\n---\n\n"

        # Load recent daily memories
        for i in range(days):
            target_date = today - timedelta(days=i)
            daily_path = self._get_daily_memory_path(target_date)

            if await self.storage.exists(daily_path):
                content_bytes = await self.storage.load(daily_path)
                if content_bytes:
                    memory_content += content_bytes.decode('utf-8') + "\n\n---\n\n"

        return memory_content
