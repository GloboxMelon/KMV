from pathlib import Path

MAGIC = b"KMOVIE"
TERMINATOR = b"." * 10
HEADER_SIZE = len(MAGIC) + len(TERMINATOR)

def encode(mp4_path, kmv_path):
    mp4 = Path(mp4_path).read_bytes()

    with open(kmv_path, "wb") as file:
        file.write(MAGIC)
        file.write(TERMINATOR)
        file.write(mp4)
    
    print(f"Saved.")

def decode(kmv_path, mp4_path):
    data = Path(kmv_path).read_bytes()

    if len(data) < HEADER_SIZE:
        raise ValueError("KMV too short.")
    
    if data[:len(MAGIC)] != MAGIC:
        raise ValueError("Inappropriate KMV header")

    if data[len(MAGIC):HEADER_SIZE] != TERMINATOR:
        raise ValueError("Inappropriate KMV terminator.")
    
    Path(mp4_path).write_bytes(data[HEADER_SIZE:])
    print(f"Recovered.")