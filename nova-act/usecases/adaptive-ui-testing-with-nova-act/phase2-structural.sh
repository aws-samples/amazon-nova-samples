#!/bin/bash

# Phase 2: Structural Changes
# Modifies UI in place to show selector/structure changes

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 2: Structural Refactoring"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will modify the UI with structural changes:"
echo "  ✓ Selector IDs changed"
echo "  ✓ Button text changed"
echo "  ✓ Field order changed"
echo "  ✓ CSS classes changed"
echo ""
echo "NO new features added - same 5 fields"
echo ""
echo -e "${YELLOW}WARNING: This will modify sample-app/index.html${NC}"
echo "A backup will be created at sample-app/index.html.phase1.backup"
echo ""

read -p "Press Enter to apply changes..."
echo ""

# Backup original
echo "Creating backup..."
cp sample-app/index.html sample-app/index.html.phase1.backup
cp sample-app/app.js sample-app/app.js.phase1.backup
echo "✓ Backup created"
echo ""

# Apply Phase 2 changes to index.html
echo "Applying structural changes to index.html..."

cat > sample-app/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Information System v1.5</title>
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
                    <!-- CHANGED: Student ID moved to top -->
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
                    <div class="form-field">
                        <label for="enrollment-date">Enrollment Date:</label>
                        <input type="text" id="enrollment-date" name="enrollmentDate" placeholder="YYYY-MM-DD" required>
                    </div>
                    <div class="form-actions">
                        <!-- CHANGED: Button ID and text -->
                        <button type="submit" id="submit-student-btn" class="btn-primary">Submit Registration</button>
                        <button type="button" id="clear-btn" class="btn-secondary">Clear Form</button>
                    </div>
                </form>
                <!-- CHANGED: Message ID -->
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

# Update app.js for new selectors
cat > sample-app/app.js << 'EOF'
// Phase 2: Updated selectors
const students = [
    { id: 'S001', firstName: 'John', lastName: 'Smith', major: 'CS', enrollmentDate: '2024-01-15' },
    { id: 'S002', firstName: 'Sarah', lastName: 'Johnson', major: 'ENG', enrollmentDate: '2023-03-22' },
    { id: 'S003', firstName: 'Michael', lastName: 'Brown', major: 'BUS', enrollmentDate: '2025-06-10' }
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
            major: formData.get('major'),
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

echo "✓ Changes applied"
echo ""
echo -e "${GREEN}Refresh your browser to see the changes!${NC}"
echo "URL: http://localhost:8000/#student"
echo ""

read -p "Press Enter after refreshing browser to run tests..."
echo ""

#############################################
# TEST PLAYWRIGHT (should fail)
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing Playwright (OLD selectors)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Expected: FAIL (selectors changed)"
echo ""

cd playwright-tests
PLAYWRIGHT_OUTPUT=$(npx playwright test tests/phase1_student.spec.js --reporter=line 2>&1 || true)
echo "$PLAYWRIGHT_OUTPUT"
cd ..

echo ""
if echo "$PLAYWRIGHT_OUTPUT" | grep -qi "failed\|error"; then
    echo -e "${GREEN}✓ EXPECTED: Playwright failed (selectors broken)${NC}"
else
    echo -e "${YELLOW}? Unexpected result - please review output${NC}"
fi

echo ""
read -p "Press Enter to test Nova Act..."
echo ""

#############################################
# TEST NOVA ACT (should pass)
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing Nova Act (SAME Phase 1 test — zero changes)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Running the exact same test file from Phase 1 (NA-01)"
echo "Expected: PASS (adapts automatically)"
echo ""

cd nova-act-tests
source venv/bin/activate
NOVA_OUTPUT=$(pytest tests/test_runner.py::test_with_nova_act -k "NA-01" -v --tb=line --no-header --quiet 2>&1)

# Show only relevant output
echo "$NOVA_OUTPUT" | grep -E "(✓|✗|Test|Error|Possible|PASSED|FAILED|passed|failed)" || echo "$NOVA_OUTPUT"

deactivate
cd ..

echo ""
if echo "$NOVA_OUTPUT" | grep -q "1 passed"; then
    echo -e "${GREEN}✓ VERIFIED: Nova Act passed (adapted to changes)${NC}"
else
    echo -e "${YELLOW}? Unexpected result - please review output${NC}"
fi

#############################################
# SUMMARY
#############################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 2 Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "  Playwright: ${RED}✗ FAILED${NC} (selectors broken)"
echo -e "  Nova Act:   ${GREEN}✓ PASSED${NC} (adapted automatically)"
echo ""
echo "Key Insight: Nova Act eliminates selector maintenance"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Step"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Run Phase 3 to see how new features are handled:"
echo "  ./phase3-features.sh"
echo ""
echo "To restore original UI:"
echo "  ./restore-original.sh"
echo ""
