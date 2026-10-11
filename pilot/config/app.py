from dataclasses import dataclass, field


@dataclass
class AppConfig:
    name: str
    repo: str
    branch: str
    branches: list[str] = field(default_factory=list)
    # A local checkout linked into apps/ instead of cloned from repo.
    path: str = ""

    @property
    def is_linked(self) -> bool:
        return bool(self.path)
