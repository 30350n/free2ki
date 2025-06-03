#!/usr/bin/env python3

from argparse import ArgumentParser
from itertools import chain
from pathlib import Path
from sys import stderr
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

NAMESPACES = {"": "https://wiki.freecad.org/Package_Metadata"}

PACKAGE_XML = "package.xml"
DEFAULT_FILES = (
    "LICENSE",
    PACKAGE_XML,
    "README.md",
)


def build_freecad_package(
    source_path: Path = Path(), output_path: Path = Path(), extra_files: list[Path] = []
) -> bool:
    package_metadata = ET.fromstring((source_path / PACKAGE_XML).read_text())
    if (version := package_metadata.find("version", NAMESPACES)) is None or not version.text:
        error(f"failed to find 'version' in '{PACKAGE_XML}'")
        return False

    if (
        (content := package_metadata.find("content", NAMESPACES)) is None
        or (workbench := content.find("workbench", NAMESPACES)) is None
        or (subdirectory := workbench.find("subdirectory", NAMESPACES)) is None
        or not subdirectory.text
    ):
        error(f"failed to find 'content.workbench.subdirectory' in '{PACKAGE_XML}'")
        return False

    package_path = source_path / subdirectory.text

    extra_paths = []
    for extra_file in extra_files:
        if (path := package_path / extra_file).is_dir():
            extra_paths += list(filter(lambda p: not p.is_dir(), path.glob("**/*")))
        elif path.is_file():
            extra_paths.append(path)
        else:
            warning(f"failed to add extra file '{extra_file}' (no such file)")

    version_name = f"free2ki_v{version.text.replace('.', '-')}"
    zip_file_path = output_path / f"{version_name}.zip"
    with ZipFile(zip_file_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        paths = chain(
            package_path.glob("**/*.py"),
            package_path.glob("**/*.ui"),
            extra_paths,
            (source_path / filename for filename in DEFAULT_FILES),
        )
        for filepath in paths:
            zip_file.write(filepath, f"{version_name}/{filepath.relative_to(source_path)}")

    return True


def warning(*values: object, prefix: str = "warning: "):
    output = f"\033[93m{prefix}{' '.join(map(str, values))}\033[0m"
    print(output)


def error(*values: object, prefix: str = "error: "):
    output = f"\033[91m{prefix}{' '.join(map(str, values))}\033[0m"
    print(output, file=stderr)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--source", default="", help="package source directory")
    parser.add_argument("--out", default="", help="output directory")
    parser.add_argument(
        "--extra-files",
        nargs="*",
        default=[],
        help="path to extra addon files (relative to package subdirectory)",
    )
    args = parser.parse_args()

    extra_files = [Path(extra_file) for extra_file in args.extra_files]
    if not build_freecad_package(Path(args.source), Path(args.out), extra_files):
        exit(1)
