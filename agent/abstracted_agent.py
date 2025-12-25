import os
import re
import subprocess


class BaseAgent:
    def __init__(self, specialization, task, can_write=False, can_execute_terminal=False, extra_tools=None, max_steps=10):
        self.specialization = specialization
        self.task = task
        self.can_write = can_write
        self.can_execute_terminal = can_execute_terminal
        self.max_steps = max_steps
        
        self.tools = {
            "list_files": self.list_files,
            "read_file": self.read_file
        }

        if self.can_write:
            self.tools["write_file"] = self.write_file
            
        if self.can_execute_terminal:
            self.tools["run_terminal"] = self.run_terminal

        if extra_tools:
            self.tools.update(extra_tools)

        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self):
        tool_list = []
        for name in self.tools:
            if name == "write_file":
                tool_list.append(f"{name}(input_str): Writes to file. Input format: 'filepath|content'")
            elif name == "list_files":
                tool_list.append(f"{name}(dir_path): Lists files recursively.")
            elif name == "read_file":
                tool_list.append(f"{name}(file_path): Reads file content.")
            elif name == "run_terminal":
                tool_list.append(f"{name}(command): Executes command in venv. (Dangerous commands blocked).")
            else:
                tool_list.append(f"{name}(input): Custom tool.")
        
        tools_desc = "\n".join([f"{i+1}. {t}" for i, t in enumerate(tool_list)])

        return f"""You are an expert in {self.specialization}.
                    Objective: {self.task}

                    Available Tools:
                    {tools_desc}

                    Protocol:
                    1. Thought: Analyze the situation and determine the next step.
                    2. Action: <tool_name>
                    3. Action Input: <input>
                    4. Observation: <tool_output>
                    ... (Repeat as needed)
                    5. Final Answer: <your conclusion>

                    Rules:
                    - Do not hallucinate file contents.
                    - Follow the Protocol strictly.
                    - When you have the answer, output it as Final Answer."""

    def list_files(self, dir_path="."):
        file_list = []
        ignore_dirs = {'.git', '__pycache__', 'venv', '.vscode', 'node_modules', '.idea', '.venv'}
        try:
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for file in files:
                    file_list.append(os.path.join(root, file))
            return "\n".join(file_list) if file_list else "No files found."
        except Exception as e:
            return str(e)

    def read_file(self, file_path):
        try:
            if ".." in file_path or file_path.startswith("/"):
                return "Error: Access denied."
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return str(e)

    def write_file(self, input_str):
        if not self.can_write:
            return "Error: Write access denied."
        
        try:
            if "|" not in input_str:
                return "Error: Input format must be 'filepath|content'"
            
            file_path, content = input_str.split("|", 1)
            file_path = file_path.strip()
            
            if ".." in file_path or file_path.startswith("/"):
                return "Error: Access denied (External path)."
                
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Success: Wrote to {file_path}"
        except Exception as e:
            return str(e)

    def run_terminal(self, command):
        if not self.can_execute_terminal:
            return "Error: Terminal access denied."
        
        forbidden_patterns = [
            r"\bsudo\b", r"\bsu\b", r"\bmkfs\b", r"\bdd\b", r"\bshutdown\b", r"\breboot\b",
            r"\brm\b\s+.*-[a-zA-Z]*[rR]", r"\brm\b\s+.*--recursive"
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, command):
                return f"Error: Command blocked for safety. Forbidden pattern detected: {pattern}"

        venv_dir = None
        if os.path.exists(".venv"):
            venv_dir = ".venv"
        elif os.path.exists("venv"):
            venv_dir = "venv"
            
        activate_cmd = ""
        if venv_dir:
            if os.name == 'nt':
                activate_cmd = f"{venv_dir}\\Scripts\\activate && "
            else:
                activate_cmd = f". {venv_dir}/bin/activate && "
        
        full_command = activate_cmd + command

        try:
            result = subprocess.run(
                full_command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
                
            return output.strip() if output.strip() else "Success (No output)"
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def call_llm(self, messages):
        raise NotImplementedError("Integrate DeepSeek API here")

    def work(self):
        messages = [{"role": "system", "content": self.system_prompt}]
        step_count = 0
        
        while step_count < self.max_steps:
            try:
                response_text = self.call_llm(messages)
                messages.append({"role": "assistant", "content": response_text})
                
                if "Final Answer:" in response_text:
                    return response_text.split("Final Answer:")[-1].strip()

                action_match = re.search(r"Action:\s*(.+)", response_text)
                input_match = re.search(r"Action Input:\s*(.+?)(?=\nObservation:|$)", response_text, re.DOTALL)

                if action_match and input_match:
                    tool_name = action_match.group(1).strip()
                    tool_input = input_match.group(1).strip()
                    
                    if tool_name in self.tools:
                        result = self.tools[tool_name](tool_input)
                    else:
                        result = f"Error: Tool '{tool_name}' not found."
                    
                    observation = f"Observation: {result}"
                    messages.append({"role": "user", "content": observation})
                else:
                    messages.append({"role": "user", "content": "Observation: Invalid format. Use Action and Action Input."})

            except Exception as e:
                print(e)
                break
            
            step_count += 1

        return "False"