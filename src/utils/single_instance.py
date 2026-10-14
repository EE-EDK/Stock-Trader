"""
@file single_instance.py
@brief Lock-file guard so only one pipeline instance runs at a time.
"""

import os
import time
import logging

logger = logging.getLogger(__name__)


def acquire_lock(lock_path: str, stale_seconds: int = 7200) -> bool:
    """
    @brief Atomically create a lock file. Returns False if a live lock exists.
    @details A lock older than stale_seconds is treated as a crashed run and broken.
    """
    if os.path.exists(lock_path):
        age = time.time() - os.path.getmtime(lock_path)
        if age < stale_seconds:
            return False
        logger.warning(f"Breaking stale pipeline lock ({age:.0f}s old): {lock_path}")
        try:
            os.remove(lock_path)
        except OSError:
            return False
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock(lock_path: str) -> None:
    """@brief Remove the lock file if present."""
    try:
        os.remove(lock_path)
    except OSError:
        pass
