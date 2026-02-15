#!/usr/bin/env python3
"""
@file gui.py
@brief Stock Trader PyQt5 GUI - Configuration and pipeline control.
@details Business-professional dark theme; same config data handling as prior GUI.
"""

import os
import sys
import yaml
import queue
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QStatusBar, QScrollArea, QLineEdit,
    QTextEdit, QCheckBox, QSpinBox, QMessageBox, QFileDialog, QSplitter,
    QListWidget, QStackedWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont


# ---------------------------------------------------------------------------
# Trading theme (dark, business-professional)
# ---------------------------------------------------------------------------

class TradingTheme:
    """Dark theme for trading-style UI (high contrast, green/red semantics)."""
    BG_DARK = "#1a1d23"
    BG_MEDIUM = "#252a33"
    BG_LIGHT = "#2d333b"
    TEXT = "#e6edf3"
    TEXT_DIM = "#8b949e"
    ACCENT = "#3fb950"   # green
    ACCENT_HOVER = "#56d364"
    DANGER = "#f85149"
    WARNING = "#d29922"
    BORDER = "#30363d"

    @staticmethod
    def stylesheet() -> str:
        return f"""
        QMainWindow, QWidget {{ background-color: {TradingTheme.BG_DARK}; color: {TradingTheme.TEXT}; }}
        QGroupBox {{
            background-color: {TradingTheme.BG_MEDIUM};
            border: 1px solid {TradingTheme.BORDER};
            border-radius: 6px;
            margin-top: 10px;
            padding: 10px 10px 10px 10px;
            font-weight: bold;
            color: {TradingTheme.TEXT};
        }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 6px; }}
        QPushButton {{
            background-color: {TradingTheme.BG_LIGHT};
            color: {TradingTheme.TEXT};
            border: 1px solid {TradingTheme.BORDER};
            border-radius: 4px;
            padding: 6px 14px;
            min-height: 24px;
        }}
        QPushButton:hover {{ border-color: {TradingTheme.ACCENT}; color: {TradingTheme.ACCENT}; }}
        QPushButton:pressed {{ background-color: {TradingTheme.ACCENT}; color: {TradingTheme.BG_DARK}; }}
        QPushButton:disabled {{ color: {TradingTheme.TEXT_DIM}; }}
        QPushButton[class="success"] {{ border-color: {TradingTheme.ACCENT}; color: {TradingTheme.ACCENT}; }}
        QPushButton[class="danger"] {{ border-color: {TradingTheme.DANGER}; color: {TradingTheme.DANGER}; }}
        QLineEdit, QSpinBox {{
            background-color: {TradingTheme.BG_LIGHT};
            color: {TradingTheme.TEXT};
            border: 1px solid {TradingTheme.BORDER};
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 22px;
        }}
        QLineEdit:focus, QSpinBox:focus {{ border-color: {TradingTheme.ACCENT}; }}
        QCheckBox {{ color: {TradingTheme.TEXT}; spacing: 8px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {TradingTheme.BORDER}; border-radius: 3px; background: {TradingTheme.BG_LIGHT}; }}
        QCheckBox::indicator:checked {{ background: {TradingTheme.ACCENT}; border-color: {TradingTheme.ACCENT}; }}
        QTextEdit {{ background-color: #0d1117; color: #c9d1d9; border: 1px solid {TradingTheme.BORDER}; font-family: Consolas; }}
        QScrollArea {{ border: none; background: transparent; }}
        QListWidget {{
            background-color: {TradingTheme.BG_MEDIUM};
            color: {TradingTheme.TEXT};
            border: none;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{ padding: 10px 12px; border-radius: 4px; border: none; outline: none; }}
        QListWidget::item:selected {{ background-color: {TradingTheme.ACCENT}; color: {TradingTheme.BG_DARK}; border: none; outline: none; }}
        QListWidget::item:selected:focus {{ border: none; outline: none; }}
        QListWidget::item:hover:!selected {{ background-color: {TradingTheme.BG_LIGHT}; }}
        QStatusBar {{ background-color: {TradingTheme.BG_MEDIUM}; color: {TradingTheme.TEXT_DIM}; border-top: 1px solid {TradingTheme.BORDER}; }}
        QLabel {{ color: {TradingTheme.TEXT}; }}
        """


# ---------------------------------------------------------------------------
# Pipeline runner thread (emits lines to main thread)
# ---------------------------------------------------------------------------

class PipelineRunner(QThread):
    line_ready = pyqtSignal(str)

    def __init__(self, cwd: str, cmd: List[str], parent=None):
        super().__init__(parent)
        self.cwd = cwd
        self.cmd = cmd
        self._process = None

    def run(self):
        try:
            self._process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
                cwd=self.cwd,
            )
            for line in iter(self._process.stdout.readline, ""):
                if line:
                    self.line_ready.emit(line)
            self._process.wait()
            if self._process.returncode == 0:
                self.line_ready.emit("\n[OK] Completed successfully.\n")
            else:
                self.line_ready.emit(f"\n[Exit code {self._process.returncode}]\n")
        except Exception as e:
            self.line_ready.emit(f"\n[Error] {e}\n")

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class StockTraderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Trader - Configuration & Control")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self.settings_path = self._get_settings_path()
        self.settings = self._load_settings()
        self.project_root = self._get_project_root()
        if not self.project_root:
            QMessageBox.critical(
                self,
                "Error",
                "Stock Trader folder not selected. Application will exit.",
            )
            sys.exit(1)
        if not self._validate_project_structure(self.project_root):
            if QMessageBox.question(
                self,
                "Warning",
                "The selected folder doesn't appear to be a Stock Trader directory.\n"
                "Create config, data, logs, src, utils?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            ) != QMessageBox.Yes:
                sys.exit(1)
            self._create_project_structure(self.project_root)

        self.config_path = os.path.join(self.project_root, "config", "config.yaml")
        self.config = {}
        self._config_widgets: List[Tuple[str, Any, Callable, Callable]] = []  # key, widget, getter, setter
        self.output_queue = queue.Queue()
        self.pipeline_process = None
        self.pipeline_runner: Optional[PipelineRunner] = None
        self.backtest_days_widget: Optional[QLineEdit] = None
        self.util_output: Optional[QTextEdit] = None

        self._build_ui()
        self.load_config()
        self._start_queue_poll()

    def _get_settings_path(self) -> str:
        if getattr(sys, "frozen", False):
            if sys.platform == "win32":
                base = os.environ.get("APPDATA", os.path.expanduser("~"))
            else:
                base = os.path.expanduser("~/.stocktrader")
            path = os.path.join(base, "StockTrader")
            os.makedirs(path, exist_ok=True)
            return os.path.join(path, "settings.yaml")
        return ".gui_settings.yaml"

    def _load_settings(self) -> dict:
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r") as f:
                    return yaml.safe_load(f) or {}
        except Exception:
            pass
        return {}

    def _save_settings(self):
        try:
            d = os.path.dirname(self.settings_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.settings_path, "w") as f:
                yaml.dump(self.settings, f, default_flow_style=False)
        except Exception:
            pass

    def _get_project_root(self) -> Optional[str]:
        root = self.settings.get("project_root")
        if root and os.path.isdir(root):
            return root
        if not getattr(sys, "frozen", False):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if self._validate_project_structure(script_dir):
                self.settings["project_root"] = script_dir
                self._save_settings()
                return script_dir
        QMessageBox.information(
            self,
            "Select Stock Trader Folder",
            "Please select your Stock-Trader folder (containing config/, src/, etc.).",
        )
        folder = QFileDialog.getExistingDirectory(self, "Select Stock-Trader Folder", "", QFileDialog.ShowDirsOnly)
        if folder:
            self.settings["project_root"] = folder
            self._save_settings()
            return folder
        return None

    def _validate_project_structure(self, folder: str) -> bool:
        for name in ["config", "src"]:
            if not os.path.exists(os.path.join(folder, name)):
                return False
        return True

    def _create_project_structure(self, folder: str):
        for name in ["config", "data", "logs", "reports", "src", "utils"]:
            os.makedirs(os.path.join(folder, name), exist_ok=True)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        self.nav_list = self._create_nav()
        content = self._create_content()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 900])
        main_layout.addWidget(splitter)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_bar = status
        status.showMessage("Ready")

        # Bottom action bar (Save / Reload / Exit)
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(10, 6, 10, 6)
        btn_save = QPushButton("Save Configuration")
        btn_save.setProperty("class", "success")
        btn_save.clicked.connect(self.save_config)
        btn_reload = QPushButton("Reload Configuration")
        btn_reload.clicked.connect(self.load_config)
        btn_exit = QPushButton("Exit")
        btn_exit.setProperty("class", "danger")
        btn_exit.clicked.connect(self.close)
        action_layout.addWidget(btn_save)
        action_layout.addWidget(btn_reload)
        action_layout.addStretch()
        action_layout.addWidget(btn_exit)
        main_layout.addWidget(action_bar)

        self.nav_list.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def _create_nav(self) -> QListWidget:
        nav = QListWidget()
        nav.setMinimumWidth(200)
        nav.setMaximumWidth(280)
        for label in [
            "API Keys",
            "Data Collection",
            "Paper Trading",
            "Backtesting",
            "Signal Thresholds",
            "Email",
            "Utilities",
            "Run Pipeline",
        ]:
            nav.addItem(label)
        return nav

    def _create_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._page_api_keys())
        self.pages.addWidget(self._page_data_collection())
        self.pages.addWidget(self._page_paper_trading())
        self.pages.addWidget(self._page_backtesting())
        self.pages.addWidget(self._page_thresholds())
        self.pages.addWidget(self._page_email())
        self.pages.addWidget(self._page_utilities())
        self.pages.addWidget(self._page_pipeline())
        layout.addWidget(self.pages)
        return content

    def _add_str(self, parent: QWidget, layout: QVBoxLayout, key: str, label: str, placeholder: str = "", tooltip: str = "", password: bool = False) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        w = QLineEdit()
        if password:
            w.setEchoMode(QLineEdit.Password)
        w.setPlaceholderText(placeholder)
        if tooltip:
            w.setToolTip(tooltip)
        w.setMinimumWidth(280)
        row.addWidget(w)
        layout.addLayout(row)
        if key == "email.recipients":
            self._config_widgets.append((key, w, lambda w: [x.strip() for x in w.text().split(",") if x.strip()], lambda w, v: w.setText(",".join(v) if isinstance(v, list) and v else str(v or ""))))
        else:
            self._config_widgets.append((key, w, lambda w: w.text(), lambda w, v: w.setText(str(v) if v is not None else "")))
        return w

    def _add_int(self, parent: QWidget, layout: QVBoxLayout, key: str, label: str, low: int, high: int, tooltip: str = "") -> QSpinBox:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        w = QSpinBox()
        w.setRange(low, high)
        if tooltip:
            w.setToolTip(tooltip)
        row.addWidget(w)
        layout.addLayout(row)
        self._config_widgets.append((key, w, lambda w: w.value(), lambda w, v: w.setValue(int(v) if v is not None else 0)))
        return w

    def _add_bool(self, parent: QWidget, layout: QVBoxLayout, key: str, label: str, tooltip: str = "") -> QCheckBox:
        w = QCheckBox(label)
        if tooltip:
            w.setToolTip(tooltip)
        layout.addWidget(w)
        self._config_widgets.append((key, w, lambda w: w.isChecked(), lambda w, v: w.setChecked(bool(v))))
        return w

    def _section(self, layout: QVBoxLayout, title: str) -> None:
        lab = QLabel(title)
        lab.setStyleSheet(f"font-weight: bold; color: {TradingTheme.ACCENT}; margin-top: 8px;")
        layout.addWidget(lab)

    def _page_api_keys(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(QLabel("API Keys (FREE tiers)"))
        self._add_str(inner, layout, "api_keys.finnhub", "Finnhub API Key (REQUIRED)", tooltip="https://finnhub.io/register")
        self._add_str(inner, layout, "api_keys.alphavantage", "Alpha Vantage API Key", tooltip="https://www.alphavantage.co/support/#api-key")
        self._add_str(inner, layout, "api_keys.fred", "FRED API Key", tooltip="https://fred.stlouisfed.org/docs/api/api_key.html")
        btn = QPushButton("API Setup Guide")
        btn.clicked.connect(self._show_api_guide)
        layout.addWidget(btn)
        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(scroll)
        return page

    def _page_data_collection(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        g1 = QGroupBox("Alpha Vantage")
        l1 = QVBoxLayout(g1)
        self._add_bool(inner, l1, "collection.alphavantage.enabled", "Enabled", "News sentiment, 100 calls/day")
        self._add_int(inner, l1, "collection.alphavantage.top_n", "Top N Tickers", 1, 100)
        self._add_int(inner, l1, "collection.alphavantage.articles_per_ticker", "Articles per Ticker", 1, 100)
        layout.addWidget(g1)
        g2 = QGroupBox("Yahoo Finance")
        l2 = QVBoxLayout(g2)
        self._add_bool(inner, l2, "collection.yfinance.enabled", "Enabled")
        self._add_bool(inner, l2, "collection.yfinance.collect_fundamentals", "Collect Fundamentals")
        self._add_bool(inner, l2, "collection.yfinance.collect_analyst_ratings", "Collect Analyst Ratings")
        layout.addWidget(g2)
        g3 = QGroupBox("VADER Sentiment")
        l3 = QVBoxLayout(g3)
        self._add_bool(inner, l3, "collection.vader_sentiment.enabled", "Enabled")
        self._add_bool(inner, l3, "collection.vader_sentiment.scrape_headlines", "Scrape Headlines")
        layout.addWidget(g3)
        g4 = QGroupBox("Technical Analysis")
        l4 = QVBoxLayout(g4)
        self._add_bool(inner, l4, "collection.technical_analysis.enabled", "Enabled")
        self._add_int(inner, l4, "collection.technical_analysis.lookback_days", "Lookback Days", 10, 200)
        layout.addWidget(g4)
        g5 = QGroupBox("FRED Macro")
        l5 = QVBoxLayout(g5)
        self._add_bool(inner, l5, "collection.fred.enabled", "Enabled")
        self._add_bool(inner, l5, "collection.fred.collect_vix", "Collect VIX")
        self._add_bool(inner, l5, "collection.fred.collect_rates", "Collect Rates")
        self._add_bool(inner, l5, "collection.fred.collect_unemployment", "Collect Unemployment")
        self._add_bool(inner, l5, "collection.fred.collect_inflation", "Collect Inflation")
        self._add_bool(inner, l5, "collection.fred.collect_forex", "Collect Forex")
        layout.addWidget(g5)
        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(scroll)
        return page

    def _page_paper_trading(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        self._add_bool(inner, layout, "paper_trading.enabled", "Enable Paper Trading")
        self._add_int(inner, layout, "paper_trading.min_conviction", "Minimum Conviction", 0, 100)
        self._add_int(inner, layout, "paper_trading.position_size", "Position Size ($)", 100, 10000)
        self._add_int(inner, layout, "paper_trading.max_open_positions", "Max Open Positions", 1, 50)
        g = QGroupBox("Exit Strategy")
        lg = QVBoxLayout(g)
        self._add_int(inner, lg, "paper_trading.hold_days", "Hold Days", 1, 365)
        self._add_int(inner, lg, "paper_trading.stop_loss_pct", "Stop Loss %", -50, 0)
        self._add_int(inner, lg, "paper_trading.take_profit_pct", "Take Profit %", 0, 200)
        layout.addWidget(g)
        self._add_bool(inner, layout, "paper_trading.report_in_dashboard", "Report in Dashboard")
        self._add_int(inner, layout, "paper_trading.backfill_days", "Backfill Days", 0, 365)
        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(scroll)
        return page

    def _page_backtesting(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        self._add_int(inner, layout, "backtesting.initial_capital", "Initial Capital ($)", 1000, 100000)
        self._add_int(inner, layout, "backtesting.position_size", "Position Size ($)", 100, 10000)
        self._add_int(inner, layout, "backtesting.max_positions", "Max Positions", 1, 50)
        self._add_bool(inner, layout, "backtesting.conviction_weighted", "Conviction Weighted Sizing")
        g = QGroupBox("Exit Strategy")
        lg = QVBoxLayout(g)
        self._add_int(inner, lg, "backtesting.hold_days", "Hold Days", 1, 365)
        self._add_int(inner, lg, "backtesting.stop_loss_pct", "Stop Loss %", -50, 0)
        self._add_int(inner, lg, "backtesting.take_profit_pct", "Take Profit %", 0, 200)
        self._add_int(inner, lg, "backtesting.min_conviction", "Min Conviction", 0, 100)
        layout.addWidget(g)
        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(scroll)
        return page

    def _page_thresholds(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        g1 = QGroupBox("Velocity Spike")
        l1 = QVBoxLayout(g1)
        self._add_int(inner, l1, "thresholds.velocity_spike.mention_vel_24h_min", "Mention Velocity 24h Min (%)", 0, 1000)
        self._add_int(inner, l1, "thresholds.velocity_spike.composite_score_min", "Composite Score Min", 0, 100)
        layout.addWidget(g1)
        g2 = QGroupBox("Insider Cluster")
        l2 = QVBoxLayout(g2)
        self._add_int(inner, l2, "thresholds.insider_cluster.min_insiders", "Min Insiders", 1, 10)
        self._add_int(inner, l2, "thresholds.insider_cluster.lookback_days", "Lookback Days", 1, 90)
        self._add_int(inner, l2, "thresholds.insider_cluster.min_value_total", "Min Value Total ($)", 1000, 10000000)
        layout.addWidget(g2)
        self._add_int(inner, layout, "thresholds.minimum_conviction", "Minimum Conviction to Report", 0, 100)
        layout.addStretch()
        scroll.setWidget(inner)
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(scroll)
        return page

    def _page_email(self) -> QWidget:
        page = QWidget()
        inner = QWidget()
        layout = QVBoxLayout(inner)
        self._add_bool(inner, layout, "email.enabled", "Enable Email Reports")
        self._add_str(inner, layout, "email.smtp_server", "SMTP Server", "smtp.gmail.com")
        self._add_int(inner, layout, "email.smtp_port", "SMTP Port", 1, 65535)
        self._add_str(inner, layout, "email.sender", "Sender Email", "your-email@gmail.com")
        self._add_str(inner, layout, "email.password", "Password (App Password)", "", password=True)
        self._add_str(inner, layout, "email.recipients", "Recipients (comma-separated)", "email1@gmail.com,email2@gmail.com")
        layout.addStretch()
        page_layout = QVBoxLayout(page)
        page_layout.addWidget(inner)
        return page

    def _page_utilities(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Development Utilities"))
        g1 = QGroupBox("Type Checker")
        l1 = QVBoxLayout(g1)
        l1.addWidget(QLabel("AST-based type checker"))
        btn1 = QPushButton("Run Type Checker")
        btn1.clicked.connect(lambda: self._run_utility("utils/type_check.py", "Type Checker"))
        l1.addWidget(btn1)
        layout.addWidget(g1)
        g2 = QGroupBox("Bug Fix Verifier")
        l2 = QVBoxLayout(g2)
        l2.addWidget(QLabel("Verify bug fixes present"))
        btn2 = QPushButton("Verify Bug Fixes")
        btn2.clicked.connect(lambda: self._run_utility("utils/verify_version.py", "Bug Fix Verifier"))
        l2.addWidget(btn2)
        layout.addWidget(g2)
        g3 = QGroupBox("Backtesting")
        l3 = QVBoxLayout(g3)
        row = QHBoxLayout()
        row.addWidget(QLabel("Lookback days:"))
        self.backtest_days_widget = QLineEdit()
        self.backtest_days_widget.setText("90")
        self.backtest_days_widget.setMaximumWidth(80)
        row.addWidget(self.backtest_days_widget)
        l3.addLayout(row)
        btn3 = QPushButton("Run Backtest")
        btn3.clicked.connect(self._run_backtest)
        l3.addWidget(btn3)
        layout.addWidget(g3)
        g4 = QGroupBox("Runtime Validation")
        l4 = QVBoxLayout(g4)
        btn4 = QPushButton("Run Runtime Tests")
        btn4.clicked.connect(lambda: self._run_utility("utils/test_runtime.py", "Runtime Validator"))
        l4.addWidget(btn4)
        layout.addWidget(g4)
        g5 = QGroupBox("Output")
        l5 = QVBoxLayout(g5)
        self.util_output = QTextEdit()
        self.util_output.setReadOnly(True)
        self.util_output.setMinimumHeight(200)
        l5.addWidget(self.util_output)
        layout.addWidget(g5)
        return page

    def _page_pipeline(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.run_btn = QPushButton("Run Main Pipeline")
        self.run_btn.setProperty("class", "success")
        self.run_btn.clicked.connect(self._run_pipeline)
        self.stop_btn = QPushButton("Stop Pipeline")
        self.stop_btn.setProperty("class", "danger")
        self.stop_btn.clicked.connect(self._stop_pipeline)
        self.stop_btn.setEnabled(False)
        row.addWidget(self.run_btn)
        row.addWidget(self.stop_btn)
        btn_backtest = QPushButton("Run Backtest")
        btn_backtest.clicked.connect(self._run_backtest_from_pipeline)
        row.addWidget(btn_backtest)
        btn_clear = QPushButton("Clear Output")
        btn_clear.clicked.connect(self._clear_console)
        row.addWidget(btn_clear)
        layout.addLayout(row)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(300)
        layout.addWidget(self.console)
        return page

    def get_nested_value(self, config: dict, key_path: str) -> Any:
        keys = key_path.split(".")
        v = config
        for k in keys:
            if isinstance(v, dict) and k in v:
                v = v[k]
            else:
                return None
        return v

    def set_nested_value(self, config: dict, key_path: str, value: Any) -> None:
        keys = key_path.split(".")
        cur = config
        for k in keys[:-1]:
            if k not in cur:
                cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value

    def load_config(self) -> None:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    self.config = yaml.safe_load(f) or {}
                for key, widget, getter, setter in self._config_widgets:
                    v = self.get_nested_value(self.config, key)
                    if v is not None:
                        setter(widget, v)
                self.status_bar.showMessage("Configuration loaded")
            else:
                self.status_bar.showMessage("No config file; using defaults")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            self.status_bar.showMessage("Load failed")

    def save_config(self) -> None:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            for section, default in (
                ("api_keys", {}),
                ("database", {"path": "data/sentiment.db"}),
                ("collection", {}),
                ("paper_trading", {}),
                ("backtesting", {}),
                ("thresholds", {}),
                ("email", {}),
                ("report", {"max_signals": 10, "include_charts": False, "watchlist_size": 20}),
            ):
                if section not in config or not isinstance(config.get(section), dict):
                    config[section] = default.copy() if isinstance(default, dict) else default
            for key, widget, getter, setter in self._config_widgets:
                val = getter(widget)
                if key == "email.recipients" and isinstance(val, list):
                    pass
                elif isinstance(val, str) and ("YOUR_" in val or not val.strip()) and "password" not in key.lower():
                    continue
                self.set_nested_value(config, key, val)
            Path(os.path.join(self.project_root, "config")).mkdir(exist_ok=True)
            with open(self.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
            self.status_bar.showMessage("Configuration saved")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _start_queue_poll(self) -> None:
        try:
            while True:
                msg = self.output_queue.get_nowait()
                self._log_console(msg)
        except queue.Empty:
            pass
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._start_queue_poll)

    def _log_console(self, text: str) -> None:
        self.console.moveCursor(self.console.textCursor().End)
        self.console.insertPlainText(text)
        self.console.moveCursor(self.console.textCursor().End)

    def _clear_console(self) -> None:
        self.console.clear()

    def _run_pipeline(self) -> None:
        if self.pipeline_runner and self.pipeline_runner.isRunning():
            QMessageBox.warning(self, "Busy", "Pipeline is already running.")
            return
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._clear_console()
        self._log_console("Starting main pipeline...\n\n")
        self.pipeline_runner = PipelineRunner(
            self.project_root,
            [sys.executable, os.path.join(self.project_root, "main.py"), "--project-root", self.project_root],
            self,
        )
        self.pipeline_runner.line_ready.connect(self._log_console)
        self.pipeline_runner.finished.connect(self._pipeline_finished)
        self.pipeline_runner.start()

    def _pipeline_finished(self) -> None:
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _stop_pipeline(self) -> None:
        if self.pipeline_runner and self.pipeline_runner.isRunning():
            self.pipeline_runner.stop()
            self._log_console("\n[Stopped by user]\n")
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _run_backtest_from_pipeline(self) -> None:
        self._clear_console()
        self._log_console("Running backtest...\n\n")
        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, os.path.join(self.project_root, "utils", "backtest.py")],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", cwd=self.project_root,
                )
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        self.output_queue.put(line)
                proc.wait()
            except Exception as e:
                self.output_queue.put(f"\nError: {e}\n")
        threading.Thread(target=run, daemon=True).start()

    def _run_utility(self, script_path: str, name: str) -> None:
        if self.util_output is None:
            return
        self.util_output.clear()
        full = os.path.join(self.project_root, script_path)
        if not os.path.exists(full):
            self.util_output.setPlainText(f"Script not found: {full}")
            return
        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, full],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", cwd=self.project_root,
                )
                out = []
                for line in iter(proc.stdout.readline, ""):
                    out.append(line)
                self.util_output.setPlainText("".join(out))
            except Exception as e:
                self.util_output.setPlainText(f"Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _run_backtest(self) -> None:
        try:
            days = int(self.backtest_days_widget.text() or "90")
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Days must be a number.")
            return
        if self.util_output is None:
            return
        self.util_output.clear()
        out_lines = []
        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, os.path.join(self.project_root, "utils", "backtest.py"), "--days", str(days)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", cwd=self.project_root,
                )
                for line in iter(proc.stdout.readline, ""):
                    out_lines.append(line)
            except Exception as e:
                out_lines.append(f"Error: {e}\n")
        def finish():
            self.util_output.setPlainText("".join(out_lines))
        t = threading.Thread(target=run, daemon=True)
        t.start()
        from PyQt5.QtCore import QTimer
        def poll():
            if t.is_alive():
                QTimer.singleShot(200, poll)
            else:
                finish()
        QTimer.singleShot(300, poll)

    def _show_api_guide(self) -> None:
        text = (
            "API SETUP (all FREE)\n\n"
            "1. Finnhub (required): https://finnhub.io/register\n"
            "2. Alpha Vantage: https://www.alphavantage.co/support/#api-key\n"
            "3. FRED: https://fred.stlouisfed.org/docs/api/api_key.html\n\n"
            "Paste keys in API Keys tab and click Save Configuration."
        )
        QMessageBox.information(self, "API Setup Guide", text)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(TradingTheme.stylesheet())
    w = StockTraderGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
