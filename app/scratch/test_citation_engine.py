import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.citation_engine import AcademicCitationEngine

class TestAcademicCitationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AcademicCitationEngine()

    def test_extract_doi(self):
        # Test basic DOI matching
        text = "This paper has DOI: 10.1109/TQE.2020.3012345 in the text."
        doi = self.engine.extract_doi(text)
        self.assertEqual(doi, "10.1109/TQE.2020.3012345")

        # Test DOI matching with punctuation at the end
        text_punct = "See DOI 10.1016/j.jbi.2015.06.020, which is..."
        doi_punct = self.engine.extract_doi(text_punct)
        self.assertEqual(doi_punct, "10.1016/j.jbi.2015.06.020")

        # Test non-existent DOI
        self.assertIsNone(self.engine.extract_doi("No DOI here."))

    def test_parse_crossref_message(self):
        # Mock message from CrossRef response
        message = {
            "title": ["Attention Is All You Need"],
            "author": [
                {"given": "Ashish", "family": "Vaswani"},
                {"given": "Noam", "family": "Shazeer"},
                {"given": "Niki", "family": "Parmar"}
            ],
            "published-print": {
                "date-parts": [[2017, 12, 6]]
            },
            "DOI": "10.5555/3295222.3295349"
        }
        
        parsed = self.engine._parse_crossref_message(message)
        self.assertEqual(parsed["title"], "Attention Is All You Need")
        self.assertEqual(parsed["authors"], "Ashish Vaswani, Noam Shazeer, Niki Parmar")
        self.assertEqual(parsed["year"], "2017")
        self.assertEqual(parsed["doi"], "10.5555/3295222.3295349")

    @patch("httpx.get")
    def test_lookup_by_doi_success(self, mock_get):
        # Mock successful CrossRef lookup response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Attention Is All You Need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "published-print": {"date-parts": [[2017]]},
                "DOI": "10.5555/3295222.3295349"
            }
        }
        mock_get.return_value = mock_response

        res = self.engine.lookup_by_doi("10.5555/3295222.3295349")
        self.assertIsNotNone(res)
        self.assertEqual(res["title"], "Attention Is All You Need")
        self.assertEqual(res["authors"], "Ashish Vaswani")
        self.assertEqual(res["year"], "2017")

    @patch("httpx.get")
    def test_lookup_by_doi_not_found(self, mock_get):
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        res = self.engine.lookup_by_doi("10.9999/notfound")
        self.assertIsNone(res)

    def test_title_similarity(self):
        # Test exact match
        self.assertGreaterEqual(self.engine._title_similarity("Attention Is All You Need", "Attention Is All You Need"), 0.99)
        
        # Test subset/subtitle truncation matches
        self.assertGreaterEqual(self.engine._title_similarity(
            "Transparency as Architecture",
            "Transparency as Architecture: Structural Compliance Gaps in EU AI Act Article 50 II"
        ), 0.99)
        
        # Test completely different titles
        self.assertLess(self.engine._title_similarity(
            "Transparency as Architecture: Structural Compliance Gaps in EU AI Act Article 50 II",
            "Take It All: Ensemble Retrieval for Multimodal Evidence Aggregation"
        ), 0.1)

        # Test partial matches
        self.assertGreaterEqual(self.engine._title_similarity("Deep Learning for Agriculture", "Machine Learning in Agriculture"), 0.6)

if __name__ == "__main__":
    unittest.main()
