import os
import sys
import argparse
import subprocess
import shutil
from urllib.parse import urlparse

from orchestrator.ochestrator import Orchestrator


def parse_github_url(url):
    parsed = urlparse(url)
    
    if parsed.scheme not in ['http', 'https']:
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
    
    if 'github.com' not in parsed.netloc and 'gitlab.com' not in parsed.netloc:
        raise ValueError(f"URL must be from github.com or gitlab.com")
    
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) < 2:
        raise ValueError("Invalid repository URL format")
    
    repo_name = path_parts[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    return repo_name


def clone_repository(url, target_dir):
    if os.path.exists(target_dir):
        print(f"Directory {target_dir} already exists. Removing...")
        shutil.rmtree(target_dir)
    
    print(f"Cloning repository from {url}...")
    
    try:
        result = subprocess.run(
            ['git', 'clone', url, target_dir],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")
        
        print(f"Repository cloned to {target_dir}")
        return True
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git clone timed out")
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not in PATH")


def setup_virtual_environment(repo_path):
    venv_path = os.path.join(repo_path, ".venv")
    
    print("Setting up virtual environment...")
    
    try:
        subprocess.run(
            [sys.executable, '-m', 'venv', venv_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if os.name == 'nt':
            pip_path = os.path.join(venv_path, 'Scripts', 'pip')
        else:
            pip_path = os.path.join(venv_path, 'bin', 'pip')
        
        requirements_path = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            print("Installing dependencies from requirements.txt...")
            subprocess.run(
                [pip_path, 'install', '-r', requirements_path],
                capture_output=True,
                text=True,
                timeout=300
            )
        
        print("Virtual environment setup complete")
        return True
        
    except Exception as e:
        print(f"Warning: Could not setup virtual environment: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Iterative Designer - AI-powered code improvement system'
    )
    
    parser.add_argument(
        '--task',
        type=str,
        required=True,
        help='The task or goal to accomplish'
    )
    
    parser.add_argument(
        '--repo',
        type=str,
        required=True,
        help='GitHub repository URL to clone and work on'
    )
    
    parser.add_argument(
        '--agents',
        type=int,
        default=3,
        help='Number of parallel agents (default: 3)'
    )
    
    parser.add_argument(
        '--workspace',
        type=str,
        default='workspace',
        help='Directory to clone the repository into (default: workspace)'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data',
        help='Directory for storing experience pool data (default: data)'
    )
    
    parser.add_argument(
        '--no-venv',
        action='store_true',
        help='Skip virtual environment setup'
    )
    
    args = parser.parse_args()
    
    try:
        repo_name = parse_github_url(args.repo)
        repo_path = os.path.join(args.workspace, repo_name)
        
        os.makedirs(args.workspace, exist_ok=True)
        os.makedirs(args.data_dir, exist_ok=True)
        
        clone_repository(args.repo, repo_path)
        
        if not args.no_venv:
            setup_virtual_environment(repo_path)
        
        print(f"\nStarting Orchestrator...")
        print(f"Task: {args.task}")
        print(f"Repository: {repo_path}")
        print(f"Agents: {args.agents}")
        print("-" * 50)
        
        orchestrator = Orchestrator(
            task=args.task,
            repo_path=repo_path,
            n_agents=args.agents,
            data_dir=args.data_dir,
            workspace_dir=os.path.join(args.workspace, 'agent_workspaces')
        )
        
        success = orchestrator.run()
        
        if success:
            print("\nTask completed successfully!")
            sys.exit(0)
        else:
            print("\nTask did not complete within max iterations.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
