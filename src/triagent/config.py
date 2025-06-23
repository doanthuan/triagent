from dotenv import load_dotenv
from loguru import logger
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    exa_api_key: str = Field(default="")
    litellm_model_default: str = Field(default="openai/gpt-4.1-mini")
    gemini_api_key: str = Field(default="")
    gemini_pro_model: str = Field(default="gemini-2.5-pro-preview-05-06")
    gemini_flash_model: str = Field(default="gemini-2.5-flash-preview-05-20")
    gemini_flash_lite_model: str = Field(default="gemini-2.5-flash-lite-preview-06-17")
    litellm_gemini_pro_model: str = Field(default="gemini/gemini-2.5-pro-preview-05-06")
    litellm_gemini_flash_model: str = Field(default="gemini/gemini-2.5-flash-preview-05-20")
    litellm_gemini_flash_lite_model: str = Field(default="gemini/gemini-2.5-flash-lite-preview-06-17")
    litellm_openai_gpt_4_1_mini_model: str = Field(default="openai/gpt-4.1-mini")
    litellm_openai_gpt_4o_mini_model: str = Field(default="openai/gpt-4o-mini")
    openai_api_key: str = Field(default="")
    tour_rank_max_tournaments: int = Field(default=2)


try:
    settings = Settings()
except Exception:
    message = "Error missing ENVIRONMENT variable. "
    logger.error(message)
    raise Exception(message)
