from pathlib import Path

from app.core.config import CONTEXT_DIR


CONTEXT_FILES = [
    "smartphone_system_pm_checklist.md",
    "design_system_guidelines.md",
    "qa_review_checklist.md",
    "jira_story_template.md",
    "sample_prd.md",
]


def load_context_pack() -> str:
    chunks: list[str] = []
    for filename in CONTEXT_FILES:
        path = Path(CONTEXT_DIR) / filename
        if path.exists():
            chunks.append(f"\n# {filename}\n{path.read_text(encoding='utf-8')}")
    return "\n".join(chunks)
