let currentStage = 1;
let appState = {
    resumeId: null,
    parsedData: null,
    predictedJobs: [],
    currentSelectedJob: null,
    currentJD: null,
    atsResults: null,
    jobSearchUnlocked: false,
    cachedAdvisorData: null,
    advisorPromise: null
};

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) { window.location.href = '/login/'; return; }
    
    // Check if Job Search should be unlocked globally
    try {
        const resResponse = await fetch('/api/resume/completed/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resResponse.ok) {
            const resData = await resResponse.json();
            appState.jobSearchUnlocked = resData.resumes && resData.resumes.length > 0;
        }
    } catch (e) { console.error("Initial unlock check failed", e); }

    updateWorkflowStage(1);
});

function updateWorkflowStage(stage) {
    const progressBar = document.getElementById('workflow-progress-line');
    for(let i = 1; i <= 8; i++) {
        const circle = document.getElementById(`step-${i}-circle`);
        const text = document.getElementById(`step-${i}-text`);
        if(circle && text) {
            circle.className = 'rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-secondary bg-body-tertiary shadow-sm';
            circle.style.border = '2px solid white';
            circle.style.background = '';
            circle.style.boxShadow = '';
            text.className = 'small fw-bold mb-0 text-secondary';
        }
    }

    for(let i = 1; i <= Math.min(stage, 8); i++) {
        const circle = document.getElementById(`step-${i}-circle`);
        const text = document.getElementById(`step-${i}-text`);
        if(circle && text) {
            circle.className = 'rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-white shadow-sm';
            circle.style.border = '2px solid white';
            circle.style.background = 'linear-gradient(to top right, #3b82f6, #8b5cf6)';
            if (i === stage) {
                circle.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.2)';
            } else {
                circle.style.boxShadow = '';
            }
            text.className = 'small fw-bold mb-0 text-primary';
        }
    }

    const percentage = ((stage - 1) / 7) * 100;
    if(progressBar) progressBar.style.width = `${percentage}%`;
}

function goToStage(stageNumber) {
    const sections = [
        'upload-container', 'parsed-results', 'field-results', 
        'predicting-loading', 'jobs-results', 'jd-loading', 'jd-results',
        'ats-loading', 'ats-results', 'skill-gap-results', 'optimizer-loading', 'optimizer-results'
    ];
    sections.forEach(id => {
        let el = document.getElementById(id);
        if(el) el.style.display = 'none';
    });

    if (stageNumber === 1) document.getElementById('upload-container').style.display = 'block';
    else if (stageNumber === 2) document.getElementById('parsed-results').style.display = 'block';
    else if (stageNumber === 3) document.getElementById('field-results').style.display = 'block';
    else if (stageNumber === 4) document.getElementById('jobs-results').style.display = 'block';
    else if (stageNumber === 5) document.getElementById('jd-results').style.display = 'block';
    else if (stageNumber === 6) document.getElementById('ats-results').style.display = 'block';
    else if (stageNumber === 7) document.getElementById('skill-gap-results').style.display = 'block';
    else if (stageNumber === 8) document.getElementById('optimizer-results').style.display = 'block';

    currentStage = stageNumber;
    updateWorkflowStage(stageNumber);
}

function goBackToStage(stageNumber) {
    if(stageNumber === 3) {
        document.getElementById('field-content').style.display = 'block';
        document.getElementById('field-loading').style.display = 'none';
    }
    goToStage(stageNumber);
}

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const btn = document.getElementById('upload-btn');
    const statusDiv = document.getElementById('upload-status');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Analyzing...';
    
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `
        <div class="p-4 rounded glass-panel text-center">
            <div class="ai-scanner-loader text-primary">
                <div class="scanner-bar"></div>
                <div class="outer-ring"></div>
                <div class="inner-dot"></div>
            </div>
            <h6 class="fw-bold mb-3">Initializing Document Intelligence</h6>
            <div id="upload-pipeline" class="pipeline-status-container"></div>
        </div>
    `;
    
    showPipelineSteps('upload-pipeline', [
        'Connecting to NLP Layer...',
        'Tokenizing Text Vectors...',
        'Applying Semantic Mapping...',
        'Validating Structural Integrity...'
    ]);

    updateWorkflowStage(2);

    const formData = new FormData();
    formData.append('resume', file);

    try {
        const response = await fetch('/api/resume/parse/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            window.currentResumeId = data.resume_id;
            appState.resumeId = data.resume_id;
            const safeParsedData = data.parsed_state || data.parsed_data || {};
            appState.parsedData = safeParsedData;
            displayParsedData(safeParsedData);
            goToStage(2);
        } else {
            statusDiv.innerHTML = `<span class="text-danger">${data.error || 'Failed to parse resume.'}</span>`;
            goToStage(1);
        }
    } catch (error) {
        statusDiv.innerHTML = `<span class="text-danger">Network error. Please try again.</span>`;
        goToStage(1);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Upload Another Resume';
        event.target.value = '';
    }
}

function displayParsedData(data) {
    // 1. Basic Fields
    document.getElementById('parsed-name').value = data.name || 'Not Provided';
    document.getElementById('parsed-email').value = data.email || 'Not Provided';
    document.getElementById('parsed-phone').value = data.phone || 'Not Provided';
    document.getElementById('parsed-linkedin').value = data.linkedin || 'Not Provided';
    document.getElementById('parsed-portfolio').value = data.portfolio || 'Not Provided';
    
    // 2. Map Top 5 Skills to Badges
    const skillsContainer = document.getElementById('parsed-skills-container');
    skillsContainer.innerHTML = '';
    const skills = data.skills || [];
    if (skills.length === 0) {
        skillsContainer.innerHTML = '<span class="text-muted small">Not Provided</span>';
    } else {
        skills.forEach(s => {
            let sName = typeof s === 'string' ? s : (s.name || 'Unknown');
            let sLevel = typeof s === 'string' ? 'Intermediate' : (s.level || 'Intermediate');
            let sReason = typeof s === 'string' ? 'Extracted successfully' : (s.reason || '');
            
            let colorClass = 'bg-secondary';
            if(sLevel.toLowerCase().includes('advanced')) colorClass = 'bg-primary';
            else if(sLevel.toLowerCase().includes('intermediate')) colorClass = 'bg-info';
            
            skillsContainer.innerHTML += `
                <div class="border rounded px-3 py-2 bg-white shadow-sm" title="${sReason}">
                    <span class="fw-bold text-dark small">${sName}</span>
                    <span class="badge ${colorClass} ms-2" style="font-size: 0.65em;">${sLevel}</span>
                </div>
            `;
        });
    }

    // 3. Map Experience 
    const expContainer = document.getElementById('parsed-experience-container');
    expContainer.innerHTML = '';
    const exps = data.experience || [];
    if (exps.length === 0) expContainer.innerHTML = '<span class="text-muted small">Not Provided</span>';
    else {
        let ul = document.createElement('ul');
        ul.className = 'list-unstyled mb-0 small text-muted';
        exps.forEach(e => {
            ul.innerHTML += `<li class="mb-2"><strong class="text-dark">${e.title || 'Role'}</strong> at ${e.company || 'Company'} <span class="text-secondary">(${e.duration || 'N/A'})</span><br/><span style="font-size: 0.85em;">${e.description || ''}</span></li>`;
        });
        expContainer.appendChild(ul);
    }
    
    // 4. Map Education & Certifications
    const eduCertsContainer = document.getElementById('parsed-edu-certs-container');
    eduCertsContainer.innerHTML = '';
    const edus = data.education || [];
    const certs = [...(data.certifications || []), ...(data.tools || [])];
    
    let html = '';
    if (edus.length > 0) {
        html += '<strong class="d-block text-dark small mb-1">Education</strong><ul class="small text-muted ps-3 mb-2">';
        edus.forEach(e => html += `<li>${e.degree || 'Degree'} - ${e.institution || 'Inst'} (${e.year || ''})</li>`);
        html += '</ul>';
    }
    if (certs.length > 0) {
        html += '<strong class="d-block text-dark small mb-1 mt-2">Certifications & Tools</strong><div class="d-flex flex-wrap gap-1">';
        certs.forEach(c => html += `<span class="badge bg-secondary bg-opacity-10 text-secondary border">${c}</span>`);
        html += '</div>';
    }
    if (html === '') html = '<span class="text-muted small">Not Provided</span>';
    eduCertsContainer.innerHTML = html;

    // 5. Map Projects to Badges
    const projectsContainer = document.getElementById('parsed-projects-container');
    projectsContainer.innerHTML = '';
    const projects = data.projects || [];
    if (projects.length === 0) {
        projectsContainer.innerHTML = '<span class="text-muted small">Not Provided</span>';
    } else {
        projects.forEach(p => {
            projectsContainer.innerHTML += `
                <div class="border rounded px-3 py-2 bg-white shadow-sm">
                    <span class="fw-bold text-dark small">${p}</span>
                </div>
            `;
        });
    }
}

async function confirmParsedData() {
    const btn = document.getElementById('confirm-parsed-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';

    // Preserve underlying strict structure, only update shallow profile changes
    const updatedData = appState.parsedData || {};
    updatedData.name = document.getElementById('parsed-name').value;
    updatedData.email = document.getElementById('parsed-email').value;
    updatedData.phone = document.getElementById('parsed-phone').value;
    updatedData.linkedin = document.getElementById('parsed-linkedin').value;
    updatedData.portfolio = document.getElementById('parsed-portfolio').value;

    const token = localStorage.getItem('access');
    try {
        const response = await fetch(`/api/resume/update-parsed/${window.currentResumeId}/`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ parsed_data: updatedData })
        });

        if (response.ok) {
            goToStage(3);
            await fetchJobFamilies();
        } else {
            alert('Failed to save parsed data.');
        }
    } catch { alert('Network error.'); }
    finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Confirm Data';
    }
}

async function fetchJobFamilies() {
    const token = localStorage.getItem('access');
    document.getElementById('field-loading').style.display = 'block';
    document.getElementById('field-content').style.display = 'none';

    try {
        const response = await fetch('/api/fields/classify/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();
        if (response.ok) {
            document.getElementById('field-loading').style.display = 'none';
            document.getElementById('field-content').style.display = 'block';
            let dropdown = document.getElementById('ai-career-field-dropdown');
            dropdown.innerHTML = '<option value="" disabled selected>-- Select an AI suggestion --</option>';
            (data.job_families || []).forEach(f => {
                let fName = typeof f === 'string' ? f : (f.field_name || f.name);
                let fLabel = typeof f === 'string' ? '' : (f.label ? `${f.label}: ` : '');
                dropdown.innerHTML += `<option value="${fName}">${fLabel}${fName}</option>`;
            });
        } else {
            alert(data.error); goToStage(2);
        }
    } catch { alert('Network error.'); goToStage(2); }
}

async function lockFieldAndPredictRoles() {
    const targetField = document.getElementById('custom-career-field').value.trim();
    if (!targetField) { alert("Please type a field."); return; }

    goToStage(4);
    document.getElementById('jobs-results').style.display = 'none';
    document.getElementById('predicting-loading').style.display = 'block';

    const token = localStorage.getItem('access');
    try {
        const response = await fetch('/api/jobs/predict/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_id: window.currentResumeId, target_field: targetField })
        });

        const data = await response.json();
        document.getElementById('predicting-loading').style.display = 'none';
        
        if (response.ok) {
            document.getElementById('jobs-results').style.display = 'block';
            const listDiv = document.getElementById('jobs-list');
            listDiv.innerHTML = '';
            
            (data.jobs || []).forEach(job => {
                let jTitle = job.job_title || job.title;
                let jReason = job.reason || job.match_reason;
                let jLevel = job.level || 'Mid';
                let jConf = job.confidence || '';
                let jLabel = job.label || 'Prediction';
                
                listDiv.innerHTML += `
                    <div class="card border-0 shadow-sm mb-2">
                        <div class="card-body d-flex align-items-center">
                            <input class="form-check-input role-radio me-3" type="radio" name="targetRoleRadio" value="${jTitle}">
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between align-items-start">
                                    <h6 class="fw-bold mb-1">${jTitle} <span class="badge bg-secondary ms-1" style="font-size: 0.7em;">${jLevel}</span> <span class="badge bg-success ms-1" style="font-size: 0.7em;">${jConf}% Match</span></h6>
                                    <span class="badge bg-primary bg-opacity-10 text-primary border border-primary small" style="font-size: 0.7em;">${jLabel}</span>
                                </div>
                                <p class="text-muted small mb-0">${jReason}</p>
                            </div>
                        </div>
                    </div>
                `;
            });
        } else { alert(data.error); goToStage(3); }
    } catch { alert('Network error.'); goToStage(3); }
}

async function generateTargetJD() {
    const selected = document.querySelector('input[name="targetRoleRadio"]:checked');
    if (!selected) { alert("Please select exactly one role."); return; }
    
    window.currentSelectedJob = { title: selected.value };
    goToStage(5);
    document.getElementById('jd-results').style.display = 'none';
    document.getElementById('jd-loading').style.display = 'block';

    const token = localStorage.getItem('access');
    try {
        const response = await fetch("/api/jd/generate/", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ resume_id: window.currentResumeId, target_role: selected.value })
        });

        const data = await response.json();
        document.getElementById("jd-loading").style.display = "none";
        
        if (response.ok) {
            document.getElementById("jd-results").style.display = "block";
            const jd = data.generated_jd;
            appState.currentJD = jd;
            
            document.getElementById("jd-title-display").innerText = jd.job_title || 'Target Role';
            document.getElementById("jd-summary-display").innerText = jd.summary || 'Not Provided';
            
            const rUl = document.getElementById("jd-responsibilities-display");
            rUl.innerHTML = '';
            (jd.responsibilities || []).forEach(r => rUl.innerHTML += `<li class="list-group-item px-2 py-1 bg-transparent border-0"><i class="bi bi-dot"></i>${r}</li>`);
            
            const hDiv = document.getElementById("jd-hard-skills-display");
            hDiv.innerHTML = (jd.hard_skills || []).map(s => `<span class="badge bg-success bg-opacity-10 text-success border border-success">${s}</span>`).join('');
            
            const sDiv = document.getElementById("jd-soft-skills-display");
            const combined = [...(jd.soft_skills || []), ...(jd.qualifications || [])];
            sDiv.innerHTML = combined.map(s => `<span class="badge bg-info bg-opacity-10 text-info border border-info">${s}</span>`).join('');
            
        } else { alert(data.error); goToStage(4); }
    } catch { alert("Network error."); goToStage(4); }
}

async function lockJDAndRunATS() {
    const btn = document.getElementById("run-ats-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Locking & Analyzing...';

    // Stringify JSON exactly as required for backend API
    const text = JSON.stringify(appState.currentJD);

    const token = localStorage.getItem('access');
    try {
        const lockRes = await fetch(`/api/jd/lock/${window.currentResumeId}/`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ locked_jd: text, target_role: window.currentSelectedJob.title })
        });

        if (!lockRes.ok) { alert("Failed to lock JD."); btn.disabled = false; return; }

        goToStage(6);
        document.getElementById("ats-results").style.display = "none";
        document.getElementById("ats-loading").style.display = "block";

        const atsRes = await fetch("/api/ats/match/", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await atsRes.json();
        document.getElementById("ats-loading").style.display = "none";

        if (atsRes.ok && data.match_results) {
            appState.atsResults = data.match_results;
            appState.jobSearchUnlocked = true; // Unlock Job Search
            document.getElementById("ats-results").style.display = "block";
            
            // Pre-fetch Course Advisor in background while user reads ATS results
            startCourseAdvisorBackgroundSearch();
            
            const r = data.match_results;
            const issues = r.issue_summary || {};
            const search = r.searchability || {};
            const scoreBrk = r.score_breakdown || {};
            const quality = r.content_quality || {};
            
            // Build Hard Skills Table
            let hsRows = (r.hard_skills_comparison || []).map(row => {
                let badge = row.status === 'Match' ? '<span class="badge bg-success">Match</span>' : (row.status === 'Missing' ? '<span class="badge bg-danger">Missing</span>' : '<span class="badge bg-warning text-dark">Partial</span>');
                return `<tr><td>${row.skill_name}</td><td class="text-center">${row.resume_count}</td><td class="text-center">${row.jd_count}</td><td class="text-center">${badge}</td></tr>`;
            }).join('');
            
            // Build Soft Skills Table
            let ssRows = (r.soft_skills_comparison || []).map(row => {
                let badge = row.status === 'Match' ? '<span class="badge bg-success">Match</span>' : '<span class="badge bg-danger">Missing</span>';
                return `<tr><td>${row.skill_name}</td><td>${row.resume_status}</td><td>${row.jd_status}</td><td class="text-center">${badge}</td></tr>`;
            }).join('');
            
            document.getElementById("ats-results").innerHTML = `
                <div class="row g-4 mb-4">
                    <!-- Left: Score Dial -->
                    <div class="col-md-4 text-center d-flex flex-column justify-content-center align-items-center border-end">
                        <h4 class="text-secondary fw-bold mb-3">Overall Match</h4>
                        <div class="rounded-circle d-flex align-items-center justify-content-center shadow-sm" style="width: 150px; height: 150px; border: 8px solid ${r.overall_match_score >= 80 ? '#22c55e' : (r.overall_match_score >= 50 ? '#eab308' : '#ef4444')}; font-size: 3rem; font-weight: 900; color: #1e293b;">
                            ${r.overall_match_score}%
                        </div>
                    </div>
                    
                    <!-- Right: Score Breakdown & Issue Summary -->
                    <div class="col-md-8">
                        <h5 class="fw-bold text-dark border-bottom pb-2 mb-3">Issue Summary</h5>
                        <div class="row g-2 mb-3">
                            <div class="col-6 col-md-3"><div class="p-3 bg-danger bg-opacity-10 rounded text-center border"><h3 class="text-danger mb-0">${issues.hard_skills_issues || 0}</h3><small class="text-muted fw-bold">Hard Skill Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-3 bg-warning bg-opacity-10 rounded text-center border"><h3 class="text-warning mb-0">${issues.soft_skills_issues || 0}</h3><small class="text-muted fw-bold">Soft Skill Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-3 bg-info bg-opacity-10 rounded text-center border"><h3 class="text-info mb-0">${issues.searchability_issues || 0}</h3><small class="text-muted fw-bold">Searchability Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-3 bg-success bg-opacity-10 rounded text-center border"><h3 class="text-success mb-0">${issues.recruiter_tips_count || 0}</h3><small class="text-muted fw-bold">Recruiter Tips</small></div></div>
                        </div>
                        <div class="d-flex flex-wrap gap-2 small">
                            <span class="badge bg-secondary">Extracted Base: ${scoreBrk.experience_score}/20</span>
                            <span class="badge bg-secondary">Education: ${scoreBrk.education_score}/10</span>
                            <span class="badge bg-secondary">Format & Keywords: ${scoreBrk.keyword_format_score}/20</span>
                            <span class="badge bg-secondary">Core Target: ${scoreBrk.hard_skills_score}/40</span>
                        </div>
                    </div>
                </div>
                
                <!-- Deep Jobscan-like Analysis -->
                <div class="row g-4 mb-4">
                    <div class="col-md-6">
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-4 h-100 shadow-sm">
                             <h6 class="fw-bold text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-briefcase-fill text-primary me-2"></i>Deep Experience Analysis</h6>
                             <div class="mb-3">
                                <span class="badge ${r.deep_experience?.status?.includes('Match') ? 'bg-success' : 'bg-warning text-dark'} mb-2 fs-6 px-3 py-2">${r.deep_experience?.status || 'Unknown'}</span>
                                <div class="fw-bold text-dark mb-2">Extracted Years: <span class="text-primary">${r.deep_experience?.years_extracted || 'N/A'}</span></div>
                                <div class="small text-muted mb-3" style="line-height: 1.6;">${r.deep_experience?.relevance_explanation || ''}</div>
                             </div>
                             <div class="small text-dark border-top pt-3 mt-auto">
                                <span class="fw-bold"><i class="bi bi-magic text-warning me-2"></i>Improvement Plan:</span> ${(r.deep_experience?.suggestions || []).join('<br> • ')}
                             </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-4 h-100 shadow-sm">
                             <h6 class="fw-bold text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-mortarboard-fill text-info me-2"></i>Deep Education Analysis</h6>
                             <div class="mb-3">
                                <span class="badge ${r.deep_education?.status?.includes('Match') ? 'bg-info' : 'bg-danger'} mb-2 fs-6 px-3 py-2">${r.deep_education?.status || 'Unknown'}</span>
                                <div class="small text-muted mb-3" style="line-height: 1.6;">${r.deep_education?.explanation || ''}</div>
                             </div>
                             <div class="small text-dark border-top pt-3 mt-auto">
                                <span class="fw-bold"><i class="bi bi-magic text-warning me-2"></i>Improvement Plan:</span> ${(r.deep_education?.suggestions || []).join('<br> • ')}
                             </div>
                        </div>
                    </div>
                </div>
                
                <div class="row g-4 mb-4">
                    <div class="col-md-6">
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-4 h-100 shadow-sm">
                             <h6 class="fw-bold text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-file-earmark-text text-success me-2"></i>Content Quality Check</h6>
                             <ul class="list-group list-group-flush small mb-3 bg-transparent">
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-2">Measurable Results <span class="badge ${r.deep_quality?.measurable_results_found ? 'bg-success' : 'bg-danger'} p-2">${r.deep_quality?.measurable_results_found ? 'Found' : 'Missing'}</span></li>
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-2">Strong Action Verbs <span class="badge ${r.deep_quality?.action_verbs_strong ? 'bg-success' : 'bg-warning text-dark'} p-2">${r.deep_quality?.action_verbs_strong ? 'Strong' : 'Weak'}</span></li>
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-2">Job Title Match <span class="badge ${r.deep_job_title?.status?.includes('Found') ? 'bg-success' : 'bg-danger'} p-2">${r.deep_job_title?.status || 'Not Found'}</span></li>
                             </ul>
                             <div class="small text-dark border-top pt-3 mt-auto" style="line-height: 1.6;">
                                <div class="mb-2"><span class="fw-bold"><i class="bi bi-chat-right-quote text-secondary me-2"></i>Feedback:</span> ${r.deep_quality?.feedback || ''}</div>
                                <div><span class="fw-bold"><i class="bi bi-magic text-warning me-2"></i>Suggestion:</span> ${r.deep_job_title?.suggestion || ''}</div>
                             </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card shadow-sm border-0 h-100">
                            <div class="card-header bg-light fw-bold p-3"><i class="bi bi-search me-2"></i>Searchability Matrix</div>
                            <ul class="list-group list-group-flush small p-2">
                                <li class="list-group-item d-flex justify-content-between align-items-center border-0">Contact Info <span class="badge ${search.contact_info?.email === 'Present' && search.contact_info?.phone === 'Present' ? 'bg-success' : 'bg-danger'}">${search.contact_info?.email}/${search.contact_info?.phone}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center border-0">Summary Section <span class="badge ${search.summary_section === 'Present' ? 'bg-success' : 'bg-danger'}">${search.summary_section || 'N/A'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center border-0">Education Heading <span class="badge ${search.education_heading === 'Present' ? 'bg-success' : 'bg-danger'}">${search.education_heading || 'N/A'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center border-0">Experience Heading <span class="badge ${search.experience_heading === 'Present' ? 'bg-success' : 'bg-danger'}">${search.experience_heading || 'N/A'}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Tables -->
                <div class="row g-4 mb-4">
                    <div class="col-md-6">
                        <h6 class="fw-bold text-dark"><i class="bi bi-cpu text-primary me-2"></i>Hard Skills Comparison</h6>
                        <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                            <table class="table table-bordered table-sm small table-hover">
                                <thead class="table-light sticky-top"><tr><th>Skill</th><th class="text-center">Res</th><th class="text-center">JD</th><th class="text-center">Status</th></tr></thead>
                                <tbody>${hsRows}</tbody>
                            </table>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="fw-bold text-dark"><i class="bi bi-people text-info me-2"></i>Soft Skills Comparison</h6>
                        <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                            <table class="table table-bordered table-sm small table-hover">
                                <thead class="table-light sticky-top"><tr><th>Skill</th><th>Res</th><th>JD Req</th><th class="text-center">Status</th></tr></thead>
                                <tbody>${ssRows}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <!-- Recruiter Tips -->
                <div class="alert alert-secondary border-0 shadow-sm mb-4">
                    <h6 class="fw-bold text-dark mb-2"><i class="bi bi-lightbulb-fill text-warning me-2"></i>Recruiter Tips</h6>
                    <ul class="mb-0 small text-muted ps-3">
                        ${(r.recruiter_tips || []).map(tip => `<li>${tip}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="text-end border-top pt-3">
                    <button class="btn btn-primary fw-bold shadow-sm px-4" onclick="showSkillGap()">Next: Final Skill Gap Summary <i class="bi bi-arrow-right"></i></button>
                </div>
            `;
        } else { alert("ATS Match Failed"); goToStage(5); }
    } catch { alert("Network error."); goToStage(5); }
    finally { btn.disabled = false; btn.innerHTML = '<i class="bi bi-cpu-fill me-2"></i>Lock JD & Run ATS Match'; }
}

async function startCourseAdvisorBackgroundSearch() {
    const token = localStorage.getItem('access');
    appState.advisorPromise = fetch("/api/ats/advise-courses/", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: window.currentResumeId })
    }).then(res => res.json()).then(data => {
        appState.cachedAdvisorData = data;
        return data;
    }).catch(err => {
        console.error("Background course fetch failed", err);
        return null;
    });
}

async function showSkillGap() {
    goToStage(7);
    const results = appState.atsResults;
    if(!results) return;

    const gap = results.skill_gap_summary || { skills_you_have: [], missing_critical_skills: [], skills_to_improve: [] };
    
    // 1. Initial UI mapping for gap
    document.getElementById('gap-have-skills').innerHTML = gap.skills_you_have.length > 0 
        ? gap.skills_you_have.map(s => `<span class="badge bg-success bg-opacity-10 text-success border border-success p-2">${s}</span>`).join('')
        : '<span class="text-muted small">None detected</span>';
        
    document.getElementById('gap-missing-skills').innerHTML = gap.missing_critical_skills.length > 0
        ? gap.missing_critical_skills.map(s => `<span class="badge bg-danger bg-opacity-10 text-danger border border-danger p-2">${s}</span>`).join('')
        : '<span class="text-muted small">None missing</span>';
        
    if(gap.skills_to_improve.length > 0) {
        document.getElementById('gap-missing-skills').innerHTML += gap.skills_to_improve.map(s => `<span class="badge bg-warning bg-opacity-10 text-dark border border-warning p-2 mt-2">${s} (Improve)</span>`).join('');
    }

    // 2. Display Course Advisor (Instant if cached)
    const container = document.getElementById('course-advisor-results');
    const loader = document.getElementById('course-advisor-loading');
    
    container.style.display = 'none';
    loader.style.display = 'block';

    let advisorData = appState.cachedAdvisorData;
    
    // Start status cycling to mask delay
    const statusSteps = document.getElementById('course-status-steps');
    const stepMessages = [
        "Synthesizing Syllabi...",
        "Evaluating Prerequisites...",
        "Calculating ROI...",
        "Cross-referencing Global Rankings...",
        "Filtering Specialized Content...",
        "Finalizing Curriculum..."
    ];
    let stepIdx = 0;
    const stepInterval = setInterval(() => {
        if (!loader || loader.style.display === 'none') {
            clearInterval(stepInterval);
            return;
        }
        if (statusSteps) {
            const badge = document.createElement('span');
            badge.className = 'badge rounded-pill bg-info bg-opacity-10 text-info border border-info border-opacity-25 py-2 px-3 animate-fade-in';
            badge.innerText = stepMessages[stepIdx % stepMessages.length];
            statusSteps.appendChild(badge);
            stepIdx++;
            if (statusSteps.children.length > 5) statusSteps.removeChild(statusSteps.children[0]);
        }
    }, 4500);

    if (!advisorData && appState.advisorPromise) {
        advisorData = await appState.advisorPromise;
    } else if (!advisorData) {
        await startCourseAdvisorBackgroundSearch();
        advisorData = await appState.advisorPromise;
    }
    
    clearInterval(stepInterval);
    loader.style.display = 'none';
    
    if (advisorData && advisorData.advisor_results) {
        container.style.display = 'block';
        const courses = advisorData.advisor_results.courses || [];
        const cardsContainer = document.getElementById('course-cards-container');
        
        if (courses.length === 0) {
            cardsContainer.innerHTML = '<div class="col-12"><p class="text-muted small">No specific courses needed or found. You are highly aligned!</p></div>';
        } else {
            cardsContainer.innerHTML = courses.map(c => {
                const isUdemy = c.platform.toLowerCase().includes('udemy');
                const platformClass = isUdemy ? 'text-purple fw-bold' : 'text-primary fw-bold';
                const priorityClass = c.priority.toLowerCase().includes('high') ? 'bg-danger' : 'bg-warning text-dark';
                
                return `
                <div class="col-md-6 col-lg-4">
                    <div class="card h-100 border shadow-sm hover-lift">
                        <div class="card-body p-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge bg-secondary bg-opacity-10 text-dark border">${c.skill}</span>
                                <span class="badge ${priorityClass}">${c.priority} Priority</span>
                            </div>
                            <h6 class="fw-bold mb-1" style="font-size:0.95rem;">${c.course_title}</h6>
                            <p class="small text-muted mb-3" style="font-size:0.8rem; height: 3.2em; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${c.reason}</p>
                            <div class="d-flex justify-content-between align-items-center mt-auto border-top pt-2">
                                <span class="small ${platformClass}"><i class="bi bi-mortarboard-fill me-1"></i>${c.platform}</span>
                                <span class="badge bg-light text-secondary border">${c.level}</span>
                            </div>
                            <div class="mt-3 text-center">
                                <a href="${c.course_link || '#'}" target="_blank" class="btn btn-sm btn-outline-primary fw-bold w-100 shadow-sm">Start Course <i class="bi bi-box-arrow-up-right ms-1"></i></a>
                            </div>
                        </div>
                    </div>
                </div>`;
            }).join('');
        }
    } else {
        console.error("Course Advisor Failed:", advisorData ? advisorData.error : "Unknown Error");
    }
}

function openEditResumeModal() {
    resetEditModal();
    const modalEl = document.getElementById('editResumeModal');
    if (!window.editModalInstance) {
        window.editModalInstance = new bootstrap.Modal(modalEl);
    }
    window.editModalInstance.show();
}

function resetEditModal() {
    const data = appState.parsedData || {};
    document.getElementById('edit-name').value = data.name || '';
    document.getElementById('edit-email').value = data.email || '';
    document.getElementById('edit-phone').value = data.phone || '';
    document.getElementById('edit-linkedin').value = data.linkedin || '';
    
    // Flatten skills text
    let sArray = [];
    (data.skills || []).forEach(s => { sArray.push(typeof s === 'string' ? s : s.name); });
    document.getElementById('edit-skills').value = sArray.join(', ');
    
    // Flatten experience and education
    let expText = '';
    (data.experience || []).forEach(e => {
        expText += `${e.title || 'Role'} at ${e.company || 'Company'} (${e.duration || 'Date'})\n${e.description || 'Resp'}\n\n`;
    });
    document.getElementById('edit-experience').value = expText.trim();
    
    let eduText = '';
    (data.education || []).forEach(e => {
        eduText += `${e.degree || 'Degree'} - ${e.institution || 'Inst'} (${e.year || 'Date'})\n`;
    });
    document.getElementById('edit-education').value = eduText.trim();

    // Flatten projects text
    let pArray = [];
    (data.projects || []).forEach(p => { pArray.push(p); });
    document.getElementById('edit-projects').value = pArray.join(', ');
}

async function saveEditAndOptimize() {
    const btn = document.querySelector('#editResumeModal .btn-primary');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
    btn.disabled = true;
    
    // Update simple fields
    appState.parsedData.name = document.getElementById('edit-name').value;
    appState.parsedData.email = document.getElementById('edit-email').value;
    appState.parsedData.phone = document.getElementById('edit-phone').value;
    appState.parsedData.linkedin = document.getElementById('edit-linkedin').value;
    
    appState.parsedData.skills = [document.getElementById('edit-skills').value];
    appState.parsedData.experience_raw = document.getElementById('edit-experience').value;
    appState.parsedData.education_raw = document.getElementById('edit-education').value;
    appState.parsedData.projects = [document.getElementById('edit-projects').value];

    const token = localStorage.getItem('access');
    try {
        await fetch(`/api/resume/update-parsed/${window.currentResumeId}/`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ parsed_data: appState.parsedData })
        });
    } catch (e) { console.error('Silent save err', e); }

    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-magic me-2"></i>Save & Optimize CV';

    if (window.editModalInstance) window.editModalInstance.hide();
    
    // Trigger Profile Merge Confirmation Modal
    openProfileUpdateModal();
}

function openProfileUpdateModal() {
    const modalEl = document.getElementById('saveProfileModal');
    if (!window.saveModalInstance) {
        window.saveModalInstance = new bootstrap.Modal(modalEl);
    }
    document.getElementById('save-profile-error').classList.add('d-none');
    document.getElementById('save-profile-success').classList.add('d-none');
    window.saveModalInstance.show();
}

async function proceedToOptimization(userConfirmed) {
    const btn = document.getElementById('btn-save-profile');
    const originalText = btn.innerHTML;
    
    if (userConfirmed) {
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Merging...';
        btn.disabled = true;

        const token = localStorage.getItem('access');
        try {
            const response = await fetch("/api/optimizer/profile/merge/", {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    resume_id: window.currentResumeId, 
                    user_confirmed: true,
                    new_data: appState.parsedData 
                })
            });
            const result = await response.json();
            if (result.update_profile) {
                document.getElementById('save-profile-success').classList.remove('d-none');
            }
        } catch (e) {
            console.error("Profile merge failed", e);
        }
    }

    setTimeout(() => {
        if (window.saveModalInstance) window.saveModalInstance.hide();
        runCVOptimizer();
        btn.innerHTML = originalText;
        btn.disabled = false;
    }, userConfirmed ? 1500 : 0);
}

async function runCVOptimizer() {
    goToStage(8);
    document.getElementById("optimizer-results").style.display = "none";
    document.getElementById("optimizer-loading").style.display = "block";
    
    const token = localStorage.getItem('access');
    
    // Extract gap report if available
    let gapText = "";
    if (appState.atsResults) {
        gapText = JSON.stringify({
            hard_skills_comparison: appState.atsResults.hard_skills_comparison,
            soft_skills_comparison: appState.atsResults.soft_skills_comparison,
            issue_summary: appState.atsResults.issue_summary
        });
    }

    try {
        const response = await fetch("/api/optimizer/variants/", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ resume_id: window.currentResumeId, gap_report: gapText })
        });
        
        const data = await response.json();
        document.getElementById("optimizer-loading").style.display = "none";
        
        if (response.ok && data.status === "success" && data.data) {
            const opt = data.data;
            document.getElementById("optimizer-results").style.display = "block";
            
            // Render text
            document.getElementById("cv-output-text").innerText = opt.optimized_cv_text || "";
            
            // Render score
            document.getElementById("optimized-score-display").innerText = `ATS Score: ${opt.new_ats_score_estimate || 0}`;
            
            // Render improvements
            const impList = document.getElementById('improvements-list');
            impList.innerHTML = (opt.improvements_made || []).map(i => `
                <li class="list-group-item d-flex align-items-center py-1 bg-transparent">
                    <i class="bi bi-star-fill text-warning me-2 small"></i>
                    <span class="small"><strong>${i.type}:</strong> ${i.change}</span>
                </li>
            `).join('');

            // Render suggestions
            const sugList = document.getElementById('suggestions-list');
            sugList.innerHTML = (opt.user_action_suggestions || []).map(s => `
                <li class="list-group-item d-flex align-items-center py-1 bg-transparent">
                    <i class="bi bi-lightning-fill text-primary me-2 small"></i>
                    <span class="small">${s}</span>
                </li>
            `).join('');

            // Store for Copy
            window.latestOptimizedCV = opt.optimized_cv_text;

            // Mark completed in DB
            await fetch('/api/resume/mark-completed/', {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    resume_id: window.currentResumeId,
                    score: opt.new_ats_score_estimate || 0,
                    optimized_content: opt.optimized_cv_text,
                    gap_data: appState.atsResults ? appState.atsResults.hard_skills_comparison : {}
                })
            });

        } else { 
            alert("Optimization failed. Returning to Skill Gap."); 
            goToStage(7); 
        }
    } catch(err) { 
        alert("Network Error during optimization."); 
        goToStage(7); 
    }
}

async function copyOptimizedCV() {
    const cvText = window.latestOptimizedCV || document.getElementById('cv-output-text').innerText;
    if(!cvText) return;

    try {
        await navigator.clipboard.writeText(cvText);
        const btn = document.querySelector('button[onclick="copyOptimizedCV()"]');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-all me-1"></i>Copied!';
        btn.classList.replace('btn-primary', 'btn-success');
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.replace('btn-success', 'btn-primary');
        }, 2000);
    } catch (err) {
        alert("Failed to copy to clipboard.");
    }
}

// End of logic

// --- UI Pipeline Helpers ---
function showPipelineSteps(containerId, steps) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = steps.map((step, idx) => `
        <div class="pipeline-step" id="${containerId}-step-${idx}">
            <div class="pipeline-dot"></div>
            <span class="small fw-medium">${step}</span>
        </div>
    `).join('');

    let currentStepIdx = 0;
    const interval = setInterval(() => {
        if (currentStepIdx > 0) {
            const prevStep = document.getElementById(`${containerId}-step-${currentStepIdx - 1}`);
            if (prevStep) {
                prevStep.classList.remove('active');
                prevStep.classList.add('completed');
                prevStep.querySelector('.pipeline-dot').innerHTML = '<i class="bi bi-check-circle-fill"></i>';
            }
        }
        
        const currentStep = document.getElementById(`${containerId}-step-${currentStepIdx}`);
        if (currentStep) {
            currentStep.classList.add('active');
        } else {
            clearInterval(interval);
        }
        currentStepIdx++;
    }, 1200); // Progress every 1.2s to mask backend delay
}

// Update existing loading functions to use pipeline
const originalFetchJobFamilies = fetchJobFamilies;
fetchJobFamilies = async function() {
    originalFetchJobFamilies.apply(this, arguments);
    showPipelineSteps('field-pipeline', [
        'Analyzing Skill Clusters...',
        'Mapping Industry Domains...',
        'Cross-referencing Global Standards...'
    ]);
};

const originalLockFieldAndPredictRoles = lockFieldAndPredictRoles;
lockFieldAndPredictRoles = async function() {
    originalLockFieldAndPredictRoles.apply(this, arguments);
    showPipelineSteps('predict-pipeline', [
        'Running Predictive Alignment...',
        'Matching Market Competencies...',
        'Optimizing Career Trajectory...'
    ]);
};

const originalGenerateTargetJD = generateTargetJD;
generateTargetJD = async function() {
    originalGenerateTargetJD.apply(this, arguments);
    showPipelineSteps('jd-pipeline', [
        'Synthesizing Master JD...',
        'Injecting Core Qualifications...',
        'Finalizing Professional Standards...'
    ]);
};

const originalLockJDAndRunATS = lockJDAndRunATS;
lockJDAndRunATS = async function() {
    originalLockJDAndRunATS.apply(this, arguments);
    setTimeout(() => {
        showPipelineSteps('ats-pipeline', [
            'Parsing Semantic Vectors...',
            'Executing Match Algorithms...',
            'Identifying Strategic Gaps...'
        ]);
    }, 100);
};

const originalRunCVOptimizer = runCVOptimizer;
runCVOptimizer = async function() {
    originalRunCVOptimizer.apply(this, arguments);
    showPipelineSteps('opt-pipeline', [
        'Re-architecting Professional Content...',
        'Systematic Keyword Injection...',
        'Optimizing for ATS Parsers...'
    ]);
};
