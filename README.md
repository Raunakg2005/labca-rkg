# Agentic AI System: Research Assistant Agent

## Academic Lab CA Activity 1

### Group Members:
- Student 1
- Student 2
- Student 3

---

## Part A – Agent Design (Modern View)

### Goal of the Agent
The goal of this Research Assistant Agent is to receive a natural language query about any research topic, autonomously search the internet for relevant, up-to-date information, synthesize the findings into a clear summary, and output a formatted PDF report containing this summary.

### Agent Role
The agent acts as an autonomous knowledge worker. Instead of simply generating text from its pre-training data, it actively researches current information, parses search results, and utilizes a document creation tool to deliver the final product without human intervention during the process.

### Tools Used
This implementation uses the LangChain framework to orchestrate the agent and integrate two primary tools:
1. **DuckDuckGo Web Search Tool:** A free, real-time search engine API used to fetch the latest data on the user's research topic.
2. **Custom PDF Generator Tool (using `fpdf2`):** A custom Python tool that takes the generated text summary from the LLM and formats it into a downloadable PDF document.

### Memory Type
The agent utilizes **Short-term Working Memory (Context Window).** During an execution trace, the agent remembers the original goal, the observations retrieved from the DuckDuckGo search tool, and its own previous "Thoughts" and "Actions". Once the task is completed and the PDF is generated, this episodic memory is cleared for the next unrelated task.

### Planning Strategy
The agent employs the **ReAct (Reason + Act)** prompting strategy. 
- **Thought:** The LLM analyzes the current state and decides what to do next.
- **Action:** The LLM selects a specific tool and provides the necessary input parameters.
- **Observation:** The tool executes and returns the result back to the LLM.
This loop continues until the agent determines it has enough information to fulfill the final goal.

---

## Part B – Implementation (Modern AI Tools)

- **Framework:** LangChain + LangGraph
- **LLM Engine:** Google Gemini (`gemini-2.5-flash` via `langchain-google-genai`), accessible for free using Google AI Studio.
- **Tools:** DuckDuckGo Search API (`duckduckgo-search`), custom PDF Generator (`fpdf2`).
- **Two execution modes** (selectable at runtime):
  - **Mode 1 – Single Agent (ReAct):** A single ReAct agent runs multi-step: search → synthesize → PDF.
  - **Mode 2 – Multi-Agent Pipeline:** A 4-node LangGraph StateGraph where specialized agents collaborate.
- **PDF Output:** Structured sections (Title, date, Summary & Findings, References) with a footer. Filename is unique per run (timestamp + topic slug).

### Observable Agent Behavior (Sample Trace)
When observing the terminal output (Verbose Mode = True in LangChain), we see the interaction loop clearly:

1. **User Goal:** "Research the latest advancements in solid-state batteries and generate a PDF."
2. **Agent Reasoning (Thought):** "I need to find information about the latest advancements in solid-state batteries. I will use the Web Search tool."
3. **Tool Call (Action):** `Action: Web Search`, `Action Input: "latest advancements solid-state batteries 2024"`
4. **Observation:** *[Returns search snippets from DuckDuckGo]*
5. **Agent Reasoning (Thought):** "I have enough information to write a summary. Now I need to use the Generate PDF Report tool to save it."
6. **Tool Call (Action):** `Action: Generate PDF Report`, `Action Input: "[Synthesized Text...]"`
7. **Observation:** "Successfully generated PDF report at research_output.pdf"
8. **Final Answer:** "I have successfully researched solid-state batteries and created a PDF report for you."

---

## Part C – Analysis & Comparison

### Classical Agent (Syllabus) vs Modern Agent (This Activity)

| Feature | Classical Agent (e.g., Expert System) | Modern Agent (LLM-based) |
| :--- | :--- | :--- |
| **Foundation** | **Rule-based:** Operates purely on pre-programmed if-then-else rules and logic trees. | **LLM-driven:** Operates on statistical probabilities and semantic understanding; generates novel behavior. |
| **Logic** | **Static logic:** The execution path is hardcoded by the developer. Cannot handle unexpected edge cases. | **Dynamic planning:** The agent decides its own execution path on the fly using the ReAct framework based on natural language reasoning. |
| **Memory** | **No memory / Hardcoded State:** Typically holds state in rigid programmatic variables without contextual understanding. | **Contextual memory:** Can hold complex, unstructured dialogue, tool outputs, and conversational context within its prompt window. |
| **Reasoning** | **Single-step:** Generally takes an input, runs through a rigid algorithm, and returns an output. | **Multi-step reasoning:** Breaks down complex problems into sub-tasks (e.g., "I must search first, parse the results, formulate a summary, then call the PDF tool"). |

---

## Part D – Multi-Agent Architecture

### Pipeline Overview (`multi_agent.py`)

```
User Topic
    │
    ▼
┌─────────────────┐
│  Researcher     │  → Runs 3 targeted DuckDuckGo searches
│  Agent          │    Returns: raw_findings + reference URLs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summarizer     │  → Synthesizes into 4-section academic summary
│  Agent          │    (Overview, Key Findings, Applications, Conclusion)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Critic         │  → Reviews quality → VERDICT: approve / revise
│  Agent          │
└────────┬────────┘
         │ (if revise, max 1 loop)
         ▼
┌─────────────────┐
│  Reviser        │  → Improves summary based on critique
│  Agent          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PDF Writer     │  → Calls generate_pdf tool → saves timestamped PDF
└─────────────────┘
```

### LangGraph State
The `ResearchState` TypedDict flows through every node:
- `topic` → `raw_findings` → `structured_summary` → `critique` → `final_summary` → `pdf_path`

### Key Design Decisions
- **Conditional edge** after Critic: routes to Reviser or PDF Writer based on verdict.
- **Revision guard** (`revision_count < 1`): prevents infinite revision loops.
- **Shared tools**: both `app.py` and `multi_agent.py` use the same `search_tool` and `generate_pdf`.

---

## Deliverables & Setup Instructions

### File Structure
```
labca-rkg/
├── src/
│   ├── app.py           # Single-agent entry point + mode selector
│   └── multi_agent.py   # Multi-agent LangGraph pipeline
├── requirements.txt
├── .env                 # Your API key (not committed)
├── .env.example         # Template
└── README.md
```

### Prerequisites
1. Python 3.9+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your key:
   ```
   GOOGLE_API_KEY=your_key_here
   ```
   Get a free key at: https://aistudio.google.com/

### Running the Agent
```bash
cd src
python app.py
```
You will be prompted to choose:
- **[1] Single Agent** — ReAct loop (fast, one agent does everything)
- **[2] Multi Agent** — 4-stage pipeline (Researcher → Summarizer → Critic → PDF)

The PDF is saved in the `src/` directory with a unique filename:
`research_<topic-slug>_<timestamp>.pdf`

A full agent interaction log is automatically saved alongside it:
`agent_log_<topic-slug>_<timestamp>.txt`

---

## Part E – Prompts Used

### Single Agent System Prompt (`app.py`)
```
You are a thorough research assistant. Your goal is to produce a polished PDF report.

Topic: "<user topic>"

Steps to follow:
1. Run 2-3 targeted searches using search_tool to gather broad and specific information.
2. Synthesize a comprehensive multi-paragraph summary covering:
   - Background / overview
   - Key findings or advancements
   - Applications or implications
   - Conclusion
3. Collect all reference URLs into a newline-separated list.
4. Call generate_pdf with:
   - paper_title = "<user topic>"
   - summary    = your complete synthesized summary (multiple paragraphs)
   - references = the newline-separated URL list
```

### Multi-Agent Prompts (`multi_agent.py`)

**Researcher Agent** – Auto-generates 3 targeted search queries:
```
You are a research specialist. Generate exactly 3 targeted search queries for
the topic: "<topic>". Return ONLY the 3 queries, one per line.
```

**Summarizer Agent** – Structures findings into 4 sections:
```
You are an expert academic summarizer. Transform raw web search results into a
clear, structured research summary with these sections:
1. Overview
2. Key Findings / Advancements
3. Applications & Implications
4. Conclusion
Write in formal academic prose. Aim for 400–600 words.
```

**Critic Agent** – Quality gate with approve/revise verdict:
```
You are a strict quality-control expert for research reports. Evaluate the
given summary and respond in exactly this format:

VERDICT: approve   (if the summary is thorough and well-structured)
      OR
VERDICT: revise

FEEDBACK: <one paragraph of specific, actionable feedback>
```

**Reviser Agent** – Improves on critique feedback:
```
You are a senior research writer. Revise the given summary based on the
critic's feedback. Keep the same 4-section structure but improve depth,
clarity, and completeness. Aim for 500–700 words.
```

---

## Output Files (per run)

| File | Description |
|---|---|
| `research_<slug>_<timestamp>.pdf` | Formatted research report PDF |
| `agent_log_<slug>_<timestamp>.txt` | Full agent interaction trace log |

