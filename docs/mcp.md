# MCP：从源码构建、安装与接入

[返回 README](../README_CN.md) | [English](mcp.en.md) | [DeepAgent 接入](deepagent.md)

通过 stdio MCP 为已有 Agent 增加电脑操作能力，模型配置继续由 Agent 客户端管理。

## 1. 准备环境

安装 Python 3.12 或更高版本及 `uv`。构建和 MCP 服务均在被操作桌面的电脑上运行。

在需要操作桌面的目标电脑上准备原生依赖：

| 平台 | 环境要求 |
| --- | --- |
| macOS | macOS 14 或更高版本、包含 Swift 6 的 Xcode 工具链，以及辅助功能和屏幕录制权限。 |
| Windows | Windows x64、.NET Framework 4.8 及其 C# 编译器；窗口截图需要 Windows 10 1903 或更高版本。 |
| Linux | 包含 AT-SPI 和 PyGObject 的图形桌面会话；截图和鼠标输入使用 X11。 |

Debian 或 Ubuntu 需要先安装 Linux 系统依赖：

```bash
sudo apt install python3-gi python3-venv gir1.2-atspi-2.0 libx11-6 libxkbcommon0
```

## 2. 安装源码并构建后端

```bash
git clone https://gitcode.com/openJiuwen/computer-use.git
cd computer-use
uv sync --no-dev
```

SDK 和 MCP 服务以 editable 方式安装到仓库的 `.venv`，不安装模型依赖。以下命令均在仓库根目录执行。

构建或准备原生后端，并检查桌面访问条件：

```bash
uv run --no-dev computer-use-build
uv run --no-dev computer-use-permissions
```

macOS 可运行 `uv run --no-dev computer-use-permissions --request` 请求缺失权限，在**系统设置 → 隐私与安全**中批准后重新检查。请使用与启动 SDK 或其 MCP 接入层相同的终端或宿主连接执行这些命令。

## 3. 接入自己的 Agent

完成上述源码安装、平台依赖准备和后端构建后，即可把 MCP 服务接入自己的 Agent。
服务在被操作桌面的电脑上运行，使用独立的 `.venv`，由 Agent 客户端通过 stdio 启动和调用。
Agent 需支持 MCP 工具调用；要使用截图，还需客户端和模型支持图片输入。

**1. 配置连接器。** 在 Agent 的 MCP 配置中添加 `computer-use`。
对于采用 `mcpServers` 格式的客户端，macOS / Linux 可使用：

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

将 `command` 替换为本机源码仓库中启动程序的绝对路径。
Windows 对应路径为 `C:/absolute/path/to/computer-use/.venv/Scripts/computer-use-mcp.exe`。
`PYTHONSAFEPATH=1` 用于避免宿主工作目录中的同名文件夹遮蔽 SDK 包。

如果客户端提供连接器表单（例如 WorkSwarm），选择 **stdio** 类型，名称填写 `computer-use`，
命令填写上述可执行文件路径，参数填写 `--desktop exclusive`，并添加环境变量 `PYTHONSAFEPATH=1`。
其配置存储位置和启用方式由客户端管理。

需要手动启动服务调试时，也可在仓库根目录运行：

```bash
uv run --no-dev computer-use-mcp --desktop exclusive
```

通过 wheel 安装时，在相应环境安装 wheel，例如
`uv pip install /absolute/path/to/computer_use_toolkit-0.0.1-py3-none-any.whl`，
然后在该环境运行 `computer-use-mcp`。

**2. 启用并验证连接。** 保存配置后，启用连接器并重新连接 MCP；必要时重启 Agent 客户端。
确认客户端能发现 `computer_use` 和 `computer_use_reset` 两个工具，然后向 Agent 发送：

```text
请使用 computer_use 列出正在运行的应用，确认能够调用本机后端。
```

工具中已提供 `computer`、`print()` 和 `print_image()`，对应的首次验证代码为：

```python
print(await computer.list_apps())
```

应看到后端返回的应用列表。工具发现确认 MCP 连通，应用枚举确认 Agent 能实际调用本机后端。
随后可选择一个有窗口的应用，执行下文的 `await app.read(view="both")`，核对界面文字与截图，
并按前述说明授予所需平台权限。`computer_use_reset` 可用于清空当前 Python 执行会话。

**3. 更新源码后重新加载。** 修改 Python 源码后，重启 MCP 连接以加载新代码；
修改依赖或启动入口后，先重新运行 `uv sync --no-dev`。
修改原生后端后，先运行 `uv run --no-dev computer-use-build`，再重启 MCP 连接。

`exclusive` 允许必要的前台准备和整桌面输入；`shared` 将输入限制在选定的 App 或 Window 范围内。上述配置显式选择 `exclusive`；如需共享模式，将参数改为 `--desktop shared`。不显式指定时读取 `COMPUTER_USE_DESKTOP`，默认值为 `shared`。桌面模式不能替代操作系统权限。

## 4. 接口使用参考

通过 `computer.app(id)` 选择应用，用 `await app.read(view="both")` 观察界面，再用 `await app.element(name_or_path)` 定位控件后执行操作。

### Python SDK

将以下示例保存为 `list_apps.py`，通过 `uv run python list_apps.py` 运行：

```python
import asyncio

from computer_use import Computer


async def main():
    computer = Computer()
    for app in await computer.list_apps():
        print(app.id, app.display_name, app.is_running)


asyncio.run(main())
```
