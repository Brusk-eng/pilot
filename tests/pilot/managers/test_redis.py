"""Tests for RedisManager.running: Redis served for the duration of a command."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pilot.managers.redis import RedisManager
from tests.pilot.managers.test_managers_extra import make_bench


@pytest.fixture
def manager(tmp_path: Path) -> RedisManager:
    bench = make_bench(tmp_path)
    return RedisManager(bench.config.redis, bench)


@contextmanager
def fake_servers(
    manager: RedisManager, listening: set[int], fail_for: str = "", starts: bool = True
) -> Iterator[Callable[[], list[MagicMock]]]:
    """Patch Popen and the port check. A started server listens on its port unless `starts` is
    False, and starting the server for the `fail_for` config file raises OSError."""
    started: list[MagicMock] = []

    def popen(argv: list[str], **_) -> MagicMock:
        name = Path(argv[-1]).name
        if name == fail_for:
            raise OSError(f"cannot start {name}")
        if starts:
            listening.add(manager.servers[name])
        started.append(MagicMock(name=name))
        return started[-1]

    with (
        patch("pilot.managers.redis.subprocess.Popen", side_effect=popen),
        patch("pilot.managers.redis.is_port_listening", side_effect=lambda port: port in listening),
        patch("pilot.managers.redis.redis_server_binary", return_value="redis-server"),
    ):
        yield lambda: started


def test_a_failure_starting_the_second_server_stops_the_first(manager: RedisManager) -> None:
    with (
        fake_servers(manager, set(), fail_for="redis_queue.conf") as started,
        pytest.raises(OSError, match=r"cannot start redis_queue\.conf"),
        manager.running(),
    ):
        pass

    [cache] = started()
    cache.terminate.assert_called_once()
    cache.wait.assert_called_once()
