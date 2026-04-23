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
                        <div class="card p-3 resume-card" onclick="selectResume(this, ${r.id}, '${r.role}')">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="fw-bold mb-0 text-success">${r.role}</h6>
                                <span class="badge bg-success bg-opacity-25 text-success">ATS Score: ${r.score}</span>
                            </div>
                            <small class="text-muted"><i class="bi bi-clock me-1"></i>Computed on ${dateSplit}</small>
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

function updateTracker(stage) {
    window.currentStage = stage;
    const progressLine = document.getElementById('workflow-progress-line');
    if (progressLine) {
        const percentage = ((stage - 1) / 4) * 100;
        progressLine.style.width = `${percentage}%`;
    }

    for (let i = 1; i <= 5; i++) {
        const circle = document.getElementById(`step-${i}-circle`);
        const text = document.getElementById(`step-${i}-text`);
        
        if (!circle || !text) continue;
        
        if (i < stage) {
            circle.className = 'rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-white shadow-sm ring-4 ring-green-100';
            circle.style.background = 'linear-gradient(to top right, #198754, #20c997)';
            circle.innerHTML = '<i class="bi bi-check-lg small"></i>';
            text.className = 'small fw-bold mb-0 text-success';
        } else if (i === stage) {
            circle.className = 'rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-white shadow-sm ring-4 ring-green-100';
            circle.style.background = 'linear-gradient(to top right, #198754, #20c997)';
            text.className = 'small fw-bold mb-0 text-success';
            
            // Reset icons based on step
            if(i===1) circle.innerHTML = '<i class="bi bi-file-person small"></i>';
            if(i===2) circle.innerHTML = '<i class="bi bi-search small"></i>';
            if(i===3) circle.innerHTML = '<i class="bi bi-lightning-charge small"></i>';
            if(i===4) circle.innerHTML = '<i class="bi bi-cpu small"></i>';
            if(i===5) circle.innerHTML = '<i class="bi bi-cpu-fill small"></i>';
        } else {
            circle.className = 'rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-secondary bg-body-tertiary shadow-sm';
            circle.style.background = '';
            text.className = 'small fw-bold mb-0 text-secondary';
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
    const loaderText = document.getElementById('loading-status-text');
    loader.classList.remove('d-none');
    
    document.getElementById('live-jobs-list').innerHTML = '';
    document.getElementById('low-job-warning').classList.add('d-none');
    document.getElementById('deep-analysis-container').style.display = 'none';

    // Simulate Dynamic Status text since API handles it all in one go
    let stageCount = 0;
    const stages = ["🔍 Finding jobs...", "⚙ Validating requirements...", "📊 Calculating match scores..."];
    loaderText.innerText = stages[0];
    const statusInterval = setInterval(() => {
        stageCount++;
        if (stageCount < stages.length) {
            loaderText.innerText = stages[stageCount];
        }
    }, 1500);

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

        clearInterval(statusInterval);
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
                            <div class="alert alert-warning small p-2 mb-0 border-0 bg-warning bg-opacity-10 text-dark">
                                <i class="bi bi-exclamation-triangle-fill me-1 text-warning"></i>
                                <strong>⚠️ Description not available</strong><br>
                                <span class="text-muted small">👉 Click "Open Job Link" and copy description for ATS analysis</span>
                            </div>
                        `;
                    } else {
                        descriptionHtml = `
                            <div class="small text-muted mb-0" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis;">
                                ${job.description}
                            </div>
                        `;
                    }
                    
                    const btnHtml = `<button class="btn btn-sm btn-purple w-100 fw-bold" onclick="openManualATSModal(${index})">ATS Score <i class="bi bi-cpu ms-1"></i></button>`;

                    const applyLinkHtml = `<a href="${job.apply_link}" target="_blank" class="text-decoration-none small fw-bold text-primary d-block mt-1"><i class="bi bi-box-arrow-up-right me-1"></i>Open Job Link</a>`;

                    listDiv.innerHTML += `
                        <div class="col-12 mb-3">
                            <div class="card border-secondary border-opacity-25 shadow-sm hover-elevate bg-white">
                                <div class="card-body p-3 d-flex flex-column flex-md-row align-items-md-center gap-3">
                                    <div class="flex-shrink-0" style="width: 250px;">
                                        <h6 class="fw-bold text-truncate mb-1" title="${job.title}">${job.title}</h6>
                                        <p class="text-primary small fw-medium mb-0"><i class="bi bi-building me-1"></i>${job.company}</p>
                                        <span class="text-muted small"><i class="bi bi-geo-alt me-1"></i>${job.location}</span>
                                        ${applyLinkHtml}
                                    </div>
                                    <div class="flex-grow-1 border-start px-3" style="min-width: 0;">
                                        ${descriptionHtml}
                                    </div>
                                    <div class="flex-shrink-0 text-md-end" style="width: 150px;">
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
    const nextBtn = document.getElementById('btn-next-skills');
    
    loader.classList.remove('d-none');
    resultsContainer.classList.add('d-none');
    skillContainer.innerHTML = ''; 
    resultsContainer.innerHTML = ''; 
    nextBtn.style.display = 'none';
    
    // Fire Deep ATS

    try {
        const response = await fetch('/api/ats/match/', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_id: window.currentResumeId, jobs: [job] })
        });
        
        const data = await response.json();
        loader.classList.add('d-none');
        
        if (response.ok && data.match_results) {
            const r = data.match_results;
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
                        <div class="d-flex flex-wrap gap-2 small">
                            <span class="badge bg-secondary">Exp: ${scoreBrk.experience_score}/20</span>
                            <span class="badge bg-secondary">Edu: ${scoreBrk.education_score}/10</span>
                            <span class="badge bg-secondary">Format: ${scoreBrk.keyword_format_score}/20</span>
                            <span class="badge bg-secondary">Skills: ${scoreBrk.hard_skills_score}/40</span>
                        </div>
                    </div>
                </div>
                
                <div class="row g-3 mb-4">
                    <div class="col-md-6">
                        <div class="card shadow-sm border-0 h-100">
                            <div class="card-header bg-light fw-bold small"><i class="bi bi-search me-2"></i>Searchability Check</div>
                            <ul class="list-group list-group-flush x-small">
                                <li class="list-group-item d-flex justify-content-between align-items-center">Contact Info <span class="badge ${search.contact_info?.email === 'Present' && search.contact_info?.phone === 'Present' ? 'bg-success' : 'bg-danger'}">${search.contact_info?.email || 'Missing'}/${search.contact_info?.phone || 'Missing'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Summary Section <span class="badge ${search.summary_section?.includes('Present') ? 'bg-success' : 'bg-danger'}">${search.summary_section || 'Missing'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Job Title Match <span class="badge ${search.job_title_match?.includes('Found') ? 'bg-success' : 'bg-danger'}">${search.job_title_match || 'Not Found'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Education Heading <span class="badge ${search.education_heading?.includes('Present') ? 'bg-success' : 'bg-danger'}">${search.education_heading || 'Missing'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Experience Heading <span class="badge ${search.experience_heading?.includes('Present') ? 'bg-success' : 'bg-danger'}">${search.experience_heading || 'Missing'}</span></li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card shadow-sm border-0 h-100">
                            <div class="card-header bg-light fw-bold small"><i class="bi bi-file-earmark-text me-2"></i>Content Quality</div>
                            <ul class="list-group list-group-flush x-small">
                                <li class="list-group-item d-flex justify-content-between align-items-center">Measurable Results <span class="badge ${quality.measurable_results === 'Found' ? 'bg-success' : 'bg-warning text-dark'}">${quality.measurable_results || 'N/A'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Resume Tone <span class="badge ${quality.resume_tone === 'Positive' ? 'bg-success' : 'bg-secondary'}">${quality.resume_tone || 'N/A'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Web Presence <span class="badge ${quality.web_presence === 'Present' ? 'bg-success' : 'bg-danger'}">${quality.web_presence || 'N/A'}</span></li>
                                <li class="list-group-item d-flex justify-content-between align-items-center">Word Count <span class="badge bg-secondary">${quality.word_count_status || 'N/A'}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="card bg-light border-0 mb-0 shadow-sm">
                    <div class="card-body p-3">
                        <h6 class="fw-bold text-dark small mb-2"><i class="bi bi-lightbulb-fill text-warning me-2"></i>Recruiter Tips</h6>
                        <ul class="mb-0 x-small text-muted ps-3">
                            ${(r.recruiter_tips || []).map(tip => `<li>${tip}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;

            skillContainer.innerHTML = `
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

                <div class="mb-0 pt-3 border-top">
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
                </div>
            `;

            nextBtn.style.display = 'block';

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


