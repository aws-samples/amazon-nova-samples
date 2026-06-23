"""
UI Widgets Module

Interactive widgets for grade selection, subject selection, and configuration.
"""

import logging

# Handle optional dependencies gracefully
try:
    import ipywidgets as widgets
    from IPython.display import display, HTML
    WIDGETS_AVAILABLE = True
except ImportError:
    WIDGETS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class GradeSelector:
    """Enhanced grade selector with automatic configuration updates."""
    
    def __init__(self, default_grade=8):
        if not WIDGETS_AVAILABLE:
            raise ImportError("ipywidgets not available - install with: pip install ipywidgets")
        
        self.default_grade = default_grade
        self.grade_configs = self._initialize_grade_configs()
        self._create_widgets()
        self._setup_observers()
        
    def _initialize_grade_configs(self):
        """Initialize grade configuration data."""
        return {
            1: {"category": "Elementary", "age": "6-7 years", "level": "Basic"},
            2: {"category": "Elementary", "age": "7-8 years", "level": "Basic"},
            3: {"category": "Elementary", "age": "8-9 years", "level": "Basic"},
            4: {"category": "Elementary", "age": "9-10 years", "level": "Basic"},
            5: {"category": "Elementary", "age": "10-11 years", "level": "Basic"},
            6: {"category": "Middle School", "age": "11-12 years", "level": "Intermediate"},
            7: {"category": "Middle School", "age": "12-13 years", "level": "Intermediate"},
            8: {"category": "Middle School", "age": "13-14 years", "level": "Intermediate"},
            9: {"category": "High School", "age": "14-15 years", "level": "Advanced"},
            10: {"category": "High School", "age": "15-16 years", "level": "Advanced"},
            11: {"category": "High School", "age": "16-17 years", "level": "Advanced"},
            12: {"category": "High School", "age": "17-18 years", "level": "Advanced"},
            13: {"category": "University Freshman", "age": "18-19 years", "level": "Expert"},
            14: {"category": "University Sophomore", "age": "19-20 years", "level": "Expert"},
            15: {"category": "University Junior", "age": "20-21 years", "level": "Expert"},
            16: {"category": "University Senior", "age": "21-22 years", "level": "Expert"},
            17: {"category": "Graduate", "age": "22+ years", "level": "Professional"},
            18: {"category": "Graduate", "age": "22+ years", "level": "Professional"},
            19: {"category": "Graduate", "age": "22+ years", "level": "Professional"},
            20: {"category": "Graduate", "age": "22+ years", "level": "Professional"}
        }
    
    def _create_widgets(self):
        """Create the grade selector widgets."""
        self.grade_selector = widgets.IntSlider(
            value=self.default_grade,
            min=1,
            max=20,
            step=1,
            description='Grade Level:',
            style={'description_width': '100px'}
        )
        
        self.subject_selector = widgets.Dropdown(
            options=['mathematics', 'science', 'english', 'social_studies'],
            value='mathematics',
            description='Subject:',
            style={'description_width': '100px'}
        )
        
        self.standards_selector = widgets.Dropdown(
            options=['common_core_math', 'ngss', 'common_core_ela'],
            value='common_core_math',
            description='Standards:',
            style={'description_width': '100px'}
        )
        
        self.grade_info = widgets.HTML(value="")
        
        # Create main container
        self.container = widgets.VBox([
            widgets.HTML('<h3 style="color: #2e86ab;">📚 Course Configuration</h3>'),
            widgets.HTML('<p>Select your target grade level and subject:</p>'),
            self.grade_selector,
            self.subject_selector,
            self.standards_selector,
            self.grade_info
        ], layout=widgets.Layout(
            border='2px solid #e8f4fd',
            border_radius='10px',
            padding='20px',
            margin='10px 0'
        ))
    
    def _setup_observers(self):
        """Set up widget observers for automatic updates."""
        self.grade_selector.observe(self._update_grade_info, names='value')
        
        # Initialize display
        self._update_grade_info({'new': self.grade_selector.value})
    
    def _update_grade_info(self, change):
        """Update grade information display when grade changes."""
        grade = change['new']
        config = self.grade_configs.get(grade, {
            "category": "Unknown", 
            "age": "Unknown", 
            "level": "Unknown"
        })
        
        info_html = f"""
        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <h4 style="color: #2e86ab; margin-top: 0;">📊 Grade {grade} Information</h4>
            <p><strong>Category:</strong> {config['category']}</p>
            <p><strong>Age Range:</strong> {config['age']}</p>
            <p><strong>Complexity Level:</strong> {config['level']}</p>
        </div>
        """
        self.grade_info.value = info_html
    
    def display(self):
        """Display the grade selector widget."""
        display(self.container)
        
        print(f"✅ Grade selector created successfully!")
        print(f"📊 Current selection: Grade {self.value}, {self.subject}")
    
    @property
    def value(self):
        """Get current grade level value."""
        return self.grade_selector.value
    
    @property
    def subject(self):
        """Get current subject value."""
        return self.subject_selector.value
    
    @property
    def standards(self):
        """Get current standards value."""
        return self.standards_selector.value
    
    def get_selection(self):
        """Get all current selections as a dictionary."""
        return {
            'grade': self.value,
            'subject': self.subject,
            'standards': self.standards
        }


class FileUploader:
    """Enhanced file upload widget with validation and progress."""
    
    def __init__(self, accept='.pdf', multiple=False):
        if not WIDGETS_AVAILABLE:
            raise ImportError("ipywidgets not available - install with: pip install ipywidgets")
        
        self.accept = accept
        self.multiple = multiple
        self._create_widgets()
        self._setup_observers()
    
    def _create_widgets(self):
        """Create file upload widgets."""
        self.upload_widget = widgets.FileUpload(
            accept=self.accept,
            multiple=self.multiple,
            description='Upload File'
        )
        
        self.status_display = widgets.HTML(value="")
        self.progress_bar = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description='Progress:',
            style={'description_width': '80px'},
            layout=widgets.Layout(display='none')
        )
        
        self.container = widgets.VBox([
            widgets.HTML('<h3 style="color: #2e86ab;">📤 File Upload</h3>'),
            self.upload_widget,
            self.progress_bar,
            self.status_display
        ], layout=widgets.Layout(
            border='2px solid #e8f4fd',
            border_radius='10px',
            padding='20px',
            margin='10px 0'
        ))
    
    def _setup_observers(self):
        """Set up upload observers."""
        self.upload_widget.observe(self._on_upload, names='value')
    
    def _on_upload(self, change):
        """Handle file upload events."""
        uploaded_files = change['new']
        
        if not uploaded_files:
            self.status_display.value = ""
            self.progress_bar.layout.display = 'none'
            return
        
        # Show progress bar
        self.progress_bar.layout.display = 'block'
        self.progress_bar.value = 50
        
        # Process uploaded files
        file_info = []
        for filename, file_info_dict in uploaded_files.items():
            content = file_info_dict['content']
            size = len(content)
            
            file_info.append({
                'name': filename,
                'size': size,
                'content': content
            })
        
        # Update status
        self.progress_bar.value = 100
        
        if len(file_info) == 1:
            file = file_info[0]
            status_html = f"""
            <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #2d5a2d; margin-top: 0;">✅ File Uploaded Successfully</h4>
                <p><strong>Filename:</strong> {file['name']}</p>
                <p><strong>Size:</strong> {file['size']:,} bytes</p>
            </div>
            """
        else:
            status_html = f"""
            <div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #2d5a2d; margin-top: 0;">✅ {len(file_info)} Files Uploaded</h4>
                <ul>
                    {''.join(f'<li>{f["name"]} ({f["size"]:,} bytes)</li>' for f in file_info)}
                </ul>
            </div>
            """
        
        self.status_display.value = status_html
        
        # Hide progress bar after a delay
        import time
        time.sleep(1)
        self.progress_bar.layout.display = 'none'
    
    def display(self):
        """Display the file upload widget."""
        display(self.container)
        print("✅ File upload widget ready")
    
    @property
    def files(self):
        """Get uploaded files."""
        return self.upload_widget.value
    
    def get_file_content(self, filename=None):
        """Get content of uploaded file(s)."""
        if not self.files:
            return None
        
        if filename:
            return self.files.get(filename, {}).get('content')
        else:
            # Return first file if no filename specified
            first_file = next(iter(self.files.values()), {})
            return first_file.get('content')


def create_grade_selector(default_grade=8):
    """Factory function to create a grade selector."""
    return GradeSelector(default_grade)


def create_file_uploader(accept='.pdf', multiple=False):
    """Factory function to create a file uploader."""
    return FileUploader(accept, multiple)


def create_progress_display():
    """Create a progress display widget."""
    if not WIDGETS_AVAILABLE:
        return None
    
    progress_bar = widgets.IntProgress(
        value=0,
        min=0,
        max=100,
        description='Progress:',
        style={'description_width': '80px'}
    )
    
    status_text = widgets.HTML(value="Ready to start...")
    
    container = widgets.VBox([
        widgets.HTML('<h3 style="color: #2e86ab;">📊 Generation Progress</h3>'),
        progress_bar,
        status_text
    ], layout=widgets.Layout(
        border='2px solid #e8f4fd',
        border_radius='10px',
        padding='20px',
        margin='10px 0'
    ))
    
    return {
        'container': container,
        'progress_bar': progress_bar,
        'status_text': status_text,
        'display': lambda: display(container)
    }
