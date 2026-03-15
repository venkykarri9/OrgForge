from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "OrgForge"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/orgforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket: str = "orgforge-metadata"

    # Salesforce OAuth
    sf_client_id: str = ""
    sf_client_secret: str = ""
    sf_callback_url: str = "http://localhost:8000/api/auth/sf/callback"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/api/auth/github/callback"

    # Jira OAuth
    jira_client_id: str = ""
    jira_client_secret: str = ""
    jira_callback_url: str = "http://localhost:8000/api/auth/jira/callback"

    # Claude AI
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Security
    secret_key: str = "change-me-in-production"
    token_encryption_key: str = ""  # Fernet key for encrypting stored tokens


@lru_cache
def get_settings() -> Settings:
    return Settings()
