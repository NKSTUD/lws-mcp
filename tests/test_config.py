import pytest

from lws_mcp.config import ConfigError, Settings


def test_reads_credentials_and_defaults():
    settings = Settings.from_env({"LWS_LOGIN": " 123456 ", "LWS_API_KEY": "prod"})
    assert settings.login == "123456"
    assert settings.api_key == "prod"
    assert not settings.test_mode
    assert settings.allows_writes
    assert not settings.allows_purchases


def test_missing_credentials_are_named():
    with pytest.raises(ConfigError, match="LWS_LOGIN, LWS_API_KEY"):
        Settings.from_env({})


def test_test_mode_prefers_the_test_key():
    env = {"LWS_LOGIN": "1", "LWS_API_KEY": "prod", "LWS_TEST_API_KEY": "test", "LWS_TEST_MODE": "true"}
    assert Settings.from_env(env).api_key == "test"
    assert Settings.from_env({**env, "LWS_TEST_MODE": "false"}).api_key == "prod"


def test_test_mode_falls_back_to_the_main_key():
    assert Settings.from_env({"LWS_LOGIN": "1", "LWS_API_KEY": "prod", "LWS_TEST_MODE": "1"}).api_key == "prod"


def test_read_only_wins_over_purchases():
    env = {"LWS_LOGIN": "1", "LWS_API_KEY": "k", "LWS_READ_ONLY": "yes", "LWS_ENABLE_PURCHASES": "true"}
    settings = Settings.from_env(env)
    assert not settings.allows_writes
    assert not settings.allows_purchases


def test_rejects_unclear_flags():
    with pytest.raises(ConfigError, match="LWS_READ_ONLY"):
        Settings.from_env({"LWS_LOGIN": "1", "LWS_API_KEY": "k", "LWS_READ_ONLY": "maybe"})
