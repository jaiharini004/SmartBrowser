import json
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, db_path: str = "tmp/memory.json"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump([], f)

    def add_memory(self, task: str, result: str):
        try:
            with open(self.db_path, "r") as f:
                memories = json.load(f)
            memories.append({"task": task, "result": result})
            # keep only last 10 mems to save tokens
            if len(memories) > 10:
                memories = memories[-10:]
            with open(self.db_path, "w") as f:
                json.dump(memories, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")

    def get_memory_context(self) -> str:
        try:
            with open(self.db_path, "r") as f:
                memories = json.load(f)
            if not memories:
                return ""
            context = "PREVIOUS SESSION MEMORIES:\n"
            for m in memories:
                context += f"- User requested: {m['task']}\n  Outcome: {m['result']}\n"
            context += "\nPlease use this information for context in your next steps.\n"
            return context
        except Exception as e:
            logger.error(f"Failed to get memory context: {e}")
            return ""

    def clear_memory(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
