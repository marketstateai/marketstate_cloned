#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CATALOG_ROOT = ROOT / "catalog"
DESIGN_SYSTEM_ROOT = CATALOG_ROOT / "design-system"
DEBUG = os.environ.get("MARKETSTATE_MCP_DEBUG", "").lower() in {"1", "true", "yes", "on"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def json_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def send_message(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def log(message: str) -> None:
    print(f"[marketstate-mcp] {message}", file=sys.stderr, flush=True)


def read_message() -> dict[str, Any] | None:
    content_length = None

    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        header = line.decode("utf-8").strip()
        if header.lower().startswith("content-length:"):
            content_length = int(header.split(":", 1)[1].strip())

    if content_length is None:
        return None

    body = sys.stdin.buffer.read(content_length)
    if not body:
        return None

    return json.loads(body.decode("utf-8"))


def list_names(path: Path) -> list[str]:
    return sorted(file.stem for file in path.glob("*.json"))


def load_catalog_item(group: str, name: str) -> dict[str, Any]:
    path = DESIGN_SYSTEM_ROOT / group / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown design-system item: {group}/{name}")
    return load_json(path)


def flatten_tokens(prefix: str, value: Any) -> list[str]:
    if isinstance(value, dict):
        tokens: list[str] = []
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            tokens.extend(flatten_tokens(child_prefix, child))
        return tokens
    return [prefix]


def validate_theme_usage(arguments: dict[str, Any]) -> dict[str, Any]:
    theme_name = arguments.get("theme", "marketstate-dark")
    tokens_used = arguments.get("tokens_used", [])
    component_names = arguments.get("component_names", [])
    hex_values = [str(value).upper() for value in arguments.get("hex_values", [])]

    theme = load_catalog_item("themes", theme_name)
    valid_tokens = set(flatten_tokens("", theme.get("tokens", {})))
    palette = {
        str(value).upper()
        for group in theme.get("tokens", {}).values()
        if isinstance(group, dict)
        for value in group.values()
        if isinstance(value, str) and value.startswith("#")
    }

    unknown_tokens = sorted(token for token in tokens_used if token not in valid_tokens)
    unknown_components = sorted(name for name in component_names if name not in list_names(DESIGN_SYSTEM_ROOT / "components"))
    unknown_hex_values = sorted(value for value in hex_values if value not in palette)

    return {
        "theme": theme_name,
        "valid": not (unknown_tokens or unknown_components or unknown_hex_values),
        "unknown_tokens": unknown_tokens,
        "unknown_components": unknown_components,
        "unknown_hex_values": unknown_hex_values
    }


def resource_catalog() -> list[dict[str, Any]]:
    resources = []
    for group in ("themes", "components", "recipes", "assets"):
        for name in list_names(DESIGN_SYSTEM_ROOT / group):
            resources.append(
                {
                    "uri": f"marketstate://design-system/{group}/{name}",
                    "name": f"design-system/{group}/{name}",
                    "mimeType": "application/json"
                }
            )
    return resources


def read_resource(uri: str) -> dict[str, Any]:
    prefix = "marketstate://design-system/"
    if not uri.startswith(prefix):
        raise FileNotFoundError(f"Unknown resource URI: {uri}")

    tail = uri[len(prefix):]
    parts = tail.split("/")
    if len(parts) != 2:
        raise FileNotFoundError(f"Unknown resource URI: {uri}")

    group, name = parts
    payload = load_catalog_item(group, name)
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(payload, indent=2)
            }
        ]
    }


def tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_themes",
            "description": "List approved MarketState theme variants.",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_theme",
            "description": "Return the full token set for a theme.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        },
        {
            "name": "list_components",
            "description": "List approved shared design-system component specs.",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "get_component_spec",
            "description": "Return the spec for one shared component.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        },
        {
            "name": "get_page_recipe",
            "description": "Return a canonical page recipe.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        },
        {
            "name": "resolve_asset",
            "description": "Return canonical brand asset metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        },
        {
            "name": "validate_theme_usage",
            "description": "Validate token names, component names, and palette values against the approved theme.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "tokens_used": {"type": "array", "items": {"type": "string"}},
                    "component_names": {"type": "array", "items": {"type": "string"}},
                    "hex_values": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    ]


def tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "list_themes":
        return tool_result({"themes": list_names(DESIGN_SYSTEM_ROOT / "themes")})
    if name == "get_theme":
        return tool_result(load_catalog_item("themes", arguments["name"]))
    if name == "list_components":
        return tool_result({"components": list_names(DESIGN_SYSTEM_ROOT / "components")})
    if name == "get_component_spec":
        return tool_result(load_catalog_item("components", arguments["name"]))
    if name == "get_page_recipe":
        return tool_result(load_catalog_item("recipes", arguments["name"]))
    if name == "resolve_asset":
        return tool_result(load_catalog_item("assets", arguments["name"]))
    if name == "validate_theme_usage":
        return tool_result(validate_theme_usage(arguments))
    raise FileNotFoundError(f"Unknown tool: {name}")


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {})

    if DEBUG:
        log(f"request method={method}")

    if method == "initialize":
        return json_response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "resources": {},
                    "tools": {}
                },
                "serverInfo": {
                    "name": "marketstate-mcp",
                    "version": "0.1.0"
                }
            }
        )

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return json_response(request_id, {})

    if method == "resources/list":
        return json_response(request_id, {"resources": resource_catalog()})

    if method == "resources/read":
        return json_response(request_id, read_resource(params["uri"]))

    if method == "tools/list":
        return json_response(request_id, {"tools": tool_catalog()})

    if method == "tools/call":
        return json_response(request_id, handle_tool_call(params["name"], params.get("arguments", {})))

    if request_id is not None:
        return json_error(request_id, -32601, f"Method not found: {method}")
    return None


def main() -> int:
    log("server started on stdio")
    log("catalog loaded: design-system")
    if DEBUG:
        log("debug logging enabled")

    while True:
        message = read_message()
        if message is None:
            log("stdin closed, shutting down")
            return 0
        try:
            response = handle_request(message)
        except FileNotFoundError as error:
            log(f"not found: {error}")
            response = json_error(message.get("id"), -32001, str(error))
        except Exception as error:
            log(f"unhandled error: {error}")
            response = json_error(message.get("id"), -32000, str(error))

        if response is not None:
            send_message(response)


if __name__ == "__main__":
    raise SystemExit(main())
