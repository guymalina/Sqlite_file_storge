from pathlib import Path
import hashlib
import mimetypes

from sql import Database

# ===== WORK MODE SELECTION =====
# Change this to "mysql" or "sqlite" to indicate your preferred mode.
# The actual engine used still comes from db_param.json -> "engine".
WORK_MODE: str = "sqlite"  # or "mysql"
# ===============================


def check_connection(db: Database) -> None:
    """Check and print the status of the database connection."""
    if db.check_connection():
        print(f"{db.engine.upper()} connection OK (read from db_param.json).")
    else:
        print(f"{db.engine.upper()} connection FAILED (tried db_param.json).")


def read_file_bytes(file_path: Path) -> bytes:
    """Read a file from disk as raw bytes."""
    with file_path.open("rb") as f:
        return f.read()


def compute_file_metadata(file_path: Path, file_contents: bytes):
    """Compute filename, MIME type, size and SHA256 hash for a file."""
    file_name = file_path.name
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"
    file_size = len(file_contents)
    sha256 = hashlib.sha256(file_contents).hexdigest()
    return file_name, mime_type, file_size, file_contents, sha256


def save_backup_file(output_dir: Path, row) -> None:
    """Save a file row from the database to disk with a '_Beckup' suffix and verify hash."""
    orig_filename = row.get("filename") or "file_from_db.bin"
    stem, dot, suffix = orig_filename.partition(".")
    if dot:
        output_filename = f"{stem}_Beckup.{suffix}"
    else:
        output_filename = f"{orig_filename}_Beckup"
    output_path = output_dir / output_filename

    # Write file to disk
    with output_path.open("wb") as f:
        f.write(row["file_data"])

    print(f"File saved to: {output_path}")
    print(f"SHA256 from database: {row['sha256']}")

    # Verify SHA256 of the saved file
    with output_path.open("rb") as f:
        file_bytes = f.read()
        calculated_sha256 = hashlib.sha256(file_bytes).hexdigest()

    if calculated_sha256 == row["sha256"]:
        print(f"File check: OK (SHA256 matches: {calculated_sha256})")
    else:
        print("File check: FAILED (SHA256 mismatch)")
        print(f"Calculated SHA256: {calculated_sha256}")


def main() -> None:
    base_dir = Path(__file__).parent

    # Database instance (reads db_param.json and engine: mysql/sqlite)
    db_param_path = base_dir / "db_param.json"
    db = Database(config_path=db_param_path)

    # Optional: warn if constant and config disagree
    if WORK_MODE.lower() != db.engine:
        print(
            f"WARNING: WORK_MODE is '{WORK_MODE}', but db_param.json engine is "
            f"'{db.engine}'. Using '{db.engine}'."
        )

    # 1) Check database connection
    check_connection(db)

    # 2) Read file from disk
    file_path = base_dir / "random_data.bin"
    file_contents = read_file_bytes(file_path)
    print(f"File head (first 64 bytes): {file_contents[:64]}")

    # 3) Compute metadata and insert into database via class method
    file_name, mime_type, file_size, file_data, sha256 = compute_file_metadata(
        file_path, file_contents
    )
    file_id = db.insert_file(file_name, mime_type, file_size, file_data, sha256)
    print(f"File inserted into database with id {file_id}.")

    # 4) Read last file from database and save backup copy
    row = db.get_last_file()
    if not row:
        print("No file found in database.")
        return

    save_backup_file(base_dir, row)


if __name__ == "__main__":
    main()
