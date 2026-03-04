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

            // Populate fields
            document.getElementById('user-email').innerText = data.email;

            const roleBadge = document.getElementById('user-role');
            if (data.role === 'job_seeker') {
                roleBadge.innerText = 'Job Seeker';
                roleBadge.className = 'badge bg-primary bg-opacity-10 text-primary border border-primary-subtle ms-1 fw-medium';
                document.getElementById('job-seeker-view').style.display = 'block';
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
        if (document.getElementById('loading')) document.getElementById('loading').innerHTML = '<div class="alert alert-danger mx-auto" style="max-width:400px;">Network error. Please try again.</div>';
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
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<span class="text-primary">Uploading and analyzing <strong>${file.name}</strong>...</span>`;

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
            displayParsedData(data.parsed_state);

            // Expose resume ID globally for next stage
            window.currentResumeId = data.resume_id;
            document.getElementById('analyze-fields-btn').style.display = 'inline-block';
            document.getElementById('field-results').style.display = 'none';

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

async function fetchJobFamilies() {
    if (!window.currentResumeId) return;

    const btn = document.getElementById('analyze-fields-btn');
    const resultsDiv = document.getElementById('field-results');
    const listDiv = document.getElementById('job-families-list');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Calculating Matches...';

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
            resultsDiv.style.display = 'block';
            listDiv.innerHTML = '';

            if (data.job_families && data.job_families.length > 0) {
                data.job_families.forEach(family => {
                    listDiv.innerHTML += `
                        <div class="px-3 py-2 border rounded-pill bg-warning bg-opacity-10 text-body-secondary fw-medium border-warning shadow-sm">
                            <i class="bi bi-briefcase me-2 text-warning"></i>${family}
                        </div>
                    `;
                });
            } else {
                listDiv.innerHTML = '<span class="text-muted small">Could not determine job families.</span>';
            }
        } else {
            alert(data.error || 'Failed to classify job fields.');
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred while classifying fields.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-magic me-2"></i>Analyze Career Match';
    }
}

async function fetchReadinessScore() {
    if (!window.currentResumeId) return;

    const btn = document.getElementById('analyze-readiness-btn');
    const resultsDiv = document.getElementById('readiness-results');
    const token = localStorage.getItem('access');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Evaluating...';

    try {
        const response = await fetch('/api/readiness/score/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();

        if (response.ok) {
            resultsDiv.style.display = 'block';
            document.getElementById('readiness-score-val').innerText = data.score;

            // Update Breakdown Data
            if (data.breakdown) {
                document.getElementById('score-skills').innerText = data.breakdown.skills;
                document.getElementById('progress-skills').style.width = `${(data.breakdown.skills / 40) * 100}%`;

                document.getElementById('score-tools').innerText = data.breakdown.tools;
                document.getElementById('progress-tools').style.width = `${(data.breakdown.tools / 30) * 100}%`;

                document.getElementById('score-certs').innerText = data.breakdown.certifications;
                document.getElementById('progress-certs').style.width = `${(data.breakdown.certifications / 20) * 100}%`;

                document.getElementById('score-projects').innerText = data.breakdown.projects;
                document.getElementById('progress-projects').style.width = `${(data.breakdown.projects / 10) * 100}%`;
            }

            document.getElementById('readiness-weakest').innerText = data.weakest_area || 'None';
            document.getElementById('readiness-reason').innerText = data.ai_feedback || data.reason || '';

            const listElem = document.getElementById('readiness-suggestions');
            listElem.innerHTML = '';
            if (data.suggestions && data.suggestions.length) {
                data.suggestions.forEach(s => {
                    listElem.innerHTML += `<li>${s}</li>`;
                });
            }

            // Fade out button as it's a one-time process for this state
            btn.style.display = 'none';
        } else {
            alert(data.error || 'Failed to calculate readiness score.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-bar-chart-line-fill me-2"></i>Calculate Readiness Score';
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred while evaluating readiness.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-bar-chart-line-fill me-2"></i>Calculate Readiness Score';
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

    try {
        const response = await fetch('/api/jobs/predict/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume_id: window.currentResumeId })
        });

        const data = await response.json();

        if (response.ok) {
            resultsDiv.style.display = 'block';
            listDiv.innerHTML = '';

            // Save the titles globally for Stage 5 API
            window.predictedJobTitles = [];

            if (data.jobs && data.jobs.length > 0) {
                data.jobs.forEach(job => {
                    window.predictedJobTitles.push(job.title);
                    let badgeColor = job.confidence >= 80 ? 'success' : (job.confidence >= 60 ? 'warning' : 'danger');
                    listDiv.innerHTML += `
                        <div class="card border-0 shadow-sm">
                            <div class="card-body py-3 d-flex align-items-center justify-content-between">
                                <div class="pe-3 w-75">
                                    <h6 class="fw-bold text-body-emphasis mb-1">${job.title}</h6>
                                    <p class="text-muted small mb-0 lh-sm">${job.match_reason}</p>
                                </div>
                                <div class="text-end">
                                    <div class="badge bg-${badgeColor} bg-opacity-10 text-${badgeColor} border border-${badgeColor}-subtle fs-6 rounded-pill px-3 py-2">
                                        <i class="bi bi-award-fill me-1"></i>${job.confidence}% Match
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                listDiv.innerHTML = '<span class="text-muted small">Could not determine predicted roles.</span>';
            }
            btn.style.display = 'none';
        } else {
            alert(data.error || 'Failed to predict jobs.');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-briefcase-fill me-2"></i>Predict Target Jobs';
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred while predicting jobs.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-briefcase-fill me-2"></i>Predict Target Jobs';
    }
}

async function fetchLiveJobs() {
    if (!window.predictedJobTitles || window.predictedJobTitles.length === 0) {
        alert('Please predict target jobs first!');
        return;
    }

    const location = document.getElementById('job-location').value || 'Remote';
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
            body: JSON.stringify({ titles: window.predictedJobTitles, location: location })
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

async function fetchATSScores() {
    if (!window.currentLiveJobs || window.currentLiveJobs.length === 0) {
        alert('No live jobs available to analyze.');
        return;
    }

    const btn = document.getElementById('run-ats-btn');
    const resultsDiv = document.getElementById('ats-results');
    const listDiv = document.getElementById('ats-jobs-list');
    const token = localStorage.getItem('access');
    const statsDiv = document.getElementById('ats-loading-stats');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning ' + window.currentLiveJobs.length + ' Jobs via ATS...';

    resultsDiv.style.display = 'block';
    statsDiv.style.display = 'block';
    statsDiv.innerHTML = `<i class="bi bi-arrow-repeat spin me-2"></i>Cross-referencing your profile against ${window.currentLiveJobs.length} live listings...`;
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
                jobs: window.currentLiveJobs
            })
        });

        const data = await response.json();

        if (response.ok) {
            statsDiv.innerHTML = `<i class="bi bi-check-circle-fill text-success me-2"></i>ATS Filtered: ${data.total_passed} passed >70% out of ${data.total_processed} scanned. Showing top 3.`;

            if (data.matched_jobs && data.matched_jobs.length > 0) {
                data.matched_jobs.forEach(job => {
                    let missingPills = job.missing_keywords.length > 0
                        ? job.missing_keywords.map(k => `<span class="badge border border-danger text-danger bg-transparent rounded-pill small me-1 mb-1">${k}</span>`).join('')
                        : '<span class="text-success small fw-medium">No critical keywords missing!</span>';

                    listDiv.innerHTML += `
                        <div class="card border border-secondary shadow bg-body-tertiary border-opacity-50">
                            <div class="card-header border-bottom border-secondary d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="fw-bold text-body-emphasis mb-0">${job.title} <span class="text-muted fw-normal ms-2">at ${job.company}</span></h6>
                                </div>
                                <h4 class="fw-bold text-success mb-0">${job.ats_score}<span class="fs-6 text-muted">/100</span></h4>
                            </div>
                            <div class="card-body">
                                <div class="row g-4">
                                    <div class="col-md-7 border-end border-secondary">
                                        <p class="small text-body mb-3"><i class="bi bi-robot me-1 text-info"></i> ${job.matching_reason}</p>
                                        
                                        <div class="mb-3">
                                            <h6 class="text-body-emphasis small fw-bold mb-2">Detailed Breakdown:</h6>
                                            <div class="progress bg-secondary bg-opacity-25 mb-2" style="height: 15px;">
                                                <div class="progress-bar bg-success" role="progressbar" style="width: ${(job.breakdown.skills_score / 40) * 100}%">Skills ${job.breakdown.skills_score}/40</div>
                                            </div>
                                            <div class="progress bg-secondary bg-opacity-25 mb-2" style="height: 15px;">
                                                <div class="progress-bar bg-info" role="progressbar" style="width: ${(job.breakdown.experience_score / 30) * 100}%">Experience ${job.breakdown.experience_score}/30</div>
                                            </div>
                                            <div class="progress bg-secondary bg-opacity-25" style="height: 15px;">
                                                <div class="progress-bar bg-warning" role="progressbar" style="width: ${(job.breakdown.education_score / 30) * 100}%">Education ${job.breakdown.education_score}/30</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-5">
                                        <h6 class="text-danger small fw-bold mb-2"><i class="bi bi-exclamation-circle me-1"></i>Missing Keywords:</h6>
                                        <div class="mb-3">${missingPills}</div>
                                        
                                        <h6 class="text-warning small fw-bold mb-1"><i class="bi bi-lightbulb me-1"></i>Improvement Tip:</h6>
                                        <p class="small text-body-secondary mb-0">${job.improvement_suggestion}</p>
                                    </div>
                                </div>
                            </div>
                            <div class="card-footer bg-secondary bg-opacity-10 border-top border-secondary text-end p-3">
                                <a href="${job.url}" target="_blank" class="btn btn-success fw-bold px-4 hover-elevate">Apply on Official Site <i class="bi bi-box-arrow-up-right ms-2"></i></a>
                            </div>
                        </div>
                    `;
                });
            } else {
                listDiv.innerHTML = `
                    <div class="alert alert-danger border-danger-subtle bg-danger bg-opacity-10 d-flex align-items-center">
                        <i class="bi bi-emoji-frown fs-3 text-danger me-3"></i>
                        <div>
                            <h6 class="fw-bold text-danger mb-1">No strong matches found.</h6>
                            <p class="mb-0 small text-danger text-opacity-75">None of the fetched jobs scored higher than our strict 70/100 ATS threshold. Your profile might need more relevant keywords. Update your resume and try generating new Target Jobs, or search in a different location.</p>
                        </div>
                    </div>`;
            }
            btn.style.display = 'none';
        } else {
            alert(data.error || 'Failed to process ATS scores.');
            statsDiv.style.display = 'none';
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-cpu-fill me-2"></i>Run ATS Match (Core AI)';
        }
    } catch (error) {
        console.error(error);
        alert('A network error occurred running the ATS engine.');
        statsDiv.style.display = 'none';
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-cpu-fill me-2"></i>Run ATS Match (Core AI)';
    }
}

function displayParsedData(data) {
    document.getElementById('parsed-results').style.display = 'block';

    // Skills
    const skillsContainer = document.getElementById('parsed-skills');
    skillsContainer.innerHTML = '';
    if (data.skills && data.skills.length > 0) {
        data.skills.forEach(skill => {
            skillsContainer.innerHTML += `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle">${skill}</span>`;
        });
    } else {
        skillsContainer.innerHTML = '<span class="text-muted small">No skills found.</span>';
    }

    // Tools
    const toolsContainer = document.getElementById('parsed-tools');
    toolsContainer.innerHTML = '';
    if (data.tools && data.tools.length > 0) {
        data.tools.forEach(tool => {
            toolsContainer.innerHTML += `<span class="badge bg-success bg-opacity-10 text-success border border-success-subtle">${tool}</span>`;
        });
    } else {
        toolsContainer.innerHTML = '<span class="text-muted small">No tools found.</span>';
    }

    // Experience
    const expContainer = document.getElementById('parsed-experience');
    expContainer.innerHTML = '';
    if (data.experience && data.experience.length > 0) {
        data.experience.forEach(exp => {
            expContainer.innerHTML += `
                <div class="mb-3 pb-2 border-bottom">
                    <div class="fw-bold">${exp.title} <span class="text-muted fw-normal">at ${exp.company}</span></div>
                    <div class="small text-muted mb-1"><i class="bi bi-calendar3 me-1"></i>${exp.duration}</div>
                    <p class="small mb-0">${exp.description}</p>
                </div>
            `;
        });
    } else {
        expContainer.innerHTML = '<span class="text-muted small">No experience found.</span>';
    }
}
