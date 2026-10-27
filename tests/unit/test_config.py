"""Settings read from the environment."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gebeta.config import Settings
from gebeta.domain.models import DEFAULT_LIMITS, Limits


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # no .env file
    for name in [
        "GEBETA_MAX_DROPS",
        "GEBETA_MAX_MOVES_WITHOUT_CAPTURE",
        "GEBETA_HOST",
        "GEBETA_PORT",
        "GEBETA_CLAUDE_MODEL",
        "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)


def load() -> Settings:
    return Settings()


def test_defaults() -> None:
    settings = load()
    assert settings.limits == DEFAULT_LIMITS
    assert (settings.host, settings.port) == ("127.0.0.1", 8000)
    assert settings.anthropic_api_key is None


def test_environment_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEBETA_MAX_DROPS", "500")
    monkeypatch.setenv("GEBETA_MAX_MOVES_WITHOUT_CAPTURE", "30")
    monkeypatch.setenv("GEBETA_PORT", "9000")
    settings = load()
    assert settings.limits == Limits(max_drops=500, max_moves_without_capture=30)
    assert settings.port == 9000


def test_api_key_uses_the_standard_name_and_is_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    settings = load()
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-test"
    assert "sk-test" not in repr(settings)


def test_empty_api_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert load().anthropic_api_key is None


@pytest.mark.parametrize(
    ("name", "value"),
    [("GEBETA_MAX_DROPS", "0"), ("GEBETA_MAX_MOVES_WITHOUT_CAPTURE", "0"), ("GEBETA_PORT", "0")],
)
def test_out_of_range_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        load()
