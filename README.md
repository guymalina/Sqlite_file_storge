# SQL File Storage

A Python application for storing files in a database (MySQL or SQLite) with a modern GUI interface. Files are stored with metadata including filename, MIME type, file size, and SHA256 hash for integrity verification.

## Features

- **Dual Database Support**: Works with both MySQL and SQLite
- **Graphical User Interface**: Modern Tkinter-based GUI for easy file management
- **Command Line Interface**: Script-based interface for automation
- **File Integrity**: SHA256 hash verification for all stored files
- **Automatic Table Creation**: Creates the `files` table automatically on first run
- **File Management**: Add, view, delete, and export files from the database
- **SQLite Optimization**: Automatic database compaction (VACUUM) after deletions

## Project Structure

```
sql_file_storge/
├── sql.py              # Database class with MySQL/SQLite support
├── gui_app.py          # Graphical user interface (Tkinter)
├── sql_app.py          # Command-line interface
├── random_data.py      # Utility to generate test files
├── db_param.json       # Database configuration file
└── requirements.txt    # Python dependencies
```

## Requirements

- Python 3.8 or higher
- MySQL Connector/Python (for MySQL mode)
- Tkinter (usually included with Python)

## Installation

1. **Clone or download this project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - `mysql-connector-python` (for MySQL support)

   Note: SQLite and Tkinter are built into Python, no installation needed.

## Setup

### Option 1: SQLite (Easiest - No Setup Required)

SQLite is file-based and requires no server setup. Just configure `db_param.json`:

1. **Edit `db_param.json`**:
   ```json
   {
       "engine": "sqlite",
       "database": "file_storage.db"
   }
   ```

2. **That's it!** The database file will be created automatically when you first run the app.

### Option 2: MySQL (Requires MySQL Server)

1. **Create the MySQL database** (one-time setup):
   ```sql
   CREATE DATABASE file_storge;
   ```

2. **Create a MySQL user** (optional, or use existing):
   ```sql
   CREATE USER 'guiuser'@'localhost' IDENTIFIED BY 'StrongPass123!';
   GRANT ALL PRIVILEGES ON file_storge.* TO 'guiuser'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. **Edit `db_param.json`**:
   ```json
   {
       "engine": "mysql",
       "host": "localhost",
       "port": 3306,
       "user": "guiuser",
       "password": "StrongPass123!",
       "database": "file_storge"
   }
   ```

4. **The `files` table will be created automatically** on first run - no manual table creation needed!

## Configuration

### Database Configuration (`db_param.json`)

The application reads database settings from `db_param.json` in the project root.

**For SQLite:**
```json
{
    "engine": "sqlite",
    "database": "file_storage.db"
}
```

**For MySQL:**
```json
{
    "engine": "mysql",
    "host": "localhost",
    "port": 3306,
    "user": "your_username",
    "password": "your_password",
    "database": "your_database_name"
}
```

## Usage

### Graphical User Interface (GUI)

Run the GUI application:

```bash
python gui_app.py
```

**Features:**
- **Status Bar**: Shows current database engine and file count
- **Database Selection**: Dropdown to switch between MySQL and SQLite
- **Add File**: Button to upload files to the database
- **File List**: Table showing all files with ID, filename, MIME type, size, and SHA256
- **File Details**: Right panel showing detailed information about selected file
- **Export**: Save files from database back to disk
- **Delete**: Remove files from database (with SQLite auto-compaction)

**GUI Workflow:**
1. Select database type (MySQL/SQLite) from dropdown
2. Click "+ Add File" to upload a file
3. Select a file in the list to view details
4. Use "Export to File" to save a file to disk
5. Use "Delete from DB" to remove a file

### Command Line Interface (CLI)

Run the command-line application:

```bash
python sql_app.py
```

**What it does:**
1. Connects to the database (from `db_param.json`)
2. Checks connection status
3. Reads `random_data.bin` from the project directory
4. Inserts the file into the database
5. Retrieves the last file and saves it as a backup with `_Beckup` suffix
6. Verifies SHA256 hash integrity

**Note**: You can modify `sql_app.py` to work with different files or add your own logic.

### Generate Test Files

Create random test files:

```bash
python random_data.py
```

Edit `random_data.py` to change the file size:
```python
FILE_SIZE_MB: int = 10  # Change this value (in megabytes)
OUTPUT_FILENAME: str = "random_data.bin"  # Change output filename
```

## Database Schema

The application automatically creates a `files` table with the following structure:

**MySQL:**
```sql
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_data LONGBLOB NOT NULL,
    sha256 CHAR(64) NOT NULL
)
```

**SQLite:**
```sql
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_data BLOB NOT NULL,
    sha256 TEXT NOT NULL
)
```

The table is created automatically when you first run the application - **no manual setup required!**

## API Usage

You can also use the `Database` class in your own code:

```python
from sql import Database
from pathlib import Path

# Create database instance (reads db_param.json)
db = Database()

# Insert a file
file_id = db.insert_file(
    filename="example.pdf",
    mime_type="application/pdf",
    file_size=1024,
    file_data=b"file content here",
    sha256="hash_here"
)

# Get all files
files = db.get_all_files()

# Get file by ID
file_data = db.get_file_by_id(file_id)

# Delete file
db.delete_file(file_id)

# Export file
export_data = db.get_file_for_export(file_id)
```

## Troubleshooting

### MySQL Connection Failed

- Verify MySQL server is running: `sudo systemctl status mysql`
- Check credentials in `db_param.json`
- Ensure the database exists: `SHOW DATABASES;`
- Verify user has permissions: `SHOW GRANTS FOR 'username'@'localhost';`

### SQLite Database Not Found

- The database file is created automatically in the project directory
- Check file permissions in the project folder
- Verify the path in `db_param.json` is correct

### Table Already Exists Error

- This shouldn't happen - the code uses `CREATE TABLE IF NOT EXISTS`
- If it does, the table structure may be incompatible - drop and recreate:
  ```sql
  DROP TABLE files;
  ```
  Then run the app again to auto-create it.

## File Size Limits

- **SQLite**: Practical limit around 2GB per file (database file size limit ~140TB)
- **MySQL**: `LONGBLOB` can store up to 4GB per file

## Security Notes

- **Never commit `db_param.json` with real passwords to version control**
- Consider using environment variables for sensitive credentials
- The SHA256 hash ensures file integrity but doesn't encrypt the data
- For production use, consider adding encryption for sensitive files

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the `db_param.json` configuration
2. Verify database server is running (for MySQL)
3. Check file permissions
4. Review error messages in the console/GUI

