"""Admin staff management view – dedicated receptionist/staff management.

Independent from user_management_view — each module has a single
responsibility.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView
from src.utils.formatters import format_datetime
from src.constants import UserStatus


class StaffManagementView(BaseView):
    """Table view for managing staff (receptionists) — admin only."""

    def __init__(
        self,
        parent: tk.Widget,
        staff: List[Dict[str, Any]],
        on_add: Optional[Callable] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        on_delete: Optional[Callable[[int], None]] = None,
        on_activate: Optional[Callable[[int], None]] = None,
        on_deactivate: Optional[Callable[[int], None]] = None,
        on_refresh: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialise the staff management view.

        Args:
            parent: Parent tkinter widget.
            staff: List of staff user dicts.
            on_add: Callback to add staff.
            on_edit: Callback to edit staff.
            on_delete: Callback to delete staff.
            on_activate: Callback to activate a staff member.
            on_deactivate: Callback to deactivate a staff member.
            on_refresh: Callback to refresh the list.
        """
        super().__init__(parent, **kwargs)
        self._staff = staff
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._on_refresh = on_refresh
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the staff management layout."""
        # Header
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        ttk.Label(header, text="Staff Management", style="Heading.TLabel").pack(side="left")

        if self._on_add:
            tk.Button(
                header, text="+ Add Staff", bg=Theme.SUCCESS, fg=Theme.WHITE,
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
        active = sum(1 for s in self._staff if s.get("status") == UserStatus.ACTIVE)
        total = len(self._staff)
        ttk.Label(
            stats_frame,
            text=f"Total Staff: {total}  |  Active: {active}",
            style="Subheading.TLabel",
        ).pack(anchor="w")

        # Table
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "username", "full_name", "email", "role", "status", "last_login")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("ID", "Username", "Full Name", "Email", "Role", "Status", "Last Login"),
        )
        self._tree.column("id", width=50, anchor="center")
        self._tree.column("username", width=120)
        self._tree.column("full_name", width=160)
        self._tree.column("email", width=180)
        self._tree.column("role", width=100, anchor="center")
        self._tree.column("status", width=80, anchor="center")
        self._tree.column("last_login", width=140)

        self.populate(self._staff)

        # Action buttons
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 0))
        btn_frame.pack(fill="x")

        if self._on_edit:
            tk.Button(
                btn_frame, text="Edit", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_edit,
            ).pack(side="left", padx=(0, 8))

        if self._on_activate:
            tk.Button(
                btn_frame, text="Activate", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_activate,
            ).pack(side="left", padx=(0, 8))

        if self._on_deactivate:
            tk.Button(
                btn_frame, text="Deactivate", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_deactivate,
            ).pack(side="left", padx=(0, 8))

        if self._on_delete:
            tk.Button(
                btn_frame, text="Delete", bg=Theme.DANGER, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_delete,
            ).pack(side="left")

    def populate(self, staff: List[Dict[str, Any]]) -> None:
        """Fill the tree with staff records.

        Args:
            staff: List of user dictionaries.
        """
        self._tree.delete(*self._tree.get_children())
        for s in staff:
            last = format_datetime(s.get("last_login", ""))
            self._tree.insert("", "end", values=(
                s.get("user_id", ""),
                s.get("username", ""),
                s.get("full_name", ""),
                s.get("email", ""),
                s.get("role_name", ""),
                s.get("status", ""),
                last,
            ), iid=str(s.get("user_id", "")))
        self.apply_default_sort(self._tree)

    def _handle_edit(self) -> None:
        """Edit the selected staff member."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a staff member.", parent=self)
            return
        self._on_edit(int(selection[0]))

    def _handle_delete(self) -> None:
        """Delete the selected staff member."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a staff member.", parent=self)
            return
        user_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Delete this staff member?\n\nThis action cannot be undone.", parent=self):
            self._on_delete(user_id)

    def _handle_activate(self) -> None:
        """Activate the selected staff member."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a staff member.", parent=self)
            return
        user_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Activate this staff member?", parent=self):
            self._on_activate(user_id)

    def _handle_deactivate(self) -> None:
        """Deactivate the selected staff member."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a staff member.", parent=self)
            return
        user_id = int(selection[0])
        if messagebox.askyesno("Confirm", "Deactivate this staff member?", parent=self):
            self._on_deactivate(user_id)


class StaffFormDialog(tk.Toplevel):
    """Modal dialog for creating/editing a staff member."""

    def __init__(
        self,
        parent: tk.Widget,
        on_submit: Callable,
        roles: Optional[List[Dict[str, Any]]] = None,
        edit_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialise the staff form dialog.

        Args:
            parent: Parent window.
            on_submit: Callback invoked with form data.
            roles: List of role dicts with role_id and role_name.
            edit_data: Optional dict to pre-fill for editing.
        """
        super().__init__(parent)
        self.title("Edit Staff" if edit_data else "Add Staff Member")
        self.geometry("460x480")
        self.configure(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()
        self._on_submit = on_submit
        self._roles = roles or []
        self._edit_data = edit_data or {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dialog form."""
        is_edit = bool(self._edit_data)

        form = ttk.Frame(self, padding=24, style="TFrame")
        form.pack(fill="both", expand=True)

        ttk.Label(
            form, text="Edit Staff Member" if is_edit else "Add Staff Member",
            style="Heading.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        self._vars: Dict[str, tk.StringVar] = {}

        # Fields
        fields = [
            ("username", "Username *", ""),
            ("full_name", "Full Name", ""),
            ("email", "Email", ""),
        ]
        if not is_edit:
            fields.append(("password", "Password *", ""))

        for key, label, default in fields:
            default_val = str(self._edit_data.get(key, default))
            ttk.Label(form, text=label, font=Theme.FONT_BODY).pack(anchor="w")
            self._vars[key] = tk.StringVar(value=default_val)
            show = "*" if key == "password" else None
            ttk.Entry(
                form, textvariable=self._vars[key], width=40,
                font=Theme.FONT_BODY, show=show,
            ).pack(fill="x", pady=(2, 12))

        # Role (only for new users)
        if not is_edit and self._roles:
            ttk.Label(form, text="Role *", font=Theme.FONT_BODY).pack(anchor="w")
            role_names = [r.get("role_name", "") for r in self._roles]
            self._role_combo = ttk.Combobox(
                form, values=role_names, width=37, state="readonly", font=Theme.FONT_BODY,
            )
            # Default to Receptionist
            receptionist_idx = next(
                (i for i, n in enumerate(role_names) if n == "Receptionist"), 0
            )
            self._role_combo.current(receptionist_idx)
            self._role_combo.pack(fill="x", pady=(2, 16))

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.pack(fill="x")

        btn_text = "Update Staff" if is_edit else "Add Staff"
        tk.Button(
            btn_frame, text=btn_text, bg=Theme.SUCCESS, fg=Theme.WHITE,
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
        data = {key: var.get() for key, var in self._vars.items()}

        is_edit = bool(self._edit_data)
        if not is_edit:
            if not data.get("username") or not data.get("password"):
                messagebox.showwarning("Warning", "Username and password are required.", parent=self)
                return
            if hasattr(self, "_role_combo"):
                role_idx = self._role_combo.current()
                if role_idx >= 0 and role_idx < len(self._roles):
                    data["role_id"] = self._roles[role_idx].get("role_id")

        self._on_submit(data)
        self.destroy()
