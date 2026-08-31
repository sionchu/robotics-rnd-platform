"""Small native ttk widgets used by the workbench."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from .models import MetricSeries


class PropertyInspector(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        ttk.Label(self, text="PROPERTY / EXPLAIN", style="Heading.TLabel").pack(anchor="w", padx=6, pady=5)
        self.tree = ttk.Treeview(self, columns=("value",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Property")
        self.tree.heading("value", text="Value")
        self.tree.column("#0", width=125, stretch=False)
        self.tree.column("value", width=230, stretch=True)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(0, 6))
        scroll.pack(side="right", fill="y", padx=(0, 6), pady=(0, 6))

    def show(self, title: str, properties: dict[str, Any], explanation: str = "") -> None:
        self.tree.delete(*self.tree.get_children())
        root = self.tree.insert("", "end", text=title, values=(explanation,), open=True)
        for key, value in properties.items():
            if isinstance(value, dict):
                parent = self.tree.insert(root, "end", text=str(key), open=True)
                for child_key, child_value in value.items():
                    self.tree.insert(parent, "end", text=str(child_key), values=(self._display(child_value),))
            elif isinstance(value, list):
                parent = self.tree.insert(root, "end", text=str(key), values=(f"{len(value)} items",))
                for index, child in enumerate(value):
                    self.tree.insert(parent, "end", text=str(index), values=(self._display(child),))
            else:
                self.tree.insert(root, "end", text=str(key), values=(self._display(value),))

    @staticmethod
    def _display(value: Any) -> str:
        if value is None:
            return "N/A"
        return str(value)


class MetricPlot(ttk.Frame):
    COLORS = ("#2455a4", "#a33d2b", "#2f7d32", "#7a4aa0")

    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master)
        self.title = title
        ttk.Label(self, text=title).pack(anchor="w")
        self.canvas = tk.Canvas(self, height=105, background="white", highlightthickness=1)
        self.canvas.pack(fill="both", expand=True)
        self.table = ttk.Treeview(
            self,
            columns=("series", "step", "value"),
            show="headings",
            height=3,
        )
        for column, width in (("series", 165), ("step", 55), ("value", 95)):
            self.table.heading(column, text=column.title())
            self.table.column(column, width=width, stretch=column == "series")
        self.table.pack(fill="x")
        self.series: list[MetricSeries] = []
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_series(self, series: list[MetricSeries]) -> None:
        self.series = [item for item in series if item.points]
        self.table.delete(*self.table.get_children())
        for item in self.series:
            for step, value in item.points:
                self.table.insert("", "end", values=(item.name, step, f"{value:.8g}"))
        self.redraw()

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 200)
        height = max(canvas.winfo_height(), 120)
        margin = 28
        canvas.create_line(margin, 8, margin, height - margin, fill="#555")
        canvas.create_line(margin, height - margin, width - 8, height - margin, fill="#555")
        points = [point for series in self.series for point in series.points]
        if not points:
            canvas.create_text(width / 2, height / 2, text="No metric data", fill="#666")
            return
        min_step = min(point[0] for point in points)
        max_step = max(point[0] for point in points)
        min_value = min(point[1] for point in points)
        max_value = max(point[1] for point in points)
        step_span = max(max_step - min_step, 1)
        value_span = max(max_value - min_value, 1.0e-12)
        for index, series in enumerate(self.series):
            coords: list[float] = []
            for step, value in series.points:
                x = margin + (step - min_step) / step_span * (width - margin - 10)
                y = height - margin - (value - min_value) / value_span * (height - margin - 12)
                coords.extend((x, y))
            if len(coords) >= 4:
                canvas.create_line(*coords, fill=self.COLORS[index % len(self.COLORS)], width=1.5)
        canvas.create_text(margin + 2, 10, text=f"{max_value:.3g}", anchor="nw", fill="#555")
        canvas.create_text(margin + 2, height - margin - 2, text=f"{min_value:.3g}", anchor="sw", fill="#555")
        canvas.create_text(width - 10, height - margin + 4, text=str(max_step), anchor="ne", fill="#555")
