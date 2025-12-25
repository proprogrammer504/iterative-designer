import os
import json

from agent.agents import *


class Orchestrator:
    def __init__(self, task: str, n_agents: int):
        self.task = task
        self.n_agents = n_agents
        self.data_dir = "data"
        self.files = ["breakthroughs.json", "hypothesis.json", "pitfalls.json", "log.json"]
        self.build()

    def orchestrator(self):
        goal = self.task
        
        if check_complete(goal):
            with open("report.md", "w") as f:
                summary = generate_summary()
                f.write(summary)

        else:
            print("here we want to initialize n_agents number of agents to begin working on the task")

    def build(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        for file_name in self.files:
            file_path = os.path.join(self.data_dir, file_name)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump({}, f)