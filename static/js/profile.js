document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    // Load both auth profile and custom user profile
    await fetchUserProfile();
    await fetchUserProfileAndHistory();
});

async function fetchUserProfile() {
    const token = localStorage.getItem('access');
    try {
        const response = await fetch('/api/auth/profile/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('profile-email').value = data.email;
            document.getElementById('profile-email-display').innerText = data.email;
            document.getElementById('profile-role').innerText = data.role === 'job_seeker' ? 'Job Seeker' : 'HR / Recruiter';
            document.getElementById('profile-avatar-letter').innerText = data.email.charAt(0).toUpperCase();
        }
    } catch (error) {
        console.error("Error fetching user details:", error);
    }
}

async function fetchUserProfileAndHistory() {
    const token = localStorage.getItem('access');
    const jobsListDiv = document.getElementById('saved-jobs-list');

    try {
        const response = await fetch('/api/profile/jobs/history/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();

            document.getElementById('jobs-saved-count').innerText = data.saved_jobs ? data.saved_jobs.length : 0;

            // Render jobs history
            jobsListDiv.innerHTML = '';
            if (data.saved_jobs && data.saved_jobs.length > 0) {
                data.saved_jobs.forEach(job => {
                    jobsListDiv.innerHTML += `
                        <div class="card border border-success shadow-sm bg-body border-opacity-50 hover-elevate">
                            <div class="card-header bg-success bg-opacity-10 border-bottom border-success d-flex justify-content-between align-items-center py-2">
                                <h6 class="fw-bold text-body-emphasis mb-0 fs-6 text-truncate" style="max-width:70%;">${job.job_title} <span class="text-muted fw-normal ms-1 fs-6">at ${job.company}</span></h6>
                                <div class="badge bg-success text-white px-3 py-2 rounded-pill shadow-sm">${job.ats_score}% Match</div>
                            </div>
                            <div class="card-body py-2 px-3 pb-3">
                                <div class="mt-2 text-muted small lh-sm line-clamp-2" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"><i class="bi bi-geo-alt text-primary me-1"></i>${job.location || 'Remote'} - ${job.description}</div>
                                <div class="mt-3 py-2 border-top border-opacity-50 small text-body">
                                    <strong><i class="bi bi-robot text-info me-1"></i> AI Feedback:</strong> 
                                    ${job.matching_reason}
                                </div>
                                ${job.improvement_suggestion ? `
                                    <div class="mt-2 fst-italic text-warning small">
                                        <i class="bi bi-lightbulb-fill"></i> ${job.improvement_suggestion}
                                    </div>
                                ` : ''}
                                <div class="mt-3 text-end">
                                    <a href="${job.job_url}" target="_blank" class="btn btn-sm btn-outline-success fw-bold px-4 rounded-pill">Apply Again <i class="bi bi-box-arrow-up-right ms-1"></i></a>
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                jobsListDiv.innerHTML = `
                    <div class="alert alert-secondary bg-body-tertiary border-0 text-center py-4">
                        <i class="bi bi-inbox fs-2 text-muted mb-2 d-block"></i>
                        <h6 class="fw-bold text-body-emphasis">No jobs saved yet</h6>
                        <p class="small text-muted mb-0">Your ATS auto-saves will appear here.</p>
                    </div>
                `;
            }

        } else {
            jobsListDiv.innerHTML = '<div class="alert alert-danger mx-auto">Failed to load history.</div>';
        }
    } catch (error) {
        console.error("Error fetching history:", error);
        jobsListDiv.innerHTML = '<div class="alert alert-danger mx-auto">Network error. Please try again.</div>';
    }
}
