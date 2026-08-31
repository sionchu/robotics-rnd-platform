"""Classic tkinter composition root for robot-learning inspection and runs."""

from __future__ import annotations

import json
import os
import queue
import tkinter as tk
from datetime import datetime
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from .discovery import discover_experiments, find_repo_root, inspect_workspace
from .models import (
    CommandSpec,
    EvaluationResult,
    ExperimentSummary,
    MetricSeries,
    WorkbenchSettings,
    measured_change,
    normalize_evaluation,
    normalized_to_physical,
    session_path,
    sha256_file,
    transition_matrix,
)
from .process_runner import (
    ProcessEvent,
    ProcessRunner,
    build_experiment_script_command,
    build_gui_command,
    build_metrics_command,
    build_probe_command,
    build_train_command,
    format_spec,
)
from .widgets import MetricPlot, PropertyInspector

GUIDED_SECTIONS = {
    "Goal": "목표 (Goal)",
    "Success": "성공 조건 (Success)",
    "Observation": "관측 (Observation)",
    "Action": "행동 (Action)",
    "Reward": "보상 (Reward)",
    "Termination": "종료 조건 (Termination)",
    "Reset / Distribution": "초기화 / 랜덤화 (Reset / Distribution)",
    "PPO / Training": "PPO / 학습 (PPO / Training)",
}

GUIDED_EXPLANATIONS = {
    "Goal": "로봇 정책이 최종적으로 달성해야 하는 작업입니다.",
    "Success": "에피소드를 성공으로 기록하는 실제 판정 조건입니다.",
    "Observation": "정책 신경망이 현재 상태를 판단할 때 실제로 입력받는 값입니다.",
    "Action": "정책이 로봇에게 내리는 명령입니다. 스케일을 적용하면 실제 이동량이 됩니다.",
    "Reward": "성공 조건 자체가 아니라, 정책이 성공 행동을 발견하도록 주는 학습 신호입니다.",
    "Termination": "성공 또는 시간 제한처럼 에피소드가 끝나는 이유입니다.",
    "Reset / Distribution": "에피소드마다 바뀌는 조건으로, 정책이 학습하는 문제 분포를 정의합니다.",
    "PPO / Training": "환경 정의를 고정한 뒤 정책을 업데이트하는 학습 설정입니다.",
}

WORKFLOW_STAGES = (
    "Environment / Config Check",
    "GUI Reviewed",
    "Semantic / Task Gate",
    "Random Baseline",
    "PPO Smoke",
    "Full Training",
    "Deterministic Evaluation",
    "Hold-Out Evaluation",
    "Evidence Recorded",
)

PROCESS_FLOW = (
    ("ASSET", "asset"),
    ("SCENE", "asset"),
    ("TASK GOAL / SUCCESS", "task"),
    ("OBSERVATION + ACTION", "task"),
    ("REWARD + RESET DISTRIBUTION", "task"),
    ("GUI VERIFY", "training"),
    ("RANDOM BASELINE", "training"),
    ("PPO SMOKE", "training"),
    ("TRAIN", "training"),
    ("EVALUATE", "evaluation"),
    ("HOLD-OUT", "evaluation"),
    ("FAILURE ANALYSIS", "evaluation"),
    ("NEXT HYPOTHESIS", "task"),
)


class RobotLearningWorkbench:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.settings = WorkbenchSettings.load()
        self.repo_root = self._initial_repo_root()
        self.isaac_lab_root = self._initial_isaac_root()
        self.experiments: list[ExperimentSummary] = []
        self.current_experiment: ExperimentSummary | None = None
        self.workspace: Any = None
        self.probe_data: dict[str, Any] = {}
        self.asset_rows: dict[str, dict[str, Any]] = {}
        self.current_spec: CommandSpec | None = None
        self.running_spec: CommandSpec | None = None
        self.runner = ProcessRunner()
        self.metric_series: dict[str, MetricSeries] = {}
        self.evaluations: list[EvaluationResult | None] = [None, None]
        self.mode_var = tk.StringVar(value=self.settings.presentation_mode or "guided")
        self.envs_var = tk.IntVar(value=64)
        self.seed_var = tk.IntVar(value=42)
        self.iterations_var = tk.IntVar(value=5)
        self.device_var = tk.StringVar(value="cuda:0")
        self.run_name_var = tk.StringVar(value="workbench_smoke_seed42")
        self.headless_var = tk.BooleanVar(value=True)
        self.gui_reviewed_var = tk.BooleanVar(value=False)
        self.status_vars = {
            name: tk.StringVar(value="NOT CHECKED") for name in ("repo", "isaac", "task", "process", "gpu")
        }
        self._configure_root()
        self._build_ui()
        self.refresh_workspace()
        self.root.after(100, self._poll_process)

    def _initial_repo_root(self) -> Path:
        configured = Path(self.settings.repo_root) if self.settings.repo_root else None
        if configured and (configured / ".git").exists():
            return configured
        discovered = find_repo_root(Path.cwd())
        return discovered or Path.cwd()

    def _initial_isaac_root(self) -> Path | None:
        configured = Path(self.settings.isaac_lab_root) if self.settings.isaac_lab_root else None
        if configured and configured.is_dir():
            return configured
        environment = os.environ.get("ISAACLAB_PATH")
        if environment and Path(environment).is_dir():
            return Path(environment)
        return None

    def _configure_root(self) -> None:
        self.root.title("Robot Learning Workbench")
        self.root.geometry(self.settings.window_geometry or "1480x900")
        self.root.minsize(1080, 700)
        style = ttk.Style(self.root)
        style.configure("Heading.TLabel", font=("TkDefaultFont", 10, "bold"))
        style.configure("Status.TLabel", relief="sunken", padding=(5, 2))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        self._build_menu()
        self._build_toolbar()
        vertical = ttk.PanedWindow(self.root, orient="vertical")
        vertical.pack(fill="both", expand=True)
        horizontal = ttk.PanedWindow(vertical, orient="horizontal")
        vertical.add(horizontal, weight=5)

        explorer_frame = ttk.Frame(horizontal, width=245)
        self._build_explorer(explorer_frame)
        horizontal.add(explorer_frame, weight=1)

        center = ttk.Frame(horizontal)
        self.notebook = ttk.Notebook(center)
        self.notebook.pack(fill="both", expand=True)
        self._build_overview_tab()
        self._build_asset_tab()
        self._build_task_tab()
        self._build_training_tab()
        self._build_evaluation_tab()
        horizontal.add(center, weight=5)

        self.inspector = PropertyInspector(horizontal)
        horizontal.add(self.inspector, weight=2)

        console_frame = ttk.Frame(vertical, height=190)
        self._build_console(console_frame)
        vertical.add(console_frame, weight=1)
        self._build_statusbar()

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Open Workspace...", command=self.choose_workspace)
        file_menu.add_command(label="Configure Isaac Lab...", command=self.choose_isaac_lab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close)
        menu.add_cascade(label="File", menu=file_menu)
        workspace = tk.Menu(menu, tearoff=False)
        workspace.add_command(label="Refresh", command=self.refresh_workspace)
        workspace.add_command(label="Probe Selected Task", command=self.probe_task)
        menu.add_cascade(label="Workspace", menu=workspace)
        asset = tk.Menu(menu, tearoff=False)
        asset.add_command(label="Browse External Asset...", command=self.add_external_asset)
        asset.add_command(label="Open Location", command=self.open_asset_location)
        menu.add_cascade(label="Asset", menu=asset)
        task = tk.Menu(menu, tearoff=False)
        task.add_command(label="Launch Task GUI", command=self.launch_gui)
        task.add_command(label="Mark GUI Reviewed", command=lambda: self.gui_reviewed_var.set(True))
        menu.add_cascade(label="Task", menu=task)
        training = tk.Menu(menu, tearoff=False)
        training.add_command(label="Preview 5-Iteration Smoke", command=lambda: self.preview_training(5))
        training.add_command(label="Preview Full Config Run", command=self.preview_full_training)
        training.add_command(label="Preview Semantic Gate", command=self.preview_semantic_gate)
        training.add_command(label="Preview Random Baseline", command=self.preview_random_baseline)
        training.add_command(label="Stop Tracked Process", command=self.stop_process)
        menu.add_cascade(label="Training", menu=training)
        evaluation = tk.Menu(menu, tearoff=False)
        evaluation.add_command(label="Open Result A...", command=lambda: self.load_evaluation(0))
        evaluation.add_command(label="Open Result B...", command=lambda: self.load_evaluation(1))
        evaluation.add_command(
            label="Preview Deterministic Evaluation", command=self.preview_deterministic_evaluation
        )
        menu.add_cascade(label="Evaluation", menu=evaluation)
        view = tk.Menu(menu, tearoff=False)
        view.add_radiobutton(
            label="Guided Mode", variable=self.mode_var, value="guided", command=self._mode_changed
        )
        view.add_radiobutton(
            label="Engineering Mode", variable=self.mode_var, value="engineering", command=self._mode_changed
        )
        menu.add_cascade(label="View", menu=view)
        self.root.configure(menu=menu)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root, relief="raised")
        toolbar.pack(fill="x")
        buttons = (
            ("Open Workspace", self.choose_workspace),
            ("Refresh", self.refresh_workspace),
            ("Probe Task", self.probe_task),
            ("Launch GUI", self.launch_gui),
            ("Stop", self.stop_process),
            ("Copy Command", self.copy_command),
        )
        for label, command in buttons:
            ttk.Button(toolbar, text=label, command=command).pack(side="left", padx=2, pady=3)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(toolbar, text="Mode:").pack(side="left")
        ttk.Combobox(
            toolbar,
            textvariable=self.mode_var,
            values=("guided", "engineering"),
            state="readonly",
            width=13,
        ).pack(side="left", padx=3)
        self.mode_var.trace_add("write", lambda *_args: self._mode_changed())

    def _build_explorer(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="PROJECT EXPLORER", style="Heading.TLabel").pack(anchor="w", padx=5, pady=5)
        self.explorer = ttk.Treeview(parent, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.explorer.yview)
        self.explorer.configure(yscrollcommand=scroll.set)
        self.explorer.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=(0, 5))
        scroll.pack(side="right", fill="y", padx=(0, 5), pady=(0, 5))
        self.explorer.bind("<<TreeviewSelect>>", self._explorer_selected)

    def _build_overview_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Overview")
        ttk.Label(tab, text="Asset-to-Learning Workflow", style="Heading.TLabel").pack(
            anchor="w", padx=8, pady=6
        )
        flow = ttk.Frame(tab)
        flow.pack(fill="x", padx=8)
        for index, (label, target) in enumerate(PROCESS_FLOW):
            ttk.Button(flow, text=label, command=partial(self._select_tab, target)).grid(
                row=index // 4, column=index % 4, sticky="ew", padx=2, pady=2
            )
        for column_index in range(4):
            flow.columnconfigure(column_index, weight=1)
        ttk.Separator(tab).pack(fill="x", padx=8, pady=8)
        ttk.Label(tab, text="Workspace Readiness", style="Heading.TLabel").pack(anchor="w", padx=8)
        self.workspace_tree = ttk.Treeview(
            tab, columns=("item", "state", "value", "action"), show="headings", height=9
        )
        for column_name, width in (
            ("item", 145),
            ("state", 120),
            ("value", 570),
            ("action", 180),
        ):
            self.workspace_tree.heading(column_name, text=column_name.title())
            self.workspace_tree.column(column_name, width=width, stretch=column_name == "value")
        self.workspace_tree.pack(fill="both", expand=True, padx=8, pady=5)
        ttk.Label(tab, text="Run / Evidence History", style="Heading.TLabel").pack(
            anchor="w", padx=8, pady=(5, 0)
        )
        self.run_tree = ttk.Treeview(
            tab,
            columns=("task", "timestamp", "checkpoint", "sha256", "status"),
            show="tree headings",
            height=5,
        )
        for column_name in ("task", "timestamp", "checkpoint", "sha256", "status"):
            self.run_tree.heading(column_name, text=column_name.title())
            self.run_tree.column(column_name, width=150, stretch=column_name in {"task", "sha256"})
        self.run_tree.pack(fill="x", padx=8, pady=5)

    def _build_asset_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Asset")
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", padx=6, pady=5)
        for label, command in (
            ("Browse External Asset...", self.add_external_asset),
            ("Inspect", self.inspect_asset),
            ("Open Location", self.open_asset_location),
            ("Copy Path", self.copy_asset_path),
            ("Open in Isaac Sim", self.open_asset_in_isaac),
        ):
            ttk.Button(toolbar, text=label, command=command).pack(side="left", padx=2)
        columns = ("type", "source", "status", "prim", "role", "owner")
        self.asset_tree = ttk.Treeview(tab, columns=columns, show="tree headings", selectmode="browse")
        self.asset_tree.heading("#0", text="Name")
        self.asset_tree.column("#0", width=150)
        headings = {
            "type": "Type",
            "source": "Source",
            "status": "Status",
            "prim": "Prim Path",
            "role": "Robot / Fixture / Sensor",
            "owner": "Referenced By",
        }
        for name in columns:
            self.asset_tree.heading(name, text=headings[name])
            self.asset_tree.column(name, width=135, stretch=name in {"source", "prim", "owner"})
        self.asset_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.asset_tree.bind("<<TreeviewSelect>>", lambda _event: self.inspect_asset())

    def _build_task_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Task / MDP")
        pane = ttk.PanedWindow(tab, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pane, width=240)
        ttk.Label(left, text="Learning Definition", style="Heading.TLabel").pack(anchor="w")
        self.mdp_tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.mdp_tree.pack(fill="both", expand=True, pady=4)
        self.mdp_tree.bind("<<TreeviewSelect>>", self._mdp_selected)
        pane.add(left, weight=1)
        right = ttk.Frame(pane)
        self.mdp_title = ttk.Label(right, text="Select a section", style="Heading.TLabel")
        self.mdp_title.pack(anchor="w")
        self.mdp_explanation = ttk.Label(right, text="", wraplength=760, justify="left")
        self.mdp_explanation.pack(anchor="w", fill="x", pady=(2, 6))
        self.mdp_detail = ttk.Treeview(
            right, columns=("value", "unit", "source"), show="tree headings", selectmode="browse"
        )
        self.mdp_detail.heading("#0", text="Term / Property")
        for column, title, width in (
            ("value", "Value", 330),
            ("unit", "Unit", 90),
            ("source", "Source", 160),
        ):
            self.mdp_detail.heading(column, text=title)
            self.mdp_detail.column(column, width=width, stretch=column == "value")
        self.mdp_detail.pack(fill="both", expand=True)
        pane.add(right, weight=4)
        self._build_question_panel(tab)

    def _build_question_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Local Experiment Question — stored outside repository")
        frame.pack(fill="x", padx=6, pady=(0, 6))
        self.note_vars: dict[str, tk.StringVar] = {}
        fields = (
            "Experiment Question",
            "Hypothesis",
            "Single Variable",
            "Expected Positive Result",
            "Expected Negative Result",
            "Metrics",
            "Stop Condition",
        )
        for index, name in enumerate(fields):
            row, column = divmod(index, 2)
            ttk.Label(frame, text=name).grid(row=row, column=column * 2, sticky="w", padx=3, pady=2)
            variable = tk.StringVar()
            self.note_vars[name] = variable
            ttk.Entry(frame, textvariable=variable).grid(
                row=row, column=column * 2 + 1, sticky="ew", padx=3, pady=2
            )
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        ttk.Button(frame, text="Save Local Note", command=self.save_local_note).grid(
            row=4, column=2, sticky="e", padx=3, pady=3
        )
        ttk.Button(frame, text="Export Markdown...", command=self.export_note).grid(
            row=4, column=3, sticky="e", padx=3, pady=3
        )

    def _build_training_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Training")
        upper = ttk.PanedWindow(tab, orient="horizontal")
        upper.pack(fill="both", expand=True, padx=6, pady=6)
        controls = ttk.Frame(upper, width=340)
        ttk.Label(controls, text="Run Workflow", style="Heading.TLabel").pack(anchor="w")
        self.workflow_tree = ttk.Treeview(controls, columns=("state",), show="tree headings", height=9)
        self.workflow_tree.heading("#0", text="Stage")
        self.workflow_tree.heading("state", text="State")
        self.workflow_tree.column("state", width=85, stretch=False)
        self.workflow_tree.pack(fill="x", pady=4)
        for stage in WORKFLOW_STAGES:
            self.workflow_tree.insert("", "end", iid=stage, text=stage, values=("NOT CHECKED",))
        ttk.Checkbutton(
            controls,
            text="GUI Reviewed (local session evidence)",
            variable=self.gui_reviewed_var,
            command=self._gui_review_changed,
        ).pack(anchor="w", pady=3)
        form = ttk.LabelFrame(controls, text="Environment / PPO Run")
        form.pack(fill="x", pady=5)
        entries = (
            ("Envs", self.envs_var),
            ("Seed", self.seed_var),
            ("Device", self.device_var),
            ("Iterations", self.iterations_var),
            ("Run Name", self.run_name_var),
        )
        for row, (label, variable) in enumerate(entries):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=3, pady=2)
            ttk.Entry(form, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=3, pady=2)
        form.columnconfigure(1, weight=1)
        ttk.Checkbutton(form, text="Headless", variable=self.headless_var).grid(
            row=len(entries), column=1, sticky="w", padx=3
        )
        presets = ttk.Frame(controls)
        presets.pack(fill="x", pady=4)
        ttk.Button(presets, text="5-Iteration Smoke", command=lambda: self.preview_training(5)).pack(
            side="left", padx=2
        )
        ttk.Button(presets, text="Full Config Run", command=self.preview_full_training).pack(
            side="left", padx=2
        )
        ttk.Button(presets, text="Run", command=self.run_previewed).pack(side="right", padx=2)
        experiment_runners = ttk.LabelFrame(controls, text="Experiment-Provided Runners")
        experiment_runners.pack(fill="x", pady=4)
        self.runner_buttons = {
            "semantic": ttk.Button(
                experiment_runners, text="Semantic Gate", command=self.preview_semantic_gate
            ),
            "random": ttk.Button(
                experiment_runners, text="Random Baseline", command=self.preview_random_baseline
            ),
            "evaluate": ttk.Button(
                experiment_runners,
                text="Deterministic Eval",
                command=self.preview_deterministic_evaluation,
            ),
        }
        for button in self.runner_buttons.values():
            button.pack(side="left", padx=2, pady=2)
        upper.add(controls, weight=1)

        command_area = ttk.Frame(upper)
        ttk.Label(command_area, text="Exact Command Preview", style="Heading.TLabel").pack(anchor="w")
        self.command_text = tk.Text(command_area, height=7, wrap="word", font=("Consolas", 9))
        self.command_text.pack(fill="x", pady=4)
        deviation = ttk.Frame(command_area)
        deviation.pack(fill="x")
        ttk.Label(deviation, text="Deviation from canonical config:").pack(side="left")
        self.deviation_var = tk.StringVar(value="NOT CHECKED")
        ttk.Label(deviation, textvariable=self.deviation_var).pack(side="left", padx=5)
        metric_toolbar = ttk.Frame(command_area)
        metric_toolbar.pack(fill="x", pady=4)
        ttk.Button(metric_toolbar, text="Load TensorBoard Run...", command=self.load_metrics).pack(
            side="left"
        )
        ttk.Label(metric_toolbar, text="Measured interpretation only").pack(side="right")
        self.training_summary_var = tk.StringVar(value="No metric evidence loaded.")
        ttk.Label(
            command_area,
            textvariable=self.training_summary_var,
            wraplength=800,
            justify="left",
        ).pack(fill="x", pady=(0, 3))
        plot_grid = ttk.Frame(command_area)
        plot_grid.pack(fill="both", expand=True)
        self.plots = {
            "success": MetricPlot(plot_grid, "Success vs iteration"),
            "reward": MetricPlot(plot_grid, "Mean reward vs iteration"),
            "length": MetricPlot(plot_grid, "Episode length vs iteration"),
            "std": MetricPlot(plot_grid, "Policy std vs iteration"),
        }
        for index, plot in enumerate(self.plots.values()):
            plot.grid(row=index // 2, column=index % 2, sticky="nsew", padx=3, pady=3)
        plot_grid.rowconfigure(0, weight=1)
        plot_grid.rowconfigure(1, weight=1)
        plot_grid.columnconfigure(0, weight=1)
        plot_grid.columnconfigure(1, weight=1)
        self.interpretation_var = tk.StringVar(value="No metric evidence loaded.")
        ttk.Label(command_area, textvariable=self.interpretation_var, wraplength=800, justify="left").pack(
            fill="x", pady=3
        )
        upper.add(command_area, weight=4)

    def _build_evaluation_tab(self) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Evaluation")
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", padx=6, pady=5)
        ttk.Button(toolbar, text="Open Result A...", command=lambda: self.load_evaluation(0)).pack(
            side="left"
        )
        ttk.Button(toolbar, text="Open Result B...", command=lambda: self.load_evaluation(1)).pack(
            side="left", padx=4
        )
        self.eval_labels = [tk.StringVar(value="A: not loaded"), tk.StringVar(value="B: not loaded")]
        ttk.Label(toolbar, textvariable=self.eval_labels[0]).pack(side="left", padx=12)
        ttk.Label(toolbar, textvariable=self.eval_labels[1]).pack(side="left", padx=12)
        pane = ttk.PanedWindow(tab, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        metrics_frame = ttk.Frame(pane)
        ttk.Label(metrics_frame, text="Evidence Metrics", style="Heading.TLabel").pack(anchor="w")
        self.eval_tree = ttk.Treeview(metrics_frame, columns=("a", "b"), show="tree headings")
        self.eval_tree.heading("#0", text="Metric")
        self.eval_tree.heading("a", text="Result A")
        self.eval_tree.heading("b", text="Result B")
        self.eval_tree.pack(fill="both", expand=True)
        pane.add(metrics_frame, weight=3)
        compare_frame = ttk.Frame(pane)
        ttk.Label(compare_frame, text="Paired Transition Matrix", style="Heading.TLabel").pack(anchor="w")
        self.matrix_tree = ttk.Treeview(compare_frame, columns=("count",), show="tree headings", height=6)
        self.matrix_tree.heading("#0", text="Transition")
        self.matrix_tree.heading("count", text="Count")
        self.matrix_tree.pack(fill="x", pady=3)
        ttk.Label(compare_frame, text="Experiment-Provided Failure Taxonomy", style="Heading.TLabel").pack(
            anchor="w", pady=(8, 0)
        )
        self.taxonomy_tree = ttk.Treeview(compare_frame, columns=("a", "b"), show="tree headings")
        self.taxonomy_tree.heading("#0", text="Label")
        self.taxonomy_tree.heading("a", text="A")
        self.taxonomy_tree.heading("b", text="B")
        self.taxonomy_tree.pack(fill="both", expand=True, pady=3)
        pane.add(compare_frame, weight=2)

    def _build_console(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="LOG / COMMAND CONSOLE", style="Heading.TLabel").pack(
            anchor="w", padx=5, pady=3
        )
        self.console = tk.Text(parent, height=10, wrap="none", font=("Consolas", 9), state="disabled")
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=yscroll.set)
        self.console.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=(0, 5))
        yscroll.pack(side="right", fill="y", padx=(0, 5), pady=(0, 5))

    def _build_statusbar(self) -> None:
        status = ttk.Frame(self.root)
        status.pack(fill="x", side="bottom")
        for name, _label in (
            ("repo", "Repo"),
            ("isaac", "Isaac Lab"),
            ("task", "Task"),
            ("process", "Process"),
            ("gpu", "GPU"),
        ):
            ttk.Label(status, textvariable=self.status_vars[name], style="Status.TLabel").pack(
                side="left", fill="x", expand=name == "task"
            )
        self.status_vars["process"].set("Process: IDLE")

    def refresh_workspace(self) -> None:
        self.workspace = inspect_workspace(self.repo_root, self.isaac_lab_root)
        self.experiments = discover_experiments(self.repo_root)
        self._populate_explorer()
        self._populate_workspace()
        self._populate_runs()
        if self.experiments:
            selected = next(
                (item for item in self.experiments if str(item.path) == self.settings.selected_experiment),
                self.experiments[-1],
            )
            self.select_experiment(selected)
        self._log("state", f"Workspace refreshed: {self.repo_root}")

    def _populate_explorer(self) -> None:
        self.explorer.delete(*self.explorer.get_children())
        workspace = self.explorer.insert("", "end", iid="workspace", text="Workspace", open=True)
        self.explorer.insert(workspace, "end", text=str(self.repo_root))
        self.explorer.insert("", "end", iid="assets", text="Assets", open=True)
        tasks = self.explorer.insert("", "end", iid="tasks", text="Tasks", open=True)
        experiments = self.explorer.insert("", "end", iid="experiments", text="Experiments", open=True)
        for experiment in self.experiments:
            iid = f"experiment:{experiment.number}"
            self.explorer.insert(
                experiments, "end", iid=iid, text=f"{experiment.number:03d} {experiment.name}"
            )
            if experiment.task_id:
                self.explorer.insert(tasks, "end", iid=f"task:{experiment.number}", text=experiment.task_id)
        self.explorer.insert("", "end", iid="runs", text="Runs", open=True)

    def _populate_workspace(self) -> None:
        self.workspace_tree.delete(*self.workspace_tree.get_children())
        state = self.workspace
        rows = (
            (
                "Repository",
                "OK" if not state.tracked_dirty else "WARNING",
                state.repo_root,
                "Open Workspace...",
            ),
            (
                "Git",
                "OK" if not state.tracked_dirty else "WARNING",
                f"{state.branch} @ {state.head[:12]}",
                "Refresh",
            ),
            ("Untracked", "WARNING" if state.untracked_count else "OK", state.untracked_count, "Preserved"),
            (
                "Isaac Lab",
                "OK" if state.isaac_lab_root else "NOT FOUND",
                state.isaac_lab_root,
                "Browse..." if not state.isaac_lab_root else "",
            ),
            (
                "Isaac Lab commit",
                "OK" if state.isaac_lab_commit else "NOT CHECKED",
                state.isaac_lab_commit,
                "",
            ),
            ("Isaac Sim", "OK" if state.isaac_sim_path else "NOT FOUND", state.isaac_sim_path, ""),
            ("GPU", "OK" if state.gpu else "NOT CHECKED", state.gpu, ""),
            ("Latest run", "OK" if state.latest_run_dir else "NOT FOUND", state.latest_run_dir, ""),
        )
        for name, readiness, value, action in rows:
            self.workspace_tree.insert("", "end", values=(name, readiness, str(value or ""), action))
        self.status_vars["repo"].set(f"Repo: {'OK' if not state.tracked_dirty else 'WARNING'}")
        self.status_vars["isaac"].set(f"Isaac Lab: {'OK' if state.isaac_lab_root else 'NOT FOUND'}")
        self.status_vars["gpu"].set(f"GPU: {state.gpu or 'NOT CHECKED'}")

    def _populate_runs(self) -> None:
        self.run_tree.delete(*self.run_tree.get_children())
        latest = self.workspace.latest_run_dir
        if not latest:
            return
        checkpoints = sorted(latest.glob("model_*.pt"), key=lambda path: path.stat().st_mtime)
        checkpoint_path = checkpoints[-1] if checkpoints else None
        checkpoint = checkpoint_path.name if checkpoint_path else ""
        checkpoint_hash = sha256_file(checkpoint_path) if checkpoint_path else ""
        timestamp = datetime.fromtimestamp(latest.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        self.run_tree.insert(
            "",
            "end",
            text=latest.name,
            values=(latest.parent.name, timestamp, checkpoint, checkpoint_hash, "EXTERNAL"),
        )

    def select_experiment(self, experiment: ExperimentSummary) -> None:
        self._save_note_for_current_task()
        self.current_experiment = experiment
        self.settings.selected_experiment = str(experiment.path)
        self.settings.selected_task = experiment.task_id or ""
        self.probe_data = {}
        self.gui_reviewed_var.set(self.settings.gui_reviewed.get(experiment.task_id or "", False))
        self.status_vars["task"].set(f"Task: {experiment.task_id or 'NOT FOUND'}")
        self._populate_mdp_outline()
        self._populate_assets()
        self._update_workflow_availability()
        self._load_note_for_current_task()
        self.inspector.show(
            f"Experiment {experiment.number:03d}",
            {
                "Task ID": experiment.task_id,
                "Play Task ID": experiment.play_task_id,
                "Registration": experiment.registration_module,
                "Runtime": experiment.runtime_module,
                "Config": experiment.env_config_class,
                "PPO": experiment.ppo_config_class,
                "Path": experiment.path,
            },
            "Source: safe AST discovery",
        )

    def _populate_mdp_outline(self) -> None:
        self.mdp_tree.delete(*self.mdp_tree.get_children())
        for key in GUIDED_SECTIONS:
            label = GUIDED_SECTIONS[key] if self.mode_var.get() == "guided" else key
            self.mdp_tree.insert("", "end", iid=key, text=label)
        first = self.mdp_tree.get_children()
        if first:
            self.mdp_tree.selection_set(first[0])
            self._mdp_selected()

    def _mdp_selected(self, _event: Any = None) -> None:
        selected = self.mdp_tree.selection()
        if not selected:
            return
        section = selected[0]
        title = GUIDED_SECTIONS[section] if self.mode_var.get() == "guided" else section
        self.mdp_title.configure(text=title)
        explanation = GUIDED_EXPLANATIONS.get(section, "") if self.mode_var.get() == "guided" else ""
        self.mdp_explanation.configure(text=explanation)
        self.mdp_detail.delete(*self.mdp_detail.get_children())
        rows = self._mdp_rows(section)
        for name, value, unit, source in rows:
            self.mdp_detail.insert("", "end", text=name, values=(self._display(value), unit, source))

    def _mdp_rows(self, section: str) -> list[tuple[str, Any, str, str]]:
        if not self.probe_data:
            if section == "Goal":
                return [("Description", "설명 없음 — 성공 조건과 reward를 확인하세요.", "", "Workbench")]
            return [("Status", "Run Probe Task to load canonical runtime metadata.", "", "AST Discovery")]
        task = self.probe_data.get("task", {})
        constants = self.probe_data.get("constants", {})
        runtime = self.probe_data.get("runtime", {})
        if section == "Goal":
            observations = [
                term.get("name")
                for group in self.probe_data.get("observations", [])
                for term in group.get("terms", [])
            ]
            if "peg_pos_rel_hole" in observations and constants.get("SUCCESS_DEPTH_M") is not None:
                return [
                    (
                        "Task statement",
                        "Align the peg with the randomized hole and insert it "
                        "to the configured success depth.",
                        "",
                        "Workbench Explanation",
                    )
                ]
            return [("Description", "설명 없음 — 성공 조건과 reward를 확인하세요.", "", "Workbench")]
        if section == "Success":
            rows = []
            for term in self.probe_data.get("terminations", []):
                if term.get("name") != "success":
                    continue
                thresholds = term.get("thresholds") or {}
                if thresholds.get("xy_error_m_max") is not None:
                    rows.append(
                        ("[ ] XY Error <=", thresholds["xy_error_m_max"] * 1000, "mm", term["source"])
                    )
                if thresholds.get("insertion_depth_m_min") is not None:
                    rows.append(
                        (
                            "[ ] Insertion Depth >=",
                            thresholds["insertion_depth_m_min"] * 1000,
                            "mm",
                            term["source"],
                        )
                    )
            rows.append(("Overall", "FALSE — no live telemetry", "", "Workbench"))
            return rows
        if section == "Observation":
            rows = []
            dims = runtime.get("observation_term_dimensions", {}).get("policy", [])
            term_index = 0
            for group in self.probe_data.get("observations", []):
                for term in group.get("terms", []):
                    dimension = dims[term_index] if term_index < len(dims) else term.get("dimension")
                    if isinstance(dimension, list) and len(dimension) == 1:
                        dimension = dimension[0]
                    rows.append(
                        (term["name"], f"dim={dimension}; {term['meaning']}", term["unit"], term["source"])
                    )
                    term_index += 1
            rows.append(
                (
                    "Total",
                    runtime.get("policy_observation_shape", [None, None])[-1],
                    "values",
                    "Runtime Probe",
                )
            )
            return rows
        if section == "Action":
            rows = []
            for term in self.probe_data.get("actions", []):
                scale = term.get("scale")
                dimension = next(
                    (
                        item.get("dimension")
                        for item in runtime.get("action_terms", [])
                        if item.get("name") == term["name"]
                    ),
                    term.get("dimension"),
                )
                rows.extend(
                    (
                        (
                            term["name"],
                            f"dimension={dimension}; controller={term.get('controller_type')}",
                            "",
                            term["source"],
                        ),
                        ("Scale", scale, "m per normalized action", term["source"]),
                        ("Relative", term.get("relative"), "", term["source"]),
                        (
                            "Body / joints",
                            f"{term.get('body_name')} / {term.get('joint_names')}",
                            "",
                            term["source"],
                        ),
                    )
                )
                if isinstance(scale, int | float):
                    physical = normalized_to_physical([0.20, -0.10, -0.50], float(scale))
                    rows.append(
                        (
                            "Example [0.20,-0.10,-0.50]",
                            [value * 1000 for value in physical],
                            "mm",
                            "Workbench",
                        )
                    )
            return rows
        if section == "Reward":
            rows = []
            for term in self.probe_data.get("rewards", []):
                gate = term.get("gate")
                value = f"weight={term.get('weight')}; function={term.get('function')}"
                if gate and gate.get("threshold") is not None:
                    value += f"; gate XY <= {gate['threshold'] * 1000:.3f} mm"
                rows.append((term["name"], value, "", term["source"]))
            return rows
        if section == "Termination":
            return [
                (term["name"], f"timeout={term.get('timeout')}; {term.get('function')}", "", term["source"])
                for term in self.probe_data.get("terminations", [])
            ]
        if section == "Reset / Distribution":
            rows = []
            for term in self.probe_data.get("resets", []):
                for name, value in (term.get("ranges") or {}).items():
                    rows.append((name, value, "m", term["source"]))
            return rows
        if section == "PPO / Training":
            ppo = self.probe_data.get("ppo") or {}
            rows = [
                (key, value, "", ppo.get("source", "Task Config"))
                for key, value in ppo.items()
                if key != "source"
            ]
            rows.extend(
                (
                    ("Episode length", task.get("episode_length_s"), "s", "Task Config"),
                    ("Control dt", task.get("control_dt_s"), "s", "Task Config"),
                )
            )
            return rows
        return []

    def _populate_assets(self) -> None:
        self.asset_tree.delete(*self.asset_tree.get_children())
        self.asset_rows.clear()
        task_owner = self.current_experiment.task_id if self.current_experiment else ""
        for index, asset in enumerate(self.probe_data.get("assets", [])):
            iid = f"task_asset:{index}"
            self.asset_rows[iid] = asset
            self.asset_tree.insert(
                "",
                "end",
                iid=iid,
                text=asset.get("name", "unnamed"),
                values=(
                    asset.get("category"),
                    asset.get("source"),
                    asset.get("status"),
                    asset.get("prim_path"),
                    asset.get("role"),
                    task_owner,
                ),
            )
        for index, asset in enumerate(self.settings.asset_catalog):
            path = Path(asset.get("path", ""))
            row = {
                "name": path.name,
                "category": "external scratch asset",
                "source": str(path),
                "status": "OK" if path.is_file() else "NOT FOUND",
                "prim_path": "N/A",
                "role": "Unassigned",
                "config_class": "Local scratch catalog",
            }
            iid = f"external_asset:{index}"
            self.asset_rows[iid] = row
            self.asset_tree.insert(
                "",
                "end",
                iid=iid,
                text=path.name,
                values=(row["category"], row["source"], row["status"], "N/A", "Unassigned", "Local Settings"),
            )

    def probe_task(self) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        output = session_path("task-probe.json")
        spec = build_probe_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            output_path=output,
            device=self.device_var.get(),
        )
        self.preview_command(spec, run=True)

    def launch_gui(self) -> None:
        experiment = self._require_experiment_and_isaac(require_play=True)
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        output = session_path("gui-probe.json")
        spec = build_gui_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            output_path=output,
            seed=self.seed_var.get(),
            device=self.device_var.get(),
        )
        self.preview_command(spec, run=True)

    def preview_training(self, iterations: int) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        self.iterations_var.set(iterations)
        spec = build_train_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            num_envs=self.envs_var.get(),
            iterations=iterations,
            seed=self.seed_var.get(),
            device=self.device_var.get(),
            run_name=self.run_name_var.get().strip() or f"workbench_{iterations}_seed{self.seed_var.get()}",
            headless=self.headless_var.get(),
        )
        self.preview_command(spec)
        self._select_tab("training")
        canonical = (self.probe_data.get("ppo") or {}).get("max_iterations")
        deviations = []
        if canonical is not None and iterations != canonical:
            deviations.append(f"iterations {canonical} -> {iterations}")
        default_envs = (self.probe_data.get("task") or {}).get("default_num_envs")
        if default_envs is not None and self.envs_var.get() != default_envs:
            deviations.append(f"envs {default_envs} -> {self.envs_var.get()}")
        self.deviation_var.set(", ".join(deviations) if deviations else "NONE")

    def preview_full_training(self) -> None:
        canonical = (self.probe_data.get("ppo") or {}).get("max_iterations")
        self.preview_training(int(canonical or 1000))
        if not self.gui_reviewed_var.get():
            messagebox.showwarning(
                "GUI review not recorded",
                "The full command is available, but this local session has not been marked GUI Reviewed.",
            )

    def preview_semantic_gate(self) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        spec = build_experiment_script_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            role="semantic",
            arguments=[
                "--task",
                experiment.play_task_id or experiment.task_id or "",
                "--seed",
                str(self.seed_var.get()),
                "--output",
                str(session_path("semantic-gate.json")),
                "--device",
                self.device_var.get(),
                "--viz",
                "none",
            ],
        )
        self._preview_optional_runner(spec, "Semantic / Task Gate")

    def preview_random_baseline(self) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        spec = build_experiment_script_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            role="random",
            arguments=[
                "--task",
                experiment.task_id or "",
                "--num_envs",
                str(self.envs_var.get()),
                "--episodes",
                "128",
                "--seed",
                str(self.seed_var.get()),
                "--output",
                str(session_path("random-baseline.json")),
                "--device",
                self.device_var.get(),
                "--viz",
                "none",
            ],
        )
        self._preview_optional_runner(spec, "Random Baseline")

    def preview_deterministic_evaluation(self) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        if "evaluate" not in experiment.scripts:
            messagebox.showinfo("Runner unavailable", "This experiment exposes no evaluation runner.")
            return
        checkpoint = filedialog.askopenfilename(
            title="Select an external checkpoint",
            filetypes=(("RSL-RL checkpoint", "*.pt"), ("All files", "*.*")),
        )
        if not checkpoint:
            return
        assert self.isaac_lab_root is not None
        spec = build_experiment_script_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            experiment=experiment,
            role="evaluate",
            arguments=[
                "--mode",
                "holdout",
                "--task",
                experiment.task_id or "",
                "--checkpoint",
                checkpoint,
                "--num_envs",
                str(self.envs_var.get()),
                "--episodes",
                "256",
                "--seed",
                str(self.seed_var.get()),
                "--output",
                str(session_path("deterministic-evaluation.json")),
                "--device",
                self.device_var.get(),
                "--viz",
                "none",
            ],
        )
        self._preview_optional_runner(spec, "Deterministic Evaluation")

    def _preview_optional_runner(self, spec: CommandSpec | None, stage: str) -> None:
        if spec is None:
            messagebox.showinfo("Runner unavailable", f"{stage} is N/A for this experiment.")
            return
        self.preview_command(spec)
        self._select_tab("training")

    def preview_command(self, spec: CommandSpec, *, run: bool = False) -> None:
        self.current_spec = spec
        self.command_text.configure(state="normal")
        self.command_text.delete("1.0", "end")
        self.command_text.insert("1.0", format_spec(spec))
        self.command_text.configure(state="disabled")
        self._log("command", format_spec(spec))
        if run and messagebox.askyesno("Run exact command?", format_spec(spec)):
            self._start_spec(spec)

    def run_previewed(self) -> None:
        if not self.current_spec:
            messagebox.showinfo("No command", "Preview a command first.")
            return
        if messagebox.askyesno("Run exact command?", format_spec(self.current_spec)):
            self._start_spec(self.current_spec)

    def _start_spec(self, spec: CommandSpec) -> None:
        try:
            self.runner.start(spec)
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Process start failed", str(error))
            return
        self.running_spec = spec
        self.status_vars["process"].set("Process: RUNNING")

    def stop_process(self) -> None:
        self.runner.stop()
        self.status_vars["process"].set("Process: STOPPED")

    def copy_command(self) -> None:
        if not self.current_spec:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(format_spec(self.current_spec))

    def load_metrics(self) -> None:
        experiment = self._require_experiment_and_isaac()
        if not experiment:
            return
        assert self.isaac_lab_root is not None
        initial = str(self.workspace.latest_run_dir or self.isaac_lab_root)
        selected = filedialog.askdirectory(title="Select external RSL-RL run directory", initialdir=initial)
        if not selected:
            return
        output = session_path("tensorboard-metrics.json")
        spec = build_metrics_command(
            repo_root=self.repo_root,
            isaac_lab_root=self.isaac_lab_root,
            run_dir=Path(selected),
            output_path=output,
        )
        self.preview_command(spec, run=True)

    def _load_metric_output(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.metric_series = {
            name: MetricSeries.from_json(name, values) for name, values in payload.get("series", {}).items()
        }
        self.plots["success"].set_series(
            [self.metric_series.get("Episode_Termination/success", MetricSeries(""))]
        )
        self.plots["reward"].set_series([self.metric_series.get("Train/mean_reward", MetricSeries(""))])
        self.plots["length"].set_series(
            [self.metric_series.get("Train/mean_episode_length", MetricSeries(""))]
        )
        self.plots["std"].set_series([self.metric_series.get("Policy/mean_std", MetricSeries(""))])
        statements = measured_change(self.metric_series)
        self.interpretation_var.set(
            " ".join(statements) if statements else "No endpoint changes are available."
        )
        primary_series = self.metric_series.get("Train/mean_reward")
        last_step = (
            primary_series.points[-1][0]
            if primary_series and primary_series.points
            else max(
                (step for series in self.metric_series.values() for step, _value in series.points),
                default=None,
            )
        )
        rollout_steps = (self.probe_data.get("ppo") or {}).get("num_steps_per_env")
        transition_text = "NOT AVAILABLE"
        if last_step is not None and isinstance(rollout_steps, int):
            transition_text = f"{(last_step + 1) * self.envs_var.get() * rollout_steps:,}"
        self.training_summary_var.set(
            f"Current iteration: {last_step if last_step is not None else 'N/A'} | "
            f"Estimated transitions: {transition_text} | Raw scalar metrics: {len(self.metric_series)}"
        )

    def load_evaluation(self, index: int) -> None:
        selected = filedialog.askopenfilename(
            title=f"Open evaluation result {'A' if index == 0 else 'B'}",
            filetypes=(("JSON evidence", "*.json"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            result = normalize_evaluation(Path(selected))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror("Invalid evaluation JSON", str(error))
            return
        self.evaluations[index] = result
        self.eval_labels[index].set(f"{'A' if index == 0 else 'B'}: {result.label}")
        self.settings.recent_evidence = [
            selected,
            *[item for item in self.settings.recent_evidence if item != selected],
        ][:10]
        self._render_evaluations()

    def _render_evaluations(self) -> None:
        self.eval_tree.delete(*self.eval_tree.get_children())
        self.matrix_tree.delete(*self.matrix_tree.get_children())
        self.taxonomy_tree.delete(*self.taxonomy_tree.get_children())
        first, second = self.evaluations
        keys = ["episodes", "successes", "timeouts"]
        metric_keys = sorted(set(first.metrics if first else {}) | set(second.metrics if second else {}))
        for key in [*keys, *metric_keys]:
            a = self._evaluation_value(first, key)
            b = self._evaluation_value(second, key)
            self.eval_tree.insert("", "end", text=key, values=(self._display(a), self._display(b)))
        if first and second:
            for label, count in transition_matrix(first, second).items():
                self.matrix_tree.insert("", "end", text=label, values=(count,))
        taxonomy_labels = sorted(
            set(first.taxonomy if first else {}) | set(second.taxonomy if second else {})
        )
        for label in taxonomy_labels:
            self.taxonomy_tree.insert(
                "",
                "end",
                text=label,
                values=(
                    (first.taxonomy.get(label, 0) if first else ""),
                    (second.taxonomy.get(label, 0) if second else ""),
                ),
            )

        region_labels = sorted(set(first.regions if first else {}) | set(second.regions if second else {}))
        for label in region_labels:
            self.eval_tree.insert(
                "",
                "end",
                text=f"region:{label}",
                values=(self._region_value(first, label), self._region_value(second, label)),
            )

    def add_external_asset(self) -> None:
        selected = filedialog.askopenfilename(
            title="Catalog external asset without copying it",
            filetypes=(
                ("Robot assets", "*.usd *.usda *.usdc *.urdf *.xml *.mjcf"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in {".usd", ".usda", ".usdc", ".urdf", ".xml", ".mjcf"}:
            messagebox.showwarning(
                "Unsupported catalog type", "V0 catalogs USD, URDF, and MJCF/XML assets only."
            )
            return
        if not any(item.get("path") == str(path) for item in self.settings.asset_catalog):
            self.settings.asset_catalog.append(
                {"path": str(path), "type": path.suffix.lower(), "status": "cataloged"}
            )
            self.settings.save()
        self._populate_assets()

    def inspect_asset(self) -> None:
        selected = self.asset_tree.selection()
        if not selected:
            return
        asset = self.asset_rows.get(selected[0], {})
        self.inspector.show(
            asset.get("name", "Asset"), asset, "No asset is copied or converted by inspection."
        )

    def open_asset_location(self) -> None:
        asset = self._selected_asset()
        path = Path(str(asset.get("source", ""))) if asset else None
        if path and path.exists():
            os.startfile(path.parent if path.is_file() else path)
        else:
            messagebox.showinfo("Location unavailable", "The selected source is not a local existing path.")

    def copy_asset_path(self) -> None:
        asset = self._selected_asset()
        if not asset:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(str(asset.get("source") or asset.get("prim_path") or ""))

    def open_asset_in_isaac(self) -> None:
        asset = self._selected_asset()
        source = Path(str(asset.get("source", ""))) if asset else None
        if source and source.suffix.lower() in {".usd", ".usda", ".usdc"} and source.is_file():
            isaac_sim = self.workspace.isaac_sim_path if self.workspace else None
            launcher = isaac_sim / "isaac-sim.bat" if isaac_sim else None
            if not launcher or not launcher.is_file():
                messagebox.showerror(
                    "Isaac Sim not found", "Configure an Isaac Lab root with a resolved _isaac_sim link."
                )
                return
            spec = CommandSpec("Open USD in Isaac Sim", (str(launcher), str(source)), self.repo_root)
            self.preview_command(spec, run=True)
            return
        if source and source.suffix.lower() in {".urdf", ".xml", ".mjcf"}:
            messagebox.showinfo(
                "Explicit importer required",
                "V0 catalogs this asset but does not silently import or convert "
                "URDF/MJCF. Use an explicit Isaac importer workflow.",
            )
            return
        self.launch_gui()

    def save_local_note(self) -> None:
        self._save_note_for_current_task()
        self.settings.save()
        self._log("state", "Local experiment note saved outside the repository.")

    def export_note(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Export experiment question Markdown",
            defaultextension=".md",
            filetypes=(("Markdown", "*.md"),),
        )
        if not selected:
            return
        lines = [
            f"# {self.current_experiment.task_id if self.current_experiment else 'Experiment Question'}",
            "",
        ]
        for name, variable in self.note_vars.items():
            lines.extend((f"## {name}", "", variable.get().strip(), ""))
        Path(selected).write_text("\n".join(lines), encoding="utf-8")

    def choose_workspace(self) -> None:
        selected = filedialog.askdirectory(title="Select robotics-rnd-platform repository")
        if not selected:
            return
        path = Path(selected)
        if not (path / ".git").exists():
            messagebox.showerror("Not a Git workspace", f"No .git directory under {path}")
            return
        self.repo_root = path
        self.settings.repo_root = str(path)
        self.settings.save()
        self.refresh_workspace()

    def choose_isaac_lab(self) -> None:
        selected = filedialog.askdirectory(title="Select IsaacLab checkout")
        if not selected:
            return
        path = Path(selected)
        if not (path / "isaaclab.bat").is_file():
            messagebox.showerror(
                "Invalid Isaac Lab root", "isaaclab.bat was not found in the selected directory."
            )
            return
        self.isaac_lab_root = path
        self.settings.isaac_lab_root = str(path)
        self.settings.save()
        self.refresh_workspace()

    def _poll_process(self) -> None:
        try:
            while True:
                event = self.runner.events.get_nowait()
                self._log(event.kind, event.text, event)
                if event.kind == "exit":
                    self.status_vars["process"].set(
                        f"Process: {self.runner.status} ({self.runner.exit_code})"
                    )
                    self._handle_completed_process()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_process)

    def _handle_completed_process(self) -> None:
        spec = self.running_spec
        self.running_spec = None
        if not spec or self.runner.exit_code != 0:
            return
        if spec.label == "PPO 5 iterations":
            self.workflow_tree.set("PPO Smoke", "state", "PASS")
        elif spec.label.startswith("PPO "):
            self.workflow_tree.set("Full Training", "state", "PASS")
        elif spec.label == "Semantic":
            self.workflow_tree.set("Semantic / Task Gate", "state", "PASS")
        elif spec.label == "Random":
            self.workflow_tree.set("Random Baseline", "state", "PASS")
        elif spec.label == "Evaluate":
            self.workflow_tree.set("Deterministic Evaluation", "state", "PASS")
        if not spec.output_path or not spec.output_path.is_file():
            return
        try:
            payload = json.loads(spec.output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self._log("error", f"Could not read helper JSON: {error}")
            return
        if spec.label == "Task Probe":
            self.probe_data = payload
            self._populate_assets()
            self._mdp_selected()
            self.workflow_tree.set("Environment / Config Check", "state", "PASS")
        elif spec.label == "Read TensorBoard Metrics":
            self._load_metric_output(spec.output_path)
        elif spec.label == "Launch Task GUI":
            self._log("state", "GUI helper exited. Visual review remains a manual checkbox.")

    def _explorer_selected(self, _event: Any) -> None:
        selected = self.explorer.selection()
        if not selected:
            return
        iid = selected[0]
        if iid.startswith("experiment:") or iid.startswith("task:"):
            number = int(iid.split(":", 1)[1])
            experiment = next((item for item in self.experiments if item.number == number), None)
            if experiment:
                self.select_experiment(experiment)
        elif iid == "assets":
            self._select_tab("asset")
        elif iid == "runs":
            self._select_tab("training")
        elif iid == "workspace":
            self._select_tab("overview")

    def _mode_changed(self) -> None:
        self.settings.presentation_mode = self.mode_var.get()
        self._populate_mdp_outline()

    def _gui_review_changed(self) -> None:
        task = self.current_experiment.task_id if self.current_experiment else ""
        if task:
            self.settings.gui_reviewed[task] = self.gui_reviewed_var.get()
            self.workflow_tree.set(
                "GUI Reviewed", "state", "PASS" if self.gui_reviewed_var.get() else "NOT CHECKED"
            )

    def _update_workflow_availability(self) -> None:
        experiment = self.current_experiment
        if experiment is None:
            return
        role_by_stage = {
            "Semantic / Task Gate": "semantic",
            "Random Baseline": "random",
            "Deterministic Evaluation": "evaluate",
            "Hold-Out Evaluation": "evaluate",
        }
        for stage in WORKFLOW_STAGES:
            self.workflow_tree.set(stage, "state", "NOT CHECKED")
        for stage, role in role_by_stage.items():
            if role not in experiment.scripts:
                self.workflow_tree.set(stage, "state", "N/A")
        for role, button in self.runner_buttons.items():
            button.configure(state="normal" if role in experiment.scripts else "disabled")
        self.workflow_tree.set(
            "GUI Reviewed", "state", "PASS" if self.gui_reviewed_var.get() else "NOT CHECKED"
        )

    def _save_note_for_current_task(self) -> None:
        task = self.current_experiment.task_id if self.current_experiment else ""
        if task and hasattr(self, "note_vars"):
            self.settings.experiment_notes[task] = {
                name: variable.get() for name, variable in self.note_vars.items()
            }

    def _load_note_for_current_task(self) -> None:
        task = (self.current_experiment.task_id if self.current_experiment else "") or ""
        note = self.settings.experiment_notes.get(task, {})
        for name, variable in self.note_vars.items():
            variable.set(note.get(name, ""))

    def _selected_asset(self) -> dict[str, Any] | None:
        selected = self.asset_tree.selection()
        return self.asset_rows.get(selected[0]) if selected else None

    def _require_experiment_and_isaac(self, *, require_play: bool = False) -> ExperimentSummary | None:
        experiment = self.current_experiment
        if not experiment or not experiment.task_id:
            messagebox.showerror("Task unavailable", "Select a discovered task first.")
            return None
        if require_play and not experiment.play_task_id:
            messagebox.showerror(
                "GUI task unavailable", "The selected experiment does not expose PLAY_TASK_ID."
            )
            return None
        if not self.isaac_lab_root or not (self.isaac_lab_root / "isaaclab.bat").is_file():
            messagebox.showerror(
                "Isaac Lab unavailable",
                "Configure an existing Isaac Lab checkout. No installation is performed.",
            )
            return None
        return experiment

    def _select_tab(self, name: str) -> None:
        indexes = {"overview": 0, "asset": 1, "task": 2, "training": 3, "evaluation": 4}
        self.notebook.select(indexes[name])

    def _log(self, kind: str, text: str, event: ProcessEvent | None = None) -> None:
        timestamp = event.timestamp if event else None
        prefix = timestamp.astimezone().strftime("%H:%M:%S") if timestamp else "--:--:--"
        self.console.configure(state="normal")
        self.console.insert("end", f"[{prefix}] [{kind.upper()}] {text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    @staticmethod
    def _evaluation_value(result: EvaluationResult | None, key: str) -> Any:
        if not result:
            return ""
        if key in {"episodes", "successes", "timeouts"}:
            return getattr(result, key)
        return result.metrics.get(key)

    @staticmethod
    def _region_value(result: EvaluationResult | None, label: str) -> str:
        if not result or label not in result.regions:
            return ""
        value = result.regions[label]
        if isinstance(value, dict):
            successes = value.get("successes")
            episodes = value.get("episodes")
            if successes is not None and episodes is not None:
                return f"{successes}/{episodes}"
        return str(value)

    @staticmethod
    def _display(value: Any) -> str:
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.8g}"
        return str(value)

    def close(self) -> None:
        if self.runner.status == "RUNNING":
            if not messagebox.askyesno(
                "Stop tracked process?", "Stop only the process tree launched by this workbench?"
            ):
                return
            self.runner.stop()
        self._save_note_for_current_task()
        self.settings.repo_root = str(self.repo_root)
        self.settings.isaac_lab_root = str(self.isaac_lab_root or "")
        self.settings.window_geometry = self.root.geometry()
        self.settings.presentation_mode = self.mode_var.get()
        self.settings.save()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    RobotLearningWorkbench(root)
    root.mainloop()
    return 0
