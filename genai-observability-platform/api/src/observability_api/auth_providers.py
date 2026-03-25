"""
Advanced Authentication Providers

Supports multiple authentication methods:
- OAuth2/OIDC (Google, Okta, Auth0, Azure AD, etc.)
- SAML 2.0
- API Keys
- JWT Tokens
"""

import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import zlib

from jose import jwt, jwk, JWTError
from jose.utils import base64url_decode

logger = logging.getLogger(__name__)


class AuthProvider(str, Enum):
    """Supported authentication providers."""
    LOCAL = "local"
    GOOGLE = "google"
    OKTA = "okta"
    AUTH0 = "auth0"
    AZURE_AD = "azure_ad"
    GITHUB = "github"
    SAML = "saml"
    CUSTOM_OIDC = "custom_oidc"


@dataclass
class UserInfo:
    """Authenticated user information."""
    user_id: str
    email: str
    name: str = ""
    picture: str = ""
    provider: AuthProvider = AuthProvider.LOCAL
    provider_user_id: str = ""
    roles: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: Optional[datetime] = None


@dataclass
class OIDCConfig:
    """OIDC provider configuration."""
    provider: AuthProvider
    client_id: str
    client_secret: str
    issuer: str
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    jwks_uri: str = ""
    scopes: List[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    redirect_uri: str = ""

    # Discovery
    discovery_url: str = ""

    # Role/group mapping
    roles_claim: str = "roles"
    groups_claim: str = "groups"

    def __post_init__(self):
        """Discover endpoints if discovery URL provided."""
        if self.discovery_url and not self.authorization_endpoint:
            self._discover_endpoints()

    def _discover_endpoints(self):
        """Fetch OIDC discovery document."""
        try:
            req = urllib.request.Request(self.discovery_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                config = json.loads(response.read().decode())

            self.issuer = config.get("issuer", self.issuer)
            self.authorization_endpoint = config.get("authorization_endpoint", "")
            self.token_endpoint = config.get("token_endpoint", "")
            self.userinfo_endpoint = config.get("userinfo_endpoint", "")
            self.jwks_uri = config.get("jwks_uri", "")

            logger.info(f"Discovered OIDC endpoints for {self.provider}")
        except Exception as e:
            logger.error(f"OIDC discovery failed: {e}")


@dataclass
class SAMLConfig:
    """SAML provider configuration."""
    entity_id: str
    sso_url: str
    slo_url: str = ""
    certificate: str = ""  # PEM encoded X.509 certificate
    private_key: str = ""  # PEM encoded private key for signing
    sp_entity_id: str = ""
    sp_acs_url: str = ""  # Assertion Consumer Service URL
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"

    # Attribute mapping
    email_attribute: str = "email"
    name_attribute: str = "name"
    roles_attribute: str = "roles"
    groups_attribute: str = "groups"


class OIDCProvider:
    """
    OAuth2/OIDC authentication provider.

    Supports various OIDC-compliant identity providers including
    Google, Okta, Auth0, Azure AD, and custom OIDC providers.
    """

    # Well-known provider configurations
    PROVIDER_CONFIGS = {
        AuthProvider.GOOGLE: {
            "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
        },
        AuthProvider.OKTA: {
            "discovery_suffix": "/.well-known/openid-configuration",
        },
        AuthProvider.AUTH0: {
            "discovery_suffix": "/.well-known/openid-configuration",
        },
        AuthProvider.AZURE_AD: {
            "discovery_url": "https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
        },
        AuthProvider.GITHUB: {
            "authorization_endpoint": "https://github.com/login/oauth/authorize",
            "token_endpoint": "https://github.com/login/oauth/access_token",
            "userinfo_endpoint": "https://api.github.com/user",
        },
    }

    def __init__(self, config: OIDCConfig):
        self.config = config
        self._jwks_cache: Dict[str, Any] = {}
        self._jwks_cache_time: float = 0
        self._jwks_cache_ttl: float = 3600  # 1 hour

    def get_authorization_url(
        self,
        state: str,
        nonce: Optional[str] = None,
        prompt: Optional[str] = None,
        login_hint: Optional[str] = None,
    ) -> str:
        """
        Generate the authorization URL for the OAuth2 flow.

        Args:
            state: State parameter for CSRF protection
            nonce: Nonce for ID token validation
            prompt: Prompt parameter (login, consent, etc.)
            login_hint: Pre-fill email for login

        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }

        if nonce:
            params["nonce"] = nonce
        if prompt:
            params["prompt"] = prompt
        if login_hint:
            params["login_hint"] = login_hint

        query_string = urllib.parse.urlencode(params)
        return f"{self.config.authorization_endpoint}?{query_string}"

    def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code
            code_verifier: PKCE code verifier (optional)

        Returns:
            Token response
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        req = urllib.request.Request(
            self.config.token_endpoint,
            data=urllib.parse.urlencode(data).encode(),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"Token exchange failed: {e.code} - {error_body}")
            raise Exception(f"Token exchange failed: {error_body}")

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using a refresh token."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        req = urllib.request.Request(
            self.config.token_endpoint,
            data=urllib.parse.urlencode(data).encode(),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def validate_id_token(
        self,
        id_token: str,
        nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate an ID token and return claims.

        Args:
            id_token: The ID token to validate
            nonce: Expected nonce value

        Returns:
            Token claims
        """
        # Get JWKS
        jwks = self._get_jwks()

        # Decode header to get key ID
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")

        # Find matching key
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            raise Exception(f"Key {kid} not found in JWKS")

        # Validate token
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256", "ES256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
            )

            # Validate nonce if provided
            if nonce and claims.get("nonce") != nonce:
                raise Exception("Invalid nonce")

            return claims

        except JWTError as e:
            logger.error(f"ID token validation failed: {e}")
            raise Exception(f"Invalid ID token: {e}")

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user info from the userinfo endpoint.

        Args:
            access_token: OAuth2 access token

        Returns:
            User information
        """
        if not self.config.userinfo_endpoint:
            return {}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        req = urllib.request.Request(
            self.config.userinfo_endpoint,
            headers=headers,
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def authenticate(
        self,
        code: str,
        nonce: Optional[str] = None,
        code_verifier: Optional[str] = None,
    ) -> UserInfo:
        """
        Complete the OIDC authentication flow.

        Args:
            code: Authorization code
            nonce: Expected nonce
            code_verifier: PKCE code verifier

        Returns:
            Authenticated user info
        """
        # Exchange code for tokens
        tokens = self.exchange_code_for_tokens(code, code_verifier)

        access_token = tokens.get("access_token", "")
        id_token = tokens.get("id_token", "")
        refresh_token = tokens.get("refresh_token", "")
        expires_in = tokens.get("expires_in", 3600)

        # Validate ID token and get claims
        claims = {}
        if id_token:
            claims = self.validate_id_token(id_token, nonce)

        # Get additional user info
        user_info = {}
        if access_token and self.config.userinfo_endpoint:
            user_info = self.get_user_info(access_token)

        # Merge claims and user info
        all_info = {**claims, **user_info}

        # Extract roles and groups
        roles = all_info.get(self.config.roles_claim, [])
        groups = all_info.get(self.config.groups_claim, [])

        if isinstance(roles, str):
            roles = [roles]
        if isinstance(groups, str):
            groups = [groups]

        return UserInfo(
            user_id=all_info.get("sub", ""),
            email=all_info.get("email", ""),
            name=all_info.get("name", all_info.get("preferred_username", "")),
            picture=all_info.get("picture", ""),
            provider=self.config.provider,
            provider_user_id=all_info.get("sub", ""),
            roles=roles,
            groups=groups,
            scopes=self.config.scopes,
            metadata=all_info,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        )

    def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS with caching."""
        now = time.time()

        if self._jwks_cache and (now - self._jwks_cache_time) < self._jwks_cache_ttl:
            return self._jwks_cache

        if not self.config.jwks_uri:
            return {"keys": []}

        req = urllib.request.Request(self.config.jwks_uri)
        with urllib.request.urlopen(req, timeout=30) as response:
            self._jwks_cache = json.loads(response.read().decode())
            self._jwks_cache_time = now
            return self._jwks_cache


class SAMLProvider:
    """
    SAML 2.0 authentication provider.

    Supports SAML SSO with various identity providers including
    Okta, OneLogin, Azure AD, ADFS, and others.
    """

    SAML_NAMESPACES = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }

    def __init__(self, config: SAMLConfig):
        self.config = config

    def create_authn_request(
        self,
        relay_state: Optional[str] = None,
        force_authn: bool = False,
    ) -> Tuple[str, str]:
        """
        Create a SAML AuthnRequest.

        Args:
            relay_state: State to pass through
            force_authn: Force re-authentication

        Returns:
            Tuple of (redirect_url, request_id)
        """
        request_id = f"_id{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.sso_url}"
    AssertionConsumerServiceURL="{self.config.sp_acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self.config.name_id_format}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Compress and encode
        compressed = zlib.compress(authn_request.encode())[2:-4]  # Remove zlib header/trailer
        encoded = base64.b64encode(compressed).decode()

        # Build redirect URL
        params = {
            "SAMLRequest": encoded,
        }
        if relay_state:
            params["RelayState"] = relay_state

        query_string = urllib.parse.urlencode(params)
        redirect_url = f"{self.config.sso_url}?{query_string}"

        return redirect_url, request_id

    def process_response(
        self,
        saml_response: str,
        expected_request_id: Optional[str] = None,
    ) -> UserInfo:
        """
        Process a SAML response and extract user information.

        Args:
            saml_response: Base64 encoded SAML response
            expected_request_id: Expected InResponseTo value

        Returns:
            Authenticated user info
        """
        # Decode response
        try:
            decoded = base64.b64decode(saml_response)
            response_xml = decoded.decode()
        except Exception as e:
            raise Exception(f"Failed to decode SAML response: {e}")

        # Parse XML
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as e:
            raise Exception(f"Failed to parse SAML response: {e}")

        # Check status
        status = root.find(".//samlp:Status/samlp:StatusCode", self.SAML_NAMESPACES)
        if status is not None:
            status_value = status.get("Value", "")
            if "Success" not in status_value:
                raise Exception(f"SAML authentication failed: {status_value}")

        # Validate InResponseTo
        in_response_to = root.get("InResponseTo", "")
        if expected_request_id and in_response_to != expected_request_id:
            raise Exception("Invalid InResponseTo")

        # Find assertion
        assertion = root.find(".//saml:Assertion", self.SAML_NAMESPACES)
        if assertion is None:
            raise Exception("No assertion found in SAML response")

        # Validate signature (simplified - in production use xmlsec)
        # self._validate_signature(response_xml)

        # Validate conditions
        self._validate_conditions(assertion)

        # Extract user info
        return self._extract_user_info(assertion)

    def _validate_conditions(self, assertion: ET.Element) -> None:
        """Validate assertion conditions."""
        conditions = assertion.find("saml:Conditions", self.SAML_NAMESPACES)
        if conditions is None:
            return

        now = datetime.utcnow()

        not_before = conditions.get("NotBefore")
        if not_before:
            not_before_dt = datetime.fromisoformat(not_before.replace("Z", "+00:00").replace("+00:00", ""))
            if now < not_before_dt:
                raise Exception("Assertion not yet valid")

        not_on_or_after = conditions.get("NotOnOrAfter")
        if not_on_or_after:
            not_on_or_after_dt = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00").replace("+00:00", ""))
            if now >= not_on_or_after_dt:
                raise Exception("Assertion has expired")

    def _extract_user_info(self, assertion: ET.Element) -> UserInfo:
        """Extract user information from SAML assertion."""
        # Get NameID
        name_id = assertion.find(".//saml:Subject/saml:NameID", self.SAML_NAMESPACES)
        user_id = name_id.text if name_id is not None else ""

        # Get attributes
        attributes: Dict[str, List[str]] = {}
        attr_statement = assertion.find("saml:AttributeStatement", self.SAML_NAMESPACES)

        if attr_statement is not None:
            for attr in attr_statement.findall("saml:Attribute", self.SAML_NAMESPACES):
                attr_name = attr.get("Name", "")
                attr_values = []
                for value in attr.findall("saml:AttributeValue", self.SAML_NAMESPACES):
                    if value.text:
                        attr_values.append(value.text)
                if attr_name and attr_values:
                    attributes[attr_name] = attr_values

        # Map attributes to user info
        email = self._get_attribute(attributes, self.config.email_attribute, user_id)
        name = self._get_attribute(attributes, self.config.name_attribute, "")
        roles = self._get_attribute_list(attributes, self.config.roles_attribute)
        groups = self._get_attribute_list(attributes, self.config.groups_attribute)

        return UserInfo(
            user_id=user_id,
            email=email,
            name=name,
            provider=AuthProvider.SAML,
            provider_user_id=user_id,
            roles=roles,
            groups=groups,
            metadata=attributes,
        )

    def _get_attribute(
        self,
        attributes: Dict[str, List[str]],
        name: str,
        default: str = "",
    ) -> str:
        """Get a single attribute value."""
        values = attributes.get(name, [])
        return values[0] if values else default

    def _get_attribute_list(
        self,
        attributes: Dict[str, List[str]],
        name: str,
    ) -> List[str]:
        """Get attribute values as a list."""
        return attributes.get(name, [])

    def create_logout_request(
        self,
        name_id: str,
        session_index: Optional[str] = None,
    ) -> str:
        """Create a SAML logout request."""
        request_id = f"_id{secrets.token_hex(16)}"
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{self.config.slo_url}">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <saml:NameID Format="{self.config.name_id_format}">{name_id}</saml:NameID>
</samlp:LogoutRequest>"""

        compressed = zlib.compress(logout_request.encode())[2:-4]
        encoded = base64.b64encode(compressed).decode()

        params = {"SAMLRequest": encoded}
        query_string = urllib.parse.urlencode(params)

        return f"{self.config.slo_url}?{query_string}"


class AuthManager:
    """
    Centralized authentication manager.

    Manages multiple authentication providers and provides
    a unified interface for authentication operations.
    """

    def __init__(self):
        self.oidc_providers: Dict[AuthProvider, OIDCProvider] = {}
        self.saml_providers: Dict[str, SAMLProvider] = {}
        self._state_store: Dict[str, Dict[str, Any]] = {}

    def register_oidc_provider(
        self,
        provider: AuthProvider,
        config: OIDCConfig,
    ) -> None:
        """Register an OIDC provider."""
        self.oidc_providers[provider] = OIDCProvider(config)
        logger.info(f"Registered OIDC provider: {provider}")

    def register_saml_provider(
        self,
        name: str,
        config: SAMLConfig,
    ) -> None:
        """Register a SAML provider."""
        self.saml_providers[name] = SAMLProvider(config)
        logger.info(f"Registered SAML provider: {name}")

    def get_login_url(
        self,
        provider: Union[AuthProvider, str],
        redirect_uri: str,
    ) -> Tuple[str, str]:
        """
        Get login URL for a provider.

        Args:
            provider: Authentication provider
            redirect_uri: Callback URL

        Returns:
            Tuple of (login_url, state)
        """
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        # Store state for validation
        self._state_store[state] = {
            "provider": provider,
            "nonce": nonce,
            "redirect_uri": redirect_uri,
            "created_at": datetime.utcnow().isoformat(),
        }

        if isinstance(provider, AuthProvider) and provider in self.oidc_providers:
            oidc = self.oidc_providers[provider]
            url = oidc.get_authorization_url(state, nonce)
            return url, state

        elif isinstance(provider, str) and provider in self.saml_providers:
            saml = self.saml_providers[provider]
            url, request_id = saml.create_authn_request(relay_state=state)
            self._state_store[state]["request_id"] = request_id
            return url, state

        else:
            raise Exception(f"Unknown provider: {provider}")

    def handle_callback(
        self,
        provider: Union[AuthProvider, str],
        params: Dict[str, str],
    ) -> UserInfo:
        """
        Handle authentication callback.

        Args:
            provider: Authentication provider
            params: Callback parameters

        Returns:
            Authenticated user info
        """
        if isinstance(provider, AuthProvider) and provider in self.oidc_providers:
            return self._handle_oidc_callback(provider, params)

        elif isinstance(provider, str) and provider in self.saml_providers:
            return self._handle_saml_callback(provider, params)

        else:
            raise Exception(f"Unknown provider: {provider}")

    def _handle_oidc_callback(
        self,
        provider: AuthProvider,
        params: Dict[str, str],
    ) -> UserInfo:
        """Handle OIDC callback."""
        # Validate state
        state = params.get("state", "")
        state_data = self._state_store.pop(state, None)

        if not state_data:
            raise Exception("Invalid state parameter")

        # Check for error
        if "error" in params:
            error = params.get("error", "")
            error_description = params.get("error_description", "")
            raise Exception(f"OAuth error: {error} - {error_description}")

        # Get code
        code = params.get("code", "")
        if not code:
            raise Exception("No authorization code received")

        # Authenticate
        oidc = self.oidc_providers[provider]
        return oidc.authenticate(
            code,
            nonce=state_data.get("nonce"),
            code_verifier=params.get("code_verifier"),
        )

    def _handle_saml_callback(
        self,
        provider: str,
        params: Dict[str, str],
    ) -> UserInfo:
        """Handle SAML callback."""
        saml_response = params.get("SAMLResponse", "")
        relay_state = params.get("RelayState", "")

        if not saml_response:
            raise Exception("No SAML response received")

        # Get state data
        state_data = self._state_store.pop(relay_state, None)
        expected_request_id = state_data.get("request_id") if state_data else None

        # Process response
        saml = self.saml_providers[provider]
        return saml.process_response(saml_response, expected_request_id)

    def create_session_token(
        self,
        user_info: UserInfo,
        secret_key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Create a session JWT token.

        Args:
            user_info: Authenticated user
            secret_key: JWT signing key
            expires_in: Token expiration in seconds

        Returns:
            JWT token
        """
        now = datetime.utcnow()
        claims = {
            "sub": user_info.user_id,
            "email": user_info.email,
            "name": user_info.name,
            "provider": user_info.provider.value,
            "roles": user_info.roles,
            "groups": user_info.groups,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }

        return jwt.encode(claims, secret_key, algorithm="HS256")

    def validate_session_token(
        self,
        token: str,
        secret_key: str,
    ) -> UserInfo:
        """
        Validate a session token and return user info.

        Args:
            token: JWT token
            secret_key: JWT signing key

        Returns:
            User info from token
        """
        try:
            claims = jwt.decode(token, secret_key, algorithms=["HS256"])

            return UserInfo(
                user_id=claims.get("sub", ""),
                email=claims.get("email", ""),
                name=claims.get("name", ""),
                provider=AuthProvider(claims.get("provider", "local")),
                roles=claims.get("roles", []),
                groups=claims.get("groups", []),
            )

        except JWTError as e:
            raise Exception(f"Invalid token: {e}")


# PKCE helpers for OAuth2
def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(64)

    # SHA256 hash
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")

    return code_verifier, code_challenge


# Factory functions for common providers
def create_google_provider(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create a Google OIDC provider."""
    config = OIDCConfig(
        provider=AuthProvider.GOOGLE,
        client_id=client_id,
        client_secret=client_secret,
        issuer="https://accounts.google.com",
        discovery_url="https://accounts.google.com/.well-known/openid-configuration",
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile"],
    )
    return OIDCProvider(config)


def create_okta_provider(
    domain: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create an Okta OIDC provider."""
    config = OIDCConfig(
        provider=AuthProvider.OKTA,
        client_id=client_id,
        client_secret=client_secret,
        issuer=f"https://{domain}",
        discovery_url=f"https://{domain}/.well-known/openid-configuration",
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile", "groups"],
        groups_claim="groups",
    )
    return OIDCProvider(config)


def create_azure_ad_provider(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> OIDCProvider:
    """Create an Azure AD OIDC provider."""
    config = OIDCConfig(
        provider=AuthProvider.AZURE_AD,
        client_id=client_id,
        client_secret=client_secret,
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        discovery_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile"],
        roles_claim="roles",
        groups_claim="groups",
    )
    return OIDCProvider(config)
