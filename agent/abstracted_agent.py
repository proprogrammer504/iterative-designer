class BaseAgent():
    def __init__(self, specialization: str, task: str):
        self.system_prompt = f"You are an agent specialized in {specialization} and are tasked with {task}"
    
    def work(self):
        pass