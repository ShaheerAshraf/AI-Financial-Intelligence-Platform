from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = (
        "postgresql://financial_user:"
        "financial_password@localhost:5432/financial_ai"
    )

    class Config:
        env_file = ".env"


settings = Settings()