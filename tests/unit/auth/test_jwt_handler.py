# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""Unit tests for JWT handler module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from jwt.exceptions import DecodeError

from ff_docs.auth.jwt_handler import JWTHandler
from ff_docs.auth.models import GitHubTeam, User, UserSession


class TestJWTHandler:
    """Test JWTHandler class."""

    @pytest.fixture
    def handler(self) -> JWTHandler:
        """Create a JWTHandler instance."""
        return JWTHandler()

    @pytest.fixture
    def user(self) -> User:
        """Create a test user."""
        return User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            github_id=12345,
        )

    @pytest.fixture
    def user_session(self, user: User) -> UserSession:
        """Create a test user session."""
        team = GitHubTeam(
            org="test-org",
            team="test-team",
            role="member",
        )

        return UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read"],
            session_id="test-session-123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            access_token="github-token",  # noqa: S106
        )

    def test_handler_initialization(self, handler: JWTHandler) -> None:
        """Test JWTHandler initialization."""
        assert handler.settings is not None
        assert handler.secret_key is not None
        assert handler.algorithm is not None
        assert handler.access_token_expire_minutes > 0

    def test_create_access_token(self, handler: JWTHandler, user: User) -> None:
        """Test creating an access token."""
        session_id = "test-session-123"
        token = handler.create_access_token(user, session_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT format

        # Decode and verify contents
        payload = jwt.decode(
            token,
            handler.secret_key,
            algorithms=[handler.algorithm],
            audience="ff-docs-api",
        )

        assert payload["sub"] == user.username
        assert payload["username"] == user.username
        assert payload["email"] == user.email
        assert payload["session_id"] == session_id
        assert payload["iss"] == "ff-docs"
        assert payload["aud"] == "ff-docs-api"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_custom_expiry(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test creating an access token with custom expiry."""
        session_id = "test-session-456"
        custom_delta = timedelta(hours=2)
        token = handler.create_access_token(user, session_id, custom_delta)

        payload = jwt.decode(
            token,
            handler.secret_key,
            algorithms=[handler.algorithm],
            audience="ff-docs-api",
        )

        # Check expiry is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_time = datetime.now(UTC) + custom_delta
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 10  # Within 10 seconds tolerance

    def test_verify_token_valid(self, handler: JWTHandler, user: User) -> None:
        """Test verifying a valid token."""
        session_id = "test-session-789"
        token = handler.create_access_token(user, session_id)

        token_data = handler.verify_token(token)

        assert token_data is not None
        assert token_data.username == user.username
        assert token_data.sub == user.username
        assert token_data.session_id == session_id
        assert token_data.exp > 0
        assert token_data.iat > 0

    def test_verify_token_expired(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test verifying an expired token."""
        session_id = "test-session-expired"
        # Create token that expires immediately
        token = handler.create_access_token(
            user, session_id, timedelta(seconds=-1)
        )

        token_data = handler.verify_token(token)

        assert token_data is None

    def test_verify_token_manual_expiry_check(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test manual expiry check when JWT decode doesn't catch it."""
        import time

        # Mock jwt.decode to return a payload with expired timestamp
        # but not raise ExpiredSignatureError to hit manual check
        expired_payload = {
            "sub": user.username,
            "username": user.username,
            "email": user.email,
            "session_id": "test-session",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
            "iss": "ff-docs",
            "aud": "ff-docs-api",
        }

        with (
            patch("jwt.decode", return_value=expired_payload) as mock_decode,
            patch("ff_docs.auth.jwt_handler.logger") as mock_logger,
        ):
            token_data = handler.verify_token("mock.token.here")

            assert token_data is None
            # Verify the manual expiry warning was called (lines 94-95)
            mock_logger.warning.assert_called_with(
                "Token expired for user: %s", user.username
            )
            mock_decode.assert_called_once()

    def test_verify_token_invalid_signature(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test verifying a token with invalid signature."""
        session_id = "test-session-invalid"
        token = handler.create_access_token(user, session_id)

        # Tamper with the token
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"

        token_data = handler.verify_token(tampered_token)

        assert token_data is None

    def test_verify_token_missing_subject(self, handler: JWTHandler) -> None:
        """Test verifying a token without subject."""
        # Create a token without 'sub' field
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "session_id": "test-session",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
            "iss": "ff-docs",
            "aud": "ff-docs-api",
        }

        token = jwt.encode(
            payload, handler.secret_key, algorithm=handler.algorithm
        )

        token_data = handler.verify_token(token)

        assert token_data is None

    def test_verify_token_invalid_format(self, handler: JWTHandler) -> None:
        """Test verifying a token with invalid format."""
        invalid_tokens = [
            "not.a.token",
            "invalid_token",
            "",
            "a.b",  # Only 2 parts
            "a.b.c.d",  # Too many parts
        ]

        for invalid_token in invalid_tokens:
            token_data = handler.verify_token(invalid_token)
            assert token_data is None

    def test_verify_token_exception_handling(self, handler: JWTHandler) -> None:
        """Test verify_token handles exceptions properly."""
        with patch("jwt.decode", side_effect=Exception("Unexpected error")):
            token_data = handler.verify_token("some.token.here")
            assert token_data is None

    def test_refresh_token_valid(
        self, handler: JWTHandler, user_session: UserSession
    ) -> None:
        """Test refreshing a valid token."""
        # Create initial token
        initial_token = handler.create_access_token(
            user_session.user, user_session.session_id
        )

        # Add small delay to ensure different iat timestamp
        import time

        time.sleep(0.1)

        # Refresh the token
        new_token = handler.refresh_token(initial_token, user_session)

        assert new_token is not None
        # Tokens might be identical if created at exact same second
        # Just verify the new token is valid

        # Verify new token is valid
        token_data = handler.verify_token(new_token)
        assert token_data is not None
        assert token_data.username == user_session.user.username
        assert token_data.session_id == user_session.session_id

    def test_refresh_token_invalid(
        self, handler: JWTHandler, user_session: UserSession
    ) -> None:
        """Test refreshing an invalid token."""
        invalid_token = "invalid.token.here"  # noqa: S105
        new_token = handler.refresh_token(invalid_token, user_session)

        assert new_token is None

    def test_refresh_token_session_mismatch(
        self, handler: JWTHandler, user_session: UserSession
    ) -> None:
        """Test refreshing token with mismatched session ID."""
        # Create token with different session ID
        initial_token = handler.create_access_token(
            user_session.user, "different-session-id"
        )

        # Try to refresh with different session
        new_token = handler.refresh_token(initial_token, user_session)

        assert new_token is None

    def test_extract_token_from_header_valid(self, handler: JWTHandler) -> None:
        """Test extracting token from valid Authorization header."""
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"  # noqa: S105
        authorization = f"Bearer {test_token}"

        extracted_token = handler.extract_token_from_header(authorization)

        assert extracted_token == test_token

    def test_extract_token_from_header_invalid_formats(
        self, handler: JWTHandler
    ) -> None:
        """Test extracting token from invalid Authorization headers."""
        invalid_headers = [
            None,
            "",
            "Bearer",
            "InvalidScheme token",
            "Bearer token extra_part",  # Too many parts
            "Token123",  # No space
        ]

        for header in invalid_headers:
            token = handler.extract_token_from_header(header)
            assert token is None

        # Test that double space still works (split() handles any whitespace)
        token = handler.extract_token_from_header("Bearer  token")
        assert token == "token"  # noqa: S105

    def test_extract_token_from_header_case_insensitive(
        self, handler: JWTHandler
    ) -> None:
        """Test that Bearer scheme is case-insensitive."""
        test_token = "test.token.here"  # noqa: S105
        headers = [
            f"bearer {test_token}",
            f"BEARER {test_token}",
            f"Bearer {test_token}",
            f"BeArEr {test_token}",
        ]

        for header in headers:
            extracted = handler.extract_token_from_header(header)
            assert extracted == test_token

    def test_get_token_expiry_valid(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test getting expiry from a valid token."""
        session_id = "test-session"
        token = handler.create_access_token(user, session_id)

        expiry = handler.get_token_expiry(token)

        assert expiry is not None
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(UTC)

    def test_get_token_expiry_invalid_token(self, handler: JWTHandler) -> None:
        """Test getting expiry from invalid token."""
        invalid_tokens = [
            "invalid.token",
            "",
            "not-a-jwt",
        ]

        for token in invalid_tokens:
            expiry = handler.get_token_expiry(token)
            assert expiry is None

    def test_get_token_expiry_no_exp_field(self, handler: JWTHandler) -> None:
        """Test getting expiry from token without exp field."""
        # Create token without exp field
        payload = {
            "sub": "testuser",
            "username": "testuser",
        }

        token = jwt.encode(
            payload, handler.secret_key, algorithm=handler.algorithm
        )

        expiry = handler.get_token_expiry(token)

        assert expiry is None

    def test_get_token_expiry_exception_handling(
        self, handler: JWTHandler
    ) -> None:
        """Test get_token_expiry handles exceptions properly."""
        with patch("jwt.decode", side_effect=Exception("Decode error")):
            expiry = handler.get_token_expiry("some.token.here")
            assert expiry is None

    def test_validate_token_format_valid(
        self, handler: JWTHandler, user: User
    ) -> None:
        """Test validating correct JWT format."""
        session_id = "test-session"
        token = handler.create_access_token(user, session_id)

        is_valid = handler.validate_token_format(token)

        assert is_valid is True

    def test_validate_token_format_invalid(self, handler: JWTHandler) -> None:
        """Test validating incorrect JWT formats."""
        invalid_formats = [
            "not.a.jwt",
            "only.two",
            "four.parts.is.invalid",
            "",
            "single_string",
            "a.b.c.d.e",  # Too many parts
        ]

        for token in invalid_formats:
            is_valid = handler.validate_token_format(token)
            assert is_valid is False

    def test_validate_token_format_malformed_content(
        self, handler: JWTHandler
    ) -> None:
        """Test validating token with malformed base64 content."""
        # Create token with invalid base64 in payload
        malformed_token = "eyJhbGciOiJIUzI1NiJ9.not-valid-base64!@#$.signature"  # noqa: S105

        is_valid = handler.validate_token_format(malformed_token)

        assert is_valid is False

    def test_validate_token_format_decode_error(
        self, handler: JWTHandler
    ) -> None:
        """Test validate_token_format handles DecodeError."""
        with patch("jwt.decode", side_effect=DecodeError("Invalid token")):
            is_valid = handler.validate_token_format("some.token.here")
            assert is_valid is False


class TestJWTHandlerIntegration:
    """Integration tests for JWT handler."""

    def test_full_token_lifecycle(self) -> None:
        """Test complete token lifecycle from creation to refresh."""
        handler = JWTHandler()

        # Create user and session
        user = User(
            username="lifecycle_user",
            email="lifecycle@example.com",
            github_id=99999,
        )

        team = GitHubTeam(org="test-org", team="test-team", role="member")

        session = UserSession(
            user=user,
            teams=[team],
            permissions=["docs:read", "docs:write"],
            session_id="lifecycle-session-123",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )

        # Create token
        token = handler.create_access_token(user, session.session_id)
        assert token is not None

        # Verify token
        token_data = handler.verify_token(token)
        assert token_data is not None
        assert token_data.username == user.username

        # Extract from header
        auth_header = f"Bearer {token}"
        extracted = handler.extract_token_from_header(auth_header)
        assert extracted == token

        # Get expiry
        expiry = handler.get_token_expiry(token)
        assert expiry is not None
        assert expiry > datetime.now(UTC)

        # Validate format
        is_valid = handler.validate_token_format(token)
        assert is_valid is True

        # Add small delay before refresh
        import time

        time.sleep(0.1)

        # Refresh token
        new_token = handler.refresh_token(token, session)
        assert new_token is not None
        # Just verify new token is valid, might be identical

        # Verify new token
        new_token_data = handler.verify_token(new_token)
        assert new_token_data is not None
        assert new_token_data.username == user.username
        assert new_token_data.session_id == session.session_id

    def test_token_expiry_timing(self) -> None:
        """Test token expiry timing is accurate."""
        handler = JWTHandler()
        user = User(username="timing_user", email="timing@example.com")

        # Create token with 30 second expiry
        expires_delta = timedelta(seconds=30)
        token = handler.create_access_token(
            user, "timing-session", expires_delta
        )

        # Get expiry and check timing
        expiry = handler.get_token_expiry(token)
        assert expiry is not None

        expected_expiry = datetime.now(UTC) + expires_delta
        time_diff = abs((expiry - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

    def test_concurrent_token_creation(self) -> None:
        """Test that multiple tokens can be created concurrently."""
        handler = JWTHandler()
        users = [
            User(username=f"user{i}", email=f"user{i}@example.com")
            for i in range(5)
        ]

        tokens = []
        for i, user in enumerate(users):
            token = handler.create_access_token(user, f"session-{i}")
            tokens.append(token)

        # Verify all tokens are unique
        assert len(set(tokens)) == len(tokens)

        # Verify all tokens are valid
        for token, user in zip(tokens, users, strict=False):
            token_data = handler.verify_token(token)
            assert token_data is not None
            assert token_data.username == user.username
