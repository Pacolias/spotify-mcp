"""The OAuth authorization server MCP hosts (e.g. Claude) connect through.

The MCP SDK owns the HTTP side of OAuth #1 (/register, /authorize, /token,
/revoke, metadata, PKCE checks) and calls into this provider for everything
that needs storage or Spotify. Logging in here *is* connecting Spotify: our
/authorize chains into Spotify's login (OAuth #2), and the user comes back to
`complete_authorization`. See journal 41 and 42.

Spotify's tokens never leave the server; MCP clients only ever get our own.
"""

from datetime import UTC, datetime, timedelta

import httpx
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlmodel import Session, col, delete

from spotify_mcp.config import settings
from spotify_mcp.db import models
from spotify_mcp.db import session as db_session
from spotify_mcp.oauth.tokens import (
    ACCESS_TOKEN_LIFETIME_SECONDS,
    hash_token,
    issue_access_token,
    new_opaque_token,
    verify_access_token,
)
from spotify_mcp.spotify.auth import (
    _utcnow,
    build_authorize_url,
    complete_login,
    generate_code_challenge,
    generate_code_verifier,
)

# Lifetimes from journal 42, item 8.
PENDING_AUTHORIZATION_LIFETIME = timedelta(minutes=10)
AUTHORIZATION_CODE_LIFETIME = timedelta(minutes=5)
REFRESH_TOKEN_LIFETIME = timedelta(days=30)


class UnknownAuthorizationError(Exception):
    """Spotify sent the user back with a `state` we don't have (never issued,
    already used, or expired). There's no MCP client to redirect to, so the
    callback route has to show an error page itself."""


def _timestamp(value: datetime) -> int:
    return int(value.replace(tzinfo=UTC).timestamp())


def _same_resource(a: str, b: str) -> bool:
    return a.rstrip("/") == b.rstrip("/")


class SpotifyOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    # --- Client registration ------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with Session(db_session.engine) as session:
            row = session.get(models.OAuthClient, client_id)
        if row is None:
            return None
        return OAuthClientInformationFull.model_validate_json(row.client_info)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        # Stored as issued, client_secret included: the SDK's client
        # authentication compares the presented secret with get_client()'s.
        with Session(db_session.engine) as session:
            session.add(
                models.OAuthClient(
                    client_id=client_info.client_id,
                    client_info=client_info.model_dump_json(),
                    created_at=_utcnow(),
                )
            )
            session.commit()

    # --- Authorization: our /authorize -> Spotify -> back to the client -----

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Park the client's request and send the user to Spotify's login."""
        if params.resource is not None and not _same_resource(
            params.resource, settings.mcp_resource_url
        ):
            raise AuthorizeError(
                error="invalid_target",
                error_description="This server only issues tokens for its own MCP endpoint.",
            )

        state = new_opaque_token()
        code_verifier = generate_code_verifier()
        with Session(db_session.engine) as session:
            _purge_expired(session)
            session.add(
                models.PendingAuthorization(
                    state=state,
                    client_id=client.client_id,
                    client_state=params.state,
                    redirect_uri=str(params.redirect_uri),
                    redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
                    code_challenge=params.code_challenge,
                    scopes=" ".join(params.scopes or []),
                    resource=params.resource,
                    spotify_code_verifier=code_verifier,
                    expires_at=_utcnow() + PENDING_AUTHORIZATION_LIFETIME,
                )
            )
            session.commit()
        return build_authorize_url(state, generate_code_challenge(code_verifier))

    async def complete_authorization(
        self, state: str, code: str | None = None, error: str | None = None
    ) -> str:
        """Handle Spotify's redirect back to us. Returns the URL to send the
        user to: the MCP client's redirect_uri, with our authorization code on
        success or an OAuth error otherwise.

        Called by the Spotify callback route, which gets wired up together
        with the HTTP transport.
        """
        with Session(db_session.engine) as session:
            pending = session.get(models.PendingAuthorization, state)
            if pending is not None:
                # Single use, whatever happens next.
                session.delete(pending)
                session.commit()
        if pending is None or pending.expires_at <= _utcnow():
            raise UnknownAuthorizationError("Unknown or expired login attempt.")

        redirect_uri, client_state = pending.redirect_uri, pending.client_state

        def back_to_client(**params: str | None) -> str:
            return construct_redirect_uri(redirect_uri, state=client_state, **params)

        if error or not code:
            # Typically the user pressed "Cancel" on Spotify's consent screen.
            return back_to_client(
                error="access_denied", error_description="Spotify login was not completed."
            )

        try:
            user_id = await complete_login(code, pending.spotify_code_verifier)
        except httpx.HTTPError:
            return back_to_client(
                error="server_error", error_description="Could not complete the Spotify login."
            )

        our_code = new_opaque_token()
        with Session(db_session.engine) as session:
            session.add(
                models.AuthorizationCode(
                    code_hash=hash_token(our_code),
                    client_id=pending.client_id,
                    user_id=user_id,
                    redirect_uri=pending.redirect_uri,
                    redirect_uri_provided_explicitly=pending.redirect_uri_provided_explicitly,
                    code_challenge=pending.code_challenge,
                    scopes=pending.scopes,
                    resource=pending.resource,
                    expires_at=_utcnow() + AUTHORIZATION_CODE_LIFETIME,
                )
            )
            session.commit()
        return back_to_client(code=our_code)

    # --- Token endpoint: authorization code grant ---------------------------

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        # Expiry and PKCE are checked by the SDK's token handler.
        with Session(db_session.engine) as session:
            row = session.get(models.AuthorizationCode, hash_token(authorization_code))
        if row is None or row.client_id != client.client_id:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=row.scopes.split(),
            expires_at=_timestamp(row.expires_at),
            client_id=row.client_id,
            code_challenge=row.code_challenge,
            redirect_uri=row.redirect_uri,
            redirect_uri_provided_explicitly=row.redirect_uri_provided_explicitly,
            resource=row.resource,
            subject=row.user_id,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        with Session(db_session.engine) as session:
            # Deleting is what makes the code single-use: a second exchange
            # (replay, or a concurrent request) finds nothing to delete.
            result = session.exec(
                delete(models.AuthorizationCode).where(
                    col(models.AuthorizationCode.code_hash) == hash_token(authorization_code.code)
                )
            )
            if result.rowcount != 1:
                raise TokenError(error="invalid_grant", error_description="Code already used.")
            assert authorization_code.subject is not None
            tokens = _issue_tokens(
                session,
                client_id=client.client_id,
                user_id=authorization_code.subject,
                scopes=authorization_code.scopes,
                resource=authorization_code.resource,
            )
            session.commit()
        return tokens

    # --- Token endpoint: refresh token grant --------------------------------

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        # Expiry is checked by the SDK's token handler.
        with Session(db_session.engine) as session:
            row = session.get(models.RefreshToken, hash_token(refresh_token))
            if row is None or row.client_id != client.client_id:
                return None
            if row.rotated_at is not None:
                # An already-rotated token came back: someone else holds a
                # copy of it. Revoke the whole grant so neither copy works.
                _revoke_grant(session, user_id=row.user_id, client_id=row.client_id)
                session.commit()
                return None
        return RefreshToken(
            token=refresh_token,
            client_id=row.client_id,
            scopes=row.scopes.split(),
            expires_at=_timestamp(row.expires_at),
            resource=row.resource,
            subject=row.user_id,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        with Session(db_session.engine) as session:
            row = session.get(models.RefreshToken, hash_token(refresh_token.token))
            if row is None or row.rotated_at is not None:
                raise TokenError(error="invalid_grant", error_description="Refresh token revoked.")
            row.rotated_at = _utcnow()
            session.add(row)
            tokens = _issue_tokens(
                session,
                client_id=client.client_id,
                user_id=row.user_id,
                scopes=scopes,
                resource=row.resource,
            )
            session.commit()
        return tokens

    # --- Every MCP request, and revocation ----------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        # Signature only, no database (journal 42, decision 2c).
        return verify_access_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Revoke the user's grant to this client, whichever token is given.

        Their refresh tokens stop working at once. An access token (a JWT)
        stays valid until it expires, at most an hour (journal 42, decision 2c).
        """
        if token.subject is None:
            return
        with Session(db_session.engine) as session:
            _revoke_grant(session, user_id=token.subject, client_id=token.client_id)
            session.commit()


def _issue_tokens(
    session: Session, *, client_id: str, user_id: str, scopes: list[str], resource: str | None
) -> OAuthToken:
    """A new JWT access token plus a new refresh token (stored hashed).
    Adds to `session`; the caller commits."""
    access_token, _ = issue_access_token(user_id, client_id, scopes)
    refresh_token = new_opaque_token()
    session.add(
        models.RefreshToken(
            token_hash=hash_token(refresh_token),
            client_id=client_id,
            user_id=user_id,
            scopes=" ".join(scopes),
            resource=resource,
            expires_at=_utcnow() + REFRESH_TOKEN_LIFETIME,
        )
    )
    return OAuthToken(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
        scope=" ".join(scopes) or None,
        refresh_token=refresh_token,
    )


def _revoke_grant(session: Session, *, user_id: str, client_id: str) -> None:
    session.exec(
        delete(models.RefreshToken).where(
            col(models.RefreshToken.user_id) == user_id,
            col(models.RefreshToken.client_id) == client_id,
        )
    )


def _purge_expired(session: Session) -> None:
    """Drop rows that can no longer be used, so the tables don't grow forever."""
    now = _utcnow()
    for model in (models.PendingAuthorization, models.AuthorizationCode, models.RefreshToken):
        session.exec(delete(model).where(col(model.expires_at) <= now))
