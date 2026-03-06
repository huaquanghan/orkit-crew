"""Memory layer exceptions."""


class MemoryError(Exception):
    """Base exception for memory layer errors."""

    def __init__(self, message: str = "Memory operation failed", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {type(self.cause).__name__}: {self.cause})"
        return self.message


class RedisConnectionError(MemoryError):
    """Raised when Redis connection fails."""

    def __init__(self, message: str = "Redis connection failed", *, host: str | None = None, port: int | None = None, cause: Exception | None = None) -> None:
        details = []
        if host:
            details.append(f"host={host}")
        if port:
            details.append(f"port={port}")
        if details:
            message = f"{message} ({', '.join(details)})"
        super().__init__(message, cause=cause)
        self.host = host
        self.port = port


class QdrantConnectionError(MemoryError):
    """Raised when Qdrant connection fails."""

    def __init__(self, message: str = "Qdrant connection failed", *, url: str | None = None, cause: Exception | None = None) -> None:
        if url:
            message = f"{message} (url={url})"
        super().__init__(message, cause=cause)
        self.url = url


class StorageError(MemoryError):
    """Raised when storage operation fails."""

    def __init__(self, message: str = "Storage operation failed", *, operation: str | None = None, key: str | None = None, cause: Exception | None = None) -> None:
        details = []
        if operation:
            details.append(f"op={operation}")
        if key:
            details.append(f"key={key}")
        if details:
            message = f"{message} ({', '.join(details)})"
        super().__init__(message, cause=cause)
        self.operation = operation
        self.key = key


class TaskNotFoundError(MemoryError):
    """Raised when a task is not found."""

    def __init__(self, task_id: str, *, cause: Exception | None = None) -> None:
        message = f"Task not found: {task_id}"
        super().__init__(message, cause=cause)
        self.task_id = task_id
