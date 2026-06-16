import os
import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Setup logger
logger = logging.getLogger("review_n_summary.llm")

# Define schema for structured paper analysis
class PaperAnalysis(BaseModel):
    synopsis: str = Field(description="A detailed executive summary explaining the core research question, context, and high-level findings.")
    contributions: List[str] = Field(description="A list of 3-5 key novel contributions or findings presented in the paper.")
    methodology: str = Field(description="A detailed description of the experimental methodology, systems design, models, formulas, or dataset details.")
    critical_review: List[str] = Field(description="A peer-review style critique highlighting limitations, key assumptions, potential threats to validity, or weak spots in the evaluation.")
    future_work: List[str] = Field(description="A list of 2-4 concrete, actionable areas where future researchers could extend this work.")
    keywords: List[str] = Field(description="5 to 8 keywords or key academic concepts that describe the paper.")

# Try importing google-genai
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    logger.warning("google-genai library not installed. Will use fallback/mock.")

class AcademicLLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        
        if HAS_GENAI and self.api_key:
            try:
                # Initialise Google GenAI client
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini API Client initialised successfully.")
            except Exception as e:
                logger.error(f"Failed to initialise Gemini Client: {e}")
                self.client = None
        else:
            logger.info("Running in Demo Mock Mode (No GEMINI_API_KEY or package missing).")

    def is_mock_mode(self) -> bool:
        return self.client is None

    def analyse_paper(self, title: str, authors: str, full_text: str) -> Dict[str, Any]:
        """Generates a structured PhD-level analysis of the academic paper."""
        if self.is_mock_mode():
            return self._generate_mock_analysis(title, authors)
            
        prompt = f"""
You are an expert PhD academic reviewer. Analyse the following research paper:
Title: {title}
Authors: {authors}

Paper Text Content:
{full_text[:80000]} # Safe truncation for token limits

Provide a comprehensive, high-quality critique and summary. Focus on technical rigor and avoid superficial summaries.
"""
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PaperAnalysis,
                    temperature=0.2
                )
            )
            # Parse the JSON response
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error during Gemini paper analysis: {e}")
            # Fallback to mock on error
            return self._generate_mock_analysis(title, authors)

    def chat_about_paper(self, title: str, sections: Dict[str, Any], chat_history: List[Dict[str, str]], query: str) -> str:
        """Answers user query about the paper using context-grounded retrieval."""
        if self.is_mock_mode():
            return self._generate_mock_chat_reply(title, query)
            
        # Build context from relevant sections
        # To avoid exceeding tokens, we find the most relevant sections based on keyword matching
        relevant_text = ""
        query_words = set(query.lower().split())
        
        scored_sections = []
        for sect_name, sect_data in sections.items():
            sect_text = sect_data.get("text", "")
            # Simple keyword overlap scoring
            score = sum(1 for w in query_words if w in sect_text.lower())
            scored_sections.append((score, sect_name, sect_text))
            
        # Sort by score descending and take top 3 sections
        scored_sections.sort(reverse=True, key=lambda x: x[0])
        
        for score, name, text in scored_sections[:3]:
            relevant_text += f"\n--- Section: {name.replace('_', ' ').title()} ---\n{text[:15000]}\n"
            
        # Build chat history context
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
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini chat: {e}")
            return f"An error occurred while connecting to the LLM: {str(e)}"

    def _generate_mock_analysis(self, title: str, authors: str) -> Dict[str, Any]:
        """Generates domain-aware placeholder content if Gemini API is unavailable."""
        t_lower = title.lower()
        
        # Domain detection heuristics
        if any(w in t_lower for w in ["neural", "learning", "network", "transformer", "bert", "gpt", "model", "llm", "ai"]):
            domain = "deep_learning"
        elif any(w in t_lower for w in ["db", "database", "sql", "query", "storage", "transaction", "index"]):
            domain = "databases"
        elif any(w in t_lower for w in ["security", "crypto", "attack", "exploit", "privacy", "malware"]):
            domain = "security"
        else:
            domain = "general"

        mock_templates = {
            "deep_learning": {
                "synopsis": f"This research presents a novel architecture aiming to optimise training efficiency and representation capability in neural network tasks. Addressing the bottlenecks in current attention-based frameworks, the paper '{title}' investigates gradient dynamics and weight initialisation strategies.",
                "contributions": [
                    "Introduces a modified self-attention head topology that reduces quadratic computation complexity to O(N log N).",
                    "Establishes a mathematical proof of convergence for the proposed adaptive optimiser in non-convex loss surfaces.",
                    "Provides extensive empirical benchmarking showing a 15% reduction in wall-clock training time on standard datasets."
                ],
                "methodology": "The model utilises a layered tensor operations design implemented in PyTorch. Experiments were conducted using 8x NVIDIA H100 GPUs. The dataset consists of standard ImageNet/WikiText preprocessed segments, with a batch size of 256 and AdamW optimiser parameterisation (lr=3e-4, weight_decay=0.01).",
                "critical_review": [
                    "The baseline comparisons do not include some recent state-of-the-art tokenizers, limiting the strength of the speed-up claims.",
                    "Hyperparameter tuning details are scarce; it is unclear how sensitive the convergence rate is to the learning rate scheduler.",
                    "The evaluation lacks real-world deployment tests, focusing only on synthetic benchmarks."
                ],
                "future_work": [
                    "Evaluate the architecture on resource-constrained edge systems.",
                    "Extend the mathematical proofs to accommodate dynamic routing mechanisms.",
                    "Investigate mixed-precision quantisation (FP8/INT4) for inference scaling."
                ],
                "keywords": ["Transformers", "Self-Attention", "Gradient Convergence", "Computational Complexity", "PyTorch", "Optimisers"]
            },
            "databases": {
                "synopsis": f"The paper '{title}' tackles concurrent transaction management bottlenecks in highly distributed, scale-out databases. The authors propose a decentralized consensus protocol that eliminates lock contention in mixed read-write analytical workloads.",
                "contributions": [
                    "Proposes a zero-lock distributed replication strategy for hot-spot database shards.",
                    "Develops a novel multi-version concurrency control (MVCC) garbage collection protocol.",
                    "Demonstrates scaling throughput linear up to 128 replica nodes."
                ],
                "methodology": "The authors implement their prototype in Rust. Benchmarks are evaluated on AWS EC2 clusters using YCSB and TPC-C workload generators. Dynamic latency measurements are captured at the microsecond scale across variable network jitter profiles.",
                "critical_review": [
                    "The system relies on highly synchronized physical clocks (GPS/Atomic), which are expensive and unavailable in commodity cloud clusters.",
                    "Recovery paths and edge failure scenarios (e.g., split-brain network partition) are not thoroughly tested.",
                    "Storage overhead of the MVCC logs increases exponentially under long-running transactions."
                ],
                "future_work": [
                    "Incorporate logical hybrid-logical clocks to remove hardware dependencies.",
                    "Optimise memory compaction rates for write-heavy workloads.",
                    "Integrate automated index building using reinforcement learning."
                ],
                "keywords": ["Distributed Systems", "MVCC", "Consensus Protocols", "Transaction Isolation", "TPC-C", "AWS EC2"]
            },
            "security": {
                "synopsis": f"Addressing cryptographic vulnerabilities in communication channels, '{title}' outlines a side-channel analysis framework capable of extracting secret keys from hardware security modules. The authors construct both the vulnerability model and its corresponding mitigations.",
                "contributions": [
                    "Identifies a new cache-timing leakage pathway in popular cryptographic libraries.",
                    "Formulates a robust mathematical modeling of electromagnetic radiation leakages.",
                    "Designs a low-overhead software patch that achieves constant-time execution."
                ],
                "methodology": "The side-channel capturing rig consists of a digital oscilloscope measuring power rail fluctuations at 1 GS/s. Cryptographic operations are run on an ARM Cortex-M4 microcontroller. The leakage is analysed using Test Vector Leakage Assessment (TVLA) methodologies.",
                "critical_review": [
                    "The attack requires physical access to the device and expensive lab equipment, limiting remote exploit feasibility.",
                    "Mitigation patches lead to a 5% CPU clock cycle overhead in core cryptography operations.",
                    "The authors only test the vulnerability against standard AES implementations, leaving post-quantum algorithms unverified."
                ],
                "future_work": [
                    "Extend side-channel vulnerability testing to lattice-based post-quantum cryptography.",
                    "Develop compiler-level automated constant-time enforcement flags.",
                    "Apply deep learning models to improve signal-to-noise ratio in low-sample TVLA tests."
                ],
                "keywords": ["Side-Channel Analysis", "Timing Attacks", "Hardware Security", "AES Encryption", "TVLA", "Cortex-M4"]
            },
            "general": {
                "synopsis": f"This academic paper titled '{title}' explores domain-specific structures and methodologies to improve performance and consistency. It reviews previous academic baselines, highlights architectural flaws, and proposes a systematic framework for solution development.",
                "contributions": [
                    "Identifies critical theoretical limitations in current baseline models.",
                    "Introduces a generalized framework that unifies disparate methodologies in the literature.",
                    "Validates the framework across three distinct empirical testbeds."
                ],
                "methodology": "A multi-phase qualitative and quantitative evaluation methodology. The theoretical framework is modeled using mathematical abstractions, and verified against numerical simulation results. Standard statistical tests (t-tests, ANOVA) are applied to establish statistical significance.",
                "critical_review": [
                    "The assumptions in the theoretical model are highly idealized and may not translate to noisy environments.",
                    "Baseline comparisons are limited to outdated methods from 2021.",
                    "Statistical significance is demonstrated on small sample sizes (N=30)."
                ],
                "future_work": [
                    "Validate the framework using a larger scale clinical/practical trial.",
                    "Incorporate dynamic feedback loops into the system model.",
                    "Investigate automated parameter optimisation methods."
                ],
                "keywords": ["Research Framework", "Comparative Analysis", "System Design", "Empirical Evaluation", "Statistical Significance"]
            }
        }
        
        return mock_templates[domain]

    def _generate_mock_chat_reply(self, title: str, query: str) -> str:
        """Returns a plausible context-aware response based on key search words."""
        q = query.lower()
        if "methodology" in q or "how" in q or "experiment" in q:
            return f"According to the methodology section of **'{title}'**, the system utilises a custom pipeline. Text/data processing is done in stages, using localised optimisation parameters. The baseline performance was evaluated against benchmark datasets, indicating significant improvements in accuracy and latency."
        elif "contribution" in q or "novelty" in q or "what is new" in q:
            return f"The main contributions of **'{title}'** include:\n1. Formulating a novel optimisation framework to address bottleneck inefficiencies.\n2. Implementing a production-ready prototype that shows competitive results.\n3. Creating an open-source benchmark suite for future research comparisons."
        elif "limitation" in q or "weakness" in q or "critique" in q or "fault" in q:
            return f"The critical analysis of **'{title}'** reveals a few limitations:\n- Idealized system assumptions that may not hold under complex real-world conditions.\n- Lack of thorough comparison with the latest 2025/2026 baselines.\n- Some hardware configurations are hard-coded, reducing portability."
        else:
            return f"In the context of the paper **'{title}'**, the research focuses on resolving complex structural issues. If you ask specifically about its *Methodology*, *Key Contributions*, or *Limitations*, I can retrieve specific sections and explain how the authors designed their solutions."
