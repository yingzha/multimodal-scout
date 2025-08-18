"""
Configuration management for Google Cloud deployment.
Handles environment variables and secrets from Google Secret Manager.
"""

import os
from typing import Optional
from google.cloud import secretmanager
from .logger import logger


class Config:
    """Configuration class for managing environment variables and secrets."""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.is_cloud_environment = bool(self.project_id)

        if self.is_cloud_environment:
            self.secret_client = secretmanager.SecretManagerServiceClient()
        else:
            self.secret_client = None

    def get_secret(
        self, secret_name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a secret from Google Secret Manager in cloud environment,
        or from environment variables in local development.
        """
        # First try environment variable (for local development)
        env_value = os.getenv(secret_name.upper().replace("-", "_"))
        if env_value:
            return env_value

        # In cloud environment, try Secret Manager
        if self.is_cloud_environment and self.secret_client:
            try:
                secret_path = (
                    f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                )
                response = self.secret_client.access_secret_version(
                    request={"name": secret_path}
                )
                secret_value = response.payload.data.decode("UTF-8")
                logger.info(f"Retrieved secret '{secret_name}' from Secret Manager")
                return secret_value
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve secret '{secret_name}' from Secret Manager: {e}"
                )

        return default

    @property
    def database_url(self) -> str:
        """Get database URL with appropriate connection string for environment."""
        if self.is_cloud_environment:
            # Cloud SQL connection via Unix socket
            db_user = os.getenv("DB_USER", "scout_user")
            db_password = self.get_secret("database-password")
            db_name = os.getenv("DB_NAME", "multimodal_scout")
            instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")

            if not all([db_password, instance_connection_name]):
                raise ValueError(
                    "Missing required database configuration for Cloud SQL"
                )

            return f"postgresql://{db_user}:{db_password}@/{db_name}?host=/cloudsql/{instance_connection_name}"
        else:
            # Local development
            return os.getenv(
                "DATABASE_URL",
                "postgresql://scout_user:scout_password@localhost:5432/multimodal_scout",
            )

    @property
    def google_api_key(self) -> str:
        """Get Google API key from secrets or environment."""
        api_key = self.get_secret("google-api-key") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Google API key not found in secrets or environment variables"
            )
        return api_key

    @property
    def debug(self) -> bool:
        """Get debug flag."""
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    @property
    def port(self) -> int:
        """Get port from environment (Cloud Run sets this automatically)."""
        return int(os.getenv("PORT", "8000"))


# Global configuration instance
config = Config()
