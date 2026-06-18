import os
import sys
import unittest

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models import User
from app.server import app

class TestPasswordReset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def setUp(self):
        self.db: Session = SessionLocal()
        # Clean existing test users if any
        self.db.query(User).filter(User.email.like("test_reset_%@litsynthese.com")).delete(synchronize_session=False)
        self.db.commit()

    def tearDown(self):
        self.db.query(User).filter(User.email.like("test_reset_%@litsynthese.com")).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_model_security_answer_hashing(self):
        email = "test_reset_model@litsynthese.com"
        pwd = "original_password"
        question = "What was the topic of your first publication?"
        answer = "  Quantum Gravitational Anomaly  "
        
        user = User(
            email=email,
            hashed_password=User.hash_password(pwd),
            security_question=question,
            hashed_security_answer=User.hash_security_answer(answer)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Verify correct answer (should ignore trailing spaces and casing)
        self.assertTrue(user.verify_security_answer("quantum gravitational anomaly"))
        self.assertTrue(user.verify_security_answer("  QUANTUM GRAVITATIONAL ANOMALY  "))
        self.assertFalse(user.verify_security_answer("wrong answer"))

    def test_api_registration_with_recovery(self):
        payload = {
            "email": "test_reset_reg@litsynthese.com",
            "password": "securepassword",
            "security_question": "What is your favorite academic journal?",
            "security_answer": "Nature Physics"
        }
        res = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(res.status_code, 200)

        # Verify database record
        user = self.db.query(User).filter(User.email == "test_reset_reg@litsynthese.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.security_question, "What is your favorite academic journal?")
        self.assertTrue(user.verify_security_answer("nature physics"))

    def test_api_question_retrieval(self):
        # Create user
        user = User(
            email="test_reset_q@litsynthese.com",
            hashed_password=User.hash_password("pass123"),
            security_question="First Conference City?",
            hashed_security_answer=User.hash_security_answer("Boston")
        )
        self.db.add(user)
        self.db.commit()

        # Retrieve question
        res = self.client.get("/api/auth/forgot-password/question?email=test_reset_q@litsynthese.com")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["question"], "First Conference City?")

        # Check behaviour for non-existent email (should return a default question to protect privacy)
        res_fake = self.client.get("/api/auth/forgot-password/question?email=non_existent@litsynthese.com")
        self.assertEqual(res_fake.status_code, 200)
        self.assertEqual(res_fake.json()["question"], "What is your recovery answer?")

    def test_api_password_reset_flow(self):
        # Create user
        user = User(
            email="test_reset_flow@litsynthese.com",
            hashed_password=User.hash_password("pass_old"),
            security_question="First Advisor?",
            hashed_security_answer=User.hash_security_answer("Professor Feynman")
        )
        self.db.add(user)
        self.db.commit()

        # Submit incorrect answer
        res_fail = self.client.post("/api/auth/forgot-password/reset", json={
            "email": "test_reset_flow@litsynthese.com",
            "security_answer": "Professor Einstein",
            "new_password": "pass_new_123"
        })
        self.assertEqual(res_fail.status_code, 400)

        # Submit correct answer
        res_success = self.client.post("/api/auth/forgot-password/reset", json={
            "email": "test_reset_flow@litsynthese.com",
            "security_answer": "  professor feynman  ",
            "new_password": "pass_new_123"
        })
        self.assertEqual(res_success.status_code, 200)

        # Verify we can log in with new password
        login_res = self.client.post("/api/auth/login", json={
            "email": "test_reset_flow@litsynthese.com",
            "password": "pass_new_123"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("access_token", login_res.json())

if __name__ == "__main__":
    unittest.main()
