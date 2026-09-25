"""Tk desktop interface for four everyday utilities."""

import csv
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from windows_apps.core import (
    Move, duplicate_groups, execute_moves, rename_plan, sort_plan, transform_text,
)


TOOLS = ("Rename files", "Sort folder", "Find duplicates", "Text tools")


def button(parent: tk.Widget, label: str, command) -> ttk.Button:
    control = ttk.Button(parent, text=label, command=command)
    control.pack(side="left", padx=(0, 8))
    return control


def row(parent: tk.Widget) -> ttk.Frame:
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=(0, 10))
    return frame


def preview_table(parent: tk.Widget) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    table = ttk.Treeview(frame, columns=("from", "to"), show="headings")
    table.heading("from", text="From")
    table.heading("to", text="To")
    table.column("from", width=320)
    table.column("to", width=320)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    table.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return table


def fill_preview(table: ttk.Treeview, moves: list[Move]) -> None:
    table.delete(*table.get_children())
    for move in moves:
        table.insert("", "end", values=(str(move.source), str(move.destination)))


class FilePanel(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=16)
        self.plan: list[Move] = []
        self.undo: list[Move] = []

    def show_plan(self, moves: list[Move]) -> None:
        self.plan = moves
        fill_preview(self.table, moves)
        self.status.set(f"{len(moves)} file(s) ready. Review the destination before applying.")

    def apply(self) -> None:
        if not self.plan:
            messagebox.showinfo("Nothing to do", "Preview a change first.", parent=self)
            return
        if not messagebox.askyesno("Confirm changes", f"Move {len(self.plan)} files?", parent=self):
            return
        try:
            execute_moves(self.plan)
            self.undo = self.plan
            self.plan = []
            fill_preview(self.table, [])
            self.status.set(f"Moved {len(self.undo)} files. Undo is available until you close this window.")
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not move files", str(error), parent=self)

    def undo_last(self) -> None:
        if not self.undo:
            messagebox.showinfo("Nothing to undo", "No completed operation in this window.", parent=self)
            return
        try:
            backwards = [
                Move(move.destination, move.source, move.size, move.modified_ns)
                for move in self.undo
            ]
            execute_moves(backwards)
            self.undo = []
            self.plan = []
            fill_preview(self.table, [])
            self.status.set("Last operation undone.")
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not undo", str(error), parent=self)


class RenamePanel(FilePanel):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.files: list[Path] = []
        self.selected = tk.StringVar(value="No files selected")
        self.status = tk.StringVar(value="Select files, choose a rule, then preview.")
        self.find = tk.StringVar()
        self.replace = tk.StringVar()
        self.prefix = tk.StringVar()
        self.suffix = tk.StringVar()
        self.numbering = tk.BooleanVar()
        self.start = tk.StringVar(value="1")

        controls = row(self)
        button(controls, "Choose files…", self.choose_files)
        ttk.Label(controls, textvariable=self.selected).pack(side="left")
        for label, variable in (("Find", self.find), ("Replace", self.replace),
                                ("Prefix", self.prefix), ("Suffix", self.suffix)):
            controls = row(self)
            ttk.Label(controls, text=label, width=12).pack(side="left")
            ttk.Entry(controls, textvariable=variable).pack(side="left", fill="x", expand=True)
        controls = row(self)
        ttk.Checkbutton(controls, text="Add sequence number", variable=self.numbering).pack(side="left")
        ttk.Label(controls, text="Start at").pack(side="left", padx=(16, 5))
        ttk.Entry(controls, textvariable=self.start, width=8).pack(side="left")
        controls = row(self)
        button(controls, "Preview", self.preview)
        button(controls, "Apply", self.apply)
        button(controls, "Undo last", self.undo_last)
        ttk.Label(self, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        self.table = preview_table(self)

    def choose_files(self) -> None:
        selection = filedialog.askopenfilenames(parent=self, title="Choose files to rename")
        if selection:
            self.files = [Path(name) for name in selection]
            self.selected.set(f"{len(self.files)} file(s) selected")
            self.plan = []
            fill_preview(self.table, [])

    def preview(self) -> None:
        try:
            self.show_plan(rename_plan(
                self.files, self.find.get(), self.replace.get(), self.prefix.get(),
                self.suffix.get(), self.numbering.get(), int(self.start.get()),
            ))
        except (OSError, ValueError) as error:
            self.plan = []
            fill_preview(self.table, [])
            messagebox.showerror("Cannot preview", str(error), parent=self)


class SortPanel(FilePanel):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.folder = tk.StringVar()
        self.status = tk.StringVar(value="Only files directly inside the selected folder are moved.")
        controls = row(self)
        ttk.Entry(controls, textvariable=self.folder).pack(side="left", fill="x", expand=True, padx=(0, 8))
        button(controls, "Choose folder…", self.choose_folder)
        controls = row(self)
        button(controls, "Preview", self.preview)
        button(controls, "Apply", self.apply)
        button(controls, "Undo last", self.undo_last)
        ttk.Label(self, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        self.table = preview_table(self)

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Choose a folder to organize")
        if folder:
            self.folder.set(folder)
            self.plan = []
            fill_preview(self.table, [])

    def preview(self) -> None:
        try:
            self.show_plan(sort_plan(Path(self.folder.get())))
        except (OSError, ValueError) as error:
            self.plan = []
            fill_preview(self.table, [])
            messagebox.showerror("Cannot preview", str(error), parent=self)


class DuplicatesPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=16)
        self.folder = tk.StringVar()
        self.status = tk.StringVar(value="Scan subfolders by file size and SHA-256 content.")
        self.groups: list[list[Path]] = []
        controls = row(self)
        ttk.Entry(controls, textvariable=self.folder).pack(side="left", fill="x", expand=True, padx=(0, 8))
        button(controls, "Choose folder…", self.choose_folder)
        controls = row(self)
        self.scan_button = button(controls, "Scan", self.scan)
        button(controls, "Export CSV…", self.export)
        ttk.Label(self, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        self.table = preview_table(self)
        self.table.heading("from", text="Group")
        self.table.heading("to", text="File path")

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Choose a folder to scan")
        if folder:
            self.folder.set(folder)

    def scan(self) -> None:
        folder = Path(self.folder.get())
        if not folder.is_dir():
            messagebox.showerror("Cannot scan", "Choose an existing folder.", parent=self)
            return
        self.groups = []
        self.table.delete(*self.table.get_children())
        self.scan_button.configure(state="disabled")
        self.status.set("Scanning…")

        def worker() -> None:
            try:
                result = duplicate_groups(folder)
            except (OSError, ValueError) as error:
                self.after(0, lambda message=str(error): self.scan_failed(message))
            else:
                self.after(0, lambda: self.show_results(*result))

        threading.Thread(target=worker, daemon=True).start()

    def scan_failed(self, error: str) -> None:
        self.scan_button.configure(state="normal")
        self.status.set("Scan failed.")
        messagebox.showerror("Cannot scan", error, parent=self)

    def show_results(self, groups: list[list[Path]], skipped: list[Path]) -> None:
        self.groups = groups
        self.scan_button.configure(state="normal")
        for number, paths in enumerate(groups, 1):
            for path in paths:
                self.table.insert("", "end", values=(number, str(path)))
        self.status.set(f"{len(groups)} duplicate group(s), {sum(map(len, groups))} matching files; "
                        f"{len(skipped)} unreadable file(s) skipped. No files were removed.")

    def export(self) -> None:
        if not self.groups:
            messagebox.showinfo("No results", "Scan for duplicates first.", parent=self)
            return
        filename = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv")])
        if filename:
            try:
                with open(filename, "w", newline="", encoding="utf-8-sig") as output:
                    writer = csv.writer(output)
                    writer.writerow(("Group", "File path"))
                    for number, paths in enumerate(self.groups, 1):
                        writer.writerows((number, str(path)) for path in paths)
                self.status.set(f"Exported {len(self.groups)} groups to {filename}")
            except OSError as error:
                messagebox.showerror("Export failed", str(error), parent=self)


class TextPanel(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, padding=16)
        self.status = tk.StringVar(value="Paste text on the left; results appear on the right.")
        controls = row(self)
        for action in ("Trim lines", "Remove empty lines", "Unique lines", "Sort lines", "Collapse spaces"):
            button(controls, action, lambda selected=action: self.transform(selected))
        controls = row(self)
        button(controls, "Paste clipboard", self.paste)
        button(controls, "Copy result", self.copy)
        button(controls, "Use result as input", self.use_result)
        ttk.Label(self, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)
        for title in ("Input", "Result"):
            frame = ttk.Frame(panes)
            ttk.Label(frame, text=title).pack(anchor="w")
            text = tk.Text(frame, wrap="word", undo=True)
            text.pack(fill="both", expand=True)
            panes.add(frame, weight=1)
            if title == "Input":
                self.input = text
            else:
                self.result = text

    def transform(self, action: str) -> None:
        value = transform_text(self.input.get("1.0", "end-1c"), action)
        self.result.delete("1.0", "end")
        self.result.insert("1.0", value)
        self.status.set(f"Applied: {action}")

    def paste(self) -> None:
        try:
            value = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Clipboard empty", "No text is available to paste.", parent=self)
            return
        self.input.delete("1.0", "end")
        self.input.insert("1.0", value)

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.result.get("1.0", "end-1c"))
        self.status.set("Result copied to clipboard.")

    def use_result(self) -> None:
        value = self.result.get("1.0", "end-1c")
        self.input.delete("1.0", "end")
        self.input.insert("1.0", value)


def main(args: list[str]) -> None:
    if len(args) > 1 or (args and args[0] not in ("rename", "sort", "duplicates", "text")):
        raise SystemExit("Usage: python -m windows_apps [rename|sort|duplicates|text]")
    root = tk.Tk()
    root.title("Everyday Tools")
    root.geometry("950x650")
    root.minsize(760, 500)
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    for title, panel in zip(TOOLS, (RenamePanel, SortPanel, DuplicatesPanel, TextPanel)):
        notebook.add(panel(notebook), text=title)
    if args:
        notebook.select(("rename", "sort", "duplicates", "text").index(args[0]))
        root.title(f"{TOOLS[notebook.index('current')]} — Everyday Tools")
    root.mainloop()
