from pathlib import Path
import plistlib


BASE_DIR = Path(__file__).resolve().parent.parent

PYTHON_PATH = BASE_DIR / ".venv" / "bin" / "python"
MANAGE_PY = BASE_DIR / "manage.py"

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = Path.home() / "Library" / "Logs" / "SalesPilotAI"

PLIST_PATH = (
    LAUNCH_AGENTS
    / "com.salespilot.task-reminders.plist"
)

if not PYTHON_PATH.is_file():
    raise SystemExit(
        f"Virtual environment Python not found: {PYTHON_PATH}"
    )

if not MANAGE_PY.is_file():
    raise SystemExit(
        f"Django manage.py not found: {MANAGE_PY}"
    )

LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

config = {
    "Label": "com.salespilot.task-reminders",

    "ProgramArguments": [
        str(PYTHON_PATH),
        str(MANAGE_PY),
        "process_task_reminders",
    ],

    "WorkingDirectory": str(BASE_DIR),

    "StartInterval": 300,

    "RunAtLoad": True,

    "StandardOutPath": str(
        LOG_DIR / "reminders.log"
    ),

    "StandardErrorPath": str(
        LOG_DIR / "reminders-error.log"
    ),
}

with PLIST_PATH.open("wb") as file:
    plistlib.dump(config, file)

print(f"Scheduler file created: {PLIST_PATH}")
print(f"Project directory: {BASE_DIR}")
print("Reminder interval: every 300 seconds")