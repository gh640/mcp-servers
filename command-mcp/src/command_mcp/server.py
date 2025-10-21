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
    description: str
    command_display: str
    help_command: list[str]
    help_command_display: str

    @property
    def help_name(self) -> str:
        return f"{self.name}-help"


@dataclass(frozen=True)
class CliArgs:
    command: str
    description: str
    command_help: str


class CommandExecutionResult(BaseModel):
    command: list[str] = Field(description="Full command that was executed")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(description="Captured standard output")
    stderr: str = Field(description="Captured standard error")


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
        "--description",
        required=True,
        help="One-line description of the command",
    )
    parser.add_argument(
        "--command-help",
        dest="command_help",
        required=True,
        help="Help command that explains usage (e.g., 'git --help')",
    )

    parsed = parser.parse_args()
    args = CliArgs(
        command=parsed.command,
        description=parsed.description,
        command_help=parsed.command_help,
    )
    config = _build_config(args, parser)

    mcp = _create_mcp(config)
    mcp.run(transport="stdio")


def _parse_command(raw: str) -> list[str]:
    return shlex.split(raw)


def _build_config(args: CliArgs, parser: argparse.ArgumentParser) -> ServerConfig:
    command_parts = _parse_command(args.command)
    if not command_parts:
        parser.error("Command in --command is empty.")
        raise AssertionError

    help_command_parts = _parse_command(args.command_help)
    if not help_command_parts:
        parser.error("Command in --command-help is empty.")
        raise AssertionError

    return ServerConfig(
        name=command_parts[0],
        command=command_parts,
        description=args.description,
        command_display=args.command,
        help_command=help_command_parts,
        help_command_display=args.command_help,
    )


def _create_mcp(config: ServerConfig) -> FastMCP:
    instructions_lines = [
        "This MCP server wraps a shell command.",
        f"Invoke the `{config.name}` tool to run `{config.command_display}`.",
        "Provide arguments via the `arguments` parameter; optional stdin can be set via `stdin`.",
        f"Commands with args `{config.command_display}` are automatically prepended and pass only additional arguments.",
        "",
        f"To review the command help, You can invoke the `{config.help_name}` tool.",
    ]

    mcp = FastMCP(
        "Command MCP",
        instructions="\n".join(instructions_lines),
    )

    _register_command_tool(mcp, config)

    return mcp


def _register_command_tool(mcp: FastMCP, config: ServerConfig):
    command = config.command
    name = config.name
    help_name = config.help_name

    @mcp.tool(name=name, description=config.description)
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
        except (FileNotFoundError, OSError) as error:
            raise RuntimeError(
                f"Failed to execute command `{name}`: {error}"
            ) from error

        return CommandExecutionResult(
            command=full_command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @mcp.tool(
        name=help_name,
        description=f"Show help of `{config.name}` tool by running `{config.help_command_display}`.",
    )
    def run_help_command() -> CommandExecutionResult:
        try:
            result = subprocess.run(
                config.help_command,
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise RuntimeError(
                f"Failed to execute command `{help_name}`: {error}"
            ) from error

        return CommandExecutionResult(
            command=config.help_command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


if __name__ == "__main__":
    main()
