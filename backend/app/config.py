from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://jobedin:jobedin_dev@localhost:5432/jobedin"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    SENTRY_DSN_BACKEND: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    AI_PIPELINE_TIMEOUT_SECONDS: int = 120
    AI_STALE_JOB_SWEEP_INTERVAL_SECONDS: int = 300
    AI_MAX_RETRIES: int = 2
    AI_RETRY_BASE_DELAY_SECONDS: float = 1.0
    AI_MALFORMED_RETRIES: int = 1

    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    GLM_MODEL: str = "glm-4-plus"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    ENCRYPTION_KEY: str = ""

    LINKEDIN_SEARCH_MAX_RESULTS: int = 25
    LINKEDIN_DELAY_MIN_SECONDS: float = 1.0
    LINKEDIN_DELAY_MAX_SECONDS: float = 4.0
    LINKEDIN_SESSION_COOLDOWN_HOURS: int = 24

    JSEARCH_API_KEY: str = ""
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    REMOTIVE_API_KEY: str = ""
    REED_API_KEY: str = ""

    JOB_DISCOVERY_CRON_HOUR: int = 6

    MATCH_SCORE_STALENESS_HOURS: int = 24
    MATCH_SCORE_CHUNK_SIZE: int = 100

    ATS_SCREENSHOT_DIR: str = "./screenshots"
    ATS_DETECT_TIMEOUT_MS: int = 30000
    ATS_DETECT_HEADLESS: bool = True
    ATS_STALE_DETECTION_MINUTES: int = 10
    ATS_FILL_TIMEOUT_SECONDS: int = 120
    ATS_RESUME_DIR: str = "./resumes"
    ATS_APPLY_MAX_BULK: int = 10
    ATS_APPLY_STALE_MINUTES: int = 15
    ATS_RESUME_FILE_FORMAT: str = "txt"

    CORS_ORIGINS: str = "http://localhost:3000"

    BYPASS_AUTH: bool = False
    BYPASS_AUTH_USER_ID: str = "00000000-0000-0000-0000-000000000001"
    BYPASS_AUTH_USER_EMAIL: str = "dev@jobedin.local"
    MAX_UPLOAD_SIZE_MB: int = 10

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_AI: str = "5/minute"
    RATE_LIMIT_APPLY: str = "5/minute"


settings = Settings()
