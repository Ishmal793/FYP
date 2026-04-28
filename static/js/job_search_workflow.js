window.currentResumeId = null;
window.selectedTargetRole = null;
window.currentLiveJobs = [];
window.selectedJob = null;
window.currentStage = 1;

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) { window.location.href = '/login/'; return; }

    try {
        const response = await fetch('/api/resume/completed/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        const loader = document.getElementById('loading-resumes');
        if(loader) loader.style.display = 'none';

        if (response.ok && data.resumes && data.resumes.length > 0) {
            const list = document.getElementById('resumes-list');
            data.resumes.forEach(r => {
                const dateSplit = r.created_at ? new Date(r.created_at).toLocaleDateString() : 'N/A';
                list.innerHTML += `
                    <div class="col-md-6">
                        <div class="glass-panel job-card-3d p-4 resume-card" onclick="selectResume(this, ${r.id}, '${r.role}')">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <div>
                                    <h5 class="fw-bold mb-1 text-dark">${r.role}</h5>
                                    <div class="text-muted" style="font-size: 11px;"><i class="bi bi-calendar3 me-2"></i>Computed on ${dateSplit}</div>
                                </div>
                                <span class="badge bg-emerald-500 bg-opacity-10 text-emerald-600 border border-emerald-500 border-opacity-20 rounded-pill px-3 py-2" style="color: var(--job-accent) !important;">
                                    ATS: ${r.score}%
                                </span>
                            </div>
                            <div class="d-flex align-items-center gap-2 small text-muted">
                                <i class="bi bi-file-earmark-check"></i> Verified Profile
                            </div>
                        </div>
                    </div>
                `;
            });
        } else {
            document.getElementById('no-resumes-warning').style.display = 'block';
        }
    } catch (error) {
        document.getElementById('loading-resumes').innerHTML = `<span class="text-danger">Network Error. Please reload.</span>`;
    }
    
    updateTracker(1);
});

function showPipelineSteps(containerId, steps) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = steps.map((step, i) => `
        <div class="v-pipeline-step" id="${containerId}-step-${i}">
            <div class="v-pipeline-dot"></div>
            <span>${step}</span>
        </div>
    `).join('');

    let current = 0;
    const interval = setInterval(() => {
        if (current < steps.length) {
            if (current > 0) {
                document.getElementById(`${containerId}-step-${current-1}`).classList.remove('active');
                document.getElementById(`${containerId}-step-${current-1}`).classList.add('completed');
            }
            document.getElementById(`${containerId}-step-${current}`).classList.add('active');
            current++;
        } else {
            clearInterval(interval);
        }
    }, 1500);

    // Return an object with a stop method that forces completion
    return {
        stop: () => {
            clearInterval(interval);
            steps.forEach((_, i) => {
                const el = document.getElementById(`${containerId}-step-${i}`);
                if (el) {
                    el.classList.remove('active');
                    el.classList.add('completed');
                }
            });
        }
    };
}

function updateTracker(stage) {
    window.currentStage = stage;
    const progressFill = document.getElementById('workflow-fill');
    if (progressFill) {
        const percentage = ((stage - 1) / 4) * 100;
        progressFill.style.width = `${percentage}%`;
    }

    for (let i = 1; i <= 5; i++) {
        const step = document.getElementById(`step-${i}`);
        if (!step) continue;
        
        step.classList.remove('active', 'completed');
        if (i < stage) {
            step.classList.add('completed');
        } else if (i === stage) {
            step.classList.add('active');
        }
    }
}

function goToStage(stageNum) {
    document.getElementById('stage-1-resume').style.display = stageNum === 1 ? 'block' : 'none';
    document.getElementById('stage-2-prefs').style.display = stageNum === 2 ? 'block' : 'none';
    document.getElementById('stage-3-results').style.display = stageNum === 3 ? 'block' : 'none';
    document.getElementById('deep-analysis-container').style.display = stageNum >= 4 ? 'block' : 'none';
    
    // Sub-containers for Stage 4 & 5
    if (stageNum >= 4) {
        document.getElementById('stage-4-container').style.display = stageNum === 4 ? 'block' : 'none';
        document.getElementById('stage-5-container').style.display = stageNum === 5 ? 'block' : 'none';
    }
    
    updateTracker(stageNum);
}

function backToJobs() {
    goToStage(3);
}

function selectResume(cardElement, resumeId, targetRole) {
    document.querySelectorAll('.resume-card').forEach(el => el.classList.remove('selected'));
    cardElement.classList.add('selected');
    window.currentResumeId = resumeId;
    window.selectedTargetRole = targetRole;

    const targetInput = document.getElementById('job-target-field');
    if(targetInput) targetInput.value = targetRole;
    
    document.getElementById('proceed-btn-1').classList.remove('disabled');
}

async function fetchAndScoreJobs() {
    const tField = document.getElementById('job-target-field').value || window.selectedTargetRole || 'Developer';
    const location = document.getElementById('job-location').value || 'Remote';
    const jobType = document.getElementById('job-type').value || 'Any';
    const timeFilter = document.getElementById('job-time').value || 'Any time';
    
    const btn = document.getElementById('search-live-jobs-btn');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

    goToStage(3);
    const loader = document.getElementById('fetching-jobs-loader');
    loader.classList.remove('d-none');
    
    document.getElementById('live-jobs-list').innerHTML = '';
    document.getElementById('low-job-warning').classList.add('d-none');
    document.getElementById('deep-analysis-container').style.display = 'none';

    const statusInterval = showPipelineSteps('fetch-pipeline', [
        "🌐 Connecting to LinkedIn job boards...",
        "🧩 Extracting live job cards...",
        "⚡ Parallel fetching detailed job descriptions...",
        "⚙️ Applying strict Date and Location filters...",
        "📊 Preparing Deep ATS matching engine..."
    ]);

    try {
        const response = await fetch('/api/search/search/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                titles: [tField], 
                location: location,
                job_type: jobType,
                time_filter: timeFilter,
                resume_id: window.currentResumeId
            })
        });

        statusInterval.stop();
        const data = await response.json();
        loader.classList.add('d-none');

        if (response.ok) {
            if (data.warning) {
                const warnBadge = document.getElementById('low-job-warning');
                warnBadge.innerHTML = data.warning.replace(/\n/g, '<br>');
                warnBadge.classList.remove('d-none');
            }

            if (data.live_jobs && data.live_jobs.length > 0) {
                window.currentLiveJobs = data.live_jobs;
                const listDiv = document.getElementById('live-jobs-list');
                
                data.live_jobs.forEach((job, index) => {
                    const isValidDescription = job.is_valid_description === true;
                    
                    let descriptionHtml = '';
                    if (!isValidDescription) {
                        descriptionHtml = `
                            <div class="jd-bridge-card" onclick="openManualATSModal(${index})">
                                <div class="bg-emerald-500 bg-opacity-10 rounded-circle p-2 text-emerald-600" style="color: var(--job-accent);">
                                    <i class="bi bi-shield-lock-fill"></i>
                                </div>
                                <div>
                                    <div class="fw-bold small text-dark">Content Restricted</div>
                                    <div class="text-muted" style="font-size: 11px;">Paste description to unlock Advanced AI Content Analysis</div>
                                </div>
                                <i class="bi bi-chevron-right ms-auto opacity-50"></i>
                            </div>
                        `;
                    } else {
                        descriptionHtml = `
                            <div class="small text-muted mb-2 border rounded p-2 bg-white" style="max-height: 120px; overflow-y: auto; line-height: 1.6; white-space: pre-wrap;">
                                ${job.description}
                            </div>
                        `;
                    }
                    
                    const btnHtml = `<button class="btn btn-sm btn-purple w-100 fw-bold" onclick="openManualATSModal(${index})">ATS Score <i class="bi bi-cpu ms-1"></i></button>`;

                    const applyLinkHtml = `<a href="${job.apply_link}" target="_blank" class="text-decoration-none small fw-bold text-primary d-block mt-1"><i class="bi bi-box-arrow-up-right me-1"></i>Open Job Link</a>`;

                    const isSaved = job.is_saved === true;
                    const heartClass = isSaved ? 'bi-heart-fill text-danger' : 'bi-heart';

                    listDiv.innerHTML += `
                        <div class="col-12 mb-4">
                            <div class="glass-panel job-card-3d position-relative overflow-hidden">
                                <div class="card-body p-4 d-flex flex-column flex-md-row align-items-md-center gap-4">
                                    <button class="btn btn-link position-absolute top-0 end-0 p-3 text-decoration-none" onclick="toggleSaveJob(this, '${job.apply_link}')">
                                        <i class="bi ${heartClass} fs-4"></i>
                                    </button>
                                    <div class="flex-shrink-0" style="width: 280px;">
                                        <h5 class="fw-bold text-truncate mb-1 pe-5" title="${job.title}">${job.title}</h5>
                                        <p class="text-emerald-500 small fw-bold mb-1" style="color: var(--job-accent);"><i class="bi bi-building me-2"></i>${job.company}</p>
                                        <div class="text-muted small mb-2"><i class="bi bi-geo-alt me-2"></i>${job.location}</div>
                                        <div class="mb-2 d-flex gap-2">
                                            <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25"><i class="bi bi-linkedin me-1"></i>LinkedIn</span>
                                            <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-25"><i class="bi bi-clock me-1"></i>${job.posting_time || 'Recent'}</span>
                                        </div>
                                        ${applyLinkHtml}
                                    </div>
                                    <div class="flex-grow-1 border-start ps-4" style="min-width: 0; border-color: rgba(var(--job-accent-rgb), 0.1) !important;">
                                        ${descriptionHtml}
                                    </div>
                                    <div class="flex-shrink-0 text-md-end" style="width: 180px;">
                                        ${btnHtml}
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                document.getElementById('live-jobs-list').innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-search text-muted" style="font-size: 3rem;"></i>
                        <h5 class="fw-bold mt-3">No jobs found for your selected filters.</h5>
                        <p class="text-muted">Please try:<br>- Different location<br>- Broader time range<br>- Another job role<br>- Remote option</p>
                        <div class="mt-3">
                            <button class="btn btn-outline-success mx-1" onclick="fetchAndScoreJobs()"><i class="bi bi-arrow-repeat me-1"></i>Retry Search</button>
                            <button class="btn btn-outline-secondary mx-1" onclick="goToStage(1)"><i class="bi bi-file-person me-1"></i>Select Another Resume</button>
                        </div>
                    </div>`;
            }
        } else { alert(data.error); }
    } catch { 
        clearInterval(statusInterval);
        alert('Network Error'); 
        loader.classList.add('d-none');
    }
    finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-search me-2"></i>Fetch & Fast Match';
    }
}

let manualATSIndex = null;

function openManualATSModal(index) {
    manualATSIndex = index;
    const job = window.currentLiveJobs[index];
    const modal = new bootstrap.Modal(document.getElementById('manualATSModal'));
    
    // Pre-fill if valid, otherwise empty
    document.getElementById('manual-jd-text').value = job.is_valid_description ? job.description : '';
    
    modal.show();
}

async function submitManualATS() {
    const text = document.getElementById('manual-jd-text').value.trim();
    if (!text || text.length < 50) {
        alert("Please paste a valid job description (min 50 characters).");
        return;
    }
    
    // Close modal
    const modalEl = document.getElementById('manualATSModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();
    
    // Update the job object in window.currentLiveJobs
    window.currentLiveJobs[manualATSIndex].description = text;
    window.currentLiveJobs[manualATSIndex].is_valid_description = true; 
    
    // Run normal deep analysis
    runDeepAnalysis(manualATSIndex);
}

async function runDeepAnalysis(index) {
    if (!window.currentLiveJobs || window.currentLiveJobs.length <= index) return;
    
    window.selectedJob = window.currentLiveJobs[index];
    const job = window.selectedJob;
    const token = localStorage.getItem('access');
    
    // STRICT MODULE SEPARATION: Hide Match, Show Deep Analysis
    goToStage(4);
    
    // Reset UI
    const resultsContainer = document.getElementById('deep-ats-results');
    const skillContainer = document.getElementById('skill-analysis-results');
    const loader = document.getElementById('deep-ats-loader');

    
    loader.classList.remove('d-none');
    resultsContainer.classList.add('d-none');
    skillContainer.innerHTML = ''; 
    resultsContainer.innerHTML = ''; 

    
    const statusInterval = showPipelineSteps('deep-ats-pipeline', [
        "🔬 Tokenizing job description...",
        "🔗 Running semantic cross-reference...",
        "🧠 Calculating AI Content Quality...",
        "✅ Synthesizing Strategic Insights..."
    ]);
    try {
        const response = await fetch('/api/ats/match/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_id: window.currentResumeId, jobs: [job] })
        });
        
        const data = await response.json();
        statusInterval.stop();
        loader.classList.add('d-none');
        
        if (response.ok && data.match_results) {
            const r = data.match_results;
            window.currentAtsResults = r;
            resultsContainer.classList.remove('d-none');
            
            // EXACT SAME UI RENDERING AS ATS INTELLIGENCE MODULE
            const issues = r.issue_summary || {};
            const search = r.searchability || {};
            const scoreBrk = r.score_breakdown || {};
            const quality = r.content_quality || {};

            let hsRows = (r.hard_skills_comparison || []).map(row => {
                let badge = row.status === 'Match' ? '<span class="badge bg-success">Match</span>' : (row.status === 'Missing' ? '<span class="badge bg-danger">Missing</span>' : '<span class="badge bg-warning text-dark">Partial</span>');
                return `<tr><td class="text-start fw-bold">${row.skill_name}</td><td class="text-center">${row.resume_count}</td><td class="text-center">${row.jd_count}</td><td class="text-center">${badge}</td></tr>`;
            }).join('');
            
            let ssRows = (r.soft_skills_comparison || []).map(row => {
                let badge = row.status === 'Match' ? '<span class="badge bg-success">Match</span>' : '<span class="badge bg-danger">Missing</span>';
                return `<tr><td class="text-start fw-bold">${row.skill_name}</td><td>${row.resume_status}</td><td>${row.jd_status}</td><td class="text-center">${badge}</td></tr>`;
            }).join('');

            resultsContainer.innerHTML = `
                <div class="row g-4 mb-4">
                    <div class="col-md-4 text-center d-flex flex-column justify-content-center align-items-center border-end">
                        <h4 class="text-secondary fw-bold mb-3">Overall Match</h4>
                        <div class="rounded-circle d-flex align-items-center justify-content-center shadow-sm" style="width: 150px; height: 150px; border: 8px solid ${r.overall_match_score >= 80 ? '#22c55e' : (r.overall_match_score >= 50 ? '#eab308' : '#ef4444')}; font-size: 3rem; font-weight: 900; color: #1e293b;">
                            ${r.overall_match_score}%
                        </div>
                    </div>
                    <div class="col-md-8">
                        <h5 class="fw-bold text-dark border-bottom pb-2 mb-3">Issue Summary</h5>
                        <div class="row g-2 mb-3">
                            <div class="col-6 col-md-3"><div class="p-2 bg-danger bg-opacity-10 rounded text-center border"><h4 class="text-danger mb-0">${issues.hard_skills_issues || 0}</h4><small class="text-muted fw-bold" style="font-size:10px;">Hard Skill Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-2 bg-warning bg-opacity-10 rounded text-center border"><h4 class="text-warning mb-0">${issues.soft_skills_issues || 0}</h4><small class="text-muted fw-bold" style="font-size:10px;">Soft Skill Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-2 bg-info bg-opacity-10 rounded text-center border"><h4 class="text-info mb-0">${issues.searchability_issues || 0}</h4><small class="text-muted fw-bold" style="font-size:10px;">Searchability Issues</small></div></div>
                            <div class="col-6 col-md-3"><div class="p-2 bg-success bg-opacity-10 rounded text-center border"><h4 class="text-success mb-0">${issues.recruiter_tips_count || 0}</h4><small class="text-muted fw-bold" style="font-size:10px;">Recruiter Tips</small></div></div>
                        </div>
                        
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-3">
                             <h6 class="fw-bold x-small text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-briefcase-fill text-primary me-2"></i>Deep Experience Analysis</h6>
                             <div class="mb-2">
                                <span class="badge ${r.deep_experience?.status?.includes('Match') ? 'bg-success' : 'bg-warning text-dark'} mb-2">${r.deep_experience?.status || 'Unknown'}</span>
                                <div class="small fw-bold text-dark mb-1">Extracted Years: <span class="text-primary">${r.deep_experience?.years_extracted || 'N/A'}</span></div>
                                <div class="x-small text-muted mb-2">${r.deep_experience?.relevance_explanation || ''}</div>
                             </div>
                             <div class="x-small text-dark border-top pt-2">
                                <span class="fw-bold"><i class="bi bi-magic text-warning me-1"></i>Improvement:</span> ${(r.deep_experience?.suggestions || []).join(', ')}
                             </div>
                        </div>
                    </div>
                </div>
                
                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-3 h-100">
                             <h6 class="fw-bold x-small text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-mortarboard-fill text-info me-2"></i>Deep Education Analysis</h6>
                             <div class="mb-2">
                                <span class="badge ${r.deep_education?.status?.includes('Match') ? 'bg-info' : 'bg-danger'} mb-2">${r.deep_education?.status || 'Unknown'}</span>
                                <div class="x-small text-muted mb-2">${r.deep_education?.explanation || ''}</div>
                             </div>
                             <div class="x-small text-dark border-top pt-2">
                                <span class="fw-bold"><i class="bi bi-magic text-warning me-1"></i>Improvement:</span> ${(r.deep_education?.suggestions || []).join(', ')}
                             </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card glass-panel border-0 bg-light bg-opacity-50 p-3 h-100">
                             <h6 class="fw-bold x-small text-uppercase tracking-wider text-muted mb-3"><i class="bi bi-file-earmark-text text-success me-2"></i>Quality & Formatting Check</h6>
                             <ul class="list-group list-group-flush x-small mb-2 bg-transparent">
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-1">Measurable Results <span class="badge ${r.deep_quality?.measurable_results_found ? 'bg-success' : 'bg-danger'}">${r.deep_quality?.measurable_results_found ? 'Found' : 'Missing'}</span></li>
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-1">Strong Action Verbs <span class="badge ${r.deep_quality?.action_verbs_strong ? 'bg-success' : 'bg-warning text-dark'}">${r.deep_quality?.action_verbs_strong ? 'Strong' : 'Weak'}</span></li>
                                <li class="list-group-item bg-transparent px-0 d-flex justify-content-between align-items-center border-0 py-1">Job Title Match <span class="badge ${r.deep_job_title?.status?.includes('Found') ? 'bg-success' : 'bg-danger'}">${r.deep_job_title?.status || 'Not Found'}</span></li>
                             </ul>
                             <div class="x-small text-dark border-top pt-2">
                                <div class="mb-1"><span class="fw-bold"><i class="bi bi-chat-right-quote text-secondary me-1"></i>Feedback:</span> ${r.deep_quality?.feedback || ''}</div>
                                <div><span class="fw-bold"><i class="bi bi-magic text-warning me-1"></i>Suggestion:</span> ${r.deep_job_title?.suggestion || ''}</div>
                             </div>
                        </div>
                    </div>
                </div>

                <div class="card bg-success bg-opacity-10 border-success border-opacity-25 mb-4 shadow-sm">
                    <div class="card-body p-3">
                        <h6 class="fw-bold text-success small mb-2"><i class="bi bi-robot text-success me-2"></i>Smart Recruiter Insights</h6>
                        <ul class="mb-0 x-small text-dark ps-3" style="line-height: 1.6;">
                            ${(r.deep_insights || r.recruiter_tips || []).map(tip => `<li>${tip}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <h6 class="fw-bold text-dark small"><i class="bi bi-cpu text-primary me-2"></i>Hard Skills Comparison</h6>
                        <div class="table-responsive" style="max-height: 250px;">
                            <table class="table table-bordered table-sm x-small table-hover mb-0">
                                <thead class="table-light"><tr><th>Skill</th><th class="text-center">Res</th><th class="text-center">JD</th><th class="text-center">Status</th></tr></thead>
                                <tbody>${hsRows}</tbody>
                            </table>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="fw-bold text-dark small"><i class="bi bi-people text-info me-2"></i>Soft Skills Comparison</h6>
                        <div class="table-responsive" style="max-height: 250px;">
                            <table class="table table-bordered table-sm x-small table-hover mb-0">
                                <thead class="table-light"><tr><th>Skill</th><th>Res</th><th>JD</th><th class="text-center">Status</th></tr></thead>
                                <tbody>${ssRows}</tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="mb-0 pt-3 border-top border-primary border-opacity-10">
                    <h6 class="fw-bold text-dark small mb-3"><i class="bi bi-zoom-in text-danger me-2"></i>Final Skill Gap Analysis</h6>
                    <div class="row g-3">
                        <div class="col-6">
                            <div class="p-3 bg-success bg-opacity-10 rounded border border-success border-opacity-25 h-100">
                                <span class="small text-success fw-bold d-block mb-2"><i class="bi bi-check-circle-fill me-1"></i>Skills You Have:</span>
                                <div class="d-flex flex-wrap gap-1">
                                    ${(r.skill_gap_summary?.skills_you_have || []).map(s => `<span class="badge bg-success bg-opacity-25 text-success border border-success" style="font-size: 10px;">${s}</span>`).join('') || '<span class="text-muted small">None</span>'}
                                </div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 bg-danger bg-opacity-10 rounded border border-danger border-opacity-25 h-100">
                                <span class="small text-danger fw-bold d-block mb-2"><i class="bi bi-exclamation-octagon-fill me-1"></i>Missing Critical:</span>
                                <div class="d-flex flex-wrap gap-1">
                                    ${(r.skill_gap_summary?.missing_critical_skills || []).map(s => `<span class="badge bg-danger bg-opacity-25 text-danger border border-danger" style="font-size: 10px;">${s}</span>`).join('') || '<span class="text-success small fw-bold">None! You are ready.</span>'}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-top text-center">
                        ${r.overall_match_score >= 70 ? 
                            `<button class="btn btn-emerald-600 fw-bold px-5 py-2 shadow-sm rounded-pill" onclick="openOptimizationModal()" style="background: var(--job-accent); color: white; border: none;"><i class="bi bi-magic me-2"></i>Unlock Deep Optimization</button>` :
                            `<button class="btn btn-secondary fw-bold px-5 py-2 shadow-sm rounded-pill" disabled title="Achieve at least 70% ATS score to unlock optimization"><i class="bi bi-lock-fill me-2"></i>Optimization Locked (Requires 70%+)</button>`
                        }
                    </div>
                </div>
            `;



            // Trigger 70% Modal
            if (r.overall_match_score >= 70) {
                document.getElementById('modal-score-val').innerText = r.overall_match_score + '%';
                document.getElementById('modal-job-title').innerText = job.title;
                document.getElementById('modal-apply-btn').href = job.apply_link;
                const modal = new bootstrap.Modal(document.getElementById('applyModal'));
                modal.show();
            }
        } else {
            alert('Deep ATS analysis failed.');
        }
    } catch (e) {
        document.getElementById('deep-ats-loader').classList.add('d-none');
        console.error("[DEBUG] runDeepAnalysis error:", e);
    }
}

async function toggleSaveJob(btn, applyLink) {
    const token = localStorage.getItem('access');
    const icon = btn.querySelector('i');
    
    try {
        const response = await fetch('/api/search/save-job/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ apply_link: applyLink })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.is_saved) {
                icon.className = 'bi bi-heart-fill text-danger fs-4';
                showToast("Job saved to your profile!", "success");
            } else {
                icon.className = 'bi bi-heart fs-4';
                showToast("Job removed from saved list.", "info");
            }
        }
    } catch (e) { console.error(e); }
}

function openOptimizationModal() {
    const modal = new bootstrap.Modal(document.getElementById('optimizationModal'));
    modal.show();
}

async function startOptimizing() {
    // Close modal
    const modalEl = document.getElementById('optimizationModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();

    const instructions = document.getElementById('optimization-instructions').value.trim();

    // Switch to Stage 5: Optimization
    goToStage(5);
    document.getElementById('optimizer-results').style.display = 'none';
    document.getElementById('optimizer-loading').style.display = 'block';

    const token = localStorage.getItem('access');
    let gapText = "";
    if (window.currentAtsResults) {
        gapText = JSON.stringify({
            hard_skills_comparison: window.currentAtsResults.hard_skills_comparison,
            soft_skills_comparison: window.currentAtsResults.soft_skills_comparison,
            custom_instructions: instructions
        });
    }

    const pipelineSteps = [
        "🔍 Parsing custom optimization constraints...",
        "🧠 Re-structuring CV logic via AI...",
        "⚙️ Injecting missing ATS keywords...",
        "✅ Finalizing optimized document..."
    ];
    const statusInterval = showPipelineSteps('optimizer-pipeline', pipelineSteps);

    try {
        const response = await fetch("/api/optimizer/variants/", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ resume_id: window.currentResumeId, gap_report: gapText })
        });
        
        const data = await response.json();
        statusInterval.stop();
        document.getElementById("optimizer-loading").style.display = "none";
        
        if (response.ok && data.status === "success" && data.data) {
            const opt = data.data;
            document.getElementById("optimizer-results").style.display = "block";
            
            document.getElementById("cv-output-text").innerText = opt.optimized_cv_text || "";
            document.getElementById("optimized-score-display").innerText = `ATS Score: ${opt.new_ats_score_estimate || 0}`;
            
            const impList = document.getElementById('improvements-list');
            impList.innerHTML = (opt.improvements_made || []).map(i => `
                <li class="list-group-item d-flex align-items-center py-1 bg-transparent">
                    <i class="bi bi-star-fill text-warning me-2 small"></i>
                    <span class="small"><strong>${i.type}:</strong> ${i.change}</span>
                </li>
            `).join('');

            const sugList = document.getElementById('suggestions-list');
            sugList.innerHTML = (opt.user_action_suggestions || []).map(s => `
                <li class="list-group-item d-flex align-items-center py-1 bg-transparent">
                    <i class="bi bi-lightning-fill text-primary me-2 small"></i>
                    <span class="small">${s}</span>
                </li>
            `).join('');

            window.latestOptimizedCV = opt.optimized_cv_text;

        } else {
            alert("Optimization failed.");
            document.getElementById('deep-ats-results').classList.remove('d-none');
        }
    } catch(err) {
        console.error(err);
        alert("Network error during optimization.");
        document.getElementById("optimizer-loading").style.display = "none";
        document.getElementById('deep-ats-results').classList.remove('d-none');
        if(statusInterval) statusInterval.stop();
    }
}

function copyOptimizedCV() {
    if (window.latestOptimizedCV) {
        navigator.clipboard.writeText(window.latestOptimizedCV);
        showToast("Optimized CV copied to clipboard!", "success");
    }
}
