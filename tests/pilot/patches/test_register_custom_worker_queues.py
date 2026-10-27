from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pilot.config import WorkerGroup
from pilot.core.bench import Bench
from pilot.managers.processes.local import ProcessManager
from pilot.patches.register_custom_worker_queues import register_custom_queues, run
from tests.pilot.commands.test_commands import make_bench


def test_lists_custom_queues_once(tmp_path: Path) -> None:
    bench_dir = tmp_path / "main"
    (bench_dir / "sites").mkdir(parents=True)
    (bench_dir / "bench.toml").write_text(
        '[bench]\nname = "main"\npython = "3.14"\n\n[[workers]]\nqueues = ["default", "guard-review"]\ncount = 2\n'
    )
    config_path = bench_dir / "sites" / "common_site_config.json"
    config_path.write_text('{"webserver_port": 8000}')

    run(tmp_path)
    assert json.loads(config_path.read_text()) == {"webserver_port": 8000, "workers": {"guard-review": {}}}

    config_path.write_text("{}")
    run(tmp_path)
    assert json.loads(config_path.read_text()) == {}


@pytest.fixture
def production_bench(tmp_path: Path):
    bench = make_bench(tmp_path)
    bench.create_directories()
    bench.config.production.enabled = True
    bench.config.production.process_manager = "systemd"
    bench.config.workers.groups.append(WorkerGroup(queues=["guard-review"], count=1))
    (bench.sites_path / "common_site_config.json").write_text("{}")
    return bench


_SYSTEMD_POOLS = {"worker_pool_default", "worker_pool_short", "worker_pool_long", "worker_pool_guard_review"}
_SUPERVISOR_WORKERS = {
    "worker_default_1",
    "worker_default_2",
    "worker_short_1",
    "worker_long_1",
    "worker_guard_review_1",
}


def _register(bench, is_running: bool = True, is_lite_mode: bool = False) -> MagicMock:
    manager = MagicMock(python=Path("/usr/bin/python3"))
    manager.is_running.return_value = is_running
    common_site_config = bench.sites_path / "common_site_config.json"
    manager.restart_processes.side_effect = lambda definitions: json.loads(common_site_config.read_text())[
        "workers"
    ]
    with (
        patch.object(ProcessManager, "detect_running", return_value=manager),
        patch.object(Bench, "is_lite_mode", new_callable=PropertyMock, return_value=is_lite_mode),
    ):
        register_custom_queues(bench)
    return manager


def _restarted(manager: MagicMock) -> set[str]:
    return {definition.name for definition in manager.restart_processes.call_args.args[0]}


@pytest.mark.parametrize(
    ("process_manager", "is_lite_mode", "restarted"),
    [
        ("systemd", False, _SYSTEMD_POOLS),
        ("supervisor", False, _SUPERVISOR_WORKERS),
        ("systemd", True, {"web"}),
    ],
)
def test_restarts_the_processes_that_run_jobs(
    production_bench, process_manager, is_lite_mode, restarted
) -> None:
    production_bench.config.production.process_manager = process_manager

    manager = _register(production_bench, is_lite_mode=is_lite_mode)

    assert _restarted(manager) == restarted


@pytest.mark.parametrize("is_production", [True, False])
def test_a_stopped_or_dev_bench_restarts_nothing(production_bench, is_production) -> None:
    production_bench.config.production.enabled = is_production

    manager = _register(production_bench, is_running=False)

    manager.restart_processes.assert_not_called()
    config = json.loads((production_bench.sites_path / "common_site_config.json").read_text())
    assert config["workers"] == {"guard-review": {}}
