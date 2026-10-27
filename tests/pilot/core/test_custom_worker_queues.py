from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pilot.config import WorkerGroup
from pilot.core.bench.settings import regenerate_configs
from pilot.exceptions import MalformedSiteConfig
from tests.pilot.commands.test_commands import make_bench


def _bench_with_queues(tmp_path: Path, *queues: str):
    bench = make_bench(tmp_path)
    bench.sites_path.mkdir(parents=True, exist_ok=True)
    bench.config.workers.groups.extend(WorkerGroup(queues=[queue], count=1) for queue in queues)
    return bench


def _common_site_config(bench) -> dict:
    return json.loads((bench.sites_path / "common_site_config.json").read_text())


def test_custom_queues_skip_the_frappe_queues(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review", "default")

    assert bench.config.workers.custom_queues == ["guard-review"]


def test_frappe_learns_the_custom_queues(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review", "guard-base")

    bench.write_common_site_config()

    assert _common_site_config(bench)["workers"] == {"guard-review": {}, "guard-base": {}}


def test_a_queue_keeps_its_timeout_and_a_dropped_queue_goes(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review")
    (bench.sites_path / "common_site_config.json").write_text(
        json.dumps({"workers": {"guard-review": {"timeout": 1500}, "guard-old": {}}})
    )

    bench.write_common_site_config()

    assert _common_site_config(bench)["workers"] == {"guard-review": {"timeout": 1500}}


def test_no_custom_queue_leaves_no_workers_key(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path)
    (bench.sites_path / "common_site_config.json").write_text(json.dumps({"workers": {"guard-old": {}}}))

    bench.write_common_site_config()

    assert "workers" not in _common_site_config(bench)


def test_saved_settings_rewrite_common_site_config(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review")

    with (
        patch("pilot.managers.redis.RedisManager"),
        patch("pilot.managers.processes.local.ProcessManager.for_bench", return_value=MagicMock()),
    ):
        regenerate_configs(bench)

    assert _common_site_config(bench)["workers"] == {"guard-review": {}}


@pytest.mark.parametrize("workers", [["guard-review"], "guard-review"])
def test_a_malformed_workers_value_fails_loudly(tmp_path: Path, workers) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review")
    path = bench.sites_path / "common_site_config.json"
    path.write_text(json.dumps({"workers": workers}))

    with pytest.raises(MalformedSiteConfig):
        bench.write_common_site_config()

    assert json.loads(path.read_text()) == {"workers": workers}


def test_a_malformed_queue_entry_is_reset(tmp_path: Path) -> None:
    bench = _bench_with_queues(tmp_path, "guard-review")
    (bench.sites_path / "common_site_config.json").write_text(json.dumps({"workers": {"guard-review": None}}))

    bench.write_common_site_config()

    assert _common_site_config(bench)["workers"] == {"guard-review": {}}
