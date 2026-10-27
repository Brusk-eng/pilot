from __future__ import annotations

from pathlib import Path

PATCH_NAME = Path(__file__).stem


def run(benches_root: Path) -> None:
    """List custom worker queues in common_site_config.json, so Frappe lets their workers start."""
    from pilot.core.bench import Bench
    from pilot.internal.patch_state import is_applied, mark_applied

    for bench_dir in sorted(benches_root.glob("*")):
        if not bench_dir.is_dir() or not (bench_dir / "bench.toml").exists():
            continue
        if is_applied(bench_dir, PATCH_NAME):
            continue
        bench = Bench(bench_dir)
        if bench.config.workers.custom_queues and (bench.sites_path / "common_site_config.json").exists():
            register_custom_queues(bench)
        mark_applied(bench_dir, PATCH_NAME)


def register_custom_queues(bench) -> None:
    from pilot.config.common_site_config import update_common_site_config
    from pilot.core.bench.config_files import BenchConfigFiles
    from pilot.managers.processes.definitions import ProcessDefinitionBuilder
    from pilot.managers.processes.local import ProcessManager

    with update_common_site_config(bench.sites_path) as config:
        BenchConfigFiles(bench).set_custom_queues(config)

    # Workers read the queue list once, at start. Lite mode runs its jobs in web.
    if not bench.config.production.enabled:
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
