# LitSynthese

[![License](https://img.shields.io/github/license/imosudi/litsynthese)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/imosudi/litsynthese)](https://github.com/imosudi/litsynthese/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/imosudi/litsynthese)](https://github.com/imosudi/litsynthese/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/imosudi/litsynthese)](https://github.com/imosudi/litsynthese/issues)
[![Python Version](https://img.shields.io/badge/Python-3.14-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini_API-2.5_Flash-blueviolet.svg?logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![Groq](https://img.shields.io/badge/Groq_API-LLaMA--3.1-orange.svg)](https://groq.com/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--Model-blue.svg)](https://openrouter.ai/)

An automated academic paper ingestion, critique, and summarisation tool designed for researchers and students. It combines custom heuristic PDF parsing, citation bibliography linking, structured multi-aspect LLM analysis (powered by Gemini API, Groq, and OpenRouter), and an interactive context-grounded chat room.

## Technical Architecture

![Technical Architecture](app/static/architecture.svg)

### 1. Document Structuring & Parser
* **Section Segmentation:** Scans PDF text page-by-page using `pypdf`, mapping section headers (such as Abstract, Introduction, Methodology, Experiments, Results, Conclusions, and References) to their respective start and end pages.
* **Bibliography Extraction:** Dynamically parses the `References` section, extracting individual publication entries (supporting both IEEE bracketed lists and APA-style alphabetized indexes).
* **In-Text Citation Mapping:** Maps every reference to its exact occurrences in the body text. Compiled citation instances display context sentences, page numbers, and parent sections to trace where and why work was cited.

### 2. PhD-Level LLM Critique & Multi-Model Synthesis
* **Multi-Model Support:** Native integration with Google's official Gemini SDK and API integration with Groq and OpenRouter. It dynamically routes requests to standard and custom large language models:
  * **Gemini 2.5 Flash** (via the native `google-genai` SDK)
  * **LLaMA 3.1 (8B & 70B)** (via Groq API or OpenRouter API)
  * **Qwen 2.5 (72B)** (via OpenRouter API)
  * **Gemma 4 (31B)** (via OpenRouter API)
* **Structured Synthesis:** Generates a 6-aspect academic evaluation utilizing the selected LLM:
  * **Executive Synopsis:** High-level problem statement, target application, and final outcomes.
  * **Key Contributions:** List of novel designs, proofs, algorithms, or experimental discoveries.
  * **Methodology & Framework:** Synthesis of datasets, training regimes, mathematical models, or hardware setups.
  * **Critical Review:** Rigorous review detailing baseline weaknesses, limitations, missing evaluations, or unproved assumptions.
  * **Future Scope:** Recommended concrete directions for follow-up studies.
  * **Keyword Tagging:** Conceptual scientific keywords with relevance scores.
* **Mock Mode Fallback:** Automatically switches to an adaptive, domain-aware mock generator if API keys are missing, enabling local evaluation out of the box.

### 3. Contextual Research Q&A
* Implements a local keyword-overlap Retrieval-Augmented Generation (RAG) system. User questions are matched against the paper's section contents to retrieve relevant context.
* The assistant replies with evidence grounded in the text, citing page numbers and section names (e.g. `[Methodology Section]`, `[Page 4]`).

---

## Technical Stack
* **Backend:** Python 3.14, FastAPI, Uvicorn, PyPDF, Google GenAI SDK (`google-genai`), Python-Dotenv.
* **Frontend:** HTML5 (Semantic Structure), Vanilla CSS (Responsive Flexbox Grid, Glassmorphic Styling, and Animations), Vanilla JavaScript (Drag-Drop Ingestion, XMLHttp progress tracking, state management, and markdown formatting).

---

## Getting Started

### 1. Installation
We have provided a helper bash script `setup.sh` that detects missing dependencies, requests permission to install APT packages (like `python3-pip` and `python3-venv`), creates a localized Python virtual environment, and installs requirements safely.

Run the setup script in your terminal:
```bash
chmod +x setup.sh
./setup.sh
```

During setup, you will be prompted to enter API keys for the model providers:
* `GEMINI_API_KEY` (to run the default Gemini 2.5 Flash model)
* `GROQ_API_KEY` (to run LLaMA 3.1 models via Groq)
* `OPENROUTER_API_KEY` (to run LLaMA, Qwen, and Gemma models via OpenRouter)

If left empty, the application will run in **Demo Mock Mode** so you can test the interface locally immediately.

### 2. Starting the Application
If you choose not to start the server automatically during setup, you can launch it manually:
```bash
# Activate the virtual environment
source venv/bin/activate

# Launch the FastAPI web server
python3 main.py
```

Open your browser and navigate to:
[http://localhost:8000](http://localhost:8000) or your network IP address.

---

## Codebase Structure
* `setup.sh` - Interactive script to manage dependencies, pip virtualenv, and config.
* `requirements.txt` - Project dependencies list.
* `main.py` - Root entrypoint script that imports and runs the application server.
* `config.py` - Central application configuration parameters.
* `app/server.py` - FastAPI application initialisation, endpoints, and file management.
* `app/parser.py` - Academic paper text segmentation and citation-to-references mapping.
* `app/llm.py` - Gemini API SDK connector, structured response generation, and RAG search.
* `app/static/` - CSS, client-side JS, and image assets.
  * `styles.css` - Theme styles, glassmorphic card variables, and smooth animations.
  * `app.js` - Dynamic DOM controller, file uploader, and state machine.
* `app/templates/` - HTML templates.
  * `index.html` - Dashboard layout with sub-section panes and SVGs.

---

## GitHub Topics

To categorise the repository on GitHub, the following topics are recommended:
`academic-research`, `pdf-parser`, `rag`, `literature-review`, `gemini-api`, `llama3`, `qwen`, `gemma`, `fastapi`, `citation-linker`, `academic-papers`, `llm`, `groq`, `openrouter`

---

## 🪪 Licence

BSD 2-Clause License

Copyright © 2025 Isiaka Olukayode Mosudi

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED “AS IS” WITHOUT WARRANTY OF ANY KIND.

## 👤 Author

**Isiaka Olukayode Mosudi**  
MEng (Communications Engineering) | MSc (IoT & Smart Systems) | BEng (Electrical and Computer Engineering)  
Vienna, Austria

* **Email:** [imosudi@outlook.com](mailto:imosudi@outlook.com)
* **Website:** [mioemi.com](https://mioemi.com)
* **GitHub:** [github.com/imosudi](https://github.com/imosudi)

