import os
import shutil
from datetime import datetime

SNAPSHOTS_DIR = "snapshots"
IGNORE = {'.git', '__pycache__', 'venv', '.venv', '.vscode', 'node_modules', '.idea', 
          SNAPSHOTS_DIR, 'agent_workspaces', 'data'}


def save_snapshot(repo_path="."):
    snapshots_path = os.path.join(repo_path, SNAPSHOTS_DIR)
    
    if not os.path.exists(snapshots_path):
        os.makedirs(snapshots_path)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = os.path.join(snapshots_path, f"snapshot_{timestamp}")
    
    try:
        shutil.copytree(
            repo_path, 
            snapshot_path, 
            ignore=shutil.ignore_patterns(*IGNORE)
        )
        return f"Snapshot saved to: {snapshot_path}"
    except Exception as e:
        return f"Error saving snapshot: {str(e)}"


def revert_snapshot(repo_path="."):
    snapshots_path = os.path.join(repo_path, SNAPSHOTS_DIR)
    
    if not os.path.exists(snapshots_path):
        return "Error: No snapshots directory found."
    
    snapshots = sorted([d for d in os.listdir(snapshots_path) if d.startswith("snapshot_")])
    if not snapshots:
        return "Error: No snapshots to revert to."
        
    latest_snapshot = os.path.join(snapshots_path, snapshots[-1])
    
    try:
        for item in os.listdir(repo_path):
            if item in IGNORE:
                continue
                
            path = os.path.join(repo_path, item)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                
        for item in os.listdir(latest_snapshot):
            src = os.path.join(latest_snapshot, item)
            dst = os.path.join(repo_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
                
        return f"Successfully reverted to {latest_snapshot}"
        
    except Exception as e:
        return f"Error reverting snapshot: {str(e)}"


def list_snapshots(repo_path="."):
    snapshots_path = os.path.join(repo_path, SNAPSHOTS_DIR)
    
    if not os.path.exists(snapshots_path):
        return []
    
    return sorted([d for d in os.listdir(snapshots_path) if d.startswith("snapshot_")])


def delete_snapshot(repo_path, snapshot_name):
    snapshot_path = os.path.join(repo_path, SNAPSHOTS_DIR, snapshot_name)
    
    if not os.path.exists(snapshot_path):
        return f"Error: Snapshot {snapshot_name} not found."
    
    try:
        shutil.rmtree(snapshot_path)
        return f"Deleted snapshot: {snapshot_name}"
    except Exception as e:
        return f"Error deleting snapshot: {str(e)}"


def cleanup_old_snapshots(repo_path=".", keep_count=5):
    snapshots = list_snapshots(repo_path)
    
    if len(snapshots) <= keep_count:
        return f"No cleanup needed. {len(snapshots)} snapshots exist."
    
    to_delete = snapshots[:-keep_count]
    deleted = []
    
    for snapshot in to_delete:
        result = delete_snapshot(repo_path, snapshot)
        deleted.append(result)
    
    return f"Cleaned up {len(to_delete)} old snapshots."
