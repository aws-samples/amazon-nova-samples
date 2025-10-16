from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from .decorators import validate_app_config

dotenv_encoding = "utf-8"
dotenv_path = find_dotenv(".env")


class BaseConfig(BaseSettings):
    """
    Base configuration class that inherits from Pydantic BaseSettings to validate env vars.
    This class is responsible for loading environment variables from a .env file and validating them.
    """

    model_config = SettingsConfigDict(
        env_file=dotenv_path,
        env_file_encoding=dotenv_encoding
    )

    @validate_app_config
    def __init__(self, **data):
        load_dotenv(dotenv_path, override=True, encoding=dotenv_encoding)
        super().__init__(**data)


class AppConfig(BaseConfig):
    """
    Defines the env vars required to run the app
    """

    WEB_APP_URL: str
    NOVA_ACT_API_KEY: str
