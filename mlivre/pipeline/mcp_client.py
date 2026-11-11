"""Cliente mínimo (JSON-RPC sobre HTTP) para o MCP do AnythingMCP.

URL e chave vêm de MLIVRE_MCP_URL / MLIVRE_MCP_KEY ou, se ausentes,
da entrada "mercadolivre" em ~/.claude.json.
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _config():
    url, key = os.environ.get("MLIVRE_MCP_URL"), os.environ.get("MLIVRE_MCP_KEY")
    if not (url and key):
        srv = json.loads((Path.home() / ".claude.json").read_text())["mcpServers"]["mercadolivre"]
        url, key = url or srv["url"], key or srv["headers"]["X-API-Key"]
    return url, key


URL, KEY = _config()


class McpError(Exception):
    pass


def call(tool, args, retries=3):
    """Chama uma ferramenta e devolve o resultado já decodificado (dict/list/str)."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    headers = {"X-API-Key": KEY, "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream", "User-Agent": "mlivre-pipeline/0.1"}
    for attempt in range(retries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(URL, body, headers), timeout=60).read().decode()
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    line = next((l[6:] for l in raw.splitlines() if l.startswith("data: ")), raw)
    msg = json.loads(line)
    if "error" in msg:
        raise McpError(msg["error"])
    res = msg["result"]
    text = res["content"][0]["text"] if res.get("content") else ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = text
    if res.get("isError"):
        raise McpError(data)
    return data
