from pathlib import Path

import pytest

from emporio_agent import Agent, SessionMemory, load_data
from emporio_agent.llm import LLMResponse, ToolCall


DATA = Path(__file__).parents[1] / "Desafio Técnico AI Engineer 2026" / "data"


class ScriptedClient:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, messages, tools):
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def test_agent_runs_tool_then_returns_answer():
    client = ScriptedClient([
        LLMResponse("", [ToolCall("call-1", "buscar_produtos", {"query": "Ohana CK-20"})], {}),
        LLMResponse("Encontrei o Ohana CK-20 por R$ 439,20.", [], {}),
    ])
    agent = Agent(client, load_data(DATA), session_id="test")
    answer = agent.respond("Quanto custa o Ohana CK-20?")
    assert "439,20" in answer
    assert client.calls == 2


def test_agent_reports_tool_errors_to_model():
    client = ScriptedClient([
        LLMResponse("", [ToolCall("call-1", "calcular_condicoes", {"product_id": 999, "city": "Campo Grande"})], {}),
        LLMResponse("Não encontrei esse produto.", [], {}),
    ])
    answer = Agent(client, load_data(DATA), session_id="test").respond("Calcule o produto 999")
    assert answer == "Não encontrei esse produto."


def test_agent_can_answer_store_information_from_tool():
    client = ScriptedClient([
        LLMResponse("", [ToolCall("call-1", "consultar_dados_da_loja", {})], {}),
        LLMResponse("Ficamos na Rua 14 de Maio, 3200, Centro, Campo Grande - MS.", [], {}),
    ])
    answer = Agent(client, load_data(DATA), session_id="store-info").respond("Qual é o endereço?")
    assert "Rua 14 de Maio, 3200" in answer


def test_agent_enforces_round_limit():
    call = LLMResponse("", [ToolCall("call", "verificar_horario", {})], {})
    with pytest.raises(RuntimeError, match="limite de 2"):
        Agent(ScriptedClient([call]), load_data(DATA), max_rounds=2).respond("horário")


def test_memory_round_trip(tmp_path):
    memory = SessionMemory([{"role": "user", "content": "Oi"}], 12)
    path = tmp_path / "session.json"
    memory.save(path)
    loaded = SessionMemory.load(path)
    assert loaded.messages == memory.messages
    assert loaded.identified_customer_id == 12
