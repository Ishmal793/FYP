document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    // Background verification (Non-blocking)
    fetch('/api/auth/profile/', {
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(res => res.ok ? res.json() : null).then(data => {
        if (data && data.role === 'hr') {
            document.getElementById('hr-recruiter-card')?.classList.remove('d-none');
            document.getElementById('ats-module-col')?.classList.add('d-none');
            document.getElementById('job-search-col')?.classList.add('d-none');
        }
    }).catch(e => console.error("Profile check failed", e));

    fetch('/api/resume/completed/', {
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(res => res.ok ? res.json() : null).then(data => {
        if (data) {
            const hasCompletedAts = data.resumes && data.resumes.length > 0;
            const jobCard = document.getElementById('job-search-card');
            const jobLock = document.getElementById('job-lock-overlay');
            if (hasCompletedAts) {
                jobLock?.classList.add('unlocked');
                jobCard?.classList.remove('locked');
                window.jobSearchUnlocked = true;
            }
        }
    }).catch(e => console.error("ATS status check failed", e));
});

function handleJobSearchClick() {
    if (window.jobSearchUnlocked) {
        window.location.href = '/dashboard/jobs/';
    } else {
        alert("Complete ATS Analysis first to unlock Job Search.");
    }
}
