import os
import re
import logging
import json
import uuid
from datetime import datetime
from typing import List, Tuple, TypedDict, Optional, Annotated
from tqdm import tqdm
from langgraph.graph import StateGraph, END

from .llm_interface import create_llm_and_parser
from .utils import clean_filename, ensure_dir, setup_logger
from langchain_core.prompts import ChatPromptTemplate


class GraphState(TypedDict):
    """
    Represents the state of our graph.
    """
    filepath: str
    output_dir: str
    candidates: List[Tuple[int, str]]
    confirmed_chapters: List[Tuple[int, str]]
    user_confirmed: bool
    auto_confirm: bool
    task_id: str  # Added for unique run identification
    start_time: str # Added to track execution time


class NovelSplitter:
    """
    A robust novel splitter using LangGraph and a detailed logging system.
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None, model_name: str = "gpt-3.5-turbo"):
        """
        Initializes the splitter, sets up logging, and configures the LLM client.
        """
        # Set up the logger. This is the first step.
        self.logger = setup_logger()

        # Initialize the LLM client and parser.
        try:
            self.llm, self.parser = create_llm_and_parser(
                api_key=api_key, base_url=base_url, model_name=model_name
            )
            self.logger.info(f"LLM client initialized. Model: [bold cyan]{model_name}[/bold cyan], Base URL: [bold cyan]{base_url or 'Default'}[/bold cyan]")
        except Exception:
            # If LLM initialization fails, log a critical error and stop.
            self.logger.error("A critical error occurred while initializing the LLM client! Check API keys or network.", exc_info=True)
            raise

        # Define the prompt template for chapter judgment.
        # The curly braces for the JSON example are escaped by doubling them up (e.g., {{...}}).
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a professional novel editor. Your task is to determine if a given line of text is an independent chapter title. Respond ONLY with a JSON object: {{\"is_chapter_title\": boolean}}, with no additional explanations."),
            ("human", "Text line: \"{candidate_line}\"")
        ])

    # --- LangGraph Nodes ---

    def _node_identify_candidates(self, state: GraphState) -> GraphState:
        """Node: Intelligently identifies candidate chapter title lines from the source file."""
        filepath = state["filepath"]
        self.logger.info(f"Node [1]: Identifying candidate chapter lines from '[bold cyan]{os.path.basename(filepath)}[/bold cyan]'...")

        candidates = []
        # A stricter regex pattern for chapter titles.
        chapter_pattern = re.compile(r'^\s*(第[一二三四五六七八九十百千万\d]+章|chapter\s*\d+)', re.IGNORECASE)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line_text = line.strip()
                    if not line_text:
                        continue

                    # Rule 1: Matches explicit patterns like "第x章" or "Chapter x".
                    if chapter_pattern.match(line_text) and len(line_text) < 50:
                        candidates.append((i, line_text))
                        continue

                    # Rule 2: Matches special titles like "序章", "楔子", etc.
                    keywords = ['序章', '序言', '序幕', '楔子', '后记', '番外', 'prologue', 'epilogue']
                    if any(kw in line_text.lower() for kw in keywords) and len(line_text) < 30:
                        candidates.append((i, line_text))
                        continue
        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}", exc_info=True)
            return {**state, "candidates": []}

        unique_candidates = sorted(list(set(candidates)), key=lambda x: x[0])
        self.logger.info(f"[green]Identification complete. Found {len(unique_candidates)} candidate lines.[/green]")
        return {**state, "candidates": unique_candidates}

    def _node_confirm_with_llm(self, state: GraphState) -> GraphState:
        """Node: Uses the LLM to confirm if each candidate line is a true chapter title."""
        self.logger.info("Node [2]: Invoking LLM for precise chapter confirmation...")
        candidates = state["candidates"]
        confirmed = []

        for line_num, text in tqdm(candidates, desc="LLM Confirmation Progress"):
            self.logger.debug(f"Processing line {line_num+1}: '{text}'")
            try:
                # Manually construct the chain of operations for robustness.
                prompt_value = self.prompt_template.invoke({"candidate_line": text})
                response_message = self.llm.invoke(prompt_value)

                # Get the raw string content from the response.
                raw_content = response_message.content
                self.logger.debug(f"LLM raw response for line {line_num+1}: {raw_content}")

                # Manually parse the JSON string, making the process robust to non-compliant API responses.
                result = json.loads(raw_content)

                if result.get("is_chapter_title"):
                    confirmed.append((line_num, text))
                    self.logger.debug(f"Line {line_num+1} confirmed as a chapter title.")

            except Exception as e:
                # This is the critical part for debugging. It logs the error with full context.
                log_message = f"Failed to process line -> Line No: {line_num+1}, Content: '{text}'"
                self.logger.error(log_message, exc_info=True)

        self.logger.info(f"[green]LLM confirmation complete. Confirmed {len(confirmed)} chapters.[/green]")
        return {**state, "confirmed_chapters": confirmed}

    def _node_prompt_user(self, state: GraphState) -> GraphState:
        """Node: Generates a preview table and prompts the user for confirmation."""
        if state["auto_confirm"]:
            self.logger.info("Node [3]: Skipping user prompt (auto_confirm is True).")
            return {**state, "user_confirmed": True}

        self.logger.info("Node [3]: Generating preview for user review.")

        from rich.table import Table
        from rich.console import Console

        table = Table(title=f"Novel Chapter Split Preview - {os.path.basename(state['filepath'])}", show_header=True, header_style="bold magenta")
        table.add_column("No.", style="dim", width=6)
        table.add_column("Chapter Title", style="bold")
        table.add_column("Original Line No.", justify="right")
        for i, (line_num, title) in enumerate(state["confirmed_chapters"]):
            table.add_row(str(i + 1), title, str(line_num + 1))

        # Use a dedicated Rich Console to print complex objects like tables.
        Console().print(table)

        try:
            answer = input("Please review the list above. Proceed with splitting? (y/n): ").lower()
            confirmed = answer in ['y', 'yes']
            self.logger.info(f"User decision: {'Proceed' if confirmed else 'Cancel'}")
            return {**state, "user_confirmed": confirmed}
        except KeyboardInterrupt:
            self.logger.warning("User cancelled the operation via KeyboardInterrupt.")
            return {**state, "user_confirmed": False}

    def _node_execute_split(self, state: GraphState):
        """
        Node: Executes the file splitting and creates a metadata file.
        """
        self.logger.info("Node [4]: Executing file split and metadata generation...")
        filepath = state["filepath"]
        chapters = state["confirmed_chapters"]
        output_dir = state["output_dir"]
        task_id = state["task_id"]
        start_time = state["start_time"]

        # Define new directory structure
        split_data_path = os.path.join(output_dir, "splitdata", task_id)
        metadata_path = os.path.join(output_dir, "metadata")

        try:
            ensure_dir(split_data_path)
            ensure_dir(metadata_path)

            with open(filepath, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except Exception:
            self.logger.error(f"Failed to read source file or create directories.", exc_info=True)
            return state

        # Prepare lists for metadata
        relative_paths = []
        chapter_titles = []

        # Define chapter indices before the loop to avoid NameError
        chapter_indices = [chap[0] for chap in chapters]

        for i, (line_num, title) in enumerate(chapters):
            start_line = line_num
            end_line = chapter_indices[i + 1] if i + 1 < len(chapters) else len(all_lines)
            content = all_lines[start_line:end_line]

            # Use a simple sequential filename
            filename = f"{i+1}.txt"
            full_path = os.path.join(split_data_path, filename)

            # Define relative path from metadata file to split data file
            relative_path = os.path.join("..", "splitdata", task_id, filename)

            try:
                with open(full_path, 'w', encoding='utf-8') as out_f:
                    out_f.writelines(content)
                relative_paths.append(relative_path.replace("\\", "/")) # Use forward slashes for consistency
                chapter_titles.append(title)
            except Exception:
                self.logger.error(f"Failed to write chapter file '{full_path}'.", exc_info=True)

        # Create metadata content
        end_time = datetime.now().isoformat()
        metadata_content = {
            "source_filename": os.path.basename(filepath),
            "split_files": relative_paths,
            "chapter_titles": chapter_titles,
            "task_id": task_id,
            "start_time": start_time,
            "end_time": end_time,
        }

        # Write metadata file
        metadata_filename = f"{task_id}-metadata.json"
        metadata_filepath = os.path.join(metadata_path, metadata_filename)
        try:
            with open(metadata_filepath, 'w', encoding='utf-8') as meta_f:
                json.dump(metadata_content, meta_f, ensure_ascii=False, indent=4)
            self.logger.info(f"Metadata file created at [bold cyan]{metadata_filepath}[/bold cyan]")
        except Exception:
            self.logger.error(f"Failed to write metadata file '{metadata_filepath}'.", exc_info=True)

        self.logger.info(f"[bold green]Split complete! Data in '{split_data_path}', Metadata in '{metadata_path}'.[/bold green]")
        return state

    # --- LangGraph Edges (Conditional Routing) ---

    def _should_continue_after_llm(self, state: GraphState) -> str:
        """Edge: Decides whether to proceed to user prompt or end the workflow."""
        if len(state["confirmed_chapters"]) > 0:
            return "continue_to_prompt"
        else:
            self.logger.warning("LLM did not confirm any chapters. Ending workflow.")
            return "end"

    def _should_split_after_prompt(self, state: GraphState) -> str:
        """Edge: Decides whether to execute the split or end based on user input."""
        if state["user_confirmed"]:
            return "continue_to_split"
        else:
            self.logger.info("User chose not to proceed. Ending workflow.")
            return "end"

    def run(self, filepath: str, output_dir: Optional[str] = None, auto_confirm: bool = False):
        """
        Builds and runs the LangGraph workflow to execute the entire splitting process.
        """
        self.logger.info(f"Workflow starting for file: '{filepath}'")
        if not os.path.exists(filepath):
            self.logger.error(f"Input file does not exist: {filepath}")
            return

        if output_dir is None:
            # Default output to a 'results' folder in the current working directory.
            output_dir = os.path.join(os.getcwd(), "results")

        # Define the workflow graph
        workflow = StateGraph(GraphState)

        # Add nodes to the graph
        workflow.add_node("identify_candidates", self._node_identify_candidates)
        workflow.add_node("confirm_with_llm", self._node_confirm_with_llm)
        workflow.add_node("prompt_user", self._node_prompt_user)
        workflow.add_node("execute_split", self._node_execute_split)

        # Set up the edges and entry point
        workflow.set_entry_point("identify_candidates")
        workflow.add_edge("identify_candidates", "confirm_with_llm")
        workflow.add_conditional_edges(
            "confirm_with_llm",
            self._should_continue_after_llm,
            {"continue_to_prompt": "prompt_user", "end": END}
        )
        workflow.add_conditional_edges(
            "prompt_user",
            self._should_split_after_prompt,
            {"continue_to_split": "execute_split", "end": END}
        )
        workflow.add_edge("execute_split", END)

        # Compile the graph into a runnable app
        app = workflow.compile()

        # Define the initial state and run the workflow
        initial_state = {
            "filepath": filepath,
            "output_dir": output_dir,
            "candidates": [],
            "confirmed_chapters": [],
            "user_confirmed": False,
            "auto_confirm": auto_confirm,
            "task_id": str(uuid.uuid4()),
            "start_time": datetime.now().isoformat()
        }

        try:
            app.invoke(initial_state)
            self.logger.info("Workflow finished successfully.")
        except Exception:
            self.logger.critical("An unhandled exception occurred during workflow execution.", exc_info=True)

