# MarketState MCP

Central internal Model Context Protocol server for MarketState.

This directory exists at the repository root because the MCP is meant to become a single internal entrypoint for shared knowledge and tooling across the whole monolith. It should not be split across app or service folders.

## Purpose

Use this server as the place to expose:

- design-system tokens and component contracts
- business definitions and product language
- API and event contracts
- operational runbooks
- domain-specific reference data
- future internal tools and validators

## Initial Module

- `catalog/design-system`: theme tokens, component specs, page recipes, and asset metadata

## Structure

- `server.py`: dependency-free stdio MCP server
- `catalog/`: resource and tool data grouped by domain

## Current Tools

- `list_themes`
- `get_theme`
- `list_components`
- `get_component_spec`
- `get_page_recipe`
- `resolve_asset`
- `validate_theme_usage`

## Run Locally

```bash
python3 /Users/gabrielzenkner/projects/marketstate/mcp/server.py
```

## Example Client Config

```json
{
  "mcpServers": {
    "marketstate": {
      "command": "python3",
      "args": [
        "/Users/gabrielzenkner/projects/marketstate/mcp/server.py"
      ]
    }
  }
}
```

## Next Modules To Add

- `catalog/contracts`
- `catalog/ops`
- `catalog/business`
- `catalog/services`
