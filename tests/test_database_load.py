"""Verificaciones sobre la base ya cargada.

Se omiten si PostgreSQL no está disponible o si la tabla está vacía, para que
`pytest` siga funcionando sin infraestructura. Con la base cargada comprueban
las condiciones finales de la Hoja de Trabajo.
"""

import pytest

from config import load_settings
from database import DatabaseError, connect, verify_load


@pytest.fixture(scope="module")
def conn():
    settings = load_settings()  # usa .env (DATABASE_URL real)
    try:
        connection = connect(settings.database_url)
    except DatabaseError as error:
        pytest.skip(f"PostgreSQL no disponible: {error}")

    with connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM faq_embeddings")
        if cur.fetchone()[0] == 0:
            connection.close()
            pytest.skip("La tabla faq_embeddings está vacía; ejecuta load_data.py.")

    yield connection
    connection.close()


def test_load_matches_expectations(conn):
    result = verify_load(conn)
    assert result.total == 120
    assert result.categories == 6
    assert result.dimension == 384
    assert result.duplicates == 0
    assert result.ok, result.problems
