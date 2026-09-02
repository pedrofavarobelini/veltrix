from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Veltrix"
    app_env: str = "development"
    api_port: int = 3333

    default_provider: str = "mock"
    default_model: str = "mock-v1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    openai_api_key: str = ""
    openai_model: str = "gpt-5.2-mini"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    xai_api_key: str = ""
    xai_model: str = "grok-4.3"
    xai_base_url: str = "https://api.x.ai/v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
