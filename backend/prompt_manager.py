"""
Prompt manager — loads prompts from the prompts/ directory.
Falls back to hardcoded defaults if files are missing.
"""
import os

_PROMPT_DIR = os.path.join(os.path.dirname(__file__), 'prompts')

_DEFAULTS = {
    'refine_query': (
        "You are a Cybercrime Threat Intelligence Expert. Refine the user query for dark web search engines. "
        "Output only the refined query, no extra text."
    ),
    'filter_results': (
        "You are a Cybercrime Threat Intelligence Expert. Select the top 20 most relevant result indices "
        "(comma-separated) from the list below that match the search query: {query}\nResults:\n"
    ),
    'generate_summary': (
        "You are a Cybercrime Threat Intelligence Expert. Generate a structured Markdown investigation report "
        "from the dark web OSINT data provided. Include: Source Links, Investigation Artifacts, Key Insights, Next Steps."
    ),
}


def load(name: str) -> str:
    """Load a prompt by name. Returns file content or hardcoded default."""
    path = os.path.join(_PROMPT_DIR, f'{name}.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return _DEFAULTS.get(name, '')
