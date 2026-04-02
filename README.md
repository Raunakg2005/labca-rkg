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

- **Framework:** LangChain
- **LLM Engine:** Google Gemini (`gemini-1.5-pro` model via `langchain-google-genai`), accessible for free using Google AI Studio.
- **Tools:** DuckDuckGo Search API, `fpdf2` Python Library.
- **Multi-step reasoning:** The agent is given a complex prompt ("First use search, then synthesize a summary, finally use the PDF generation tool"). It must plan and execute these distinct steps sequentially based on the observations returned from each tool.

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

## Deliverables & Setup Instructions

### Prerequisites
1. Install Python 3.9+
2. Install dependencies: `pip install -r requirements.txt`
3. Rename `.env.example` to `.env` and add your free Google AI Studio API key (`GOOGLE_API_KEY`). Get it at `https://aistudio.google.com/`

### Running the Agent
1. Navigate to the `src` directory.
2. Run the script: `python app.py`
3. Enter your research query when prompted.
4. Watch the agent's Thought/Action/Observation loop in the console.
5. Retrieve your output file at `research_output.pdf`.

