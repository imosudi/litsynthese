import re
from pypdf import PdfReader

def clean_text(text: str) -> str:
    """Cleans up common PDF extraction artifacts like hyphenated line breaks."""
    if not text:
        return ""
    # Remove soft hyphens and combine words broken across lines
    text = re.sub(r'(\w+)-\n\s*(\w+)', r'\1\2', text)
    # Replace single newlines (not double newlines) with spaces to preserve paragraphs
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Remove multiple consecutive spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences using a simple rule-based approach."""
    # Split on period, question mark, or exclamation followed by space and uppercase letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]

class AcademicPaperParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.reader = PdfReader(file_path)
        self.pages_text = [] # list of dicts: {"page_num": int, "raw_text": str, "clean_text": str}
        self.metadata = {}
        self.sections = {} # dict: {section_name: {"text": str, "pages": list[int]}}
        self.references = [] # list of dicts: {"index": int, "raw_text": str, "citations": list[dict]}
        
    def parse(self):
        """Main entry point to parse the PDF."""
        self._extract_raw_text()
        self._extract_metadata()
        self._segment_sections()
        self._extract_bibliography()
        self._map_citations()
        
        return {
            "metadata": self.metadata,
            "sections": self.sections,
            "references": self.references
        }
        
    def _extract_raw_text(self):
        """Extracts text page by page."""
        for i, page in enumerate(self.reader.pages):
            raw_text = page.extract_text() or ""
            self.pages_text.append({
                "page_num": i + 1,
                "raw_text": raw_text,
                "clean_text": clean_text(raw_text)
            })

    def _extract_metadata(self):
        """Extracts basic metadata from the PDF structure or first page heuristics."""
        info = self.reader.metadata
        title = ""
        authors = ""
        
        if info:
            title = info.title or ""
            authors = info.author or ""
            
        # Fallback to first page heuristics if title/authors are empty
        if not title and len(self.pages_text) > 0:
            first_page = self.pages_text[0]["clean_text"]
            # Split by lines
            lines = [line.strip() for line in first_page.split("\n") if line.strip()]
            if lines:
                title = lines[0] # Assume first non-empty line on first page is title
                if len(lines) > 1:
                    authors = lines[1] # Assume second line contains authors
        
        # Clean title
        if len(title) > 200:
            title = title[:197] + "..."
            
        creation_date = info.get("/CreationDate", "") if info and info.get("/CreationDate") else ""
        if creation_date.startswith("D:"):
            creation_date = creation_date[2:]
        year_val = creation_date[:4] if creation_date else "Unknown Year"
        if not year_val.isdigit():
            year_val = "Unknown Year"
            
        self.metadata = {
            "title": title or "Unknown Title",
            "authors": authors or "Unknown Authors",
            "year": year_val,
            "pages_count": len(self.reader.pages)
        }

    def _segment_sections(self):
        """Segments the paper into logical academic sections based on heading patterns."""
        # Common section heading patterns in academic papers
        section_patterns = {
            "abstract": re.compile(r'^\s*(?:abstract)\b', re.IGNORECASE),
            "introduction": re.compile(r'^\s*(?:\d+\.?\s*)?(?:introduction)\b', re.IGNORECASE),
            "related_work": re.compile(r'^\s*(?:\d+\.?\s*)?(?:related\s+work|background|literature\s+review)\b', re.IGNORECASE),
            "methodology": re.compile(r'^\s*(?:\d+\.?\s*)?(?:methodology|method|system\s+design|proposed\s+approach|architecture)\b', re.IGNORECASE),
            "experiments": re.compile(r'^\s*(?:\d+\.?\s*)?(?:experiments|evaluation|experimental\s+setup|methodology\s+evaluation)\b', re.IGNORECASE),
            "results": re.compile(r'^\s*(?:\d+\.?\s*)?(?:results|discussion|findings|analysis)\b', re.IGNORECASE),
            "conclusion": re.compile(r'^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions|concluding\s+remarks)\b', re.IGNORECASE),
            "references": re.compile(r'^\s*(?:\d+\.?\s*)?(?:references|bibliography|works\s+cited|bibliographical\s+references)\b', re.IGNORECASE)
        }
        
        # Initialise sections dict
        for sect in section_patterns:
            self.sections[sect] = {"text": "", "start_page": None, "end_page": None}
            
        current_section = "abstract"
        self.sections[current_section]["start_page"] = 1
        
        # We iterate line by line to detect headings
        for page in self.pages_text:
            page_num = page["page_num"]
            lines = page["raw_text"].split("\n")
            
            for line in lines:
                cleaned_line = line.strip()
                if not cleaned_line:
                    continue
                
                # Check if this line matches any section heading
                matched_sect = None
                for sect_name, pattern in section_patterns.items():
                    if pattern.match(cleaned_line):
                        matched_sect = sect_name
                        break
                
                if matched_sect and matched_sect != current_section:
                    # Close current section
                    self.sections[current_section]["end_page"] = page_num
                    
                    # Open new section
                    current_section = matched_sect
                    self.sections[current_section]["start_page"] = page_num
                
                # Append to current section
                self.sections[current_section]["text"] += line + "\n"

        # Close the last section
        if current_section:
            self.sections[current_section]["end_page"] = len(self.pages_text)
            
        # Clean up section texts
        for sect_name in self.sections:
            self.sections[sect_name]["text"] = clean_text(self.sections[sect_name]["text"])
            
    def _extract_bibliography(self):
        """Extracts individual entries from the references/bibliography section."""
        ref_text = self.sections["references"]["text"]
        if not ref_text:
            return
            
        # Remove section heading if it is at the start of the text
        ref_heading_pattern = re.compile(r'^\s*(?:\d+\.?\s*)?(?:references|bibliography|works\s+cited|bibliographical\s+references)\b\s*', re.IGNORECASE)
        ref_text = ref_heading_pattern.sub('', ref_text)
            
        # Try to split on bracketed numbers like [1], [2]
        # Common bibliography numbering format: [1] Author, Title...
        bracket_pattern = re.compile(r'\[(\d+)\]\s*(.*?)(?=\[\d+\]|\Z)', re.DOTALL)
        matches = bracket_pattern.findall(ref_text)
        
        if matches:
            for idx, text in matches:
                self.references.append({
                    "index": int(idx),
                    "raw_text": text.strip().replace("\n", " "),
                    "citations": []
                })
        else:
            # Fallback 1: Numbered list like "1. Author, Title"
            numbered_pattern = re.compile(r'(?:^|\s)(\d{1,3})\.\s+(.*?)(?=\s\d{1,3}\.\s|\Z)', re.DOTALL)
            matches = numbered_pattern.findall(ref_text)
            is_valid_numbered = False
            if matches:
                indices = [int(idx) for idx, _ in matches]
                if len(indices) > 1 and (1 in indices or 2 in indices):
                    is_valid_numbered = True
                    
            if is_valid_numbered:
                for idx, text in matches:
                    self.references.append({
                        "index": int(idx),
                        "raw_text": text.strip().replace("\n", " "),
                        "citations": []
                    })
            else:
                # Fallback 2: APA / Harvard style unnumbered author-year bibliography list
                # 1. Find all 4-digit years in the references text
                year_matches = list(re.finditer(r'\b(19\d{2}|20\d{2})[a-z]?\b', ref_text))
                
                boundaries = [0]
                
                # Common words that appear in titles/venues/drafts but NOT in author lists
                forbidden_words = {
                    'in', 'on', 'for', 'at', 'by', 'from', 'the', 'version', 
                    'draft', 'proceedings', 'conference', 'journal', 'workshop', 'volume', 
                    'pages', 'page', 'editor', 'editors', 'edition', 'university', 'press', 
                    'science', 'technology', 'department', 'institute', 'society', 'association'
                }
                
                for i in range(1, len(year_matches)):
                    year_start = year_matches[i].start()
                    prev_year_end = year_matches[i-1].end()
                    
                    # Search text between the end of the previous year and the start of the current year
                    search_text = ref_text[prev_year_end:year_start]
                    
                    # Find all periods in search_text
                    period_indices = [m.start() for m in re.finditer(r'\.', search_text)]
                    
                    boundary_idx = None
                    # Go backwards through the periods (from closest to the year)
                    for p_idx in reversed(period_indices):
                        # Skip if it is just the separator period between authors and the year
                        # (i.e. no words between this period and the end of search_text)
                        text_after_period = search_text[p_idx + 1:]
                        if not re.search(r'\w', text_after_period):
                            continue
                            
                        # Skip if it is part of an initial (e.g. ' D.')
                        part_before = search_text[:p_idx]
                        if re.search(r'\b[A-Z]$', part_before.strip()):
                            continue
                            
                        # Skip if it is part of 'et al.'
                        if part_before.strip().endswith('et al'):
                            continue
                            
                        # Skip if the candidate author list (text after the period) contains forbidden words
                        candidate_authors = text_after_period.lower()
                        words = set(re.findall(r'\b\w+\b', candidate_authors))
                        if words.intersection(forbidden_words):
                            continue
                            
                        boundary_idx = prev_year_end + p_idx + 1
                        break
                        
                    if boundary_idx is not None:
                        boundaries.append(boundary_idx)
                        
                boundaries.append(len(ref_text))
                
                # Split entries and build the references list
                for idx in range(len(boundaries) - 1):
                    entry_text = ref_text[boundaries[idx]:boundaries[idx+1]].strip()
                    if entry_text:
                        self.references.append({
                            "index": idx + 1,
                            "raw_text": entry_text,
                            "citations": []
                        })

    def _map_citations(self):
        """Finds where each bibliography item is cited in the text and extracts surrounding context."""
        if not self.references:
            return
            
        # Scan page-by-page to find in-text citations
        for page in self.pages_text:
            page_num = page["page_num"]
            clean_page = page["clean_text"]
            
            # Find the section name for this page
            page_section = "Unknown"
            for sect_name, sect_data in self.sections.items():
                start = sect_data.get("start_page")
                end = sect_data.get("end_page")
                if start and end and start <= page_num <= end:
                    page_section = sect_name.replace("_", " ").title()
                    break
                    
            sentences = split_into_sentences(clean_page)
            
            for sentence in sentences:
                # IEEE Style citation matching: checks for [X], [X, Y], [X-Y]
                # We search for bracketed numbers and check if our reference index is inside them.
                brackets = re.findall(r'\[([\d\s,\-]+)\]', sentence)
                for bracket_content in brackets:
                    # Parse contents like "1", "1, 2", "1-3"
                    indices = self._parse_citation_brackets(bracket_content)
                    for idx in indices:
                        for ref in self.references:
                            if ref["index"] == idx:
                                # Found a citation context! Avoid duplicate context for same sentence
                                if sentence not in [c["context"] for c in ref["citations"]]:
                                    ref["citations"].append({
                                        "context": sentence,
                                        "page": page_num,
                                        "section": page_section
                                    })
                                    
                # APA Style fallback: if no brackets are found, check if first author name appears
                # e.g., for "Smith, J. and Jones, M., 2020...", search for "Smith" and the year
                if not brackets:
                    for ref in self.references:
                        ref_txt = ref["raw_text"]
                        # Extract first author name (usually first word or word before comma)
                        author_match = re.match(r'^([A-Z][a-zA-Z]+)', ref_txt)
                        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', ref_txt)
                        if author_match and year_match:
                            author = author_match.group(1)
                            year = year_match.group(1)
                            # Look for author name and year in sentence (case sensitive for author)
                            if author in sentence and year in sentence:
                                if sentence not in [c["context"] for c in ref["citations"]]:
                                    ref["citations"].append({
                                        "context": sentence,
                                        "page": page_num,
                                        "section": page_section
                                    })

    def _parse_citation_brackets(self, content: str) -> list[int]:
        """Parses citation brackets content like '1, 2', '1-3', '4' to a list of integers."""
        indices = set()
        # Split by comma
        parts = content.split(",")
        for part in parts:
            part = part.strip()
            if '-' in part or '–' in part: # hyphens or en-dashes
                subparts = re.split(r'[\-–]', part)
                if len(subparts) == 2:
                    try:
                        start = int(subparts[0].strip())
                        end = int(subparts[1].strip())
                        for idx in range(start, end + 1):
                            indices.add(idx)
                    except ValueError:
                        pass
            else:
                try:
                    indices.add(int(part))
                except ValueError:
                    pass
        return list(indices)
