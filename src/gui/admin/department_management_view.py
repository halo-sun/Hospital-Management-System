"""Admin department management view – dedicated department CRUD.

Independent from DoctorManagementView — each module has a single
responsibility.  The view is a pure presentation layer: it renders
whatever department list the factory supplies and forwards add/edit/
delete actions through its callbacks.  The admin factory backs those
callbacks exclusively with ``DepartmentController``, which persists
to the real ``departments`` table (via ``DepartmentService`` /
``DepartmentRepository``).
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView


class DepartmentManagementView(BaseView):
    """Table view for managing departments (admin only)."""

    def __init__(
        self,
        parent: tk.Widget,
        departments: List[Dict[str, Any]],
        on_add: Optional[Callable] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        on_delete: Optional[Callable[[int], None]] = None,
        on_refresh: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialise the department management view.

        Args:
            parent: Parent tkinter widget.
            departments: List of department dicts.
            on_add: Callback to add a department.
            on_edit: Callback to edit a department.
            on_delete: Callback to delete a department.
            on_refresh: Callback to refresh the list.
        """
        super().__init__(parent, **kwargs)
        self._departments = departments
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_refresh = on_refresh
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the department management layout."""
        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        ttk.Label(header, text="Department Management", style="Heading.TLabel").pack(side="left")

        if self._on_add:
            tk.Button(
                header, text="+ Add Department", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_add,
            ).pack(side="right", padx=4)

        if self._on_refresh:
            tk.Button(
                header, text="Refresh", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_refresh,
            ).pack(side="right", padx=4)

        # Stats summary
        stats_frame = ttk.Frame(self, style="TFrame", padding=(16, 8))
        stats_frame.pack(fill="x")
        total = len(self._departments)
        ttk.Label(
            stats_frame, text=f"Total Departments: {total}",
            style="Subheading.TLabel",
        ).pack(anchor="w")

        # Table
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "name", "description", "doctors")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("ID", "Department Name", "Description", "Doctors"),
        )
        self._tree.column("id", width=60, anchor="center")
        self._tree.column("name", width=200)
        self._tree.column("description", width=350)
        self._tree.column("doctors", width=80, anchor="center")

        self.populate(self._departments)

        # Action buttons
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 0))
        btn_frame.pack(fill="x")

        if self._on_edit:
            tk.Button(
                btn_frame, text="Edit", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_edit,
            ).pack(side="left", padx=(0, 8))

        if self._on_delete:
            tk.Button(
                btn_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_delete,
            ).pack(side="left")

    def populate(self, departments: List[Dict[str, Any]]) -> None:
        """Fill the tree with department records.

        Args:
            departments: List of department dictionaries.
        """
        self._tree.delete(*self._tree.get_children())
        for d in departments:
            self._tree.insert("", "end", values=(
                d.get("department_id", ""),
                d.get("department_name", ""),
                d.get("description", "") or "",
                d.get("doctor_count", 0),
            ), iid=str(d.get("department_id", "")))

    def _handle_edit(self) -> None:
        """Edit the selected department."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a department.", parent=self)
            return
        self._on_edit(int(selection[0]))

    def _handle_delete(self) -> None:
        """Delete the selected department."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a department.", parent=self)
            return
        dept_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this department?\n\nThis cannot be undone if no doctors are assigned.", parent=self):
            self._on_delete(dept_id)


class DepartmentFormDialog(tk.Toplevel):
    """Modal dialog for creating/editing a department."""

    def __init__(
        self,
        parent: tk.Widget,
        on_submit: Callable,
        edit_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialise the department form dialog.

        Args:
            parent: Parent window.
            on_submit: Callback invoked with form data.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent)
        self.title("Edit Department" if edit_data else "Add Department")
        self.geometry("480x280")
        self.configure(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()
        self._on_submit = on_submit
        self._edit_data = edit_data or {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dialog form."""
        is_edit = bool(self._edit_data)

        form = ttk.Frame(self, padding=24, style="TFrame")
        form.pack(fill="both", expand=True)

        ttk.Label(
            form, text="Edit Department" if is_edit else "Add Department",
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        # Department name
        ttk.Label(form, text="Department Name *", font=Theme.FONT_BODY).pack(anchor="w")
        self._name_var = tk.StringVar(value=self._edit_data.get("department_name", ""))
        ttk.Entry(form, textvariable=self._name_var, width=40, font=Theme.FONT_BODY).pack(
            fill="x", pady=(2, 12)
        )

        # Description
        ttk.Label(form, text="Description", font=Theme.FONT_BODY).pack(anchor="w")
        self._desc_var = tk.StringVar(value=self._edit_data.get("description", ""))
        ttk.Entry(form, textvariable=self._desc_var, width=40, font=Theme.FONT_BODY).pack(
            fill="x", pady=(2, 16)
        )

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Save", bg=Theme.SUCCESS, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=self._handle_submit,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame, text="Cancel", bg=Theme.DANGER, fg=Theme.WHITE,
            font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=16, pady=6,
            command=self.destroy,
        ).pack(side="left")

    def _handle_submit(self) -> None:
        """Collect data and invoke the submit callback."""
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Department name is required.", parent=self)
            return

        data = {
            "department_name": name,
            "description": self._desc_var.get().strip(),
        }
        self._on_submit(data)
        self.destroy()
