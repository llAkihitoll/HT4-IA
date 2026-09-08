"""Agente de terminal que responde únicamente con evidencia del corpus."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import Settings, load_settings
from search import FAQSearch, build_search


SYSTEM_PROMPT = """Eres el agente de FAQs de Parachute S.A.
Debes usar search_faqs antes de contestar cada pregunta. Responde únicamente con
hechos presentes en los resultados de la herramienta y en español. No uses tu
conocimiento general ni completes detalles implícitos. Si los resultados están
vacíos o no contienen evidencia para la pregunta, di exactamente: "No puedo
responder con la información disponible en el corpus." Sé breve e indica los
faq_id usados como fuentes.
"""

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_faqs",
        "description": "Busca evidencia semántica en el corpus de FAQs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pregunta del usuario"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

NO_EVIDENCE = "No puedo responder con la información disponible en el corpus."


class FAQAgent:
    def __init__(self, client: Any, model: str, search: FAQSearch) -> None:
        self.client = client
        self.model = model
        self.search = search

    def answer(self, question: str) -> str:
        question = question.strip()
        if not question:
            raise ValueError("La pregunta no puede estar vacía.")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[SEARCH_TOOL],
            tool_choice="required",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        found_evidence = False
        for call in message.tool_calls or []:
            if call.function.name != "search_faqs":
                result: Any = {"error": "Herramienta desconocida."}
            else:
                try:
                    arguments = json.loads(call.function.arguments)
                    result = self.search.search_faqs(
                        arguments["query"], arguments.get("limit", 5)
                    )
                    found_evidence = found_evidence or bool(result)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    result = {"error": str(error)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        if not found_evidence:
            return NO_EVIDENCE

        final = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[SEARCH_TOOL],
            tool_choice="none",
        )
        return (final.choices[0].message.content or NO_EVIDENCE).strip()


def build_agent(settings: Settings | None = None) -> FAQAgent:
    settings = settings or load_settings(require_llm_key=True)
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return FAQAgent(client, settings.llm_model, build_search(settings))


def main() -> None:
    agent = build_agent()
    print("Agente de FAQs listo. Escribe Bye o presiona Ctrl+C para salir.")
    try:
        while True:
            question = input("\nTú: ").strip()
            if question.casefold() == "bye":
                print("Bye")
                break
            if not question:
                continue
            try:
                print(f"Agente: {agent.answer(question)}")
            except Exception as error:
                print(f"Error al procesar la pregunta: {error}")
    except (KeyboardInterrupt, EOFError):
        print("\nBye")
    finally:
        agent.search.conn.close()


if __name__ == "__main__":
    main()
