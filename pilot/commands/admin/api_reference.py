from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar

from pilot.commands import Arg, BenchMode, Command


@dataclass(kw_only=True)
class ApiReferenceCommand(Command):
    name: ClassVar[str] = "api-reference"
    group: ClassVar[str] = "admin"
    help: ClassVar[str] = "Write the Admin API reference from the routes."
    bench_mode: ClassVar[BenchMode] = BenchMode.NONE

    output: Annotated[str, Arg(help="Markdown file to write (default: docs/admin-api-reference.md).")] = (
        "docs/admin-api-reference.md"
    )

    def run(self) -> None:
        from admin.backend.api.reference import get_api_reference

        Path(self.output).write_text(get_api_reference(), encoding="utf-8")
        self.report(f"Wrote {self.output}")
