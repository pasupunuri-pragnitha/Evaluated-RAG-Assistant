import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "rag_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = ""

    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Documents to exclude (changelogs, contributor rosters, meta files)
    exclude_docs: list[str] = [
        "release-notes.md",
        "contributing.md",
        "fastapi-people.md",
        "translations.md",
        "translation-banner.md",
        "_llm-test.md",
        "reference/",
        "resources/index.md",
        "about/index.md",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
