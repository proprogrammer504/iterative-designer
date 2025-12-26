import os
import json
import threading
from datetime import datetime


class ExperiencePool:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.lock = threading.Lock()
        self.files = {
            "breakthroughs": "breakthroughs.json",
            "hypotheses": "hypothesis.json",
            "pitfalls": "pitfalls.json",
            "logs": "log.json",
            "results": "results.json"
        }
        self._initialize()

    def _initialize(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        for key, filename in self.files.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    json.dump({"entries": []}, f)

    def _read_file(self, key):
        filepath = os.path.join(self.data_dir, self.files[key])
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"entries": []}

    def _write_file(self, key, data):
        filepath = os.path.join(self.data_dir, self.files[key])
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def add_breakthrough(self, agent_id, description, hypothesis_id=None):
        with self.lock:
            data = self._read_file("breakthroughs")
            data["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "hypothesis_id": hypothesis_id,
                "description": description
            })
            self._write_file("breakthroughs", data)

    def add_pitfall(self, agent_id, description, hypothesis_id=None, error=None):
        with self.lock:
            data = self._read_file("pitfalls")
            data["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "hypothesis_id": hypothesis_id,
                "description": description,
                "error": error
            })
            self._write_file("pitfalls", data)

    def add_hypothesis(self, agent_id, hypothesis_text, status="proposed"):
        with self.lock:
            data = self._read_file("hypotheses")
            hypothesis_id = f"hyp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{agent_id}"
            entry = {
                "id": hypothesis_id,
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "hypothesis": hypothesis_text,
                "status": status,
                "plan": None,
                "evaluation": None
            }
            if "candidates" not in data:
                data["candidates"] = []
            data["candidates"].append(entry)
            self._write_file("hypotheses", data)
            return hypothesis_id

    def update_hypothesis(self, hypothesis_id, updates):
        with self.lock:
            data = self._read_file("hypotheses")
            for entry in data.get("candidates", []):
                if entry.get("id") == hypothesis_id:
                    entry.update(updates)
                    entry["updated_at"] = datetime.now().isoformat()
                    break
            self._write_file("hypotheses", data)

    def add_result(self, agent_id, hypothesis_id, result, metrics=None):
        with self.lock:
            data = self._read_file("results")
            data["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "hypothesis_id": hypothesis_id,
                "result": result,
                "metrics": metrics or {}
            })
            self._write_file("results", data)

    def add_log(self, agent_id, phase, message, level="info"):
        with self.lock:
            data = self._read_file("logs")
            data["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "phase": phase,
                "level": level,
                "message": message
            })
            self._write_file("logs", data)

    def get_all_context(self):
        context = {}
        for key in self.files:
            context[key] = self._read_file(key)
        return context

    def get_completed_hypotheses(self):
        data = self._read_file("hypotheses")
        return [h for h in data.get("candidates", []) if h.get("status") == "completed"]

    def get_successful_results(self):
        data = self._read_file("results")
        return [r for r in data.get("entries", []) if r.get("result", {}).get("accepted")]

    def get_pitfalls_summary(self):
        data = self._read_file("pitfalls")
        return data.get("entries", [])

    def get_breakthroughs_summary(self):
        data = self._read_file("breakthroughs")
        return data.get("entries", [])
