from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "autlead"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    database_url: str = ""
    database_echo: bool = False

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"
    gemini_rpm: int = 4
    gemini_rpd: int = 1450

    groq_cloud_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_requests_per_minute: int = 25
    groq_requests_per_day: int = 900
    groq_max_rate_limit_attempts: int = 3

    # Resend
    resend_api_key: str = ""
    resend_api_url: str = "https://api.resend.com"
    resend_from_email: str = ""
    resend_from_name: str = ""
    resend_reply_to: str | None = None
    resend_timeout_seconds: float = 30.0

    # Email outreach
    email_send_enabled: bool = False
    email_send_limit: int = 10
    email_skip_previously_sent: bool = True
    email_min_verification_confidence: float = 0.70
    email_allowed_verification_statuses: str = "deliverable"

    pagespeed_api_key: str = ""

    # Runtime data
    discovery_results_root: Path = Path(
        "data/discovery/gosom"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()