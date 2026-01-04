#!/usr/bin/env python3
"""
Stock Trader GUI - Modern interface for configuration and pipeline execution
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import yaml
import subprocess
import threading
import queue
import os
import sys
from pathlib import Path


class StockTraderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Trader - Configuration & Control Panel")
        self.root.geometry("1200x1200")

        # GUI settings file path (for project root location)
        self.settings_path = self._get_settings_path()
        self.settings = {}

        # Load GUI settings
        self.load_settings()

        # Get or prompt for project root folder
        self.project_root = self.get_project_root()
        if not self.project_root:
            messagebox.showerror(
                "Error",
                "Stock Trader folder not selected. Application will exit."
            )
            sys.exit(1)

        # Validate project root structure
        if not self.validate_project_structure(self.project_root):
            if not messagebox.askyesno(
                "Warning",
                "The selected folder doesn't appear to be a Stock Trader directory.\n"
                "Some folders (config, data, logs, src) are missing.\n\n"
                "Do you want to create them automatically?"
            ):
                sys.exit(1)
            self.create_project_structure(self.project_root)

        # Config file path (relative to project root)
        self.config_path = os.path.join(self.project_root, "config", "config.yaml")
        self.config = {}

        # Queue for pipeline output
        self.output_queue = queue.Queue()
        self.pipeline_process = None

        # Queue for utilities output
        self.util_output_queue = queue.Queue()

        # Create main container
        self.create_widgets()

        # Load existing config
        self.load_config()

        # Start output queue checkers
        self.check_output_queue()
        self.check_util_output_queue()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Create notebook (tabbed interface)
        self.notebook = ttkb.Notebook(self.root, bootstyle="dark")
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Create tabs
        self.create_api_keys_tab()
        self.create_collection_tab()
        self.create_paper_trading_tab()
        self.create_backtesting_tab()
        self.create_thresholds_tab()
        self.create_email_tab()
        self.create_utilities_tab()
        self.create_pipeline_tab()

        # Bottom buttons
        button_frame = ttkb.Frame(self.root)
        button_frame.pack(fill=X, padx=10, pady=10)

        ttkb.Button(
            button_frame,
            text="💾 Save Configuration",
            command=self.save_config,
            bootstyle="success"
        ).pack(side=LEFT, padx=5)

        ttkb.Button(
            button_frame,
            text="🔄 Reload Configuration",
            command=self.load_config,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        ttkb.Button(
            button_frame,
            text="❌ Exit",
            command=self.root.quit,
            bootstyle="danger"
        ).pack(side=RIGHT, padx=5)

    def create_api_keys_tab(self):
        """API Keys configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="🔑 API Keys")

        # Help button at the top
        help_frame = ttkb.Frame(tab)
        help_frame.pack(fill=X, padx=10, pady=10)

        ttkb.Button(
            help_frame,
            text="📖 API Setup Guide",
            command=self.show_api_setup_guide,
            bootstyle="info-outline",
            width=20
        ).pack(side=LEFT, padx=5)

        ttkb.Label(
            help_frame,
            text="Click for detailed instructions on getting your FREE API keys",
            font=("Helvetica", 9, "italic")
        ).pack(side=LEFT, padx=10)

        # Scrollable frame
        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollbar = ttkb.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # API Keys section
        self.api_vars = {}

        # Finnhub (Required)
        self.create_labeled_entry(
            scrollable_frame, "Finnhub API Key (REQUIRED)", "api_keys.finnhub",
            "https://finnhub.io/register - FREE tier: 60 calls/min", row=0
        )

        # Alpha Vantage
        self.create_labeled_entry(
            scrollable_frame, "Alpha Vantage API Key", "api_keys.alphavantage",
            "https://www.alphavantage.co/support/#api-key - FREE: 100 calls/day", row=1
        )

        # FMP
        self.create_labeled_entry(
            scrollable_frame, "Financial Modeling Prep Key", "api_keys.fmp",
            "https://site.financialmodelingprep.com - FREE: 250 calls/day", row=2
        )

        # FRED
        self.create_labeled_entry(
            scrollable_frame, "FRED API Key", "api_keys.fred",
            "https://fred.stlouisfed.org/docs/api/api_key.html - FREE", row=3
        )

