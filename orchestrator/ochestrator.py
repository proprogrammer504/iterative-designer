import os
import json
import multiprocessing
from datetime import datetime

from agent.agents import (
    check_complete, 
    generate_summary, 
    generate_hypothesis, 
    run_designer_agent, 
    run_coding_agent,
    run_training_agent,
    run_evaluation_pipeline
)
from checkpoint import save_snapshot, revert_snapshot

class Orchestrator:
    def __init__(self, task, n_agents):
        self.task = task
        self.n_agents = n_agents
        self.data_dir = "data"
        self.files = ["breakthroughs.json", "hypothesis.json", "pitfalls.json", "log.json", "results.json"]
        self.build()

    def orchestrator(self):
        goal = self.task
        
        if check_complete(goal):
            print("Task Completed. Generating Report...")
            with open("report.md", "w") as f:
                summary = generate_summary()
                f.write(summary)
            print("Report saved to report.md")
            return

        print(save_snapshot())
        
        pending_hypotheses = self.get_proposed_hypotheses()
        
        if pending_hypotheses:
            print(f"Found {len(pending_hypotheses)} proposed hypotheses. Processing...")
            self.process_hypotheses(pending_hypotheses, goal)

        else:
            print(f"No pending hypotheses. Spawning {self.n_agents} researchers...")
            
            with multiprocessing.Pool(processes=self.n_agents) as pool:
                new_hypotheses = pool.map(generate_hypothesis, [goal] * self.n_agents)
            
            self.update_hypotheses(new_hypotheses)
            
        self.orchestrator()

    def get_proposed_hypotheses(self):
        hyp_file = os.path.join(self.data_dir, "hypothesis.json")
        if not os.path.exists(hyp_file):
            return []
            
        with open(hyp_file, 'r') as f:
            try:
                data = json.load(f)
                return [h for h in data.get("candidates", []) if h.get("status") == "proposed"]
            except:
                return []

    def process_hypotheses(self, hypotheses, goal):
        hyp_file = os.path.join(self.data_dir, "hypothesis.json")
        
        with open(hyp_file, 'r') as f:
            full_data = json.load(f)

        for candidate in hypotheses:
            hypothesis_text = candidate["hypothesis"]
            print(f"\n--- Implementing Hypothesis: {hypothesis_text[:50]}... ---")
            
            print("Running Designer Agent...")
            plan = run_designer_agent(hypothesis_text, goal)
            print(f"Design Plan Created.")
            
            print("Running Coding Agent...")
            run_coding_agent(plan)
            print("Coding Complete.")

            print("Running Training/Execution Agent...")
            run_training_agent()
            print("Execution Phase Complete.")

            print("Running Evaluation Pipeline...")
            eval_result = run_evaluation_pipeline(hypothesis_text)
            print(f"Evaluation Result: {eval_result}")
            
            for entry in full_data.get("candidates", []):
                if entry["hypothesis"] == hypothesis_text and entry["status"] == "proposed":
                    entry["status"] = "completed"
                    entry["plan"] = plan
                    entry["evaluation"] = eval_result
                    entry["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
            
            with open(hyp_file, 'w') as f:
                json.dump(full_data, f, indent=4)


    def update_hypotheses(self, new_hypotheses):
        hyp_file = os.path.join(self.data_dir, "hypothesis.json")
        current_data = {}
        if os.path.exists(hyp_file):
            with open(hyp_file, 'r') as f:
                try: 
                    current_data = json.load(f)
                except: 
                    current_data = {}
        
        if "candidates" not in current_data:
            current_data["candidates"] = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for h in new_hypotheses:
            if h and "False" not in h:
                current_data["candidates"].append({
                    "timestamp": timestamp,
                    "hypothesis": h,
                    "status": "proposed"
                })

        with open(hyp_file, 'w') as f:
            json.dump(current_data, f, indent=4)

    def build(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        for file_name in self.files:
            file_path = os.path.join(self.data_dir, file_name)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump({}, f)