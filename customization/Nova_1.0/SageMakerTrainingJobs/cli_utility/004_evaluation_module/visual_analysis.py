#!/usr/bin/env python3
"""
Script to fix the visual failure analysis UI in the evaluator.py file.
"""

import os
import json
import http.server
import socketserver
from pathlib import Path

def create_visual_failure_analysis(jsonl_file, output_dir=None, port=8000):
    """Create a visual failure analysis UI for analyzing JSONL inference results.
    
    Args:
        jsonl_file: Path to the JSONL file containing inference results
        output_dir: Directory to store the HTML UI files (optional)
        port: Port to use for the HTTP server
        
    Returns:
        Tuple of (HTML file path, server port)
    """
    try:
        # Create output directory if not provided
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(jsonl_file), "visual_analysis")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Read the JSONL file
        print(f"Reading inference results from {jsonl_file}...")
        records = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    records.append(record)
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line[:50]}...")
        
        print(f"Loaded {len(records)} records")
        
        # Create the HTML file
        html_file = os.path.join(output_dir, "visual_analysis.html")
        notes_file = os.path.join(output_dir, "analysis_notes.json")
        annotated_jsonl_file = os.path.join(output_dir, "annotated_inferences.jsonl")
        
        # Initialize notes file if it doesn't exist
        if not os.path.exists(notes_file):
            with open(notes_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
        # Create the HTML content
        html_content = _generate_html_ui(records, notes_file, annotated_jsonl_file)
        
        # Write the HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Visual failure analysis UI created at: {html_file}")
        
        # Start a simple HTTP server to serve the HTML file
        print(f"Starting HTTP server on port {port}...")
        print(f"Open your browser and navigate to: http://localhost:{port}/visual_analysis.html")
        print("Press Ctrl+C to stop the server when finished")
        
        # Change to the output directory and start the server
        os.chdir(output_dir)
        
        # After changing directory, use relative paths for files
        notes_file_relative = "analysis_notes.json"
        annotated_jsonl_file_relative = "annotated_inferences.jsonl"
        
        # Create a custom HTTP request handler that can handle POST requests for saving notes
        class NotesHandler(http.server.SimpleHTTPRequestHandler):
            def do_POST(self):
                """Handle POST requests for saving notes."""
                if self.path == '/save_notes_file' or self.path == '/write_notes_to_file':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        # Parse the JSON data
                        if self.path == '/write_notes_to_file':
                            # Handle JSON data
                            data = json.loads(post_data.decode('utf-8'))
                            notes_data = data.get('notes', {})
                            record_data = data.get('record', {})
                            file_path = data.get('filePath', notes_file_relative)
                            record_id = data.get('recordId', '')
                            annotated_file_path = data.get('annotatedFilePath', annotated_jsonl_file_relative)
                            
                            # Ensure the directory exists
                            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                            os.makedirs(os.path.dirname(os.path.abspath(annotated_file_path)), exist_ok=True)
                            
                            # Save to the notes file (JSON format)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(notes_data, f, indent=2)
                            
                            # Append the notes to the annotated JSONL file
                            # Each line is a complete record with its notes
                            if record_id in notes_data and notes_data[record_id] and record_data:
                                # Create a new record that includes the original data and the notes
                                annotated_record = record_data.copy()
                                
                                # Add the notes
                                annotated_record['notes'] = notes_data[record_id]
                                
                                # Check if this record already exists in the file
                                existing_records = {}
                                if os.path.exists(annotated_file_path):
                                    with open(annotated_file_path, 'r', encoding='utf-8') as f:
                                        for line in f:
                                            try:
                                                existing_record = json.loads(line.strip())
                                                if 'id' in existing_record:
                                                    existing_records[existing_record['id']] = True
                                                elif 'example_id' in existing_record:
                                                    existing_records[existing_record['example_id']] = True
                                            except:
                                                pass
                                
                                # Only append if the record doesn't already exist
                                record_unique_id = record_data.get('id', record_data.get('example_id', record_id))
                                if record_unique_id not in existing_records:
                                    with open(annotated_file_path, 'a', encoding='utf-8') as f:
                                        f.write(json.dumps(annotated_record) + '\n')
                            
                            # Send response
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
                            print(f"Notes saved to {file_path}")
                            print(f"Annotated record appended to {annotated_file_path}")
                            
                        elif self.path == '/save_notes_file':
                            # Handle multipart form data
                            import cgi
                            import io
                            
                            # Parse the multipart form data
                            environ = {'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
                            form = cgi.FieldStorage(fp=io.BytesIO(post_data), headers=self.headers, environ=environ)
                            
                            # Get the notes file
                            if 'notes' in form:
                                notes_data = form['notes'].file.read().decode('utf-8')
                                file_path = form.getvalue('filePath', notes_file)
                                
                                # Write the notes to the file
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(notes_data)
                                
                                # Send response
                                self.send_response(200)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
                                print(f"Notes saved to {file_path}")
                            else:
                                # Send error response
                                self.send_response(400)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps({'success': False, 'error': 'No notes file provided'}).encode('utf-8'))
                        
                    except Exception as e:
                        # Send error response
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
                        print(f"Error saving notes: {e}")
                else:
                    # Send error response for unknown paths
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'error': 'Not found'}).encode('utf-8'))
        
        # Use the custom handler
        httpd = socketserver.TCPServer(("", port), NotesHandler)
        
        print(f"Server started at http://localhost:{port}")
        print(f"Notes will be automatically saved to {notes_file_relative}")
        print(f"Annotated records will be automatically saved to {annotated_jsonl_file_relative}")
        httpd.serve_forever()
        
        return html_file, port
    except Exception as e:
        raise ValueError(f"Error creating visual failure analysis UI: {e}")

def _generate_html_ui(records, notes_file, annotated_jsonl_file):
    """Generate HTML content for the visual failure analysis UI.
    
    Args:
        records: List of records from the JSONL file
        notes_file: Path to the notes JSON file
        annotated_jsonl_file: Path to the annotated JSONL file
        
    Returns:
        HTML content as a string
    """
    # Load existing notes if available
    notes = {}
    try:
        with open(notes_file, 'r', encoding='utf-8') as f:
            notes = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    # Use relative paths for the HTML content
    notes_file_relative = os.path.basename(notes_file)
    annotated_jsonl_file_relative = os.path.basename(annotated_jsonl_file)
    
    # Create the HTML content
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Failure Analysis</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .controls {{
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .record-nav {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .record-count {{
            font-weight: bold;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }}
        button:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
        .record {{
            margin-bottom: 20px;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
        }}
        .field {{
            margin-bottom: 15px;
        }}
        .field-label {{
            font-weight: bold;
            margin-bottom: 5px;
            color: #555;
        }}
        .field-value {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 3px;
            border: 1px solid #eee;
            white-space: pre-wrap;
            overflow-x: auto;
        }}
        textarea {{
            width: 100%;
            height: 150px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
            resize: vertical;
        }}
        .search-container {{
            margin-bottom: 20px;
        }}
        #searchInput {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
            margin-bottom: 10px;
        }}
        .filter-container {{
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .filter-option {{
            padding: 5px 10px;
            background-color: #eee;
            border-radius: 3px;
            cursor: pointer;
        }}
        .filter-option.active {{
            background-color: #4CAF50;
            color: white;
        }}
        .hidden {{
            display: none;
        }}
        .status-bar {{
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 3px;
            margin-top: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Visual Failure Analysis</h1>
        
        <div class="search-container">
            <input type="text" id="searchInput" placeholder="Search in examples, gold answers, or predictions...">
            <div class="filter-container">
                <div class="filter-option active" data-filter="all">All Records</div>
                <div class="filter-option" data-filter="with-notes">With Notes</div>
                <div class="filter-option" data-filter="without-notes">Without Notes</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="record-nav">
                <button id="prevBtn">Previous</button>
                <span class="record-count">Record <span id="currentRecord">1</span> of <span id="totalRecords">{len(records)}</span></span>
                <button id="nextBtn">Next</button>
            </div>
            <button id="saveBtn">Save Notes</button>
        </div>
        
        <div id="recordsContainer">
            <!-- Records will be inserted here by JavaScript -->
        </div>
        
        <div class="status-bar" id="statusBar"></div>
    </div>
    
    <script>
        // Store all records and notes
        const allRecords = {json.dumps(records)};
        let notes = {json.dumps(notes)};
        const notesFilePath = "{notes_file_relative}";
        const annotatedJsonlFilePath = "{annotated_jsonl_file_relative}";
        
        // Current record index
        let currentIndex = 0;
        let filteredRecords = [...allRecords];
        
        // Initialize the UI when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {{
            initUI();
        }});
        
        // Initialize the UI
        function initUI() {{
            console.log("Initializing UI with", allRecords.length, "records");
            
            // Try to load notes from local storage
            try {{
                const savedNotes = localStorage.getItem('visual_analysis_notes');
                if (savedNotes) {{
                    const parsedNotes = JSON.parse(savedNotes);
                    if (parsedNotes && typeof parsedNotes === 'object') {{
                        notes = parsedNotes;
                        console.log("Loaded notes from local storage");
                    }}
                }}
            }} catch (error) {{
                console.error("Error loading notes from local storage:", error);
            }}
            
            // Set up event listeners
            setupEventListeners();
            
            // Initial render
            renderCurrentRecord();
            updateNavButtons();
            
            console.log("UI initialized successfully");
        }}
        
        // Set up all event listeners
        function setupEventListeners() {{
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            const saveBtn = document.getElementById('saveBtn');
            const searchInput = document.getElementById('searchInput');
            const filterOptions = document.querySelectorAll('.filter-option');
            
            // Navigation buttons
            prevBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                console.log("Previous button clicked, currentIndex:", currentIndex);
                showPreviousRecord();
            }});
            
            nextBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                console.log("Next button clicked, currentIndex:", currentIndex, "filteredRecords.length:", filteredRecords.length);
                showNextRecord();
            }});
            
            // Save button
            saveBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                console.log("Save button clicked");
                saveNotes();
            }});
            
            // Search input
            searchInput.addEventListener('input', filterRecords);
            
            // Filter options
            filterOptions.forEach(option => {{
                option.addEventListener('click', function() {{
                    // Remove active class from all options
                    filterOptions.forEach(opt => opt.classList.remove('active'));
                    // Add active class to clicked option
                    this.classList.add('active');
                    // Apply filter
                    applyFilter(this.dataset.filter);
                }});
            }});
            
            // Keyboard navigation
            document.addEventListener('keydown', function(event) {{
                if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {{
                    event.preventDefault();
                    showNextRecord();
                }} else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {{
                    event.preventDefault();
                    showPreviousRecord();
                }}
            }});
            
            // Notes textarea change event for auto-save
            document.addEventListener('input', function(event) {{
                if (event.target && event.target.id === 'notesTextarea') {{
                    // Auto-save after a short delay
                    clearTimeout(event.target.saveTimeout);
                    event.target.saveTimeout = setTimeout(() => {{
                        saveCurrentNotes();
                        saveNotesToFile();
                    }}, 1000); // 1 second delay
                }}
            }});
        }}
        
        // Show previous record
        function showPreviousRecord() {{
            if (currentIndex > 0) {{
                saveCurrentNotes();
                saveNotesToFile(); // Auto-save to file when navigating
                currentIndex--;
                console.log("Moving to previous record, new index:", currentIndex);
                renderCurrentRecord();
                updateNavButtons();
            }} else {{
                console.log("Cannot move to previous record: already at first record");
            }}
        }}
        
        // Show next record
        function showNextRecord() {{
            if (currentIndex < filteredRecords.length - 1) {{
                saveCurrentNotes();
                saveNotesToFile(); // Auto-save to file when navigating
                currentIndex++;
                console.log("Moving to next record, new index:", currentIndex);
                renderCurrentRecord();
                updateNavButtons();
            }} else {{
                console.log("Cannot move to next record: already at last record");
                console.log("Current index:", currentIndex, "Filtered records length:", filteredRecords.length);
            }}
        }}
        
        // Update navigation buttons state
        function updateNavButtons() {{
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            const hasRecords = filteredRecords.length > 0;
            
            prevBtn.disabled = !hasRecords || currentIndex === 0;
            nextBtn.disabled = !hasRecords || currentIndex >= filteredRecords.length - 1;
            
            console.log("Navigation buttons updated - Previous disabled:", prevBtn.disabled, "Next disabled:", nextBtn.disabled);
            console.log("Current index:", currentIndex, "Total filtered records:", filteredRecords.length);
        }}
        
        // Render the current record
        function renderCurrentRecord() {{
            const recordsContainer = document.getElementById('recordsContainer');
            const currentRecordSpan = document.getElementById('currentRecord');
            const totalRecordsSpan = document.getElementById('totalRecords');
            
            if (filteredRecords.length === 0) {{
                recordsContainer.innerHTML = '<div class="record"><p>No records match your search criteria.</p></div>';
                currentRecordSpan.textContent = '0';
                totalRecordsSpan.textContent = '0';
                return;
            }}
            
            // Ensure currentIndex is within bounds
            if (currentIndex >= filteredRecords.length) {{
                currentIndex = filteredRecords.length - 1;
            }}
            if (currentIndex < 0) {{
                currentIndex = 0;
            }}
            
            const record = filteredRecords[currentIndex];
            const recordId = getRecordId(record);
            const noteContent = notes[recordId] || '';
            
            let html = '<div class="record">';
            
            // Add each field from the record
            for (const [key, value] of Object.entries(record)) {{
                if (key === 'example' || key === 'gold' || key === 'predictions' || 
                    key === 'query' || key === 'response') {{
                    html += `
                        <div class="field">
                            <div class="field-label">${{key.charAt(0).toUpperCase() + key.slice(1)}}:</div>
                            <div class="field-value">${{formatValue(value)}}</div>
                        </div>
                    `;
                }}
            }}
            
            // Add notes textarea
            html += `
                <div class="field">
                    <div class="field-label">Notes:</div>
                    <textarea id="notesTextarea" placeholder="Add your analysis notes here...">${{noteContent}}</textarea>
                </div>
            `;
            
            html += '</div>';
            
            recordsContainer.innerHTML = html;
            currentRecordSpan.textContent = (currentIndex + 1).toString();
            totalRecordsSpan.textContent = filteredRecords.length.toString();
            
            console.log("Rendered record", (currentIndex + 1), "of", filteredRecords.length);
        }}
        
        // Format value for display
        function formatValue(value) {{
            if (typeof value === 'string') {{
                return value.replace(/\\n/g, '<br>').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }} else if (value === null || value === undefined) {{
                return '';
            }} else if (typeof value === 'object') {{
                return JSON.stringify(value, null, 2).replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }} else {{
                return value.toString().replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }}
        }}
        
        // Get a unique ID for the record
        function getRecordId(record) {{
            // Try to use existing ID fields, or create a hash from the content
            if (record.id) return record.id;
            if (record.example_id) return record.example_id;
            
            // Create a simple hash from the example content
            let content = '';
            if (record.example) content += record.example;
            if (record.gold) content += record.gold;
            if (record.query) content += record.query;
            return btoa(unescape(encodeURIComponent(content))).substring(0, 20);
        }}
        
        // Save the current notes to the notes object
        function saveCurrentNotes() {{
            if (filteredRecords.length === 0) return;
            
            const textarea = document.getElementById('notesTextarea');
            if (textarea) {{
                const record = filteredRecords[currentIndex];
                const recordId = getRecordId(record);
                notes[recordId] = textarea.value;
            }}
        }}
        
        // Save all notes
        function saveNotes() {{
            saveCurrentNotes();
            saveNotesToFile();
            const statusBar = document.getElementById('statusBar');
            
            try {{
                // Save notes to local storage as a backup
                localStorage.setItem('visual_analysis_notes', JSON.stringify(notes));
                
                statusBar.textContent = 'Notes saved to local storage and file!';
                statusBar.style.backgroundColor = '#d4edda';
                statusBar.style.color = '#155724';
                
                // Clear the status message after a few seconds
                setTimeout(() => {{
                    statusBar.textContent = '';
                    statusBar.style.backgroundColor = '#f0f0f0';
                    statusBar.style.color = '';
                }}, 3000);
            }} catch (error) {{
                console.error("Save error:", error);
                statusBar.textContent = 'Error saving notes: ' + error.message;
                statusBar.style.backgroundColor = '#f8d7da';
                statusBar.style.color = '#721c24';
            }}
        }}
        
        // Save notes to file using fetch API
        function saveNotesToFile() {{
            try {{
                // Get the current record to include in the saved data
                const currentRecord = filteredRecords[currentIndex];
                const recordId = getRecordId(currentRecord);
                
                // Create a Blob with the notes JSON
                const notesBlob = new Blob([JSON.stringify(notes, null, 2)], {{type: 'application/json'}});
                
                // Create a FormData object
                const formData = new FormData();
                formData.append('notes', notesBlob, 'analysis_notes.json');
                formData.append('filePath', notesFilePath);
                
                // Use the fetch API to send the notes to the server
                fetch('/save_notes_file', {{
                    method: 'POST',
                    body: formData
                }})
                .then(response => {{
                    console.log("Notes auto-saved to file");
                }})
                .catch(error => {{
                    console.log("Auto-save to file failed (expected in static mode):", error);
                }});
                
                // Also save to the actual file path using a server-side endpoint
                // This will also append the annotated record to the JSONL file
                fetch('/write_notes_to_file', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        notes: notes,
                        filePath: notesFilePath,
                        annotatedFilePath: annotatedJsonlFilePath,
                        record: currentRecord,  // Include the current record data
                        recordId: recordId      // Include the record ID
                    }})
                }})
                .then(response => {{
                    console.log("Notes saved to file via server endpoint");
                }})
                .catch(error => {{
                    console.log("Server endpoint save failed (expected if no server):", error);
                }});
                
            }} catch (error) {{
                console.error("Error in saveNotesToFile:", error);
            }}
        }}
        
        // Filter records based on search input
        function filterRecords() {{
            const searchInput = document.getElementById('searchInput');
            const searchTerm = searchInput.value.toLowerCase();
            const activeFilter = document.querySelector('.filter-option.active').dataset.filter;
            
            // Apply both search term and active filter
            applyFilter(activeFilter, searchTerm);
        }}
        
        // Apply filter to records
        function applyFilter(filterType, searchTerm = '') {{
            const searchInput = document.getElementById('searchInput');
            if (!searchTerm) {{
                searchTerm = searchInput.value.toLowerCase();
            }}
            
            // First filter by notes
            let filtered = [...allRecords];
            
            if (filterType === 'with-notes') {{
                filtered = filtered.filter(record => {{
                    const recordId = getRecordId(record);
                    return notes[recordId] && notes[recordId].trim() !== '';
                }});
            }} else if (filterType === 'without-notes') {{
                filtered = filtered.filter(record => {{
                    const recordId = getRecordId(record);
                    return !notes[recordId] || notes[recordId].trim() === '';
                }});
            }}
            
            // Then filter by search term
            if (searchTerm) {{
                filtered = filtered.filter(record => {{
                    // Search in example, gold, and predictions
                    const example = record.example ? record.example.toLowerCase() : '';
                    const gold = record.gold ? record.gold.toLowerCase() : '';
                    const query = record.query ? record.query.toLowerCase() : '';
                    const response = record.response ? record.response.toLowerCase() : '';
                    const predictions = record.predictions ? 
                        (typeof record.predictions === 'string' ? 
                            record.predictions.toLowerCase() : 
                            JSON.stringify(record.predictions).toLowerCase()) 
                        : '';
                    
                    return example.includes(searchTerm) || 
                        gold.includes(searchTerm) || 
                        query.includes(searchTerm) ||
                        response.includes(searchTerm) ||
                        predictions.includes(searchTerm);
                }});
            }}
            
            filteredRecords = filtered;
            currentIndex = 0;
            renderCurrentRecord();
            updateNavButtons();
            
            console.log("Filter applied: " + filterType + ", search: '" + searchTerm + 
                    "', filtered records: " + filteredRecords.length);
        }}
    </script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a visual failure analysis UI for JSONL inference results.")
    parser.add_argument("jsonl_file", help="Path to the JSONL file containing inference results")
    parser.add_argument("--output-dir", help="Directory to store the HTML UI files")
    parser.add_argument("--port", type=int, default=8000, help="Port to use for the HTTP server")
    
    args = parser.parse_args()
    
    try:
        create_visual_failure_analysis(args.jsonl_file, args.output_dir, args.port)
    except Exception as e:
        print(f"Error: {e}")
