"""Application configuration loaded from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Runtime settings for the backend application."""

	APP_NAME: str = "Sushant Neural Twin"
	APP_VERSION: str = "0.1.0"
	APP_ENV: str = "development"
	DEBUG: bool = True
	API_PREFIX: str = "/api"
	HOST: str = "127.0.0.1"
	PORT: int = 8000
	CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
	AUTH_ENABLED: bool = False
	AUTH_TOKEN: str | None = None
	RATE_LIMIT_REQUESTS: int = 60
	RATE_LIMIT_WINDOW_SECONDS: int = 60

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	@model_validator(mode="after")
	def validate_security_settings(self) -> "Settings":
		"""Require an explicit token when authentication is enabled."""

		if self.AUTH_ENABLED and not self.AUTH_TOKEN:
			raise ValueError("AUTH_TOKEN is required when AUTH_ENABLED is true")
		if self.RATE_LIMIT_REQUESTS < 1 or self.RATE_LIMIT_WINDOW_SECONDS < 1:
			raise ValueError("rate-limit settings must be at least 1")
		return self

	@property
	def cors_origins(self) -> list[str]:
		"""Return configured CORS origins as a normalized list."""

		return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
