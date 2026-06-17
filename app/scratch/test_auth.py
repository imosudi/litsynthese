import os
import sys
import unittest
from datetime import timedelta

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models import User, Project, UserProfile
from app.auth import create_access_token, get_current_user

class TestAuthSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Bind the engine and build tables
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db: Session = SessionLocal()
        # Clean existing test users if any
        self.db.query(User).filter(User.email.like("test_%@litsynthese.com")).delete(synchronize_session=False)
        self.db.commit()

    def tearDown(self):
        self.db.query(User).filter(User.email.like("test_%@litsynthese.com")).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_user_creation_and_hashing(self):
        # Create test user
        email = "test_user@litsynthese.com"
        password = "secret_password_2026"
        hashed = User.hash_password(password)
        
        user = User(email=email, hashed_password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, email)
        
        # Verify valid and invalid credentials
        self.assertTrue(user.verify_password(password))
        self.assertFalse(user.verify_password("wrong_password"))

    def test_user_profile_relationship(self):
        email = "test_profile@litsynthese.com"
        hashed = User.hash_password("password123")
        
        user = User(email=email, hashed_password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        profile = UserProfile(
            user_id=user.id,
            institution="Stanford University",
            research_domain="Quantum Computing",
            research_topic="Quantum Annealing Optimization"
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(user)

        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.institution, "Stanford University")
        self.assertEqual(user.profile.research_domain, "Quantum Computing")

    def test_jwt_generation_and_validation(self):
        email = "test_jwt@litsynthese.com"
        hashed = User.hash_password("password123")
        
        user = User(email=email, hashed_password=hashed)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Create access token
        token = create_access_token({"sub": user.email}, expires_delta=timedelta(minutes=5))
        self.assertIsNotNone(token)
        
        # Validate dependency resolution
        resolved_user = get_current_user(token=token, db=self.db)
        self.assertEqual(resolved_user.email, email)
        self.assertEqual(resolved_user.id, user.id)

    def test_project_isolation(self):
        # Create user A
        user_a = User(email="test_a@litsynthese.com", hashed_password=User.hash_password("passA"))
        self.db.add(user_a)
        self.db.commit()
        self.db.refresh(user_a)

        # Create user B
        user_b = User(email="test_b@litsynthese.com", hashed_password=User.hash_password("passB"))
        self.db.add(user_b)
        self.db.commit()
        self.db.refresh(user_b)

        # Associate project with User A
        proj_a = Project(id="proj-a-1234", name="ML Safety", owner=user_a)
        self.db.add(proj_a)
        
        # Associate project with User B
        proj_b = Project(id="proj-b-5678", name="NLP Models", owner=user_b)
        self.db.add(proj_b)
        self.db.commit()

        # Query projects for User A and User B separately
        projects_a = self.db.query(Project).filter(Project.user_id == user_a.id).all()
        projects_b = self.db.query(Project).filter(Project.user_id == user_b.id).all()

        self.assertEqual(len(projects_a), 1)
        self.assertEqual(projects_a[0].name, "ML Safety")
        self.assertEqual(projects_a[0].id, "proj-a-1234")

        self.assertEqual(len(projects_b), 1)
        self.assertEqual(projects_b[0].name, "NLP Models")
        self.assertEqual(projects_b[0].id, "proj-b-5678")

if __name__ == "__main__":
    unittest.main()
