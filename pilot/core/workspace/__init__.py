from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from pilot.exceptions import BenchError
from pilot.utils import benches_dir

if TYPE_CHECKING:
    from pilot.core.bench import Bench
    from pilot.core.site import Site

ADMIN_PASSWORD = "admin"
DEFAULT_DB_TYPE = "sqlite"


class Workspace:
    """A Frappe app repository developed on its own bench. The bench lives in the
    benches directory and links the repository into apps/, so the repository
    stays the developer's own checkout."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    @classmethod
    def find(cls, start: Path | None = None) -> "Workspace | None":
        """The app repository containing `start` (default: the current directory)."""
        start = (start or Path.cwd()).resolve()
        for directory in (start, *start.parents):
            workspace = cls(directory)
            if workspace.is_frappe_app:
                return workspace
        return None

    @classmethod
    def current(cls) -> "Workspace":
        workspace = cls.find()
        if workspace is None:
            raise BenchError(
                "No Frappe app found here. Run this inside an app repository, next to its pyproject.toml."
            )
        return workspace

    @cached_property
    def app_name(self) -> str:
        """The app's importable package name, read from pyproject.toml."""
        try:
            project = tomllib.loads((self.root / "pyproject.toml").read_text()).get("project", {})
        except (OSError, tomllib.TOMLDecodeError):
            return ""
        return str(project.get("name", "")).replace("-", "_")

    @property
    def is_frappe_app(self) -> bool:
        return bool(self.app_name) and (self.root / self.app_name / "hooks.py").exists()

    @property
    def default_frappe_branch(self) -> str:
        """The app's own `version-N` branch, or develop for any other branch."""
        from pilot.internal.git import GitRepo

        branch = GitRepo(self.root).branch
        return branch if re.fullmatch(r"version-\d+", branch) else "develop"

    @property
    def bench(self) -> "Bench":
        bench = self.find_bench()
        if bench is None:
            raise BenchError(f"{self.root} has no bench yet. Run: pilot dev setup")
        return bench

    def find_bench(self) -> "Bench | None":
        """The bench that links this repository, if one was set up."""
        from pilot.core.bench import Bench

        for toml_path in sorted(benches_dir().glob("*/bench.toml")):
            if self.is_linked_from(toml_path):
                return Bench(toml_path.parent)
        return None

    def is_linked_from(self, toml_path: Path) -> bool:
        try:
            apps = tomllib.loads(toml_path.read_text()).get("apps", [])
        except (OSError, tomllib.TOMLDecodeError):
            return False
        return any(app.get("path") == str(self.root) for app in apps)

    def site(self, bench: "Bench") -> "Site":
        return bench.site(f"{bench.config.name}.localhost")

    def setup(
        self,
        db_type: str | None = None,
        frappe_branch: str | None = None,
        on_progress: Callable[[str], None] = lambda message: None,
    ) -> "Site":
        """Create, initialise, and provision the bench, or bring an existing one
        up to date with the repository. Safe to run again."""
        if self.app_name == "frappe":
            raise BenchError("Pilot dev cannot develop the frappe framework itself yet.")
        bench = self.find_bench()
        if bench is None:
            bench = self.create_bench(
                db_type or DEFAULT_DB_TYPE, frappe_branch or self.default_frappe_branch, on_progress
            )
        else:
            self.ensure_matches(bench, db_type, frappe_branch)
        if not bench.python.exists():
            bench.initialize(on_progress)
        site = self.site(bench)
        if site.exists:
            self.sync(bench, site, on_progress)
        else:
            self.create_site(bench, on_progress)
        self.configure_site(bench, site)
        return site

    def create_bench(self, db_type: str, frappe_branch: str, on_progress: Callable[[str], None]) -> "Bench":
        from pilot.config import AppConfig, BenchConfig
        from pilot.core.bench import Bench

        name = self.new_bench_name()
        on_progress(f"Creating bench '{name}' ({db_type}, frappe {frappe_branch}) for {self.root}")
        path = benches_dir() / name
        Bench.create_at(path, name, db_type=db_type)
        with BenchConfig.open(path) as config:
            config.admin.enabled = False
            config.allow_developer_mode = True
            config.framework_app.branch = frappe_branch
            config.apps.append(AppConfig(name=self.app_name, repo="", branch="", path=str(self.root)))
        return Bench(path)

    def new_bench_name(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.root.name.lower()).strip("-") or "app"
        name = base = f"dev-{slug}"
        suffix = 2
        while (benches_dir() / name).exists():
            name = f"{base}-{suffix}"
            suffix += 1
        return name

    def ensure_matches(self, bench: "Bench", db_type: str | None, frappe_branch: str | None) -> None:
        """An existing bench keeps its database and framework branch. Changing either
        means starting over, which deletes the site's data."""
        current = {"database": bench.config.db_type, "frappe branch": bench.config.framework_app.branch}
        requested = {"database": db_type, "frappe branch": frappe_branch}
        for label, value in requested.items():
            if value and value != current[label]:
                raise BenchError(
                    f"Bench '{bench.config.name}' uses {label} '{current[label]}', not '{value}'. "
                    "Run 'pilot dev drop' first to start over."
                )

    def create_site(self, bench: "Bench", on_progress: Callable[[str], None]) -> "Site":
        from pilot.core.site import Site

        name = self.site(bench).config.name
        return Site.provision(bench, name, [self.app_name], ADMIN_PASSWORD, on_progress=on_progress)

    def configure_site(self, bench: "Bench", site: "Site") -> None:
        """Turn on developer mode, and make this the site that Frappe commands
        without --site use."""
        from pilot.config.common_site_config import update_common_site_config

        site.set_config_values({"developer_mode": 1})
        with update_common_site_config(bench.sites_path) as config:
            config["default_site"] = site.config.name

    def sync(self, bench: "Bench", site: "Site", on_progress: Callable[[str], None]) -> None:
        """Catch up with a pulled repository: new requirements and schema changes."""
        from pilot.managers.redis import RedisManager

        bench.install_requirements(on_progress)
        on_progress(f"Migrating {site.config.name}...")
        with RedisManager(bench.config.redis, bench).running():
            site.migrate()

    def start(self, on_progress: Callable[[str], None] = lambda message: None) -> None:
        """Run the bench in the foreground until interrupted."""
        from pilot.managers.processes.workspace import WorkspaceProcessManager

        bench = self.bench
        site = self.site(bench)
        if not bench.python.exists() or not site.exists:
            raise BenchError(f"Bench '{bench.config.name}' is not set up yet. Run: pilot dev setup")
        manager = WorkspaceProcessManager(bench, bench.app(self.app_name))
        if manager.is_running():
            raise BenchError(f"Bench '{bench.config.name}' is already running.")
        on_progress(f"\n  Site   {self.site_url(bench)}")
        on_progress(f"  Login  Administrator / {ADMIN_PASSWORD}\n")
        manager.start()

    def site_url(self, bench: "Bench") -> str:
        return f"http://{self.site(bench).config.name}:{bench.config.http_port}"

    def drop(self, on_progress: Callable[[str], None] = lambda message: None) -> None:
        """Delete the bench and its site. The repository is left untouched."""
        bench = self.bench
        site = self.site(bench)
        if site.exists:
            site.drop(on_progress, no_backup=True)
        bench.drop(on_progress)
