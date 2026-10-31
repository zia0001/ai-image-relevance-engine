from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads configuration from environment variables and the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    gemini_api_key: str = ""
    vision_model: str = "gemini-3.5-flash"

    # The free tier allows about 5 requests per minute per model,
    # so calls are spaced at least this many seconds apart.
    max_attempts: int = 4
    seconds_between_calls: float = 13.0

    # Below this confidence an image is flagged for human review instead of trusted.
    min_confidence: float = 0.6

    # Embeddings. 768 dimensions is plenty for matching and keeps rows small.
    # The price is an estimate: verify it on the Gemini pricing page.
    embedding_model: str = "gemini-embedding-001"
    embedding_dims: int = 768
    embedding_input_rate: float = 0.15

    # Estimated list price, USD per 1M tokens. The free tier is not billed,
    # but we still record what a call would cost. Verify on the Gemini pricing page.
    vision_input_rate: float = 0.75
    vision_output_rate: float = 3.75

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
