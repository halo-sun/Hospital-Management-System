"""Admin user management view."""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
from src.gui.theme import Theme
from src.gui.common.base_view import BaseView


class UserManagementView(BaseView):
    """Table view for managing system users (admin only)."""

    def __init__(
        self,
        parent: tk.Widget,
        users: List[Dict[str, Any]],
        on_create: Optional[Callable] = None,
        on_reset_password: Optional[Callable[[int], None]] = None,
        on_refresh: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """Initialise the user management view.

        Args:
            parent: Parent tkinter widget.
            users: List of user dicts.
            on_create: Callback to create a new user.
            on_reset_password: Callback to reset a user's password.
            on_refresh: Callback to refresh the list.
        """
        super().__init__(parent, **kwargs)
        self._users = users
        self._on_create = on_create
        self._on_reset_password = on_reset_password
        self._on_refresh = on_refresh
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the user management layout."""
        header = ttk.Frame(self, style="Header.TFrame", padding=16)
        header.pack(fill="x")

        ttk.Label(header, text="User Management", style="Heading.TLabel").pack(side="left")

        if self._on_create:
            tk.Button(
                header, text="+ New User", bg=Theme.SUCCESS, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_create,
            ).pack(side="right", padx=4)

        if self._on_refresh:
            tk.Button(
                header, text="Refresh", bg=Theme.ACCENT, fg=Theme.WHITE,
                font=Theme.FONT_SMALL, cursor="hand2", bd=0, padx=12, pady=4,
                command=self._on_refresh,
            ).pack(side="right", padx=4)

        # Table
        table_frame = ttk.Frame(self, style="TFrame", padding=16)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "username", "full_name", "email", "role", "status", "last_login")
        self._tree = self.create_treeview(
            table_frame, columns=columns,
            headings=("ID", "Username", "Full Name", "Email", "Role", "Status", "Last Login"),
            height=15,
        )
        self._tree.column("id", width=50, anchor="center")
        self._tree.column("username", width=120)
        self._tree.column("full_name", width=160)
        self._tree.column("email", width=160)
        self._tree.column("role", width=100, anchor="center")
        self._tree.column("status", width=80, anchor="center")
        self._tree.column("last_login", width=140)

        self.populate(self._users)

        # Action buttons
        btn_frame = ttk.Frame(self, style="TFrame", padding=(16, 0))
        btn_frame.pack(fill="x")

        if self._on_reset_password:
            tk.Button(
                btn_frame, text="Reset Password", bg=Theme.WARNING, fg=Theme.WHITE,
                font=Theme.FONT_BUTTON_BOLD, cursor="hand2", bd=0, padx=12, pady=6,
                command=self._handle_reset_password,
            ).pack(side="left")

    def populate(self, users: List[Dict[str, Any]]) -> None:
        """Fill the tree with user records.

        Args:
            users: List of user dictionaries.
        """
        self._tree.delete(*self._tree.get_children())
        for u in users:
            last = u.get("last_login", "")
            if hasattr(last, "strftime"):
                last = last.strftime("%Y-%m-%d %H:%M")
            self._tree.insert("", "end", values=(
                u.get("user_id", ""),
                u.get("username", ""),
                u.get("full_name", ""),
                u.get("email", ""),
                u.get("role_name", ""),
                u.get("status", ""),
                last,
            ), iid=str(u.get("user_id", "")))

    def _handle_reset_password(self) -> None:
        """Reset password for the selected user."""
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a user.", parent=self)
            return
        user_id = int(selection[0])
        self._on_reset_password(user_id)


class CreateUserDialog(tk.Toplevel):
    """Modal dialog for creating a new user."""

    def __init__(
        self,
        parent: tk.Widget,
        roles: List[Dict[str, Any]],
        on_submit: Callable,
    ) -> None:
        """Initialise the create user dialog.

        Args:
            parent: Parent window.
            roles: List of role dicts with 'role_id' and 'role_name'.
            on_submit: Callback invoked with form data.
        """
        super().__init__(parent)
        self.title("Create New User")
        self.geometry("420x480")
        self.configure(bg=Theme.BG)
        self.transient(parent)
        self.grab_set()
        self._on_submit = on_submit
        self._roles = roles
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the dialog form."""
        form = ttk.Frame(self, padding=24, style="TFrame")
        form.pack(fill="both", expand=True)

        ttk.Label(form, text="Create New User", style="Heading.TLabel").pack(anchor="w", pady=(0, 16))

        self._vars: Dict[str, tk.StringVar] = {}
        fields = [
            ("username", "Username *", ""),
            ("full_name", "Full Name", ""),
            ("email", "Email", ""),
            ("password", "Password *", ""),
        ]
        for key, label, default in fields:
            ttk.Label(form, text=label, font=Theme.FONT_BODY).pack(anchor="w")
            self._vars[key] = tk.StringVar(value=default)
            show = "*" if key == "password" else None
            entry = ttk.Entry(form, textvariable=self._vars[key], width=40, font=Theme.FONT_BODY, show=show)
            entry.pack(fill="x", pady=(2, 12))

        # Role
        ttk.Label(form, text="Role *", font=Theme.FONT_BODY).pack(anchor="w")
        self._vars["role_id"] = tk.StringVar()
        role_names = [r.get("role_name", "") for r in self._roles]
        self._role_combo = ttk.Combobox(form, values=role_names, width=37, state="readonly", font=Theme.FONT_BODY)
        self._role_combo.pack(fill="x", pady=(2, 12))

        # Status
        ttk.Label(form, text="Status", font=Theme.FONT_BODY).pack(anchor="w")
        self._vars["status"] = tk.StringVar(value="Active")
        ttk.Combobox(form, textvariable=self._vars["status"], values=["Active", "Inactive"], width=37, state="readonly", font=Theme.FONT_BODY).pack(fill="x", pady=(2, 16))

        # Buttons
        btn_frame = ttk.Frame(form, style="TFrame")
        btn_frame.pack(fill="x")

        tk.Button(
            btn_frame, text="Create User", bg=Theme.SUCCESS, fg=Theme.WHITE,
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
        role_idx = self._role_combo.current()
        if role_idx < 0:
            messagebox.showwarning("Warning", "Please select a role.", parent=self)
            return

        data = {key: var.get() for key, var in self._vars.items()}
        data["role_id"] = self._roles[role_idx].get("role_id")

        if not data.get("username") or not data.get("password"):
            messagebox.showwarning("Warning", "Username and password are required.", parent=self)
            return

        self._on_submit(data)
        self.destroy()
