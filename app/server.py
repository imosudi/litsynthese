import os
import uuid
import json
import logging
import shutil
import time
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from app.parser import AcademicPaperParser
from app.llm import AcademicLLMService

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("litsynthese.server")

app = FastAPI(title="LitSynthese API", version="1.0.0")

# Base directory for all projects
PROJECTS_BASE_DIR = config.PROJECTS_BASE_DIR
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
    model: str = "gemini-2.5-flash"

class ProjectCreate(BaseModel):
    name: str

def migrate_existing_data():
    """Migrates legacy data and converts any 'default' project to a standard UUID-based project."""
    os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)
    
    # 1. Convert legacy 'default' project folder to a UUID project
    old_default_dir = os.path.join(PROJECTS_BASE_DIR, "default")
    if os.path.exists(old_default_dir) and os.path.isdir(old_default_dir):
        new_project_id = str(uuid.uuid4())
        new_project_dir = os.path.join(PROJECTS_BASE_DIR, new_project_id)
        try:
            # Load metadata if it exists to preserve name
            meta_path = os.path.join(old_default_dir, "metadata.json")
            name = "Machine Learning Reviews"
            created_at = time.time()
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if meta.get("name") and meta.get("name") != "Default Project":
                        name = meta.get("name")
                    created_at = meta.get("created_at", created_at)
            
            # Rename the folder
            os.rename(old_default_dir, new_project_dir)
            
            # Write updated metadata
            new_meta_path = os.path.join(new_project_dir, "metadata.json")
            with open(new_meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": new_project_id,
                    "name": name,
                    "created_at": created_at
                }, f, indent=2)
            logger.info(f"Successfully migrated old 'default' project to UUID project '{name}' ({new_project_id})")
        except Exception as e:
            logger.error(f"Error migrating 'default' project folder: {e}")

    # 2. Check if we need to initialize a fresh project
    existing_projects = []
    for item in os.listdir(PROJECTS_BASE_DIR):
        item_path = os.path.join(PROJECTS_BASE_DIR, item)
        if os.path.isdir(item_path):
            meta_path = os.path.join(item_path, "metadata.json")
            if os.path.exists(meta_path):
                existing_projects.append(item)

    if not existing_projects:
        # Create initial project
        new_id = str(uuid.uuid4())
        new_dir = os.path.join(PROJECTS_BASE_DIR, new_id)
        os.makedirs(os.path.join(new_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(new_dir, "processed"), exist_ok=True)
        meta = {
            "id": new_id,
            "name": "Machine Learning Reviews",
            "created_at": time.time()
        }
        with open(os.path.join(new_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        logger.info(f"Initialized new project '{meta['name']}' ({new_id})")
        existing_projects.append(new_id)

    # 3. Migrate any legacy unassigned uploads/processed files from root data/ to the first project
    target_project_id = existing_projects[0]
    target_dir = os.path.join(PROJECTS_BASE_DIR, target_project_id)
    target_uploads = os.path.join(target_dir, "uploads")
    target_processed = os.path.join(target_dir, "processed")

    base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    legacy_uploads = os.path.join(base_data_dir, "uploads")
    legacy_processed = os.path.join(base_data_dir, "processed")

    os.makedirs(target_uploads, exist_ok=True)
    os.makedirs(target_processed, exist_ok=True)

    if os.path.exists(legacy_uploads) and os.path.isdir(legacy_uploads):
        for f_name in os.listdir(legacy_uploads):
            src = os.path.join(legacy_uploads, f_name)
            dst = os.path.join(target_uploads, f_name)
            if os.path.isfile(src):
                try:
                    os.rename(src, dst)
                except Exception as e:
                    logger.warning(f"Failed to migrate upload file {f_name}: {e}")

    if os.path.exists(legacy_processed) and os.path.isdir(legacy_processed):
        for f_name in os.listdir(legacy_processed):
            src = os.path.join(legacy_processed, f_name)
            dst = os.path.join(target_processed, f_name)
            if os.path.isfile(src):
                try:
                    os.rename(src, dst)
                except Exception as e:
                    logger.warning(f"Failed to migrate processed file {f_name}: {e}")

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

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve index.html directly from templates/ folder."""
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates", "index.html"))
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="index.html template not found.")
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

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
                    
    # If no projects exist, initialize a new default one on the fly
    if not projects:
        project_id = str(uuid.uuid4())
        project_dir = os.path.join(PROJECTS_BASE_DIR, project_id)
        os.makedirs(os.path.join(project_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "processed"), exist_ok=True)
        meta = {
            "id": project_id,
            "name": "Machine Learning Reviews",
            "created_at": time.time()
        }
        with open(os.path.join(project_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        projects.append(meta)
        
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
async def upload_paper(project_id: str, model: str = "gemini-2.5-flash", file: UploadFile = File(...)):
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
            full_text=full_text,
            model=model
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
        query=request.query,
        model=request.model
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
Generated automatically by LitSynthese.
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
