from dataclasses import dataclass, field


@dataclass
class AppEntry:
    name: str
    path: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    icon: str = "📦"
    launch_type: str = "startfile"  # "startfile" | "command"
    command: str = ""
    args: str = ""
    last_used: str = ""  # ISO timestamp of last launch

    @property
    def search_text(self) -> str:
        """Lowercase concatenation of name, description, and tags for filtering."""
        parts = [self.name, self.description] + self.tags
        return " ".join(parts).lower()

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "tags": self.tags,
            "icon": self.icon,
            "launch_type": self.launch_type,
            "command": self.command,
            "args": self.args,
        }
        if self.last_used:
            d["last_used"] = self.last_used
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AppEntry":
        return cls(
            name=d.get("name", ""),
            path=d.get("path", ""),
            description=d.get("description", ""),
            tags=d.get("tags", []),
            icon=d.get("icon", "📦"),
            launch_type=d.get("launch_type", "startfile"),
            command=d.get("command", ""),
            args=d.get("args", ""),
            last_used=d.get("last_used", ""),
        )
