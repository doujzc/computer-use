# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Build-time contract for backend artifacts exchanged by the build jobs."""

import hashlib
import json
import platform
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

WHEEL_PLATFORMS = {
    "macos-arm64": "macosx_14_0_arm64",
    "windows-x86_64": "win_amd64",
    "linux-x86_64": "linux_x86_64",
}
TARGETS = tuple(WHEEL_PLATFORMS)
PLATFORMS = dict(zip((("darwin", "arm64"), ("win32", "x86_64"), ("linux", "x86_64")), TARGETS))
FORMAT = 1

MAC_BUNDLE = "os_adapter/macos/.build/ComputerUseDriver.app"
MAC_DRIVER = f"{MAC_BUNDLE}/Contents/MacOS/computer-use-driver"
WINDOWS_FILES = {
    f"os_adapter/windows/.build/{name}"
    for name in ("computer-use-driver.exe", "computer-use-capture.exe", "Interop.NativeUIA.dll")
}
LINUX_LOCK = "os_adapter/linux/requirements.lock"
LINUX_WHEEL = re.compile(r"os_adapter/linux/\.build/openjiuwen_computeruse_linux-[\w.+!-]+-py3-none-any\.whl")


def host_target(system=None):
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    system = system or sys.platform
    try:
        return PLATFORMS[system, machine]
    except KeyError:
        raise RuntimeError(f"Cannot build a backend for {system}/{machine}. Supported: {', '.join(TARGETS)}.") from None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_archive(path, target, *, destination=None):
    """Validate the complete selected archive, optionally unpacking into a private staging directory."""
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("backend.json"))
        if manifest["format"] != FORMAT or manifest["target"] != target or target not in TARGETS:
            raise ValueError(f"Invalid backend format or target: {target}")
        files = manifest["files"]
        names = set(files)
        if target == "macos-arm64":
            valid = {MAC_DRIVER, f"{MAC_BUNDLE}/Contents/Info.plist"} <= names and all(
                name.startswith(f"{MAC_BUNDLE}/Contents/") for name in names
            )
            valid = valid and files[MAC_DRIVER]["mode"] == 0o755
        elif target == "windows-x86_64":
            valid = names == WINDOWS_FILES
        else:
            valid = (
                LINUX_LOCK in names
                and len(names) == 2
                and all(name == LINUX_LOCK or LINUX_WHEEL.fullmatch(name) for name in names)
            )
        if (
            not valid
            or set(archive.namelist()) != names | {"backend.json"}
            or len(archive.infolist()) != len(names) + 1
        ):
            raise ValueError(f"Unexpected backend files for {target}")
        for name, entry in files.items():
            relative = PurePosixPath(name)
            if relative.as_posix() != name or ".." in relative.parts or any(char in name for char in "\\:"):
                raise ValueError(f"Invalid backend path: {name}")
            is_link = stat.S_ISLNK(archive.getinfo(name).external_attr >> 16)
            if is_link or entry["mode"] not in (0o644, 0o755):
                raise ValueError(f"Invalid backend file type or mode: {name}")
            data = archive.read(name)
            if digest(data) != entry["sha256"]:
                raise ValueError(f"Backend checksum mismatch: {name}")
            if destination is not None:
                output = Path(destination) / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
                output.chmod(entry["mode"])
        if destination is not None:
            (Path(destination) / "backend.json").write_bytes(canonical(manifest))
    return manifest
