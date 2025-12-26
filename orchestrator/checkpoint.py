import os
import shutil
from datetime import datetime

SNAPSHOTS_DIR = "snapshots"
IGNORE = {'.git', '__pycache__', 'venv', '.venv', '.vscode', 'node_modules', '.idea', SNAPSHOTS_DIR}


def save_snapshot():
    if not os.path.exists(SNAPSHOTS_DIR):
        os.makedirs(SNAPSHOTS_DIR)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(SNAPSHOTS_DIR, f"snapshot_{timestamp}")
    
    try:
        shutil.copytree(".", snapshot_path, ignore=shutil.ignore_patterns(*IGNORE))
        return f"Snapshot saved to: {snapshot_path}"
    except Exception as e:
        return f"Error saving snapshot: {str(e)}"


def revert_snapshot():
    if not os.path.exists(SNAPSHOTS_DIR):
        return "Error: No snapshots directory found."
    
    snapshots = sorted([d for d in os.listdir(SNAPSHOTS_DIR) if d.startswith("snapshot_")])
    if not snapshots:
        return "Error: No snapshots to revert to."
        
    latest_snapshot = os.path.join(SNAPSHOTS_DIR, snapshots[-1])
    
    try:
        for item in os.listdir("."):
            if item in IGNORE:
                continue
                
            path = os.path.join(".", item)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                
        shutil.copytree(latest_snapshot, ".", dirs_exist_ok=True)
        return f"Successfully reverted to {latest_snapshot}"
        
    except Exception as e:
        return f"Error reverting snapshot: {str(e)}"