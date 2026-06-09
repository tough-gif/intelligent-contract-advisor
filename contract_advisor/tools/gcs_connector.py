"""Tool for fetching and parsing contracts from Google Cloud Storage"""

import io
import logging
import os
import pypdf
import docx
from google.cloud import storage
from google.adk.tools import ToolContext
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _parse_content(byte_content: bytes, file_name: str) -> str:
    """Helper to extract text from various file formats."""
    text_content = ""
    file_ext = file_name.lower()
    try:
        if file_ext.endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(io.BytesIO(byte_content))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted: text_content += extracted + "\n"
        elif file_ext.endswith(".docx"):
            doc = docx.Document(io.BytesIO(byte_content))
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        else:
            text_content = byte_content.decode('utf-8')
    except Exception as e:
        logger.error(f"Error parsing {file_name}: {e}")
        return f"[ERROR PARSING FILE: {e}]"
    return text_content

async def fetch_contract_from_gcs(tool_context: ToolContext, file_name: str) -> dict:
    """Fetches and parses a contract from Google Cloud Storage."""
    if not config.contract_bucket_name:
        return {"status": "error", "error_message": "CONTRACT_BUCKET_NAME is not configured."}
    
    try:
        client = storage.Client(project=config.project_id)
        bucket = client.bucket(config.contract_bucket_name)
        blob = bucket.blob(file_name)
        
        if not blob.exists():
            for ext in [".pdf", ".docx", ".txt"]:
                alt_blob = bucket.blob(file_name + ext)
                if alt_blob.exists():
                    blob = alt_blob
                    file_name += ext
                    break
            if not blob.exists():
                tool_context.state["current_contract_text"] = "[NO CONTRACT LOADED IN CONTEXT]"
                return {"status": "error", "error_message": f"File '{file_name}' not found."}

        byte_content = blob.download_as_bytes()
        text_content = _parse_content(byte_content, file_name)
        
        tool_context.state["current_contract_name"] = file_name
        tool_context.state["current_contract_text"] = text_content
        return {"status": "success", "message": f"Loaded '{file_name}'.", "chars": len(text_content)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

async def upload_file_to_gcs(tool_context: ToolContext, local_path: str = None) -> dict:
    """Uploads and IMMEDIATELY INGESTS a contract into context."""
    if not config.contract_bucket_name:
        return {"status": "error", "error_message": "CONTRACT_BUCKET_NAME is not configured."}

    file_name = None
    byte_content = None

    #Check current message parts for attachments first
    session = tool_context.session
    if session and session.events:
        last_user_event = next((e for e in reversed(session.events) if e.author == "user"), None)
        if last_user_event and last_user_event.content and last_user_event.content.parts:
            for part in last_user_event.content.parts:
                if part.file_data:
                    file_name = part.file_data.file_uri
                elif part.inline_data:
                    file_name = "attached_contract.pdf" # Default name
                    byte_content = part.inline_data.data
                
                if file_name and not byte_content:
                    try:
                        artifact = await tool_context.load_artifact(file_name)
                        if hasattr(artifact, "inline_data") and artifact.inline_data:
                            byte_content = artifact.inline_data.data
                        elif isinstance(artifact, bytes):
                            byte_content = artifact
                        if byte_content: break
                    except: file_name = None

    #Fallback to state recorded by callback
    if not byte_content:
        uploaded_files = tool_context.state.get("uploaded_files", [])
        if uploaded_files:
            file_name = uploaded_files[-1]
            try:
                artifact = await tool_context.load_artifact(file_name)
                if hasattr(artifact, "inline_data") and artifact.inline_data:
                    byte_content = artifact.inline_data.data
                elif isinstance(artifact, bytes):
                    byte_content = artifact
            except: pass

    #Fallback to local_path
    if not byte_content and local_path:
        if os.path.exists(local_path):
            file_name = os.path.basename(local_path)
            with open(local_path, "rb") as f: byte_content = f.read()

    if not byte_content or not file_name:
        return {"status": "error", "error_message": "No attachment found."}

    # UPLOAD AND INGEST
    try:
        
        clean_name = file_name.replace("artifact://", "")
        
        client = storage.Client(project=config.project_id)
        bucket = client.bucket(config.contract_bucket_name)
        blob = bucket.blob(clean_name)
        blob.upload_from_string(byte_content)
        
        # INGEST: Automatically parse and set state so the next agent is ready
        text_content = _parse_content(byte_content, clean_name)
        tool_context.state["current_contract_name"] = clean_name
        tool_context.state["current_contract_text"] = text_content
        
        return {
            "status": "success",
            "message": f"Successfully uploaded and ingested '{clean_name}'.",
            "file_name": clean_name
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}