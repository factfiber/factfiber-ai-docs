# Copyright 2025 Fact Fiber Inc. All rights reserved.
# ruff: noqa: SLF001

"""Test configuration settings."""

import os
from unittest.mock import patch

from ff_docs.config.settings import (
    AuthSettings,
    DatabaseSettings,
    GitHubSettings,
    LoggingSettings,
    MkDocsSettings,
    MonitoringSettings,
    ServerSettings,
    Settings,
    get_settings,
    settings,
)


class TestDatabaseSettings:
    """Test DatabaseSettings configuration."""

    def test_default_values(self) -> None:
        """Test default database settings."""
        db_settings = DatabaseSettings()
        assert db_settings.url == "sqlite:///./ff_docs.db"
        assert db_settings.echo is False

    def test_custom_values(self) -> None:
        """Test custom database settings."""
        db_settings = DatabaseSettings(
            url="postgresql://user:pass@localhost/db", echo=True
        )
        assert db_settings.url == "postgresql://user:pass@localhost/db"
        assert db_settings.echo is True


class TestGitHubSettings:
    """Test GitHubSettings configuration."""

    def test_default_values(self) -> None:
        """Test default GitHub settings."""
        github_settings = GitHubSettings()
        assert github_settings.token == ""
        assert github_settings.org == "factfiber"
        assert github_settings.webhook_secret == ""

    def test_github_webhook_secret_property(self) -> None:
        """Test GitHub webhook secret backward compatibility property."""
        github_settings = GitHubSettings(webhook_secret="test-secret")  # noqa: S106
        assert github_settings.github_webhook_secret == "test-secret"  # noqa: S105
        assert github_settings.webhook_secret == "test-secret"  # noqa: S105

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "test-token",
                "GITHUB_ORG": "test-org",
                "GITHUB_WEBHOOK_SECRET": "test-webhook-secret",
            },
        ):
            github_settings = GitHubSettings()
            assert github_settings.token == "test-token"  # noqa: S105
            assert github_settings.org == "test-org"
            assert github_settings.webhook_secret == "test-webhook-secret"  # noqa: S105


class TestAuthSettings:
    """Test AuthSettings configuration."""

    def test_default_values(self) -> None:
        """Test default auth settings."""
        auth_settings = AuthSettings()
        assert auth_settings.secret_key == "dev-secret-key-change-in-production"  # noqa: S105
        assert auth_settings.algorithm == "HS256"
        assert auth_settings.access_token_expire_minutes == 30
        assert auth_settings.oauth2_proxy_enabled is False
        assert auth_settings.oauth2_proxy_user_header == "X-Auth-Request-User"
        assert auth_settings.oauth2_proxy_email_header == "X-Auth-Request-Email"
        assert auth_settings.oauth2_proxy_groups_header == "X-Forwarded-Groups"
        assert (
            auth_settings.oauth2_proxy_access_token_header
            == "X-Auth-Request-Access-Token"  # noqa: S105
        )

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        with patch.dict(
            os.environ,
            {
                "AUTH_SECRET_KEY": "test-secret",
                "AUTH_ALGORITHM": "RS256",
                "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
                "AUTH_OAUTH2_PROXY_ENABLED": "true",
            },
        ):
            auth_settings = AuthSettings()
            assert auth_settings.secret_key == "test-secret"  # noqa: S105
            assert auth_settings.algorithm == "RS256"
            assert auth_settings.access_token_expire_minutes == 60
            assert auth_settings.oauth2_proxy_enabled is True


class TestServerSettings:
    """Test ServerSettings configuration."""

    def test_default_values(self) -> None:
        """Test default server settings."""
        server_settings = ServerSettings()
        assert server_settings.host == "127.0.0.1"
        assert server_settings.port == 8000
        assert server_settings.workers == 1
        assert server_settings.reload is False
        assert server_settings.cors_origins == ["http://localhost:3000"]

    def test_cors_origins_factory(self) -> None:
        """Test CORS origins default factory."""
        server_settings1 = ServerSettings()
        server_settings2 = ServerSettings()

        # Should be separate lists
        assert (
            server_settings1.cors_origins is not server_settings2.cors_origins
        )
        assert server_settings1.cors_origins == server_settings2.cors_origins


class TestMkDocsSettings:
    """Test MkDocsSettings configuration."""

    def test_default_values(self) -> None:
        """Test default MkDocs settings."""
        mkdocs_settings = MkDocsSettings()
        assert mkdocs_settings.site_name == "FactFiber Documentation"
        assert mkdocs_settings.site_url == "https://docs.factfiber.ai"
        assert mkdocs_settings.theme == "material"
        assert mkdocs_settings.build_dir == "./build"
        assert mkdocs_settings.temp_dir == "./temp"


class TestLoggingSettings:
    """Test LoggingSettings configuration."""

    def test_default_values(self) -> None:
        """Test default logging settings."""
        logging_settings = LoggingSettings()
        assert logging_settings.level == "INFO"
        assert (
            logging_settings.format
            == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        assert logging_settings.file == ""


class TestMonitoringSettings:
    """Test MonitoringSettings configuration."""

    def test_default_values(self) -> None:
        """Test default monitoring settings."""
        monitoring_settings = MonitoringSettings()
        assert monitoring_settings.prometheus_enabled is True
        assert monitoring_settings.prometheus_port == 9090
        assert monitoring_settings.health_check_enabled is True


class TestSettings:
    """Test main Settings configuration."""

    def test_default_values(self) -> None:
        """Test default main settings."""
        app_settings = Settings()
        assert app_settings.environment == "development"
        assert app_settings.debug is False
        assert isinstance(app_settings.database, DatabaseSettings)
        assert isinstance(app_settings.github, GitHubSettings)
        assert isinstance(app_settings.auth, AuthSettings)
        assert isinstance(app_settings.server, ServerSettings)
        assert isinstance(app_settings.mkdocs, MkDocsSettings)
        assert isinstance(app_settings.logging, LoggingSettings)
        assert isinstance(app_settings.monitoring, MonitoringSettings)

    def test_is_development_property(self) -> None:
        """Test is_development property."""
        # Test development environment
        dev_settings = Settings(environment="development")
        assert dev_settings.is_development is True

        # Test dev shorthand
        dev_short_settings = Settings(environment="dev")
        assert dev_short_settings.is_development is True

        # Test non-development
        prod_settings = Settings(environment="production")
        assert prod_settings.is_development is False

    def test_is_production_property(self) -> None:
        """Test is_production property."""
        # Test production environment
        prod_settings = Settings(environment="production")
        assert prod_settings.is_production is True

        # Test prod shorthand
        prod_short_settings = Settings(environment="prod")
        assert prod_short_settings.is_production is True

        # Test non-production
        dev_settings = Settings(environment="development")
        assert dev_settings.is_production is False

    def test_model_dump_config(self) -> None:
        """Test MkDocs configuration export."""
        app_settings = Settings()
        config = app_settings.model_dump_config()

        assert config["site_name"] == "FactFiber Documentation"
        assert config["site_url"] == "https://docs.factfiber.ai"
        assert config["theme"] == {"name": "material"}
        assert "plugins" in config
        assert "markdown_extensions" in config

    def test_get_mkdocs_plugins_without_github_token(self) -> None:
        """Test MkDocs plugins without GitHub token."""
        app_settings = Settings()
        app_settings.github.token = ""  # Ensure no token

        plugins = app_settings._get_mkdocs_plugins()

        # Should not include multirepo plugin without token
        plugin_names = [next(iter(plugin.keys())) for plugin in plugins]
        assert "multirepo" not in plugin_names
        assert "search" in plugin_names
        assert "awesome-pages" in plugin_names

    def test_get_mkdocs_plugins_with_github_token(self) -> None:
        """Test MkDocs plugins with GitHub token."""
        app_settings = Settings()
        app_settings.github.token = "test-token"  # noqa: S105

        plugins = app_settings._get_mkdocs_plugins()

        # Should include multirepo plugin with token
        plugin_names = [next(iter(plugin.keys())) for plugin in plugins]
        assert "multirepo" in plugin_names

    def test_get_markdown_extensions(self) -> None:
        """Test Markdown extensions configuration."""
        app_settings = Settings()
        extensions = app_settings._get_markdown_extensions()

        # Check some key extensions
        assert "abbr" in extensions
        assert "admonition" in extensions
        assert "attr_list" in extensions

        # Check dictionary-based extensions
        extension_names: list[str] = []
        for ext in extensions:
            if isinstance(ext, dict):
                extension_names.extend(ext.keys())
            else:
                extension_names.append(ext)

        assert "toc" in extension_names
        assert "pymdownx.arithmatex" in extension_names
        assert "pymdownx.superfences" in extension_names


class TestGlobalSettings:
    """Test global settings instance."""

    def test_settings_instance(self) -> None:
        """Test global settings instance."""
        assert isinstance(settings, Settings)

    def test_get_settings_function(self) -> None:
        """Test get_settings function."""
        retrieved_settings = get_settings()
        assert retrieved_settings is settings
        assert isinstance(retrieved_settings, Settings)

    def test_settings_singleton_behavior(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
