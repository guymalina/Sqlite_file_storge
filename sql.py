
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import mysql.connector
from mysql.connector.connection import MySQLConnection


# Connection details are stored in JSON next to this file: db_param.json
CONFIG_PATH = Path(__file__).with_name("db_param.json")

ConnectionType = Union[MySQLConnection, sqlite3.Connection]


class Database:
    """
    Generic database helper that can work with MySQL or SQLite.

    Work mode is selected in db_param.json with the key:
        "engine": "mysql"   or   "engine": "sqlite"
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path: Path = config_path or CONFIG_PATH
        self.params: Dict[str, Any] = self._load_params()
        self.engine: str = self.params.get("engine", "mysql").lower()
        self._ensure_files_table()

    # ----- configuration and connection -----

    def _load_params(self) -> Dict[str, Any]:
        """Load connection parameters from the JSON config file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        data = json.loads(self.config_path.read_text())

        engine = str(data.get("engine", "mysql")).lower()
        if engine not in {"mysql", "sqlite"}:
            raise ValueError("db_param.json 'engine' must be either 'mysql' or 'sqlite'")

        if engine == "mysql":
            required_keys = ["host", "user", "password", "database"]
            missing = [k for k in required_keys if not data.get(k)]
            if missing:
                raise ValueError(
                    f"Missing required MySQL fields in db_param.json: {missing}"
                )

            # Default port if not provided
            if "port" not in data or not data["port"]:
                data["port"] = 3306

        elif engine == "sqlite":
            if not data.get("database"):
                raise ValueError(
                    "For SQLite, db_param.json must contain 'database' (file name/path)"
                )

        return data

    def _sqlite_path(self) -> Path:
        """Return absolute path for SQLite database file."""
        raw = self.params["database"]
        db_path = Path(raw)
        if not db_path.is_absolute():
            db_path = self.config_path.parent / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    def get_connection(self) -> ConnectionType:
        """Create and return a new connection for the selected engine."""
        engine = self.engine
        if engine == "mysql":
            return mysql.connector.connect(
                host=self.params["host"],
                port=self.params["port"],
                user=self.params["user"],
                password=self.params["password"],
                database=self.params["database"],
            )
        if engine == "sqlite":
            return sqlite3.connect(self._sqlite_path())

        raise ValueError(f"Unsupported engine: {engine}")

    def check_connection(self) -> bool:
        """
        Check if the database connection can be established.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            conn = self.get_connection()
            conn.close()
            return True
        except Exception as exc:
            print(f"Connection failed: {exc}")
            return False

    # ----- generic SQL helpers -----

    def _prepare_sql(self, sql: str) -> str:
        """
        Normalize placeholder style for the current engine.

        In this project we write SQL using MySQL-style '%s' placeholders.
        For SQLite we convert them to '?'.
        """
        if self.engine == "sqlite":
            return sql.replace("%s", "?")
        return sql

    def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> None:
        """
        Execute an INSERT/UPDATE/DELETE statement.

        Args:
            sql: SQL statement with optional placeholders.
            params: Sequence of parameters for the statement.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            sql_to_run = self._prepare_sql(sql)
            cursor.execute(sql_to_run, params or ())
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def query(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT statement and return all rows as a list of dicts.

        Args:
            sql: SELECT statement with optional placeholders.
            params: Sequence of parameters for the statement.
        """
        conn = self.get_connection()
        try:
            if self.engine == "mysql":
                cursor = conn.cursor(dictionary=True)
            else:  # sqlite
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

            sql_to_run = self._prepare_sql(sql)
            cursor.execute(sql_to_run, params or ())
            rows = cursor.fetchall()

            if self.engine == "sqlite":
                # convert sqlite3.Row objects to plain dicts
                rows = [dict(row) for row in rows]

            return rows
        finally:
            cursor.close()
            conn.close()

    # ----- File storage helpers -----

    def insert_file(
        self,
        filename: str,
        mime_type: str,
        file_size: int,
        file_data: bytes,
        sha256: str,
    ) -> int:
        """
        Insert a file record into the 'files' table.

        Returns:
            The auto-increment id of the inserted row.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            sql = """
                INSERT INTO files (filename, mime_type, file_size, file_data, sha256)
                VALUES (%s, %s, %s, %s, %s)
            """
            sql_to_run = self._prepare_sql(sql)
            cursor.execute(
                sql_to_run, (filename, mime_type, file_size, file_data, sha256)
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            cursor.close()
            conn.close()

    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        Get all files from the 'files' table, ordered by ID descending.

        Returns:
            A list of dicts with file metadata (id, filename, mime_type, file_size, sha256).
        """
        return self.query(
            """
            SELECT id, filename, mime_type, file_size, sha256
            FROM files
            ORDER BY id DESC
            """
        )

    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a file by its ID, including full file data.

        Args:
            file_id: The ID of the file to retrieve.

        Returns:
            A dict with the row data, or None if not found.
        """
        rows = self.query(
            """
            SELECT id, filename, mime_type, file_size, file_data, sha256
            FROM files
            WHERE id = %s
            """,
            (file_id,),
        )
        return rows[0] if rows else None

    def get_file_for_export(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file data for export (filename, file_data, sha256) by ID.

        Args:
            file_id: The ID of the file to retrieve.

        Returns:
            A dict with filename, file_data, and sha256, or None if not found.
        """
        rows = self.query(
            """
            SELECT filename, file_data, sha256
            FROM files
            WHERE id = %s
            """,
            (file_id,),
        )
        return rows[0] if rows else None

    def get_last_file(self) -> Optional[Dict[str, Any]]:
        """
        Get the last file stored in the 'files' table (by highest id).

        Returns:
            A dict with the row data, or None if table is empty.
        """
        rows = self.query(
            """
            SELECT id, filename, mime_type, file_size, file_data, sha256
            FROM files
            ORDER BY id DESC
            LIMIT 1
            """
        )
        return rows[0] if rows else None

    def vacuum(self) -> None:
        """
        Reclaim unused space in SQLite database.
        Only works for SQLite; no-op for MySQL.
        """
        if self.engine != "sqlite":
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("VACUUM")
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def delete_file(self, file_id: int, vacuum_after: bool = True) -> bool:
        """
        Delete a file from the database by ID.
        For SQLite, optionally vacuum after deletion to reclaim space.

        Args:
            file_id: The ID of the file to delete.
            vacuum_after: If True and using SQLite, vacuum the database after deletion.

        Returns:
            True if a row was deleted, False otherwise.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        connection_closed = False
        try:
            sql = "DELETE FROM files WHERE id = %s"
            sql_to_run = self._prepare_sql(sql)
            cursor.execute(sql_to_run, (file_id,))
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected == 0:
                cursor.close()
                conn.close()
                return False
                
            # Close connection before vacuum (vacuum needs exclusive access)
            cursor.close()
            conn.close()
            connection_closed = True
                
            if vacuum_after and self.engine == "sqlite":
                self.vacuum()
                
            return True
        except Exception:
            if not connection_closed:
                try:
                    cursor.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
            raise

    # ----- Schema helpers -----

    def _ensure_files_table(self) -> None:
        """
        Ensure the 'files' table exists for the selected engine.
        Called automatically on first use.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if self.engine == "mysql":
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS files (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(255) NOT NULL,
                        file_size BIGINT NOT NULL,
                        file_data LONGBLOB NOT NULL,
                        sha256 CHAR(64) NOT NULL
                    )
                    """
                )
            elif self.engine == "sqlite":
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        mime_type TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        file_data BLOB NOT NULL,
                        sha256 TEXT NOT NULL
                    )
                    """
                )
            conn.commit()
        finally:
            cursor.close()
            conn.close()


# Backwards-compatible alias
MySQLDatabase = Database

