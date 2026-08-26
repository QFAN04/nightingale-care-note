from app.config import Settings


def test_settings_repr_redacts_database_and_provider_credentials() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:database-secret@db.example/postgres",
        deepseek_api_key="deepseek-secret",
    )

    rendered = repr(settings)

    assert "database-secret" not in rendered
    assert "deepseek-secret" not in rendered
    assert (
        settings.database_url.get_secret_value()
        == "postgresql+psycopg://user:database-secret@db.example/postgres"
    )
    assert settings.deepseek_api_key is not None
    assert settings.deepseek_api_key.get_secret_value() == "deepseek-secret"

