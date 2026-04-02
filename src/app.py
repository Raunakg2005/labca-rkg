import os
import re
import sys
import logging
import warnings
import unicodedata
from datetime import datetime
from dotenv import load_dotenv

# Suppress known deprecation warnings from Pydantic v1 / LangGraph v1 migration
warnings.filterwarnings("ignore", category=UserWarning, message=".*Pydantic V1.*")
warnings.filterwarnings("ignore", message=".*create_react_agent has been moved.*")
warnings.filterwarnings("ignore", message=".*LangGraphDeprecated.*")

# ---------------------------------------------------------------------------
# Startup: load env and validate API key BEFORE importing heavy dependencies
# ---------------------------------------------------------------------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("\n" + "="*60)
    print("  [ERROR] GOOGLE_API_KEY is missing!")
    print("="*60)
    print("  Create a .env file in the project root with:")
    print("    GOOGLE_API_KEY=your_key_here")
    print("  Get a free key at: https://aistudio.google.com/")
    print("="*60 + "\n")
    exit(1)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from fpdf import FPDF
from ddgs import DDGS

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# ---------------------------------------------------------------------------
# Logger — tees all output to a timestamped log file AND the terminal
# ---------------------------------------------------------------------------
class AgentLogger:
    """
    Writes every print() call and agent trace line to both the terminal
    and a text log file (for the 'Agent interaction logs' deliverable).
    """
    def __init__(self, log_path: str):
        self.terminal = sys.stdout
        self.log_file = open(log_path, "w", encoding="utf-8")
        self.log_path = log_path

    def write(self, message: str):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()
        sys.stdout = self.terminal


_active_logger: AgentLogger | None = None


def start_logging(topic: str) -> str:
    """Redirect stdout to both terminal and a log file. Returns the log path."""
    global _active_logger
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(topic) if topic else "session"
    log_path = f"agent_log_{slug}_{timestamp}.txt"
    _active_logger = AgentLogger(log_path)
    sys.stdout = _active_logger
    return log_path


def stop_logging():
    """Close the log file and restore normal stdout."""
    global _active_logger
    if _active_logger:
        _active_logger.close()
        _active_logger = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# Map of common problematic Unicode characters → ASCII-safe equivalents.
# fpdf2's built-in Helvetica font only supports Latin-1 (ISO 8859-1), so any
# character outside that range must be substituted BEFORE passing to the PDF.
_UNICODE_MAP: dict[str, str] = {
    "\u2014": "--",   # em dash  —
    "\u2013": "-",    # en dash  –
    "\u2018": "'",    # left single quote  '
    "\u2019": "'",    # right single quote  '
    "\u201c": '"',    # left double quote  "
    "\u201d": '"',    # right double quote  "
    "\u2026": "...",  # ellipsis  …
    "\u2022": "*",    # bullet  •
    "\u2192": "->",   # right arrow  →
    "\u2190": "<-",   # left arrow  ←
    "\u00d7": "x",    # multiplication sign  ×
    "\u00f7": "/",    # division sign  ÷
    "\u00b0": "deg",  # degree sign  °
    "\u00b1": "+/-",  # plus-minus  ±
    "\u00ae": "(R)",  # registered trademark  ®
    "\u00a9": "(C)",  # copyright  ©
    "\u00e9": "e",    # é
    "\u00e8": "e",    # è
    "\u00ea": "e",    # ê
    "\u00fc": "u",    # ü
    "\u00f6": "o",    # ö
    "\u00e4": "a",    # ä
}


def safe_text(text: str) -> str:
    """Convert text to a PDF-safe Latin-1 string, substituting known Unicode punctuation."""
    text = str(text)
    for char, replacement in _UNICODE_MAP.items():
        text = text.replace(char, replacement)
    # NFKD decomposition handles accented characters; latin-1 replace catches the rest
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("latin-1", "replace").decode("latin-1")


def slugify(text: str) -> str:
    """Convert a topic string into a safe, readable filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:50]


def strip_inline_md(text: str) -> str:
    """Remove inline markdown markers: **bold**, *italic*, `code`."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **bold** -> text
    text = re.sub(r"\*(.+?)\*",     r"\1", text)   # *italic* -> text
    text = re.sub(r"`(.+?)`",       r"\1", text)   # `code`   -> text
    return text.strip()


def render_markdown(pdf: "FPDF", text: str) -> None:
    """
    Render a markdown-formatted string into a fpdf2 PDF object.
    Handles: # / ## / ### headings, - / * bullet points, blank lines,
    and **bold** / *italic* inline markers.
    """
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()

        # ── H1 heading ─────────────────────────────────────────────────────
        if stripped.startswith("# ") and not stripped.startswith("##"):
            heading = safe_text(strip_inline_md(stripped[2:]))
            pdf.ln(4)
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(0, 8, txt=heading)
            # thin underline
            pdf.set_draw_color(160, 160, 160)
            pdf.set_line_width(0.2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)
            pdf.set_text_color(30, 30, 30)

        # ── H2 heading ─────────────────────────────────────────────────────
        elif stripped.startswith("## ") and not stripped.startswith("###"):
            heading = safe_text(strip_inline_md(stripped[3:]))
            pdf.ln(4)
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(0, 8, txt=heading)
            pdf.set_draw_color(180, 180, 180)
            pdf.set_line_width(0.2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)
            pdf.set_text_color(30, 30, 30)

        # ── H3 heading ─────────────────────────────────────────────────────
        elif stripped.startswith("### "):
            heading = safe_text(strip_inline_md(stripped[4:]))
            pdf.ln(3)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 7, txt=heading)
            pdf.ln(1)
            pdf.set_text_color(30, 30, 30)

        # ── Bullet point (- or *) ──────────────────────────────────────────
        elif re.match(r"^[-*]\s+", stripped):
            content = safe_text(strip_inline_md(re.sub(r"^[-*]\s+", "", stripped)))
            pdf.set_font("Helvetica", size=11)
            pdf.set_x(25)  # indent
            pdf.multi_cell(0, 7, txt=f"  *  {content}")

        # ── Blank line → paragraph gap ─────────────────────────────────────
        elif stripped == "":
            pdf.ln(4)

        # ── Normal paragraph text ──────────────────────────────────────────
        else:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 7, txt=safe_text(strip_inline_md(stripped)))
            pdf.ln(1)


# ---------------------------------------------------------------------------
# Tool 1 — Web Search
# ---------------------------------------------------------------------------
@tool
def search_tool(query: str) -> str:
    """
    Search the web for up-to-date information on any topic.
    Returns titles, reference URLs, and text snippets.
    Run multiple targeted queries for best results.
    """
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found for this query. Try a different search term."

        formatted = []
        for r in results:
            formatted.append(
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL:   {r.get('href', 'N/A')}\n"
                f"Info:  {r.get('body', 'N/A')}\n"
            )
        return "\n".join(formatted)

    except Exception as e:
        return (
            f"Search failed ({type(e).__name__}: {e}). "
            "Check your internet connection or try rephrasing the query."
        )


# ---------------------------------------------------------------------------
# Tool 2 — Structured PDF Generator
# ---------------------------------------------------------------------------
@tool
def generate_pdf(paper_title: str, summary: str, references: str) -> str:
    """
    Generate a well-formatted PDF research report.

    Args:
        paper_title: Title of the paper or research topic.
        summary    : The full synthesized multi-paragraph summary / findings.
        references : Newline-separated list of source URLs found during research.

    Returns a message with the path to the saved PDF file.
    """
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        # ── Title ──────────────────────────────────────────────────────────
        pdf.set_font("Helvetica", style="B", size=18)
        pdf.multi_cell(0, 12, txt=safe_text(paper_title), align="C")
        pdf.ln(3)

        # ── Horizontal rule ────────────────────────────────────────────────
        pdf.set_draw_color(30, 30, 30)
        pdf.set_line_width(0.6)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)

        # ── Generated date ─────────────────────────────────────────────────
        pdf.set_font("Helvetica", style="I", size=10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0, 8,
            txt=f"Generated: {datetime.now().strftime('%B %d, %Y  |  %H:%M')}",
            align="C",
            ln=True,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(8)

        # ── Summary & Findings ─────────────────────────────────────────────
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.cell(0, 9, txt="Summary & Findings", ln=True)

        pdf.set_draw_color(120, 120, 120)
        pdf.set_line_width(0.3)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)

        # Render markdown-formatted summary cleanly
        render_markdown(pdf, summary)
        pdf.ln(8)

        # ── References ─────────────────────────────────────────────────────
        if references and references.strip():
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 9, txt="References", ln=True)

            pdf.set_line_width(0.3)
            pdf.set_draw_color(120, 120, 120)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(5)

            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(30, 30, 80)
            for i, ref in enumerate(references.strip().splitlines(), start=1):
                ref = ref.strip()
                if ref:
                    pdf.multi_cell(0, 6, txt=f"[{i}]  {safe_text(ref)}")
                    pdf.ln(2)

        # ── Footer ─────────────────────────────────────────────────────────
        pdf.set_y(-18)
        pdf.set_font("Helvetica", style="I", size=8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, txt="Agentic Research Assistant - Powered by Gemini + LangChain", align="C")

        # ── Save ───────────────────────────────────────────────────────────
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = slugify(paper_title)
        output_file = f"research_{slug}_{timestamp}.pdf"
        pdf.output(output_file)
        return f"PDF successfully generated: {output_file}"

    except Exception as e:
        return f"PDF generation failed ({type(e).__name__}: {e}). Check the inputs and try again."


# ---------------------------------------------------------------------------
# Single-Agent Runner
# ---------------------------------------------------------------------------
tools = [search_tool, generate_pdf]
agent_app = create_react_agent(llm, tools=tools)


def run_research_assistant(paper_title: str) -> None:
    """Run the single ReAct agent to research a topic and generate a PDF."""
    log_path = start_logging(paper_title)
    print(f"\nGoal: Research  '{paper_title}'\n" + "="*60)
    print(f"[LOG] Agent interaction log: {log_path}\n")

    prompt_text = f"""
You are a thorough research assistant. Your goal is to produce a polished PDF report.

Topic: "{paper_title}"

Steps to follow:
1. Run 2-3 targeted searches using search_tool to gather broad and specific information.
2. Synthesize a comprehensive multi-paragraph summary covering:
   - Background / overview
   - Key findings or advancements
   - Applications or implications
   - Conclusion
3. Collect all reference URLs into a newline-separated list.
4. Call generate_pdf with:
   - paper_title = "{paper_title}"
   - summary    = your complete synthesized summary (multiple paragraphs)
   - references = the newline-separated URL list
"""

    try:
        for chunk in agent_app.stream(
            {"messages": [("user", prompt_text)]},
            stream_mode="values",
        ):
            chunk["messages"][-1].pretty_print()

    except KeyboardInterrupt:
        print("\n[Stopped by user]")
    except Exception as e:
        print(f"\n[ERROR] Agent execution failed: {type(e).__name__}: {e}")
        print("Possible causes: invalid API key, network issue, or model timeout.")
    finally:
        stop_logging()
        # Restore stdout before printing to ensure it shows on terminal
        print(f"\n[LOG] Full interaction saved to: {log_path}")


# ---------------------------------------------------------------------------
# Entry Point — Mode Selection
# ---------------------------------------------------------------------------
def prompt_input(prompt_text: str, default: str = "") -> str:
    """Read a line from stdin with fallback for non-interactive environments."""
    try:
        # Flush stdout so the prompt appears before blocking on input
        print(prompt_text, end="", flush=True)
        return sys.stdin.readline().rstrip("\n").strip()
    except EOFError:
        return default


if __name__ == "__main__":
    print("\n" + "="*60)
    print("   Agentic Research Assistant")
    print("   Powered by Gemini  |  LangChain  |  DuckDuckGo")
    print("="*60)
    print("\n  [1] Single Agent  — ReAct (search → summarize → PDF)")
    print("  [2] Multi Agent   — Researcher → Summarizer → Critic → PDF")
    print()

    mode = prompt_input("Choose mode [1/2]: ", default="1")
    if mode not in ("1", "2"):
        mode = "1"

    print()  # blank line for readability
    user_topic = prompt_input("Enter the paper or topic to research: ")
    if not user_topic:
        print("\n[ERROR] No topic entered. Please type a topic and press Enter.")
        exit(1)

    if mode == "2":
        try:
            from multi_agent import run_multi_agent_pipeline
            run_multi_agent_pipeline(user_topic)
        except ImportError:
            print("[ERROR] multi_agent.py not found. Make sure you are running from the src/ directory.")
    else:
        run_research_assistant(user_topic)
