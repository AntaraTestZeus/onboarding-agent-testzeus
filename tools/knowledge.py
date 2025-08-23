# tools/knowledge.py
"""
GPT-5 Custom Tool: testzeus_knowledge
Purpose: Answer user questions using RAG over TestZeus docs
Input: Raw text question
Output: Raw text answer (no JSON)
"""

from typing import List
import os


class RAGService:
    def __init__(self, docs_path: str):
        self.docs_path = docs_path
        self.documents = self._load_docs()

    def _load_docs(self) -> dict:
        """Load all .txt files from docs_path"""
        docs = {}
        if not os.path.exists(self.docs_path):
            print(f"Warning: Docs path not found: {self.docs_path}")
            return docs

        for file in os.listdir(self.docs_path):
            if file.endswith(".txt"):
                path = os.path.join(self.docs_path, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            docs[file] = content
                except Exception as e:
                    print(f"Error reading {file}: {e}")
        print(f"Loaded {len(docs)} docs for RAG")
        return docs

    def retrieve(self, query: str) -> List[str]:
        """Simple keyword-based retrieval"""
        query = query.lower()
        results = []

        for title, content in self.documents.items():
            if query in title.lower() or any(kw in query for kw in ["test", "api", "web", "pricing", "cost", "qa"]):
                snippet = content[:500] + "..." if len(content) > 500 else content
                results.append(f"From '{title}':\n{snippet}")
        return results[:2]


# Global instance
rag_service = RAGService("backend/testzeus_docs")


def tool_testzeus_knowledge(query: str) -> str:
    """
    Called by GPT-5 via free-form tool call.
    Input: "What's the cost for 5 users?"
    Output: Raw text answer
    """
    results = rag_service.retrieve(query)
    if not results:
        return "I don't have detailed info on that. Ask about web, API, or pricing."
    
    return "\n\n".join(results)