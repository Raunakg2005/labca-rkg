import os
import shutil

# 1. Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "report_submission")
IMG_DIR = os.path.join(REPORT_DIR, "img")

# Make directories
os.makedirs(IMG_DIR, exist_ok=True)

# 2. Find generated images in the brain folder
brain_folder = r"C:\Users\kjsce_comp75\.gemini\antigravity\brain\8ea1aa71-cd1d-467c-81a6-87552edab1ed"

image_files = [f for f in os.listdir(brain_folder) if f.endswith('.png')]

print("Moving images...")
for img in image_files:
    source_path = os.path.join(brain_folder, img)
    # Simplify the image names
    target_name = "architecture_diagram.png" if "architecture" in img else "tool_flow_diagram.png"
    target_path = os.path.join(IMG_DIR, target_name)
    shutil.copy2(source_path, target_path)
    print(f"  -> Copied to: {target_path}")

# 3. Move the report and convert to the report_submission directory
report_source = os.path.join(BASE_DIR, "Final_Report.md")
report_target = os.path.join(REPORT_DIR, "Final_Report.md")
if os.path.exists(report_source):
    # Rewrite the markdown to use the new relative local images path
    with open(report_source, "r", encoding="utf-8") as f:
        md_text = f.read()
    
    # Replace the absolute paths with relative paths
    import re
    md_text = re.sub(r"!\[System Architecture Diagram\]\(file:///.*?\.png\)", "![System Architecture Diagram](img/architecture_diagram.png)", md_text)
    md_text = re.sub(r"!\[Tool Flow Diagram\]\(file:///.*?\.png\)", "![Tool Flow Diagram](img/tool_flow_diagram.png)", md_text)
    
    with open(report_target, "w", encoding="utf-8") as f:
        f.write(md_text)
    
    # Delete the old one
    os.remove(report_source)
    print(f"\n  -> Moved and updated: {report_target}")

# Move the conversion script as well
conv_source = os.path.join(BASE_DIR, "convert_report.py")
conv_target = os.path.join(REPORT_DIR, "convert_report.py")
if os.path.exists(conv_source):
    shutil.move(conv_source, conv_target)

print("\n✅ Successfully organized files into the `report_submission` folder!")
