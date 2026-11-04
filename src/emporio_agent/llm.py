import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _load_dotenv() -> None:
    path = os.getenv("EMPORIO_DOTENV", ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def _request_json(request: Request, provider: str) -> dict[str, Any]:
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code in {429, 503} and attempt < 2:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Falha no provedor {provider} ({error.code}): {detail}") from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError(f"Falha no provedor {provider}: {error}") from error
    raise RuntimeError(f"Falha no provedor {provider}: tentativas esgotadas.")


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    raw: dict[str, Any]


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse: ...


class OpenAICompatibleClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, "tools": tools}
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        body = _request_json(request, "OpenAI-compatible")
        choice = body["choices"][0]["message"]
        calls = [
            ToolCall(call["id"], call["function"]["name"], json.loads(call["function"]["arguments"]))
            for call in choice.get("tool_calls", [])
        ]
        return LLMResponse(choice.get("content") or "", calls, body)


class AnthropicClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com/v1") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        system = next((message["content"] for message in messages if message["role"] == "system"), "")
        conversation = [message for message in messages if message["role"] != "system"]
        payload = {"model": self.model, "max_tokens": 1024, "system": system, "messages": conversation, "tools": tools}
        request = Request(
            f"{self.base_url}/messages",
            data=json.dumps(payload).encode(),
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            method="POST",
        )
        body = _request_json(request, "Anthropic")
        text = "".join(block.get("text", "") for block in body.get("content", []) if block.get("type") == "text")
        calls = [
            ToolCall(block["id"], block["name"], block.get("input", {}))
            for block in body.get("content", []) if block.get("type") == "tool_use"
        ]
        return LLMResponse(text, calls, body)


def client_from_environment() -> LLMClient:
    _load_dotenv()
    provider = os.getenv("EMPORIO_PROVIDER", "openai").casefold()
    model = os.getenv("EMPORIO_MODEL", "gpt-4o-mini")
    key = os.getenv("EMPORIO_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Defina EMPORIO_API_KEY, OPENAI_API_KEY ou ANTHROPIC_API_KEY.")
    if provider == "anthropic":
        return AnthropicClient(key, model, os.getenv("EMPORIO_BASE_URL", "https://api.anthropic.com/v1"))
    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleClient(key, model, os.getenv("EMPORIO_BASE_URL", "https://api.openai.com/v1"))
    raise ValueError(f"Provedor desconhecido: {provider}")
