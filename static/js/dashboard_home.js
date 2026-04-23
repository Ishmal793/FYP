document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('access');
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    try {
        // Fetch user profile to check role
        const profileRes = await fetch('/api/auth/profile/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        let userRole = 'job_seeker';
        if (profileRes.ok) {
            const profileData = await profileRes.json();
            userRole = profileData.role;
        }

        if (userRole === 'hr') {
            // Recruiter View
            document.getElementById('hr-recruiter-card').classList.remove('d-none');
            document.getElementById('ats-module-col').classList.add('d-none');
            document.getElementById('job-search-col').classList.add('d-none');
        } else {
            // Job Seeker View
            // Fetch completed resumes to check if Job Search should be unlocked
            const response = await fetch('/api/resume/completed/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                const hasCompletedAts = data.resumes && data.resumes.length > 0;
                
                const jobCard = document.getElementById('job-search-card');
                const jobLock = document.getElementById('job-lock-overlay');
                
                if (hasCompletedAts) {
                    jobLock.classList.add('unlocked');
                    jobCard.classList.remove('locked');
                    window.jobSearchUnlocked = true;
                } else {
                    jobLock.classList.remove('unlocked');
                    jobCard.classList.add('locked');
                    window.jobSearchUnlocked = false;
                }
            }
        }

        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-modules').style.display = 'flex';

    } catch (error) {
        console.error("Error fetching dashboard status:", error);
        document.getElementById('loading').innerHTML = '<div class="alert alert-danger mx-auto" style="max-width:400px;">Failed to verify module access. Please refresh.</div>';
    }
});

function handleJobSearchClick() {
    if (window.jobSearchUnlocked) {
        window.location.href = '/dashboard/jobs/';
    } else {
        alert("Complete ATS Analysis first to unlock Job Search.");
    }
}
