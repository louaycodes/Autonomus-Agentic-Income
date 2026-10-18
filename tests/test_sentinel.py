import pytest
from pathlib import Path
from src.cluster.storage import Database
from src.cluster.sentinel import SentinelWatchdog

def test_sentinel_health_check(tmp_path: Path):
    db_file = tmp_path / "test_sentinel.db"
    db = Database(db_file)
    watchdog = SentinelWatchdog(db)

    health = watchdog.check_system_health()
    assert health["status"] == "healthy"
    assert health["database_integrity"] == "ok"
    assert health["disk_free_gb"] > 0
