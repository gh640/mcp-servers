import argparse
import shlex
import subprocess
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ServerConfig:
    name: str
    command: list[str]
    command_display: str
    help_command_display: str


@dataclass(frozen=True)
class ParsedArguments:
    command: str
    command_help: str


class CommandExecutionResult(BaseModel):
    command: list[str] = Field(description="Full command that was executed")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(description="Captured standard output")
    stderr: str = Field(description="Captured standard error")


def _parse_command(raw: str) -> list[str]:
    return shlex.split(raw)


def _build_config(
    parsed: ParsedArguments, parser: argparse.ArgumentParser
) -> ServerConfig:
    command_parts = _parse_command(parsed.command)
    if not command_parts:
        parser.error("No command specified for --command")
        raise AssertionError

    name = command_parts[0]

    if not _parse_command(parsed.command_help):
        parser.error("No command specified for --command-help")
        raise AssertionError

    return ServerConfig(
        name=name,
        command=command_parts,
        command_display=parsed.command,
        help_command_display=parsed.command_help,
    )


def _create_mcp(config: ServerConfig) -> FastMCP:
    instructions_lines = [
        "This MCP server wraps a shell command.",
        f"Invoke the `{config.name}` tool to run `{config.command_display}`.",
        "Provide arguments via the `arguments` parameter; optional stdin can be set via `stdin`.",
    ]

    instructions_lines.append(
        f"To review the command help, run: {config.help_command_display}"
    )

    mcp = FastMCP(
        "Command MCP",
        instructions="\n".join(instructions_lines),
    )

    _register_command_tool(mcp, config)

    return mcp


def _register_command_tool(mcp: FastMCP, config: ServerConfig):
    command = config.command
    name = config.name

    @mcp.tool(name=name)
    def run_command(
        arguments: list[str] = Field(
            default_factory=list,
            description="Command-line arguments appended to the base command",
        ),
        stdin: str | None = Field(
            default=None,
            description="Optional standard input string piped to the command",
        ),
    ) -> CommandExecutionResult:
        full_command: list[str] = [*command, *arguments]

        try:
            result = subprocess.run(
                full_command,
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Failed to execute command `{name}`: file not found"
            ) from error
        except OSError as error:
            raise RuntimeError(
                f"Failed to execute command `{name}`: {error}"  # noqa: TRY003
            ) from error

        return CommandExecutionResult(
            command=full_command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Expose a shell command via MCP",
    )
    parser.add_argument(
        "--command",
        required=True,
        help="Command to expose as an MCP tool (e.g., 'git')",
    )
    parser.add_argument(
        "--command-help",
        dest="command_help",
        required=True,
        help="Help command that explains usage (e.g., 'git --help')",
    )

    namespace = parser.parse_args()
    parsed_arguments = ParsedArguments(
        command=namespace.command,
        command_help=namespace.command_help,
    )
    config = _build_config(parsed_arguments, parser)

    mcp = _create_mcp(config)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
