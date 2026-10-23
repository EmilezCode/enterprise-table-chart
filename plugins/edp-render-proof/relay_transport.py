"""Personal authorized HTTPS transport only; no business data or UI implementation."""
import os
import time
import tomllib
import urllib.parse
from pathlib import Path
from contextlib import asynccontextmanager
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
_http_pool=None

class _PoolLease(httpx.AsyncBaseTransport):
    """Each MCP session has its own headers; only TCP/TLS connections are shared."""
    def __init__(self, pool):
        self.pool = pool

    async def handle_async_request(self, request):
        return await self.pool.handle_async_request(request)

    async def aclose(self):
        pass  # The worker's transport_runtime owns pool shutdown.


@asynccontextmanager
async def transport_runtime():
    global _http_pool
    async with httpx.AsyncHTTPTransport(trust_env=False, retries=0) as pool:
        _http_pool = pool
        try:
            yield
        finally:
            _http_pool = None


@asynccontextmanager
async def authorized_session(timing=None):
    # Use exactly the user's already-configured connection. No admin/Feishu token,
    # no URL/credential supplied by the widget, no copying secrets to another file.
    timing = timing if timing is not None else {}
    phase = time.perf_counter()
    config_root=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
    configured = tomllib.loads((config_root/'config.toml').read_text(encoding="utf-8"))
    connection = configured["mcp_servers"]["enterprise_data_remote"]
    address = connection["url"]
    parsed = urllib.parse.urlsplit(address)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Existing enterprise MCP connection must use a plain HTTPS endpoint.")
    timing['config_ms'] = round((time.perf_counter()-phase)*1000,3)
    timing['connection_pool_enabled'] = _http_pool is not None
    phase = time.perf_counter()
    transport = _PoolLease(_http_pool) if _http_pool is not None else None
    async with httpx.AsyncClient(headers=connection["http_headers"], transport=transport, trust_env=False, timeout=40, follow_redirects=False) as http:
        timing['client_setup_ms'] = round((time.perf_counter()-phase)*1000,3)
        phase = time.perf_counter()
        async with streamable_http_client(address,http_client=http) as streams:
            async with ClientSession(streams[0],streams[1]) as session:
                initialized = await session.initialize()
                timing['mcp_initialize_ms'] = round((time.perf_counter()-phase)*1000,3)
                yield session, initialized
