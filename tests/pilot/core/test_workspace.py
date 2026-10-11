"""Tests for `pilot dev`: an app repository developed on its own linked bench."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pilot.config import AppConfig, BenchConfig
from pilot.core.app import App
from pilot.core.bench import Bench
from pilot.core.site import Site
from pilot.core.workspace import Workspace
from pilot.exceptions import BenchError
from pilot.internal.cli.dispatch import CliContext, find_bench_root
from pilot.managers.environment import PythonEnvManager
from pilot.managers.processes.workspace import WorkspaceProcessManager
from pilot.managers.python_assets import PythonAssetBuilder
from pilot.managers.redis import RedisManager
from tests.pilot.commands.test_commands import make_bench


@pytest.fixture
def benches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "benches"
    path.mkdir()
    monkeypatch.setattr("pilot.core.workspace.benches_dir", lambda: path)
    return path


def make_repo(path: Path, name: str = "gameplan", dev_script: bool = True) -> Path:
    (path / name).mkdir(parents=True)
    (path / name / "hooks.py").write_text(f"app_name = '{name}'\n")
    (path / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n')
    (path / ".git").mkdir()
    scripts = {"dev": "vite"} if dev_script else {}
    (path / "package.json").write_text(json.dumps({"scripts": scripts}))
    return path


def fake_provision(bench: Bench, name: str, apps: list[str], admin_password: str, **_) -> Site:
    site = bench.site(name)
    site.path.mkdir(parents=True)
    (site.path / "site_config.json").write_text("{}")
    return site


def test_linked_app_round_trips_through_bench_toml(tmp_path: Path) -> None:
    config = make_bench(tmp_path).config
    config.apps.append(AppConfig(name="gameplan", repo="", branch="", path="/src/gameplan"))
    config.write(tmp_path)

    assert 'path = "/src/gameplan"' in (tmp_path / "bench.toml").read_text()
    linked = BenchConfig.read(tmp_path).get_app_by_name("gameplan")
    assert linked.is_linked
    assert linked.path == "/src/gameplan"


def test_workspace_is_found_from_inside_the_repository(tmp_path: Path, benches: Path) -> None:
    repo = make_repo(tmp_path / "Projects" / "gameplan")
    nested = repo / "gameplan" / "api"
    nested.mkdir()

    workspace = Workspace.find(nested)

    assert workspace is not None
    assert workspace.root == repo
    assert workspace.app_name == "gameplan"
    assert workspace.find_bench() is None
    assert Workspace.find(tmp_path) is None


def test_setup_creates_a_linked_bench_and_reruns_only_sync_it(tmp_path: Path, benches: Path) -> None:
    repo = make_repo(tmp_path / "gameplan")
    workspace = Workspace(repo)

    with (
        patch.object(Bench, "initialize") as initialize,
        patch.object(Site, "provision", side_effect=fake_provision) as provision,
        patch.object(Bench, "install_requirements") as install_requirements,
        patch.object(Site, "installed_apps", return_value=["frappe", "gameplan"]),
        patch.object(Site, "install_app") as install_app,
        patch.object(Site, "migrate") as migrate,
        patch.object(RedisManager, "running") as redis_running,
    ):
        site = workspace.setup()
        bench = workspace.bench
        (bench.env_path / "bin").mkdir(parents=True)
        bench.python.touch()
        workspace.setup()

    assert bench.path == benches / "dev-gameplan"
    assert bench.config.db_type == "sqlite"
    assert bench.config.framework_app.branch == "develop"
    assert not bench.config.admin.enabled
    assert bench.config.get_app_by_name("gameplan").path == str(repo)
    assert site.config.name == "dev-gameplan.localhost"
    assert json.loads((site.path / "site_config.json").read_text()) == {"developer_mode": 1}
    common_site_config = json.loads((bench.sites_path / "common_site_config.json").read_text())
    assert common_site_config["default_site"] == "dev-gameplan.localhost"
    initialize.assert_called_once()
    provision.assert_called_once()
    install_requirements.assert_called_once()
    install_app.assert_not_called()
    migrate.assert_called_once()
    redis_running.assert_called_once()

    with pytest.raises(BenchError, match="uses database 'sqlite', not 'postgres'"):
        workspace.setup(db_type="postgres")


def test_setup_resumes_a_site_left_without_the_app(tmp_path: Path, benches: Path) -> None:
    repo = make_repo(tmp_path / "gameplan")

    def provision_without_app(bench: Bench, name: str, *args, **kwargs) -> Site:
        fake_provision(bench, name, *args, **kwargs)
        raise BenchError("install-app failed")

    with (
        patch.object(Bench, "initialize"),
        patch.object(Site, "provision", side_effect=provision_without_app),
        pytest.raises(BenchError, match="install-app failed"),
    ):
        Workspace(repo).setup()

    workspace = Workspace(repo)
    bench = workspace.bench
    assert bench.config.get_app_by_name("gameplan").is_linked
    assert not bench.config.admin.enabled
    App(bench.config.get_app_by_name("gameplan"), bench).link()
    (bench.env_path / "bin").mkdir(parents=True)
    bench.python.touch()

    with (
        patch.object(Bench, "install_requirements"),
        patch.object(Site, "installed_apps", return_value=["frappe"]),
        patch.object(Site, "install_app") as install_app,
        patch.object(Site, "migrate") as migrate,
        patch.object(RedisManager, "running"),
    ):
        workspace.setup()

    assert install_app.call_args.args[0].config.name == "gameplan"
    migrate.assert_called_once()


def test_a_second_checkout_gets_its_own_bench(tmp_path: Path, benches: Path) -> None:
    (benches / "dev-gameplan").mkdir()

    workspace = Workspace(make_repo(tmp_path / "gameplan"))

    assert workspace.new_bench_name() == "dev-gameplan-2"


def test_linked_app_is_a_symlink_whose_git_state_pilot_never_touches(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "src" / "gameplan")
    bench = make_bench(tmp_path / "bench")
    bench.create_directories()
    app = App(AppConfig(name="gameplan", repo="", branch="", path=str(repo)), bench)

    app.link()

    assert (bench.apps_path / "gameplan").resolve() == repo
    assert bench.app("gameplan").is_linked
    with pytest.raises(BenchError, match="is linked to"):
        bench.app("gameplan").update()


def test_removing_a_linked_app_unlinks_it_and_keeps_the_checkout(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "src" / "gameplan")
    bench = make_bench(tmp_path / "bench")
    bench.create_directories()
    App(AppConfig(name="gameplan", repo="", branch="", path=str(repo)), bench).link()
    (bench.sites_path / "apps.txt").write_text("frappe\ngameplan\n")

    with patch.object(App, "_pip_uninstall"):
        bench.app("gameplan").remove()

    assert not (bench.apps_path / "gameplan").is_symlink()
    assert (repo / "gameplan" / "hooks.py").exists()
    assert bench.registered_apps() == ["frappe"]


def test_linked_app_builds_from_source_with_the_bench_path(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "src" / "gameplan")
    (repo / "frontend").mkdir()
    (repo / "frontend" / "package.json").write_text("{}")
    bench = make_bench(tmp_path / "bench")
    bench.create_directories()
    (bench.apps_path / "gameplan").symlink_to(repo)
    builder = PythonAssetBuilder(PythonEnvManager(bench))

    with (
        patch("pilot.core.app.prebuilt_assets.PrebuiltAssets") as prebuilt,
        patch.object(PythonAssetBuilder, "ensure_yarn_install"),
        patch.object(PythonAssetBuilder, "run_compiler") as run_compiler,
        patch("pilot.managers.python_assets.get_yarn_bin", return_value="yarn"),
    ):
        builder.build_assets_for_app(bench.app("gameplan"))

    prebuilt.assert_not_called()
    assert [call.args[0][-1] for call in run_compiler.call_args_list] == ["gameplan", "build"]
    for call in run_compiler.call_args_list:
        assert call.kwargs["env"]["FRAPPE_BENCH_PATH"] == str(bench.path)


def test_dev_processes_run_the_app_dev_script_without_admin(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "src" / "gameplan")
    bench = make_bench(tmp_path / "bench")
    bench.create_directories()
    (bench.apps_path / "gameplan").symlink_to(repo)

    definitions = WorkspaceProcessManager(bench, bench.app("gameplan"))._process_definitions()
    by_name = {definition.name: definition for definition in definitions}

    assert "admin" not in by_name
    assert {"web", "socketio", "watch"} <= by_name.keys()
    assert by_name["gameplan"].argv[-1] == "dev"
    assert by_name["gameplan"].env == {
        "FRAPPE_BENCH_PATH": str(bench.path),
        "FRAPPE_WEB_SERVER_PORT": str(bench.config.http_port),
    }


def test_bench_commands_inside_the_repository_use_its_bench(
    tmp_path: Path, benches: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path / "gameplan")
    bench_path = benches / "dev-gameplan"
    config = make_bench(bench_path).config
    config.apps.append(AppConfig(name="gameplan", repo="", branch="", path=str(repo)))
    bench_path.mkdir()
    config.write(bench_path)
    monkeypatch.chdir(repo / "gameplan")

    root = find_bench_root(CliContext(installation_root=tmp_path / "pilot"))

    assert root == bench_path
