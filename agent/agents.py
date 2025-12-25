import os
import json

from agent.abstracted_agent import BaseAgent


def check_complete(task):
    prompt = f"""
        Analyze the codebase to determine if this task is complete: {task}
        Use the available tools to verify files and content.
        Constraint: Your Final Answer must be strictly 'True' or 'False'. No other text.
        """
    agent = BaseAgent(
        can_write=False,
        extra_tools=None,
        max_steps=20,
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
        can_write=False,
        max_steps=6
    )
    
    return agent.work()