from pathlib import Path

import pytest

from config import ConfigurationError, load_settings


def test_load_settings_uses_project_defaults(tmp_path: Path) -> None:
    settings = load_settings(project_root=tmp_path, env={})

    assert settings.embedding_dimension == 384
    assert settings.faq_file == (
        tmp_path / "data/Corpus_FAQs_Parachute_SA_2026.txt"
    ).resolve()
    assert settings.database_url.endswith("/parachute_faqs")


def test_load_settings_rejects_schema_dimension_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match=r"VECTOR\(384\)"):
        load_settings(
            project_root=tmp_path,
            env={"EMBEDDING_DIMENSION": "768"},
        )


def test_load_settings_requires_key_only_for_agent(tmp_path: Path) -> None:
    load_settings(project_root=tmp_path, env={}, require_llm_key=False)

    with pytest.raises(ConfigurationError, match="LLM_API_KEY"):
        load_settings(project_root=tmp_path, env={}, require_llm_key=True)
