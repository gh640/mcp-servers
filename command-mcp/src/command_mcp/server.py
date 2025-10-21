import argparse
import shlex
import subprocess
from dataclasses import dataclass
from typing import Self

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class CliArgs:
    command: list[str]
    description: str
    command_help: list[str]


@dataclass(frozen=True)
class ServerConfig:
    name: str
    command: list[str]
    description: str
    command_help: list[str]

    @classmethod
    def from_cli_args(cls, args: CliArgs) -> Self:
        return cls(
            name=args.command[0],
            command=args.command,
            description=args.description,
            command_help=args.command_help,
        )

    @property
    def help_name(self) -> str:
        return f"{self.name}-help"

    @property
    def command_display(self) -> str:
        return shlex.join(self.command)

    @property
    def command_help_display(self) -> str:
        return shlex.join(self.command_help)


class CommandExecutionResult(BaseModel):
    command: list[str] = Field(description="Full command that was executed")
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(description="Captured standard output")
    stderr: str = Field(description="Captured standard error")


def main() -> None:
    args = _parse_cli_args()
    config = ServerConfig.from_cli_args(args)
    mcp = _create_mcp(config)
    mcp.run(transport="stdio")


def _parse_cli_args() -> CliArgs:
    parser = argparse.ArgumentParser(
        description="Expose a shell command via MCP",
    )
    parser.add_argument(
        "--command",
        required=True,
        type=_parse_command,
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
        type=_parse_command,
        help="Help command that explains usage (e.g., 'git --help')",
    )

    parsed = parser.parse_args()

    return CliArgs(
        command=parsed.command,
        description=parsed.description,
        command_help=parsed.command_help,
    )


def _parse_command(value: str) -> list[str]:
    parts = shlex.split(value)

    if not parts:
        raise argparse.ArgumentTypeError(f"command is empty: {value!r}")

    return parts


def _create_mcp(config: ServerConfig) -> FastMCP:
    name = config.name
    command = config.command
    help_name = config.help_name

    instructions_lines = [
        "This MCP server wraps a shell command.",
        "",
        f"- Invoke the `{name}` tool to run `{config.command_display}`.",
        "    - Provide arguments via the `arguments` parameter.",
        "    - Optional stdin can be set via `stdin`.",
    ]

    if len(command) > 1:
        fixed_args = shlex.join(command[1:])
        instructions_lines.append(
            f"    - Fixed arguments `{fixed_args}` are automatically prepended and be sure to pass only additional arguments."
        )

    instructions_lines.extend([
        "",
        f"- Use the `{help_name}` resource to review the command help.",
    ])

    mcp = FastMCP(
        "Command MCP",
        instructions="\n".join(instructions_lines),
    )

    @mcp.tool(name=name, description=config.description)
    def run_command(
        arguments: list[str] = Field(
            default_factory=list,
            description="Additional command-line arguments appended to the base command",
        ),
        stdin: str | None = Field(
            default=None,
            description="Optional standard input string piped to the command",
        ),
    ) -> CommandExecutionResult:
        return _run([*command, *arguments], stdin)

    @mcp.resource(
        f"command-mcp-help://{name}",
        name=help_name,
        description=f"Show help of `{name}` tool by running `{config.command_help_display}`.",
    )
    def run_help_command() -> str:
        result = _run(config.command_help, None)
        return result.stdout

    return mcp


def _run(args: list[str], input: str | None) -> CommandExecutionResult:
    try:
        result = subprocess.run(
            args,
            input=input,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError) as error:
        args_joined = shlex.join(args)
        raise RuntimeError(
            f"Failed to execute command `{args_joined}`: {error}"
        ) from error

    return CommandExecutionResult(
        command=args,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


if __name__ == "__main__":
    main()
