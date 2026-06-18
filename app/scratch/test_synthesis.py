import os
import sys
import unittest
import json
from datetime import timedelta

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models import User, Project, AcademicPaper
from app import app
from app.auth import create_access_token

class TestSynthesisAndMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def setUp(self):
        self.db: Session = SessionLocal()
        # Clean existing test objects
        self.db.query(AcademicPaper).delete()
        self.db.query(Project).delete()
        self.db.query(User).filter(User.email.like("test_%")).delete()
        self.db.commit()

        # Create user
        self.user = User(email="test_reviewer@litsynthese.com", hashed_password=User.hash_password("password123"))
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Create access token
        self.token = create_access_token({"sub": self.user.email})
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create project
        self.project = Project(id="test-proj-123", name="Test Review Project", owner=self.user)
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

    def tearDown(self):
        self.db.query(AcademicPaper).delete()
        self.db.query(Project).delete()
        self.db.query(User).filter(User.email.like("test_%")).delete()
        self.db.commit()
        self.db.close()

    def test_upload_and_matrix_generation(self):
        # 1. Upload a sample paper PDF using the test client
        pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "paper_attention.pdf"))
        
        with open(pdf_path, "rb") as f:
            response = self.client.post(
                f"/api/project/{self.project.id}/upload",
                headers=self.headers,
                files={"file": ("paper_attention.pdf", f, "application/pdf")}
            )
            
        self.assertEqual(response.status_code, 200, response.text)
        res_data = response.json()
        self.assertIn("id", res_data)
        
        # 2. Query the comparison matrix endpoint
        matrix_res = self.client.get(
            f"/api/project/{self.project.id}/matrix",
            headers=self.headers
        )
        self.assertEqual(matrix_res.status_code, 200, matrix_res.text)
        matrix_data = matrix_res.json()
        
        self.assertIn("items", matrix_data)
        self.assertIn("latex", matrix_data)
        self.assertEqual(len(matrix_data["items"]), 1)
        
        item = matrix_data["items"][0]
        self.assertEqual(item["title"], "Attention-based Sparse Representation")
        self.assertEqual(item["citation_key"], "Smith (2026)") # Since author is "A. Smith" and year is 2026
        self.assertIn("synopsis", item)
        self.assertIn("methodology", item)
        self.assertIn("contributions", item)
        self.assertIn("limitations", item)
        
        # Verify LaTeX table generation contains reference and sections
        latex_code = matrix_data["latex"]
        self.assertIn("\\begin{table}", latex_code)
        self.assertIn("Smith (2026)", latex_code)

    def test_cross_document_synthesis(self):
        # 1. Upload paper_attention.pdf
        pdf_path1 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "paper_attention.pdf"))
        with open(pdf_path1, "rb") as f:
            self.client.post(
                f"/api/project/{self.project.id}/upload",
                headers=self.headers,
                files={"file": ("paper_attention.pdf", f, "application/pdf")}
            )

        # 2. Post a synthesis request
        synthesis_payload = {
            "query": "What are the advantages of Sparse Attention?",
            "model": "gemini-2.5-flash"
        }
        
        response = self.client.post(
            f"/api/project/{self.project.id}/synthesize",
            headers=self.headers,
            json=synthesis_payload
        )
        self.assertEqual(response.status_code, 200, response.text)
        res_data = response.json()
        self.assertIn("reply", res_data)
        self.assertIn("Mock Synthesis Engine", res_data["reply"]) # Since in mock mode

if __name__ == "__main__":
    unittest.main()
