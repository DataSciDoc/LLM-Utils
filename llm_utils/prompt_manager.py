# -*- coding: utf-8 -*-
"""
Prompt Queue Management for LLM Batch Processing

Manages prompt queues, tracks results, handles failures, and orchestrates retries.
Designed for processing large batches of prompts through LLM APIs.

Author: Richard Kerr
Created: 2024
"""

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PromptResult:
    """Container for a single prompt's result."""
    prompt: str
    result: Any
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    attempts: int = 1
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "prompt": self.prompt[:500] + "..." if len(self.prompt) > 500 else self.prompt,
            "result": self.result,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "attempts": self.attempts,
            "error": self.error,
            "metadata": self.metadata
        }


class PromptManager:
    """
    Manages prompt processing, result tracking, and retry logic.
    
    Features:
    - Queue management for batch processing
    - Automatic retry tracking for failed prompts
    - Result aggregation and persistence
    - Progress tracking and logging
    
    Example:
        >>> manager = PromptManager()
        >>> manager.add_prompts(["prompt1", "prompt2", "prompt3"])
        >>> 
        >>> for prompt in manager.pending_prompts():
        ...     try:
        ...         result = call_api(prompt)
        ...         manager.record_success(prompt, result)
        ...     except Exception as e:
        ...         manager.record_failure(prompt, str(e))
        >>> 
        >>> print(manager.summary())
        >>> manager.save_results("results.json")
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._pending: deque = deque()
        self._failed: deque = deque()
        self._results: List[PromptResult] = []
        self._attempt_counts: Dict[str, int] = {}
        self._start_time: Optional[datetime] = None
    
    def add_prompts(self, prompts: List[str], metadata: Optional[Dict] = None) -> None:
        """
        Add prompts to the processing queue.
        
        Args:
            prompts: List of prompt strings
            metadata: Optional metadata to attach to all prompts
        """
        for prompt in prompts:
            self._pending.append((prompt, metadata or {}))
            self._attempt_counts[prompt] = 0
        
        logger.info(f"Added {len(prompts)} prompts to queue. Total pending: {len(self._pending)}")
    
    def pending_prompts(self) -> List[Tuple[str, Dict]]:
        """
        Get iterator over pending prompts.
        
        Yields:
            Tuples of (prompt, metadata)
        """
        if self._start_time is None:
            self._start_time = datetime.now()
        
        return list(self._pending)
    
    def get_next_prompt(self) -> Optional[Tuple[str, Dict]]:
        """
        Get the next prompt from the queue.
        
        Returns:
            Tuple of (prompt, metadata) or None if queue is empty
        """
        if self._start_time is None:
            self._start_time = datetime.now()
        
        if self._pending:
            return self._pending.popleft()
        return None
    
    def record_success(self, prompt: str, result: Any, metadata: Optional[Dict] = None) -> None:
        """
        Record a successful prompt result.
        
        Args:
            prompt: The prompt that was processed
            result: The result from the API
            metadata: Optional additional metadata
        """
        # Remove from pending if still there
        self._remove_from_pending(prompt)
        
        attempts = self._attempt_counts.get(prompt, 1)
        
        self._results.append(PromptResult(
            prompt=prompt,
            result=result,
            success=True,
            attempts=attempts,
            metadata=metadata or {}
        ))
        
        logger.info(f"Success: {prompt[:50]}... (attempt {attempts})")
    
    def record_failure(self, prompt: str, error: str, metadata: Optional[Dict] = None) -> bool:
        """
        Record a failed prompt attempt.
        
        Args:
            prompt: The prompt that failed
            error: Error message
            metadata: Optional additional metadata
            
        Returns:
            True if prompt will be retried, False if max retries exceeded
        """
        # Remove from pending if still there
        self._remove_from_pending(prompt)
        
        self._attempt_counts[prompt] = self._attempt_counts.get(prompt, 0) + 1
        attempts = self._attempt_counts[prompt]
        
        if attempts < self.max_retries:
            # Add to failed queue for retry
            self._failed.append((prompt, metadata or {}))
            logger.warning(f"Failed (will retry): {prompt[:50]}... Error: {error} (attempt {attempts})")
            return True
        else:
            # Max retries exceeded, record as permanent failure
            self._results.append(PromptResult(
                prompt=prompt,
                result=None,
                success=False,
                attempts=attempts,
                error=error,
                metadata=metadata or {}
            ))
            logger.error(f"Failed (max retries): {prompt[:50]}... Error: {error}")
            return False
    
    def retry_failed(self) -> int:
        """
        Move failed prompts back to pending queue for retry.
        
        Returns:
            Number of prompts queued for retry
        """
        retry_count = len(self._failed)
        
        if retry_count > 0:
            logger.info(f"Retrying {retry_count} failed prompts...")
            while self._failed:
                self._pending.append(self._failed.popleft())
        
        return retry_count
    
    def _remove_from_pending(self, prompt: str) -> None:
        """Remove a prompt from the pending queue."""
        self._pending = deque(
            (p, m) for p, m in self._pending if p != prompt
        )
    
    @property
    def total_processed(self) -> int:
        """Total prompts that have been processed (success + failure)."""
        return len(self._results)
    
    @property
    def successful_count(self) -> int:
        """Number of successful results."""
        return sum(1 for r in self._results if r.success)
    
    @property
    def failed_count(self) -> int:
        """Number of permanently failed results."""
        return sum(1 for r in self._results if not r.success)
    
    @property
    def pending_count(self) -> int:
        """Number of prompts still pending."""
        return len(self._pending)
    
    @property
    def retry_count(self) -> int:
        """Number of prompts awaiting retry."""
        return len(self._failed)
    
    def progress(self) -> Tuple[int, int, float]:
        """
        Get processing progress.
        
        Returns:
            Tuple of (processed, total, percentage)
        """
        total = self.total_processed + self.pending_count + self.retry_count
        if total == 0:
            return 0, 0, 100.0
        
        processed = self.total_processed
        percentage = round(processed / total * 100, 1)
        
        return processed, total, percentage
    
    def summary(self) -> Dict:
        """
        Get processing summary.
        
        Returns:
            Dictionary with processing statistics
        """
        processed, total, percentage = self.progress()
        
        elapsed = None
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
        
        return {
            "total": total,
            "processed": processed,
            "successful": self.successful_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "awaiting_retry": self.retry_count,
            "progress_pct": percentage,
            "elapsed_seconds": elapsed
        }
    
    def get_results(self, successful_only: bool = False) -> List[PromptResult]:
        """
        Get all results.
        
        Args:
            successful_only: If True, only return successful results
            
        Returns:
            List of PromptResult objects
        """
        if successful_only:
            return [r for r in self._results if r.success]
        return self._results.copy()
    
    def get_successful_results(self) -> List[Any]:
        """Get just the result values from successful prompts."""
        return [r.result for r in self._results if r.success]
    
    def save_results(self, filepath: str, indent: int = 2) -> None:
        """
        Save all results to a JSON file.
        
        Args:
            filepath: Path to save results
            indent: JSON indentation (default: 2)
        """
        output = {
            "summary": self.summary(),
            "results": [r.to_dict() for r in self._results]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=indent, default=str)
        
        logger.info(f"Results saved to {filepath}")
    
    def clear(self) -> None:
        """Clear all state."""
        self._pending.clear()
        self._failed.clear()
        self._results.clear()
        self._attempt_counts.clear()
        self._start_time = None


def process_prompts_with_callback(
    prompts: List[str],
    api_callback: Callable[[str], Any],
    max_retries: int = 3,
    save_path: Optional[str] = None
) -> List[PromptResult]:
    """
    Convenience function to process prompts with a callback.
    
    Args:
        prompts: List of prompts to process
        api_callback: Function that takes a prompt and returns a result
        max_retries: Maximum retry attempts per prompt
        save_path: Optional path to save results
        
    Returns:
        List of PromptResult objects
    
    Example:
        >>> def call_api(prompt):
        ...     return anthropic.messages.create(...)
        >>> 
        >>> results = process_prompts_with_callback(
        ...     prompts=my_prompts,
        ...     api_callback=call_api,
        ...     save_path="results.json"
        ... )
    """
    manager = PromptManager(max_retries=max_retries)
    manager.add_prompts(prompts)
    
    # Process all prompts
    while manager.pending_count > 0 or manager.retry_count > 0:
        # Process pending
        while True:
            item = manager.get_next_prompt()
            if item is None:
                break
            
            prompt, metadata = item
            
            try:
                result = api_callback(prompt)
                manager.record_success(prompt, result, metadata)
            except Exception as e:
                manager.record_failure(prompt, str(e), metadata)
            
            # Log progress
            processed, total, pct = manager.progress()
            logger.info(f"Progress: {processed}/{total} ({pct}%)")
        
        # Retry failed
        if manager.retry_count > 0:
            manager.retry_failed()
    
    # Save if path provided
    if save_path:
        manager.save_results(save_path)
    
    return manager.get_results()
