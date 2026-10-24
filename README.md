# KMV

**What is KMV?**
It's a new movie file format **(not really)** called KMV (Kitten MoVie).

**How it works?**

KMV format is like this:
- MAGIC (KMOVIE)
- Terminators (10 2E bytes)
- MP4 data

## This repository contains KAD and KAR

**What is KAD?**
It's a new audio file format **(not really)** called KAD (Kitten AuDio).

**How it works?**

KAD format is like this:
- MAGIC (KAUDIO)
- Terminators (10 2E bytes)
- File format
- FLAC/MP3/WAV/MIDI data

**What is KAR?**
It's a new archive file format **(really)** called KAR (Kitten ARchive).

**How it works?**

KAR format is like this:
- MAGIC (KARCHIVE + 10 2E bytes)
- Version (1 byte)
- Number of files (Little-endian)
- Length of name (2 bytes)
- Filename (changable)
- Compression method (0 = no compression, 1 = zlib)
- Original size (8 bytes)
- Saved size (8 bytes)
- File data (changable)

Scheme:
KARCHIVE..........
Version + number of files (5 bytes)
File record 1 (Name + method + sizes + data)
File record 2 ... N (Same layout for every file)

# IMPORTANT:
KMV and KAD doesn't have players because if you want to use them in a game, then you need to just create your own KMV and KAD player, as we don't know which library you are using for game.
