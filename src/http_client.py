"""HTTP utilities shared by the project.

We centralize:
- a single :class:`requests.Session` with sane defaults
- timeouts
- a lightweight retry strategy for transient errors

This keeps the API modules small and consistent.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def build_session(
    *,
    retries: int = 3,
    backoff_factor: float = 0.4,
    status_forcelist: Optional[list[int]] = None,
) -> requests.Session:
    """Create a configured requests session.

    Parameters
    ----------
    retries:
        Total number of retries for transient failures.
    backoff_factor:
        Exponential backoff factor (see urllib3 Retry docs).
    status_forcelist:
        HTTP status codes that should be retried.
    """

    if status_forcelist is None:
        # Common transient errors (server overload / gateway issues)
        status_forcelist = [429, 500, 502, 503, 504]

    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # A polite default User-Agent (some endpoints block the default requests UA).
    session.headers.update(
        {
            "User-Agent": "amse-weather-app/1.0 (+https://github.com/)"
        }
    )

    return session
