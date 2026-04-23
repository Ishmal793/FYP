let currentStage = 1;

let appState = {
    resumeId: null,
    parsedData: null,
    readinessScore: null,
    predictedJobs: [],
    atsResults: [],
    jobSearchUnlocked: false
};

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    try {
        const response = await fetch('/api/auth/profile/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();

            // Check if Job Search should be unlocked globally
            const resResponse = await fetch('/api/resume/completed/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (resResponse.ok) {
                const resData = await resResponse.json();
                appState.jobSearchUnlocked = resData.resumes && resData.resumes.length > 0;
            }

            // Populate fields
            document.getElementById('user-name-display').innerText = data.name || data.email;
            document.getElementById('summary-name').innerText = data.name || 'Not set';
            document.getElementById('summary-email').innerText = data.email;
            
            const profile = data.career_profile || {};
            document.getElementById('summary-level').innerText = profile.career_level || 'Not set';
            document.getElementById('summary-role').innerText = profile.target_job_role || 'Not set';
            document.getElementById('summary-location').innerText = (profile.preferred_locations && profile.preferred_locations.length) ? profile.preferred_locations.join(', ') : 'Not set';

            const roleBadge = document.getElementById('user-role');
            if (data.role === 'job_seeker') {
                roleBadge.innerText = 'Job Seeker';
                roleBadge.className = 'badge bg-primary bg-opacity-10 text-primary border border-primary-subtle ms-1 fw-medium';
                document.getElementById('job-seeker-view').style.display = 'block';
                document.getElementById('profile-summary-section').style.display = 'none';
                updateWorkflowStage(1);
            } else {
                roleBadge.innerText = 'HR / Recruiter';
                roleBadge.className = 'badge bg-success bg-opacity-10 text-success border border-success-subtle ms-1 fw-medium';
                document.getElementById('hr-view').style.display = 'block';
            }

            // Show sections
            if (document.getElementById('loading')) document.getElementById('loading').style.display = 'none';
            if (document.getElementById('dashboard-header')) document.getElementById('dashboard-header').style.display = 'flex';
            if (document.getElementById('dashboard-content')) document.getElementById('dashboard-content').style.display = 'flex';
        } else if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('access');
            localStorage.removeItem('refresh');
            window.location.href = '/login/';
        } else {
            if (document.getElementById('loading')) document.getElementById('loading').innerHTML = '<div class="alert alert-danger mx-auto" style="max-width:400px;">Failed to load profile.</div>';
        }
    } catch (error) {
        console.error("Error fetching profile:", error);
        if (document.getElementById('loading')) {
            document.getElementById('loading').innerHTML = `<div class="alert alert-danger mx-auto" style="max-width:800px; text-align:left;">
                <h5>UI Rendering Error</h5>
                <pre style="white-space: pre-wrap; font-size: 12px;">${error.name}: ${error.message}\n${error.stack}</pre>
            </div>`;
        }
    }
});

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const btn = document.getElementById('upload-btn');
    const statusDiv = document.getElementById('upload-status');
    const resultsDiv = document.getElementById('parsed-results');
    const token = localStorage.getItem('access');

    // Reset UI
    resultsDiv.style.display = 'none';
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Parsing with AI...';
    
    // Modern parsing blocks on upload
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `
        <div class="text-center py-4 mt-3 rounded border border-primary border-opacity-10 bg-primary bg-opacity-10 shadow-sm">
            <div class="spinner-grow text-primary mb-3" style="width: 2.5rem; height: 2.5rem;" role="status"></div>
            <h6 class="fw-bold text-primary mb-1">AI Document Analysis</h6>
            <p class="small text-muted mb-0">Extracting skills, experience, and structuring your profile...</p>
        </div>
    `;
    
    // Set to Step 2 since we are actively parsing now
    updateWorkflowStage(2);

    const formData = new FormData();
    formData.append('resume', file);

    try {
        const response = await fetch('/api/resume/parse/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.innerHTML = `<span class="text-success"><i class="bi bi-check-circle-fill me-1"></i> Successfully parsed!</span>`;
            
            // Expose resume ID globally for next stage
            window.currentResumeId = data.resume_id;
            
            // Protect against malformed JSON from returning AI
            const safeParsedData = data.parsed_state || data.parsed_data || {};
            displayParsedData(safeParsedData);

            document.getElementById('field-results').style.display = 'none';
            
            updateWorkflowStage(2);

        } else {
            let errorMsg = data.error || 'Failed to parse resume.';
            statusDiv.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i> ${errorMsg}</span>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle-fill me-1"></i> Network error. Please try again.</span>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Upload Another Resume';
        event.target.value = ''; // reset input
    }
}

async function fetchJobFamilies(btnElement = null) {
    if (!window.currentResumeId) return;

    const resultsDiv = document.getElementById('field-results');
    const dropdown = document.getElementById('ai-career-field-dropdown');
    const token = localStorage.getItem('access');

    try {
        const response = await fetch('/api/fields/classify/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('field-loading').style.display = 'none';
            document.getElementById('field-content').style.display = 'block';
            dropdown.innerHTML = '<option value="" disabled selected>-- Select an AI suggestion --</option>';

            if (data.job_families && data.job_families.length > 0) {
                data.job_families.forEach(family => {
                    dropdown.innerHTML += `<option value="${family}">${family}</option>`;
                });
            } else {
            }
            if (btnElement) btnElement.style.display = 'none';
            
            updateWorkflowStage(3);
        } else {
            alert(data.error || 'Failed to classify job fields.');
            document.getElementById('field-results').style.display = 'none';
            document.getElementById('verify-parsed-form').style.display = 'block'; // Unhide past block on error
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Confirm Data & Analyze Match';
            }
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred while classifying fields.');
        document.getElementById('field-results').style.display = 'none';
        document.getElementById('verify-parsed-form').style.display = 'block'; // Unhide past block on error
        if (btnElement) {
            btnElement.disabled = false;
            btnElement.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Confirm Data & Analyze Match';
        }
    }
}

async function lockFieldAndScoreReadiness() {
    if (!window.currentResumeId) return;
    
    const targetFieldInput = document.getElementById('custom-career-field').value.trim();
    if (!targetFieldInput) {
        alert("Please type a career field or select one from the AI suggestions.");
        return;
    }

    const btn = document.getElementById('analyze-readiness-btn');
    const resultsDiv = document.getElementById('readiness-results');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Locking & Evaluating...';

    // Show massive loading state
    document.getElementById('readiness-loading').style.display = 'block';
    resultsDiv.style.display = 'none';

    // Lock the field visually
    document.getElementById('custom-career-field').disabled = true;
    document.getElementById('ai-career-field-dropdown').disabled = true;

    try {
        const response = await fetch('/api/readiness/score/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                resume_id: window.currentResumeId,
                target_field: targetFieldInput 
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('readiness-loading').style.display = 'none';
            resultsDiv.style.display = 'block';
            
            // Hide previous container as per User requirement
            document.getElementById('field-results').style.display = 'none';
            
            // Render Overall Score
            const overallScore = data.overall_score || 0;
            const scoreSpan = document.getElementById('ats-overall-score');
            scoreSpan.innerText = overallScore;
            
            // Score Colors
            const scoreCircle = scoreSpan.parentElement.parentElement;
            scoreCircle.className = `bg-white border border-3 rounded-circle d-flex align-items-center justify-content-center shadow-sm mx-auto ${overallScore >= 80 ? 'border-success' : overallScore >= 50 ? 'border-warning' : 'border-danger'}`;
            scoreSpan.className = overallScore >= 80 ? 'text-success' : overallScore >= 50 ? 'text-warning' : 'text-danger';
            document.getElementById('ats-score-message').innerText = overallScore >= 80 ? 'Strong ATS Match!' : overallScore >= 50 ? 'Needs Improvement' : 'Critical Mismatch Detected';

            // Title Match Check
            const titleMatch = data.searchability_title_match || {};
            const titleBadge = document.getElementById('ats-title-status');
            if (titleMatch.matched) {
                titleBadge.className = 'badge bg-success';
                titleBadge.innerHTML = '<i class="bi bi-check-circle me-1"></i>Found';
            } else {
                titleBadge.className = 'badge bg-danger';
                titleBadge.innerHTML = '<i class="bi bi-x-circle me-1"></i>Missing';
            }

            // Contact Info
            const contact = data.contact_info || {};
            const contactList = [];
            if (contact.email) contactList.push('Email');
            if (contact.phone) contactList.push('Phone');
            if (contact.location) contactList.push('Location');
            document.getElementById('ats-contact-info').innerHTML = contactList.length > 0 ? contactList.join(', ') : '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Missing</span>';

            // Web Presence
            const web = data.web_presence || {};
            const webList = [];
            if (web.linkedin) webList.push('LinkedIn');
            if (web.portfolio) webList.push('Portfolio');
            document.getElementById('ats-web-presence').innerHTML = webList.length > 0 ? webList.join(', ') : '<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> Missing</span>';

            // Structure List
            const struct = data.section_structure || {};
            const structElem = document.getElementById('ats-section-structure');
            structElem.innerHTML = `
                <li class="list-group-item px-0 py-1 border-0 d-flex justify-content-between">Summary/Objective: <span class="${struct.summary ? 'text-success' : 'text-danger fw-bold'}">${struct.summary ? '<i class="bi bi-check2"></i> Present' : '<i class="bi bi-x"></i> Missing'}</span></li>
                <li class="list-group-item px-0 py-1 border-0 d-flex justify-content-between">Experience: <span class="${struct.experience ? 'text-success' : 'text-danger fw-bold'}">${struct.experience ? '<i class="bi bi-check2"></i> Present' : '<i class="bi bi-x"></i> Missing'}</span></li>
                <li class="list-group-item px-0 py-1 border-0 d-flex justify-content-between">Education: <span class="${struct.education ? 'text-success' : 'text-danger fw-bold'}">${struct.education ? '<i class="bi bi-check2"></i> Present' : '<i class="bi bi-x"></i> Missing'}</span></li>
                <li class="list-group-item px-0 py-1 border-0 d-flex justify-content-between">Projects: <span class="${struct.projects ? 'text-success' : 'text-warning'}">${struct.projects ? '<i class="bi bi-check2"></i> Present' : '<i class="bi bi-dash"></i> None Detected'}</span></li>
            `;

            // Experience Analysis
            const exp = data.experience_analysis || {};
            document.getElementById('ats-exp-years').innerText = parseFloat(exp.years_total || 0).toFixed(1);
            document.getElementById('ats-exp-roles').innerText = exp.relevant_roles || 0;
            document.getElementById('ats-exp-impact').innerText = exp.impact_bullets || 0;
            
            const gapsContainer = document.getElementById('ats-exp-gaps-container');
            if (exp.gaps_detected && exp.gaps_detected.length > 0) {
                gapsContainer.classList.remove('d-none');
                document.getElementById('ats-exp-gaps').innerText = exp.gaps_detected.join(' | ');
            } else {
                gapsContainer.classList.add('d-none');
            }

            // Hard Skills Table
            const hardElem = document.getElementById('ats-hard-skills-tbody');
            hardElem.innerHTML = '';
            if (data.hard_skills && data.hard_skills.length) {
                data.hard_skills.forEach(hs => {
                    const statusClass = hs.resume_score >= hs.required_score ? 'text-success' : 'text-danger fw-bold';
                    const icon = hs.resume_score >= hs.required_score ? '<i class="bi bi-check-circle-fill"></i>' : '<i class="bi bi-arrow-down-circle-fill"></i>';
                    hardElem.innerHTML += `
                        <tr>
                            <td class="fw-medium">${hs.skill}</td>
                            <td class="text-center">${hs.required_score}</td>
                            <td class="text-center fw-bold">${hs.resume_score}</td>
                            <td class="text-center ${statusClass}">${icon}</td>
                        </tr>
                    `;
                });
            } else {
                hardElem.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No specific hard skills analyzed.</td></tr>';
            }

            // Soft Skills Badges
            const softElem = document.getElementById('ats-soft-skills-container');
            softElem.innerHTML = '';
            if (data.soft_skills && data.soft_skills.length) {
                data.soft_skills.forEach(ss => {
                    if (ss.detected) {
                        softElem.innerHTML += `<span class="badge bg-info bg-opacity-25 text-info border border-info">${ss.skill}</span>`;
                    }
                });
            }
            if (softElem.innerHTML === '') softElem.innerHTML = '<span class="text-muted small">None explicitly detected.</span>';

            // Tone Warnings
            const toneElem = document.getElementById('ats-tone-warnings');
            toneElem.innerHTML = '';
            if (data.tone_analysis && data.tone_analysis.length) {
                data.tone_analysis.forEach(tone => {
                    toneElem.innerHTML += `<li class="mb-1"><i class="bi bi-x-circle text-danger me-1"></i>Found "<span class="fw-bold">${tone.cliche}</span>". Use "<span class="fw-bold text-success">${tone.suggestion}</span>" instead.</li>`;
                });
            }
            if (toneElem.innerHTML === '') toneElem.innerHTML = '<li class="text-success"><i class="bi bi-check-circle-fill me-1"></i>Tone is completely professional.</li>';

            // Fade out button as it's a one-time process for this state
            btn.style.display = 'none';
            updateWorkflowStage(4);
        } else {
            document.getElementById('readiness-loading').style.display = 'none';
            alert(data.error || 'Failed to calculate readiness score.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lock-fill me-2"></i>Lock Field & Score Readiness';
            document.getElementById('custom-career-field').disabled = false;
            document.getElementById('ai-career-field-dropdown').disabled = false;
        }
    } catch (error) {
        console.error(error);
        document.getElementById('readiness-loading').style.display = 'none';
        alert('A network error occurred while evaluating readiness.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lock-fill me-2"></i>Lock Field & Score Readiness';
        document.getElementById('custom-career-field').disabled = false;
        document.getElementById('ai-career-field-dropdown').disabled = false;
    }
}

async function fetchPredictedJobs() {
    if (!window.currentResumeId) return;

    const btn = document.getElementById('predict-jobs-btn');
    const resultsDiv = document.getElementById('jobs-results');
    const listDiv = document.getElementById('jobs-list');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Predicting Roles...';

    document.getElementById('predicting-loading').style.display = 'block';
    resultsDiv.style.display = 'none';

    try {
        const response = await fetch('/api/fields/analyze/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                resume_id: window.currentResumeId,
                preferred_field: appState.careerGoal || '' 
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('predicting-loading').style.display = 'none';
            resultsDiv.style.display = 'block';
            listDiv.innerHTML = '';

            // Update the Top Skills summary if needed (from the orchestrated response)
            if (data.skills && data.skills.length > 0) {
                console.log("Updated skills from Analysis:", data.skills);
            }

            // Save the titles globally for Stage 5 API
            window.predictedJobTitles = [];

            if (data.prediction) {
                const job = data.prediction;
                window.predictedJobTitles.push(job.job_title);
                let badgeColor = job.confidence >= 80 ? 'success' : (job.confidence >= 60 ? 'warning' : 'danger');
                
                listDiv.innerHTML = `
                    <div class="card border-0 shadow-sm border-start border-4 border-success">
                        <div class="card-body py-4 d-flex align-items-center justify-content-between">
                            <div class="pe-3 w-75 d-flex align-items-center">
                                <div class="form-check me-3">
                                    <input class="form-check-input role-checkbox" type="checkbox" value="${job.job_title}" checked>
                                </div>
                                <div>
                                    <div class="d-flex align-items-center mb-1">
                                        <h5 class="fw-bold text-dark mb-0">${job.job_title}</h5>
                                        <span class="ms-3 badge bg-secondary bg-opacity-10 text-secondary">${job.level}</span>
                                    </div>
                                    <p class="text-muted small mb-0 lh-base">${job.reason}</p>
                                </div>
                            </div>
                            <div class="text-end">
                                <div class="badge bg-${badgeColor} bg-opacity-10 text-${badgeColor} border border-${badgeColor}-subtle fs-5 rounded-pill px-3 py-2">
                                    <i class="bi bi-award-fill me-1"></i>${job.confidence}% Match
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-light border-0 small text-center text-muted mt-2">
                        <i class="bi bi-info-circle me-1"></i> This role has been strictly locked to your chosen career path and seniority profile.
                    </div>
                `;
            } else {
                listDiv.innerHTML = '<span class="text-muted small">Could not determine predicted roles.</span>';
            }
            btn.style.display = 'none';
        } else {
            document.getElementById('predicting-loading').style.display = 'none';
            alert(data.error || 'Failed to predict jobs.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-briefcase-fill me-2"></i>Predict Target Jobs';
        }
    } catch (error) {
        console.error(error);
        document.getElementById('predicting-loading').style.display = 'none';
        alert('A network error occurred while predicting jobs.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-briefcase-fill me-2"></i>Predict Target Jobs';
    }
}

async function fetchLiveJobs() {
    const checkboxes = document.querySelectorAll('.role-checkbox:checked');
    const selectedTitles = Array.from(checkboxes).map(cb => cb.value);

    if (selectedTitles.length === 0) {
        alert('Please select at least one target role from the list above!');
        return;
    }

    const location = document.getElementById('job-location').value || 'Remote';
    const tField = document.getElementById('job-target-field').value || '';
    
    // Append field to query to ensure accuracy as requested
    const refinedTitles = tField ? selectedTitles.map(t => `${t} ${tField}`) : selectedTitles;

    const btn = document.getElementById('search-live-jobs-btn');
    const resultsDiv = document.getElementById('live-jobs-results');
    const listDiv = document.getElementById('live-jobs-list');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Searching Google...';

    try {
        const response = await fetch('/api/search/search/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ titles: refinedTitles, location: location })
        });

        const data = await response.json();

        if (response.ok) {
            resultsDiv.style.display = 'block';
            listDiv.innerHTML = '';

            if (data.live_jobs && data.live_jobs.length > 0) {
                window.currentLiveJobs = data.live_jobs; // Store for ATS processing

                data.live_jobs.forEach(job => {
                    listDiv.innerHTML += `
                        <div class="col-md-6">
                            <div class="card h-100 border shadow-sm hover-elevate transition-all border-secondary border-opacity-25 bg-body">
                                <div class="card-body">
                                    <h6 class="fw-bold text-body-emphasis text-truncate mb-1" title="${job.title}">${job.title}</h6>
                                    <p class="text-primary small fw-medium mb-2"><i class="bi bi-building me-1"></i>${job.company} <span class="text-muted ms-2"><i class="bi bi-geo-alt me-1"></i>${job.location}</span></p>
                                    <p class="text-muted small line-clamp-3 mb-3" style="display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${job.description}</p>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                listDiv.innerHTML = '<div class="col-12"><div class="alert alert-warning border-warning-subtle text-body-emphasis">No live jobs found for those titles in ' + location + '. Try a different location!</div></div>';
            }

            // Switch out button state
            btn.style.display = 'none';
            updateWorkflowStage(7);
        } else {
            alert(data.error || 'Failed to fetch live jobs.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-google me-2"></i>Search Google Jobs';
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred while fetching live jobs.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-google me-2"></i>Search Google Jobs';
    }
}

async function fetchAdvancedJobMatches() {
    if (!window.currentLiveJobs || window.currentLiveJobs.length === 0) {
        alert('No live jobs available to rank.');
        return;
    }

    const btn = document.getElementById('run-advanced-matcher-btn');
    const loadingDiv = document.getElementById('matcher-loading');
    const resultsDiv = document.getElementById('matcher-results');
    const listDiv = document.getElementById('matcher-jobs-list');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Ranking ' + window.currentLiveJobs.length + ' Jobs...';

    loadingDiv.style.display = 'block';
    resultsDiv.style.display = 'none';
    listDiv.innerHTML = '';

    try {
        const response = await fetch('/api/matcher/score/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resume_id: window.currentResumeId,
                jobs: window.currentLiveJobs
            })
        });

        const data = await response.json();

        if (response.ok) {
            loadingDiv.style.display = 'none';
            resultsDiv.style.display = 'block';

            if (data.matched_jobs && data.matched_jobs.length > 0) {
                // Pass the ranked top jobs perfectly to ATS stage
                window.rankedJobs = data.matched_jobs.slice(0, 5); 

                data.matched_jobs.forEach(job => {
                    let atsText = job.final_match_score >= 80 ? 'âœ… Strong Match' : 'âš  Partial Match';
                    let atsColor = job.final_match_score >= 80 ? 'success' : (job.final_match_score >= 60 ? 'warning text-dark' : 'danger');
                    let missingHtml = job.final_match_score < 80 ? '<p class="small text-danger mb-2">âŒ <strong>Missing / Weak:</strong> Requires deeper industry terminology and keyword density.</p>' : '';
                    let btnHtml = job.final_match_score >= 80 ? 
                        `<a href="${job.url}" target="_blank" class="btn btn-sm btn-success fw-bold px-3"><i class="bi bi-box-arrow-up-right me-1"></i>Apply Now</a>` : 
                        `<button class="btn btn-sm btn-outline-danger fw-bold px-3" onclick="document.getElementById('skill-gap-results').style.display='block'; updateWorkflowStage(8); document.getElementById('gap-target-role').innerText='${job.title} at ${job.company}';"><i class="bi bi-zoom-in me-1"></i>Analyze Skill Gap</button>`;

                    listDiv.innerHTML += `
                        <div class="card border border-secondary shadow-sm bg-white hover-elevate transition-all">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="fw-bold text-body-emphasis mb-1">${job.title}</h6>
                                        <p class="small mb-0 text-muted"><i class="bi bi-building me-1"></i>${job.company} <span class="mx-2">|</span> <i class="bi bi-geo-alt me-1"></i>${job.location}</p>
                                    </div>
                                    <div class="text-end">
                                        <span class="badge bg-success bg-opacity-10 text-success border border-success-subtle mb-1"><i class="bi bi-check-circle-fill me-1"></i>VALIDATED</span>
                                        <h5 class="fw-bold text-${atsColor} mb-0 mt-1">${job.final_match_score}%</h5>
                                        <span class="small text-muted" style="font-size:10px;">ATS MATCH</span>
                                    </div>
                                </div>
                                <hr class="my-2 opacity-10">
                                <div class="mb-3">
                                    <p class="small fw-bold text-${atsColor} mb-1">${atsText}</p>
                                    ${missingHtml}
                                    <p class="small text-muted fst-italic mb-0" style="line-height:1.4;">"${job.reasoning}"</p>
                                </div>
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="small text-muted"><i class="bi bi-robot text-primary me-1"></i>AI Score Breakdown ðŸ‘‡</span>
                                    ${btnHtml}
                                </div>
                                <div class="row g-2 mt-2 border-top pt-2">
                                    <div class="col-4 col-md-2"><div class="p-1 rounded bg-body-tertiary text-center"><span class="d-block text-muted" style="font-size:9px;">ELIGIBILITY</span><strong class="text-primary small">${job.breakdown ? job.breakdown.eligibility : 0}%</strong></div></div>
                                    <div class="col-4 col-md-2"><div class="p-1 rounded bg-body-tertiary text-center"><span class="d-block text-muted" style="font-size:9px;">SKILLS</span><strong class="text-success small">${job.breakdown ? job.breakdown.proficiency : 0}%</strong></div></div>
                                    <div class="col-4 col-md-2"><div class="p-1 rounded bg-body-tertiary text-center"><span class="d-block text-muted" style="font-size:9px;">INDUSTRY</span><strong class="text-info small">${job.breakdown ? job.breakdown.industry : 0}%</strong></div></div>
                                    <div class="col-6 col-md-3"><div class="p-1 rounded bg-body-tertiary text-center"><span class="d-block text-muted" style="font-size:9px;">LOCATION</span><strong class="text-warning text-dark small">${job.breakdown ? job.breakdown.location : 0}%</strong></div></div>
                                    <div class="col-6 col-md-3"><div class="p-1 rounded bg-body-tertiary text-center"><span class="d-block text-muted" style="font-size:9px;">SALARY</span><strong class="text-danger small">${job.breakdown ? job.breakdown.salary : 0}%</strong></div></div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                listDiv.innerHTML = '<div class="alert alert-warning">No jobs successfully ranked.</div>';
            }
            btn.style.display = 'none';
        } else {
            loadingDiv.style.display = 'none';
            alert(data.error || 'Failed to process job matcher scores.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-funnel-fill me-2"></i>Rank Jobs with Advanced Matcher';
        }
    } catch (error) {
        console.error(error);
        loadingDiv.style.display = 'none';
        alert('A network error occurred running the Advanced Job Matcher.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-funnel-fill me-2"></i>Rank Jobs with Advanced Matcher';
    }
}

async function generateCustomJob() {
    const tField = document.getElementById('job-target-field').value || '';
    if (!tField) {
        alert("Please enter a Target Field (e.g. 'Software Engineering') before generating a custom JD.");
        return;
    }
    const btn = document.getElementById('generate-custom-job-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating JD & Matching...';
    
    try {
        const token = localStorage.getItem('access');
        const response = await fetch('/api/ats/generate-target/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId, target_field: tField })
        });
        const data = await response.json();
        if (response.ok) {
            document.getElementById('live-jobs-results').style.display = 'none';
            document.getElementById('ats-loading').style.display = 'none';
            renderATSResults(data);
        } else {
            alert(data.error || "Failed to generate custom JD.");
        }
    } catch (e) {
        alert("Network error.");
    }
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-magic me-2"></i>Generate Custom JD Match';
}

async function fetchATSScores() {
    if (!window.rankedJobs || window.rankedJobs.length === 0) {
        alert('No ranked jobs available to analyze.');
        return;
    }

    const btn = document.getElementById('run-ats-btn');
    const resultsDiv = document.getElementById('ats-results');
    const listDiv = document.getElementById('ats-jobs-list');
    const token = localStorage.getItem('access');
    const statsDiv = document.getElementById('ats-loading-stats');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning ' + window.rankedJobs.length + ' Jobs via ATS...';

    const loadingDiv = document.getElementById('ats-loading');
    loadingDiv.style.display = 'block';
    resultsDiv.style.display = 'none';
    statsDiv.innerHTML = `Cross-referencing your profile against ${window.rankedJobs.length} live listings. This takes time...`;
    listDiv.innerHTML = '';

    try {
        const response = await fetch('/api/ats/match/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resume_id: window.currentResumeId,
                jobs: window.rankedJobs
            })
        });

        const data = await response.json();

        if (response.ok) {
            loadingDiv.style.display = 'none';
            renderATSResults(data);
            btn.style.display = 'none';
            appState.jobSearchUnlocked = true;
            updateWorkflowStage(6);
        } else {
            loadingDiv.style.display = 'none';
            alert(data.error || 'Failed to process ATS scores.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-cpu-fill me-2"></i>Run ATS Match (Core AI)';
        }
    } catch (error) {
        console.error(error);
        loadingDiv.style.display = 'none';
        alert('A network error occurred running the ATS engine.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-cpu-fill me-2"></i>Run ATS Match (Core AI)';
    }
}

function renderATSResults(data) {
    const listDiv = document.getElementById('ats-jobs-list');
    const statsDiv = document.getElementById('ats-final-stats');
    const resultsDiv = document.getElementById('ats-results');
    
    resultsDiv.style.display = 'block';
    listDiv.innerHTML = '';
    
    statsDiv.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>Processed: ${data.total_passed}/${data.total_processed} matched successfully`;

    if (data.matched_jobs && data.matched_jobs.length > 0) {
        appState.atsResults = data.matched_jobs;
        window.atsJobs = data.matched_jobs;
        
        window.atsJobs.forEach((job, index) => {
            // Pill generation for details
            let matchedHtml = '<span class="text-muted small">None</span>';
            if (job.details && job.details.matched_skills && job.details.matched_skills.length > 0) {
                matchedHtml = job.details.matched_skills.map(s => `<span class="badge border border-success text-success bg-transparent rounded-pill small me-1 mb-1">${s}</span>`).join('');
            }
            
            let missingHtml = '<span class="text-success small fw-medium">No critical keywords missing!</span>';
            if (job.details && job.details.missing_skills && job.details.missing_skills.length > 0) {
                missingHtml = job.details.missing_skills.map(s => `<span class="badge border border-danger text-danger bg-transparent rounded-pill small me-1 mb-1">${s}</span>`).join('');
            }
            
            let weakHtml = '';
            if (job.details && job.details.weak_skills && job.details.weak_skills.length > 0) {
                weakHtml = job.details.weak_skills.map(ws => `
                    <div class="mb-2">
                        <span class="badge border border-warning text-warning bg-transparent rounded-pill small me-1 mb-1">${ws.skill}</span>
                        <p class="small text-muted mb-0 ps-2" style="font-size: 0.8rem; border-left: 2px solid #ffc107;">${ws.reason}</p>
                    </div>
                `).join('');
            }

            // Searchability flags
            let searchabilityHtml = '';
            if (job.searchability) {
                let titleMatchIcon = job.searchability.job_title_match ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger';
                let summMatchIcon = job.searchability.summary_present ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger';
                searchabilityHtml = `
                    <div class="mb-3 border-start border-3 ps-3 ${job.searchability.job_title_match ? 'border-success' : 'border-danger'}">
                        <h6 class="fw-bold mb-1 small text-dark"><i class="bi ${titleMatchIcon} me-2"></i>Job Title Match</h6>
                    </div>
                    <div class="mb-3 border-start border-3 ps-3 ${job.searchability.summary_present ? 'border-success' : 'border-danger'}">
                        <h6 class="fw-bold mb-1 small text-dark"><i class="bi ${summMatchIcon} me-2"></i>Summary Present</h6>
                    </div>
                `;
            }

            // Recruiter Tips list
            let recTipsHtml = '';
            if (job.recruiter_tips && job.recruiter_tips.length > 0) {
                recTipsHtml = job.recruiter_tips.map(tip => `
                    <div class="mb-2 text-muted small"><i class="bi bi-arrow-right-short text-primary"></i> ${tip}</div>
                `).join('');
            } else {
                recTipsHtml = '<span class="text-muted small">No specific tips at this time.</span>';
            }

            listDiv.innerHTML += `
                <div class="card border border-secondary shadow bg-body-tertiary border-opacity-50 mb-4">
                    <div class="card-header bg-secondary bg-opacity-10 border-bottom border-secondary py-3 d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="fw-bold text-body-emphasis mb-1">${job.company}</h6>
                            <p class="text-muted small mb-0"><i class="bi bi-geo-alt me-1"></i>${job.location} | ${job.title}</p>
                        </div>
                        <div class="text-end">
                            <h4 class="fw-bold text-success mb-0">${job.overall_score}%</h4>
                            <span class="badge bg-success bg-opacity-25 text-success">ATS Match</span>
                        </div>
                    </div>
                    
                    <div class="card-body bg-white py-4 px-4">
                        <div class="row g-4 border-bottom border-secondary border-opacity-25 pb-4 mb-4">
                            <!-- Breakdowns -->
                            <div class="col-md-5 border-end">
                                <h6 class="fw-bold mb-3 small text-secondary text-uppercase"><i class="bi bi-bar-chart-line me-2"></i>Formula Breakdown</h6>
                                
                                <div class="d-flex align-items-center mb-3">
                                    <div class="fw-bold small text-body-emphasis" style="width: 140px;">
                                        <i class="bi bi-tools text-success me-2"></i>Skills (${job.score_breakdown.skills_score}/40)
                                    </div>
                                    <div class="progress bg-secondary bg-opacity-25 flex-grow-1" style="height: 15px;">
                                        <div class="progress-bar bg-success" role="progressbar" style="width: ${(job.score_breakdown.skills_score / 40) * 100}%"></div>
                                    </div>
                                </div>
                                <div class="d-flex align-items-center mb-3">
                                    <div class="fw-bold small text-body-emphasis" style="width: 140px;">
                                        <i class="bi bi-briefcase text-primary me-2"></i>Experience (${job.score_breakdown.experience_score}/30)
                                    </div>
                                    <div class="progress bg-secondary bg-opacity-25 flex-grow-1" style="height: 15px;">
                                        <div class="progress-bar bg-primary" role="progressbar" style="width: ${(job.score_breakdown.experience_score / 30) * 100}%"></div>
                                    </div>
                                </div>
                                <div class="d-flex align-items-center mb-4">
                                    <div class="fw-bold small text-body-emphasis" style="width: 140px;">
                                        <i class="bi bi-mortarboard text-info me-2"></i>Education (${job.score_breakdown.education_score}/30)
                                    </div>
                                    <div class="progress bg-secondary bg-opacity-25 flex-grow-1" style="height: 15px;">
                                        <div class="progress-bar bg-info" role="progressbar" style="width: ${(job.score_breakdown.education_score / 30) * 100}%"></div>
                                    </div>
                                </div>
                                
                                <h6 class="fw-bold mb-3 mt-4 small text-secondary text-uppercase"><i class="bi bi-search me-2"></i>Searchability</h6>
                                ${searchabilityHtml}
                            </div>
                            
                            <!-- Deep Details -->
                            <div class="col-md-7">
                                <h6 class="text-body-emphasis small fw-bold mb-2"><i class="bi bi-check-circle me-1 text-success"></i>Matched Skills:</h6>
                                <div class="mb-3">${matchedHtml}</div>
                                
                                <h6 class="text-danger small fw-bold mb-2"><i class="bi bi-exclamation-circle me-1"></i>Missing Critical Skills:</h6>
                                <div class="mb-3">${missingHtml}</div>
                                
                                ${weakHtml ? `<h6 class="text-warning small fw-bold mb-2 mt-4"><i class="bi bi-exclamation-triangle me-1"></i>Weak Skills Identified:</h6><div class="mb-3">${weakHtml}</div>` : ''}
                                
                                <h6 class="text-primary small fw-bold mb-2 mt-4"><i class="bi bi-lightbulb me-1"></i>Recruiter Guidance:</h6>
                                <div class="p-3 bg-light rounded border">
                                    ${recTipsHtml}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card-footer bg-secondary bg-opacity-10 border-top border-secondary p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <button class="btn btn-primary fw-bold px-4 btn-sm" onclick="handleOptimizeCV(${index})" id="optimize-btn-${index}">
                                <i class="bi bi-magic me-2"></i>AI Optimize Resume
                            </button>
                            <a href="${job.url}" target="_blank" class="btn btn-success fw-bold px-4 hover-elevate btn-sm">Apply on Official Site <i class="bi bi-box-arrow-up-right ms-2"></i></a>
                        </div>
                        <div id="optimize-results-${index}" class="mt-3 bg-body border border-primary border-opacity-25 rounded-3 p-3 shadow-sm d-none">
                        </div>
                    </div>
                </div>
            `;
        });
        
        if (typeof updateWorkflowStage === 'function') {
           // updateWorkflowStage(8); 
        }
    } else {
        listDiv.innerHTML = '<div class="alert alert-warning">No jobs successfully processed via ATS. Ensure candidate data is accurate.</div>';
    }
}

function displayParsedData(data) {
    document.getElementById('upload-container').style.display = 'none';
    const subtitle = document.getElementById('upload-subtitle');
    if (subtitle) subtitle.style.display = 'none';
    document.getElementById('parsed-results').style.display = 'block';

    document.getElementById('parsed-name').value = data.name || '';
    document.getElementById('parsed-email').value = data.email || '';
    document.getElementById('parsed-phone').value = data.phone || '';
    document.getElementById('parsed-linkedin').value = data.linkedin || '';
    document.getElementById('parsed-portfolio').value = data.portfolio || '';

    if (data.skills && data.skills.length > 0) {
        document.getElementById('parsed-skills-input').value = data.skills.join(', ');
    } else {
        document.getElementById('parsed-skills-input').value = '';
    }

    let certsTools = [];
    if (data.certifications) certsTools.push(...data.certifications);
    if (data.tools) certsTools.push(...data.tools);
    document.getElementById('parsed-certs-input').value = certsTools.join(', ');

    if (data.experience && data.experience.length > 0) {
        let expText = data.experience.map(e => `${e.title} at ${e.company} (${e.duration})\n${e.description}`).join('\n\n');
        document.getElementById('parsed-experience-input').value = expText;
    } else {
        document.getElementById('parsed-experience-input').value = '';
    }

    if (data.education && data.education.length > 0) {
        let eduText = data.education.map(e => `${e.degree} from ${e.institution} (${e.year})`).join('\n\n');
        document.getElementById('parsed-education-input').value = eduText;
    } else {
        document.getElementById('parsed-education-input').value = '';
    }

    if (data.projects && data.projects.length > 0) {
        document.getElementById('parsed-projects-input').value = data.projects.join('\n');
    } else {
        document.getElementById('parsed-projects-input').value = '';
    }
}

async function confirmParsedData() {
    if (!window.currentResumeId) return;

    const nameVal = document.getElementById('parsed-name').value.trim();
    const emailVal = document.getElementById('parsed-email').value.trim();
    const skillsVal = document.getElementById('parsed-skills-input').value.trim();
    const expVal = document.getElementById('parsed-experience-input').value.trim();
    
    if (!nameVal || !emailVal || !skillsVal || !expVal) {
        alert('Please ensure your Name, Email, Skills, and Experience fields are filled before analyzing.');
        return;
    }

    const btn = document.getElementById('confirm-parsed-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving & Analyzing...';
    
    const updatedData = {
        name: document.getElementById('parsed-name').value,
        email: document.getElementById('parsed-email').value,
        phone: document.getElementById('parsed-phone').value,
        linkedin: document.getElementById('parsed-linkedin').value,
        portfolio: document.getElementById('parsed-portfolio').value,
        skills: document.getElementById('parsed-skills-input').value.split(',').map(s => s.trim()).filter(s => s),
        certifications: document.getElementById('parsed-certs-input').value.split(',').map(s => s.trim()).filter(s => s),
        experience_raw: document.getElementById('parsed-experience-input').value,
        education_raw: document.getElementById('parsed-education-input').value,
        projects_raw: document.getElementById('parsed-projects-input').value,
    };

    const token = localStorage.getItem('access');

    try {
        const response = await fetch(`/api/resume/update-parsed/${window.currentResumeId}/`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ parsed_data: updatedData })
        });

        if (response.ok) {
            const responseData = await response.json();
            
            // Phase 4: DAG Recomputation Hook
            if (responseData.pipeline_status === "RECOMPUTING") {
                console.warn("[DAG] Resume hash changed. Invalidating downstream UI caches.");
                appState.readinessScore = null;
                appState.predictedJobs = [];
                appState.atsResults = [];
                
                // Clear any leftover DOM texts
                if(document.getElementById('ats-results')) document.getElementById('ats-results').innerHTML = '';
                if(document.getElementById('live-jobs-list')) document.getElementById('live-jobs-list').innerHTML = '';
            }

            // Carefully hide ONLY the verify form and its immediate headers to not swallow nested subsequent sections.
            document.getElementById('verify-parsed-form').style.display = 'none';
            document.querySelector('#parsed-results h5').style.display = 'none';
            document.querySelector('#parsed-results p').style.display = 'none';
            
            // Show new section & set to loading state
            document.getElementById('field-results').style.display = 'block';
            document.getElementById('field-loading').style.display = 'block';
            document.getElementById('field-content').style.display = 'none';
            
            await fetchJobFamilies(btn);
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to save parsed data.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Confirm Data & Analyze Match';
        }
    } catch (error) {
        alert('A network error occurred while saving.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Confirm Data & Analyze Match';
    }
}

window.currentOptimizeIndex = null;

function handleOptimizeCV(index) {
    if (!window.atsJobs || !window.atsJobs[index]) return;
    
    document.getElementById('modal-review-skills').value = document.getElementById('parsed-skills-input').value;
    document.getElementById('modal-review-exp').value = document.getElementById('parsed-experience-input').value;
    window.currentOptimizeIndex = index;
    
    const cvModal = new bootstrap.Modal(document.getElementById('cvReviewModal'));
    cvModal.show();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('confirmOptimizationBtn')?.addEventListener('click', async function() {
        const idx = window.currentOptimizeIndex;
        if (idx === null) return;
        
        const modalEl = document.getElementById('cvReviewModal');
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.hide();
        
        await performOptimization(idx);
    });
});

async function performOptimization(index) {
    if (!window.atsJobs || !window.atsJobs[index]) return;
    const job = window.atsJobs[index];
    const btn = document.getElementById(`optimize-btn-${index}`);
    const resultsDiv = document.getElementById(`optimize-results-${index}`);
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running 3-Round Optimization Loop...';
    resultsDiv.classList.remove('d-none');
    resultsDiv.innerHTML = `
        <div class="text-center py-4 px-2 text-primary border border-primary border-opacity-25 bg-primary bg-opacity-10 rounded">
            <div class="spinner-border mb-3 border-3" style="width: 2.5rem; height: 2.5rem;" role="status"></div>
            <h6 class="fw-bold mb-1"><i class="bi bi-magic me-2"></i>AI Resume Optimization</h6>
            <p class="small text-muted mb-0">Our AI is iteratively rewriting your resume and re-measuring your ATS score.<br><strong>This intensive 3-round process takes up to 45 seconds.</strong></p>
        </div>
    `;

    try {
        const response = await fetch('/api/ats/optimize/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resume_id: window.currentResumeId,
                target_job: {
                    title: job.title,
                    description: job.description
                }
            })
        });

        const data = await response.json();

        if (response.ok) {
            const opt = data.optimization;
            
            let roundsHtml = '';
            opt.rounds.forEach(r => {
                let changesList = r.changes_made.map(c => `<li>${c}</li>`).join('');
                roundsHtml += `
                    <div class="d-flex mb-2">
                        <div class="badge bg-primary text-white rounded-circle me-2 d-flex align-items-center justify-content-center" style="width:24px;height:24px;">${r.round_number}</div>
                        <div>
                            <h6 class="mb-1 text-primary small fw-bold">${r.focus_area} <span class="badge bg-success bg-opacity-25 text-success ms-2">+${r.score_bump} points</span></h6>
                            <ul class="small text-muted mb-0 ps-3">${changesList}</ul>
                        </div>
                    </div>
                `;
            });
            
            let missingContactHtml = '';
            if (opt.missing_contact_info && opt.missing_contact_info.length > 0) {
                missingContactHtml = `<div class="alert alert-danger p-2 small mb-3"><i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Missing Info:</strong> Add ${opt.missing_contact_info.join(', ')} to your resume header!</div>`;
            }

            resultsDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-center border-bottom border-primary border-opacity-25 pb-2 mb-3">
                    <h6 class="fw-bold text-primary mb-0"><i class="bi bi-stars me-2"></i>Optimization Complete</h6>
                    <div class="small fw-bold border border-success rounded-pill px-2 py-1 bg-success bg-opacity-10 text-success">
                        Est. New ATS Score: ${opt.original_score_estimate} <i class="bi bi-arrow-right mx-1"></i> ${opt.final_score_estimate}/100
                    </div>
                </div>
                
                ${missingContactHtml}
                
                <div class="mb-3">
                    <span class="small fw-bold text-body-emphasis mb-1 d-block"><i class="bi bi-file-earmark-text me-1"></i>Optimized Professional Summary:</span>
                    <div class="bg-body-secondary p-2 rounded small text-body font-monospace">${opt.optimized_summary}</div>
                </div>
                
                <div>
                    <span class="small fw-bold text-body-emphasis mb-2 d-block"><i class="bi bi-arrow-repeat me-1"></i>3-Round Improvement Log:</span>
                    ${roundsHtml}
                </div>
            `;
            
            btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Optimized';
        }
    } catch (error) {
        console.error("Optimization Error:", error);
        alert("An error occurred during AI optimization.");
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-magic me-2"></i>AI Optimize Resume';
    }
}

function updateWorkflowStage(stage) {
    currentStage = stage;
    const progressBar = document.getElementById('workflow-progress-line');
    
    for(let i = 1; i <= 10; i++) {
        const circle = document.getElementById(`step-${i}-circle`);
        const text = document.getElementById(`step-${i}-text`);
        if(!circle) continue;

        if (i < stage) {
            circle.className = 'step-circle rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-white shadow-sm';
            circle.style.background = 'linear-gradient(to top right, #10b981, #059669)';
            circle.innerHTML = '<i class="bi bi-check-lg"></i>';
            text.className = 'small fw-bold mb-0 text-success';
        } else if (i === stage) {
            circle.className = 'step-circle rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-white shadow-sm active-step';
            circle.style.background = 'linear-gradient(to top right, #3b82f6, #8b5cf6)';
            circle.innerHTML = i === 10 && !appState.jobSearchUnlocked ? '<i class="bi bi-lock-fill"></i>' : i;
            text.className = 'small fw-bold mb-0 text-primary';
        } else {
            circle.className = 'step-circle rounded-circle d-flex align-items-center justify-content-center mx-auto mb-2 text-secondary bg-body-tertiary shadow-sm';
            circle.style.background = '';
            circle.innerHTML = i === 10 && !appState.jobSearchUnlocked ? '<i class="bi bi-lock-fill"></i>' : i;
            text.className = 'small fw-bold mb-0 text-secondary';
        }
    }

    const percentage = ((stage - 1) / 9) * 100;
    if(progressBar) progressBar.style.width = `${percentage}%`;

    updateNavigationArrows();
}

function updateNavigationArrows() {
    const prevBtn = document.getElementById('nav-prev-btn');
    const nextBtn = document.getElementById('nav-next-btn');

    if (prevBtn) prevBtn.parentElement.style.display = currentStage > 1 ? 'block' : 'none';
    if (nextBtn) {
        nextBtn.parentElement.style.display = currentStage < 10 ? 'block' : 'none';
        nextBtn.disabled = !completedStages.has(currentStage + 1) && !isStageLogicComplete(currentStage);
    }
}

function isStageLogicComplete(stage) {
    if (stage === 1) return !!window.currentResumeId;
    if (stage === 2) return true;
    if (stage === 3) return !!appState.careerGoal;
    if (stage === 5) return !!document.getElementById('editable-jd-container')?.value;
    if (stage === 6) return !!appState.atsResults;
    return true;
}

function handleStepClick(targetStage) {
    if (targetStage === 10 && !appState.jobSearchUnlocked) {
        alert("Job Search is locked! Complete the ATS Match (Step 6) to unlock.");
        return;
    }
    if (targetStage <= currentStage || completedStages.has(targetStage)) {
        goToStage(targetStage);
    } else {
        alert("Please complete the current steps sequentially first.");
    }
}

function goToNextStep() {
    if (currentStage < 10) {
        if (currentStage === 8) {
            $('#cvReviewModal').modal('show');
            return;
        }
        const next = currentStage + 1;
        if (next === 10 && !appState.jobSearchUnlocked) {
             alert("Job Search is locked! Complete the ATS Match (Step 6) to unlock.");
             return;
        }
        goToStage(next);
    }
}

function goToPreviousStep() {
    if (currentStage > 1) {
        goToStage(currentStage - 1);
    }
}

function goToStage(stageNum) {
    const containers = [
        'upload-container', 'parsed-results', 'field-results', 
        'predicted-jobs-results', 'jd-results', 'ats-results', 
        'skill-gap-results', 'optimizer-results', 'job-preferences-section',
        'live-jobs-results'
    ];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if(el) el.style.display = 'none';
    });

    document.getElementById('optimizer-coaching-section').style.display = 'none';

    if (stageNum === 1) document.getElementById('upload-container').style.display = 'block';
    else if (stageNum === 2) document.getElementById('parsed-results').style.display = 'block';
    else if (stageNum === 3) {
        document.getElementById('field-results').style.display = 'block';
        if (!appState.careerGoal) fetchJobFamilies();
    }
    else if (stageNum === 4) fetchPredictedJobs();
    else if (stageNum === 5) document.getElementById('jd-results').style.display = 'block';
    else if (stageNum === 6) document.getElementById('ats-results').style.display = 'block';
    else if (stageNum === 7) document.getElementById('skill-gap-results').style.display = 'block';
    else if (stageNum === 8) {
        document.getElementById('main-workflow-container').innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-pencil-square text-primary display-1 mb-4"></i>
                <h3>Final Data Review</h3>
                <p class="text-muted">You are one step away from Professional Optimization. Click the button below to review your extracted skills, projects, and experience.</p>
                <button class="btn btn-primary btn-lg fw-bold mt-3 px-5" data-bs-toggle="modal" data-bs-target="#cvReviewModal">
                    Open Review Editor <i class="bi bi-chevron-right ms-2"></i>
                </button>
            </div>
        `;
    }
    else if (stageNum === 9) document.getElementById('optimizer-results').style.display = 'block';
    else if (stageNum === 10) document.getElementById('job-preferences-section').style.display = 'block';

    completedStages.add(stageNum);
    updateWorkflowStage(stageNum);
}

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const btn = document.getElementById('upload-btn');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Analyzing...';
    
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
            appState.parsedData = data.parsed_state || data.parsed_data;
            goToStage(2);
            populateParsedUI(appState.parsedData);
        } else {
            alert(data.error || 'Upload failed');
        }
    } catch (error) {
        alert('Network error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Select Resume';
    }
}

function populateParsedUI(data) {
    if (!data) return;
    document.getElementById('parsed-name').value = data.name || '';
    document.getElementById('parsed-email').value = data.email || '';
    document.getElementById('parsed-phone').value = data.phone || '';
    document.getElementById('parsed-linkedin').value = data.linkedin || '';
    document.getElementById('parsed-portfolio').value = data.portfolio || '';
    document.getElementById('parsed-skills-input').value = Array.isArray(data.skills) ? data.skills.join(', ') : (data.skills || '');
    document.getElementById('parsed-certs-input').value = Array.isArray(data.tools) ? data.tools.join(', ') : (data.tools || '');
    document.getElementById('parsed-experience-input').value = data.experience || '';
    document.getElementById('parsed-education-input').value = data.education || '';
    document.getElementById('parsed-projects-input').value = data.projects || '';

    document.getElementById('edit-name').value = data.name || '';
    document.getElementById('edit-email').value = data.email || '';
    document.getElementById('edit-phone').value = data.phone || '';
    document.getElementById('edit-linkedin').value = data.linkedin || '';
    document.getElementById('edit-portfolio').value = data.portfolio || '';
    document.getElementById('edit-skills').value = Array.isArray(data.skills) ? data.skills.join(', ') : (data.skills || '');
    document.getElementById('edit-tools').value = Array.isArray(data.tools) ? data.tools.join(', ') : (data.tools || '');
    document.getElementById('edit-experience').value = data.experience || '';
    document.getElementById('edit-education').value = data.education || '';
    document.getElementById('edit-projects').value = data.projects || '';
}

async function fetchJobFamilies() {
    const dropdown = document.getElementById('ai-career-field-dropdown');
    document.getElementById('field-loading').style.display = 'block';
    document.getElementById('field-content').style.display = 'none';

    try {
        const response = await fetch('/api/fields/classify/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();
        if (response.ok) {
            document.getElementById('field-loading').style.display = 'none';
            document.getElementById('field-content').style.display = 'block';
            dropdown.innerHTML = '<option value="" disabled selected>-- Select an AI suggestion --</option>';
            data.job_families.forEach(f => {
                dropdown.innerHTML += `<option value="${f}">${f}</option>`;
            });
        }
    } catch (e) { console.error(e); }
}

async function lockFieldAndScoreReadiness() {
    const field = document.getElementById('custom-career-field').value || document.getElementById('ai-career-field-dropdown').value;
    if (!field) return alert("Select a career field");
    appState.careerGoal = field;
    goToStage(4);
}

async function fetchPredictedJobs() {
    const listDiv = document.getElementById('jobs-list');
    document.getElementById('predict-jobs-results').style.display = 'block';
    document.getElementById('predicting-loading').style.display = 'block';
    document.getElementById('jobs-results').style.display = 'none';

    try {
        const response = await fetch('/api/jobs/predict/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();
        if (response.ok) {
            document.getElementById('predicting-loading').style.display = 'none';
            document.getElementById('jobs-results').style.display = 'block';
            listDiv.innerHTML = '';
            data.jobs.forEach(job => {
                listDiv.innerHTML += `
                    <div class="card border border-secondary border-opacity-10 mb-2" onclick="window.currentSelectedJob = {title: '${job.title}'}; document.querySelectorAll('.job-card').forEach(c=>c.classList.remove('border-primary')); this.classList.add('border-primary');" style="cursor:pointer;">
                        <div class="card-body p-3 d-flex justify-content-between align-items-center">
                            <div><h6 class="fw-bold mb-0">${job.title}</h6><p class="small text-muted mb-0">${job.match_reason}</p></div>
                            <span class="badge bg-success bg-opacity-10 text-success">${job.confidence}%</span>
                        </div>
                    </div>
                `;
            });
        }
    } catch (e) {}
}

document.getElementById('confirmOptimizationBtn').addEventListener('click', async () => {
    appState.parsedData = {
        name: document.getElementById('edit-name').value,
        email: document.getElementById('edit-email').value,
        phone: document.getElementById('edit-phone').value,
        linkedin: document.getElementById('edit-linkedin').value,
        portfolio: document.getElementById('edit-portfolio').value,
        skills: document.getElementById('edit-skills').value,
        tools: document.getElementById('edit-tools').value,
        experience: document.getElementById('edit-experience').value,
        education: document.getElementById('edit-education').value,
        projects: document.getElementById('edit-projects').value
    };

    $('#cvReviewModal').modal('hide');
    runCVOptimizer();
});

async function runCVOptimizer() {
    document.getElementById('optimizer-loading').style.display = 'block';
    document.getElementById('optimizer-results').style.display = 'none';
    updateWorkflowStage(9);

    try {
        const response = await fetch("/api/optimizer/variants/", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem('access')}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ 
                resume_id: window.currentResumeId,
                edited_data: appState.parsedData
            })
        });

        const res = await response.json();
        document.getElementById('optimizer-loading').style.display = 'none';
        
        if (response.ok && res.status === "success") {
            const data = res.data;
            document.getElementById('optimizer-results').style.display = 'block';
            document.getElementById('optimizer-coaching-section').style.display = 'block';
            document.getElementById('cv-output-balanced').innerText = data.optimized_cv_text;
            document.getElementById('cv-output-aggressive').innerText = data.optimized_cv_text;
            document.getElementById('cv-output-concise').innerText = data.optimized_cv_text;
            document.getElementById('coach-missing-elements').innerHTML = data.missing_elements.map(e => `<li>${e}</li>`).join('');
            document.getElementById('coach-action-suggestions').innerHTML = data.user_action_suggestions.map(e => `<li>${e}</li>`).join('');
        } else {
            alert("Optimization failed");
        }
    } catch (e) {
        alert("Network Error");
    }
}

async function fetchLiveJobs() {
    const field = document.getElementById('job-target-field').value || appState.careerGoal;
    const location = document.getElementById('job-location').value;
    document.getElementById('live-jobs-results').style.display = 'block';
    const listDiv = document.getElementById('live-jobs-list');
    listDiv.innerHTML = '<div class="text-center w-100 py-5"><div class="spinner-border text-primary"></div><p class="mt-2 small">Fetching live listings...</p></div>';

    try {
        const response = await fetch('/api/search/search/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ titles: [field], location: location })
        });

        const data = await response.json();
        if (response.ok) {
            listDiv.innerHTML = '';
            data.live_jobs.forEach(job => {
                listDiv.innerHTML += `
                    <div class="col-md-6 mb-3">
                        <div class="card h-100 shadow-sm border-0">
                            <div class="card-body">
                                <h6 class="fw-bold mb-1">${job.title}</h6>
                                <p class="text-primary small mb-2">${job.company} | ${job.location}</p>
                                <p class="text-muted small">${job.description.substring(0, 100)}...</p>
                                <a href="${job.url}" target="_blank" class="btn btn-outline-primary btn-sm rounded-pill px-3">View Job</a>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
    } catch (e) {}
}

function confirmParsedData() { goToStage(3); }
window.confirmParsedData = confirmParsedData;
window.runCVOptimizer = runCVOptimizer;
window.handleStepClick = handleStepClick;
window.goToNextStep = goToNextStep;
window.goToPreviousStep = goToPreviousStep;