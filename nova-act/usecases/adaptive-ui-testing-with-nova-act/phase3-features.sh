#!/bin/bash

# Phase 3: New Features
# Adds email and GPA fields to demonstrate feature enhancement

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 3: Feature Enhancement"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will add NEW features to the UI:"
echo "  ✨ Email Address field (required)"
echo "  ✨ GPA field (optional)"
echo ""
echo "Plus keeps all Phase 2 structural changes"
echo ""
echo -e "${YELLOW}WARNING: This will modify sample-app/index.html${NC}"
echo "A backup will be created at sample-app/index.html.phase2.backup"
echo ""

read -p "Press Enter to apply changes..."
echo ""

# Backup Phase 2 version
echo "Creating backup of Phase 2 version..."
cp sample-app/index.html sample-app/index.html.phase2.backup
cp sample-app/app.js sample-app/app.js.phase2.backup
echo "✓ Backup created"
echo ""

# Apply Phase 3 changes
echo "Adding new features to index.html..."

cat > sample-app/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Information System v2.0</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="phase-info-panel" id="phase-info-panel">
        <!-- Phase information will be injected by JavaScript -->
    </div>
    <div class="container">
        <header>
            <h1>Student Information System</h1>
            <div class="user-info">Welcome, Admin User</div>
        </header>

        <nav class="main-nav">
            <button id="nav-home" class="nav-btn active">Home</button>
            <button id="nav-student-data" class="nav-btn">Student Data</button>
            <button id="nav-search" class="nav-btn">Search</button>
        </nav>

        <main id="content">
            <div id="home-view" class="view active">
                <h2>Dashboard</h2>
                <div class="dashboard-cards">
                    <div class="card">
                        <h3>Total Students</h3>
                        <p class="stat">1,247</p>
                    </div>
                    <div class="card">
                        <h3>Active Enrollments</h3>
                        <p class="stat">1,198</p>
                    </div>
                </div>
            </div>

            <div id="student-view" class="view">
                <h2>Student Registration</h2>
                <form id="student-form">
                    <div class="form-field">
                        <label for="student-id-input">Student ID:</label>
                        <input type="text" id="student-id-input" name="studentId" required>
                    </div>
                    <div class="form-field">
                        <label for="first-name">First Name:</label>
                        <input type="text" id="first-name" name="firstName" required>
                    </div>
                    <div class="form-field">
                        <label for="last-name">Last Name:</label>
                        <input type="text" id="last-name" name="lastName" required>
                    </div>
                    <!-- NEW FIELD: Email -->
                    <div class="form-field new-field">
                        <label for="student-email">Email Address: <span class="new-badge">✨ NEW</span></label>
                        <input type="email" id="student-email" name="email" required>
                    </div>
                    <div class="form-field">
                        <label for="major">Major:</label>
                        <select id="major" name="major" required>
                            <option value="">Select Major</option>
                            <option value="CS">Computer Science</option>
                            <option value="ENG">Engineering</option>
                            <option value="BUS">Business</option>
                            <option value="BIO">Biology</option>
                        </select>
                    </div>
                    <!-- NEW FIELD: GPA -->
                    <div class="form-field new-field">
                        <label for="student-gpa">GPA (0.0-4.0): <span class="new-badge">✨ NEW</span></label>
                        <input type="number" id="student-gpa" name="gpa" min="0.0" max="4.0" step="0.01">
                    </div>
                    <div class="form-field">
                        <label for="enrollment-date">Enrollment Date:</label>
                        <input type="text" id="enrollment-date" name="enrollmentDate" placeholder="YYYY-MM-DD" required>
                    </div>
                    <div class="form-actions">
                        <button type="submit" id="submit-student-btn" class="btn-primary">Submit Registration</button>
                        <button type="button" id="clear-btn" class="btn-secondary">Clear Form</button>
                    </div>
                </form>
                <div id="confirmation-msg" class="message success" style="display: none;">
                    Student registration completed successfully!
                </div>
            </div>

            <div id="search-view" class="view">
                <h2>Student Search</h2>
                <div class="search-box">
                    <input type="text" id="search-input" placeholder="Search by name or ID...">
                    <button id="search-btn" class="btn-primary">Search</button>
                </div>
                <div id="search-results" class="results-table"></div>
            </div>
        </main>
    </div>
    <script src="app.js"></script>
</body>
</html>
EOF

# Update app.js for new fields
cat > sample-app/app.js << 'EOF'
// Phase 3: Added email and GPA fields
const students = [
    { id: 'S001', firstName: 'John', lastName: 'Smith', email: 'john.smith@university.edu', major: 'CS', gpa: 3.8, enrollmentDate: '2024-01-15' },
    { id: 'S002', firstName: 'Sarah', lastName: 'Johnson', email: 'sarah.j@university.edu', major: 'ENG', gpa: 3.9, enrollmentDate: '2023-03-22' },
    { id: 'S003', firstName: 'Michael', lastName: 'Brown', email: 'mbrown@university.edu', major: 'BUS', gpa: 3.5, enrollmentDate: '2025-06-10' }
];

const NAV_MAP = {
    'nav-home': 'home-view',
    'nav-student-data': 'student-view',
    'nav-search': 'search-view'
};

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

const studentForm = document.getElementById('student-form');
if (studentForm) {
    studentForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const student = {
            id: formData.get('studentId'),
            firstName: formData.get('firstName'),
            lastName: formData.get('lastName'),
            email: formData.get('email'),
            major: formData.get('major'),
            gpa: formData.get('gpa'),
            enrollmentDate: formData.get('enrollmentDate')
        };
        
        students.push(student);
        
        const successMsg = document.getElementById('confirmation-msg');
        if (successMsg) {
            successMsg.style.display = 'block';
            setTimeout(() => {
                successMsg.style.display = 'none';
            }, 3000);
        }
        
        e.target.reset();
    });
}

const clearBtn = document.getElementById('clear-btn');
if (clearBtn) {
    clearBtn.addEventListener('click', () => {
        const form = document.getElementById('student-form');
        if (form) {
            form.reset();
        }
    });
}

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
                    <th>Email</th>
                    <th>Major</th>
                    <th>GPA</th>
                    <th>Enrollment Date</th>
                </tr>
            </thead>
            <tbody>
                ${results.map(student => `
                    <tr>
                        <td>${student.id}</td>
                        <td>${student.firstName}</td>
                        <td>${student.lastName}</td>
                        <td>${student.email || 'N/A'}</td>
                        <td>${student.major}</td>
                        <td>${student.gpa || 'N/A'}</td>
                        <td>${student.enrollmentDate}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = table;
}

window.addEventListener('DOMContentLoaded', () => {
    if (window.location.hash === '#student') {
        setTimeout(() => {
            const studentBtn = document.getElementById('nav-student-data');
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
EOF

echo "✓ New features added"
echo ""
echo -e "${GREEN}Refresh your browser to see the new fields!${NC}"
echo "URL: http://localhost:8000/#student"
echo ""
echo "Look for the yellow-highlighted Email and GPA fields"
echo ""

read -p "Press Enter after refreshing browser to continue..."
echo ""

#############################################
# EXPLAIN THE SITUATION
#############################################

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 3: New Features Require Test Updates"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The UI now has 2 new fields that both frameworks need to test:"
echo "  ✨ Email Address (required)"
echo "  ✨ GPA (optional)"
echo ""
echo "Both test frameworks need updates to handle these new fields."
echo ""
echo "Updating tests:"
echo "  • Playwright: Adding 2 selector-based lines"
echo "    await page.fill('#student-email', 'jane.doe@university.edu');"
echo "    await page.fill('#student-gpa', '3.8');"
echo ""
echo "  • Nova Act: Adding 2 natural language steps"
echo "    \"Enter email jane.doe@university.edu\""
echo "    \"Enter GPA 3.8\""
echo ""
read -p "Press Enter to run updated tests..."
echo ""

#############################################
# TEST PLAYWRIGHT (updated test)
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing Updated Playwright${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd playwright-tests
PLAYWRIGHT_OUTPUT=$(npx playwright test tests/phase3_features.spec.js --reporter=line 2>&1)
echo "$PLAYWRIGHT_OUTPUT"
cd ..

echo ""
if echo "$PLAYWRIGHT_OUTPUT" | grep -q "1 passed"; then
    echo -e "${GREEN}✓ VERIFIED: Playwright test passed${NC}"
else
    echo -e "${YELLOW}? Unexpected result - please review output${NC}"
fi

echo ""
read -p "Press Enter to test Nova Act..."
echo ""

#############################################
# TEST NOVA ACT (updated test)
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing Updated Nova Act${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd nova-act-tests
source venv/bin/activate
NOVA_OUTPUT=$(pytest tests/test_runner.py::test_with_nova_act -k "NA-03" -v --tb=line --no-header --quiet 2>&1)

# Show only relevant output
echo "$NOVA_OUTPUT" | grep -E "(✓|✗|Test|Error|Possible|PASSED|FAILED|passed|failed)" || echo "$NOVA_OUTPUT"

deactivate
cd ..

echo ""
if echo "$NOVA_OUTPUT" | grep -q "1 passed"; then
    echo -e "${GREEN}✓ VERIFIED: Nova Act test passed${NC}"
else
    echo -e "${YELLOW}? Unexpected result - please review output${NC}"
fi

#############################################
# SUMMARY
#############################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 3 Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Both frameworks needed updates for new features:"
echo "  ✓ Playwright: 2 selector-based lines added"
echo "  ✓ Nova Act: 2 natural language steps added"
echo ""
echo "Key Insight: Nova Act's natural language approach requires"
echo "             no selector knowledge, making updates simpler."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Demo Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To restore original UI:"
echo "  ./restore-original.sh"
echo ""
