# MCP servers

Custom MCP servers to use locally.

## Prerequisites

- Python 3.13 or later
- `uv`

## Usage

Clone this repo and set one as an MCP server.

## Examples

### Codex CLI

`config.toml`:

```toml
[mcp_servers.youtube-transcript-mcp]
command = "uv"
args = [
  "--directory",
  "/path/to/mcp-servers/youtube-transcript-mcp",
  "run",
  "src/youtube_transcript_mcp/server.py",
]
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-transcript-mcp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/mcp-servers/youtube-transcript-mcp",
        "run",
        "src/youtube_transcript_mcp/server.py"
      ]
    }
  }
}
```

### Cline

`cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "youtube-transcript-mcp": {
      "transportType": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-servers/youtube-transcript-mcp",
        "run",
        "src/youtube_transcript_mcp/server.py"
      ],
      "disabled": false,
      "autoApprove": [],
      "protocolVersion": "2025-03-26"
    },
  }
}
```
