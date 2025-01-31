from pydantic import BaseSettings


class Settings(BaseSettings):
    etranslation_username: str
    etranslation_password: str
    # Either callback_url or snippet_callback_url and document_callback_url must be set
    callback_url: str = None
    snippet_callback_url: str = None  # Overrides callback_url
    document_callback_url: str = None  # Overrides callback_url
    snippet_timeout: int
    document_timeout: int
