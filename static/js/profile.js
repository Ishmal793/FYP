const token = localStorage.getItem('access');
let currentProfileData = null;

document.addEventListener('DOMContentLoaded', async () => {
    if (!token) {
        window.location.href = '/login/';
        return;
    }
    
    // Load data in background
    Promise.allSettled([loadProfile(), loadResumes()]);

    // Attach Listeners
    attachListener('form-personal', handleSavePersonal);
    attachListener('form-education', handleSaveEducation);
    attachListener('form-career', handleSaveCareer);
    attachListener('form-add-skill', handleAddSkill);
    attachListener('form-add-experience', handleAddExperience);
    attachListener('form-add-project', handleAddProject);
});

function showLoader(show) {
    const loader = document.getElementById('profile-loader');
    const content = document.getElementById('profile-content');
    if (loader) loader.style.display = show ? 'block' : 'none';
    if (content) content.style.display = show ? 'none' : 'block';
}

function attachListener(id, handler) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('submit', handler);
}

async function loadProfile() {
    try {
        const response = await fetch('/api/auth/profile/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            currentProfileData = await response.json();
            populateUI(currentProfileData);
        }
    } catch (e) {
        console.error("Profile Fetch Exception:", e);
    }
}

async function loadResumes() {
    const resumeList = document.getElementById('resume-list');
    if (!resumeList) return;

    try {
        const response = await fetch('/api/resume/completed/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            window.allResumes = data.resumes || [];
            renderResumeList(false);
        }
    } catch (e) {
        console.error("Resume load error:", e);
    }
}

function renderResumeList(showAll) {
    const resumeList = document.getElementById('resume-list');
    const toggleContainer = document.getElementById('resume-toggle-container');
    const resumes = window.allResumes || [];
    
    if (resumes.length === 0) {
        resumeList.innerHTML = '<div class="text-center py-3 text-muted small">No resumes found.</div>';
        toggleContainer?.classList.add('d-none');
        return;
    }

    const itemsToShow = showAll ? resumes : resumes.slice(0, 3);
    
    resumeList.innerHTML = itemsToShow.map(r => `
        <div class="resume-item d-flex justify-content-between align-items-center animate-fade-in">
            <div class="d-flex align-items-center gap-2">
                <i class="bi bi-file-earmark-pdf text-danger fs-5"></i>
                <div>
                    <div class="fw-bold small text-truncate" style="max-width: 150px;">${r.filename || 'Resume.pdf'}</div>
                    <div class="text-muted" style="font-size: 0.65rem;">ATS Score: ${r.score || '--'}%</div>
                </div>
            </div>
            <a href="${r.file_url}" target="_blank" class="btn btn-sm btn-link text-decoration-none fw-bold small">View</a>
        </div>
    `).join('');

    if (resumes.length > 3) {
        toggleContainer?.classList.remove('d-none');
        const btn = document.getElementById('resume-toggle-btn');
        if (btn) btn.innerHTML = showAll ? 'Show Less <i class="bi bi-chevron-up ms-1"></i>' : `Show More (${resumes.length - 3}) <i class="bi bi-chevron-down ms-1"></i>`;
    } else {
        toggleContainer?.classList.add('d-none');
    }
}

window.toggleResumeList = () => {
    window.isShowingAllResumes = !window.isShowingAllResumes;
    renderResumeList(window.isShowingAllResumes);
};

function populateUI(data) {
    if (!data) return;
    try {
        const p = data.career_profile || {};
        
        safeSetText('hero-name', data.name || 'User');
        safeSetText('hero-role', p.target_job_role || 'Professional');
        safeSetText('hero-location', data.address || 'Global');
        safeSetText('hero-experience', p.experience || 'Entry Level');
        safeSetText('avatar-initials', (data.name ? data.name[0] : 'U').toUpperCase());

        safeSetText('view-email', data.email);
        safeSetText('view-phone', data.phone);
        safeSetText('view-dob', data.date_of_birth);
        safeSetText('view-address', data.address);
        
        safeSetVal('edit-name', data.name || '');
        safeSetVal('edit-phone', data.phone || '');
        safeSetVal('edit-dob', data.date_of_birth || '');
        safeSetVal('edit-address', data.address || '');

        safeSetText('view-edu-display', `${p.education_level || '--'} in ${data.field_of_study || '--'}`);
        safeSetText('view-university', data.university);
        safeSetText('view-grad-status', p.student_or_graduate);
        safeSetText('view-grad-year', p.graduation_year);
        safeSetText('view-cgpa', p.cgpa || '--');

        safeSetVal('edit-university', data.university || '');
        safeSetVal('edit-field', data.field_of_study || '');
        safeSetVal('edit-grad-status', p.student_or_graduate || '');
        safeSetVal('edit-cgpa', p.cgpa || '');

        safeSetText('view-target-role', p.target_job_role);
        safeSetText('view-career-display', `${p.experience || '--'} Experience (${p.career_level || '--'})`);
        setLink('view-linkedin', p.linkedin_url);
        setLink('view-portfolio', p.portfolio_url);

        safeSetVal('edit-target-role', p.target_job_role || '');
        safeSetVal('edit-experience', p.experience || '');
        safeSetVal('edit-career-level', p.career_level || '');
        safeSetVal('edit-linkedin', p.linkedin_url || '');
        safeSetVal('edit-portfolio', p.portfolio_url || '');

        renderSkills(p.skills);
        renderExperience(p.experience_list);
        renderProjects(p.projects);

    } catch (err) {
        console.error("UI Population Exception:", err);
    }
}

function renderSkills(skills) {
    const el = document.getElementById('view-skills');
    if (!el) return;
    let items = [];
    if (Array.isArray(skills)) {
        items = skills.map(s => (typeof s === 'object' ? (s.name || s.skill) : s));
    } else if (typeof skills === 'string') {
        items = skills.split(',').map(s=>s.trim());
    }
    
    if (items.length > 0) {
        el.innerHTML = items.map((s, idx) => `
            <div class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-10 me-1 mb-1 small px-3 py-2 rounded-pill d-inline-flex align-items-center gap-2">
                <span>${s}</span>
                <i class="bi bi-x-circle-fill text-primary text-opacity-50 cursor-pointer" onclick="confirmDeleteSkill(${idx})" style="cursor: pointer;"></i>
            </div>
        `).join('');
    } else {
        el.innerHTML = '<span class="text-muted small">No skills added yet.</span>';
    }
}

function renderExperience(list) {
    const el = document.getElementById('view-experience-list');
    if (!el) return;
    if (list && Array.isArray(list) && list.length > 0) {
        el.innerHTML = list.map((item, idx) => {
            let role, company, duration;
            if (typeof item === 'string') {
                role = item;
                company = 'Professional Record';
                duration = '';
            } else {
                role = item.role || item.title || 'Role';
                company = item.company || item.organization || 'Experience';
                duration = item.duration || '';
            }
            return `
                <div class="mb-3 border-start ps-3 border-primary border-opacity-25 position-relative group">
                    <div class="fw-bold small text-primary">${role}</div>
                    <div class="text-muted" style="font-size: 0.8rem;">${company}</div>
                    ${duration ? `<div class="text-muted" style="font-size: 0.7rem;">${duration}</div>` : ''}
                    <button class="btn btn-link text-danger p-0 position-absolute top-0 end-0 small opacity-50" onclick="confirmDeleteExp(${idx})"><i class="bi bi-trash3"></i></button>
                </div>
            `;
        }).join('');
    } else {
        el.innerHTML = '<div class="text-muted small">No experience records.</div>';
    }
}

function renderProjects(list) {
    const el = document.getElementById('view-projects-list');
    if (!el) return;
    if (list && Array.isArray(list) && list.length > 0) {
        el.innerHTML = list.map((item, idx) => {
            let title, desc;
            if (typeof item === 'string') {
                title = item;
                desc = '';
            } else {
                title = item.title || item.name || 'Project';
                desc = item.description || item.summary || '';
            }
            return `
                <div class="mb-3 border-start ps-3 border-success border-opacity-25 position-relative">
                    <div class="fw-bold small text-success">${title}</div>
                    ${desc ? `<div class="text-muted" style="font-size: 0.8rem;">${desc}</div>` : ''}
                    <button class="btn btn-link text-danger p-0 position-absolute top-0 end-0 small opacity-50" onclick="confirmDeleteProj(${idx})"><i class="bi bi-trash3"></i></button>
                </div>
            `;
        }).join('');
    } else {
        el.innerHTML = '<div class="text-muted small">No project records found.</div>';
    }
}

function safeSetText(id, text) { const el = document.getElementById(id); if (el) el.innerText = text || '--'; }
function safeSetVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function setLink(id, url) { const el = document.getElementById(id); if (!el) return; if (url) { el.href = url; el.style.display = 'inline-block'; } else { el.style.display = 'none'; } }

async function submitProfileUpdate(payload, sectionName) {
    try {
        const response = await fetch('/api/auth/career-profile/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            if (typeof showToast === 'function') showToast(`${sectionName} updated!`, 'success');
            await loadProfile();
            
            // Auto hide modals
            const modals = ['Skill', 'Experience', 'Project'];
            modals.forEach(m => {
                const el = document.getElementById(`add${m}Modal`);
                if (el) {
                    const inst = bootstrap.Modal.getInstance(el);
                    if (inst) inst.hide();
                }
            });

            // Reset forms
            const forms = ['form-add-skill', 'form-add-experience', 'form-add-project'];
            forms.forEach(f => document.getElementById(f)?.reset());

            // Exit edit modes
            document.querySelectorAll('.is-editing').forEach(el => el.classList.remove('is-editing'));

        } else {
            if (typeof showToast === 'function') showToast('Update failed.', 'error');
        }
    } catch (e) { console.error("Update error:", e); }
}

function handleSavePersonal(e) { e.preventDefault(); submitProfileUpdate({ name: document.getElementById('edit-name').value, phone: document.getElementById('edit-phone').value, date_of_birth: document.getElementById('edit-dob').value, address: document.getElementById('edit-address').value }, 'Personal'); }
function handleSaveEducation(e) { e.preventDefault(); submitProfileUpdate({ university: document.getElementById('edit-university').value, field_of_study: document.getElementById('edit-field').value, student_or_graduate: document.getElementById('edit-grad-status').value, cgpa: document.getElementById('edit-cgpa').value }, 'Education'); }
function handleSaveCareer(e) { e.preventDefault(); submitProfileUpdate({ target_job_role: document.getElementById('edit-target-role').value, experience: document.getElementById('edit-experience').value, career_level: document.getElementById('edit-career-level').value, linkedin_url: document.getElementById('edit-linkedin').value, portfolio_url: document.getElementById('edit-portfolio').value }, 'Career'); }

function handleAddSkill(e) {
    e.preventDefault();
    const newSkills = document.getElementById('new-skill-name').value.split(',').map(s => s.trim()).filter(s => s !== '');
    const existing = (currentProfileData.career_profile || {}).skills || [];
    const updated = [...existing, ...newSkills];
    submitProfileUpdate({ skills: updated }, 'Skill');
}

function handleAddExperience(e) {
    e.preventDefault();
    const list = (currentProfileData.career_profile || {}).experience_list || [];
    list.push({ role: document.getElementById('new-exp-role').value, company: document.getElementById('new-exp-company').value, duration: document.getElementById('new-exp-duration').value });
    submitProfileUpdate({ experience_list: list }, 'Experience');
}

function handleAddProject(e) {
    e.preventDefault();
    const list = (currentProfileData.career_profile || {}).projects || [];
    list.push({ title: document.getElementById('new-proj-title').value, description: document.getElementById('new-proj-desc').value });
    submitProfileUpdate({ projects: list }, 'Project');
}

// Delete Logic with custom messages
window.confirmDeleteSkill = (idx) => {
    if (confirm("Do you want to delete this skill from your profile?")) {
        const skills = (currentProfileData.career_profile || {}).skills || [];
        skills.splice(idx, 1);
        submitProfileUpdate({ skills: skills }, 'Skill');
    }
};

window.confirmDeleteExp = (idx) => {
    if (confirm("Remove this experience record?")) {
        const list = (currentProfileData.career_profile || {}).experience_list || [];
        list.splice(idx, 1);
        submitProfileUpdate({ experience_list: list }, 'Experience');
    }
};

window.confirmDeleteProj = (idx) => {
    if (confirm("Delete this project from your profile?")) {
        const list = (currentProfileData.career_profile || {}).projects || [];
        list.splice(idx, 1);
        submitProfileUpdate({ projects: list }, 'Project');
    }
};

function toggleEdit(section) {
    const el = document.getElementById(`section-${section}`);
    if (el) el.classList.add('is-editing');
}

function cancelEdit(section) {
    const el = document.getElementById(`section-${section}`);
    if (el) el.classList.remove('is-editing');
    if (currentProfileData) populateUI(currentProfileData);
}
