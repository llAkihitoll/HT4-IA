"""Generación de embeddings con sentence-transformers (all-MiniLM-L6-v2).

Para cada FAQ se genera un único embedding a partir de la pregunta y la
respuesta, que es el texto con significado semántico útil para la búsqueda.
La metadata no se incluye porque no aporta a la similitud de la consulta.
"""

from __future__ import annotations

import os

# En algunos Windows, torch + OpenMP con varios hilos provoca un segfault al
# codificar lotes grandes. Limitar los hilos lo evita.
os.environ.setdefault("OMP_NUM_THREADS", "1")

from corpus import FaqRecord


def embedding_text(record: FaqRecord) -> str:
    return f"{record.question}\n{record.answer}"


class Embedder:
    def __init__(self, model_name: str, expected_dim: int) -> None:
        # Import diferido: cargar sentence-transformers es lento.
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.expected_dim = expected_dim

    def encode(self, records: list[FaqRecord]) -> list[list[float]]:
        texts = [embedding_text(record) for record in records]
        vectors = self.model.encode(texts, show_progress_bar=False)

        result = []
        for record, vector in zip(records, vectors):
            vector = [float(value) for value in vector]
            if len(vector) != self.expected_dim:
                raise ValueError(
                    f"El embedding de '{record.faq_id}' tiene {len(vector)} "
                    f"dimensiones y se esperaban {self.expected_dim}."
                )
            result.append(vector)
        return result
