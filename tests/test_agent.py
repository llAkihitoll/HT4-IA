from __future__ import annotations

import json
from contextlib import nullcontext
from types import SimpleNamespace

from agent import FAQAgent, NO_EVIDENCE


class FakeMessage:
    def __init__(self, content=None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        data = {"role": "assistant"}
        if self.content is not None:
            data["content"] = self.content
        if self.tool_calls is not None:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]
        return data


def tool_response(query="horario"):
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(
            name="search_faqs",
            arguments=json.dumps({"query": query, "limit": 5}),
        ),
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=FakeMessage(tool_calls=[call]))])


def final_response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=FakeMessage(content=text))])


class FakeCompletions:
    def __init__(self, responses) -> None:
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


class FakeSearch:
    def __init__(self, results) -> None:
        self.results = results
        self.calls = []
        self.conn = SimpleNamespace(close=lambda: None)

    def search_faqs(self, query, limit=5):
        self.calls.append((query, limit))
        return self.results


def client_with(*responses):
    completions = FakeCompletions(responses)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def test_agent_uses_search_tool_and_passes_evidence_to_llm() -> None:
    evidence = [{"faq_id": "FAQ-001", "answer": "De lunes a viernes"}]
    client, completions = client_with(
        tool_response(), final_response("De lunes a viernes. Fuente: FAQ-001")
    )
    search = FakeSearch(evidence)

    answer = FAQAgent(client, "test-model", search).answer("¿Cuál es el horario?")

    assert answer == "De lunes a viernes. Fuente: FAQ-001"
    assert search.calls == [("horario", 5)]
    assert completions.calls[0]["tool_choice"] == "required"
    assert completions.calls[1]["tool_choice"] == "none"
    tool_message = completions.calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert "FAQ-001" in tool_message["content"]


def test_agent_refuses_question_without_evidence_without_second_llm_call() -> None:
    client, completions = client_with(tool_response("ganador del mundial"))
    search = FakeSearch([])

    answer = FAQAgent(client, "test-model", search).answer("¿Quién ganó el mundial?")

    assert answer == NO_EVIDENCE
    assert len(completions.calls) == 1


def test_agent_accepts_multiple_questions_in_same_session() -> None:
    client, _ = client_with(
        tool_response("horario"),
        final_response("Respuesta uno. Fuente: FAQ-001"),
        tool_response("contacto"),
        final_response("Respuesta dos. Fuente: FAQ-002"),
    )
    search = FakeSearch([{"faq_id": "FAQ-001", "answer": "evidencia"}])
    agent = FAQAgent(client, "test-model", search)

    assert "Respuesta uno" in agent.answer("Primera pregunta")
    assert "Respuesta dos" in agent.answer("Segunda pregunta")
    assert len(search.calls) == 2
