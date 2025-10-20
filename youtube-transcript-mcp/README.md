# YouTube Transcript MCP

This project exposes YouTube subtitle data through a Model Context Protocol (MCP) server. By supplying a video URL or ID you can list the available subtitle languages and retrieve the transcript in any supported language.

## Prerequisites

- Python 3.13 or later
- [uv](https://github.com/astral-sh/uv) installed

Run the following command once to resolve dependencies:

```bash
uv sync
```

## Dependencies

- [`mcp[cli]`](https://github.com/modelcontextprotocol/python-sdk)
- [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)

## Starting the Server

You can start the MCP server with:

```bash
uv run src/youtube_transcript_mcp/server.py
```

## Available Tools

### `list_transcript_languages`

Returns the list of subtitle languages available for the specified video.

Arguments:

- `video`: Video URL or video ID

### `get_transcript`

Retrieves the transcript for the requested language, including start times and durations. If machine-translatable captions exist, the server attempts an automatic translation as well.

Arguments:

- `video`: Video URL or ID
- `language`: Desired language code (example: `en`, `ja`)

## Tips for Testing

After starting the server, connect with an MCP-compatible client such as [MCP Inspector](https://github.com/modelcontextprotocol/inspector) and invoke the tools described above.
