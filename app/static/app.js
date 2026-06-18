document.addEventListener("DOMContentLoaded", () => {
    // Intercept fetch to automatically add Authorization token and handle 401s
    const originalFetch = window.fetch;
    window.fetch = async function (url, options) {
        options = options || {};
        options.headers = options.headers || {};
        
        const token = localStorage.getItem("access_token");
        if (token) {
            options.headers["Authorization"] = `Bearer ${token}`;
        }
        
        try {
            const response = await originalFetch(url, options);
            if (response.status === 401) {
                // If unauthorized and not auth-related call, log out
                if (!url.includes("/api/auth/login") && !url.includes("/api/auth/register")) {
                    logout();
                }
            }
            return response;
        } catch (error) {
            throw error;
        }
    };

    function logout() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_email");
        showAuthOverlay();
    }

    // Application State
    const state = {
        projects: [],
        selectedProjectId: localStorage.getItem("selectedProjectId") || "",
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
    const navMatrix = document.getElementById("nav-matrix");
    const navSynthesis = document.getElementById("nav-synthesis");
    const navProfile = document.getElementById("nav-profile");
    const profileView = document.getElementById("profile-view");
    const matrixView = document.getElementById("matrix-view");
    const synthesisView = document.getElementById("synthesis-view");

    // Matrix Elements
    const matrixTableBody = document.getElementById("matrix-table-body");
    const emptyMatrixState = document.getElementById("empty-matrix-state");
    const latexCodePreview = document.getElementById("latex-code-preview");
    const exportLatexBtn = document.getElementById("export-latex-btn");

    // Synthesis Elements
    const synthesisHistory = document.getElementById("synthesis-history");
    const synthesisForm = document.getElementById("synthesis-form");
    const synthesisInput = document.getElementById("synthesis-input");
    const synthesisErrorAlert = document.getElementById("synthesis-error-alert");

    // Profile View stats elements
    const statProjectsCount = document.getElementById("stat-projects-count");
    const statPapersCount = document.getElementById("stat-papers-count");

    // Indicators
    const indicatorGemini = document.getElementById("indicator-gemini");
    const indicatorGroq = document.getElementById("indicator-groq");
    const indicatorOpenrouter = document.getElementById("indicator-openrouter");

    // Auth DOM Elements
    const authOverlay = document.getElementById("auth-overlay");
    const authForm = document.getElementById("auth-form");
    const authEmail = document.getElementById("auth-email");
    const authPassword = document.getElementById("auth-password");
    const authSubmitBtn = document.getElementById("auth-submit-btn");
    const authToggleBtn = document.getElementById("auth-toggle-btn");
    const authToggleText = document.getElementById("auth-toggle-text");
    const authErrorAlert = document.getElementById("auth-error-alert");

    // Profile View edit elements
    const editProfileBtn = document.getElementById("edit-profile-btn");
    const cancelProfileBtn = document.getElementById("cancel-profile-btn");
    const saveProfileBtn = document.getElementById("save-profile-btn");
    const profileInfoView = document.getElementById("profile-info-view");
    const profileInfoForm = document.getElementById("profile-info-form");
    const logoutBtn = document.getElementById("logout-btn");

    let isRegisterMode = false;

    // Theme names map
    const themeNames = {
        "dark": "Amethyst Dark",
        "light": "Lumina Light",
        "google": "Aura Blue",
        "samsung": "OLED Eclipse",
        "microsoft": "Nordic Frost",
        "hyundai": "Deep Steel"
    };

    const themeFlashNameLabel = document.getElementById("theme-flash-name");

    // Authentication UI Logic
    function showAuthOverlay() {
        if (authOverlay) authOverlay.classList.remove("hidden");
    }

    function hideAuthOverlay() {
        if (authOverlay) authOverlay.classList.add("hidden");
    }

    if (authToggleBtn) {
        authToggleBtn.addEventListener("click", (e) => {
            e.preventDefault();
            isRegisterMode = !isRegisterMode;
            
            const recoveryFields = document.getElementById("register-recovery-fields");
            const qInput = document.getElementById("auth-question");
            const aInput = document.getElementById("auth-answer");
            const loginExtraRow = document.getElementById("login-extra-row");
            
            if (isRegisterMode) {
                document.querySelector(".auth-title").textContent = "Register";
                authToggleText.textContent = "Already have an account?";
                authToggleBtn.textContent = "Sign In";
                authSubmitBtn.textContent = "Create Account";
                if (recoveryFields) recoveryFields.classList.remove("hidden");
                if (qInput) qInput.required = true;
                if (aInput) aInput.required = true;
                if (loginExtraRow) loginExtraRow.classList.add("hidden");
            } else {
                document.querySelector(".auth-title").textContent = "LitSynthese";
                authToggleText.textContent = "New to LitSynthese?";
                authToggleBtn.textContent = "Create an Account";
                authSubmitBtn.textContent = "Sign In";
                if (recoveryFields) recoveryFields.classList.add("hidden");
                if (qInput) qInput.required = false;
                if (aInput) aInput.required = false;
                if (loginExtraRow) loginExtraRow.classList.remove("hidden");
            }
            authErrorAlert.classList.add("hidden");
        });
    }

    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = authEmail.value.trim();
            const password = authPassword.value;
            
            if (!email || !password) return;
            
            authSubmitBtn.disabled = true;
            authSubmitBtn.textContent = isRegisterMode ? "Registering..." : "Signing In...";
            authErrorAlert.classList.add("hidden");
            
            const endpoint = isRegisterMode ? "/api/auth/register" : "/api/auth/login";
            
            let bodyObj = { email, password };
            if (isRegisterMode) {
                bodyObj.security_question = document.getElementById("auth-question").value;
                bodyObj.security_answer = document.getElementById("auth-answer").value.trim();
            }
            
            try {
                const res = await originalFetch(endpoint, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(bodyObj)
                });
                
                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem("access_token", data.access_token);
                    localStorage.setItem("user_email", data.email);
                    
                    hideAuthOverlay();
                    
                    // Fetch profile info and load dashboard data
                    await fetchUserProfile();
                    await fetchProjectsList();
                    await fetchPapersList();
                } else {
                    const errData = await res.json();
                    authErrorAlert.textContent = errData.detail || "Authentication failed.";
                    authErrorAlert.classList.remove("hidden");
                }
            } catch (err) {
                console.error("Auth error:", err);
                authErrorAlert.textContent = "Connection error. Please try again.";
                authErrorAlert.classList.remove("hidden");
            } finally {
                authSubmitBtn.disabled = false;
                authSubmitBtn.textContent = isRegisterMode ? "Create Account" : "Sign In";
            }
        });
    }

    // Forgot Password Flow Handlers
    const forgotPasswordLink = document.getElementById("forgot-password-link");
    const forgotPasswordForm = document.getElementById("forgot-password-form");
    const recoveryEmail = document.getElementById("recovery-email");
    const recoveryAnswer = document.getElementById("recovery-answer");
    const recoveryNewPassword = document.getElementById("recovery-new-password");
    
    const recoveryStepEmail = document.getElementById("recovery-step-email");
    const recoveryStepQuestion = document.getElementById("recovery-step-question");
    const recoveryStepPassword = document.getElementById("recovery-step-password");
    
    const recoveryQuestionLabel = document.getElementById("recovery-question-label");
    const recoveryErrorAlert = document.getElementById("recovery-error-alert");
    const recoverySuccessAlert = document.getElementById("recovery-success-alert");
    
    const recoveryNextEmailBtn = document.getElementById("recovery-next-email-btn");
    const recoveryNextAnswerBtn = document.getElementById("recovery-next-answer-btn");
    const recoveryCancelBtn = document.getElementById("recovery-cancel-btn");

    function resetRecoveryWizard() {
        if (recoveryEmail) recoveryEmail.value = "";
        if (recoveryAnswer) recoveryAnswer.value = "";
        if (recoveryNewPassword) recoveryNewPassword.value = "";
        if (recoveryErrorAlert) recoveryErrorAlert.classList.add("hidden");
        if (recoverySuccessAlert) recoverySuccessAlert.classList.add("hidden");
        
        if (recoveryStepEmail) recoveryStepEmail.classList.remove("hidden");
        if (recoveryStepQuestion) recoveryStepQuestion.classList.add("hidden");
        if (recoveryStepPassword) recoveryStepPassword.classList.add("hidden");
    }

    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener("click", (e) => {
            e.preventDefault();
            if (authForm) authForm.classList.add("hidden");
            if (forgotPasswordForm) forgotPasswordForm.classList.remove("hidden");
            document.querySelector(".auth-toggle").classList.add("hidden");
            document.querySelector(".auth-title").textContent = "Recover Account";
            resetRecoveryWizard();
        });
    }

    if (recoveryCancelBtn) {
        recoveryCancelBtn.addEventListener("click", () => {
            if (forgotPasswordForm) forgotPasswordForm.classList.add("hidden");
            if (authForm) authForm.classList.remove("hidden");
            document.querySelector(".auth-toggle").classList.remove("hidden");
            document.querySelector(".auth-title").textContent = isRegisterMode ? "Register" : "LitSynthese";
        });
    }

    if (recoveryNextEmailBtn) {
        recoveryNextEmailBtn.addEventListener("click", async () => {
            const email = recoveryEmail.value.trim();
            if (!email) {
                recoveryErrorAlert.textContent = "Please enter your email address.";
                recoveryErrorAlert.classList.remove("hidden");
                return;
            }
            recoveryErrorAlert.classList.add("hidden");
            recoveryNextEmailBtn.disabled = true;
            
            try {
                const res = await originalFetch(`/api/auth/forgot-password/question?email=${encodeURIComponent(email)}`);
                if (res.ok) {
                    const data = await res.json();
                    recoveryQuestionLabel.textContent = `Security Question: ${data.question}`;
                    
                    recoveryStepEmail.classList.add("hidden");
                    recoveryStepQuestion.classList.remove("hidden");
                } else {
                    recoveryErrorAlert.textContent = "Failed to fetch security question.";
                    recoveryErrorAlert.classList.remove("hidden");
                }
            } catch (err) {
                console.error("Recovery error:", err);
                recoveryErrorAlert.textContent = "Connection error. Please try again.";
                recoveryErrorAlert.classList.remove("hidden");
            } finally {
                recoveryNextEmailBtn.disabled = false;
            }
        });
    }

    if (recoveryNextAnswerBtn) {
        recoveryNextAnswerBtn.addEventListener("click", () => {
            const answer = recoveryAnswer.value.trim();
            if (!answer) {
                recoveryErrorAlert.textContent = "Please provide your answer.";
                recoveryErrorAlert.classList.remove("hidden");
                return;
            }
            recoveryErrorAlert.classList.add("hidden");
            
            recoveryStepQuestion.classList.add("hidden");
            recoveryStepPassword.classList.remove("hidden");
        });
    }

    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = recoveryEmail.value.trim();
            const answer = recoveryAnswer.value.trim();
            const newPassword = recoveryNewPassword.value;
            
            if (!email || !answer || !newPassword) return;
            if (newPassword.length < 6) {
                recoveryErrorAlert.textContent = "Password must be at least 6 characters.";
                recoveryErrorAlert.classList.remove("hidden");
                return;
            }
            
            const submitBtn = document.getElementById("recovery-submit-btn");
            if (submitBtn) submitBtn.disabled = true;
            recoveryErrorAlert.classList.add("hidden");
            
            try {
                const res = await originalFetch("/api/auth/forgot-password/reset", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        email: email,
                        security_answer: answer,
                        new_password: newPassword
                    })
                });
                
                if (res.ok) {
                    recoverySuccessAlert.textContent = "Password reset successfully! Redirecting...";
                    recoverySuccessAlert.classList.remove("hidden");
                    
                    setTimeout(() => {
                        forgotPasswordForm.classList.add("hidden");
                        authForm.classList.remove("hidden");
                        document.querySelector(".auth-toggle").classList.remove("hidden");
                        document.querySelector(".auth-title").textContent = "LitSynthese";
                        isRegisterMode = false;
                        authEmail.value = email;
                        authPassword.value = "";
                        resetRecoveryWizard();
                    }, 2000);
                } else {
                    const errData = await res.json();
                    recoveryErrorAlert.textContent = errData.detail || "Verification failed.";
                    recoveryErrorAlert.classList.remove("hidden");
                    
                    recoveryStepPassword.classList.add("hidden");
                    recoveryStepQuestion.classList.remove("hidden");
                }
            } catch (err) {
                console.error("Reset submit error:", err);
                recoveryErrorAlert.textContent = "Connection error. Please try again.";
                recoveryErrorAlert.classList.remove("hidden");
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

    // Profile Customisation Logic
    async function fetchUserProfile() {
        try {
            const res = await fetch("/api/auth/me");
            if (res.ok) {
                const data = await res.json();
                
                // Set avatar initials
                const initial = (data.email[0] || 'R').toUpperCase();
                const avatarInit = document.getElementById("profile-avatar-initial");
                if (avatarInit) avatarInit.textContent = initial;
                
                const emailDisp = document.getElementById("profile-email-display");
                if (emailDisp) emailDisp.textContent = data.email;
                
                // Fill profile card details
                const profile = data.profile || {};
                const instVal = document.getElementById("profile-institution-val");
                if (instVal) instVal.textContent = profile.institution || "N/A";
                
                const domVal = document.getElementById("profile-domain-val");
                if (domVal) domVal.textContent = profile.research_domain || "N/A";
                
                const topicVal = document.getElementById("profile-topic-val");
                if (topicVal) topicVal.textContent = profile.research_topic || "N/A";
                
                // Pre-populate input fields
                const editInst = document.getElementById("edit-institution");
                if (editInst) editInst.value = profile.institution || "";
                
                const editDom = document.getElementById("edit-domain");
                if (editDom) editDom.value = profile.research_domain || "";
                
                const editTopic = document.getElementById("edit-topic");
                if (editTopic) editTopic.value = profile.research_topic || "";
                
                // If backend theme matches user's preferred theme, set it.
                if (profile.theme && profile.theme !== state.currentTheme) {
                    setApplicationTheme(profile.theme, false);
                }
            }
        } catch (e) {
            console.error("Error fetching user profile", e);
        }
    }

    if (editProfileBtn) {
        editProfileBtn.addEventListener("click", () => {
            if (profileInfoView) profileInfoView.classList.add("hidden");
            if (profileInfoForm) profileInfoForm.classList.remove("hidden");
        });
    }

    if (cancelProfileBtn) {
        cancelProfileBtn.addEventListener("click", () => {
            if (profileInfoView) profileInfoView.classList.remove("hidden");
            if (profileInfoForm) profileInfoForm.classList.add("hidden");
        });
    }

    if (profileInfoForm) {
        profileInfoForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const institution = document.getElementById("edit-institution").value.trim();
            const research_domain = document.getElementById("edit-domain").value.trim();
            const research_topic = document.getElementById("edit-topic").value.trim();
            
            try {
                const res = await fetch("/api/profile/update", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        institution,
                        research_domain,
                        research_topic,
                        theme: state.currentTheme
                    })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    
                    const instVal = document.getElementById("profile-institution-val");
                    if (instVal) instVal.textContent = data.profile.institution || "N/A";
                    
                    const domVal = document.getElementById("profile-domain-val");
                    if (domVal) domVal.textContent = data.profile.research_domain || "N/A";
                    
                    const topicVal = document.getElementById("profile-topic-val");
                    if (topicVal) topicVal.textContent = data.profile.research_topic || "N/A";
                    
                    if (profileInfoView) profileInfoView.classList.remove("hidden");
                    if (profileInfoForm) profileInfoForm.classList.add("hidden");
                } else {
                    alert("Failed to update profile.");
                }
            } catch (err) {
                console.error("Error updating profile:", err);
                alert("Connection error while updating profile.");
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            logout();
        });
    }

    // Initialise Theme and Persistence
    function setApplicationTheme(themeVal, triggerFlash = false) {
        state.currentTheme = themeVal;
        document.documentElement.setAttribute("data-theme", themeVal);
        localStorage.setItem("theme", themeVal);
        
        // Sync theme preference with backend if logged in
        if (localStorage.getItem("access_token")) {
            fetch("/api/profile/update", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ theme: themeVal })
            }).catch(err => console.error("Error saving theme to backend:", err));
        }

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

    // Custom Synthesis Settings persistence
    const extractionFocusSelect = document.getElementById("extraction-focus");
    const citationFormatSelect = document.getElementById("citation-format");
    const modelTemperatureInput = document.getElementById("model-temperature");
    const temperatureValSpan = document.getElementById("temperature-val");

    if (extractionFocusSelect) {
        extractionFocusSelect.value = localStorage.getItem("extractionFocus") || "standard";
        extractionFocusSelect.addEventListener("change", (e) => {
            localStorage.setItem("extractionFocus", e.target.value);
        });
    }

    if (citationFormatSelect) {
        citationFormatSelect.value = localStorage.getItem("citationFormat") || "apa";
        citationFormatSelect.addEventListener("change", (e) => {
            localStorage.setItem("citationFormat", e.target.value);
            if (state.selectedProjectId) {
                loadComparisonMatrix();
            }
        });
    }

    if (modelTemperatureInput) {
        const storedTemp = localStorage.getItem("modelTemperature") || "0.2";
        modelTemperatureInput.value = storedTemp;
        if (temperatureValSpan) temperatureValSpan.textContent = storedTemp;
        
        modelTemperatureInput.addEventListener("input", (e) => {
            if (temperatureValSpan) temperatureValSpan.textContent = e.target.value;
        });
        modelTemperatureInput.addEventListener("change", (e) => {
            localStorage.setItem("modelTemperature", e.target.value);
        });
    }

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
        if (navDashboard) navDashboard.classList.remove("active");
        if (navMatrix) navMatrix.classList.remove("active");
        if (navSynthesis) navSynthesis.classList.remove("active");
        if (navProfile) navProfile.classList.remove("active");

        if (welcomeView) welcomeView.classList.add("hidden");
        if (analysisView) analysisView.classList.add("hidden");
        if (matrixView) matrixView.classList.add("hidden");
        if (synthesisView) synthesisView.classList.add("hidden");
        if (profileView) profileView.classList.add("hidden");

        if (viewName === "dashboard") {
            if (navDashboard) navDashboard.classList.add("active");
            if (state.selectedPaper) {
                analysisView.classList.remove("hidden");
            } else {
                welcomeView.classList.remove("hidden");
            }
        } else if (viewName === "matrix") {
            if (navMatrix) navMatrix.classList.add("active");
            if (matrixView) matrixView.classList.remove("hidden");
            loadComparisonMatrix();
        } else if (viewName === "synthesis") {
            if (navSynthesis) navSynthesis.classList.add("active");
            if (synthesisView) synthesisView.classList.remove("hidden");
        } else if (viewName === "profile") {
            if (navProfile) navProfile.classList.add("active");
            if (profileView) profileView.classList.remove("hidden");
            updateProfileMetrics();
            checkAPIConnectivity();
        }
    }

    if (navDashboard) navDashboard.addEventListener("click", () => switchView("dashboard"));
    if (navMatrix) navMatrix.addEventListener("click", () => switchView("matrix"));
    if (navSynthesis) navSynthesis.addEventListener("click", () => switchView("synthesis"));
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
                if (!exists) {
                    state.selectedProjectId = state.projects.length > 0 ? state.projects[0].id : "";
                    localStorage.setItem("selectedProjectId", state.selectedProjectId);
                }
                
                renderProjectsDropdown();
            }
        } catch (e) {
            console.error("Error fetching projects list", e);
        }
    }

    function updateDropZoneState() {
        if (!dropZone) return;
        const dropText = dropZone.querySelector(".drop-text");
        const browseBtn = dropZone.querySelector(".browse-btn");
        if (!state.selectedProjectId) {
            dropZone.style.opacity = "0.5";
            if (dropText) dropText.textContent = "Create project first";
            if (browseBtn) browseBtn.style.pointerEvents = "none";
        } else {
            dropZone.style.opacity = "1";
            if (dropText) dropText.textContent = "Drag & drop paper PDF(s)";
            if (browseBtn) browseBtn.style.pointerEvents = "auto";
        }
    }

    function renderProjectsDropdown() {
        if (!projectSelect) return;
        projectSelect.innerHTML = "";
        
        if (state.projects.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "-- Create a Project --";
            opt.disabled = true;
            opt.selected = true;
            projectSelect.appendChild(opt);
        } else {
            state.projects.forEach(proj => {
                const opt = document.createElement("option");
                opt.value = proj.id;
                opt.textContent = proj.name;
                opt.selected = proj.id === state.selectedProjectId;
                projectSelect.appendChild(opt);
            });
        }
        
        if (state.projects.length > 0) {
            deleteProjectBtn.style.display = "flex";
        } else {
            deleteProjectBtn.style.display = "none";
        }

        // Toggle Guidance Alert
        const noProjectGuidance = document.getElementById("no-project-guidance");
        if (noProjectGuidance) {
            if (!state.selectedProjectId) {
                noProjectGuidance.classList.remove("d-none");
            } else {
                noProjectGuidance.classList.add("d-none");
            }
        }
        
        updateDropZoneState();
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
         
         const noProjectGuidance = document.getElementById("no-project-guidance");
         if (noProjectGuidance) {
             if (!state.selectedProjectId) {
                 noProjectGuidance.classList.remove("d-none");
             } else {
                 noProjectGuidance.classList.add("d-none");
             }
         }
         updateDropZoneState();
         
         switchView("dashboard");
         state.selectedPaper = null;
         
         if (synthesisHistory) {
             synthesisHistory.innerHTML = `
            <div class="system-message p-3 rounded mb-3" style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.95rem; border-radius: 8px;">
                Hello! I am the Cross-Document Synthesis Engine. I can compare, contrast, and synthesize answers across all papers in this active project. Ask me questions like:
                <ul class="mt-2 mb-0" style="padding-left: 20px; line-height: 1.6;">
                    <li><em>"Compare the experimental designs and datasets used."</em></li>
                    <li><em>"What are the common weaknesses or threats to validity across these studies?"</em></li>
                    <li><em>"How does the methodology of each paper address performance limits?"</em></li>
                </ul>
            </div>`;
         }
         
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
    dropZone.addEventListener("click", () => {
        if (!state.selectedProjectId) {
            alert("Please create or select a review project first.");
            return;
        }
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            if (!state.selectedProjectId) {
                alert("Please create or select a review project first.");
                fileInput.value = "";
                return;
            }
            handleMultipleFilesUpload(e.target.files);
            fileInput.value = "";
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
        if (!state.selectedProjectId) {
            alert("Please create or select a review project first.");
            return;
        }
        if (e.dataTransfer.files.length > 0) {
            handleMultipleFilesUpload(e.dataTransfer.files);
        }
    });

    async function handleMultipleFilesUpload(filesList) {
        const pdfFiles = Array.from(filesList).filter(file => {
            return file.type === "application/pdf" || (file.name && file.name.toLowerCase().endsWith(".pdf"));
        });

        if (pdfFiles.length === 0) {
            alert("Please drop or select valid PDF files.");
            return;
        }

        progressContainer.classList.remove("hidden");
        
        let successCount = 0;
        let lastUploadedPaperId = null;
        const errors = [];

        for (let i = 0; i < pdfFiles.length; i++) {
            const file = pdfFiles[i];
            const fileNum = i + 1;
            const totalFiles = pdfFiles.length;
            
            progressBar.style.width = "0%";
            progressStatus.textContent = `[${fileNum}/${totalFiles}] Uploading ${file.name}...`;
            
            try {
                const uploadedPaper = await uploadSingleFile(file, (percent) => {
                    progressBar.style.width = `${percent}%`;
                    if (percent === 100) {
                        progressStatus.textContent = `[${fileNum}/${totalFiles}] Analysing ${file.name}...`;
                    } else {
                        progressStatus.textContent = `[${fileNum}/${totalFiles}] Uploading ${file.name} (${percent}%)...`;
                    }
                });
                
                successCount++;
                lastUploadedPaperId = uploadedPaper.id;
            } catch (err) {
                console.error(`Failed to upload ${file.name}:`, err);
                errors.push(`${file.name}: ${err.message || err}`);
            }
        }

        if (errors.length > 0) {
            progressStatus.textContent = "Completed with errors";
            progressBar.style.width = "100%";
            setTimeout(() => {
                progressContainer.classList.add("hidden");
            }, 2000);
            
            let extraGuidance = "";
            if (errors.some(errStr => {
                const lower = errStr.toLowerCase();
                return lower.includes("project not found") || lower.includes("unauthorized");
            })) {
                extraGuidance = "\n\nTroubleshooting Tip: It looks like you do not have an active project selected or authorization expired. Please ensure a project is selected in the 'Active Project' dropdown in the left sidebar.";
            }
            alert(`Upload completed with some errors:\n\n${errors.join("\n")}${extraGuidance}`);
        } else {
            progressStatus.textContent = "All papers parsed successfully!";
            progressBar.style.width = "100%";
            setTimeout(() => {
                progressContainer.classList.add("hidden");
            }, 1500);
        }

        if (successCount > 0) {
            await fetchPapersList();
            if (lastUploadedPaperId) {
                selectPaper(lastUploadedPaperId);
            }
        }
    }

    function uploadSingleFile(file, onProgress) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append("file", file);

            const focus = localStorage.getItem("extractionFocus") || "standard";
            const temp = localStorage.getItem("modelTemperature") || "0.2";
            const xhr = new XMLHttpRequest();
            xhr.open("POST", `/api/project/${state.selectedProjectId}/upload?model=${state.selectedModelId}&focus=${focus}&temperature=${temp}`, true);

            const token = localStorage.getItem("access_token");
            if (token) {
                xhr.setRequestHeader("Authorization", `Bearer ${token}`);
            }

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    onProgress(percent);
                }
            });

            xhr.onload = function() {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error("Invalid response format."));
                    }
                } else {
                    let errorMsg = "Upload failed.";
                    try {
                        const err = JSON.parse(xhr.responseText);
                        errorMsg = err.detail || errorMsg;
                    } catch(e) {}
                    reject(new Error(errorMsg));
                }
            };

            xhr.onerror = function() {
                reject(new Error("Network error."));
            };

            xhr.send(formData);
        });
    }

    // 2. Fetch Ingested Papers List
    async function fetchPapersList() {
        if (!state.selectedProjectId) return;
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
                
                // Fetch dynamic chat history from database
                try {
                    const chatRes = await fetch(`/api/project/${state.selectedProjectId}/paper/${id}/chat`);
                    if (chatRes.ok) {
                        state.chatHistories[id] = await chatRes.json();
                    } else {
                        state.chatHistories[id] = [];
                    }
                } catch (chatErr) {
                    console.error("Error loading chat history:", chatErr);
                    state.chatHistories[id] = [];
                }

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
        
        exportBtn.onclick = async () => {
            try {
                const res = await fetch(`/api/project/${state.selectedProjectId}/paper/${state.selectedPaper.id}/export`);
                if (res.ok) {
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    
                    const contentDisposition = res.headers.get("content-disposition");
                    let filename = `Summary_${state.selectedPaper.metadata.title.replace(/\s+/g, "_")}.md`;
                    if (contentDisposition) {
                        const match = contentDisposition.match(/filename=(.+)/);
                        if (match && match[1]) filename = match[1];
                    }
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } else {
                    alert("Failed to export summary.");
                }
            } catch (err) {
                console.error("Export error:", err);
                alert("Connection error during export.");
            }
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

    // 9. Comparison Matrix & Cross-Doc Synthesis Logic
    async function loadComparisonMatrix() {
        if (!state.selectedProjectId) {
            if (matrixTableBody) matrixTableBody.innerHTML = "";
            if (emptyMatrixState) emptyMatrixState.classList.remove("hidden");
            if (latexCodePreview) latexCodePreview.textContent = "% Select a project first";
            return;
        }

        try {
            if (matrixTableBody) {
                matrixTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-4"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Compiling literature matrix...</td></tr>';
            }
            if (emptyMatrixState) emptyMatrixState.classList.add("hidden");

            const style = localStorage.getItem("citationFormat") || "apa";
            const res = await fetch(`/api/project/${state.selectedProjectId}/matrix?style=${style}`);

            if (!res.ok) {
                throw new Error("Failed to load comparison matrix.");
            }

            const data = await res.json();
            const items = data.items || [];
            
            if (matrixTableBody) {
                matrixTableBody.innerHTML = "";
                if (items.length === 0) {
                    if (emptyMatrixState) emptyMatrixState.classList.remove("hidden");
                    if (latexCodePreview) latexCodePreview.textContent = "% Upload papers to generate LaTeX table code";
                    return;
                }
                
                items.forEach(item => {
                    const tr = document.createElement("tr");
                    tr.style.borderBottom = "1px solid var(--border-color)";
                    
                    // Format contributions list
                    const contribs = Array.isArray(item.contributions) 
                        ? item.contributions.map(c => `<li>${escapeHtml(c)}</li>`).join("") 
                        : escapeHtml(item.contributions);
                    const contribsHtml = Array.isArray(item.contributions) 
                        ? `<ul style="padding-left: 16px; margin: 0;">${contribs}</ul>` 
                        : contribs;

                    // Format limitations list
                    const limitations = Array.isArray(item.limitations) 
                        ? item.limitations.map(l => `<li>${escapeHtml(l)}</li>`).join("") 
                        : escapeHtml(item.limitations);
                    const limitationsHtml = Array.isArray(item.limitations) 
                        ? `<ul style="padding-left: 16px; margin: 0;">${limitations}</ul>` 
                        : limitations;

                    tr.innerHTML = `
                        <td class="fw-bold" style="color: var(--text-primary); vertical-align: top;">${escapeHtml(item.citation_key)}<br><span class="text-secondary fw-normal" style="font-size: 0.8rem;">${escapeHtml(item.title)}</span></td>
                        <td style="vertical-align: top;">${escapeHtml(item.synopsis) || '<span class="text-secondary small">N/A</span>'}</td>
                        <td style="vertical-align: top;">${escapeHtml(item.methodology) || '<span class="text-secondary small">N/A</span>'}</td>
                        <td style="vertical-align: top;">${contribsHtml || '<span class="text-secondary small">N/A</span>'}</td>
                        <td style="vertical-align: top;">${limitationsHtml || '<span class="text-secondary small">N/A</span>'}</td>
                    `;
                    matrixTableBody.appendChild(tr);
                });
            }

            if (latexCodePreview) {
                latexCodePreview.textContent = data.latex || "% No papers available";
            }
        } catch (err) {
            console.error("Error loading matrix:", err);
            if (matrixTableBody) {
                matrixTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Error loading comparison matrix: ${escapeHtml(err.message)}</td></tr>`;
            }
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    if (exportLatexBtn) {
        exportLatexBtn.addEventListener("click", () => {
            if (!latexCodePreview || !latexCodePreview.textContent) return;
            const code = latexCodePreview.textContent;
            navigator.clipboard.writeText(code).then(() => {
                const originalText = exportLatexBtn.innerHTML;
                exportLatexBtn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-1">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    Copied!
                `;
                setTimeout(() => {
                    exportLatexBtn.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                console.error("Failed to copy LaTeX code: ", err);
                alert("Failed to copy code to clipboard.");
            });
        });
    }

    if (synthesisForm) {
        synthesisForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const query = synthesisInput.value.trim();
            if (!query) return;
            
            if (!state.selectedProjectId) {
                alert("Please select a project first.");
                return;
            }
            
            // Append User Message to history
            appendSynthesisMessage("user", query);
            synthesisInput.value = "";
            synthesisInput.disabled = true;
            
            // Show Loading message
            const loadingMsgId = appendSynthesisMessage("assistant", "Synthesizing literature analysis across papers...", true);
            
            try {
                if (synthesisErrorAlert) synthesisErrorAlert.classList.add("hidden");
                
                const modelSelect = document.getElementById("model-select");
                const selectedModel = modelSelect ? modelSelect.value : "gemini";
                
                const res = await fetch(`/api/project/${state.selectedProjectId}/synthesize`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        query: query,
                        model: selectedModel
                    })
                });
                
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Synthesis query failed.");
                }
                
                const data = await res.json();
                
                // Replace loading message with actual response
                removeSynthesisMessage(loadingMsgId);
                appendSynthesisMessage("assistant", data.reply);
            } catch (err) {
                console.error("Synthesis error:", err);
                removeSynthesisMessage(loadingMsgId);
                if (synthesisErrorAlert) {
                    synthesisErrorAlert.textContent = `Error: ${err.message}`;
                    synthesisErrorAlert.classList.remove("hidden");
                }
            } finally {
                synthesisInput.disabled = false;
                synthesisInput.focus();
            }
        });
    }

    function appendSynthesisMessage(role, content, isLoading = false) {
        if (!synthesisHistory) return null;
        
        const msgId = "synthesis-msg-" + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.id = msgId;
        
        if (role === "user") {
            msgDiv.className = "user-message p-3 rounded mb-3 ms-auto text-end";
            msgDiv.style.background = "rgba(168, 85, 247, 0.15)";
            msgDiv.style.border = "1px solid rgba(168, 85, 247, 0.25)";
            msgDiv.style.color = "var(--text-primary)";
            msgDiv.style.maxWidth = "80%";
            msgDiv.style.width = "fit-content";
            msgDiv.textContent = content;
        } else {
            msgDiv.className = "assistant-message p-3 rounded mb-3";
            msgDiv.style.background = "rgba(255, 255, 255, 0.02)";
            msgDiv.style.border = "1px solid var(--border-color)";
            msgDiv.style.color = "var(--text-primary)";
            msgDiv.style.maxWidth = "90%";
            
            if (isLoading) {
                msgDiv.innerHTML = `<div class="d-flex align-items-center"><div class="spinner-border spinner-border-sm me-2" role="status"></div><span>${escapeHtml(content)}</span></div>`;
            } else {
                msgDiv.innerHTML = formatSynthesisMarkdown(content);
            }
        }
        
        synthesisHistory.appendChild(msgDiv);
        synthesisHistory.scrollTop = synthesisHistory.scrollHeight;
        return msgId;
    }

    function removeSynthesisMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function formatSynthesisMarkdown(text) {
        if (!text) return "";
        let formatted = escapeHtml(text);
        
        // Bold
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        
        // Lists
        formatted = formatted.replace(/^\s*-\s+(.*?)$/gm, "<li>$1</li>");
        formatted = formatted.replace(/(<li>.*?<\/li>)/gs, "<ul>$1</ul>");
        formatted = formatted.replace(/<\/ul>\s*<ul>/g, "");
        
        // Line breaks
        formatted = formatted.replace(/\n/g, "<br>");
        
        // Citation highlighting
        formatted = formatted.replace(/([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?\s*\(\d{4}\))/g, '<span class="badge bg-primary-glow" style="font-weight: 500; font-size: 0.85rem; padding: 2px 6px; border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 4px; background: rgba(168, 85, 247, 0.1); color: var(--accent-color);">$1</span>');

        return formatted;
    }

    // Initialise loading sequence based on authentication status
    const token = localStorage.getItem("access_token");
    if (token) {
        hideAuthOverlay();
        fetchUserProfile();
        fetchProjectsList().then(() => {
            fetchPapersList();
        });
    } else {
        showAuthOverlay();
    }
});
