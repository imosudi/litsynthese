import os
import uuid
import json
import logging
import shutil
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

import config
from app.parser import AcademicPaperParser
from app.llm import AcademicLLMService
from app.database import Base, engine, get_db
from app.models import User, Project, AcademicPaper, ChatMessage, UserProfile
from app.auth import get_current_user, create_access_token

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("litsynthese.server")

# Initialise database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LitSynthese API", version="1.0.0")

# Setup Jinja2 templates directory
templates = Jinja2Templates(directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "templates")))

# Base directory for all projects
PROJECTS_BASE_DIR = config.PROJECTS_BASE_DIR
os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)

# Initialise LLM Service
llm_service = AcademicLLMService()

# Pydantic Schemas
class ChatMessageSchema(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessageSchema]
    model: str = "gemini-2.5-flash"

class ProjectCreate(BaseModel):
    name: str

class UserAuth(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    security_question: str
    security_answer: str

class PasswordResetRequest(BaseModel):
    email: str
    security_answer: str
    new_password: str

class SynthesisRequest(BaseModel):
    query: str
    model: str = "gemini-2.5-flash"

# Helpers
def get_project_dirs(project_id: str) -> tuple[str, str]:
    """Helper to get safe project directories and create them if needed."""
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid project ID.")
        
    project_dir = os.path.join(PROJECTS_BASE_DIR, clean_id)
    uploads_dir = os.path.join(project_dir, "uploads")
    processed_dir = os.path.join(project_dir, "processed")
    
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    return uploads_dir, processed_dir

def get_user_project(project_id: str, user_id: int, db: Session) -> Project:
    """Helper to retrieve a project, validating ownership for multi-tenant isolation."""
    clean_id = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
    proj = db.query(Project).filter(Project.id == clean_id, Project.user_id == user_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized access.")
    return proj

# Authentication Endpoints
@app.post("/api/auth/register")
def register_user(auth_req: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user and automatically initialises their first default project."""
    email = auth_req.email.strip().lower()
    password = auth_req.password
    security_q = auth_req.security_question.strip()
    security_a = auth_req.security_answer.strip()
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password cannot be empty.")
    if not security_q or not security_a:
        raise HTTPException(status_code=400, detail="Security question and answer are required.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
        
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
        
    # Create user
    hashed_pwd = User.hash_password(password)
    hashed_ans = User.hash_security_answer(security_a)
    new_user = User(
        email=email,
        hashed_password=hashed_pwd,
        security_question=security_q,
        hashed_security_answer=hashed_ans
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": new_user.email})
    return {"access_token": token, "token_type": "bearer", "email": new_user.email}

@app.post("/api/auth/login")
def login_user(auth_req: UserAuth, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues a JWT token."""
    email = auth_req.email.strip().lower()
    password = auth_req.password
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.verify_password(password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
        
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "email": user.email}

@app.get("/api/auth/forgot-password/question")
def get_forgot_password_question(email: str, db: Session = Depends(get_db)):
    """Retrieves the security question for the specified email."""
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not user.security_question:
        return {"question": "What is your recovery answer?"}
    return {"question": user.security_question}

@app.post("/api/auth/forgot-password/reset")
def reset_forgot_password(req: PasswordResetRequest, db: Session = Depends(get_db)):
    """Verifies security answer and updates password."""
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not user.hashed_security_answer:
        raise HTTPException(status_code=400, detail="Invalid email or security answer.")
        
    if not user.verify_security_answer(req.security_answer):
        raise HTTPException(status_code=400, detail="Invalid email or security answer.")
        
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
        
    user.hashed_password = User.hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully."}

class ProfileUpdate(BaseModel):
    institution: Optional[str] = None
    research_domain: Optional[str] = None
    research_topic: Optional[str] = None
    theme: Optional[str] = None

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns the profile information of the authorized active session."""
    if not current_user.profile:
        profile = UserProfile(
            user_id=current_user.id,
            theme="dark",
            institution="N/A",
            research_domain="N/A",
            research_topic="N/A"
        )
        db.add(profile)
        db.commit()
        db.refresh(current_user)
        
    return {
        "email": current_user.email,
        "id": current_user.id,
        "profile": {
            "theme": current_user.profile.theme,
            "institution": current_user.profile.institution or "N/A",
            "research_domain": current_user.profile.research_domain or "N/A",
            "research_topic": current_user.profile.research_topic or "N/A"
        }
    }

@app.post("/api/profile/update")
def update_profile(
    req: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates the user profile metadata or active theme selection."""
    if not current_user.profile:
        current_user.profile = UserProfile(
            user_id=current_user.id,
            theme="dark",
            institution="N/A",
            research_domain="N/A",
            research_topic="N/A"
        )
        db.add(current_user.profile)
        
    if req.institution is not None:
        current_user.profile.institution = req.institution.strip()
    if req.research_domain is not None:
        current_user.profile.research_domain = req.research_domain.strip()
    if req.research_topic is not None:
        current_user.profile.research_topic = req.research_topic.strip()
    if req.theme is not None:
        current_user.profile.theme = req.theme.strip()
        
    db.commit()
    db.refresh(current_user)
    
    return {
        "status": "success",
        "profile": {
            "theme": current_user.profile.theme,
            "institution": current_user.profile.institution,
            "research_domain": current_user.profile.research_domain,
            "research_topic": current_user.profile.research_topic
        }
    }

@app.get("/api/api-status")
async def get_api_status():
    """Returns the configuration status of all backend API keys."""
    return {
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY"))
    }

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve index.html via Jinja2 templates."""
    return templates.TemplateResponse(request=request, name="index.html")

# Project management endpoints
@app.get("/api/projects")
async def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lists all available review projects for the authorized user."""
    user_projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    
    # Sort projects by creation time
    user_projects.sort(key=lambda x: x.created_at)
    return [{"id": p.id, "name": p.name, "created_at": p.created_at.timestamp()} for p in user_projects]

@app.post("/api/projects")
async def create_project(
    req: ProjectCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Creates a new isolated review project."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty.")
        
    project_id = str(uuid.uuid4())
    get_project_dirs(project_id)
    
    proj = Project(id=project_id, name=name, owner=current_user)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    
    return {"id": proj.id, "name": proj.name, "created_at": proj.created_at.timestamp()}

@app.delete("/api/project/{project_id}")
async def delete_project(
    project_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Deletes a review project and all its uploaded papers/summaries."""
    proj = get_user_project(project_id, current_user.id, db)
    project_dir = os.path.join(PROJECTS_BASE_DIR, proj.id)
    
    try:
        # Cascade delete from database
        db.delete(proj)
        db.commit()
        
        # Clean filesystem
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
            
        logger.info(f"Deleted project {project_id}")
        return {"status": "success", "message": f"Project {project_id} deleted."}
    except Exception as e:
        logger.exception("Error deleting project")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

# Helper to build LaTeX Comparison Matrix code
def generate_latex_matrix(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "% No papers available to generate LaTeX table"
        
    def escape_latex(text: Any) -> str:
        if not text:
            return ""
        if isinstance(text, list):
            text = "; ".join(text)
        text = str(text)
        replacements = {
            "\\": "\\textbackslash{}",
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
        }
        for key, val in replacements.items():
            text = text.replace(key, val)
        return text

    latex = []
    latex.append("\\begin{table}[htbp]")
    latex.append("\\caption{Literature Comparison Matrix generated by LitSynthese}")
    latex.append("\\label{tab:lit_comparison_matrix}")
    latex.append("\\centering")
    latex.append("\\begin{tabular}{|l|p{3.5cm}|p{3.5cm}|p{3.5cm}|p{3.5cm}|}")
    latex.append("\\hline")
    latex.append("\\textbf{Paper Reference} & \\textbf{Core Objectives} & \\textbf{Methodology} & \\textbf{Key Contributions} & \\textbf{Limitations \\& Critique} \\\\")
    latex.append("\\hline")
    
    for item in items:
        ref = escape_latex(item["citation_key"])
        obj = escape_latex(item["synopsis"])
        meth = escape_latex(item["methodology"])
        contrib = escape_latex(item["contributions"])
        lim = escape_latex(item["limitations"])
        
        def truncate(s: str, max_l: int = 350) -> str:
            if len(s) > max_l:
                return s[:max_l-3] + "..."
            return s

        latex.append(f"{ref} & {truncate(obj)} & {truncate(meth)} & {truncate(contrib)} & {truncate(lim)} \\\\")
        latex.append("\\hline")
        
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")
    
    return "\n".join(latex)

@app.get("/api/project/{project_id}/matrix")
async def get_project_matrix(
    project_id: str,
    style: str = "apa",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates aspect-based literature comparison matrix & LaTeX code."""
    proj = get_user_project(project_id, current_user.id, db)
    papers = db.query(AcademicPaper).filter(AcademicPaper.project_id == proj.id).all()
    
    matrix_items = []
    for paper in papers:
        title = paper.title
        authors = paper.authors or "Unknown"
        year = str(paper.year) if paper.year else "N/A"
        
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        idx = papers.index(paper) + 1
        if style == "ieee":
            citation_key = f"[{idx}]"
        elif style == "harvard":
            if author_list:
                first_author = author_list[0].split()[-1]
                if len(author_list) > 1:
                    citation_key = f"({first_author} et al., {year})"
                else:
                    citation_key = f"({first_author}, {year})"
            else:
                citation_key = f"(Unknown, {year})"
        elif style == "bibtex":
            if author_list:
                first_author = "".join(c for c in author_list[0].split()[-1] if c.isalnum())
                citation_key = f"{first_author.lower()}{year}"
            else:
                citation_key = f"unknown{year}"
        else: # apa / default
            if author_list:
                first_author = author_list[0].split()[-1]
                if len(author_list) > 1:
                    citation_key = f"{first_author} et al. ({year})"
                else:
                    citation_key = f"{first_author} ({year})"
            else:
                citation_key = f"Unknown ({year})"
            
        synopsis = ""
        methodology = ""
        contributions = []
        limitations = []
        
        if paper.processed_path and os.path.exists(paper.processed_path):
            try:
                with open(paper.processed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    analysis = data.get("analysis", {})
                    synopsis = analysis.get("synopsis", "")
                    methodology = analysis.get("methodology", "")
                    contributions = analysis.get("contributions", [])
                    limitations = analysis.get("critical_review", [])
            except Exception as e:
                logger.warning(f"Failed to load processed json for paper {paper.id}: {str(e)}")
                
        matrix_items.append({
            "id": paper.id,
            "citation_key": citation_key,
            "title": title,
            "synopsis": synopsis,
            "methodology": methodology,
            "contributions": contributions,
            "limitations": limitations
        })
        
    latex_code = generate_latex_matrix(matrix_items)
    return {
        "items": matrix_items,
        "latex": latex_code
    }

@app.post("/api/project/{project_id}/synthesize")
async def synthesize_project(
    project_id: str,
    req: SynthesisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Runs a synthesis query across all project papers using RAG context."""
    proj = get_user_project(project_id, current_user.id, db)
    papers = db.query(AcademicPaper).filter(AcademicPaper.project_id == proj.id).all()
    
    if not papers:
        raise HTTPException(status_code=400, detail="No papers available in this project to synthesize.")
        
    context_parts = []
    for paper in papers:
        title = paper.title
        authors = paper.authors or "Unknown"
        year = str(paper.year) if paper.year else "N/A"
        
        synopsis = ""
        methodology = ""
        contributions_str = ""
        limitations_str = ""
        
        if paper.processed_path and os.path.exists(paper.processed_path):
            try:
                with open(paper.processed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    analysis = data.get("analysis", {})
                    synopsis = analysis.get("synopsis", "")
                    methodology = analysis.get("methodology", "")
                    contributions_str = "; ".join(analysis.get("contributions", []))
                    limitations_str = "; ".join(analysis.get("critical_review", []))
            except Exception as e:
                logger.warning(f"Failed to load paper {paper.id} JSON: {str(e)}")
                
        context_parts.append(
            f"Paper Citation: {authors} ({year})\n"
            f"Title: {title}\n"
            f"Synopsis: {synopsis}\n"
            f"Methodology: {methodology}\n"
            f"Contributions: {contributions_str}\n"
            f"Limitations: {limitations_str}\n"
        )
        
    compiled_context = "\n---\n".join(context_parts)
    
    try:
        reply = llm_service.synthesize_project_papers(
            context=compiled_context,
            query=req.query,
            model=req.model
        )
        return {"reply": reply}
    except Exception as e:
        logger.exception("Error during cross-doc synthesis")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

# Isolated paper endpoints
@app.post("/api/project/{project_id}/upload")
async def upload_paper(
    project_id: str, 
    model: str = "gemini-2.5-flash", 
    file: UploadFile = File(...),
    focus: str = "standard",
    temperature: float = 0.2,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Receives PDF file, parses sections, generates LLM summary, caches, and returns analysis ID."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    proj = get_user_project(project_id, current_user.id, db)
    uploads_dir, processed_dir = get_project_dirs(proj.id)
    
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
            model=model,
            focus=focus,
            temperature=temperature
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
            
        # Register paper entry in database
        meta = parsed_data["metadata"]
        new_paper = AcademicPaper(
            id=paper_id,
            project=proj,
            title=meta.get("title", "Untitled Paper"),
            authors=meta.get("authors", "Unknown Authors"),
            year=meta.get("year"),
            pages_count=meta.get("pages_count"),
            file_path=pdf_path,
            processed_path=result_path
        )
        db.add(new_paper)
        db.commit()
        
        logger.info(f"Paper {paper_id} successfully parsed and analysed inside project {project_id}.")
        return {"id": paper_id, "metadata": parsed_data["metadata"], "analysis": analysis}
        
    except Exception as e:
        logger.exception("Error processing PDF upload")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/api/project/{project_id}/papers")
async def list_papers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all successfully processed papers within a specific project."""
    proj = get_user_project(project_id, current_user.id, db)
    papers = db.query(AcademicPaper).filter(AcademicPaper.project_id == proj.id).all()
    
    result = []
    for p in papers:
        # Load keywords from cache JSON if available
        keywords = []
        if p.processed_path and os.path.exists(p.processed_path):
            try:
                with open(p.processed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    keywords = data.get("analysis", {}).get("keywords", [])
            except Exception:
                pass
                
        result.append({
            "id": p.id,
            "filename": os.path.basename(p.file_path),
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "pages_count": p.pages_count,
            "keywords": keywords
        })
    return result

@app.get("/api/project/{project_id}/paper/{paper_id}")
async def get_paper(
    project_id: str, 
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full analysis details of a specific paper inside a project."""
    proj = get_user_project(project_id, current_user.id, db)
    paper = db.query(AcademicPaper).filter(
        AcademicPaper.id == paper_id, 
        AcademicPaper.project_id == proj.id
    ).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in project.")
        
    if not paper.processed_path or not os.path.exists(paper.processed_path):
        raise HTTPException(status_code=404, detail="Paper analysis data not found.")
        
    with open(paper.processed_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Isolated chat endpoints
@app.get("/api/project/{project_id}/paper/{paper_id}/chat")
async def get_chat_history(
    project_id: str,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves chat message history for a specific paper."""
    proj = get_user_project(project_id, current_user.id, db)
    paper = db.query(AcademicPaper).filter(
        AcademicPaper.id == paper_id,
        AcademicPaper.project_id == proj.id
    ).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    db_history = db.query(ChatMessage).filter(ChatMessage.paper_id == paper.id).order_by(ChatMessage.created_at.asc()).all()
    return [{"role": msg.role, "content": msg.content} for msg in db_history]

@app.post("/api/project/{project_id}/paper/{paper_id}/chat")
async def chat_paper(
    project_id: str, 
    paper_id: str, 
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Asks a question about the paper in a context-grounded conversation."""
    proj = get_user_project(project_id, current_user.id, db)
    paper = db.query(AcademicPaper).filter(
        AcademicPaper.id == paper_id, 
        AcademicPaper.project_id == proj.id
    ).first()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    if not paper.processed_path or not os.path.exists(paper.processed_path):
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    with open(paper.processed_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Fetch previous chat history from DB
    db_history = db.query(ChatMessage).filter(ChatMessage.paper_id == paper.id).order_by(ChatMessage.created_at.asc()).all()
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in db_history]
    
    reply = llm_service.chat_about_paper(
        title=data["metadata"]["title"],
        sections=data["sections"],
        chat_history=history_dicts,
        query=request.query,
        model=request.model,
        analysis=data.get("analysis")
    )
    
    # Save user message and assistant reply to DB
    user_msg = ChatMessage(paper=paper, role="user", content=request.query)
    assistant_msg = ChatMessage(paper=paper, role="assistant", content=reply)
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    
    return {"reply": reply}

@app.get("/api/project/{project_id}/paper/{paper_id}/export")
async def export_paper_summary(
    project_id: str, 
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports structured paper analysis as a markdown file."""
    proj = get_user_project(project_id, current_user.id, db)
    paper = db.query(AcademicPaper).filter(
        AcademicPaper.id == paper_id, 
        AcademicPaper.project_id == proj.id
    ).first()
    
    if not paper or not paper.processed_path or not os.path.exists(paper.processed_path):
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    with open(paper.processed_path, "r", encoding="utf-8") as f:
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
