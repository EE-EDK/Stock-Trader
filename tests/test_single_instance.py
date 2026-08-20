"""
@file test_single_instance.py
@brief Tests for the pipeline single-instance lock.
"""

import os
from src.utils.single_instance import acquire_lock, release_lock


def test_acquire_creates_lock(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    assert os.path.exists(lock)
    release_lock(lock)
    assert not os.path.exists(lock)


def test_second_acquire_fails(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    assert acquire_lock(lock) is False
    release_lock(lock)


def test_stale_lock_is_broken(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    # Backdate the lock file beyond the stale window
    old = os.path.getmtime(lock) - 10_000
    os.utime(lock, (old, old))
    assert acquire_lock(lock, stale_seconds=7200) is True
    release_lock(lock)
