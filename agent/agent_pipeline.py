import os
import shutil
import json
from datetime import datetime
from agent.abstracted_agent import BaseAgent


class AgentPipeline:
    def __init__(self, agent_id, task, base_repo_path, workspace_dir, experience_pool):
        self.agent_id = agent_id
        self.task = task
        self.base_repo_path = base_repo_path
        self.workspace_dir = workspace_dir
        self.experience_pool = experience_pool
        self.agent_workspace = os.path.join(workspace_dir, f"agent_{agent_id}")
        self.hypothesis_id = None
        self.hypothesis_text = None
        self.plan = None
        self.evaluation_result = None

    def setup_isolated_workspace(self):
        self.experience_pool.add_log(self.agent_id, "setup", "Creating isolated workspace")
        
        if os.path.exists(self.agent_workspace):
            shutil.rmtree(self.agent_workspace)
        
        ignore_patterns = shutil.ignore_patterns('.git', '__pycache__', 'venv', '.venv', 
                                                  '.vscode', 'node_modules', '.idea', 
                                                  'agent_workspaces', 'snapshots', 'data')
        shutil.copytree(self.base_repo_path, self.agent_workspace, ignore=ignore_patterns)
        
        self.experience_pool.add_log(self.agent_id, "setup", f"Workspace created at {self.agent_workspace}")
        return True

    def cleanup_workspace(self):
        self.experience_pool.add_log(self.agent_id, "cleanup", "Removing isolated workspace")
        if os.path.exists(self.agent_workspace):
            shutil.rmtree(self.agent_workspace)

    def run_hypothesis_phase(self):
        self.experience_pool.add_log(self.agent_id, "hypothesis", "Generating hypothesis")
        
        context = self.experience_pool.get_all_context()
        context_str = json.dumps(context, indent=2)
        
        prompt = f"""
            You are a Lead Research Scientist. 
            Your goal is: {self.task}

            Review the current project state (logs, past hypotheses, results, breakthroughs, pitfalls) below:
            {context_str}

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
            can_execute_terminal=False,
            working_dir=self.agent_workspace
        )
        
        self.hypothesis_text = agent.work()
        
        if self.hypothesis_text and "False" not in self.hypothesis_text:
            self.hypothesis_id = self.experience_pool.add_hypothesis(
                self.agent_id, 
                self.hypothesis_text,
                status="in_progress"
            )
            self.experience_pool.add_log(self.agent_id, "hypothesis", f"Generated: {self.hypothesis_text[:100]}...")
            return True
        
        self.experience_pool.add_log(self.agent_id, "hypothesis", "Failed to generate hypothesis", level="error")
        return False

    def run_planning_phase(self):
        if not self.hypothesis_text:
            return False
            
        self.experience_pool.add_log(self.agent_id, "planning", "Creating implementation plan")
        
        prompt = f"""
            You are a Principal Software Architect.
            Goal: {self.task}
            Hypothesis to Implement: "{self.hypothesis_text}"

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
            can_execute_terminal=False,
            working_dir=self.agent_workspace
        )
        
        self.plan = agent.work()
        
        if self.plan:
            self.experience_pool.update_hypothesis(self.hypothesis_id, {"plan": self.plan})
            self.experience_pool.add_log(self.agent_id, "planning", "Plan created successfully")
            return True
            
        self.experience_pool.add_log(self.agent_id, "planning", "Failed to create plan", level="error")
        return False

    def run_coding_phase(self):
        if not self.plan:
            return False
            
        self.experience_pool.add_log(self.agent_id, "coding", "Implementing plan")
        
        prompt = f"""
            You are a Senior DevOps & Python Engineer.
            Your task is to execute the following implementation plan with precision:

            PLAN:
            {self.plan}

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
            can_execute_terminal=True,
            working_dir=self.agent_workspace
        )
        
        result = agent.work()
        
        if result and "False" not in result:
            self.experience_pool.add_log(self.agent_id, "coding", "Implementation complete")
            return True
            
        self.experience_pool.add_pitfall(
            self.agent_id,
            "Coding phase failed",
            hypothesis_id=self.hypothesis_id,
            error=result
        )
        self.experience_pool.add_log(self.agent_id, "coding", "Implementation failed", level="error")
        return False

    def run_execution_phase(self):
        self.experience_pool.add_log(self.agent_id, "execution", "Running training/execution")
        
        prompt = f"""
            You are a DevOps Engineer responsible for running and monitoring code execution.
            
            Your task:
            1. Identify any main scripts, training scripts, or test suites in the codebase.
            2. Execute them and capture all output.
            3. Monitor for errors or unexpected behavior.
            4. Document the execution results.

            Use the terminal to run scripts and capture output.
            Your Final Answer should summarize what was executed and the results.
            """
            
        agent = BaseAgent(
            specialization="DevOps Engineer",
            task=prompt,
            can_write=True,
            can_execute_terminal=True,
            working_dir=self.agent_workspace
        )
        
        result = agent.work()
        self.experience_pool.add_log(self.agent_id, "execution", f"Execution result: {result[:200] if result else 'None'}...")
        return True

    def run_testing_phase(self):
        self.experience_pool.add_log(self.agent_id, "testing", "Running tests")
        
        prompt = f"""
            You are a QA Engineer.
            
            Your task:
            1. Identify all test files in the codebase.
            2. Run the test suite using pytest or the appropriate test runner.
            3. Analyze test results and identify any failures.
            4. Document which tests passed and which failed.

            Use the terminal to run tests.
            Your Final Answer should be a summary of test results.
            """
            
        agent = BaseAgent(
            specialization="QA Engineer",
            task=prompt,
            can_write=False,
            can_execute_terminal=True,
            working_dir=self.agent_workspace
        )
        
        result = agent.work()
        self.experience_pool.add_log(self.agent_id, "testing", f"Test results: {result[:200] if result else 'None'}...")
        return result

    def run_evaluation_phase(self):
        self.experience_pool.add_log(self.agent_id, "evaluation", "Evaluating hypothesis")
        
        context = self.experience_pool.get_all_context()
        context_str = json.dumps(context, indent=2)
        
        prompt = f"""
            You are a Senior Data Analyst evaluating experiment results.
            
            Goal: {self.task}
            Hypothesis: {self.hypothesis_text}
            Plan: {self.plan}
            
            Project Context:
            {context_str}

            Analyze the codebase and any logs/outputs to determine:
            1. Was the hypothesis successfully tested?
            2. Should the hypothesis be ACCEPTED or REJECTED?
            3. What evidence supports your conclusion?
            4. Were there any unexpected findings or side effects?
            5. What improvements or next steps do you recommend?

            Your Final Answer must be a JSON object with this structure:
            {{
                "accepted": true/false,
                "confidence": 0.0-1.0,
                "evidence": "summary of evidence",
                "findings": "key findings",
                "recommendations": "next steps"
            }}
            """
            
        agent = BaseAgent(
            specialization="Data Analyst",
            task=prompt,
            can_write=False,
            can_execute_terminal=True,
            working_dir=self.agent_workspace
        )
        
        result = agent.work()
        
        try:
            if "{" in result and "}" in result:
                json_str = result[result.index("{"):result.rindex("}")+1]
                self.evaluation_result = json.loads(json_str)
            else:
                self.evaluation_result = {
                    "accepted": False,
                    "confidence": 0.0,
                    "evidence": result,
                    "findings": "Could not parse evaluation",
                    "recommendations": "Review manually"
                }
        except:
            self.evaluation_result = {
                "accepted": False,
                "confidence": 0.0,
                "evidence": result,
                "findings": "Evaluation parsing failed",
                "recommendations": "Review manually"
            }
        
        self.experience_pool.add_result(
            self.agent_id,
            self.hypothesis_id,
            self.evaluation_result
        )
        
        self.experience_pool.update_hypothesis(self.hypothesis_id, {
            "status": "completed",
            "evaluation": self.evaluation_result,
            "completed_at": datetime.now().isoformat()
        })
        
        if self.evaluation_result.get("accepted"):
            self.experience_pool.add_breakthrough(
                self.agent_id,
                f"Hypothesis accepted: {self.hypothesis_text[:100]}...",
                hypothesis_id=self.hypothesis_id
            )
        else:
            self.experience_pool.add_pitfall(
                self.agent_id,
                f"Hypothesis rejected: {self.hypothesis_text[:100]}...",
                hypothesis_id=self.hypothesis_id
            )
        
        self.experience_pool.add_log(self.agent_id, "evaluation", f"Evaluation complete: accepted={self.evaluation_result.get('accepted')}")
        return self.evaluation_result

    def run_full_pipeline(self):
        self.experience_pool.add_log(self.agent_id, "pipeline", "Starting full pipeline")
        
        try:
            if not self.setup_isolated_workspace():
                return None
            
            if not self.run_hypothesis_phase():
                self.cleanup_workspace()
                return None
            
            if not self.run_planning_phase():
                self.cleanup_workspace()
                return None
            
            if not self.run_coding_phase():
                self.cleanup_workspace()
                return None
            
            self.run_execution_phase()
            self.run_testing_phase()
            result = self.run_evaluation_phase()
            
            self.cleanup_workspace()
            
            self.experience_pool.add_log(self.agent_id, "pipeline", "Pipeline completed")
            
            return {
                "agent_id": self.agent_id,
                "hypothesis_id": self.hypothesis_id,
                "hypothesis": self.hypothesis_text,
                "plan": self.plan,
                "evaluation": result
            }
            
        except Exception as e:
            self.experience_pool.add_log(self.agent_id, "pipeline", f"Pipeline failed: {str(e)}", level="error")
            self.experience_pool.add_pitfall(
                self.agent_id,
                f"Pipeline crashed: {str(e)}",
                hypothesis_id=self.hypothesis_id,
                error=str(e)
            )
            self.cleanup_workspace()
            return None
