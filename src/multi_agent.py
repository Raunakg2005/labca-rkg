"""
multi_agent.py — Multi-Agent Research Pipeline

Architecture:
    Researcher Agent  →  Summarizer Agent  →  Critic Agent  →  PDF

Each agent is a specialized LLM node in a LangGraph StateGraph.
The Critic can request one revision loop if quality is insufficient.
"""

import os
from typing import TypedDict, Literal
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# Re-use the shared tools AND logger from app.py
from app import search_tool, generate_pdf, slugify, start_logging, stop_logging

# ---------------------------------------------------------------------------
# Shared LLM
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------
class ResearchState(TypedDict):
    topic: str
    raw_findings: str       # Output of Researcher
    structured_summary: str # Output of Summarizer
    references: str         # URLs extracted during research
    critique: str           # Output of Critic
    revision_count: int     # Guard: max 1 revision loop
    final_summary: str      # Approved summary ready for PDF
    pdf_path: str           # Final output path


# ---------------------------------------------------------------------------
# Node 1 — Researcher Agent
# ---------------------------------------------------------------------------
def researcher_node(state: ResearchState) -> dict:
    """
    Conducts 3 targeted searches on the topic and returns raw findings.
    """
    topic = state["topic"]
    print("\n" + "─"*60)
    print("🔍  [RESEARCHER]  Searching for information...")
    print("─"*60)

    # Build 3 search queries for broad + deep coverage
    query_prompt = f"""
You are a research specialist. Generate exactly 3 targeted search queries
for the topic: "{topic}".
Return ONLY the 3 queries, one per line. No numbering, no explanation.
"""
    query_response = llm.invoke([HumanMessage(content=query_prompt)])
    queries = [q.strip() for q in query_response.content.strip().splitlines() if q.strip()][:3]

    all_results = []
    all_urls = []

    for q in queries:
        print(f"  → Searching: {q}")
        result = search_tool.invoke({"query": q})
        all_results.append(f"[Query: {q}]\n{result}")

        # Extract URLs from result lines
        for line in result.splitlines():
            if line.startswith("URL:"):
                url = line.replace("URL:", "").strip()
                if url and url not in all_urls:
                    all_urls.append(url)

    raw_findings = "\n\n".join(all_results)
    references = "\n".join(all_urls)

    print(f"\n  ✅ Collected {len(all_urls)} unique references from {len(queries)} searches.")

    return {
        "raw_findings": raw_findings,
        "references": references,
    }


# ---------------------------------------------------------------------------
# Node 2 — Summarizer Agent
# ---------------------------------------------------------------------------
def summarizer_node(state: ResearchState) -> dict:
    """
    Synthesizes raw findings into a well-structured multi-section summary.
    """
    print("\n" + "─"*60)
    print("📝  [SUMMARIZER]  Synthesizing findings...")
    print("─"*60)

    system_prompt = SystemMessage(content="""
You are an expert academic summarizer. Your task is to transform raw web search
results into a clear, structured, and thorough research summary.

Structure your output with these sections:
1. Overview
2. Key Findings / Advancements
3. Applications & Implications
4. Conclusion

Write in formal academic prose. Do NOT include any URLs or references in this
output — those will be added separately. Aim for 400–600 words.
""")

    user_prompt = HumanMessage(content=f"""
Topic: {state['topic']}

Raw Research Findings:
{state['raw_findings']}

Write the structured summary now.
""")

    response = llm.invoke([system_prompt, user_prompt])
    summary = response.content.strip()
    print(f"  ✅ Summary generated ({len(summary.split())} words).")

    return {"structured_summary": summary}


# ---------------------------------------------------------------------------
# Node 3 — Critic Agent
# ---------------------------------------------------------------------------
def critic_node(state: ResearchState) -> dict:
    """
    Reviews the summary for quality. Returns 'approve' or 'revise' + feedback.
    """
    print("\n" + "─"*60)
    print("🧐  [CRITIC]  Reviewing summary quality...")
    print("─"*60)

    system_prompt = SystemMessage(content="""
You are a strict quality-control expert for research reports.
Evaluate the given summary and respond in exactly this format:

VERDICT: approve   (if the summary is thorough and well-structured)
      OR
VERDICT: revise

FEEDBACK: <one paragraph of specific, actionable feedback — even if approving>
""")

    user_prompt = HumanMessage(content=f"""
Topic: {state['topic']}

Summary to evaluate:
{state['structured_summary']}

Evaluate and respond with VERDICT and FEEDBACK.
""")

    response = llm.invoke([system_prompt, user_prompt])
    critique_text = response.content.strip()

    verdict_line = next(
        (l for l in critique_text.splitlines() if "VERDICT:" in l.upper()), ""
    )
    verdict = "approve" if "approve" in verdict_line.lower() else "revise"

    print(f"  ✅ Critic verdict: {verdict.upper()}")
    print(f"  Feedback: {critique_text[:200]}...")

    return {"critique": critique_text}


# ---------------------------------------------------------------------------
# Node 4 — Reviser Agent  (only runs if Critic says 'revise')
# ---------------------------------------------------------------------------
def reviser_node(state: ResearchState) -> dict:
    """
    Improves the summary based on the Critic's feedback.
    This node runs at most once (revision_count guard).
    """
    print("\n" + "─"*60)
    print("✏️   [REVISER]   Improving summary based on critique...")
    print("─"*60)

    system_prompt = SystemMessage(content="""
You are a senior research writer. Revise the given summary based on the
critic's feedback. Keep the same 4-section structure but improve depth,
clarity, and completeness. Aim for 500–700 words.
""")

    user_prompt = HumanMessage(content=f"""
Topic: {state['topic']}

Original Summary:
{state['structured_summary']}

Critic's Feedback:
{state['critique']}

Write the improved summary now.
""")

    response = llm.invoke([system_prompt, user_prompt])
    revised = response.content.strip()
    print(f"  ✅ Revised summary ready ({len(revised.split())} words).")

    return {
        "structured_summary": revised,
        "revision_count": state.get("revision_count", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Node 5 — PDF Writer
# ---------------------------------------------------------------------------
def pdf_writer_node(state: ResearchState) -> dict:
    """
    Calls the generate_pdf tool with the final approved summary.
    """
    print("\n" + "─"*60)
    print("📄  [PDF WRITER]  Generating final PDF report...")
    print("─"*60)

    result = generate_pdf.invoke({
        "paper_title": state["topic"],
        "summary": state["structured_summary"],
        "references": state.get("references", ""),
    })

    print(f"  ✅ {result}")
    return {"pdf_path": result}


# ---------------------------------------------------------------------------
# Routing Logic
# ---------------------------------------------------------------------------
def route_after_critic(state: ResearchState) -> Literal["reviser", "pdf_writer"]:
    """
    Route to Reviser if the Critic said 'revise' AND we haven't revised yet.
    Otherwise go straight to PDF generation.
    """
    critique = state.get("critique", "")
    revision_count = state.get("revision_count", 0)

    if "VERDICT: revise" in critique.upper() and revision_count < 1:
        return "reviser"
    return "pdf_writer"


# ---------------------------------------------------------------------------
# Build the Graph
# ---------------------------------------------------------------------------
def build_pipeline() -> StateGraph:
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("researcher", researcher_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("critic",     critic_node)
    graph.add_node("reviser",    reviser_node)
    graph.add_node("pdf_writer", pdf_writer_node)

    # Define edges
    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "summarizer")
    graph.add_edge("summarizer", "critic")
    graph.add_conditional_edges("critic", route_after_critic, {
        "reviser":    "reviser",
        "pdf_writer": "pdf_writer",
    })
    graph.add_edge("reviser",    "critic")   # Critic checks revised version once
    graph.add_edge("pdf_writer", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------
def run_multi_agent_pipeline(topic: str) -> tuple[str | None, str]:
    """
    Run the full multi-agent research pipeline for the given topic.
    Returns: (pdf_path, log_path)
    """
    log_path = start_logging(topic)
    print(f"\n{'='*60}")
    print(f"  MULTI-AGENT PIPELINE")
    print(f"  Topic: {topic}")
    print(f"  Log:   {log_path}")
    print(f"{'='*60}")

    pipeline = build_pipeline()

    initial_state: ResearchState = {
        "topic": topic,
        "raw_findings": "",
        "structured_summary": "",
        "references": "",
        "critique": "",
        "revision_count": 0,
        "final_summary": "",
        "pdf_path": "",
    }

    try:
        final_state = pipeline.invoke(initial_state)
    finally:
        stop_logging()

    print(f"\n{'='*60}")
    print(f"  Pipeline complete!")
    pdf_out = final_state.get("pdf_path")
    if pdf_out:
        print(f"  Output: {pdf_out}")
    print(f"  Log saved to: {log_path}")
    print(f"{'='*60}\n")
    
    # Parse the actual file path string from the return text
    if pdf_out and "PDF successfully generated:" in pdf_out:
        pdf_out = pdf_out.split("PDF successfully generated:")[-1].strip()
        
    return pdf_out, log_path
