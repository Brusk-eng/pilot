from __future__ import annotations

import copy
from pathlib import Path

PATCH_NAME = Path(__file__).stem


def run(benches_root: Path) -> None:
    """List worker queues and their timeouts in common_site_config.json, so Frappe lets custom queues start."""
    from pilot.core.bench import Bench
    from pilot.internal.patch_state import is_applied, mark_applied

    for bench_dir in sorted(benches_root.glob("*")):
        if not bench_dir.is_dir() or not (bench_dir / "bench.toml").exists():
            continue
        if is_applied(bench_dir, PATCH_NAME):
            continue
        if (bench_dir / "sites" / "common_site_config.json").exists():
            import_queue_timeouts(bench_dir)
            register_worker_queues(Bench(bench_dir))
        mark_applied(bench_dir, PATCH_NAME)


def import_queue_timeouts(bench_dir: Path) -> None:
    """bench.toml owns the queue timeouts now, so carry over the ones set by hand.
    A group keeps one timeout, so it takes the longest of its queues, counting Frappe's default for the rest."""
    from pilot.config import BenchConfig
    from pilot.config.common_site_config import read_common_site_config
    from pilot.exceptions import ConfigError

    entries = read_common_site_config(bench_dir / "sites").get("workers")
    if not isinstance(entries, dict):
        return
    with BenchConfig.open(bench_dir) as config:
        groups = config.workers.groups
        before = [group.timeout for group in groups]
        for group in groups:
            if group.timeout is None:
                group.timeout = get_imported_timeout(bench_dir, entries, group.queues)
        try:
            config.workers.validate()
        except ConfigError as error:
            for group, timeout in zip(groups, before, strict=True):
                group.timeout = timeout
            print(f"{bench_dir.name}: set the worker timeouts in Settings again ({error})")


def get_imported_timeout(bench_dir: Path, entries: dict, queues: list[str]) -> int | None:
    from pilot.config.worker import frappe_default_timeout

    timeouts = {queue: get_hand_set_timeout(bench_dir, entries, queue) for queue in queues}
    if not any(timeouts.values()):
        return None
    return max(timeout or frappe_default_timeout(queue) for queue, timeout in timeouts.items())


def get_hand_set_timeout(bench_dir: Path, entries: dict, queue: str) -> int | None:
    entry = entries.get(queue)
    if not isinstance(entry, dict) or "timeout" not in entry:
        return None
    timeout = entry["timeout"]
    if type(timeout) is int and timeout > 0:
        return timeout
    print(f"{bench_dir.name}: set the timeout of queue '{queue}' in Settings again (got {timeout!r})")
    return None


def register_worker_queues(bench) -> None:
    from pilot.config.common_site_config import update_common_site_config
    from pilot.core.bench.config_files import BenchConfigFiles
    from pilot.managers.processes.definitions import ProcessDefinitionBuilder
    from pilot.managers.processes.local import ProcessManager

    with update_common_site_config(bench.sites_path) as config:
        before = copy.deepcopy(config.get("workers"))
        BenchConfigFiles(bench).set_worker_queues(config)
        is_changed = config.get("workers") != before

    # Workers read the queue list once, at start. Lite mode runs its jobs in web.
    if not is_changed or not bench.config.production.enabled:
        return
    manager = ProcessManager.detect_running(bench)
    if not manager.is_running():
        return
    job_process = "web" if bench.is_lite_mode else "worker"
    builder = ProcessDefinitionBuilder(bench, manager.python, watch_admin_js=False)
    manager.restart_processes(
        [
            definition
            for definition in builder.workload_definitions()
            if definition.name.startswith(job_process)
        ]
    )


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from pilot.utils import benches_dir

    run(benches_dir())
