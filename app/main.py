import os
import uuid
import json
import logging
import shutil
import time
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.parser import AcademicPaperParser
from app.llm import AcademicLLMService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review_n_summary.main")

app = FastAPI(title="review_n_summary API", version="1.0.0")

# Base directory for all projects
PROJECTS_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "projects"))
os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)

# Initialise LLM Service
llm_service = AcademicLLMService()

# Models
class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage]

class ProjectCreate(BaseModel):
    name: str

def migrate_existing_data():
    """Migrates any existing legacy data into a default project folder."""
    default_project_id = "default"
    default_project_name = "Default Project"
    
    default_dir = os.path.join(PROJECTS_BASE_DIR, default_project_id)
    default_uploads = os.path.join(default_dir, "uploads")
    default_processed = os.path.join(default_dir, "processed")
    
    legacy_uploads = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))
    legacy_processed = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
    
    os.makedirs(default_uploads, exist_ok=True)
    os.makedirs(default_processed, exist_ok=True)
    
    meta_path = os.path.join(default_dir, "metadata.json")
    if not os.path.exists(meta_path):
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "id": default_project_id,
                "name": default_project_name,
                "created_at": time.time()
            }, f, indent=2)
            
    # Migrate uploads
    if os.path.exists(legacy_uploads):
        for f_name in os.listdir(legacy_uploads):
            src = os.path.join(legacy_uploads, f_name)
            dst = os.path.join(default_uploads, f_name)
            if os.path.isfile(src):
                try:
                    os.rename(src, dst)
                except Exception as e:
                    logger.warning(f"Failed to migrate upload file {f_name}: {e}")
                    
    # Migrate processed
    if os.path.exists(legacy_processed):
        for f_name in os.listdir(legacy_processed):
            src = os.path.join(legacy_processed, f_name)
            dst = os.path.join(default_processed, f_name)
            if os.path.isfile(src):
                try:
                    os.rename(src, dst)
                except Exception as e:
                    logger.warning(f"Failed to migrate processed file {f_name}: {e}")
                    
    # Cleanup empty folders
    try:
        if os.path.exists(legacy_uploads) and not os.listdir(legacy_uploads):
            os.rmdir(legacy_uploads)
        if os.path.exists(legacy_processed) and not os.listdir(legacy_processed):
            os.rmdir(legacy_processed)
    except Exception as e:
        logger.warning(f"Failed to clean up legacy folders: {e}")

# Initialise default project on startup
migrate_existing_data()

def get_project_dirs(project_id: str) -> tuple[str, str]:
    """Helper to get safe project directories and create them if needed."""
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid project ID.")
        
    project_dir = os.path.join(PROJECTS_BASE_DIR, clean_id)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found.")
        
    uploads_dir = os.path.join(project_dir, "uploads")
    processed_dir = os.path.join(project_dir, "processed")
    
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    return uploads_dir, processed_dir

@app.get("/")
async def root_redirect():
    """Redirect root access to static index.html."""
    return RedirectResponse(url="/static/index.html")

# Project management endpoints
@app.get("/api/projects")
async def list_projects():
    """Lists all available review projects."""
    projects = []
    for item in os.listdir(PROJECTS_BASE_DIR):
        item_path = os.path.join(PROJECTS_BASE_DIR, item)
        if os.path.isdir(item_path):
            meta_path = os.path.join(item_path, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        projects.append(meta)
                except Exception as e:
                    logger.error(f"Error reading project metadata for {item}: {e}")
    # Sort projects by creation time
    projects.sort(key=lambda x: x.get("created_at", 0))
    return projects

@app.post("/api/projects")
async def create_project(req: ProjectCreate):
    """Creates a new isolated review project."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty.")
        
    project_id = str(uuid.uuid4())
    project_dir = os.path.join(PROJECTS_BASE_DIR, project_id)
    
    os.makedirs(os.path.join(project_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "processed"), exist_ok=True)
    
    meta = {
        "id": project_id,
        "name": name,
        "created_at": time.time()
    }
    
    with open(os.path.join(project_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    return meta

@app.delete("/api/project/{project_id}")
async def delete_project(project_id: str):
    """Deletes a review project and all its uploaded papers/summaries."""
    if project_id == "default":
        raise HTTPException(status_code=400, detail="The default project cannot be deleted.")
        
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid project ID.")
        
    project_dir = os.path.join(PROJECTS_BASE_DIR, clean_id)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found.")
        
    try:
        shutil.rmtree(project_dir)
        logger.info(f"Deleted project {clean_id}")
        return {"status": "success", "message": f"Project {clean_id} deleted."}
    except Exception as e:
        logger.exception("Error deleting project directory")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

# Isolated paper endpoints
@app.post("/api/project/{project_id}/upload")
async def upload_paper(project_id: str, file: UploadFile = File(...)):
    """Receives PDF file, parses sections, generates LLM summary, caches, and returns analysis ID."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    uploads_dir, processed_dir = get_project_dirs(project_id)
    
    paper_id = str(uuid.uuid4())
    pdf_path = os.path.join(uploads_dir, f"{paper_id}.pdf")
    
    try:
        # Save uploaded PDF
        with open(pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        logger.info(f"Saved PDF to {pdf_path}. Commencing extraction...")
        
        # Parse PDF
        parser = AcademicPaperParser(pdf_path)
        parsed_data = parser.parse()
        
        # Generate summary and critique
        logger.info("Requesting academic analysis from LLM service...")
        
        # Gather full clean text for global summary
        full_text = ""
        for pg in parser.pages_text:
            full_text += pg["clean_text"] + " "
            
        analysis = llm_service.analyse_paper(
            title=parsed_data["metadata"]["title"],
            authors=parsed_data["metadata"]["authors"],
            full_text=full_text
        )
        
        # Combine parsed structure + summary analysis
        result = {
            "id": paper_id,
            "filename": file.filename,
            "metadata": parsed_data["metadata"],
            "sections": parsed_data["sections"],
            "references": parsed_data["references"],
            "analysis": analysis
        }
        
        # Save JSON output
        result_path = os.path.join(processed_dir, f"{paper_id}.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Paper {paper_id} successfully parsed and analysed inside project {project_id}.")
        return {"id": paper_id, "metadata": parsed_data["metadata"], "analysis": analysis}
        
    except Exception as e:
        logger.exception("Error processing PDF upload")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/api/project/{project_id}/papers")
async def list_papers(project_id: str):
    """Lists all successfully processed papers within a specific project."""
    _, processed_dir = get_project_dirs(project_id)
    papers = []
    for filename in os.listdir(processed_dir):
        if filename.endswith(".json"):
            try:
                path = os.path.join(processed_dir, filename)
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    papers.append({
                        "id": data["id"],
                        "filename": data["filename"],
                        "title": data["metadata"]["title"],
                        "authors": data["metadata"]["authors"],
                        "year": data["metadata"]["year"],
                        "pages_count": data["metadata"]["pages_count"],
                        "keywords": data["analysis"].get("keywords", [])
                    })
            except Exception as e:
                logger.error(f"Error reading summary file {filename}: {e}")
    return papers

@app.get("/api/project/{project_id}/paper/{paper_id}")
async def get_paper(project_id: str, paper_id: str):
    """Retrieves full analysis details of a specific paper inside a project."""
    _, processed_dir = get_project_dirs(project_id)
    
    clean_paper_id = "".join(c for c in paper_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_paper_id:
        raise HTTPException(status_code=400, detail="Invalid paper ID.")
        
    path = os.path.join(processed_dir, f"{clean_paper_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Paper analysis not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/project/{project_id}/paper/{paper_id}/chat")
async def chat_paper(project_id: str, paper_id: str, request: ChatRequest):
    """Asks a question about the paper in a context-grounded conversation."""
    _, processed_dir = get_project_dirs(project_id)
    
    clean_paper_id = "".join(c for c in paper_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_paper_id:
        raise HTTPException(status_code=400, detail="Invalid paper ID.")
        
    path = os.path.join(processed_dir, f"{clean_paper_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
    
    reply = llm_service.chat_about_paper(
        title=data["metadata"]["title"],
        sections=data["sections"],
        chat_history=history_dicts,
        query=request.query
    )
    
    return {"reply": reply}

@app.get("/api/project/{project_id}/paper/{paper_id}/export")
async def export_paper_summary(project_id: str, paper_id: str):
    """Exports structured paper analysis as a markdown file."""
    _, processed_dir = get_project_dirs(project_id)
    
    clean_paper_id = "".join(c for c in paper_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_paper_id:
        raise HTTPException(status_code=400, detail="Invalid paper ID.")
        
    path = os.path.join(processed_dir, f"{clean_paper_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    meta = data["metadata"]
    analysis = data["analysis"]
    
    md_content = f"""# Academic Synthesis & Critical Review

## Paper Metadata
* **Title:** {meta['title']}
* **Authors:** {meta['authors']}
* **Year:** {meta['year']}
* **Pages:** {meta['pages_count']}
* **Keywords:** {", ".join(analysis.get('keywords', []))}

---

## 1. Executive Synopsis
{analysis.get('synopsis', 'No synopsis available.')}

---

## 2. Key Contributions
{chr(10).join(f"* {c}" for c in analysis.get('contributions', []))}

---

## 3. Methodology & Experimental Framework
{analysis.get('methodology', 'No methodology details available.')}

---

## 4. Critical Review & Limitations
{chr(10).join(f"* {crit}" for crit in analysis.get('critical_review', []))}

---

## 5. Potential Future Work
{chr(10).join(f"* {f}" for f in analysis.get('future_work', []))}

---
Generated automatically by review_n_summary.
"""
    clean_title = "".join(c for c in meta["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
    clean_title = clean_title.replace(" ", "_")[:50]
    filename = f"Summary_{clean_title}.md"
    
    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Mount static files folder
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
