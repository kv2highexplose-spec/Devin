"""File and text operations shared by the desktop utilities."""

import hashlib
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}
CATEGORIES = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
    "Archives": {".zip", ".7z", ".rar", ".tar", ".gz"},
    "Installers": {".exe", ".msi", ".msix", ".msixbundle"},
}


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path
    size: int
    modified_ns: int


def _file_move(source: Path, destination: Path) -> Move:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Not a regular file: {source}")
    info = source.stat()
    return Move(source, destination, info.st_size, info.st_mtime_ns)


def _validate_name(name: str) -> None:
    if not name or name.endswith((" ", ".")) or INVALID_NAME.search(name):
        raise ValueError(f"Invalid Windows filename: {name!r}")
    if name.split(".")[0].upper() in RESERVED_NAMES:
        raise ValueError(f"Reserved Windows filename: {name!r}")


def validate_moves(moves: list[Move]) -> None:
    sources = set()
    destinations = set()
    for move in moves:
        source_key = str(move.source.absolute()).casefold()
        target_key = str(move.destination.absolute()).casefold()
        if source_key in sources or target_key in destinations:
            raise ValueError("The selection contains duplicate sources or destinations")
        if move.source == move.destination or source_key == target_key:
            raise ValueError(f"Source and destination are the same: {move.source}")
        if move.destination.exists() or move.destination.is_symlink():
            raise FileExistsError(f"Destination already exists: {move.destination}")
        sources.add(source_key)
        destinations.add(target_key)
    if destinations & sources:
        raise ValueError("A destination is another selected source; rename in separate steps")


def rename_plan(
    files: list[Path], find: str = "", replace: str = "", prefix: str = "",
    suffix: str = "", numbering: bool = False, start: int = 1,
) -> list[Move]:
    if replace and not find:
        raise ValueError("Enter text to find before using replacement")
    if start < 0:
        raise ValueError("Starting number must be nonnegative")
    moves = []
    for index, source in enumerate(files):
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Not a regular file: {source}")
        number = f"{start + index:03d}_" if numbering else ""
        name = f"{prefix}{number}{source.stem.replace(find, replace) if find else source.stem}{suffix}{source.suffix}"
        _validate_name(name)
        if name != source.name:
            moves.append(_file_move(source, source.with_name(name)))
    validate_moves(moves)
    return moves


def sort_plan(folder: Path) -> list[Move]:
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    extensions = {extension: category for category, values in CATEGORIES.items() for extension in values}
    moves = []
    for source in sorted(folder.iterdir(), key=lambda path: path.name.casefold()):
        if source.is_symlink() or not source.is_file():
            continue
        category = extensions.get(source.suffix.lower(), "Other")
        moves.append(_file_move(source, folder / category / source.name))
    validate_moves(moves)
    return moves


def execute_moves(moves: list[Move]) -> None:
    validate_moves(moves)
    for move in moves:
        info = move.source.stat()
        if info.st_size != move.size or info.st_mtime_ns != move.modified_ns:
            raise ValueError(f"File changed since preview: {move.source}")
    completed = []
    created = []
    try:
        for move in moves:
            parent = move.destination.parent
            if not parent.exists():
                parent.mkdir()
                created.append(parent)
            if move.destination.exists() or move.destination.is_symlink():
                raise FileExistsError(f"Destination already exists: {move.destination}")
            move.source.rename(move.destination)
            completed.append(move)
    except OSError:
        for move in reversed(completed):
            move.destination.rename(move.source)
        for parent in reversed(created):
            parent.rmdir()
        raise


def duplicate_groups(folder: Path) -> tuple[list[list[Path]], list[Path]]:
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    by_size = defaultdict(list)
    skipped = []
    for root, directories, files in os.walk(folder, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in files:
            path = Path(root) / name
            try:
                if not path.is_symlink():
                    by_size[path.stat().st_size].append(path)
            except OSError:
                skipped.append(path)

    groups = []
    for paths in by_size.values():
        if len(paths) < 2:
            continue
        by_digest = defaultdict(list)
        for path in paths:
            digest = hashlib.sha256()
            try:
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                by_digest[digest.hexdigest()].append(path)
            except OSError:
                skipped.append(path)
        groups.extend(sorted(paths) for paths in by_digest.values() if len(paths) > 1)
    return sorted(groups, key=lambda group: str(group[0])), skipped


def transform_text(text: str, action: str) -> str:
    lines = text.splitlines()
    ending = "\n" if text.endswith(("\n", "\r")) else ""
    if action == "Trim lines":
        lines = [line.strip() for line in lines]
    elif action == "Remove empty lines":
        lines = [line for line in lines if line.strip()]
    elif action == "Unique lines":
        lines = list(dict.fromkeys(lines))
    elif action == "Sort lines":
        lines = sorted(lines, key=str.casefold)
    elif action == "Collapse spaces":
        lines = [re.sub(r"[ \t]+", " ", line) for line in lines]
    else:
        raise ValueError(f"Unknown action: {action}")
    return "\n".join(lines) + ending
