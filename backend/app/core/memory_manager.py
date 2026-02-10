"""
Memory Manager - Manages the Markdown-based memory system.
Handles daily logs, medical records, and conversation history.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pathlib import Path
from ..storage import StorageInterface


class MemoryManager:
    """
    Manages the structured memory system for users.
    Uses Markdown files for human-readable, searchable records.
    """

    def __init__(self, storage: StorageInterface, user_id: str):
        """
        Initialize memory manager for a specific user.
        
        Args:
            storage: Storage implementation to use
            user_id: User identifier
        """
        self.storage = storage
        self.user_id = user_id
        self.base_path = f"users/{user_id}"

    def _get_daily_log_path(self, target_date: date) -> str:
        """Get path for daily log file."""
        return f"{self.base_path}/memories/daily_logs/{target_date.isoformat()}.md"

    def _get_medical_record_path(self, filename: str) -> str:
        """Get path for medical record file."""
        return f"{self.base_path}/medical/records/{filename}"

    def _get_chat_log_path(self, session_id: str) -> str:
        """Get path for chat log file."""
        return f"{self.base_path}/raw_chats/{session_id}.json"

    async def create_daily_log(self, target_date: date, content: Dict[str, Any]) -> bool:
        """
        Create or update daily log for a specific date.
        
        Args:
            target_date: Date for the log
            content: Dictionary containing diet, fitness, and conversation data
            
        Returns:
            bool: True if successful
        """
        from ..templates import markdown_templates
        
        # Generate markdown content from template
        md_content = markdown_templates.daily_log_template(
            date=target_date,
            diet=content.get('diet', []),
            fitness=content.get('fitness', {}),
            conversations=content.get('conversations', []),
            summary=content.get('summary', '')
        )
        
        path = self._get_daily_log_path(target_date)
        return await self.storage.save(path, md_content)

    async def get_daily_log(self, target_date: date) -> Optional[str]:
        """
        Retrieve daily log for a specific date.
        
        Args:
            target_date: Date to retrieve
            
        Returns:
            Optional[str]: Markdown content or None if not found
        """
        path = self._get_daily_log_path(target_date)
        content = await self.storage.load(path)
        return content.decode('utf-8') if content else None

    async def append_to_daily_log(
        self,
        target_date: date,
        section: str,
        content: str
    ) -> bool:
        """
        Append content to a specific section of the daily log.
        
        Args:
            target_date: Date of the log
            section: Section name (e.g., "diet", "fitness", "conversations")
            content: Content to append
            
        Returns:
            bool: True if successful
        """
        path = self._get_daily_log_path(target_date)
        
        # Check if log exists, create if not
        if not await self.storage.exists(path):
            await self.create_daily_log(target_date, {})
        
        # Append content with proper formatting
        append_content = f"\n### {section} - {datetime.now().strftime('%H:%M:%S')}\n{content}\n"
        return await self.storage.append(path, append_content)

    async def save_medical_record(
        self,
        filename: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a medical record file (image or PDF).
        
        Args:
            filename: Name of the file
            content: File content as bytes
            metadata: Optional metadata (OCR results, extracted data, etc.)
            
        Returns:
            bool: True if successful
        """
        path = self._get_medical_record_path(filename)
        return await self.storage.save(path, content, metadata)

    async def save_medical_analysis(
        self,
        record_id: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Save analysis results for a medical record.
        
        Args:
            record_id: Identifier for the medical record
            analysis: Analysis results including extracted data and trends
            
        Returns:
            bool: True if successful
        """
        from ..templates import markdown_templates
        
        # Generate markdown summary
        md_content = markdown_templates.medical_record_template(
            record_id=record_id,
            analysis_date=datetime.now(),
            extracted_data=analysis.get('extracted_data', {}),
            trends=analysis.get('trends', []),
            recommendations=analysis.get('recommendations', [])
        )
        
        path = self._get_medical_record_path(f"{record_id}_summary.md")
        return await self.storage.save(path, md_content)

    async def save_chat_log(
        self,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Save raw chat conversation log.
        
        Args:
            session_id: Session identifier
            messages: List of message objects
            
        Returns:
            bool: True if successful
        """
        import json
        
        path = self._get_chat_log_path(session_id)
        content = json.dumps(messages, indent=2, ensure_ascii=False)
        return await self.storage.save(path, content)

    async def search_memories(
        self,
        query: str,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search through user's memories.
        
        Args:
            query: Search query
            days_back: Optional limit to search only recent days
            
        Returns:
            List of search results
        """
        search_path = f"{self.base_path}/memories/daily_logs"
        
        if days_back:
            # Filter by date range if specified
            # This is a simple implementation; could be optimized
            pass
        
        results = await self.storage.search(
            path=search_path,
            query=query,
            file_pattern="*.md"
        )
        
        return results

    async def get_recent_logs(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent daily logs.
        
        Args:
            days: Number of recent days to retrieve
            
        Returns:
            List of log metadata
        """
        logs = []
        today = date.today()
        
        for i in range(days):
            target_date = date.fromordinal(today.toordinal() - i)
            path = self._get_daily_log_path(target_date)
            
            if await self.storage.exists(path):
                metadata = await self.storage.get_metadata(path)
                content = await self.get_daily_log(target_date)
                logs.append({
                    'date': target_date.isoformat(),
                    'metadata': metadata,
                    'preview': content[:200] if content else None
                })
        
        return logs

    async def get_user_context(self, days_back: int = 7) -> str:
        """
        Get user context for AI agents by aggregating recent memories.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            str: Aggregated context as text
        """
        logs = await self.get_recent_logs(days_back)
        
        context = f"# User Context for {self.user_id}\n\n"
        context += f"## Recent Activity (Last {days_back} days)\n\n"
        
        for log in logs:
            context += f"### {log['date']}\n"
            if log['preview']:
                context += f"{log['preview']}...\n\n"
        
        return context

    async def list_medical_records(self) -> List[Dict[str, Any]]:
        """
        List all medical records for the user.
        
        Returns:
            List of medical record metadata
        """
        path = f"{self.base_path}/medical/records"
        files = await self.storage.list(path, recursive=False)
        
        records = []
        for file_path in files:
            if not file_path.endswith('_summary.md'):
                metadata = await self.storage.get_metadata(file_path)
                records.append(metadata)
        
        return records
