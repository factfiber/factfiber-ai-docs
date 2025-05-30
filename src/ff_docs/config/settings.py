# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Application settings and configuration."""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(
        default="sqlite:///./ff_docs.db", description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Enable SQL query logging")


class GitHubSettings(BaseSettings):
    """GitHub integration settings."""

    token: str = Field(default="", description="GitHub personal access token")
    org: str = Field(
        default="factfiber", description="GitHub organization name"
    )
    webhook_secret: str = Field(default="", description="GitHub webhook secret")

    model_config = SettingsConfigDict(env_prefix="GITHUB_")


class AuthSettings(BaseSettings):
    """Authentication and authorization settings."""

    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT token signing",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )

    # OAuth2-Proxy settings
    oauth2_proxy_enabled: bool = Field(
        default=False, description="Enable OAuth2-Proxy integration"
    )
    oauth2_proxy_user_header: str = Field(
        default="X-Auth-Request-User",
        description="Header containing authenticated user",
    )
    oauth2_proxy_email_header: str = Field(
        default="X-Auth-Request-Email",
        description="Header containing user email",
    )
    oauth2_proxy_groups_header: str = Field(
        default="X-Forwarded-Groups",
        description="Header containing user groups",
    )
    oauth2_proxy_access_token_header: str = Field(
        default="X-Auth-Request-Access-Token",
        description="Header containing GitHub access token",
    )

    model_config = SettingsConfigDict(env_prefix="AUTH_")


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    host: str = Field(
        default="0.0.0.0",  # noqa: S104
        description="Server host",
    )
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    reload: bool = Field(
        default=False, description="Enable auto-reload in development"
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    model_config = SettingsConfigDict(env_prefix="SERVER_")


class MkDocsSettings(BaseSettings):
    """MkDocs configuration settings."""

    site_name: str = Field(
        default="FactFiber Documentation",
        description="Site name for generated documentation",
    )
    site_url: str = Field(
        default="https://docs.factfiber.ai",
        description="Base URL for the documentation site",
    )
    theme: str = Field(default="material", description="MkDocs theme to use")
    build_dir: str = Field(
        default="./build", description="Directory for built documentation"
    )
    temp_dir: str = Field(
        default="./temp", description="Temporary directory for processing"
    )

    model_config = SettingsConfigDict(env_prefix="MKDOCS_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file: str = Field(
        default="", description="Log file path (empty for stdout only)"
    )

    model_config = SettingsConfigDict(env_prefix="LOG_")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""

    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(
        default=9090, description="Prometheus metrics port"
    )
    health_check_enabled: bool = Field(
        default=True, description="Enable health check endpoints"
    )

    model_config = SettingsConfigDict(env_prefix="MONITORING_")


class Settings(BaseSettings):
    """Main application settings."""

    environment: str = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    mkdocs: MkDocsSettings = Field(default_factory=MkDocsSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ("production", "prod")

    def model_dump_config(self) -> dict[str, Any]:
        """Export configuration for MkDocs."""
        return {
            "site_name": self.mkdocs.site_name,
            "site_url": self.mkdocs.site_url,
            "theme": {"name": self.mkdocs.theme},
            "plugins": self._get_mkdocs_plugins(),
            "markdown_extensions": self._get_markdown_extensions(),
        }

    def _get_mkdocs_plugins(self) -> list[dict[str, Any]]:
        """Get MkDocs plugins configuration."""
        plugins: list[dict[str, Any]] = [
            {"search": {}},
            {"awesome-pages": {}},
            {
                "git-revision-date-localized": {
                    "enable_creation_date": True,
                    "type": "date",
                }
            },
            {
                "minify": {
                    "minify_html": True,
                    "minify_css": True,
                    "minify_js": True,
                }
            },
        ]

        if self.github.token:
            plugins.append(
                {
                    "multirepo": {
                        "cleanup": True,
                        "keep_docs_dir": False,
                    }
                }
            )

        return plugins

    def _get_markdown_extensions(self) -> list[str | dict[str, Any]]:
        """Get Markdown extensions configuration."""
        return [
            "abbr",
            "admonition",
            "attr_list",
            "def_list",
            "footnotes",
            "md_in_html",
            {"toc": {"permalink": True}},
            {"pymdownx.arithmatex": {"generic": True}},
            {"pymdownx.betterem": {"smart_enable": "all"}},
            "pymdownx.caret",
            "pymdownx.details",
            {
                "pymdownx.emoji": {
                    "emoji_index": (
                        "!!python/name:material.extensions.emoji.twemoji"
                    ),
                    "emoji_generator": (
                        "!!python/name:material.extensions.emoji.to_svg"
                    ),
                }
            },
            {
                "pymdownx.highlight": {
                    "anchor_linenums": True,
                    "line_spans": "__span",
                    "pygments_lang_class": True,
                }
            },
            "pymdownx.inlinehilite",
            "pymdownx.keys",
            "pymdownx.mark",
            "pymdownx.smartsymbols",
            {
                "pymdownx.superfences": {
                    "custom_fences": [
                        {
                            "name": "mermaid",
                            "class": "mermaid",
                            "format": (
                                "!!python/name:pymdownx.superfences.fence_code_format"
                            ),
                        }
                    ]
                }
            },
            {"pymdownx.tabbed": {"alternate_style": True}},
            {"pymdownx.tasklist": {"custom_checkbox": True}},
            "pymdownx.tilde",
        ]


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
