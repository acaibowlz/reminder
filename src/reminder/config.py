from pydantic_settings import BaseSettings


class Constants(BaseSettings):
    LINE_CHANNEL_SECRET: str
    LINE_CHANNEL_ACCESS_TOKEN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


const = Constants()
