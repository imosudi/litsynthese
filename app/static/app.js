document.addEventListener("DOMContentLoaded", () => {
    // Application State
    const state = {
        projects: [],
        selectedProjectId: localStorage.getItem("selectedProjectId") || "default",
        selectedModelId: localStorage.getItem("selectedModelId") || "gemini",
        papers: [],
        selectedPaper: null,
        chatHistories: {}, // Map of paperId -> chatMessages
        currentTheme: localStorage.getItem("theme") || "dark"
    };

    // DOM Elements
    const projectSelect = document.getElementById("project-select");
    const newProjectBtn = document.getElementById("new-project-btn");
    const deleteProjectBtn = document.getElementById("delete-project-btn");
    const modelSelect = document.getElementById("model-select");

    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressStatus = document.getElementById("progress-status");
    const papersList = document.getElementById("papers-list");
    const themeToggle = document.getElementById("theme-toggle");
    
    const welcomeView = document.getElementById("welcome-view");
    const analysisView = document.getElementById("analysis-view");
    
    const paperTitle = document.getElementById("paper-title");
    const paperAuthors = document.getElementById("paper-authors");
    const paperYear = document.getElementById("paper-year");
    const paperPages = document.getElementById("paper-pages");
    const exportBtn = document.getElementById("export-summary-btn");
    
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");
    
    // Summary Tab Elements
    const summarySynopsis = document.getElementById("summary-synopsis");
    const summaryContributions = document.getElementById("summary-contributions");
    const summaryMethodology = document.getElementById("summary-methodology");
    const summaryCritique = document.getElementById("summary-critique");
    const summaryFuture = document.getElementById("summary-future");
    
    // Citations Tab Elements
    const referencesList = document.getElementById("references-list");
    const contextsContainer = document.getElementById("contexts-container");
    
    // Chat Tab Elements
    const chatHistory = document.getElementById("chat-history");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    
    // Keywords Tab Elements
    const keywordsCloud = document.getElementById("keywords-cloud");

    // Sidebar Navigation Elements
    const navDashboard = document.getElementById("nav-dashboard");
    const navProfile = document.getElementById("nav-profile");
    const profileView = document.getElementById("profile-view");

    // Profile View stats elements
    const statProjectsCount = document.getElementById("stat-projects-count");
    const statPapersCount = document.getElementById("stat-papers-count");

    // Indicators
    const indicatorGemini = document.getElementById("indicator-gemini");
    const indicatorGroq = document.getElementById("indicator-groq");
    const indicatorOpenrouter = document.getElementById("indicator-openrouter");

    // Theme names map - professional & relevant to scientific research assistant themes
    const themeNames = {
        "dark": "Amethyst Dark",
        "light": "Lumina Light",
        "google": "Aura Blue",
        "samsung": "OLED Eclipse",
        "microsoft": "Nordic Frost",
        "hyundai": "Deep Steel"
    };

    const themeFlashNameLabel = document.getElementById("theme-flash-name");

    // Initialise Theme and Persistence
    function setApplicationTheme(themeVal, triggerFlash = false) {
        state.currentTheme = themeVal;
        document.documentElement.setAttribute("data-theme", themeVal);
        localStorage.setItem("theme", themeVal);
        
        if (triggerFlash && themeFlashNameLabel) {
            themeFlashNameLabel.textContent = themeNames[themeVal] || themeVal;
            themeFlashNameLabel.classList.add("show");
            
            if (state.themeFlashTimeout) {
                clearTimeout(state.themeFlashTimeout);
            }
            state.themeFlashTimeout = setTimeout(() => {
                themeFlashNameLabel.classList.remove("show");
            }, 1500);
        }
    }

    // Initialize with false so we don't flash on page load
    setApplicationTheme(state.currentTheme, false);

    // Theme Toggle Handler (Cycles through available themes)
    const availableThemes = ["dark", "light", "google", "samsung", "microsoft", "hyundai"];
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            let currentIndex = availableThemes.indexOf(state.currentTheme);
            let nextIndex = (currentIndex + 1) % availableThemes.length;
            setApplicationTheme(availableThemes[nextIndex], true);
        });
    }

    // View Switching Logic
    function switchView(viewName) {
        if (viewName === "dashboard") {
            if (navDashboard) navDashboard.classList.add("active");
            if (navProfile) navProfile.classList.remove("active");
            if (profileView) profileView.classList.add("hidden");
            
            if (state.selectedPaper) {
                welcomeView.classList.add("hidden");
                analysisView.classList.remove("hidden");
            } else {
                welcomeView.classList.remove("hidden");
                analysisView.classList.add("hidden");
            }
        } else if (viewName === "profile") {
            if (navDashboard) navDashboard.classList.remove("active");
            if (navProfile) navProfile.classList.add("active");
            if (profileView) profileView.classList.remove("hidden");
            welcomeView.classList.add("hidden");
            analysisView.classList.add("hidden");
            
            updateProfileMetrics();
            checkAPIConnectivity();
        }
    }

    if (navDashboard) navDashboard.addEventListener("click", () => switchView("dashboard"));
    if (navProfile) navProfile.addEventListener("click", () => switchView("profile"));

    function updateProfileMetrics() {
        if (statProjectsCount) {
            statProjectsCount.textContent = state.projects.length;
        }
        if (statPapersCount) {
            statPapersCount.textContent = state.papers.length;
        }
    }

    async function checkAPIConnectivity() {
        try {
            const res = await fetch("/api/api-status");
            if (res.ok) {
                const status = await res.json();
                
                if (indicatorGemini) {
                    if (status.gemini) {
                        indicatorGemini.textContent = "Connected";
                        indicatorGemini.classList.add("active");
                    } else {
                        indicatorGemini.textContent = "Not Configured";
                        indicatorGemini.classList.remove("active");
                    }
                }

                if (indicatorGroq) {
                    if (status.groq) {
                        indicatorGroq.textContent = "Connected";
                        indicatorGroq.classList.add("active");
                    } else {
                        indicatorGroq.textContent = "Not Configured";
                        indicatorGroq.classList.remove("active");
                    }
                }

                if (indicatorOpenrouter) {
                    if (status.openrouter) {
                        indicatorOpenrouter.textContent = "Connected";
                        indicatorOpenrouter.classList.add("active");
                    } else {
                        indicatorOpenrouter.textContent = "Not Configured";
                        indicatorOpenrouter.classList.remove("active");
                    }
                }
            }
        } catch (err) {
            console.error("Failed to check API connectivity:", err);
        }
    }

    // Run API connectivity check on page load as well
    checkAPIConnectivity();

    // Project Selection and Management Handlers
    async function fetchProjectsList() {
        try {
            const res = await fetch("/api/projects");
            if (res.ok) {
                state.projects = await res.json();
                
                const exists = state.projects.some(p => p.id === state.selectedProjectId);
                if (!exists && state.projects.length > 0) {
                    state.selectedProjectId = state.projects[0].id;
                    localStorage.setItem("selectedProjectId", state.selectedProjectId);
                }
                
                renderProjectsDropdown();
            }
        } catch (e) {
            console.error("Error fetching projects list", e);
        }
    }

    function renderProjectsDropdown() {
        projectSelect.innerHTML = "";
        state.projects.forEach(proj => {
            const opt = document.createElement("option");
            opt.value = proj.id;
            opt.textContent = proj.name;
            opt.selected = proj.id === state.selectedProjectId;
            projectSelect.appendChild(opt);
        });
        
        if (state.projects.length > 0) {
            deleteProjectBtn.style.display = "flex";
        } else {
            deleteProjectBtn.style.display = "none";
        }
    }

    newProjectBtn.addEventListener("click", async () => {
        const name = prompt("Enter the name for the new review project:");
        if (!name || !name.trim()) return;
        
        try {
            const res = await fetch("/api/projects", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ name: name.trim() })
            });
            if (res.ok) {
                const newProj = await res.json();
                state.selectedProjectId = newProj.id;
                localStorage.setItem("selectedProjectId", state.selectedProjectId);
                
                switchView("dashboard");
                state.selectedPaper = null;
                
                await fetchProjectsList();
                await fetchPapersList();
            } else {
                const err = await res.json();
                alert(err.detail || "Failed to create project.");
            }
        } catch (e) {
            console.error("Error creating project", e);
            alert("Connection error while creating project.");
        }
     });
 
     deleteProjectBtn.addEventListener("click", async () => {
         const activeProj = state.projects.find(p => p.id === state.selectedProjectId);
         const name = activeProj ? activeProj.name : state.selectedProjectId;
         if (!confirm(`Are you sure you want to delete project "${name}"?\nThis will permanently remove all its uploaded papers and reviews.`)) {
             return;
         }
         
         try {
             const res = await fetch(`/api/project/${state.selectedProjectId}`, {
                 method: "DELETE"
             });
             if (res.ok) {
                 state.selectedProjectId = "";
                 localStorage.setItem("selectedProjectId", "");
                 
                 switchView("dashboard");
                 state.selectedPaper = null;
                 
                 await fetchProjectsList();
                 await fetchPapersList();
             } else {
                 const err = await res.json();
                 alert(err.detail || "Failed to delete project.");
             }
         } catch (e) {
             console.error("Error deleting project", e);
             alert("Connection error while deleting project.");
         }
     });
 
     projectSelect.addEventListener("change", (e) => {
         state.selectedProjectId = e.target.value;
         localStorage.setItem("selectedProjectId", state.selectedProjectId);
         
         switchView("dashboard");
         state.selectedPaper = null;
         
         fetchPapersList();
     });

    if (modelSelect) {
        modelSelect.value = state.selectedModelId;
        modelSelect.addEventListener("change", (e) => {
            state.selectedModelId = e.target.value;
            localStorage.setItem("selectedModelId", state.selectedModelId);
        });
    }

    // 1. Ingestion / Upload Event Listeners
    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    ["dragleave", "dragend"].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    function handleFileUpload(file) {
        const isPdf = file.type === "application/pdf" || (file.name && file.name.toLowerCase().endsWith(".pdf"));
        if (!isPdf) {
            alert("Please select a valid PDF file.");
            fileInput.value = "";
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        // Show progress UI
        progressContainer.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressStatus.textContent = "Uploading PDF...";

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/api/project/${state.selectedProjectId}/upload?model=${state.selectedModelId}`, true);

        // Track upload progress
        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = `${percent}%`;
                if (percent === 100) {
                    progressStatus.textContent = `Analysing Paper with LLM (${state.selectedModelId})...`;
                } else {
                    progressStatus.textContent = `Uploading PDF (${percent}%)...`;
                }
            }
        });

        // Request complete
        xhr.onload = function() {
            fileInput.value = ""; // Reset input value
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                progressStatus.textContent = "Parsing Complete!";
                progressBar.style.width = "100%";
                setTimeout(() => {
                    progressContainer.classList.add("hidden");
                }, 1000);
                
                // Refresh list and select paper
                fetchPapersList().then(() => {
                    selectPaper(response.id);
                });
            } else {
                let errorMsg = "Failed to upload and parse paper.";
                try {
                    const err = JSON.parse(xhr.responseText);
                    errorMsg = err.detail || errorMsg;
                } catch(e) {}
                alert(errorMsg);
                progressContainer.classList.add("hidden");
            }
        };

        xhr.onerror = function() {
            fileInput.value = ""; // Reset input value
            alert("A network error occurred during upload.");
            progressContainer.classList.add("hidden");
        };

        xhr.send(formData);
    }

    // 2. Fetch Ingested Papers List
    async function fetchPapersList() {
        try {
            const res = await fetch(`/api/project/${state.selectedProjectId}/papers`);
            if (res.ok) {
                state.papers = await res.json();
                renderPapersList();
            }
        } catch (e) {
            console.error("Error fetching papers list", e);
        }
    }

    function renderPapersList() {
        if (state.papers.length === 0) {
            papersList.innerHTML = '<div class="empty-list-state">No papers uploaded yet</div>';
            return;
        }

        papersList.innerHTML = "";
        state.papers.forEach(paper => {
            const el = document.createElement("div");
            el.className = `paper-item ${state.selectedPaper && state.selectedPaper.id === paper.id ? 'active' : ''}`;
            el.innerHTML = `
                <h4>${paper.title}</h4>
                <p>${paper.authors.split(',')[0]} et al. • ${paper.year}</p>
            `;
            el.addEventListener("click", () => selectPaper(paper.id));
            papersList.appendChild(el);
        });
    }

    // 3. Selection & Workspace Loading
    async function selectPaper(id) {
        try {
            document.querySelectorAll(".paper-item").forEach(item => item.classList.remove("active"));
            
            const res = await fetch(`/api/project/${state.selectedProjectId}/paper/${id}`);
            if (res.ok) {
                state.selectedPaper = await res.json();
                renderPapersList();
                
                // Toggle view states
                switchView("dashboard");
                
                // Render paper contents
                renderPaperHeader();
                renderSummaryTab();
                renderCitationsTab();
                renderChatTab();
                renderKeywordsTab();
                
                // Reset active tab to summary
                switchTab("summary");
            }
        } catch (e) {
            console.error("Error fetching paper details", e);
            alert("Error opening selected paper.");
        }
    }

    function renderPaperHeader() {
        paperTitle.textContent = state.selectedPaper.metadata.title;
        paperAuthors.textContent = state.selectedPaper.metadata.authors;
        paperYear.textContent = state.selectedPaper.metadata.year;
        paperPages.textContent = `${state.selectedPaper.metadata.pages_count} pages`;
        
        exportBtn.onclick = () => {
            window.location.href = `/api/project/${state.selectedProjectId}/paper/${state.selectedPaper.id}/export`;
        };
    }

    // 4. Tab Navigation Switcher
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabName = btn.getAttribute("data-tab");
            switchTab(tabName);
        });
    });

    function switchTab(tabName) {
        tabBtns.forEach(btn => {
            if (btn.getAttribute("data-tab") === tabName) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        tabPanes.forEach(pane => {
            if (pane.id === `tab-${tabName}`) {
                pane.classList.add("active");
            } else {
                pane.classList.remove("active");
            }
        });
    }

    // 5. Render Structured Review
    function renderSummaryTab() {
        const analysis = state.selectedPaper.analysis;
        
        summarySynopsis.textContent = analysis.synopsis || "No synopsis extracted.";
        summaryMethodology.textContent = analysis.methodology || "No methodology parameters available.";
        
        // Render lists
        renderList(summaryContributions, analysis.contributions);
        renderList(summaryCritique, analysis.critical_review);
        renderList(summaryFuture, analysis.future_work);
    }

    function renderList(container, items) {
        container.innerHTML = "";
        if (!items || items.length === 0) {
            container.innerHTML = "<li>No details extracted.</li>";
            return;
        }
        items.forEach(item => {
            const li = document.createElement("li");
            li.textContent = item;
            container.appendChild(li);
        });
    }

    // 6. Render Citation Linker
    function renderCitationsTab() {
        const refs = state.selectedPaper.references || [];
        referencesList.innerHTML = "";
        contextsContainer.innerHTML = '<div class="empty-context-state">Select a reference on the left to see where it was cited in the paper.</div>';
        
        if (refs.length === 0) {
            referencesList.innerHTML = '<div class="empty-list-state">No bibliography items extracted.</div>';
            return;
        }

        refs.forEach(ref => {
            const card = document.createElement("div");
            card.className = "ref-card";
            card.innerHTML = `
                <div class="ref-index">[${ref.index}]</div>
                <div class="ref-text">${ref.raw_text}</div>
                <div class="ref-citation-count">${ref.citations.length}</div>
            `;
            
            card.addEventListener("click", () => {
                document.querySelectorAll(".ref-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                renderCitationContexts(ref);
            });
            
            referencesList.appendChild(card);
        });
    }

    function renderCitationContexts(ref) {
        contextsContainer.innerHTML = "";
        if (ref.citations.length === 0) {
            contextsContainer.innerHTML = `<div class="empty-context-state">No in-text citations found for reference [${ref.index}]. This reference might be listed but not directly cited.</div>`;
            return;
        }

        ref.citations.forEach(cit => {
            const contextCard = document.createElement("div");
            contextCard.className = "context-card";
            contextCard.innerHTML = `
                <p class="context-text">"...${highlightCitation(cit.context, ref.index)}..."</p>
                <div class="context-meta">
                    <span>Page ${cit.page}</span>
                    <span>Section: ${cit.section}</span>
                </div>
            `;
            contextsContainer.appendChild(contextCard);
        });
    }

    function highlightCitation(sentence, index) {
        const escapedIndex = index.toString();
        const regex = new RegExp(`(\\[[^\\]]*?\\b${escapedIndex}\\b.*?\\])`, "g");
        return sentence.replace(regex, `<span style="background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: bold;">$1</span>`);
    }

    // 7. Render Chat Window
    function renderChatTab() {
        const id = state.selectedPaper.id;
        
        if (!state.chatHistories[id]) {
            state.chatHistories[id] = [];
        }
        
        chatHistory.innerHTML = `
            <div class="system-message">
                Hello! I have fully ingested this paper. Ask me anything about its methodology, results, contributions, or references, and I will answer grounded directly in the text.
            </div>
        `;
        
        state.chatHistories[id].forEach(msg => {
            appendChatBubble(msg.role, msg.content);
        });
    }

    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query || !state.selectedPaper) return;

        const paperId = state.selectedPaper.id;
        
        appendChatBubble("user", query);
        chatInput.value = "";
        
        state.chatHistories[paperId].push({ role: "user", content: query });
        
        const typingBubble = appendChatBubble("assistant", "Thinking...");
        
        try {
            const res = await fetch(`/api/project/${state.selectedProjectId}/paper/${paperId}/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    query: query,
                    history: state.chatHistories[paperId].slice(0, -1),
                    model: state.selectedModelId
                })
            });
            
            if (res.ok) {
                const data = await res.json();
                typingBubble.innerHTML = formatMarkdown(data.reply);
                state.chatHistories[paperId].push({ role: "assistant", content: data.reply });
            } else {
                typingBubble.textContent = "Error: Failed to obtain response.";
            }
        } catch (err) {
            console.error("Chat error", err);
            typingBubble.textContent = "A connection error occurred.";
        }
        
        chatHistory.scrollTop = chatHistory.scrollHeight;
    });

    function appendChatBubble(role, content) {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${role}`;
        
        if (role === "assistant" && content !== "Thinking...") {
            bubble.innerHTML = formatMarkdown(content);
        } else {
            bubble.textContent = content;
        }
        
        chatHistory.appendChild(bubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return bubble;
    }

    function formatMarkdown(text) {
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\* (.*?)/g, '<br>• $1')
            .replace(/\n\d+\. (.*?)/g, '<br>$1')
            .replace(/\n/g, '<br>');
        return formatted;
    }

    // 8. Keywords Tab
    function renderKeywordsTab() {
        const keywords = state.selectedPaper.analysis.keywords || [];
        keywordsCloud.innerHTML = "";
        
        if (keywords.length === 0) {
            keywordsCloud.innerHTML = '<div class="empty-list-state">No concepts extracted.</div>';
            return;
        }

        keywords.forEach(kw => {
            const badge = document.createElement("span");
            badge.className = "keyword-badge";
            badge.textContent = kw;
            keywordsCloud.appendChild(badge);
        });
    }

    // Initialise loading sequence
    fetchProjectsList().then(() => {
        fetchPapersList();
    });
});
