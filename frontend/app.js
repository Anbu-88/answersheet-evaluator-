/**
 * ExamAI - Frontend Application
 * Handles PDF upload, API integration, results display, and PDF download.
 */

const API_BASE = "http://localhost:8000";

// ── State ──
let answerKeyFile = null;
let examSheetFile = null;
let reportBlob = null;

// ── DOM References ──
const answerKeyZone = document.getElementById("answerKeyZone");
const examSheetZone = document.getElementById("examSheetZone");
const answerKeyInput = document.getElementById("answerKeyInput");
const examSheetInput = document.getElementById("examSheetInput");
const answerKeyInfo = document.getElementById("answerKeyInfo");
const examSheetInfo = document.getElementById("examSheetInfo");
const answerKeyName = document.getElementById("answerKeyName");
const examSheetName = document.getElementById("examSheetName");
const gradeBtn = document.getElementById("gradeBtn");
const uploadSection = document.getElementById("uploadSection");
const progressSection = document.getElementById("progressSection");
const resultsSection = document.getElementById("resultsSection");
const errorSection = document.getElementById("errorSection");

// ── Background Animation ──
function initBackground() {
    const canvas = document.getElementById("bgCanvas");
    const ctx = canvas.getContext("2d");

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    const particles = [];
    const count = 50;

    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * 2 + 0.5,
            dx: (Math.random() - 0.5) * 0.4,
            dy: (Math.random() - 0.5) * 0.4,
            alpha: Math.random() * 0.3 + 0.05,
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach((p) => {
            p.x += p.dx;
            p.y += p.dy;

            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(108, 99, 255, ${p.alpha})`;
            ctx.fill();
        });

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(108, 99, 255, ${0.06 * (1 - dist / 150)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }

    animate();
}

// ── Drag & Drop + File Selection ──
function setupUploadZone(zone, input, target) {
    // Click to browse
    zone.addEventListener("click", (e) => {
        if (e.target.classList.contains("remove-btn")) return;
        input.click();
    });

    // File selected
    input.addEventListener("change", () => {
        if (input.files.length > 0) {
            handleFile(input.files[0], target);
        }
    });

    // Drag events
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
                handleFile(file, target);
            } else {
                alert("Please upload a PDF file.");
            }
        }
    });
}

function handleFile(file, target) {
    if (target === "answerKey") {
        answerKeyFile = file;
        answerKeyName.textContent = file.name;
        answerKeyInfo.style.display = "flex";
    } else {
        examSheetFile = file;
        examSheetName.textContent = file.name;
        examSheetInfo.style.display = "flex";
    }
    updateGradeButton();
}

function removeFile(target) {
    if (target === "answerKey") {
        answerKeyFile = null;
        answerKeyInput.value = "";
        answerKeyInfo.style.display = "none";
    } else {
        examSheetFile = null;
        examSheetInput.value = "";
        examSheetInfo.style.display = "none";
    }
    updateGradeButton();
}

function updateGradeButton() {
    gradeBtn.disabled = !(answerKeyFile && examSheetFile);
}

// ── Remove Buttons ──
document.querySelectorAll(".remove-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        removeFile(btn.dataset.target);
    });
});

// ── Section Visibility ──
function showSection(section) {
    uploadSection.style.display = "none";
    progressSection.style.display = "none";
    resultsSection.style.display = "none";
    errorSection.style.display = "none";
    section.style.display = "block";
}

// ── Progress Animation ──
function animateProgress() {
    const steps = ["step1", "step2", "step3", "step4"];
    const bar = document.getElementById("progressBar");
    let currentStep = 0;

    function activateStep() {
        if (currentStep >= steps.length) return;

        // Mark previous steps as done
        for (let i = 0; i < currentStep; i++) {
            document.getElementById(steps[i]).classList.remove("active");
            document.getElementById(steps[i]).classList.add("done");
        }

        // Activate current step
        document.getElementById(steps[currentStep]).classList.add("active");
        bar.style.width = `${((currentStep + 1) / steps.length) * 100}%`;

        currentStep++;
        if (currentStep < steps.length) {
            setTimeout(activateStep, 8000); // ~8 seconds per step
        }
    }

    // Reset
    steps.forEach((s) => {
        const el = document.getElementById(s);
        el.classList.remove("active", "done");
    });
    bar.style.width = "0%";

    activateStep();
}

// ── Grade Exam ──
async function gradeExam() {
    showSection(progressSection);
    animateProgress();

    const formData = new FormData();
    formData.append("answer_key", answerKeyFile);
    formData.append("exam_sheet", examSheetFile);

    try {
        const response = await fetch(`${API_BASE}/api/grade`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${response.status}`);
        }

        // Check content type — if PDF, handle as blob download
        const contentType = response.headers.get("content-type");
        
        if (contentType && contentType.includes("application/pdf")) {
            reportBlob = await response.blob();
            
            // We still need to show some results. Let's parse what we can 
            // from the grading. Make a secondary request for display data.
            try {
                const analyzeForm = new FormData();
                analyzeForm.append("answer_key", answerKeyFile);
                const analyzeResp = await fetch(`${API_BASE}/api/analyze-answer-key`, {
                    method: "POST",
                    body: analyzeForm,
                });
                if (analyzeResp.ok) {
                    const answerData = await analyzeResp.json();
                    showResultsFromBlob(answerData);
                } else {
                    showResultsMinimal();
                }
            } catch {
                showResultsMinimal();
            }
        } else {
            // If JSON returned (shouldn't happen in normal flow)
            const data = await response.json();
            showResults(data);
        }
    } catch (err) {
        showError(err.message);
    }
}

// ── Show Results (Minimal — when we only have the PDF blob) ──
function showResultsMinimal() {
    showSection(resultsSection);

    const scoreValue = document.getElementById("scoreValue");
    const scoreCircle = document.getElementById("scoreCircle");
    const summary = document.getElementById("resultsSummary");
    const table = document.getElementById("resultsTable");

    scoreValue.textContent = "✅";
    scoreCircle.style.background = `conic-gradient(var(--success) 360deg, transparent 0deg)`;

    summary.innerHTML = `
        <div class="summary-item">
            <span class="value">✅</span>
            <span class="label">Grading Complete</span>
        </div>
    `;

    table.innerHTML = `
        <p style="color: var(--text-secondary); text-align: center; padding: 20px;">
            Your graded report PDF has been generated. Click the download button below to view the detailed results.
        </p>
    `;
}

// ── Show Results with answer data ──
function showResultsFromBlob(answerData) {
    showSection(resultsSection);

    const scoreValue = document.getElementById("scoreValue");
    const scoreCircle = document.getElementById("scoreCircle");
    const summary = document.getElementById("resultsSummary");
    const table = document.getElementById("resultsTable");

    const totalQ = answerData.total_questions || "?";
    const totalM = answerData.total_marks || "?";

    scoreValue.textContent = "✅";
    scoreCircle.style.background = `conic-gradient(var(--success) 360deg, transparent 0deg)`;

    summary.innerHTML = `
        <div class="summary-item">
            <span class="value">${totalQ}</span>
            <span class="label">Questions Found</span>
        </div>
        <div class="summary-item">
            <span class="value">${totalM}</span>
            <span class="label">Total Marks</span>
        </div>
        <div class="summary-item">
            <span class="value">✅</span>
            <span class="label">Graded</span>
        </div>
    `;

    table.innerHTML = `
        <p style="color: var(--text-secondary); text-align: center; padding: 20px;">
            Your detailed grading report has been generated as a PDF.<br>
            Click <strong>Download Report PDF</strong> below to view per-question marks and reasoning.
        </p>
    `;
}

// ── Show Full JSON Results (if available) ──
function showResults(data) {
    showSection(resultsSection);

    const scoreValue = document.getElementById("scoreValue");
    const scoreCircle = document.getElementById("scoreCircle");
    const summary = document.getElementById("resultsSummary");
    const table = document.getElementById("resultsTable");

    const pct = data.percentage || 0;
    const obtained = data.total_marks_obtained || 0;
    const possible = data.total_marks_possible || 0;

    // Score circle
    scoreValue.textContent = `${Math.round(pct)}%`;
    scoreCircle.style.background = `conic-gradient(var(--accent) ${pct * 3.6}deg, rgba(255,255,255,0.06) 0deg)`;

    // Summary cards
    summary.innerHTML = `
        <div class="summary-item">
            <span class="value">${obtained}/${possible}</span>
            <span class="label">Marks</span>
        </div>
        <div class="summary-item">
            <span class="value">${pct.toFixed(1)}%</span>
            <span class="label">Percentage</span>
        </div>
        <div class="summary-item">
            <span class="value">${data.results ? data.results.length : 0}</span>
            <span class="label">Questions</span>
        </div>
    `;

    // Results table
    if (data.results && data.results.length > 0) {
        let tableHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Q.No</th>
                        <th>Marks</th>
                        <th>Status</th>
                        <th>Reasoning</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.results.forEach((r) => {
            const marks = r.marks_obtained || 0;
            const max = r.max_marks || 0;
            let badgeClass = "zero";
            let statusIcon = "❌";
            if (marks >= max) {
                badgeClass = "full";
                statusIcon = "✅";
            } else if (marks > 0) {
                badgeClass = "partial";
                statusIcon = "⚠️";
            }

            tableHTML += `
                <tr>
                    <td>Q${r.question_number}</td>
                    <td><span class="marks-badge ${badgeClass}">${statusIcon} ${marks}/${max}</span></td>
                    <td>${badgeClass === "full" ? "Correct" : badgeClass === "partial" ? "Partial" : "Incorrect"}</td>
                    <td><span class="reasoning-text">${r.reasoning || ""}</span></td>
                </tr>
            `;
        });

        tableHTML += "</tbody></table>";
        table.innerHTML = tableHTML;
    }
}

// ── Show Error ──
function showError(message) {
    showSection(errorSection);
    document.getElementById("errorMessage").textContent = message;
}

// ── Download Report ──
function downloadReport() {
    if (!reportBlob) {
        alert("No report available for download.");
        return;
    }
    const url = URL.createObjectURL(reportBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "examai_grading_report.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ── Reset ──
function resetApp() {
    answerKeyFile = null;
    examSheetFile = null;
    reportBlob = null;
    answerKeyInput.value = "";
    examSheetInput.value = "";
    answerKeyInfo.style.display = "none";
    examSheetInfo.style.display = "none";
    updateGradeButton();
    showSection(uploadSection);
    uploadSection.style.display = "block";
}

// ── Event Listeners ──
setupUploadZone(answerKeyZone, answerKeyInput, "answerKey");
setupUploadZone(examSheetZone, examSheetInput, "examSheet");

gradeBtn.addEventListener("click", gradeExam);
document.getElementById("downloadBtn").addEventListener("click", downloadReport);
document.getElementById("newGradeBtn").addEventListener("click", resetApp);
document.getElementById("retryBtn").addEventListener("click", resetApp);

// ── Init ──
initBackground();
