"""
Thread-safe in-memory task store for tracking background processing progress.
"""
import threading
from typing import Optional, Any
from models.schemas import TaskStatus


class TaskInfo:
    """Holds the state of a single background task."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: float = 0.0
        self.message: str = "Queued"
        self.result: Optional[Any] = None
        self.error: Optional[str] = None


class TaskStore:
    """
    Singleton in-memory store.
    Uses a lock so it's safe for use from BackgroundTasks/threadpool.
    """

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.Lock()

    def create_task(self, task_id: str) -> TaskInfo:
        with self._lock:
            task = TaskInfo(task_id)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_progress(
        self,
        task_id: str,
        progress: float,
        message: str = "",
        status: Optional[TaskStatus] = None,
    ):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.progress = min(progress, 100.0)
                if message:
                    task.message = message
                if status:
                    task.status = status
                elif task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.PROCESSING

    def set_result(self, task_id: str, result: Any):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.progress = 100.0
                task.message = "Done"
                task.result = result

    def set_failed(self, task_id: str, error: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.message = f"Error: {error}"
                task.error = error


# Global singleton
task_store = TaskStore()
