# novel_splitter/__init__.py
"""
A robust tool to split novel text files into chapters using LLMs
with a human-in-the-loop confirmation step.
"""
__version__ = "0.1.0"

from .core import NovelSplitter
def main() -> None:
    print("Hello from novel-splitter!")
