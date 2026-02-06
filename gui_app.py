from __future__ import annotations

from pathlib import Path
import hashlib
import json
import mimetypes
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

from sql import Database


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format (KB, MB, GB)."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            if unit == "B":
                return f"{int(size_bytes)} {unit}"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_file_icon(mime_type: str) -> str:
    """Get emoji icon based on MIME type."""
    if not mime_type:
        return "📄"
    
    mime_lower = mime_type.lower()
    
    if "pdf" in mime_lower:
        return "📕"
    elif "image" in mime_lower:
        return "🖼️"
    elif "video" in mime_lower:
        return "🎬"
    elif "audio" in mime_lower:
        return "🎵"
    elif "text" in mime_lower or "json" in mime_lower or "xml" in mime_lower:
        return "📝"
    elif "zip" in mime_lower or "archive" in mime_lower or "tar" in mime_lower:
        return "📦"
    elif "sql" in mime_lower or "database" in mime_lower:
        return "🗄️"
    elif "excel" in mime_lower or "spreadsheet" in mime_lower:
        return "📊"
    elif "powerpoint" in mime_lower or "presentation" in mime_lower:
        return "📽️"
    elif "word" in mime_lower or "document" in mime_lower:
        return "📄"
    elif "code" in mime_lower or "script" in mime_lower:
        return "💻"
    else:
        return "📄"


class FileStorageGUI(tk.Tk):
    """
    Tkinter GUI for the SQL file storage app.

    - Supports both MySQL and SQLite via the shared Database class.
    - Lets you view files stored in the 'files' table.
    - Lets you add files to the database.
    - Lets you delete selected files from the database.
    - Lets you export a selected file from the DB back to disk.
    """

    def __init__(self) -> None:
        super().__init__()

        base_dir = Path(__file__).parent
        self.db_param_path = base_dir / "db_param.json"
        self.base_dir = base_dir
        self.db: Database | None = None

        self.title("File Storage")
        self.geometry("1200x600")
        self.minsize(800, 500)
        
        # Configure dark theme colors
        self.configure(bg="#2b2b2b")

        self._load_database()
        if self.db:
            self.title(f"File Storage ({self.db.engine.upper()})")
        self._build_widgets()
        self.refresh_files()

    # ----- Database management -----

    def _load_database(self) -> None:
        """Load database connection from db_param.json."""
        try:
            self.db = Database(config_path=self.db_param_path)
        except Exception as exc:
            messagebox.showerror(
                "Database error",
                f"Failed to connect to database:\n{exc}\n\nPlease check db_param.json",
            )
            self.db = None

    def _get_current_engine(self) -> str:
        """Get the current engine from db_param.json."""
        try:
            if self.db_param_path.exists():
                data = json.loads(self.db_param_path.read_text())
                return str(data.get("engine", "mysql")).lower()
        except Exception:
            pass
        return "mysql"

    def _get_file_count(self) -> int:
        """Get the number of files in the database."""
        if not self.db:
            return 0
        try:
            files = self.db.get_all_files()
            return len(files)
        except Exception:
            return 0

    def _switch_database(self, engine: str) -> None:
        """Switch database engine by updating db_param.json and reconnecting."""
        current_engine = self._get_current_engine()
        try:
            # Read current config
            if self.db_param_path.exists():
                data = json.loads(self.db_param_path.read_text())
            else:
                data = {}

            # Update engine
            data["engine"] = engine.lower()

            # For SQLite, ensure database path exists
            if engine.lower() == "sqlite":
                if "database" not in data or not data["database"]:
                    data["database"] = "file_storage.db"
            # For MySQL, keep existing fields (they should already be there)

            # Write updated config
            self.db_param_path.write_text(json.dumps(data, indent=4))

            # Reconnect
            self._load_database()
            if self.db:
                self.title(f"File Storage ({self.db.engine.upper()})")
                # Update combo box to reflect current engine
                if hasattr(self, 'db_combo'):
                    self.db_combo.set(self.db.engine.lower())
                self._update_status_bar()
                self.refresh_files()
                messagebox.showinfo("Database switched", f"Switched to {engine.upper()} database.")
            else:
                # Revert combo box if connection failed
                if hasattr(self, 'db_combo'):
                    self.db_combo.set(current_engine)
                messagebox.showerror("Connection failed", "Failed to connect to the new database.")
        except Exception as exc:
            # Revert combo box on error
            if hasattr(self, 'db_combo'):
                self.db_combo.set(current_engine)
            messagebox.showerror("Error", f"Failed to switch database:\n{exc}")

    # ----- UI setup -----

    def _build_widgets(self) -> None:
        # Top status bar
        status_frame = tk.Frame(self, bg="#2b2b2b", height=35)
        status_frame.pack(side=tk.TOP, fill=tk.X)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame,
            text="",
            font=("Arial", 11, "bold"),
            bg="#2b2b2b",
            fg="white",
            anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, padx=15, pady=8)

        # Top control panel
        top_frame = tk.Frame(self, bg="#3a3a3a", relief=tk.RAISED, bd=1)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))

        # Left side: Database selection
        left_panel = tk.Frame(top_frame, bg="#3a3a3a")
        left_panel.pack(side=tk.LEFT, padx=10, pady=8)

        db_label = tk.Label(
            left_panel,
            text="Database:",
            font=("Arial", 10, "bold"),
            bg="#3a3a3a",
            fg="white",
        )
        db_label.pack(side=tk.LEFT, padx=(0, 5))

        self.db_combo = ttk.Combobox(
            left_panel,
            values=("mysql", "sqlite"),
            state="readonly",
            width=12,
            font=("Arial", 10),
        )
        self.db_combo.set(self._get_current_engine())
        self.db_combo.pack(side=tk.LEFT, padx=5)
        self.db_combo.bind("<<ComboboxSelected>>", self._on_db_selected)

        # Right side: Action buttons
        right_panel = tk.Frame(top_frame, bg="#3a3a3a")
        right_panel.pack(side=tk.RIGHT, padx=10, pady=8)

        add_file_btn = tk.Button(
            right_panel,
            text="+ Add File",
            command=self.add_file,
            width=12,
            height=1,
            font=("Arial", 10, "bold"),
            bg="#3b8ed0",
            fg="white",
            activebackground="#2d6fa0",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
        )
        add_file_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(
            right_panel,
            text="Refresh",
            command=self.refresh_files,
            width=12,
            height=1,
            font=("Arial", 10),
            bg="#4a4a4a",
            fg="white",
            activebackground="#5a5a5a",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Main content area
        main_frame = tk.Frame(self, bg="#2b2b2b")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left side: File list with treeview
        list_frame = tk.Frame(main_frame, bg="#3a3a3a", relief=tk.RAISED, bd=1)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)

        header_label = tk.Label(
            list_frame,
            text="FILES IN DATABASE",
            font=("Arial", 14, "bold"),
            bg="#3a3a3a",
            fg="white",
            anchor="w",
        )
        header_label.pack(anchor="w", padx=15, pady=(15, 10))

        # Treeview container
        tree_container = tk.Frame(list_frame, bg="#3a3a3a")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Style the treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#1e1e1e",
            foreground="white",
            fieldbackground="#1e1e1e",
            borderwidth=0,
            rowheight=25,
        )
        style.configure(
            "Treeview.Heading",
            background="#1f538d",
            foreground="white",
            borderwidth=1,
            relief="flat",
            font=("Arial", 10, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "white")],
        )

        columns = ("id", "filename", "mime_type", "file_size", "sha256")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("filename", text="FILENAME")
        self.tree.heading("mime_type", text="MIME TYPE")
        self.tree.heading("file_size", text="SIZE")
        self.tree.heading("sha256", text="SHA256")

        self.tree.column("id", width=60, anchor=tk.CENTER)
        self.tree.column("filename", width=250, anchor=tk.W)
        self.tree.column("mime_type", width=180, anchor=tk.W)
        self.tree.column("file_size", width=100, anchor=tk.E)
        self.tree.column("sha256", width=250, anchor=tk.W)

        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        tree_scroll_y = ttk.Scrollbar(
            tree_container, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.LEFT, fill=tk.Y)

        # Right side: Details and actions
        details_frame = tk.Frame(main_frame, bg="#3a3a3a", relief=tk.RAISED, bd=1, width=350)
        details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0), pady=5)
        details_frame.pack_propagate(False)

        details_header = tk.Label(
            details_frame,
            text="FILE DETAILS",
            font=("Arial", 14, "bold"),
            bg="#3a3a3a",
            fg="white",
            anchor="w",
        )
        details_header.pack(anchor="w", padx=15, pady=(15, 10))

        # Details placeholder/content area
        self.details_container = tk.Frame(details_frame, bg="#3a3a3a")
        self.details_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # Placeholder for when no file is selected
        self.details_placeholder = tk.Frame(self.details_container, bg="#3a3a3a")
        self.details_placeholder.pack(fill=tk.BOTH, expand=True)

        placeholder_icon = tk.Label(
            self.details_placeholder,
            text="📄",
            font=("Arial", 48),
            bg="#3a3a3a",
            fg="gray",
        )
        placeholder_icon.pack(pady=(30, 15))

        placeholder_text = tk.Label(
            self.details_placeholder,
            text="Select a file to view details",
            font=("Arial", 12),
            bg="#3a3a3a",
            fg="gray",
        )
        placeholder_text.pack()

        # Details text area (hidden initially)
        self.details_text = tk.Text(
            self.details_container,
            width=32,
            height=15,
            font=("Courier", 10),
            bg="#1e1e1e",
            fg="white",
            relief=tk.FLAT,
            bd=2,
            wrap=tk.WORD,
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)
        self.details_text.configure(state="disabled")
        self.details_text.pack_forget()  # Hide initially

        # Action buttons
        btn_frame = tk.Frame(details_frame, bg="#3a3a3a")
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))

        export_btn = tk.Button(
            btn_frame,
            text="💾 Export to File",
            command=self.export_selected,
            width=20,
            height=2,
            font=("Arial", 10, "bold"),
            bg="#3b8ed0",
            fg="white",
            activebackground="#2d6fa0",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
        )
        export_btn.pack(fill=tk.X, pady=(0, 8))

        delete_btn = tk.Button(
            btn_frame,
            text="🗑️ Delete from DB",
            command=self.delete_selected,
            width=20,
            height=2,
            font=("Arial", 10, "bold"),
            bg="#d32f2f",
            fg="white",
            activebackground="#c62828",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
        )
        delete_btn.pack(fill=tk.X)

    def _update_status_bar(self) -> None:
        """Update the status bar with database engine and file count."""
        if not self.db:
            self.status_label.configure(text="No database connection")
            return

        engine = self.db.engine.upper()
        file_count = self._get_file_count()
        count_text = f"{file_count} file" + ("s" if file_count != 1 else "") + " stored"
        self.status_label.configure(text=f"{engine} • {count_text}")

    def _on_db_selected(self, event=None) -> None:
        """Handle database engine selection change."""
        new_engine = self.db_combo.get()
        current_engine = self._get_current_engine()
        if new_engine != current_engine:
            if messagebox.askyesno(
                "Switch database",
                f"Switch from {current_engine.upper()} to {new_engine.upper()}?\n\n"
                "This will update db_param.json and reconnect.",
            ):
                self._switch_database(new_engine)
            else:
                # Revert combo selection if user cancels
                self.db_combo.set(current_engine)

    # ----- Data loading -----

    def refresh_files(self) -> None:
        """Reload the list of files from the database into the treeview."""
        if not self.db:
            return

        # Clear current rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            rows = self.db.get_all_files()
        except Exception as exc:
            messagebox.showerror("Database error", f"Failed to load files:\n{exc}")
            return

        for row in rows:
            icon = get_file_icon(row["mime_type"])
            filename_with_icon = f"{icon} {row['filename']}"
            size_formatted = format_file_size(row["file_size"])
            sha_short = row["sha256"][:16] + "..." if row["sha256"] else ""

            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(
                    row["id"],
                    filename_with_icon,
                    row["mime_type"],
                    size_formatted,
                    sha_short,
                ),
            )

        self._update_status_bar()
        self._clear_details()

    # ----- Selection handling -----

    def _on_selection_changed(self, event=None) -> None:
        """Update details panel when the user selects a file."""
        selection = self.tree.selection()
        if not selection:
            self._clear_details()
            return

        item_id = selection[0]
        file_id = int(self.tree.set(item_id, "id"))

        if not self.db:
            self._clear_details()
            return

        # Fetch full row including file_data for preview
        try:
            row = self.db.get_file_by_id(file_id)
        except Exception as exc:
            messagebox.showerror("Database error", f"Failed to load file details:\n{exc}")
            return

        if not row:
            self._clear_details()
            return

        self._show_details(row)

    def _clear_details(self) -> None:
        """Show placeholder when no file is selected."""
        self.details_text.pack_forget()
        self.details_placeholder.pack(fill=tk.BOTH, expand=True)

    def _show_details(self, row: dict) -> None:
        """Display metadata and a short preview of the file data."""
        # Hide placeholder, show details
        self.details_placeholder.pack_forget()
        self.details_text.pack(fill=tk.BOTH, expand=True)

        preview_bytes = row["file_data"][:64] if row.get("file_data") else b""
        preview_hex = preview_bytes.hex(" ")[:128]
        size_formatted = format_file_size(row["file_size"])

        text = (
            f"ID: {row['id']}\n"
            f"Filename: {row['filename']}\n"
            f"MIME type: {row['mime_type']}\n"
            f"Size: {size_formatted} ({row['file_size']:,} bytes)\n"
            f"SHA256: {row['sha256']}\n"
            f"\nPreview (first 64 bytes, hex):\n{preview_hex}\n"
        )

        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, text)
        self.details_text.configure(state="disabled")

    # ----- Actions -----

    def add_file(self) -> None:
        """Open file dialog to select a file and add it to the database."""
        if not self.db:
            messagebox.showerror("No database", "Database connection not available.")
            return

        file_path = filedialog.askopenfilename(
            title="Select file to add to database",
            initialdir=str(self.base_dir),
        )
        if not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            messagebox.showerror("File not found", f"File does not exist:\n{path}")
            return

        try:
            # Read file
            with path.open("rb") as f:
                file_contents = f.read()

            # Compute metadata
            file_name = path.name
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "application/octet-stream"
            file_size = len(file_contents)
            sha256 = hashlib.sha256(file_contents).hexdigest()

            # Insert into database
            file_id = self.db.insert_file(file_name, mime_type, file_size, file_contents, sha256)

            messagebox.showinfo(
                "File added",
                f"File added to database successfully.\n\n"
                f"ID: {file_id}\n"
                f"Filename: {file_name}\n"
                f"Size: {format_file_size(file_size)}\n",
            )

            # Refresh list
            self.refresh_files()

        except Exception as exc:
            messagebox.showerror("Error", f"Failed to add file to database:\n{exc}")

    def _get_selected_file_id(self) -> int | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please select a file in the list.")
            return None
        item_id = selection[0]
        # The iid is set to the string version of the file ID, so we can use it directly
        try:
            return int(item_id)
        except (ValueError, TypeError):
            # Fallback: try to get from the "id" column
            try:
                return int(self.tree.set(item_id, "id"))
            except (ValueError, TypeError):
                messagebox.showerror("Error", "Could not determine file ID from selection.")
                return None

    def delete_selected(self) -> None:
        """Delete the selected file from the database."""
        if not self.db:
            messagebox.showerror("No database", "Database connection not available.")
            return

        file_id = self._get_selected_file_id()
        if file_id is None:
            return

        if not messagebox.askyesno(
            "Delete file",
            f"Are you sure you want to delete file with ID {file_id} from the database?",
        ):
            return

        try:
            # Use delete_file method which handles SQLite vacuum automatically
            deleted = self.db.delete_file(file_id, vacuum_after=True)
            if not deleted:
                messagebox.showwarning(
                    "Delete failed",
                    f"File with ID {file_id} was not found in the database.\n\n"
                    "It may have already been deleted.",
                )
                self.refresh_files()
                return
        except Exception as exc:
            messagebox.showerror("Database error", f"Failed to delete file:\n{exc}")
            return

        self.refresh_files()
        
        # Show info about database compaction for SQLite
        if self.db.engine == "sqlite":
            messagebox.showinfo(
                "File deleted",
                f"File with ID {file_id} deleted.\n\n"
                "SQLite database has been compacted to reclaim space.",
            )
        else:
            messagebox.showinfo(
                "File deleted",
                f"File with ID {file_id} deleted successfully.",
            )

    def export_selected(self) -> None:
        """Export the selected file from the database to a file on disk."""
        if not self.db:
            messagebox.showerror("No database", "Database connection not available.")
            return

        file_id = self._get_selected_file_id()
        if file_id is None:
            return

        try:
            row = self.db.get_file_for_export(file_id)
        except Exception as exc:
            messagebox.showerror("Database error", f"Failed to load file from DB:\n{exc}")
            return

        if not row:
            messagebox.showerror("Not found", "File not found in database.")
            return

        default_name = row["filename"] or f"file_{file_id}.bin"

        save_path = filedialog.asksaveasfilename(
            title="Save file as",
            initialdir=str(self.base_dir),
            initialfile=default_name,
        )
        if not save_path:
            return

        out_path = Path(save_path)
        try:
            with out_path.open("wb") as f:
                f.write(row["file_data"])
        except Exception as exc:
            messagebox.showerror("File error", f"Failed to save file:\n{exc}")
            return

        # Verify hash after save
        with out_path.open("rb") as f:
            data = f.read()
            sha = hashlib.sha256(data).hexdigest()

        if sha == row["sha256"]:
            messagebox.showinfo(
                "Export complete",
                f"File saved to:\n{out_path}\n\nSHA256 verified OK.",
            )
        else:
            messagebox.showwarning(
                "Export complete (hash mismatch)",
                f"File saved to:\n{out_path}\n\n"
                "WARNING: SHA256 of saved file does not match value from DB.",
            )


def main() -> None:
    app = FileStorageGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
