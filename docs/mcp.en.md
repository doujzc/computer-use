# MCP: build, install and integrate from source

[Back to README](../README.md) | [简体中文](mcp.md) | [DeepAgent integration](deepagent.en.md)

Add desktop operation tools to an existing agent over stdio MCP. The agent client continues to manage its model configuration.

## 1. Prepare the environment

Install Python 3.12 or later and `uv`. Build and run the MCP server on the computer whose desktop it will operate.

Prepare the native dependencies on the computer whose desktop you will operate:

| Platform | Requirements |
| --- | --- |
| macOS | macOS 14 or later, an Xcode toolchain with Swift 6, Accessibility and Screen Recording permissions. |
| Windows | Windows x64 with .NET Framework 4.8 and its C# compiler; window capture requires Windows 10 1903 or later. |
| Linux | A graphical desktop session with AT-SPI and PyGObject. Use X11 for screenshots and mouse input. |

On Debian or Ubuntu, install the Linux system dependencies first:

```bash
sudo apt install python3-gi python3-venv gir1.2-atspi-2.0 libx11-6 libxkbcommon0
```

## 2. Install from source and build the backend

```bash
git clone https://gitcode.com/openJiuwen/computer-use.git
cd computer-use
uv sync --no-dev
```

The SDK and MCP server are installed in editable mode into the checkout's `.venv`, without model dependencies. Run the following commands from the checkout root.

Build or prepare the native backend, then check desktop access:

```bash
uv run --no-dev computer-use-build
uv run --no-dev computer-use-permissions
```

On macOS, use `uv run --no-dev computer-use-permissions --request` to request missing permissions. Approve them in **System Settings → Privacy & Security**, then run the check again. Run the commands from the same terminal or host connection that will launch the SDK or its MCP adapter.

## 3. Connect your agent

After installing from source, preparing the platform dependencies and building the
backend above, connect the MCP server to your own agent. The server runs on the
computer whose desktop it operates, using its own `.venv`; the agent client starts
and calls it over stdio. The agent must support MCP tool calls. To use screenshots,
the client and model must also support image input.

**1. Configure the connector.** Add `computer-use` to the agent's MCP configuration.
For clients accepting the `mcpServers` format, use this on macOS / Linux:

```json
{
  "mcpServers": {
    "computer-use": {
      "command": "/absolute/path/to/computer-use/.venv/bin/computer-use-mcp",
      "args": ["--desktop", "exclusive"],
      "env": {
        "PYTHONSAFEPATH": "1"
      }
    }
  }
}
```

Replace `command` with the absolute path to the executable in your checkout.
On Windows, use `C:/absolute/path/to/computer-use/.venv/Scripts/computer-use-mcp.exe`.
`PYTHONSAFEPATH=1` prevents same-named directories in the host's working directory
from shadowing the SDK package.

For a connector form, such as WorkSwarm's, select **stdio**, name it `computer-use`,
set the command to the executable path above, set arguments to `--desktop exclusive` and add the
environment variable `PYTHONSAFEPATH=1`. The client manages configuration storage
and connector activation.

For manual server debugging, you can also run this from the checkout root:

```bash
uv run --no-dev computer-use-mcp --desktop exclusive
```

For a wheel installation, install the wheel into its environment, for example
`uv pip install /absolute/path/to/computer_use_toolkit-0.0.1-py3-none-any.whl`,
then run `computer-use-mcp` from that environment.

**2. Enable and verify the connection.** Save the configuration, enable the connector
and reconnect MCP; restart the agent client if needed. Confirm that it discovers
the `computer_use` and `computer_use_reset` tools, then send your agent:

```text
Use computer_use to list the running applications and verify calls to this computer's backend.
```

The tool provides `computer`, `print()` and `print_image()`. The code for this first
check is:

```python
print(await computer.list_apps())
```

You should receive the backend's application list. Tool discovery verifies the MCP
connection; application enumeration verifies that the agent can call the local backend.
Then select an application with a window, use `await app.read(view="both")` as described
below, and check the interface text and screenshot. Grant the required platform
permissions as described above. Use `computer_use_reset` to clear the current Python
execution session.

**3. Reload after source changes.** Restart the MCP connection after editing Python
source. After changing dependencies or entry points, first rerun
`uv sync --no-dev`. After changing the native backend, run
`uv run --no-dev computer-use-build`, then restart the MCP connection.

`exclusive` allows foreground preparation and desktop-wide input; `shared` limits input to the selected App or Window. This configuration explicitly selects `exclusive`; change the arguments to `--desktop shared` for shared mode. Without an explicit argument, `COMPUTER_USE_DESKTOP` is used, defaulting to `shared`. Desktop mode does not grant operating system permissions.

## 4. Interface reference

Select an application with `computer.app(id)`, observe it with `await app.read(view="both")`, and resolve a control with `await app.element(name_or_path)` before operating it.

### Python SDK

Save this example as `list_apps.py` and run it with `uv run python list_apps.py`:

```python
import asyncio

from computer_use import Computer


async def main():
    computer = Computer()
    for app in await computer.list_apps():
        print(app.id, app.display_name, app.is_running)


asyncio.run(main())
```
