import os
import json
import multiprocessing
from agent.abstracted_agent import BaseAgent

def check_complete(task):
    prompt = f"""
        Analyze the codebase to determine if this task is complete: {task}
        Use the available tools to verify files and content.
        Constraint: Your Final Answer must be strictly 'True' or 'False'. No other text.
        """
    agent = BaseAgent(
        specialization="Quality Assurance", 
        task=prompt
    )
    
    result = agent.work()
    
    if result and "True" in result:
        return True
    return False

def generate_summary():
    data_dir = "data"
    files = ["breakthroughs.json", "hypothesis.json", "pitfalls.json", "log.json"]
    context = ""

    for filename in files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    formatted_content = json.dumps(content, indent=2)
                    context += f"\n\n--- FILE: {filename} ---\n{formatted_content}"
            except Exception as e:
                context += f"\n\n--- FILE: {filename} ---\n[Error reading file: {str(e)}]"
        else:
            context += f"\n\n--- FILE: {filename} ---\n[File not found]"

    prompt = f"""
        You are a Project Manager and Documentation Expert.
        Your task is to review the following project logs and generate a concise but comprehensive progress report.

        Here are the project logs:
        {context}

        Please structure your summary to include:
        1. Key Breakthroughs & Achievements
        2. Current Hypotheses being tested
        3. Identified Pitfalls & Risks
        4. A chronological summary of recent events (from log.json)

        Format the output using Markdown with clear headers, bullet points, and appropriate spacing. 
        Ensure that newlines are used effectively to make the report readable and aesthetically pleasing. 
        Return ONLY the summary text.
        """

    agent = BaseAgent(
        specialization="Technical Project Manager", 
        task=prompt,
        can_write=False 
    )
    
    return agent.work()

def generate_hypothesis(task):
    data_dir = "data"
    files = ["breakthroughs.json", "hypothesis.json", "pitfalls.json", "log.json", "results.json"]
    context = ""

    for filename in files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    formatted_content = json.dumps(content, indent=2)
                    context += f"\n\n--- FILE: {filename} ---\n{formatted_content}"
            except Exception:
                pass

    prompt = f"""
        You are a Lead Research Scientist. 
        Your goal is: {task}

        Review the current project state (logs, past hypotheses, results, breakthroughs, pitfalls) below:
        {context}

        Based on this data, formulate a NEW, scientifically grounded hypothesis that could bring us closer to the goal.
        Your hypothesis can focus on direct improvements, OR it can focus on gathering more data (logging, tracking, observability) if we lack sufficient information.
        The hypothesis must be testable: we need to be able to clearly Accept or Reject it based on the results.

        Avoid repeating failed hypotheses or pitfalls.

        Format:
        Return ONLY the hypothesis text. Do not add conversational filler.
        """

    agent = BaseAgent(
        specialization="Scientific Researcher", 
        task=prompt,
        can_write=False,
        can_execute_terminal=False
    )
    
    return agent.work()

def run_designer_agent(hypothesis, goal):
    prompt = f"""
        You are a Principal Software Architect.
        Goal: {goal}
        Hypothesis to Implement: "{hypothesis}"

        Your task is to analyze the codebase and create a COMPREHENSIVE implementation plan to test this hypothesis.

        Important Context:
        The implementation does not strictly need to be a "feature". It can involve:
        - Adding logging or telemetry to track behavior.
        - Writing isolated scripts to stress-test components.
        - Refactoring code to expose internal states for measurement.
        Your priority is designing a mechanism that generates data to definitively ACCEPT or REJECT the hypothesis.

        Guidelines:
        1. Use the available tools to explore the existing code structure.
        2. Outline specific files to create or modify.
        3. Describe the logic and data flow changes required.
        4. Define verification steps (e.g., "Run script X to verify Y").
        5. DO NOT WRITE CODE. Only write the plan/logic.

        Output Format:
        Return the plan as a detailed step-by-step set of instructions that a developer can follow blindly.
        """
    agent = BaseAgent(
        specialization="Software Architect", 
        task=prompt,
        can_write=False,
        can_execute_terminal=False
    )
    return agent.work()

def run_coding_agent(plan):
    prompt = f"""
        You are a Senior DevOps & Python Engineer.
        Your task is to execute the following implementation plan with precision:

        PLAN:
        {plan}

        Important Context:
        Your work involves creating the necessary code to validate the hypothesis. This includes:
        - Writing feature code.
        - Implementing logging, metrics, or tracing.
        - Creating test scripts or simulation harnesses.
        Do not hesitate to modify the codebase to add "invisible" work (logging/tracking) if the plan requires it.

        Instructions:
        1. Use 'write_file' to create/edit code.
        2. Use 'run_terminal' to install dependencies, run tests, or execute scripts.
        3. If you encounter errors, debug them using the terminal and file tools.
        4. Ensure the solution is robust and follows the plan.

        Constraint:
        When you have completed the plan and verified it works, your Final Answer should be a brief confirmation of what was done.
        """
    agent = BaseAgent(
        specialization="Full Stack Engineer", 
        task=prompt,
        can_write=True,
        can_execute_terminal=True
    )
    return agent.work()