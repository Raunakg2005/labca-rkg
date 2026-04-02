import os
import sys
from flask import Flask, render_template, request, jsonify, send_file

# Resolve the absolute path of the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, "src"))

from multi_agent import run_multi_agent_pipeline

app = Flask(__name__)

# Basic in-memory store for demo purposes 
# (in prod, use Celery + Redis for long-running Tasks, but this is fine for a hack/lab exercise)
latest_run = {
    "pdf_path": None,
    "log_path": None,
    "topic": None
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run_agent():
    data = request.json
    topic = data.get("topic")
    if not topic:
        return jsonify({"success": False, "error": "No topic provided"}), 400
    
    print(f"Flask API received request for topic: {topic}")
    
    try:
        # Run the pipeline (this blocks for ~30 seconds)
        pdf_path, log_path = run_multi_agent_pipeline(topic)
        
        # Save to our basic state store
        latest_run["topic"] = topic
        latest_run["pdf_path"] = pdf_path
        latest_run["log_path"] = log_path
        
        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({"success": False, "error": "Pipeline finished but failed to write PDF."}), 500
        
        return jsonify({
            "success": True, 
            "pdf_path": pdf_path,
            "log_path": log_path,
            "filename": os.path.basename(pdf_path)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/download/pdf")
def download_pdf():
    pdf_path = latest_run["pdf_path"]
    if not pdf_path:
        return "PDF not found", 404
        
    # Anchor to root explicitly
    abs_path = os.path.join(PROJECT_ROOT, pdf_path)
    if not os.path.exists(abs_path):
        return "PDF not found on disk", 404
    return send_file(abs_path, as_attachment=True)

@app.route("/download/log")
def download_log():
    log_path = latest_run["log_path"]
    if not log_path:
        return "Log not found", 404
        
    # Anchor to root explicitly
    abs_path = os.path.join(PROJECT_ROOT, log_path)
    if not os.path.exists(abs_path):
        return "Log not found on disk", 404
    return send_file(abs_path, as_attachment=True, mimetype="text/plain")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🚀 Starting Web UI for Agentic AI Assistant")
    print("  🌍 Open http://127.0.0.1:5000 in your browser")
    print("="*60 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
