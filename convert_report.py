import markdown
import os

def convert_md_to_html(input_file: str, output_file: str) -> None:
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Note: the standard markdown library doesn't parse Mermaid natively into SVGs,
    # it just leaves them as `<code>` blocks. 
    # But we can inject the Mermaid.js script to render them when the HTML is opened!
    html_body = markdown.markdown(md_text, extensions=['fenced_code', 'tables'])

    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Final Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                padding: 2rem;
                max-width: 900px;
                margin: 0 auto;
                color: #333;
            }}
            h1, h2, h3 {{ color: #2c3e50; }}
            pre, code {{ background: #f4f4f4; border-radius: 4px; padding: 2px 5px; }}
            pre {{ padding: 10px; overflow-x: auto; }}
            /* Hide the raw code text for mermaid blocks initially so it doesn't flash */
            .language-mermaid {{ display: none; }}
        </style>
        
        <!-- Mermaid JS library -->
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true }});
            
            // The python markdown library converts ```mermaid into <code class="language-mermaid">
            // Mermaid.js looks for <div class="mermaid">. Let's convert them so they render.
            document.addEventListener("DOMContentLoaded", () => {{
                document.querySelectorAll('code.language-mermaid').forEach((block) => {{
                    const div = document.createElement('div');
                    div.className = 'mermaid';
                    div.textContent = block.textContent;
                    block.parentNode.replaceWith(div);
                }});
                mermaid.init(undefined, document.querySelectorAll('.mermaid'));
            }});
        </script>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    print(f"✅ Success! Report exported to {output_file}")
    print(f"➡️ Open '{output_file}' in Chrome/Edge and press Ctrl+P to Print and 'Save as PDF'.")
    print(f"   (This ensures the Mermaid architecture diagrams render perfectly into the PDF!)")

if __name__ == "__main__":
    convert_md_to_html("Final_Report.md", "Final_Report.html")
