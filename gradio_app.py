import gradio as gr
import vertexai
from vertexai import agent_engines
import os
import base64
import tempfile
from fpdf import FPDF
from dotenv import load_dotenv

print("--- Starting Gradio App v17 ---")
load_dotenv(override=True)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set in .env")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_RESOURCE_ID = os.getenv("AGENT_RESOURCE_ID")
if not AGENT_RESOURCE_ID:
    raise ValueError("AGENT_RESOURCE_ID environment variable is not set in .env")
AGENT_RESOURCE_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_RESOURCE_ID}"




vertexai.init(project=PROJECT_ID, location=LOCATION)

try:
    print(f"Connecting to: {AGENT_RESOURCE_NAME}")
    agent = agent_engines.get(AGENT_RESOURCE_NAME)
    print("✅ SDK Connection Established.")
except Exception as e:
    print(f"❌ SDK Error: {e}")
    agent = None

def get_pdf_html(file_path):
    if not file_path or not file_path.lower().endswith(".pdf"):
        return "<div style='color:gray; padding:20px;'>No PDF preview available.</div>"
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        return f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" style="border:none;"></iframe>'
    except:
        return "<div style='color:red;'>Failed to load PDF preview.</div>"

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    clean_text = text.replace("#", "").replace("*", "").replace("`", "")
    pdf.multi_cell(0, 10, clean_text)
    temp_path = os.path.join(tempfile.gettempdir(), "analysis_report.pdf")
    pdf.output(temp_path)
    return temp_path

def analyze(message, files):
    if not agent: yield "Agent not connected.", "", gr.update(visible=False), gr.update(); return
    
    print(f"\n--- Request received ---")
    
    # Hide download button at the start of every new request
    yield "*🔍 Thinking...*", gr.update(), gr.update(visible=False), gr.update()
    
    parts = [{"text": message if message else "Analyze the contract."}]
    pdf_html = ""
    if files:
        file_list = files if isinstance(files, list) else [files]
        print(f"Processing {len(file_list)} uploaded files...")
        
        for f in file_list:
            file_path = f if isinstance(f, str) else getattr(f, "name", str(f))
            if file_path.lower().endswith(".pdf") and not pdf_html:
                pdf_html = get_pdf_html(file_path)
            with open(file_path, "rb") as b:
                data = b.read()
            parts.append({"inline_data": {"data": base64.b64encode(data).decode("utf-8"), "mime_type": "application/pdf" if file_path.lower().endswith(".pdf") else "application/octet-stream"}})
            print(f"  Encoded: {os.path.basename(file_path)}")
            
    full_text = ""
    report_started = False
    clean_report_text = ""
    try:
        print(f"Calling agent.stream_query...")
        for event in agent.stream_query(user_id="gradio_user", message={"role": "user", "parts": parts}):
            text_chunk = ""
            if hasattr(event, "text") and event.text: text_chunk = event.text
            elif isinstance(event, dict):
                p_list = event.get("content", {}).get("parts", [])
                for p in p_list:
                    if "text" in p: text_chunk += p["text"]
            full_text += text_chunk
            if "### Executive Summary" in full_text:
                report_started = True
                clean_report_text = full_text[full_text.find("### Executive Summary"):]
            elif any(marker in full_text for marker in ["Contracting Parties:", "Finding:", "SUCCESS: Loaded"]):
                clean_report_text = "*🔍 The Advisor is reviewing your contract... please wait.*"
            else:
                clean_report_text = full_text
            yield clean_report_text, pdf_html, None, gr.update()
        
        if report_started:
            print(f"✅ Success. Clean report length: {len(clean_report_text)}")
            pdf_path = create_pdf(clean_report_text)
            # Explicitly set visible=True for the download button
            yield clean_report_text, pdf_html, gr.update(value=pdf_path, visible=True), gr.update(value="")
        else:
            print(f"✅ Success. Conversational response length: {len(clean_report_text)}")
            yield clean_report_text, pdf_html, None, gr.update(value="")
    except Exception as e:
        print(f"❌ SDK Query Error: {e}")
        yield f"Error: {e}", pdf_html, None, gr.update()

# UI Layout with Tabs (Standard Theme)
with gr.Blocks(title="Intelligent Contract Advisor") as demo:
    gr.Markdown("# Intelligent Contract Advisor")
    
    with gr.Row():
        with gr.Column(scale=1):
            file_in = gr.File(label="Upload Contract", file_count="multiple")
            text_in = gr.Textbox(label="Instructions", placeholder="e.g. Analyze the contract")
            btn = gr.Button("🚀 Run Analysis", variant="primary")
        
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab("📋 Advisor Report"):
                    # Hidden until report is ready
                    pdf_download = gr.File(label="Download Analysis (PDF)", visible=False, height=100)
                    out = gr.Markdown(value="*Report will appear here...*")
                with gr.Tab("📄 Document Preview"):
                    pdf_view = gr.HTML()

    btn.click(fn=analyze, inputs=[text_in, file_in], outputs=[out, pdf_view, pdf_download, text_in])

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=8080, share=False)
