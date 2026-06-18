import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import config

logger = logging.getLogger("litsynthese.chat_engine")



class AcademicChatEngine:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if self.api_key:
            logger.info("Gemini API Client (REST HTTPX) initialised successfully in Chat Engine.")
        else:
            logger.info("Running Chat Engine in Demo Mock Mode (No GEMINI_API_KEY).")

    def is_mock_mode(self) -> bool:
        return not self.api_key or self.api_key.startswith("AQ.Ab8")

    def chat_about_paper(self, title: str, sections: Dict[str, Any], chat_history: List[Dict[str, str]], query: str, model: str = "gemini-2.5-flash", analysis: Optional[Dict[str, Any]] = None) -> str:
        """Answers user query about the paper using context-grounded retrieval."""
        model = model.strip()
        
        if self.is_mock_mode():
            return self._generate_mock_chat_reply(title, sections, query, analysis)
            
        # Retrieve highly focused relevant passages using our intelligent RAG engine
        relevant_text = self._retrieve_relevant_passages(sections, query, top_k=6, analysis=analysis)

        # 1. Gemini Client path
        if model == "gemini" or model.startswith("gemini-") or model == "gemini-2.5-flash":
                
            formatted_history = ""
            for msg in chat_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                formatted_history += f"{role}: {msg['content']}\n"
                
            prompt = f"""
You are an intelligent research assistant specialising in analysing academic papers. 
You are discussing the paper: "{title}".

Below is the relevant context extracted from the paper:
{relevant_text}

Here is the conversation history:
{formatted_history}

User Query: "{query}"

Answer the query accurately, objectively, and technically based ONLY on the provided paper context. 
If the paper text does not contain enough information to answer the question, state that clearly.
Do not hallucinate facts. Cite specific section names (e.g., "[Methodology]", "[Introduction]") in your answer where appropriate.
"""
            # Prioritized order of models to try
            if model == "gemini":
                models_to_try = config.GEMINI_MODELS_FALLBACK
            else:
                models_to_try = [model]
                for m in config.GEMINI_MODELS_FALLBACK:
                    if m != model:
                        models_to_try.append(m)
                    
            for m in models_to_try:
                try:
                    logger.info(f"Attempting chat with Gemini model: {m}...")
                    import httpx
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
                    headers = {"Content-Type": "application/json"}
                    
                    payload = {
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.3
                        }
                    }
                    
                    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                    response.raise_for_status()
                    resp_json = response.json()
                    
                    text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                except Exception as e:
                    logger.warning(f"Gemini API chat call with model {m} failed: {e}. Trying next available model...")
            
            logger.error("All Gemini API chat models failed. Returning connection error.")
            return "An error occurred while connecting to the Gemini LLM service. All fallback models failed."
                
        # 2. External API provider path (Groq / OpenRouter / LLaMA Auto-select)
        if model == "llama" or model.startswith("groq/") or model.startswith("openrouter/"):
            # Determine order of LLaMA models to try
            if model == "llama":
                models_to_try = config.LLAMA_MODELS_FALLBACK
            else:
                models_to_try = [model]
                if "llama" in model:
                    for m in config.LLAMA_MODELS_FALLBACK:
                        if m != model:
                            models_to_try.append(m)
                            
            import httpx
            for m in models_to_try:
                try:
                    logger.info(f"Attempting chat with model: {m}...")
                    url = ""
                    headers = {}
                    api_key = ""
                    actual_model = ""
                    
                    if m.startswith("groq/"):
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        api_key = config.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
                        actual_model = m.replace("groq/", "")
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                    elif m.startswith("openrouter/"):
                        url = "https://openrouter.ai/v1/chat/completions"
                        api_key = config.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
                        actual_model = m.replace("openrouter/", "")
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://mioemi.com",
                            "X-Title": "LitSynthese"
                        }
                    else:
                        raise ValueError(f"Unknown LLM provider style for model: {m}")
                        
                    if not api_key:
                        raise ValueError(f"API Key for {m} is not configured.")
                        
                    messages = [
                        {
                            "role": "system",
                            "content": f"You are an intelligent research assistant specialising in analysing academic papers. You are discussing the paper: \"{title}\".\n\nBelow is the relevant context extracted from the paper:\n{relevant_text}\n\nAnswer the query accurately, objectively, and technically based ONLY on the provided paper context. Cite specific section names (e.g., [Methodology]) in your answer where appropriate. If the paper text does not contain enough information to answer, state that clearly."
                        }
                    ]
                    
                    for msg in chat_history:
                        role = "user" if msg["role"] == "user" else "assistant"
                        messages.append({"role": role, "content": msg["content"]})
                        
                    messages.append({"role": "user", "content": query})
                    
                    payload = {
                        "model": actual_model,
                        "messages": messages,
                        "temperature": 0.3
                    }
                    
                    res = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                    res.raise_for_status()
                    resp_data = res.json()
                    return resp_data["choices"][0]["message"]["content"]
                except Exception as e:
                    logger.warning(f"Chat API call to model {m} failed: {e}. Trying next available model...")
                    
            logger.error("All alternative LLM models failed for chat. Returning connection error.")
            return "An error occurred while connecting to the LLM service. All fallback models failed."

    def _generate_mock_chat_reply(self, title: str, sections: Dict[str, Any], query: str, analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        An intelligent offline RAG chat engine that searches the actual paper sections
        for terms matching the query, extracting and formatting relevant passages.
        """
        relevant_text = self._retrieve_relevant_passages(sections, query, top_k=3, analysis=analysis)
        if relevant_text:
            return f"### Grounded Response from **'{title}'**\n\n{relevant_text}"
        else:
            available_sections = ", ".join([s.replace("_", " ").title() for s in sections.keys() if sections[s].get("text")])
            return f"I searched the document **'{title}'** for references matching your query, but could not find direct passages. \n\n" \
                   f"The available sections in this paper are: **{available_sections}**. " \
                   f"Please refine your query using terms found in these sections (e.g., asking about 'methodology' or 'contributions')."

    def _retrieve_relevant_passages(self, sections: Dict[str, Any], query: str, top_k: int = 6, analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Retrieves the top_k most semantically relevant paragraphs across all paper sections
        and structured analysis, using a normalized keyword-overlap scoring mechanism.
        """
        # Clean query: lowercase and remove punctuation
        q_cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        query_words = [w for w in q_cleaned.split() if len(w) > 3]
        
        # Stop words to ignore
        stop_words = {
            "about", "above", "after", "again", "against", "all", "am", "an", "and",
            "any", "are", "arent", "as", "at", "be", "because", "been", "before",
            "being", "below", "between", "both", "but", "by", "cant", "cannot",
            "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing",
            "dont", "down", "during", "each", "few", "for", "from", "further",
            "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he",
            "her", "here", "hers", "herself", "him", "himself", "his", "how",
            "i", "if", "in", "into", "is", "isnt", "it", "its", "itself", "more",
            "most", "mustnt", "my", "myself", "no", "nor", "not", "of", "off",
            "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
            "out", "over", "own", "same", "shant", "she", "shes", "should", "shouldnt",
            "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
            "themselves", "then", "there", "theres", "these", "they", "theyre",
            "theyve", "this", "those", "through", "to", "too", "under", "until",
            "up", "very", "was", "wasnt", "we", "were", "werent", "what", "whats",
            "when", "wherent", "where", "which", "while", "who", "whom", "why",
            "with", "wont", "would", "wouldnt", "you", "your", "yours", "yourself",
            "yourselves"
        }
        
        keywords = [w for w in query_words if w not in stop_words]
        if not keywords:
            keywords = [w for w in query_words]
            
        # Build search sections, including extra metadata from analysis if available
        search_sections = dict(sections)
        if analysis:
            if "synopsis" in analysis and analysis["synopsis"]:
                search_sections["executive_synopsis"] = {"text": analysis["synopsis"]}
            if "contributions" in analysis and analysis["contributions"]:
                search_sections["key_contributions"] = {"text": "\n".join(analysis["contributions"])}
            if "critical_review" in analysis and analysis["critical_review"]:
                search_sections["critical_review_and_limitations"] = {"text": "\n".join(analysis["critical_review"])}
            if "future_work" in analysis and analysis["future_work"]:
                search_sections["future_research"] = {"text": "\n".join(analysis["future_work"])}
            if "keywords" in analysis and analysis["keywords"]:
                search_sections["keywords"] = {"text": ", ".join(analysis["keywords"])}

        passages = []
        for sect_name, sect_data in search_sections.items():
            # Skip references section unless query specifically asks for references/bibliography
            if sect_name == "references" and not any(w in query.lower() for w in ["reference", "bibliography", "cite", "citation"]):
                continue
                
            text = sect_data.get("text", "")
            if not text:
                continue
            
            # Split section text into paragraphs
            raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            paragraphs = []
            for rp in raw_paragraphs:
                # If paragraph is too long (over 1000 characters), split it into smaller sentences/chunks
                if len(rp) > 1000:
                    sentences = re.split(r'(?<=[.!?])\s+', rp)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) < 800:
                            current_chunk += (" " if current_chunk else "") + sent
                        else:
                            if current_chunk:
                                paragraphs.append(current_chunk.strip())
                            current_chunk = sent
                    if current_chunk:
                        paragraphs.append(current_chunk.strip())
                else:
                    paragraphs.append(rp)
                
            for para in paragraphs:
                para_lower = para.lower()
                
                # Calculate frequency score
                match_score = 0.0
                matched_keywords = set()
                for word in keywords:
                    count = para_lower.count(word)
                    if count > 0:
                        match_score += count
                        matched_keywords.add(word)
                    
                    # Bonus if the query word is in the section name itself
                    if word in sect_name.lower():
                        match_score += 15.0
                        matched_keywords.add(word)
                
                # Bonus for matching unique query terms
                match_score += len(matched_keywords) * 5
                
                # Length normalization to prevent selection of extremely long, wordy paragraphs
                length = len(para_lower.split())
                if length > 0:
                    norm_score = match_score / (length ** 0.5)
                else:
                    norm_score = 0.0
                    
                if norm_score > 0:
                    passages.append((norm_score, sect_name, para))
                    
        # Sort by normalized score descending
        passages.sort(reverse=True, key=lambda x: x[0])
        
        # Format output context
        retrieved_context = ""
        seen_paras = set()
        count = 0
        for score, sect_name, para in passages:
            para_prefix = para[:60].lower()
            if para_prefix in seen_paras:
                continue
            seen_paras.add(para_prefix)
            
            sect_title = sect_name.replace("_", " ").title()
            retrieved_context += f"\n**From Section [{sect_title}]:**\n> {para}\n\n"
            
            count += 1
            if count >= top_k:
                break
                
        if not retrieved_context:
            # Fallback to main sections if query keywords found no matches
            fallback_sections = ["abstract", "introduction", "methodology"]
            for s in fallback_sections:
                if s in search_sections and search_sections[s].get("text"):
                    retrieved_context += f"\n**From Section [{s.title()}]:**\n> {search_sections[s]['text'][:800]}...\n\n"
                    
        return retrieved_context.strip()
