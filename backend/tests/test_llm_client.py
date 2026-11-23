import httpx
import pytest
from app.services import llm_client
def test_generate_answer_appelle_gemma(monkeypatch):
    captured = {}
    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(200,json={"message": {"role": "assistant", "content": " Bonjour ! "}},request=httpx.Request("POST", url),)
    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    answer = llm_client.generate_answer([{"role": "user", "content": 
    "Salut"}])
    assert answer == "Bonjour !"
    assert captured["url"].endswith("/api/chat")
    assert captured["json"]["model"] == "gemma4:e4b"
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][-1] == {"role": "user", "content": 
    "Salut"}
def test_generate_answer_ollama_indisponible(monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("connexion refusée")
    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with pytest.raises(llm_client.LLMUnavailableError):
        llm_client.generate_answer([{"role": "user", "content": "Salut"}])


def test_warm_up_model_charge_et_garde_le_modele(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return httpx.Response(200, json={"done": True, "done_reason": "load"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    assert llm_client.warm_up_model() is True
    assert captured["url"].endswith("/api/generate")
    assert captured["json"] == {"model": "gemma4:e4b", "prompt": "", "keep_alive": -1}
    assert captured["timeout"] == llm_client.settings.ollama_load_timeout_seconds


def test_warm_up_model_ollama_indisponible(monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("connexion refusée")

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    assert llm_client.warm_up_model() is False