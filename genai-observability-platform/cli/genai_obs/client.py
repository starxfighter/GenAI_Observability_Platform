"""
API Client for CLI
"""
import requests
from typing import Any, Optional
from urllib.parse import urljoin

from .config import Config


class APIError(Exception):
    """API error with status code and message."""
    def __init__(self, status_code: int, message: str, details: Optional[dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"API Error {status_code}: {message}")


class APIClient:
    """HTTP client for the Observability API."""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'genai-obs-cli/0.1.0'
        })

    def _url(self, path: str) -> str:
        """Build full URL from path."""
        return urljoin(self.config.endpoint, path)

    def _handle_response(self, response: requests.Response) -> dict:
        """Handle API response."""
        try:
            data = response.json()
        except ValueError:
            data = {'message': response.text}

        if response.status_code >= 400:
            raise APIError(
                status_code=response.status_code,
                message=data.get('message', data.get('detail', 'Unknown error')),
                details=data
            )

        return data

    def get(self, path: str, params: Optional[dict] = None) -> dict:
        """GET request."""
        response = self.session.get(
            self._url(path),
            params=params,
            timeout=self.config.timeout
        )
        return self._handle_response(response)

    def post(self, path: str, data: Optional[dict] = None) -> dict:
        """POST request."""
        response = self.session.post(
            self._url(path),
            json=data,
            timeout=self.config.timeout
        )
        return self._handle_response(response)

    def put(self, path: str, data: Optional[dict] = None) -> dict:
        """PUT request."""
        response = self.session.put(
            self._url(path),
            json=data,
            timeout=self.config.timeout
        )
        return self._handle_response(response)

    def patch(self, path: str, data: Optional[dict] = None) -> dict:
        """PATCH request."""
        response = self.session.patch(
            self._url(path),
            json=data,
            timeout=self.config.timeout
        )
        return self._handle_response(response)

    def delete(self, path: str) -> dict:
        """DELETE request."""
        response = self.session.delete(
            self._url(path),
            timeout=self.config.timeout
        )
        return self._handle_response(response)
