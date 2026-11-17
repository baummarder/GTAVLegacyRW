"""Reader and writer for GTA San Andreas ``.img`` archives (VER2).

The format is a flat container: an 8-byte header, a directory of fixed-size
32-byte records and the file data itself, aligned to 2048-byte sectors::

    "VER2"                4 bytes
    entry count           4 bytes (uint32, little endian)
    entry * count        32 bytes each
    data                  sector aligned

Each directory record is::

    offset                4 bytes (uint32, in sectors)
    streaming size        2 bytes (uint16, in sectors)
    size in archive       2 bytes (uint16, always 0)
    name                 24 bytes (null terminated, max 23 characters)

Files are copied sector by sector, so this module rebuilds an archive without
loading it into memory.
"""

from __future__ import annotations

import logging
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SECTOR_SIZE = 2048
HEADER_SIZE = 8
ENTRY_SIZE = 32
MAGIC = b"VER2"
MAX_NAME_LENGTH = 23
MAX_SECTORS = 0xFFFF
COPY_CHUNK = 1024 * 1024

log = logging.getLogger("gtavlegacy.img")


class ImgError(RuntimeError):
    """Raised when an archive cannot be read or written."""


@dataclass(frozen=True)
class Entry:
    """A single file inside an IMG archive."""

    name: str
    offset: int  # in sectors
    sectors: int

    @property
    def byte_offset(self) -> int:
        return self.offset * SECTOR_SIZE

    @property
    def byte_size(self) -> int:
        return self.sectors * SECTOR_SIZE


@dataclass(frozen=True)
class RebuildResult:
    """Summary of a rebuild."""

    total: int
    replaced: int
    added: int
    size: int


@dataclass(frozen=True)
class _PlanItem:
    name: str
    sectors: int
    source_offset: int | None = None
    path: Path | None = None


def _decode_name(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("latin-1")


def _encode_name(name: str) -> bytes:
    encoded = name.encode("latin-1")
    if not encoded:
        raise ImgError("Entry name must not be empty.")
    if len(encoded) > MAX_NAME_LENGTH:
        raise ImgError(
            f"Entry name '{name}' is {len(encoded)} characters long, "
            f"the limit is {MAX_NAME_LENGTH}."
        )
    return encoded.ljust(24, b"\0")


def _sectors_for(byte_size: int) -> int:
    return max(1, -(-byte_size // SECTOR_SIZE))


def read_directory(path: Path) -> list[Entry]:
    """Return all directory entries of a VER2 archive."""
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ImgError(f"Cannot open archive {path}: {exc}") from exc

    if size < HEADER_SIZE:
        raise ImgError(f"{path} is too small to be an IMG archive.")

    with path.open("rb") as handle:
        header = handle.read(HEADER_SIZE)
        if header[:4] != MAGIC:
            raise ImgError(
                f"{path} is not a GTA San Andreas IMG archive "
                f"(expected magic {MAGIC!r}, found {header[:4]!r})."
            )
        count = struct.unpack("<I", header[4:])[0]
        if HEADER_SIZE + count * ENTRY_SIZE > size:
            raise ImgError(
                f"{path} claims {count} entries, which does not fit into "
                f"{size} bytes."
            )

        entries: list[Entry] = []
        for _ in range(count):
            record = handle.read(ENTRY_SIZE)
            offset, streaming, archived = struct.unpack("<IHH", record[:8])
            entries.append(Entry(_decode_name(record[8:]), offset, streaming or archived))

    if any(entry.sectors == 0 for entry in entries):
        entries = _fill_missing_sizes(entries, size)

    return entries


def _fill_missing_sizes(entries: list[Entry], file_size: int) -> list[Entry]:
    """Derive sizes for archives that store them only as 'next offset'."""
    ordered = sorted((entry for entry in entries if entry.sectors), key=lambda e: e.offset)
    offsets = [entry.offset for entry in ordered] + [file_size // SECTOR_SIZE]

    fixed: list[Entry] = []
    for entry in entries:
        if entry.sectors:
            fixed.append(entry)
            continue
        following = next((offset for offset in offsets if offset > entry.offset), None)
        if following is None:
            raise ImgError(f"Cannot determine the size of archive entry '{entry.name}'.")
        fixed.append(Entry(entry.name, entry.offset, following - entry.offset))
    return fixed


def rebuild(
    source: Path,
    destination: Path,
    replacements: dict[str, Path] | None = None,
    additions: Iterable[Path] = (),
) -> RebuildResult:
    """Rebuild ``source`` into ``destination`` with replaced and added files.

    ``replacements`` maps an archive entry name (case insensitive) to a file on
    disk. ``additions`` are files whose names are not yet in the archive.

    ``destination`` must differ from ``source``; write to a temporary path and
    rename it afterwards if an in-place rebuild is needed.
    """
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ImgError("Source and destination archive must be different files.")

    replacement_map = {name.upper(): Path(path) for name, path in (replacements or {}).items()}
    entries = read_directory(source)
    existing = {entry.name.upper() for entry in entries}

    plan: list[_PlanItem] = []
    replaced = 0
    for entry in entries:
        candidate = replacement_map.get(entry.name.upper())
        if candidate is None:
            plan.append(_PlanItem(entry.name, entry.sectors, entry.byte_offset))
            continue
        sectors = _sectors_for(candidate.stat().st_size)
        plan.append(_PlanItem(entry.name, sectors, None, candidate))
        replaced += 1

    added = 0
    for path in sorted(additions, key=lambda item: item.name.upper()):
        path = Path(path)
        name = path.name.upper()
        if name in existing:
            raise ImgError(
                f"'{name}' already exists in {source.name}; pass it as a replacement instead."
            )
        sectors = _sectors_for(path.stat().st_size)
        plan.append(_PlanItem(name, sectors, None, path))
        existing.add(name)
        added += 1

    for item in plan:
        if item.sectors > MAX_SECTORS:
            raise ImgError(
                f"'{item.name}' needs {item.sectors} sectors, the format only allows "
                f"{MAX_SECTORS} ({MAX_SECTORS * SECTOR_SIZE // (1024 * 1024)} MiB)."
            )

    header_bytes = HEADER_SIZE + ENTRY_SIZE * len(plan)
    first_sector = -(-header_bytes // SECTOR_SIZE)
    offsets: list[int] = []
    sector = first_sector
    for item in plan:
        offsets.append(sector)
        sector += item.sectors
    total_sectors = sector

    log.info(
        "      %s: %d entries (%d replaced, %d added)",
        source.name,
        len(plan),
        replaced,
        added,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")

    try:
        with source.open("rb") as reader, temporary.open("wb") as writer:
            writer.write(MAGIC)
            writer.write(struct.pack("<I", len(plan)))
            for item, offset in zip(plan, offsets):
                writer.write(struct.pack("<IHH", offset, item.sectors, 0))
                writer.write(_encode_name(item.name))

            padding = first_sector * SECTOR_SIZE - header_bytes
            if padding:
                writer.write(b"\0" * padding)

            for item, offset in zip(plan, offsets):
                writer.seek(offset * SECTOR_SIZE)
                log.debug("      %s -> sector %d (%d sectors)", item.name, offset, item.sectors)
                if item.path is not None:
                    _copy_file(item.path, writer, item.sectors)
                else:
                    _copy_stream(reader, item.source_offset or 0, writer, item.sectors)

            writer.truncate(total_sectors * SECTOR_SIZE)
            writer.flush()
            os.fsync(writer.fileno())

        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return RebuildResult(
        total=len(plan),
        replaced=replaced,
        added=added,
        size=total_sectors * SECTOR_SIZE,
    )


def _copy_file(path: Path, writer, sectors: int) -> None:
    written = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(COPY_CHUNK)
            if not chunk:
                break
            writer.write(chunk)
            written += len(chunk)

    expected = sectors * SECTOR_SIZE
    if written > expected:
        raise ImgError(f"'{path.name}' grew while it was being written.")
    writer.write(b"\0" * (expected - written))


def _copy_stream(reader, offset: int, writer, sectors: int) -> None:
    reader.seek(offset)
    remaining = sectors * SECTOR_SIZE
    while remaining:
        chunk = reader.read(min(COPY_CHUNK, remaining))
        if not chunk:
            raise ImgError("Unexpected end of archive while copying file data.")
        writer.write(chunk)
        remaining -= len(chunk)
