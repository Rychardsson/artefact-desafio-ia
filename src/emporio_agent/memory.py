import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionMemory:
    messages: list[dict[str, Any]] = field(default_factory=list)
    identified_customer_id: int | None = None

    @classmethod
    def load(cls, path: str | Path) -> "SessionMemory":
        file = Path(path)
        if not file.exists():
            return cls()
        data = json.loads(file.read_text(encoding="utf-8"))
        return cls(data.get("messages", []), data.get("identified_customer_id"))

    def save(self, path: str | Path) -> None:
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps({
            "messages": self.messages,
            "identified_customer_id": self.identified_customer_id,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def append(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    def bounded_messages(self, turns: int = 12) -> list[dict[str, Any]]:
        return self.messages[-turns * 2:]
