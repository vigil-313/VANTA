"""
Async Helpers
Utility functions for asyncio operations
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar, Optional, Set

logger = logging.getLogger(__name__)

T = TypeVar('T')


def run_in_executor(func: Callable) -> Callable:
    """
    Decorator to run a synchronous function in an executor.
    Useful for CPU-bound or blocking IO operations.
    
    Args:
        func: Synchronous function to run in executor
        
    Returns:
        Asynchronous wrapper function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            functools.partial(func, *args, **kwargs)
        )
    return wrapper


async def cancel_tasks(tasks: Set[asyncio.Task]) -> None:
    """
    Cancel a set of tasks and wait for them to complete
    
    Args:
        tasks: Set of tasks to cancel
    """
    if not tasks:
        return
        
    for task in tasks:
        task.cancel()
        
    await asyncio.gather(*tasks, return_exceptions=True)


async def wait_for_with_timeout(
    coro: Coroutine, 
    timeout: float, 
    default: Optional[T] = None
) -> Optional[T]:
    """
    Wait for a coroutine with timeout, returning a default value if it times out
    
    Args:
        coro: Coroutine to wait for
        timeout: Timeout in seconds
        default: Default value to return on timeout
        
    Returns:
        Coroutine result or default value
    """
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        logger.debug(f"Operation timed out after {timeout}s")
        return default


class TaskGroup:
    """
    Simple task group for managing a set of related tasks
    """
    
    def __init__(self, name: str = "TaskGroup"):
        """
        Initialize a task group
        
        Args:
            name: Name for this group (for logging)
        """
        self.name = name
        self.tasks: Set[asyncio.Task] = set()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    def create_task(self, coro: Coroutine) -> asyncio.Task:
        """
        Create and register a new task in this group
        
        Args:
            coro: Coroutine to run as a task
            
        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task
    
    def _on_task_done(self, task: asyncio.Task) -> None:
        """Handle task completion"""
        self.tasks.discard(task)
        if task.cancelled():
            return
            
        if exc := task.exception():
            self.logger.error(f"Task raised exception: {exc}")
    
    async def cancel_all(self) -> None:
        """Cancel all tasks in this group"""
        self.logger.debug(f"Cancelling {len(self.tasks)} tasks")
        await cancel_tasks(self.tasks)
        self.tasks.clear()
    
    def __len__(self) -> int:
        """Get number of active tasks"""
        return len(self.tasks)