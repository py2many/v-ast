"""Minimal PEP 517 backend for this repository.

This backend builds a wheel for the local `py_match_parser` package without
requiring third-party build dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import pathlib
import zipfile


NAME = "v-ast"
VERSION = "0.1.0"
PACKAGE_DIR = pathlib.Path("py_match_parser")


def _dist_info_dir() -> str:
    return f"{NAME.replace('-', '_')}-{VERSION}.dist-info"


def _wheel_name() -> str:
    return f"{NAME.replace('-', '_')}-{VERSION}-py3-none-any.whl"


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
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _record_line(path: str, data: bytes) -> tuple[str, str, str]:
    digest = hashlib.sha256(data).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return path, f"sha256={b64}", str(len(data))


def get_requires_for_build_wheel(config_settings=None):  # noqa: D401
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel_dir = pathlib.Path(wheel_directory)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    wheel_path = wheel_dir / _wheel_name()
    dist_info = _dist_info_dir()

    rows: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for py in sorted(PACKAGE_DIR.rglob("*.py")):
            arcname = py.as_posix()
            data = py.read_bytes()
            zf.writestr(arcname, data)
            rows.append(_record_line(arcname, data))

        metadata_path = f"{dist_info}/METADATA"
        metadata_data = _metadata().encode("utf-8")
        zf.writestr(metadata_path, metadata_data)
        rows.append(_record_line(metadata_path, metadata_data))

        wheel_meta_path = f"{dist_info}/WHEEL"
        wheel_meta_data = _wheel_file().encode("utf-8")
        zf.writestr(wheel_meta_path, wheel_meta_data)
        rows.append(_record_line(wheel_meta_path, wheel_meta_data))

        record_path = f"{dist_info}/RECORD"
        record_lines = []
        for row in rows:
            record_lines.append(",".join(row))
        record_lines.append(f"{record_path},,")
        record_data = ("\n".join(record_lines) + "\n").encode("utf-8")
        zf.writestr(record_path, record_data)

    return wheel_path.name


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    # For this project, editable install can use the same pure-Python wheel.
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
