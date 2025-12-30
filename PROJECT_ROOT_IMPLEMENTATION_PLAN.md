# Project Root Implementation Plan

## Problem
Exe builds break because file paths are hardcoded relative to the script location. When packaged as exe, the working directory changes and paths like `config/config.yaml`, `data/sentiment.db`, etc. can't be found.

## Solution
Prompt for the Stock-Trader project root folder on startup and make all file/folder operations relative to this root.

---

## Files to Modify

### 1. gui.py
**Changes needed:**

#### A. __init__ method (lines 19-50)
- Add `self.settings_path = self._get_settings_path()` (use AppData for exe, local for dev)
- Add `self.project_root = self.get_project_root()` (prompts if not set)
- Validate project structure with `validate_project_structure()`
- Update `self.config_path` to use `os.path.join(self.project_root, "config", "config.yaml")`

#### B. Remove utils folder functionality
- **Delete:** Lines 519-526 (utils folder button in title_frame)
- **Delete:** Lines 529-535 (utils path label)
- **Delete:** Lines 997-1030 (get_utils_folder() and set_utils_folder() methods)
- **Delete:** "utils_folder" from settings usage

#### C. Add new helper methods
- `_get_settings_path()` - Returns AppData path for exe, local for dev
- `get_project_root()` - Gets from settings or prompts user
- `validate_project_structure(folder)` - Checks for config/, src/ folders
- `create_project_structure(folder)` - Creates missing folders

#### D. Update file paths to use project_root
- Line 967: `Path(os.path.join(self.project_root, "config")).mkdir(exist_ok=True)`
- Line 636: Use `os.path.join(self.project_root, "utils", script_filename)`
- Line 706: Use `os.path.join(self.project_root, "utils", "backtest.py")`
- Line 1050-1051: Pass `--project-root` to main.py subprocess
- Line 1100-1101: Pass project_root to backtest subprocess

### 2. main.py
**Changes needed:**

#### A. Add project root detection (lines 1-100)
- Add `--project-root` argument to argparser (line 560-590)
- Detect if running as exe with `getattr(sys, 'frozen', False)`
- If exe and no `--project-root`, prompt user via dialog (use tkinter)
- Set working directory to project_root with `os.chdir(project_root)`

#### B. Update all file paths
- Line 34: `Path(os.path.join(project_root, "logs")).mkdir(exist_ok=True)`
- Line 40: `logging.FileHandler(os.path.join(project_root, 'logs', 'pipeline.log'))`
- Line 86: `config_path` parameter should be relative to project_root
- Line 596: `Path(os.path.join(project_root, "logs")).mkdir(exist_ok=True)`
- Line 597: `Path(os.path.join(project_root, "data")).mkdir(exist_ok=True)`

#### C. Update DashboardGenerator call
- Line 520: Pass project_root to DashboardGenerator
- Update dashboard.py to accept and use project_root

### 3. src/reporters/dashboard.py
**Changes needed:**

#### A. Update __init__ and generate methods
- Accept `project_root` parameter
- Update `self.output_dir` to use `os.path.join(project_root, output_dir)`
- Update all file writes to use project_root-relative paths

---

## Implementation Order

1. ✅ Create this plan document
2. Modify gui.py:
   - Add project root detection in __init__
   - Remove utils folder button and methods
   - Update all file paths
3. Modify main.py:
   - Add --project-root argument
   - Add exe detection and folder prompt
   - Update all file paths
4. Modify src/reporters/dashboard.py:
   - Accept project_root parameter
   - Update output paths
5. Test:
   - Test as script (should auto-detect)
   - Test manual folder selection
   - Test with exe build
6. Commit and push

---

## Testing Scenarios

### Scenario 1: Running as script (dev mode)
- Should auto-detect project root from script location
- Should save to `.gui_settings.yaml` locally
- All paths should work relative to project root

### Scenario 2: Running as exe (first time)
- Should prompt for Stock-Trader folder location
- Should save to AppData\StockTrader\settings.yaml
- All paths should work relative to selected folder

### Scenario 3: Running as exe (subsequent runs)
- Should load project_root from AppData settings
- Should NOT prompt again
- All paths should work

---

## Key Files/Folders Affected

All these should be relative to project_root:
- `config/config.yaml` - Configuration file
- `config/config.example.yaml` - Template
- `data/sentiment.db` - Database
- `logs/pipeline.log` - Logs
- `reports/dashboard_*.html` - Generated reports
- `utils/*.py` - Utility scripts
- `src/**/*.py` - Source code (for imports)

---

## Notes
- Remove `utils_folder` setting entirely (user request)
- Settings file location differs for exe vs script
- Exe uses AppData, script uses local .gui_settings.yaml
- Project root validation checks for `config/` and `src/` folders
- Auto-create missing folders if user approves
