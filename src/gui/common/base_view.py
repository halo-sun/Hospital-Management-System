"""Base view class and reusable widgets for the GUI layer.

Provides the foundational ``BaseView`` that every screen inherits from,
along with standalone helper functions for creating labelled form rows,
cards, and styled buttons.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import (
    Any, Callable, Dict, List, Optional, Sequence, Tuple,
)

from src.gui.theme import Theme


# ═══════════════════════════════════════════════════════════════
# Base View
# ═══════════════════════════════════════════════════════════════

class BaseView(ttk.Frame):
    """Abstract base frame that every screen inherits from.

    Provides:
    * Consistent layout skeleton
    * Sortable ``create_treeview`` with click-to-sort columns
    * Right-click context menu for treeviews
    * Loading overlay (``with_loading`` context manager)
    * Responsive column weights (``make_responsive``)
    * Message helpers for info, warning, error, yes/no prompts
    """

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        """Initialise the base frame.

        Args:
            parent: Parent tkinter widget.
            **kwargs: Extra keyword arguments forwarded to ttk.Frame.
        """
        super().__init__(parent, **kwargs)
        self.configure(style="TFrame")

    # ── Message dialogs ───────────────────────────────────────

    def show_info(self, title: str, message: str) -> None:
        """Show an information message box.

        Args:
            title: Dialog title.
            message: Dialog body text.
        """
        messagebox.showinfo(title, message, parent=self)

    def show_warning(self, title: str, message: str) -> None:
        """Show a warning message box.

        Args:
            title: Dialog title.
            message: Dialog body text.
        """
        messagebox.showwarning(title, message, parent=self)

    def show_error(self, title: str, message: str) -> None:
        """Show an error message box.

        Args:
            title: Dialog title.
            message: Dialog body text.
        """
        messagebox.showerror(title, message, parent=self)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Show a yes/no confirmation dialog.

        Args:
            title: Dialog title.
            message: Dialog body text.

        Returns:
            True if the user clicked Yes, False otherwise.
        """
        return messagebox.askyesno(title, message, parent=self)

    # ── View management ───────────────────────────────────────

    def clear_frame(self) -> None:
        """Destroy all child widgets of this frame."""
        for widget in self.winfo_children():
            widget.destroy()

    def make_responsive(
        self, container: ttk.Frame, columns: int = 1,
    ) -> None:
        """Configure a container so its children stretch on resize.

        Call after packing/griding children.

        Args:
            container: The frame to configure.
            columns: Number of equally-weighted columns.
        """
        for col in range(columns):
            container.columnconfigure(col, weight=1, uniform="resp")
        container.rowconfigure(0, weight=1)

    # ── Sortable Treeview ─────────────────────────────────────

    def create_treeview(
        self,
        parent: tk.Widget,
        columns: Sequence[str],
        headings: Optional[Sequence[str]] = None,
        show: str = "headings",
        sortable: bool = True,
        enable_context_menu: bool = True,
        **kwargs: Any,
    ) -> ttk.Treeview:
        """Create a styled Treeview with sortable columns and context menu.

        Click a column heading to sort ascending; click again to
        toggle direction.  Right-click on a row to show a basic
        context menu (override ``_on_treeview_context_menu`` to
        customise).

        Args:
            parent: Parent widget.
            columns: Column ID list.
            headings: Human-readable heading labels (defaults to columns).
            show: Treeview show option.
            sortable: Whether columns are click-to-sort.
            enable_context_menu: Whether right-click shows a menu.

        Returns:
            Configured ttk.Treeview widget with sorting enabled.
        """
        headings = list(headings or columns)
        col_list = list(columns)

        tree = ttk.Treeview(parent, columns=col_list, show=show, **kwargs)

        for col, heading in zip(col_list, headings):
            tree.heading(col, text=heading, anchor="w")
            tree.column(col, anchor="w", minwidth=80, width=120)

        # Scrollbars
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Sortable columns
        if sortable:
            self._enable_sorting(tree, col_list)

        # Context menu
        if enable_context_menu:
            self._enable_context_menu(tree)

        return tree

    # ── Internal: treeview sorting ────────────────────────────

    # Class-level columns that should sort as dates/times rather than
    # plain strings.  Subclasses can extend via ``_date_sort_columns``.
    _date_sort_columns: set = {"date", "last_login", "created_at",
                                "updated_at", "holiday_date", "time"}

    # Per-view-class sort state.  Keyed by the concrete subclass so
    # each view type (Appointments, Doctors, …) remembers its own
    # sort independently, and the state survives view destroy/recreate
    # cycles (e.g. after a forced refresh).
    _sort_state_registry: Dict[str, Tuple[Optional[str], str]] = {}

    def _enable_sorting(
        self, tree: ttk.Treeview, columns: List[str],
    ) -> None:
        """Wire column-heading clicks to toggle-sort.

        Sort state is stored per concrete view class in
        ``_sort_state_registry`` so it survives tree rebuilds
        (e.g. after a forced refresh destroys and recreates
        the tree).

        Clicking a header sorts ascending; clicking again toggles to
descending; clicking a different header resets to ascending.

        The first time a view's tree is created, a default sort by
        ``"id"`` ascending is applied automatically (if an ``"id"``
        column exists).  Call ``apply_default_sort()`` after populating
        data to re-apply this default.

        Args:
            tree: The Treeview widget.
            columns: List of column IDs.
        """
        # Retrieve or initialise sort state for this view class
        _key = type(self).__name__
        if _key not in self._sort_state_registry:
            self._sort_state_registry[_key] = (None, "asc")

        def _sort_column(col: str) -> None:
            """Toggle sort direction and re-order rows."""
            cur_col, cur_dir = self._sort_state_registry.get(_key, (None, "asc"))
            if cur_col == col:
                new_dir = "desc" if cur_dir == "asc" else "asc"
            else:
                new_dir = "asc"
            self._sort_state_registry[_key] = (col, new_dir)

            # Gather rows
            items = [(tree.set(child, col), child)
                     for child in tree.get_children("")]
            if not items:
                return

            # Choose sort key: dates/times, numerics, then text
            use_date = col in self._date_sort_columns

            def _sort_key(pair: tuple) -> tuple:
                val = pair[0]
                if not val:
                    return (1, "")  # empty values sort last
                if use_date:
                    # Try DD-MM-YYYY first (canonical), then YYYY-MM-DD, then time
                    for date_fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                        try:
                            return (0, datetime.strptime(
                                str(val)[:10], date_fmt))
                        except ValueError:
                            pass
                    try:
                        return (0, datetime.strptime(
                            str(val)[:5], "%H:%M"))
                    except ValueError:
                        pass
                # Try numeric
                try:
                    return (0, float(val))
                except (ValueError, TypeError):
                    return (0, str(val).lower())

            items.sort(key=_sort_key, reverse=(new_dir == "desc"))

            # Re-insert in order
            for idx, (_, child) in enumerate(items):
                tree.move(child, "", idx)

            # Update heading indicators
            indicator = " ▲" if new_dir == "asc" else " ▼"
            for c in columns:
                text = tree.heading(c)["text"].rstrip(" \u25b2\u25bc")
                tree.heading(c, text=text)
            current_text = tree.heading(col)["text"].rstrip(" \u25b2\u25bc")
            tree.heading(col, text=f"{current_text}{indicator}")

        for col in columns:
            tree.heading(
                col, command=lambda c=col: _sort_column(c),
            )

        # If there was a previous sort, re-apply it now
        saved_col, saved_dir = self._sort_state_registry.get(_key, (None, "asc"))
        if saved_col and saved_col in columns:
            # Directly sort without toggling — just set state and sort
            self._sort_state_registry[_key] = (saved_col, saved_dir)
            # Build items and sort them
            items = [(tree.set(child, saved_col), child)
                     for child in tree.get_children("")]
            if items:
                use_date = saved_col in self._date_sort_columns
                def _reapply_key(pair: tuple) -> tuple:
                    val = pair[0]
                    if not val:
                        return (1, "")
                    if use_date:
                        for date_fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                            try:
                                return (0, datetime.strptime(
                                    str(val)[:10], date_fmt))
                            except ValueError:
                                pass
                        try:
                            return (0, datetime.strptime(
                                str(val)[:5], "%H:%M"))
                        except ValueError:
                            pass
                    try:
                        return (0, float(val))
                    except (ValueError, TypeError):
                        return (0, str(val).lower())
                items.sort(key=_reapply_key,
                           reverse=(saved_dir == "desc"))
                for idx, (_, child) in enumerate(items):
                    tree.move(child, "", idx)
            # Update heading indicators
            indicator = " \u25b2" if saved_dir == "asc" else " \u25bc"
            for c in columns:
                text = tree.heading(c)["text"].rstrip(" \u25b2\u25bc")
                tree.heading(c, text=text)
            current_text = tree.heading(saved_col)["text"].rstrip(" \u25b2\u25bc")
            tree.heading(saved_col,
                        text=f"{current_text}{indicator}")

        # Set default sort to ID ascending on first load
        if _key not in self._sort_state_registry or \
                self._sort_state_registry[_key] == (None, "asc"):
            if "id" in columns:
                self._sort_state_registry[_key] = ("id", "asc")

    # ── Internal: treeview context menu ───────────────────────

    def _enable_context_menu(self, tree: ttk.Treeview) -> None:
        """Wire right-click to show a context menu.

        The menu can be customised by overriding
        ``_on_treeview_context_menu`` in subclasses.

        Args:
            tree: The Treeview widget.
        """
        menu = tk.Menu(tree, tearoff=0, bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT,
                       font=Theme.FONT_SMALL, activebackground=Theme.ACCENT_LIGHT,
                       activeforeground=Theme.SURFACE_TEXT)

        # Default menu items
        menu.add_command(label="Select", command=lambda: None)

        def _show_context(event: tk.Event) -> None:
            """Select the row under cursor and show the menu."""
            iid = tree.identify_row(event.y)
            if iid:
                tree.selection_set(iid)
                tree.focus(iid)
                # Let subclasses customise the menu
                self._on_treeview_context_menu(tree, menu, iid)
                menu.post(event.x_root, event.y_root)

        tree.bind("<Button-3>", _show_context)

    def _on_treeview_context_menu(
        self, tree: ttk.Treeview, menu: tk.Menu, item_id: str,
    ) -> None:
        """Override in subclasses to customise the right-click menu.

        Base implementation adds a basic ``View Details`` option.

        Args:
            tree: The Treeview widget.
            menu: The popup Menu to modify.
            item_id: The internal ID of the item under the cursor.
        """
        values = tree.item(item_id, "values")
        if values:
            # Replace 'Select' label with first column's value
            menu.entryconfigure(0, label=f"Select {values[0]}")
        else:
            menu.entryconfigure(0, label="Select")

    def apply_default_sort(self, tree: ttk.Treeview) -> None:
        """Apply the default sort (ID ascending) to the given tree.

        Call this at the end of every ``populate()`` method after
        inserting rows.  It reads the saved sort state for the
        current view class and applies it; on first load that
        defaults to ``"id"`` ascending.

        Args:
            tree: The Treeview widget to sort.
        """
        _key = type(self).__name__
        col, direction = self._sort_state_registry.get(_key, ("id", "asc"))
        if not col:
            return
        columns = list(tree["columns"])
        if col not in columns:
            return
        items = [(tree.set(child, col), child)
                 for child in tree.get_children("")]
        if not items:
            return

        use_date = col in self._date_sort_columns

        def _sort_key(pair: tuple) -> tuple:
            val = pair[0]
            if not val:
                return (1, "")
            if use_date:
                for date_fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                    try:
                        return (0, datetime.strptime(
                            str(val)[:10], date_fmt))
                    except ValueError:
                        pass
                try:
                    return (0, datetime.strptime(
                        str(val)[:5], "%H:%M"))
                except ValueError:
                    pass
            try:
                return (0, float(val))
            except (ValueError, TypeError):
                return (0, str(val).lower())

        items.sort(key=_sort_key, reverse=(direction == "desc"))
        for idx, (_, child) in enumerate(items):
            tree.move(child, "", idx)

        # Update heading indicators
        indicator = " \u25b2" if direction == "asc" else " \u25bc"
        for c in columns:
            text = tree.heading(c)["text"].rstrip(" \u25b2\u25bc")
            tree.heading(c, text=text)
        current_text = tree.heading(col)["text"].rstrip(" \u25b2\u25bc")
        tree.heading(col, text=f"{current_text}{indicator}")

    # ── Loading overlay ──────────────────────────────────────

    def with_loading(self, message: str = "Loading...") -> "_LoadingContext":
        """Return a context manager that shows/hides a loading overlay.

        Usage::

            with self.with_loading("Searching..."):
                data = self._on_search(term)
                self.populate(data)

        Args:
            message: Text to display on the overlay.

        Returns:
            A context manager that manages the overlay lifecycle.
        """
        return _LoadingContext(self, message)


# ═══════════════════════════════════════════════════════════════
# Loading context manager
# ═══════════════════════════════════════════════════════════════

class _LoadingContext:
    """Context manager that displays a loading overlay on a parent frame.

    The overlay is a semi-transparent-like panel with a progress bar
    and message text that covers the entire parent.
    """

    def __init__(self, parent: tk.Widget, message: str = "Loading...") -> None:
        """Initialise the loading overlay.

        Args:
            parent: The widget to overlay.
            message: Loading message text.
        """
        self._parent = parent
        self._message = message
        self._overlay: Optional[tk.Frame] = None

    def __enter__(self) -> "_LoadingContext":
        """Create and display the overlay."""
        overlay = tk.Frame(self._parent, bg=Theme.SURFACE)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Inner container for vertical centering
        inner = tk.Frame(overlay, bg=Theme.SURFACE)
        inner.place(relx=0.5, rely=0.4, anchor="center")

        tk.Label(
            inner, text=self._message, bg=Theme.SURFACE, fg=Theme.SURFACE_TEXT,
            font=Theme.FONT_SUBHEADING,
        ).pack(pady=(0, 12))

        progress = ttk.Progressbar(inner, mode="indeterminate", length=200)
        progress.pack()
        progress.start(10)

        self._overlay = overlay
        self._parent.update_idletasks()
        return self

    def __exit__(self, *exc_args: Any) -> None:
        """Destroy the overlay."""
        if self._overlay is not None:
            self._overlay.destroy()
            self._overlay = None
            self._parent.update_idletasks()


# ═══════════════════════════════════════════════════════════════
# Helper: labelled entry
# ═══════════════════════════════════════════════════════════════

def create_label_entry(
    parent: tk.Widget,
    label_text: str,
    row: int,
    column: int = 0,
    placeholder: str = "",
    show: Optional[str] = None,
    width: int = 30,
    state: str = "normal",
) -> ttk.Entry:
    """Create a label + entry pair and return the Entry widget.

    Args:
        parent: Parent widget.
        label_text: Text for the label.
        row: Grid row to place the pair in.
        column: Grid column for the entry (label is at column-1 or column).
        placeholder: Placeholder text for the entry.
        show: Character masking (e.g. '*' for passwords).
        width: Entry width in characters.
        state: Entry state ('normal' or 'readonly').

    Returns:
        The created ttk.Entry widget.
    """
    lbl = ttk.Label(parent, text=label_text, font=Theme.FONT_BODY)
    lbl.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)

    entry = ttk.Entry(parent, width=width, font=Theme.FONT_BODY, state=state)
    if show:
        entry.configure(show=show)
    entry.grid(row=row, column=column + 1, sticky="ew", pady=4, padx=(0, 16))

    if placeholder:
        entry.insert(0, placeholder)
        entry.configure(foreground=Theme.MUTED)

        def _on_focus_in(e: tk.Event) -> None:
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.configure(foreground=Theme.DARK_TEXT)

        def _on_focus_out(e: tk.Event) -> None:
            if not entry.get():
                entry.insert(0, placeholder)
                entry.configure(foreground=Theme.MUTED)

        entry.bind("<FocusIn>", _on_focus_in)
        entry.bind("<FocusOut>", _on_focus_out)

    return entry


# ═══════════════════════════════════════════════════════════════
# Helper: labelled combobox
# ═══════════════════════════════════════════════════════════════

def create_combo_box(
    parent: tk.Widget,
    label_text: str,
    values: List[str],
    row: int,
    column: int = 0,
    width: int = 28,
    state: str = "readonly",
) -> ttk.Combobox:
    """Create a label + combobox pair and return the Combobox widget.

    Args:
        parent: Parent widget.
        label_text: Text for the label.
        values: List of selectable values.
        row: Grid row.
        column: Grid column for the entry.
        width: Combobox width.
        state: Combobox state.

    Returns:
        The created ttk.Combobox widget.
    """
    lbl = ttk.Label(parent, text=label_text, font=Theme.FONT_BODY)
    lbl.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=4)

    combo = ttk.Combobox(
        parent, values=values, width=width,
        font=Theme.FONT_BODY, state=state,
    )
    combo.grid(row=row, column=column + 1, sticky="ew", pady=4, padx=(0, 16))
    return combo


# ═══════════════════════════════════════════════════════════════
# Helper: styled button
# ═══════════════════════════════════════════════════════════════

def create_button(
    parent: tk.Widget,
    text: str,
    command: Optional[Callable] = None,
    style: str = "TButton",
    row: Optional[int] = None,
    column: Optional[int] = None,
    **kwargs: Any,
) -> ttk.Button:
    """Create a styled button and optionally grid it.

    Args:
        parent: Parent widget.
        text: Button label.
        command: Callback.
        style: ttk style name (e.g. 'Primary.TButton', 'Success.TButton').
        row: Optional grid row.
        column: Optional grid column.
        **kwargs: Extra grid options.

    Returns:
        The created ttk.Button widget.
    """
    btn = ttk.Button(parent, text=text, command=command, style=style)
    if row is not None and column is not None:
        btn.grid(row=row, column=column, sticky="ew", pady=4, padx=4)
    return btn


# ═══════════════════════════════════════════════════════════════
# Helper: card widget
# ═══════════════════════════════════════════════════════════════

def create_card(
    parent: tk.Widget,
    title: str,
    value: str,
    row: int,
    column: int = 0,
    subtitle: str = "",
) -> ttk.Frame:
    """Create a dashboard summary card with optional subtitle.

    Args:
        parent: Parent widget.
        title: Card title.
        value: Card value text.
        row: Grid row.
        column: Grid column.
        subtitle: Optional additional info shown below the value.

    Returns:
        The card frame widget.
    """
    card = ttk.Frame(parent, style="Card.TFrame", padding=16)
    card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")

    lbl_title = ttk.Label(card, text=title, style="CardTitle.TLabel")
    lbl_title.pack(anchor="w")

    lbl_value = ttk.Label(card, text=value, style="CardValue.TLabel")
    lbl_value.pack(anchor="w", pady=(4, 0))

    if subtitle:
        lbl_sub = ttk.Label(card, text=subtitle, style="Muted.TLabel")
        lbl_sub.pack(anchor="w", pady=(2, 0))

    return card


# ═══════════════════════════════════════════════════════════════
# Helper: status badge
# ═══════════════════════════════════════════════════════════════

def create_status_badge(
    parent: tk.Widget,
    text: str,
    color: Optional[str] = None,
) -> tk.Label:
    """Create a coloured status badge label.

    Args:
        parent: Parent widget.
        text: Status text.
        color: Background colour (defaults from ``Theme.status_color``).

    Returns:
        A styled tk.Label representing the status badge.
    """
    if color is None:
        color = Theme.status_color(text)

    badge = tk.Label(
        parent, text=text, bg=color, fg=Theme.WHITE,
        font=Theme.FONT_SMALL_BOLD, padx=8, pady=2,
        bd=0,
    )
    return badge
