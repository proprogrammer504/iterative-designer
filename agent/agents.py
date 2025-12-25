from agent.abstracted_agent import BaseAgent


def check_complete(task: str):
    agent = BaseAgent(task=f"The task at hand is {task}. Evaluate the codebase to determine if this task is complete. Return only True or False")
    return bool(agent.work())