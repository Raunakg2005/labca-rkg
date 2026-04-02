import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from fpdf import FPDF
from ddgs import DDGS  # Specifically importing DDGS here

# Load environment variables
load_dotenv()

# Set up Gemini 2.5 Flash
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# 1. Search Tool that actively retrieves URLs/Reference Links
@tool
def search_tool(query: str) -> str:
    """Useful for when you need to answer questions about a paper or topic. Returns snippets AND Reference URLs."""
    try:
        results = DDGS().text(query, max_results=4)
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
        
        if not formatted_results:
            return "No results found."
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Search failed: {e}. Try generic knowledge instead."

# 2. PDF Generation Tool that formats the Paper Title and Content cleanly
@tool
def generate_pdf(paper_title: str, text_content: str) -> str:
    """Takes a paper title and a summary string (with references) and saves it as a PDF."""
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Format the provided paper title
        pdf.set_font("Helvetica", style="B", size=16)
        title_clean = str(paper_title).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=title_clean, align='C')
        pdf.ln(10)
        
        # Format the content and references
        pdf.set_font("Helvetica", size=12)
        # multi_cell to handle line breaks naturally
        content_clean = str(text_content).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=content_clean)
        
        # Save the pdf
        output_file = "research_output.pdf"
        pdf.output(output_file)
        return f"Successfully generated PDF report at {output_file}"
    except Exception as e:
        return f"Failed to generate PDF: {str(e)}"

# 3. Initialize the Tool Calling Agent
tools = [search_tool, generate_pdf]
agent_app = create_react_agent(llm, tools=tools)

def run_research_assistant(paper_title: str):
    print(f"Goal: Research Paper '{paper_title}'\n" + "="*50)
    prompt_text = f"""
    Research the following paper or topic: '{paper_title}'. 
    First, use search_tool to find information and specific URLs for this paper/topic. 
    Then, synthesize a comprehensive summary based on the web search. 
    AT THE BOTTOM of your summary, you MUST include a 'References' section containing the URLs you found.
    Finally, use your generate_pdf tool passing the exact parameter `paper_title` and your finalized `text_content` to output a PDF file.
    """
    
    try:
        for chunk in agent_app.stream(
            {"messages": [("user", prompt_text)]},
            stream_mode="values",
        ):
            # Print the trace output as it happens
            chunk["messages"][-1].pretty_print()
            
    except Exception as e:
        print(f"Error during agent execution: {e}")

if __name__ == "__main__":
    print("Welcome to the Agentic Research Assistant!")
    print("This agent uses Google Gemini (LLM), DuckDuckGo (Search Tool), and Python FPDF to write complete paper reviews.")
    user_topic = input("Enter the title of the paper or topic you want me to review: ")
    run_research_assistant(user_topic)
