"""Installer prerequisites. Never output credential values."""
import os
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11+ required.')

if sys.argv[1] == 'connection':
    import tomllib
    from urllib.parse import urlsplit
    root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    try:
        configured = tomllib.loads((root / 'config.toml').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise SystemExit('Personal Codex connection config missing or invalid.')
    connection = configured.get('mcp_servers', {}).get('enterprise_data_remote', {})
    try:
        address = urlsplit(connection.get('url', ''))
        valid = address.scheme == 'https' and address.hostname and not any((address.username, address.password, address.query, address.fragment)) and connection.get('http_headers')
    except ValueError:
        valid = False
    if not valid:
        raise SystemExit('Configure your own authorized HTTPS enterprise_data_remote with http_headers first.')
    print('Personal MCP configuration found; credentials unchanged.')
elif sys.argv[1] == 'runtime':
    from importlib.metadata import version
    expected = {'mcp': '2.2.0', 'httpx': '0.28.1', 'anyio': '4.15.1'}
    if not all(version(name) == value for name, value in expected.items()):
        raise SystemExit('Runtime dependencies must match requirements.txt.')
else:
    raise SystemExit('Unknown setup check.')
