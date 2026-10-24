from pathlib import Path, PurePosixPath
import struct
import zlib

MAGIC = b"KARCHIVE" + b"." * 10
VERSION = 1

METHOD_STORED = 0
METHOD_ZLIB = 1

MAX_FILES = 1_000_000
MAX_NAME_LENGTH = 65535
MAX_FILE_SIZE = 1 << 40

def _safe_name(name):
    if not isinstance(name, str) or not name:
        raise ValueError("Invalid file name")

    if "\x00" in name or "\\" in name:
        raise ValueError("Invalid characters in file name")
    
    path = PurePosixPath(name)

    if path.is_absolute() or any(part in ("..", ".") for part in path.parts):
        raise ValueError(f"Unsafe archive path: {name}")
    
    if not path.parts:
        raise ValueError("Empty archive path")

    normalized = path.as_posix()

    if len(normalized.encode("utf-8")) > MAX_NAME_LENGTH:
        raise ValueError("File name is too long")
    
    return normalized

def _pack_entry(name, data):
    name = _safe_name(name)
    name_bytes = name.encode("utf-8")

    if len(data) > MAX_FILE_SIZE:
        raise ValueError("File is too large")
    
    compressed = zlib.compress(data)

    if len(compressed) < len(data):
        method = METHOD_ZLIB
        payload = compressed
    else:
        method = METHOD_STORED
        payload = data
    
    header = (struct.pack("<H", len(name_bytes)) + name_bytes + struct.pack("<BQQ", method, len(data), len(payload)))
    return header + payload

def _write_archive(destination, entries):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if len(entries) > MAX_FILES:
        raise ValueError("Too many files")
    
    with destination.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<BI", VERSION, len(entries)))

        for name, data in entries:
            f.write(_pack_entry(name, data))

def _read_archive(source):
    source = Path(source)

    with source.open("rb") as f:
        if f.read(len(MAGIC)) != MAGIC:
            raise ValueError("Not a valid KAR archive")
        
        metadata = f.read(5)
        if len(metadata) != 5:
            raise ValueError("Incomlpete KAR header")

        version, count = struct.unpack("<BI", metadata)

        if version != VERSION:
            raise ValueError(f"Unsupported KAR version: {version}")
        
        if count > MAX_FILES:
            raise ValueError("Too many files in archive")
        
        entries = []
        seen_names = set()

        for _ in range(count):
            raw_len = f.read(2)
            if len(raw_len) != 2:
                raise ValueError("Incomplete file nae length")
            
            name_len = struct.unpack("<H", raw_len)[0]
            name_bytes = f.read(name_len)

            if len(name_bytes) != name_len:
                raise ValueError("Incomplete file name")
            
            try:
                name = name_bytes.decode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("Invalid UTF-8 file name") from exc
            
            name = _safe_name(name)

            if name in seen_names:
                raise ValueError(f"Duplicate file: {name}")
            seen_names.add(name)

            raw_header = f.read(17)
            if len(raw_header) != 17:
                raise ValueError("Incomplete file header")
            
            method, original_size, stored_size = struct.unpack("<BQQ", raw_header)

            if original_size > MAX_FILE_SIZE:
                raise ValueError("File exceeds size limit")
            # lets hope that no archive will be having a file that has 1 TiB
            
            remaining = source.stat().st_size - f.tell()
            if stored_size > remaining:
                raise ValueError("Incomplete file data")
            
            payload = f.read(stored_size)

            if len(payload) != stored_size:
                raise ValueError("Incomplete file data")
            
            if method == METHOD_STORED:
                data = payload
            
            elif method == METHOD_ZLIB:
                try:
                    decoder = zlib.decompressobj()
                    data = decoder.decompress(payload, original_size + 1)

                    if (len(data) > original_size or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data):
                        raise ValueError("Invalid compressed data")
                
                except zlib.error as exc:
                    raise ValueError("Corrupted compressed data") from exc
            
            else:
                raise ValueError(f"Unsupported compression method: {method}")

            if len(data) != original_size:
                raise ValueError("Original file size mismatch")
            
            entries.append((name, data))
        
        if f.read(1):
            raise ValueError("Unexpected data after KAR archive")
    
    return entries

def create(files, destination):
    entries = []
    seen = set()

    for item in files:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            source, archive_name = item
        else:
            source = item
            archive_name = Path(source).name
        
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        
        name = _safe_name(str(archive_name))

        if name in seen:
            raise ValueError(f"Duplicate file: {name}")
        seen.add(name)

        entries.append((name, source.read_bytes()))
    
    _write_archive(destination, entries)

def list_files(source):
    entries = _read_archive(source)

    return [{"name": name, "size": len(data)} for name, data in entries]

def extract(source, output_dir="."):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = _read_archive(source)

    destinations = []

    for name, _ in entries:
        target = (output_dir / name).resolve()

        if not target.is_relative_to(output_dir):
            raise ValueError(f"Unsafe extraction path: {name}")

        current = output_dir
        for part in PurePosixPath(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"Symbolic link in extraction path: {name}")

        if target.exists() and target.is_dir():
            raise ValueError(f"Destination is a directory: {name}")

        destinations.append(target)

    for (name, data), target in zip(entries, destinations):
        target.parent.mkdir(parents=True, exist_ok=True)

        resolved_parent = target.parent.resolve()
        if not resolved_parent.is_relative_to(output_dir):
            raise ValueError(f"Unsafe extraction path: {name}")

        with target.open("wb") as f:
            f.write(data)

def add_file(source, file_to_add, archive_name=None):
    entries = _read_archive(source)

    file_to_add = Path(file_to_add)
    if not file_to_add.is_file():
        raise FileNotFoundError(file_to_add)

    if archive_name is None:
        archive_name = file_to_add.name

    archive_name = _safe_name(str(archive_name))

    if any(name == archive_name for name, _ in entries):
        raise ValueError(f"File already exists: {archive_name}")

    entries.append((archive_name, file_to_add.read_bytes()))
    _write_archive(source, entries)           