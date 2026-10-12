from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pilot.core.app.node_packages import NodePackages
from pilot.managers.processes.definitions import ProcessDefinition
from pilot.managers.processes.local import ProcessManager

if TYPE_CHECKING:
    from pilot.core.app import App
    from pilot.core.bench import Bench


class WorkspaceProcessManager(ProcessManager):
    """Runs a workspace bench in the foreground: Frappe without the admin plane,
    plus the linked app's own `dev` script."""

    def __init__(self, bench: "Bench", app: "App") -> None:
        super().__init__(bench, watch_admin_js=False)
        self.app = app

    @property
    def has_app_dev_script(self) -> bool:
        package_json = self.app.path / "package.json"
        if not package_json.exists():
            return False
        return "dev" in json.loads(package_json.read_text()).get("scripts", {})

    def app_dev_definition(self) -> ProcessDefinition:
        # frappe-ui's Vite plugins read these, since the app repository has no bench
        # folder above it.
        name = f"{self.app.config.name}-dev"
        return ProcessDefinition(
            name=name,
            argv=NodePackages(self.app.path).get_script_command("dev"),
            log_file=self.bench.logs_path / f"{name}.log",
            env={
                "FRAPPE_BENCH_PATH": str(self.bench.path),
                "FRAPPE_WEB_SERVER_PORT": str(self.bench.config.http_port),
            },
            working_dir=self.app.path,
            critical=False,
        )

    def _process_definitions(self) -> list[ProcessDefinition]:
        definitions = [pd for pd in super()._process_definitions() if pd.name != "admin"]
        if self.has_app_dev_script:
            definitions.append(self.app_dev_definition())
        return definitions
