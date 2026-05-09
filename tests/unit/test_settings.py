import importlib

import app.settings as settings_module


def test_settings_prefer_groq_environment_variables(monkeypatch):
    original_values = (
        settings_module.settings.llm_api_key,
        settings_module.settings.llm_base_url,
        settings_module.settings.llm_model,
    )
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("LLM_API_KEY", "legacy-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("LLM_MODEL", "legacy-model")

    reloaded = importlib.reload(settings_module)

    assert reloaded.settings.llm_api_key == "groq-key"
    assert reloaded.settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert reloaded.settings.llm_model == "llama-3.3-70b-versatile"

    monkeypatch.undo()
    restored = importlib.reload(settings_module)

    assert restored.settings.llm_api_key == original_values[0]
    assert restored.settings.llm_base_url == original_values[1]
    assert restored.settings.llm_model == original_values[2]