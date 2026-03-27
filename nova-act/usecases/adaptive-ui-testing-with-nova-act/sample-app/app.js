// Phase 1: Original v1.0 (5 fields only)
const students = [
    { id: 'S001', firstName: 'John', lastName: 'Smith', major: 'CS', enrollmentDate: '2024-01-15' },
    { id: 'S002', firstName: 'Sarah', lastName: 'Johnson', major: 'ENG', enrollmentDate: '2023-03-22' },
    { id: 'S003', firstName: 'Michael', lastName: 'Brown', major: 'BUS', enrollmentDate: '2025-06-10' }
];

// Navigation mapping: button ID -> view ID
const NAV_MAP = {
    'nav-home': 'home-view',
    'nav-student': 'student-view',
    'nav-search': 'search-view'
};

// Setup navigation
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        
        e.target.classList.add('active');
        
        const viewId = NAV_MAP[e.target.id];
        if (viewId) {
            const view = document.getElementById(viewId);
            if (view) {
                view.classList.add('active');
            }
        }
    });
});

// Student form submission
const studentForm = document.getElementById('student-form');
if (studentForm) {
    studentForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const student = {
            id: formData.get('studentId'),
            firstName: formData.get('firstName'),
            lastName: formData.get('lastName'),
            major: formData.get('major'),
            enrollmentDate: formData.get('enrollmentDate')
        };
        
        students.push(student);
        
        const successMsg = document.getElementById('success-message');
        if (successMsg) {
            successMsg.style.display = 'block';
            setTimeout(() => {
                successMsg.style.display = 'none';
            }, 3000);
        }
        
        e.target.reset();
    });
}

// Clear form
const clearBtn = document.getElementById('clear-btn');
if (clearBtn) {
    clearBtn.addEventListener('click', () => {
        const form = document.getElementById('student-form');
        if (form) {
            form.reset();
        }
    });
}

// Search functionality
const searchBtn = document.getElementById('search-btn');
if (searchBtn) {
    searchBtn.addEventListener('click', () => {
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;
        
        const query = searchInput.value.toLowerCase();
        const results = students.filter(student => 
            student.id.toLowerCase().includes(query) ||
            student.firstName.toLowerCase().includes(query) ||
            student.lastName.toLowerCase().includes(query)
        );
        
        displayResults(results);
    });
}

function displayResults(results) {
    const container = document.getElementById('search-results');
    if (!container) return;
    
    if (results.length === 0) {
        container.innerHTML = '<p>No students found.</p>';
        return;
    }
    
    const table = `
        <table>
            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Major</th>
                    <th>Enrollment Date</th>
                </tr>
            </thead>
            <tbody>
                ${results.map(student => `
                    <tr>
                        <td>${student.id}</td>
                        <td>${student.firstName}</td>
                        <td>${student.lastName}</td>
                        <td>${student.major}</td>
                        <td>${student.enrollmentDate}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = table;
}

// Auto-navigate to Student Data if hash is present
window.addEventListener('DOMContentLoaded', () => {
    if (window.location.hash === '#student') {
        setTimeout(() => {
            const studentBtn = document.getElementById('nav-student');
            if (studentBtn) {
                studentBtn.click();
            }
        }, 200);
    }
    
    // Initialize phase information panel
    initializePhasePanel();
});

// Phase Panel Configuration
function initializePhasePanel() {
    const panel = document.getElementById('phase-info-panel');
    if (!panel) return;
    
    // Detect phase from document title or default to Phase 1
    const title = document.title;
    let phase = 1;
    let phaseClass = 'phase-1';
    let content = '';
    
    if (title.includes('v1.5')) {
        phase = 2;
        phaseClass = 'phase-2';
    } else if (title.includes('v2.0')) {
        phase = 3;
        phaseClass = 'phase-3';
    }
    
    panel.className = `phase-info-panel ${phaseClass}`;
    
    if (phase === 1) {
        content = `
            <h3><span class="phase-icon">📋</span> PHASE 1: BASELINE</h3>
            <div class="divider"></div>
            <p style="font-size: 14px; line-height: 1.6; margin-bottom: 15px;">
                Simple Student Information System
            </p>
            <div class="section-title">Form Fields:</div>
            <ul class="info-list">
                <li>✓ Student ID</li>
                <li>✓ First Name</li>
                <li>✓ Last Name</li>
                <li>✓ Major</li>
                <li>✓ Enrollment Date</li>
            </ul>
            <div class="status-badge">Original UI - Both frameworks testing</div>
        `;
    } else if (phase === 2) {
        content = `
            <h3><span class="phase-icon">🔄</span> PHASE 2: STRUCTURAL CHANGES</h3>
            <div class="divider"></div>
            <div class="section-title">What Changed:</div>
            
            <div class="change-item">
                <strong>Button ID:</strong><br>
                #save-btn <span class="change-arrow">→</span> #submit-student-btn
            </div>
            
            <div class="change-item">
                <strong>Button Text:</strong><br>
                "Save Student" <span class="change-arrow">→</span> "Submit Registration"
            </div>
            
            <div class="change-item">
                <strong>Student ID Field:</strong><br>
                #student-id <span class="change-arrow">→</span> #student-id-input
            </div>
            
            <div class="change-item">
                <strong>Field Order:</strong><br>
                Student ID moved to top
            </div>
            
            <div class="change-item">
                <strong>CSS Classes:</strong><br>
                .form-group <span class="change-arrow">→</span> .form-field
            </div>
            
            <div class="status-badge">Testing Adaptation...</div>
        `;
    } else if (phase === 3) {
        content = `
            <h3><span class="phase-icon">✨</span> PHASE 3: NEW FEATURES</h3>
            <div class="divider"></div>
            <div class="section-title">What's New:</div>
            
            <div class="change-item">
                <strong>✨ Email Address</strong><br>
                Required field
            </div>
            
            <div class="change-item">
                <strong>✨ GPA</strong><br>
                Optional field
            </div>
            
            <div class="section-title" style="margin-top: 25px;">Previous Changes:</div>
            <ul class="info-list">
                <li>✓ Structural refactoring</li>
                <li>✓ Updated selectors</li>
                <li>✓ Field reordering</li>
            </ul>
            
            <div class="status-badge">Testing Feature Addition...</div>
        `;
    }
    
    panel.innerHTML = content;
}
