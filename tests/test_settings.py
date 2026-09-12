from app.config.settings import BotMode, Environment, Settings


def test_settings_defaults() -> None:
    settings = Settings(bot_token="123456:TEST_TOKEN")

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.bot_mode is BotMode.POLLING
    assert settings.log_level == "INFO"


def test_webhook_requires_base_url() -> None:
    settings = Settings(
        bot_token="123456:TEST_TOKEN",
        bot_mode=BotMode.WEBHOOK,
        webhook_secret="test-secret",
    )

    try:
        settings.validate_runtime()
    except ValueError as exc:
        assert "WEBHOOK_BASE_URL" in str(exc)
    else:
        raise AssertionError("Expected webhook validation to fail")
