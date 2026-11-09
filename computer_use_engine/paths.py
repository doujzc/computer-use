# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

LINUX_RUNTIME = Path("os_adapter/linux/.build/runtime")


def linux_python():
    command = os.environ.get("COMPUTER_USE_PYTHON")
    if command:
        return shutil.which(command) or command
    system_python = shutil.which("/usr/bin/python3")
    if system_python is not None:
        probe = subprocess.run(
            [
                system_python, "-I", "-S", "-c",
                "import sys; sys.exit(sys.implementation.name != 'cpython' or sys.version_info < (3, 11))",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if probe.returncode == 0:
            return system_python
    return sys.executable


def checkout_root():
    root = Path(__file__).resolve().parents[1]
    return root if (root / "pyproject.toml").is_file() and (root / "os_adapter").is_dir() else None


@lru_cache(maxsize=1)
def repository_root():
    root = checkout_root()
    if root is not None:
        return root
    # Materialize packaged resources in an atomic, user-owned runtime tree.
    # Legacy builds can prepare their driver without writing to site-packages.
    assets = Path(__file__).parent / "_resources"
    manifest = (assets / "manifest.json").read_bytes()
    key = hashlib.sha256(manifest).hexdigest()[:20]
    directory = Path.home() / ".computer-use/runtime"
    target = directory / key
    if target.is_dir():
        return target
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = Path(tempfile.mkdtemp(prefix=".prepare-", dir=directory))
    try:
        shutil.copytree(assets, temporary, dirs_exist_ok=True)
        try:
            os.rename(temporary, target)
        except OSError:
            if not target.is_dir():
                raise
        return target
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def native_driver(platform=None, root=None):
    platform, root = platform or sys.platform, Path(root) if root is not None else repository_root()
    if platform == "darwin":
        return dict(
            command=str(root / "os_adapter/macos/.build/ComputerUseDriver.app/Contents/MacOS/computer-use-driver"),
            args=[],
        )
    if platform == "linux":
        if (root / LINUX_RUNTIME / "__main__.py").is_file():
            # CPython adds the entry directory itself to the import path, including with -I.
            return dict(command=linux_python(), args=["-I", str(root / LINUX_RUNTIME)])
        return dict(command=str(root / "os_adapter/linux/.venv/bin/python"), args=["-m", "computer_use_linux"])
    if platform == "win32":
        return dict(command=str(root / "os_adapter/windows/.build/computer-use-driver.exe"), args=[])
    raise RuntimeError(f"platform {platform} is not implemented")
