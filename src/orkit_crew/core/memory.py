"""Memory management with Redis (short-term) and Qdrant (long-term)."""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from dataclasses import dataclass

import redis
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from orkit_crew.core.config import get_settings


@dataclass
class MemoryEntry:
    """A single memory entry."""
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None


class RedisMemory:
    """Short-term memory using Redis."""
    
    def __init__(self, redis_url: Optional[str] = None):
        settings = get_settings()
        self.client = redis.from_url(redis_url or settings.redis_url, decode_responses=True)
        self.default_ttl = 3600  # 1 hour
    
    def store(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value in Redis."""
        serialized = json.dumps(value) if not isinstance(value, str) else value
        self.client.setex(key, ttl or self.default_ttl, serialized)
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis."""
        value = self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    def store_session(self, session_id: str, data: Dict[str, Any], ttl: int = 7200) -> None:
        """Store session data."""
        key = f"session:{session_id}"
        self.store(key, data, ttl)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.retrieve(f"session:{session_id}")
    
    def append_to_history(self, session_id: str, entry: Dict[str, Any], max_items: int = 50) -> None:
        """Append entry to conversation history."""
        key = f"history:{session_id}"
        self.client.lpush(key, json.dumps(entry))
        self.client.ltrim(key, 0, max_items - 1)
        self.client.expire(key, self.default_ttl * 2)
    
    def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history."""
        key = f"history:{session_id}"
        items = self.client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in reversed(items)]


class QdrantMemory:
    """Long-term memory using Qdrant vector database."""
    
    COLLECTION_NAME = "orkit_memories"
    VECTOR_SIZE = 1536  # OpenAI embedding size
    
    def __init__(self, qdrant_url: Optional[str] = None):
        settings = get_settings()
        self.client = QdrantClient(
            url=qdrant_url or settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Ensure the memories collection exists."""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
        except Exception:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=self.VECTOR_SIZE, distance=Distance.COSINE),
            )
    
    def store(
        self,
        content: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """Store a memory with its vector embedding."""
        if memory_id is None:
            memory_id = hashlib.md5(content.encode()).hexdigest()
        
        point = PointStruct(
            id=memory_id,
            vector=vector,
            payload={
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[point],
        )
        return memory_id
    
    def search(
        self,
        vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar memories."""
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        
        return [
            {
                "id": r.id,
                "content": r.payload.get("content", ""),
                "metadata": r.payload.get("metadata", {}),
                "score": r.score,
            }
            for r in results
        ]


class MarkdownMemory:
    """Working memory stored as markdown files."""
    
    def __init__(self, working_dir: str = ".orkit"):
        import os
        self.working_dir = working_dir
        os.makedirs(working_dir, exist_ok=True)
    
    def save(self, filename: str, content: str) -> None:
        """Save content to a markdown file."""
        import os
        filepath = os.path.join(self.working_dir, f"{filename}.md")
        with open(filepath, "w") as f:
            f.write(content)
    
    def load(self, filename: str) -> Optional[str]:
        """Load content from a markdown file."""
        import os
        filepath = os.path.join(self.working_dir, f"{filename}.md")
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return None
    
    def append(self, filename: str, content: str) -> None:
        """Append content to a markdown file."""
        import os
        filepath = os.path.join(self.working_dir, f"{filename}.md")
        with open(filepath, "a") as f:
            f.write(f"\n\n{content}")


class MemoryManager:
    """Unified memory manager combining Redis, Qdrant, and Markdown."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        working_dir: str = ".orkit",
    ):
        self.redis = RedisMemory(redis_url)
        self.qdrant = QdrantMemory(qdrant_url)
        self.markdown = MarkdownMemory(working_dir)
    
    # Session management (Redis)
    def store_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Store session data."""
        self.redis.store_session(session_id, data)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.redis.get_session(session_id)
    
    def add_to_history(self, session_id: str, role: str, content: str) -> None:
        """Add a message to conversation history."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.redis.append_to_history(session_id, entry)
    
    def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.redis.get_history(session_id, limit)
    
    # Long-term memory (Qdrant)
    def store_memory(
        self,
        content: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a long-term memory."""
        return self.qdrant.store(content, vector, metadata)
    
    def search_memories(
        self,
        vector: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search long-term memories."""
        return self.qdrant.search(vector, limit)
    
    # Working memory (Markdown)
    def save_working_memory(self, name: str, content: str) -> None:
        """Save working memory to markdown."""
        self.markdown.save(name, content)
    
    def load_working_memory(self, name: str) -> Optional[str]:
        """Load working memory from markdown."""
        return self.markdown.load(name)
    
    def append_working_memory(self, name: str, content: str) -> None:
        """Append to working memory."""
        self.markdown.append(name, content)
