from pathlib import Path
from typing import Union

MAGIC = b"KAUDIO"
TERMINATOR = b"." * 10
FORMAT_SEPARATOR = b":"

SUPPORTED_FORMATS = {"FLAC", "WAV", "MP3", "MIDI"}

BytesSource = Union[bytes, bytearray, memoryview]

def encode(data: BytesSource, file_format: str) -> bytes:
    fmt = file_format.upper()

    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Not supported format: {file_format}." f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")

    header = MAGIC + TERMINATOR + fmt.encode("ascii") + FORMAT_SEPARATOR
    return header + bytes(data)

def decode(data: BytesSource) -> tuple[str, bytes]:
    raw = bytes(data)
    prefix = MAGIC + TERMINATOR

    if not raw.startswith(prefix):
        raise ValueError("Inappropriate KAD header")
    
    format_start = len(prefix)
    format_end = raw.find(FORMAT_SEPARATOR, format_start)

    if format_end == -1:
        raise ValueError("No format separator")
    
    try:
        file_format = raw[format_start:format_end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("Inappropirate format identificator") from exc
    
    if file_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Not supported KAD file format: {file_format}")
    
    payload = raw[format_end + len(FORMAT_SEPARATOR):]
    return file_format, payload

def encode_file(source: str, destination: str) -> None:
    path = Path(source)
    extension = path.suffix.lower()

    formats = {
        ".flac": "FLAC",
        ".wav": "WAV",
        ".mp3": "MP3",
        ".mid": "MIDI",
        ".midi": "MIDI",
    }

    if extension not in formats:
        raise ValueError(f"Not supported file format: {extension}")
    
    kad_data = encode(path.read_bytes(), formats[extension])
    Path(destination).write_bytes(kad_data)

def decode_file(source: str, destination: str) -> str:
    file_format, payload = decode(Path(source).read_bytes())
    Path(destination).write_bytes(payload)
    return file_format