# Command MCP

This is an MCP to provide a shell command through a Model Context Protocol (MCP) server. By configuring the server with the desired command, any MCP client can invoke that command as a tool.

## Prerequisites

- Python 3.13 or later
- [uv](https://github.com/astral-sh/uv) installed

Run the following command once to resolve dependencies:

```bash
uv sync
```

## Starting the Server

Configure the server with the command and its help invocation:

```bash
uv run src/command_mcp/server.py --command "git" --description "Git CLI wrapper" --command-help "git --help"
```

- `--command` (required): Command to expose as an MCP tool (for example, `git`).
- `--description` (required): One-line text used as the tool description surfaced to MCP clients.
- `--command-help` (required): Help command that provides descriptive output (for example, `git --help`). The output is surfaced in the server instructions and is available via a dedicated help resource.

## Available Tools

### Command execution tool

The MCP server exposes a tool with the same name as the configured command. The tool accepts the following arguments:

- `arguments`: List of arguments that will be passed to the command.
- `stdin`: Optional standard input string that will be piped to the command.

The tool returns:

- `exit_code`: Process exit status.
- `stdout`: Captured standard output.
- `stderr`: Captured standard error.

### Help resource

The MCP server additionally exposes a `<command>-help` resource available at `command-mcp-help://<command>`. Fetching this resource runs the command configured via `--command-help` and returns its standard output, making it easy to surface usage documentation inside MCP clients.

The resource returns:

- `stdout`: Captured standard output from the help command.

## Tips for Testing

After starting the server, connect with an MCP-compatible client such as [MCP Inspector](https://github.com/modelcontextprotocol/inspector) and invoke the generated tool. For example, with `--command git`, call the tool with `arguments` set to `--version`.
