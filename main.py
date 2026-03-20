import ipaddress
import logging
import os
from typing import Union

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("proxy")

API_ENDPOINT: str = os.getenv("API_ENDPOINT", "https://gm-donate.net/api").rstrip("/")

BLOCKED_REQUEST_HEADERS: tuple[str, ...] = (
    "x-forwarded-",
    "x-real-ip",
    "x-original-",
)

STRIPPED_RESPONSE_HEADERS: tuple[str, ...] = (
    "transfer-encoding",
    "content-length",
)

PROXY_TIMEOUT: float = float(os.getenv("PROXY_TIMEOUT", "30.0"))

_raw_allowed = os.getenv("ALLOWED_IPS", "")

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

ALLOWED_NETWORKS: list[IPNetwork] = [
    ipaddress.ip_network(entry.strip(), strict=False)
    for entry in _raw_allowed.split(",")
    if entry.strip()
]

# ---------------------------------------------------------------------------
# IP whitelist
# ---------------------------------------------------------------------------


def is_ip_allowed(ip: str) -> bool:
    """Return True if whitelist is empty (disabled) or IP matches any entry."""
    if not ALLOWED_NETWORKS:
        return True
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in ALLOWED_NETWORKS)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_target_url(full_path: str, query: str) -> str:
    """Normalise path and append query string."""
    if not full_path.startswith("api"):
        full_path = f"api/{full_path.lstrip('/')}"
    url = f"{API_ENDPOINT}/{full_path.lstrip('/')}"
    if query:
        url += f"?{query}"
    return url


def filter_request_headers(headers: dict[str, str]) -> dict[str, str]:
    """Drop headers that could leak internal routing info."""
    return {
        key: value
        for key, value in headers.items()
        if not key.lower().startswith(BLOCKED_REQUEST_HEADERS)
    }


def filter_response_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers that must not be forwarded."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in STRIPPED_RESPONSE_HEADERS
    }


# ---------------------------------------------------------------------------
# Proxy core
# ---------------------------------------------------------------------------


async def forward_request(request: Request, target_url: str) -> Response:
    headers = filter_request_headers(dict(request.headers))
    body = await request.body()

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=PROXY_TIMEOUT,
        http2=True,
    ) as client:
        upstream = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
        )

    logger.info("%s %s -> %s", request.method, target_url, upstream.status_code)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=filter_response_headers(dict(upstream.headers)),
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

PROXY_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]


@app.api_route("/{full_path:path}", methods=PROXY_METHODS)
async def proxy(full_path: str, request: Request) -> Response:
    client_ip = request.client.host if request.client else "unknown"
    if not is_ip_allowed(client_ip):
        logger.warning("Blocked request from %s", client_ip)
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    target_url = build_target_url(full_path, request.url.query)
    try:
        return await forward_request(request, target_url)
    except httpx.TimeoutException:
        logger.warning("Timeout reaching %s", target_url)
        return JSONResponse({"error": "Upstream timeout"}, status_code=504)
    except Exception as exc:
        logger.exception("Proxy error for %s", target_url)
        return JSONResponse({"error": f"Proxy error: {exc}"}, status_code=502)
