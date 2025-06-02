#!/usr/bin/env python3

from argparse import ArgumentParser
from itertools import chain
from pathlib import Path
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
    path: Path = Path(),
    output_path: Path = Path(),
    extra_files: list[Path] = [],
):
    package_metadata = ET.fromstring((path / PACKAGE_XML).read_text())
    version = package_metadata.find("version", NAMESPACES).text

    workbench = package_metadata.find("content", NAMESPACES).find("workbench", NAMESPACES)
    subdirectory = workbench.find("subdirectory", NAMESPACES).text
    package_path = path / subdirectory

    version_name = f"free2ki_v{version.replace('.', '-')}"
    zip_file_path = output_path / f"{version_name}.zip"
    with ZipFile(zip_file_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        paths = chain(
            package_path.glob("**/*.py"),
            package_path.glob("**/*.ui"),
            (package_path / extra_file for extra_file in extra_files),
            (path / filename for filename in DEFAULT_FILES),
        )
        for filepath in paths:
            zip_file.write(filepath, f"{version_name}/{filepath.relative_to(path)}")


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

    build_freecad_package(
        Path(args.source), Path(args.out), [Path(extra_file) for extra_file in args.extra_files]
    )
