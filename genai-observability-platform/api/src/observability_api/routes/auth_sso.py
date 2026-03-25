"""
SSO Authentication Routes

Provides OAuth2/OIDC and SAML authentication endpoints.
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..config import get_settings
from ..auth_providers import (
    AuthManager,
    AuthProvider,
    OIDCConfig,
    SAMLConfig,
    UserInfo,
    create_google_provider,
    create_okta_provider,
    create_azure_ad_provider,
    generate_pkce_pair,
)

router = APIRouter()

# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create the auth manager."""
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = AuthManager()
        settings = get_settings()

        # Register configured providers
        if settings.google_client_id:
            _auth_manager.register_oidc_provider(
                AuthProvider.GOOGLE,
                OIDCConfig(
                    provider=AuthProvider.GOOGLE,
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                    issuer="https://accounts.google.com",
                    discovery_url="https://accounts.google.com/.well-known/openid-configuration",
                    redirect_uri=f"{settings.api_base_url}/auth/callback/google",
                ),
            )

        if settings.okta_domain:
            _auth_manager.register_oidc_provider(
                AuthProvider.OKTA,
                OIDCConfig(
                    provider=AuthProvider.OKTA,
                    client_id=settings.okta_client_id,
                    client_secret=settings.okta_client_secret,
                    issuer=f"https://{settings.okta_domain}",
                    discovery_url=f"https://{settings.okta_domain}/.well-known/openid-configuration",
                    redirect_uri=f"{settings.api_base_url}/auth/callback/okta",
                    groups_claim="groups",
                ),
            )

        if settings.azure_tenant_id:
            _auth_manager.register_oidc_provider(
                AuthProvider.AZURE_AD,
                OIDCConfig(
                    provider=AuthProvider.AZURE_AD,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret,
                    issuer=f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0",
                    discovery_url=f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0/.well-known/openid-configuration",
                    redirect_uri=f"{settings.api_base_url}/auth/callback/azure",
                ),
            )

        if settings.auth0_domain:
            _auth_manager.register_oidc_provider(
                AuthProvider.AUTH0,
                OIDCConfig(
                    provider=AuthProvider.AUTH0,
                    client_id=settings.auth0_client_id,
                    client_secret=settings.auth0_client_secret,
                    issuer=f"https://{settings.auth0_domain}/",
                    discovery_url=f"https://{settings.auth0_domain}/.well-known/openid-configuration",
                    redirect_uri=f"{settings.api_base_url}/auth/callback/auth0",
                ),
            )

        if settings.saml_idp_entity_id:
            _auth_manager.register_saml_provider(
                "default",
                SAMLConfig(
                    entity_id=settings.saml_idp_entity_id,
                    sso_url=settings.saml_sso_url,
                    slo_url=settings.saml_slo_url,
                    certificate=settings.saml_certificate,
                    sp_entity_id=settings.saml_sp_entity_id,
                    sp_acs_url=f"{settings.api_base_url}/auth/callback/saml",
                ),
            )

    return _auth_manager


# Pydantic models
class LoginResponse(BaseModel):
    """Login initiation response."""
    login_url: str
    state: str


class TokenResponse(BaseModel):
    """Token response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: dict


class UserInfoResponse(BaseModel):
    """User information response."""
    user_id: str
    email: str
    name: str
    picture: str = ""
    provider: str
    roles: list
    groups: list


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class ProvidersResponse(BaseModel):
    """Available authentication providers."""
    providers: list


# Routes
@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> ProvidersResponse:
    """List available authentication providers."""
    providers = []

    for provider in auth_manager.oidc_providers:
        providers.append({
            "id": provider.value,
            "name": provider.value.replace("_", " ").title(),
            "type": "oidc",
        })

    for name in auth_manager.saml_providers:
        providers.append({
            "id": f"saml:{name}",
            "name": f"SAML ({name})",
            "type": "saml",
        })

    return ProvidersResponse(providers=providers)


@router.get("/login/{provider}")
async def initiate_login(
    provider: str,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
    redirect_uri: str = Query(None, description="Post-login redirect URI"),
    request: Request = None,
) -> RedirectResponse:
    """
    Initiate SSO login flow.

    Redirects user to the identity provider for authentication.
    """
    settings = get_settings()

    # Determine callback URI
    callback_uri = redirect_uri or f"{settings.frontend_url}/auth/callback"

    try:
        # Handle SAML provider
        if provider.startswith("saml:"):
            saml_name = provider.split(":")[1]
            login_url, state = auth_manager.get_login_url(saml_name, callback_uri)
        else:
            # OIDC provider
            auth_provider = AuthProvider(provider)
            login_url, state = auth_manager.get_login_url(auth_provider, callback_uri)

        # Store redirect URI in cookie
        response = RedirectResponse(url=login_url, status_code=302)
        response.set_cookie(
            key="auth_redirect",
            value=callback_uri,
            max_age=600,  # 10 minutes
            httponly=True,
            secure=True,
            samesite="lax",
        )
        response.set_cookie(
            key="auth_state",
            value=state,
            max_age=600,
            httponly=True,
            secure=True,
            samesite="lax",
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/login/{provider}/url", response_model=LoginResponse)
async def get_login_url(
    provider: str,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
    redirect_uri: str = Query(..., description="Post-login redirect URI"),
) -> LoginResponse:
    """
    Get login URL without redirecting.

    Useful for SPAs that need to handle the redirect themselves.
    """
    try:
        if provider.startswith("saml:"):
            saml_name = provider.split(":")[1]
            login_url, state = auth_manager.get_login_url(saml_name, redirect_uri)
        else:
            auth_provider = AuthProvider(provider)
            login_url, state = auth_manager.get_login_url(auth_provider, redirect_uri)

        return LoginResponse(login_url=login_url, state=state)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/{provider}")
async def handle_callback(
    provider: str,
    request: Request,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> RedirectResponse:
    """
    Handle OAuth2/OIDC callback from identity provider.
    """
    settings = get_settings()

    # Check for error
    if error:
        error_msg = f"{error}: {error_description}" if error_description else error
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={error_msg}",
            status_code=302,
        )

    # Get callback parameters
    params = dict(request.query_params)

    try:
        # Handle authentication
        auth_provider = AuthProvider(provider)
        user_info = auth_manager.handle_callback(auth_provider, params)

        # Create session token
        access_token = auth_manager.create_session_token(
            user_info,
            settings.jwt_secret_key,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

        # Get redirect URI from cookie
        redirect_uri = request.cookies.get("auth_redirect", settings.frontend_url)

        # Redirect with token
        response = RedirectResponse(
            url=f"{redirect_uri}?token={access_token}",
            status_code=302,
        )

        # Clear auth cookies
        response.delete_cookie("auth_redirect")
        response.delete_cookie("auth_state")

        # Set session cookie
        response.set_cookie(
            key="session",
            value=access_token,
            max_age=settings.jwt_expiration_hours * 3600,
            httponly=True,
            secure=True,
            samesite="lax",
        )

        return response

    except Exception as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={str(e)}",
            status_code=302,
        )


@router.post("/callback/{provider}", response_model=TokenResponse)
async def handle_callback_post(
    provider: str,
    request: Request,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> TokenResponse:
    """
    Handle callback via POST (for SAML and API clients).
    """
    settings = get_settings()

    # Get form data for SAML or JSON for API
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        params = dict(form_data)
    else:
        params = await request.json()

    try:
        # Handle SAML response
        if provider == "saml" or "SAMLResponse" in params:
            saml_name = params.get("saml_provider", "default")
            user_info = auth_manager.handle_callback(saml_name, params)
        else:
            # OIDC response
            auth_provider = AuthProvider(provider)
            user_info = auth_manager.handle_callback(auth_provider, params)

        # Create tokens
        access_token = auth_manager.create_session_token(
            user_info,
            settings.jwt_secret_key,
            expires_in=settings.jwt_expiration_hours * 3600,
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_expiration_hours * 3600,
            refresh_token=user_info.refresh_token or None,
            user={
                "user_id": user_info.user_id,
                "email": user_info.email,
                "name": user_info.name,
                "provider": user_info.provider.value,
                "roles": user_info.roles,
                "groups": user_info.groups,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> TokenResponse:
    """
    Refresh an access token using a refresh token.
    """
    settings = get_settings()

    # Note: This requires storing provider info with the refresh token
    # In a production system, you'd need to track which provider issued the token

    raise HTTPException(
        status_code=501,
        detail="Token refresh requires provider-specific implementation",
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    request: Request,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> UserInfoResponse:
    """
    Get current user information from session.
    """
    settings = get_settings()

    # Get token from cookie or header
    token = request.cookies.get("session")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_info = auth_manager.validate_session_token(token, settings.jwt_secret_key)

        return UserInfoResponse(
            user_id=user_info.user_id,
            email=user_info.email,
            name=user_info.name,
            picture=user_info.picture,
            provider=user_info.provider.value,
            roles=user_info.roles,
            groups=user_info.groups,
        )

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
    initiate_slo: bool = Query(False, description="Initiate SAML Single Logout"),
    revoke_tokens: bool = Query(True, description="Revoke OIDC tokens if supported"),
) -> dict:
    """
    Log out the current user.

    Supports:
    - SAML Single Logout (SLO) when initiate_slo=True
    - OIDC token revocation when revoke_tokens=True
    """
    settings = get_settings()
    slo_url = None
    tokens_revoked = False

    # Get current session info
    token = request.cookies.get("session")
    user_info = None

    if token:
        try:
            user_info = auth_manager.validate_session_token(token, settings.jwt_secret_key)
        except Exception:
            pass  # Session already invalid

    # Handle OIDC token revocation
    if user_info and revoke_tokens and user_info.refresh_token:
        try:
            tokens_revoked = await _revoke_oidc_tokens(
                auth_manager,
                user_info.provider,
                user_info.access_token,
                user_info.refresh_token,
            )
        except Exception as e:
            # Log but don't fail logout
            pass

    # Handle SAML Single Logout
    if user_info and initiate_slo and user_info.provider.value.startswith("saml"):
        try:
            slo_url = _get_saml_logout_url(
                auth_manager,
                user_info,
                settings.frontend_url,
            )
        except Exception as e:
            # Log but don't fail logout
            pass

    # Clear session cookie
    response.delete_cookie("session")
    response.delete_cookie("auth_redirect")
    response.delete_cookie("auth_state")

    result = {"message": "Logged out successfully"}

    if tokens_revoked:
        result["tokens_revoked"] = True

    if slo_url:
        result["slo_redirect"] = slo_url

    return result


async def _revoke_oidc_tokens(
    auth_manager: AuthManager,
    provider: "AuthProvider",
    access_token: Optional[str],
    refresh_token: Optional[str],
) -> bool:
    """
    Revoke OIDC tokens at the identity provider.

    Args:
        auth_manager: The auth manager instance
        provider: The OIDC provider
        access_token: The access token to revoke
        refresh_token: The refresh token to revoke

    Returns:
        True if tokens were revoked successfully
    """
    import urllib.request
    import urllib.error
    import urllib.parse

    oidc_config = auth_manager._oidc_configs.get(provider)
    if not oidc_config:
        return False

    # Get revocation endpoint from discovery
    revocation_endpoint = None

    # Common revocation endpoints by provider
    revocation_endpoints = {
        AuthProvider.GOOGLE: "https://oauth2.googleapis.com/revoke",
        AuthProvider.OKTA: f"{oidc_config.issuer}/oauth2/v1/revoke",
        AuthProvider.AZURE_AD: f"{oidc_config.issuer}/oauth2/v2.0/logout",
        AuthProvider.AUTH0: f"{oidc_config.issuer}oauth/revoke",
    }

    revocation_endpoint = revocation_endpoints.get(provider)
    if not revocation_endpoint:
        return False

    tokens_to_revoke = []
    if refresh_token:
        tokens_to_revoke.append(("refresh_token", refresh_token))
    if access_token:
        tokens_to_revoke.append(("access_token", access_token))

    success = True
    for token_type, token_value in tokens_to_revoke:
        try:
            data = urllib.parse.urlencode({
                "token": token_value,
                "token_type_hint": token_type,
                "client_id": oidc_config.client_id,
                "client_secret": oidc_config.client_secret,
            }).encode()

            req = urllib.request.Request(
                revocation_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status not in [200, 204]:
                    success = False
        except Exception:
            success = False

    return success


def _get_saml_logout_url(
    auth_manager: AuthManager,
    user_info: "UserInfo",
    return_url: str,
) -> Optional[str]:
    """
    Generate SAML Single Logout URL.

    Args:
        auth_manager: The auth manager instance
        user_info: The current user info
        return_url: URL to return to after logout

    Returns:
        The SLO URL to redirect to, or None if SLO is not configured
    """
    import base64
    import urllib.parse
    import zlib
    from datetime import datetime
    import uuid

    # Get SAML config
    saml_name = user_info.provider.value.replace("saml:", "")
    saml_config = auth_manager._saml_configs.get(saml_name)

    if not saml_config or not saml_config.slo_url:
        return None

    # Build LogoutRequest
    request_id = f"_logout_{uuid.uuid4().hex}"
    issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{saml_config.slo_url}">
    <saml:Issuer>{saml_config.sp_entity_id}</saml:Issuer>
    <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
        {user_info.email}
    </saml:NameID>
</samlp:LogoutRequest>"""

    # Compress and encode
    compressed = zlib.compress(logout_request.encode())[2:-4]  # Remove zlib header/trailer
    encoded = base64.b64encode(compressed).decode()

    # Build URL with query parameters
    params = urllib.parse.urlencode({
        "SAMLRequest": encoded,
        "RelayState": return_url,
    })

    return f"{saml_config.slo_url}?{params}"


@router.get("/logout/saml")
async def saml_logout_redirect(
    request: Request,
    response: Response,
    auth_manager: Annotated[AuthManager, Depends(get_auth_manager)],
) -> RedirectResponse:
    """
    Initiate SAML Single Logout with redirect.

    This endpoint redirects the user to the IdP's SLO endpoint.
    """
    settings = get_settings()

    # Get current session
    token = request.cookies.get("session")
    if not token:
        return RedirectResponse(url=settings.frontend_url, status_code=302)

    try:
        user_info = auth_manager.validate_session_token(token, settings.jwt_secret_key)

        slo_url = _get_saml_logout_url(
            auth_manager,
            user_info,
            settings.frontend_url,
        )

        if slo_url:
            # Clear local session
            resp = RedirectResponse(url=slo_url, status_code=302)
            resp.delete_cookie("session")
            return resp
        else:
            # No SLO configured, just clear session
            resp = RedirectResponse(url=settings.frontend_url, status_code=302)
            resp.delete_cookie("session")
            return resp

    except Exception:
        resp = RedirectResponse(url=settings.frontend_url, status_code=302)
        resp.delete_cookie("session")
        return resp


@router.post("/logout/saml/callback")
async def saml_logout_callback(
    request: Request,
    response: Response,
) -> RedirectResponse:
    """
    Handle SAML Single Logout response from IdP.

    The IdP redirects here after completing logout.
    """
    settings = get_settings()

    # Clear any remaining session data
    resp = RedirectResponse(url=settings.frontend_url, status_code=302)
    resp.delete_cookie("session")
    resp.delete_cookie("auth_redirect")
    resp.delete_cookie("auth_state")

    return resp


@router.get("/saml/metadata")
async def get_saml_metadata() -> Response:
    """
    Get SAML Service Provider metadata.
    """
    settings = get_settings()

    metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{settings.saml_sp_entity_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{settings.api_base_url}/auth/callback/saml"
            index="0"
            isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    return Response(
        content=metadata,
        media_type="application/xml",
    )
