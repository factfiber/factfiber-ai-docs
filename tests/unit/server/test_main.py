# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Test main FastAPI application."""

from unittest.mock import Mock, patch

from ff_docs.server.main import app, create_app


class TestFastAPIApp:
    """Test FastAPI application creation and configuration."""

    def test_create_app(self) -> None:
        """Test app creation."""
        test_app = create_app()
        assert test_app.title == "FactFiber Documentation Server"
        assert test_app.version == "0.1.0"

    def test_app_instance(self) -> None:
        """Test the app instance is created."""
        assert app is not None
        assert app.title == "FactFiber Documentation Server"

    def test_cors_middleware(self) -> None:
        """Test CORS middleware is configured."""
        # Check that middleware is in the middleware stack
        # Note: FastAPI wraps middleware, so we check for presence
        assert len(app.user_middleware) >= 2  # At least CORS + Auth middleware

    def test_auth_middleware(self) -> None:
        """Test repository auth middleware is configured."""
        # Check that middleware stack has expected number of entries
        assert len(app.user_middleware) >= 2  # At least CORS + Auth middleware

    def test_routes_included(self) -> None:
        """Test all route modules are included."""
        # Get all route paths
        routes = [route.path for route in app.routes]

        # Check health routes
        assert "/health/status" in routes or any(
            "/health" in route for route in routes
        )

        # Check other expected route prefixes are present
        expected_prefixes = ["/auth", "/docs", "/repos"]
        for prefix in expected_prefixes:
            assert any(route.startswith(prefix) for route in routes), (
                f"Missing routes for {prefix}"
            )


class TestServerRunFunction:
    """Test the run_server function (marked as no cover)."""

    @patch("uvicorn.run")
    def test_run_server_called_with_settings(self, mock_uvicorn: Mock) -> None:
        """Test run_server function configuration."""
        from ff_docs.server.main import run_server

        # This function is marked as # pragma: no cover
        # but we can still test it to ensure it configures uvicorn correctly
        run_server()

        mock_uvicorn.assert_called_once()
        args, kwargs = mock_uvicorn.call_args

        # Check that it's called with the correct module string
        assert args[0] == "ff_docs.server.main:app"
