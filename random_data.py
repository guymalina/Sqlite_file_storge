
from __future__ import annotations
import random
from pathlib import Path

# ===== USER SETTINGS =====
# Change this value to control the file size (in megabytes)
FILE_SIZE_MB: int = 1  # for example: 10 MB

# Change this to control the output file name (created in the same folder as this script)
OUTPUT_FILENAME: str = "random_data.bin"
# =========================

def create_random_file(size_mb: int, output_path: Path) -> None:
    if size_mb <= 0:
        raise ValueError("size_mb must be a positive integer")

    total_bytes = size_mb * 1024 * 1024
    chunk_size = 1024 * 1024  # max bytes to write per loop

    print(f"Creating file: {output_path}")
    print(f"Target size: {size_mb} MB ({total_bytes} bytes)")

    bytes_written = 0
    with output_path.open("wb") as f:
        while bytes_written < total_bytes:
            remaining = total_bytes - bytes_written

            # Build a chunk of random numbers as text (e.g. "5 8 0 3 ...\n")
            numbers = [str(random.randint(0, 9)) for _ in range(10000)]
            chunk_str = " ".join(numbers) + "\n"
            data = chunk_str.encode("utf-8")

            if len(data) > min(chunk_size, remaining):
                data = data[: min(chunk_size, remaining)]

            f.write(data)
            bytes_written += len(data)

    print(f"Done. Wrote {bytes_written} bytes.")


def main() -> None:
    script_dir = Path(__file__).parent
    output_path = script_dir / OUTPUT_FILENAME
    create_random_file(FILE_SIZE_MB, output_path)


if __name__ == "__main__":
    main()


