import os
import json
import concurrent.futures
from datetime import datetime

from agent.agents import check_complete, generate_summary
from agent.agent_pipeline import AgentPipeline
from orchestrator.experience_pool import ExperiencePool
from orchestrator.checkpoint import save_snapshot, revert_snapshot


class Orchestrator:
    def __init__(self, task, repo_path, n_agents=3, data_dir="data", workspace_dir="agent_workspaces"):
        self.task = task
        self.repo_path = repo_path
        self.n_agents = n_agents
        self.data_dir = data_dir
        self.workspace_dir = workspace_dir
        self.experience_pool = ExperiencePool(data_dir)
        self.iteration = 0
        self.max_iterations = 100
        self._setup_directories()

    def _setup_directories(self):
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir)

    def run(self):
        self.experience_pool.add_log("orchestrator", "start", f"Starting orchestration with {self.n_agents} agents")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            self.experience_pool.add_log("orchestrator", "iteration", f"Starting iteration {self.iteration}")
            
            if self._check_task_complete():
                self._generate_report()
                return True
            
            save_snapshot(self.repo_path)
            
            results = self._run_parallel_agents()
            
            if results:
                improvement = self._synthesize_improvements(results)
                if improvement:
                    self._apply_improvement(improvement)
            
            self.experience_pool.add_log("orchestrator", "iteration", f"Completed iteration {self.iteration}")
        
        self.experience_pool.add_log("orchestrator", "end", "Max iterations reached")
        self._generate_report()
        return False

    def _check_task_complete(self):
        self.experience_pool.add_log("orchestrator", "check", "Checking if task is complete")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo_path)
            result = check_complete(self.task)
            return result
        finally:
            os.chdir(original_cwd)

    def _run_parallel_agents(self):
        self.experience_pool.add_log("orchestrator", "parallel", f"Spawning {self.n_agents} parallel agent pipelines")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.n_agents) as executor:
            futures = {}
            
            for i in range(self.n_agents):
                agent_id = f"agent_{self.iteration}_{i}"
                pipeline = AgentPipeline(
                    agent_id=agent_id,
                    task=self.task,
                    base_repo_path=self.repo_path,
                    workspace_dir=self.workspace_dir,
                    experience_pool=self.experience_pool
                )
                future = executor.submit(pipeline.run_full_pipeline)
                futures[future] = agent_id
            
            for future in concurrent.futures.as_completed(futures):
                agent_id = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.experience_pool.add_log(
                            "orchestrator", 
                            "parallel", 
                            f"Agent {agent_id} completed successfully"
                        )
                    else:
                        self.experience_pool.add_log(
                            "orchestrator", 
                            "parallel", 
                            f"Agent {agent_id} returned no result",
                            level="warning"
                        )
                except Exception as e:
                    self.experience_pool.add_log(
                        "orchestrator", 
                        "parallel", 
                        f"Agent {agent_id} failed with error: {str(e)}",
                        level="error"
                    )
        
        self.experience_pool.add_log(
            "orchestrator", 
            "parallel", 
            f"Parallel execution complete. {len(results)}/{self.n_agents} agents succeeded"
        )
        
        return results

    def _synthesize_improvements(self, results):
        self.experience_pool.add_log("orchestrator", "synthesis", "Synthesizing improvements from agent results")
        
        accepted_results = [r for r in results if r.get("evaluation", {}).get("accepted")]
        
        if not accepted_results:
            self.experience_pool.add_log(
                "orchestrator", 
                "synthesis", 
                "No accepted hypotheses to synthesize",
                level="warning"
            )
            return None
        
        best_result = max(
            accepted_results,
            key=lambda r: r.get("evaluation", {}).get("confidence", 0)
        )
        
        self.experience_pool.add_log(
            "orchestrator", 
            "synthesis", 
            f"Selected best result from agent {best_result['agent_id']} with confidence {best_result.get('evaluation', {}).get('confidence', 0)}"
        )
        
        context = self.experience_pool.get_all_context()
        
        from agent.abstracted_agent import BaseAgent
        
        prompt = f"""
            You are a Principal Software Engineer responsible for integrating improvements.
            
            Task Goal: {self.task}
            
            The following hypothesis was tested and ACCEPTED:
            Hypothesis: {best_result['hypothesis']}
            Plan: {best_result['plan']}
            Evaluation: {json.dumps(best_result['evaluation'], indent=2)}
            
            Additional context from all agent experiments:
            {json.dumps(context, indent=2)[:5000]}
            
            Your task:
            1. Analyze the accepted hypothesis and its implementation plan.
            2. Create a FINAL implementation plan that incorporates the validated improvement.
            3. This plan will be applied to the MAIN codebase.
            4. Be conservative - only include changes that are well-supported by the evidence.
            
            Output the implementation plan as detailed step-by-step instructions.
            """
        
        agent = BaseAgent(
            specialization="Principal Software Engineer",
            task=prompt,
            can_write=False,
            can_execute_terminal=False,
            working_dir=self.repo_path
        )
        
        improvement_plan = agent.work()
        
        self.experience_pool.add_log("orchestrator", "synthesis", "Improvement plan created")
        
        return {
            "source_agent": best_result["agent_id"],
            "hypothesis_id": best_result["hypothesis_id"],
            "hypothesis": best_result["hypothesis"],
            "plan": improvement_plan,
            "confidence": best_result.get("evaluation", {}).get("confidence", 0)
        }

    def _apply_improvement(self, improvement):
        self.experience_pool.add_log(
            "orchestrator", 
            "apply", 
            f"Applying improvement from hypothesis: {improvement['hypothesis'][:50]}..."
        )
        
        from agent.abstracted_agent import BaseAgent
        
        prompt = f"""
            You are a Senior Software Engineer applying a validated improvement to the codebase.
            
            Task Goal: {self.task}
            
            Validated Improvement:
            Hypothesis: {improvement['hypothesis']}
            Implementation Plan: {improvement['plan']}
            Confidence: {improvement['confidence']}
            
            Your task:
            1. Follow the implementation plan exactly.
            2. Make the necessary code changes.
            3. Run any tests to verify the changes work.
            4. Be careful and conservative - this affects the main codebase.
            
            When complete, provide a summary of what was changed.
            """
        
        agent = BaseAgent(
            specialization="Senior Software Engineer",
            task=prompt,
            can_write=True,
            can_execute_terminal=True,
            working_dir=self.repo_path
        )
        
        result = agent.work()
        
        self.experience_pool.add_log("orchestrator", "apply", f"Improvement applied: {result[:200] if result else 'None'}...")
        self.experience_pool.add_breakthrough(
            "orchestrator",
            f"Applied improvement: {improvement['hypothesis'][:100]}",
            hypothesis_id=improvement["hypothesis_id"]
        )

    def _generate_report(self):
        self.experience_pool.add_log("orchestrator", "report", "Generating final report")
        
        summary = generate_summary()
        
        report_path = os.path.join(self.data_dir, "report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Project Report\n\n")
            f.write(f"**Task:** {self.task}\n\n")
            f.write(f"**Iterations:** {self.iteration}\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")
            f.write(summary if summary else "No summary generated.")
        
        self.experience_pool.add_log("orchestrator", "report", f"Report saved to {report_path}")
        print(f"Report saved to {report_path}")

    def revert_to_snapshot(self):
        result = revert_snapshot(self.repo_path)
        self.experience_pool.add_log("orchestrator", "revert", result)
        return result
