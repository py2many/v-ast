"""PEP 517 backend for v-ast.

Build outputs include:
- Python package `py_match_parser`
- Native V shared library
- CPython extension that calls into the V shared library
- Native parser executable fallback
"""

from __future__ import annotations

import base64
import hashlib
import os
import pathlib
import shlex
import subprocess
import sys
import sysconfig
import tempfile
import zipfile


NAME = "v-ast"
VERSION = "0.1.0"
ROOT = pathlib.Path(__file__).resolve().parent
PACKAGE_DIR = ROOT / "py_match_parser"
VSRC_DIR = ROOT / "vlang_match_parser"
EXT_SOURCE = PACKAGE_DIR / "_vext.c"
BINARY_BASENAME = "v_ast_parser"


def _dist_info_dir() -> str:
    return f"{NAME.replace('-', '_')}-{VERSION}.dist-info"


def _wheel_tag() -> str:
    platform = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    return f"py3-none-{platform}"


def _wheel_name() -> str:
    return f"{NAME.replace('-', '_')}-{VERSION}-{_wheel_tag()}.whl"


def _metadata() -> str:
    return "\n".join(
        [
            "Metadata-Version: 2.1",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: V-based parser for a modified Python dialect with match as an expression.",
            "Requires-Python: >=3.11",
            "",
        ]
    )


def _wheel_file() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: v-ast-local-backend",
            "Root-Is-Purelib: false",
            f"Tag: {_wheel_tag()}",
            "",
        ]
    )


def _record_line(path: str, data: bytes) -> tuple[str, str, str]:
    digest = hashlib.sha256(data).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return path, f"sha256={b64}", str(len(data))


def _run_checked(cmd: list[str], cwd: pathlib.Path | None = None) -> None:
    proc = subprocess.run(cmd, cwd=cwd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "command failed"
        rendered = " ".join(shlex.quote(x) for x in cmd)
        raise RuntimeError(f"{rendered}: {message}")


def _shared_lib_name() -> str:
    if os.name == "nt":
        return "v_ast_parser.dll"
    if sys.platform == "darwin":
        return "libv_ast_parser.dylib"
    return "libv_ast_parser.so"


def _build_shared_library() -> tuple[str, bytes]:
    libname = _shared_lib_name()
    with tempfile.TemporaryDirectory() as tmpdir:
        out = pathlib.Path(tmpdir) / libname
        _run_checked(["v", "-enable-globals", "-shared", "-o", str(out), str(VSRC_DIR)], cwd=ROOT)
        return libname, out.read_bytes()


def _build_binary() -> tuple[str, bytes]:
    suffix = ".exe" if os.name == "nt" else ""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = pathlib.Path(tmpdir) / f"{BINARY_BASENAME}{suffix}"
        _run_checked(["v", "-enable-globals", "-o", str(out), str(VSRC_DIR)], cwd=ROOT)
        return out.name, out.read_bytes()


def _build_python_extension() -> tuple[str, bytes]:
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    include_dir = sysconfig.get_paths().get("include")
    if not include_dir:
        raise RuntimeError("unable to locate Python include directory")
    with tempfile.TemporaryDirectory() as tmpdir:
        out = pathlib.Path(tmpdir) / f"_vext{ext_suffix}"
        cmd = ["cc", "-O2", "-fPIC", "-I", include_dir, str(EXT_SOURCE), "-shared", "-o", str(out)]
        if sys.platform == "darwin":
            cmd.extend(["-undefined", "dynamic_lookup"])
        elif os.name != "nt":
            cmd.append("-ldl")
        _run_checked(cmd, cwd=ROOT)
        return out.name, out.read_bytes()


def _write_entry(zf: zipfile.ZipFile, arcname: str, data: bytes, mode: int) -> tuple[str, str, str]:
    info = zipfile.ZipInfo(arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3  # Unix mode bits
    info.external_attr = (mode & 0xFFFF) << 16
    zf.writestr(info, data)
    return _record_line(arcname, data)


def get_requires_for_build_wheel(config_settings=None):  # noqa: D401
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel_dir = pathlib.Path(wheel_directory)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    wheel_path = wheel_dir / _wheel_name()
    dist_info = _dist_info_dir()

    ext_name, ext_data = _build_python_extension()
    lib_name, lib_data = _build_shared_library()
    bin_name, bin_data = _build_binary()

    rows: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for py in sorted(PACKAGE_DIR.rglob("*.py")):
            arcname = py.relative_to(ROOT).as_posix()
            rows.append(_write_entry(zf, arcname, py.read_bytes(), 0o644))

        rows.append(_write_entry(zf, f"{PACKAGE_DIR.name}/{ext_name}", ext_data, 0o755))
        rows.append(_write_entry(zf, f"{PACKAGE_DIR.name}/{lib_name}", lib_data, 0o755))
        rows.append(_write_entry(zf, f"{PACKAGE_DIR.name}/_bin/{bin_name}", bin_data, 0o755))

        for src in sorted(VSRC_DIR.glob("*.v")):
            rows.append(
                _write_entry(
                    zf,
                    f"{PACKAGE_DIR.name}/_vsrc/{src.name}",
                    src.read_bytes(),
                    0o644,
                )
            )

        metadata_path = f"{dist_info}/METADATA"
        rows.append(_write_entry(zf, metadata_path, _metadata().encode("utf-8"), 0o644))

        wheel_meta_path = f"{dist_info}/WHEEL"
        rows.append(_write_entry(zf, wheel_meta_path, _wheel_file().encode("utf-8"), 0o644))

        record_path = f"{dist_info}/RECORD"
        record_lines = [",".join(row) for row in rows]
        record_lines.append(f"{record_path},,")
        record_data = ("\n".join(record_lines) + "\n").encode("utf-8")
        _write_entry(zf, record_path, record_data, 0o644)

    return wheel_path.name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return build_wheel(wheel_directory, config_settings, metadata_directory)


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    meta_dir = pathlib.Path(metadata_directory) / _dist_info_dir()
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "METADATA").write_text(_metadata(), encoding="utf-8")
    (meta_dir / "WHEEL").write_text(_wheel_file(), encoding="utf-8")
    (meta_dir / "RECORD").write_text("", encoding="utf-8")
    return meta_dir.name


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)
