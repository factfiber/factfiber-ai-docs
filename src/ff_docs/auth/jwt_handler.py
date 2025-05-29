# Copyright 2025 Fact Fiber Inc. All rights reserved.

"""JWT token handling and validation."""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError

from ff_docs.auth.models import TokenData, User, UserSession
from ff_docs.config.settings import get_settings

logger = logging.getLogger(__name__)

# Constants
BEARER_TOKEN_PARTS = 2
JWT_TOKEN_PARTS = 3


class JWTHandler:
    """JWT token handler for authentication."""

    def __init__(self) -> None:
        """Initialize JWT handler with settings."""
        self.settings = get_settings()
        self.secret_key = self.settings.auth.secret_key
        self.algorithm = self.settings.auth.algorithm
        self.access_token_expire_minutes = (
            self.settings.auth.access_token_expire_minutes
        )

    def create_access_token(
        self,
        user: User,
        session_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a new JWT access token."""
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        # Create token payload
        to_encode = {
            "sub": user.username,
            "username": user.username,
            "email": user.email,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "iss": "ff-docs",
            "aud": "ff-docs-api",
        }

        # Encode the JWT token
        encoded_jwt = jwt.encode(
            to_encode, self.secret_key, algorithm=self.algorithm
        )
        logger.info("Created access token for user: %s", user.username)
        return encoded_jwt

    def verify_token(self, token: str) -> TokenData | None:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="ff-docs-api",
            )

            username: str = payload.get("sub")
            if username is None:
                logger.warning("Token missing subject (username)")
                return None

            # Extract token data
            token_data = TokenData(
                username=username,
                sub=payload.get("sub", ""),
                exp=payload.get("exp", 0),
                iat=payload.get("iat", 0),
                session_id=payload.get("session_id", ""),
            )

            # Check if token is expired
            if datetime.fromtimestamp(token_data.exp, tz=UTC) < datetime.now(
                UTC
            ):
                logger.warning("Token expired for user: %s", username)
                return None

        except InvalidTokenError as e:
            logger.warning("Invalid token: %s", e)
            return None
        except Exception:
            logger.exception("Error verifying token")
            return None
        else:
            logger.debug("Successfully verified token for user: %s", username)
            return token_data

    def refresh_token(self, token: str, session: UserSession) -> str | None:
        """Refresh an access token if valid and not expired."""
        token_data = self.verify_token(token)
        if not token_data:
            return None

        # Verify session ID matches
        if token_data.session_id != session.session_id:
            logger.warning(
                "Session ID mismatch for user: %s", token_data.username
            )
            return None

        # Create new token with same session
        new_token = self.create_access_token(session.user, session.session_id)
        logger.info("Refreshed token for user: %s", session.user.username)
        return new_token

    def extract_token_from_header(
        self, authorization: str | None
    ) -> str | None:
        """Extract JWT token from Authorization header."""
        if not authorization:
            return None

        # Check for Bearer token format
        parts = authorization.split()
        if len(parts) != BEARER_TOKEN_PARTS or parts[0].lower() != "bearer":
            logger.warning("Invalid authorization header format")
            return None

        return parts[1]

    def get_token_expiry(self, token: str) -> datetime | None:
        """Get the expiration time of a JWT token."""
        try:
            # Decode without verification to get expiry
            payload = jwt.decode(
                token, options={"verify_signature": False, "verify_exp": False}
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=UTC)
        except Exception:
            logger.exception("Error extracting token expiry")
            return None
        else:
            return None

    def validate_token_format(self, token: str) -> bool:
        """Validate that a token has the correct JWT format."""
        try:
            # Basic format check - JWT should have 3 parts separated by dots
            parts = token.split(".")
            if len(parts) != JWT_TOKEN_PARTS:
                return False

            # Try to decode header and payload (without verification)
            jwt.decode(
                token, options={"verify_signature": False, "verify_exp": False}
            )
        except (jwt.DecodeError, ValueError):
            return False
        else:
            return True
