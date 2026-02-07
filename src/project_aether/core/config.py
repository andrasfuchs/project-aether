"""
Configuration management for Project Aether.
Loads environment variables and provides centralized access to application settings.
"""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AetherConfig(BaseSettings):
    """
    Centralized configuration for Project Aether.
    Loads from environment variables and .env file.
    """
    
    # === API Tokens ===
    lens_org_api_token: str = Field(default="", alias="LENS_ORG_API_TOKEN")
    google_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    serpapi_key: str = Field(default="", alias="SERPAPI_KEY")
    
    # === Application Configuration ===
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_path: Path = Field(default=Path("./data/aether.db"), alias="DATABASE_PATH")
    vector_db_path: Path = Field(default=Path("./data/vectors"), alias="VECTOR_DB_PATH")
    
    # === Search Configuration ===
    default_jurisdictions: str = Field(
        default="RU,PL,RO,CZ,NL,ES,IT,SE,NO,FI",
        alias="DEFAULT_JURISDICTIONS"
    )
    search_window_days: int = Field(default=7, alias="SEARCH_WINDOW_DAYS")
    
    # === MCP Configuration ===
    mcp_host: str = Field(default="localhost", alias="MCP_HOST")
    mcp_port: int = Field(default=3000, alias="MCP_PORT")
    
    # === Rate Limiting ===
    max_requests_per_minute: int = Field(default=30, alias="MAX_REQUESTS_PER_MINUTE")
    max_retry_attempts: int = Field(default=5, alias="MAX_RETRY_ATTEMPTS")
    retry_delay_multiplier: float = Field(default=1.0, alias="RETRY_DELAY_MULTIPLIER")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def jurisdictions_list(self) -> List[str]:
        """Parse jurisdictions from comma-separated string."""
        return [j.strip().upper() for j in self.default_jurisdictions.split(",")]
    
    @property
    def lens_api_url(self) -> str:
        """Lens.org API endpoint."""
        return "https://api.lens.org/patent/search"
    
    @property
    def is_lens_configured(self) -> bool:
        """Check if Lens.org API token is configured."""
        return bool(self.lens_org_api_token and self.lens_org_api_token != "")
    
    @property
    def is_llm_configured(self) -> bool:
        """Check if at least one LLM API key is configured."""
        return bool(self.google_api_key or self.openai_api_key)
    
    def ensure_data_directories(self):
        """Create data directories if they don't exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)


# Singleton instance
_config: AetherConfig | None = None


def get_config() -> AetherConfig:
    """
    Get the application configuration singleton.
    Initializes on first call.
    """
    global _config
    if _config is None:
        _config = AetherConfig()
        _config.ensure_data_directories()
    return _config


def reload_config() -> AetherConfig:
    """Force reload of configuration from environment."""
    global _config
    _config = AetherConfig()
    _config.ensure_data_directories()
    return _config
