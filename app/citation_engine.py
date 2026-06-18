import re
import logging
import urllib.parse
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger("litsynthese.citation_engine")

class AcademicCitationEngine:
    """
    A dedicated engine to reliably extract and format accurate citations and metadata
    from academic papers by searching CrossRef and arXiv reference databases.
    """

    # Robust regex to detect DOIs (Digital Object Identifiers) in PDF text
    DOI_REGEX = re.compile(
        r'\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)',
        re.IGNORECASE
    )

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def extract_doi(self, text: str) -> Optional[str]:
        """
        Scans a text segment (usually the first page of a PDF) to locate a DOI.
        Cleans trailing punctuation common in text extractions.
        """
        if not text:
            return None
        
        match = self.DOI_REGEX.search(text)
        if match:
            doi = match.group(1)
            # Strip trailing punctuation commonly captured at the end of a DOI match in text
            doi = re.sub(r'[.,;()\]}]+$', '', doi)
            # Basic validation
            if doi.startswith("10.") and "/" in doi:
                return doi
        return None

    def lookup_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Queries the CrossRef API for a specific DOI to retrieve precise metadata.
        """
        try:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
            # User agent requested by CrossRef to prevent rate limiting
            headers = {"User-Agent": "LitSynthese/1.0 (mailto:imosudi@outlook.com)"}
            
            logger.info(f"Querying CrossRef API for DOI: {doi}")
            resp = httpx.get(url, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                data = resp.json()
                message = data.get("message", {})
                return self._parse_crossref_message(message)
            else:
                logger.warning(f"CrossRef DOI query returned status: {resp.status_code}")
        except Exception as e:
            logger.error(f"CrossRef DOI lookup failed: {str(e)}")
        return None

    def search_by_metadata(self, title: str, first_page_text: str = "") -> Optional[Dict[str, Any]]:
        """
        Searches CrossRef and arXiv using extracted titles/text chunks to find the closest match.
        """
        if not title or title.lower() in ["unknown title", "untitled paper"]:
            # Try searching with the first 200 characters of the PDF body text
            if len(first_page_text) > 50:
                query_str = first_page_text[:200]
            else:
                return None
        else:
            query_str = title

        # 1. Search CrossRef
        crossref_match = self._search_crossref(query_str)
        if crossref_match:
            return crossref_match

        # 2. Fallback to arXiv Search
        arxiv_match = self._search_arxiv(query_str)
        if arxiv_match:
            return arxiv_match

        return None

    def _search_crossref(self, query: str) -> Optional[Dict[str, Any]]:
        """Queries CrossRef works search API."""
        try:
            url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&rows=3"
            headers = {"User-Agent": "LitSynthese/1.0 (mailto:imosudi@outlook.com)"}
            
            logger.info(f"Searching CrossRef for metadata: '{query[:50]}...' ")
            resp = httpx.get(url, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                if items:
                    # Select the first result as the best candidate
                    best_item = items[0]
                    # basic title similarity checking can be done if needed, but return first candidate for now
                    return self._parse_crossref_message(best_item)
        except Exception as e:
            logger.error(f"CrossRef metadata search failed: {str(e)}")
        return None

    def _search_arxiv(self, query: str) -> Optional[Dict[str, Any]]:
        """Queries arXiv API for preprints."""
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results=1"
            logger.info(f"Searching arXiv for metadata: '{query[:50]}...' ")
            resp = httpx.get(url, timeout=self.timeout)
            
            if resp.status_code == 200:
                text = resp.text
                # Simple XML parsing using regexes to avoid external XML dependencies
                title_match = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
                published_match = re.search(r'<published>(\d{4})', text)
                author_matches = re.findall(r'<name>(.*?)</name>', text)
                
                if title_match and (published_match or author_matches):
                    # The first title match in entry is the actual paper title (the first main one is the feed title)
                    # We look for <entry> structure
                    entry_match = re.search(r'<entry>(.*?)</entry>', text, re.DOTALL)
                    if entry_match:
                        entry_text = entry_match.group(1)
                        e_title = re.search(r'<title>(.*?)</title>', entry_text, re.DOTALL)
                        e_pub = re.search(r'<published>(\d{4})', entry_text)
                        e_authors = re.findall(r'<name>(.*?)</name>', entry_text)
                        
                        title_val = re.sub(r'\s+', ' ', e_title.group(1)).strip() if e_title else query
                        year_val = e_pub.group(1) if e_pub else "Unknown Year"
                        authors_val = ", ".join(e_authors) if e_authors else "Unknown Authors"
                        
                        return {
                            "title": title_val,
                            "authors": authors_val,
                            "year": year_val,
                            "source": "arXiv"
                        }
        except Exception as e:
            logger.error(f"arXiv metadata search failed: {str(e)}")
        return None

    def _parse_crossref_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and formats metadata from CrossRef API schema."""
        title_list = message.get("title", [])
        title = title_list[0] if title_list else "Unknown Title"
        title = re.sub(r'\s+', ' ', title).strip()

        # Format Author list (e.g. "First Last, First Last")
        authors_raw = message.get("author", [])
        author_names = []
        for auth in authors_raw:
            given = auth.get("given", "").strip()
            family = auth.get("family", "").strip()
            if given and family:
                author_names.append(f"{given} {family}")
            elif family:
                author_names.append(family)
            elif given:
                author_names.append(given)
                
        authors = ", ".join(author_names) if author_names else "Unknown Authors"

        # Determine year of publication
        year = "Unknown Year"
        for date_key in ["published-print", "published-online", "created", "issued"]:
            date_parts = message.get(date_key, {}).get("date-parts", [])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                y = str(date_parts[0][0])
                if y.isdigit() and len(y) == 4:
                    year = y
                    break
                    
        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": message.get("DOI"),
            "source": "CrossRef"
        }
