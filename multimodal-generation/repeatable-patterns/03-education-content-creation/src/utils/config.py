"""
Configuration Module

Grade level configurations and system settings for educational content generation.
"""

# Grade Level Configuration System
GRADE_LEVEL_CONFIGS = {
    "elementary": {
        "grades": [1, 2, 3, 4, 5],
        "age_range": "6-11 years",
        "vocabulary_level": "basic",
        "sentence_complexity": "simple",
        "visual_emphasis": "high",
        "activity_duration": "15-20 minutes",
        "reading_level": "elementary",
        "max_bullets_per_slide": 3,
        "font_size": 24
    },
    "middle_school": {
        "grades": [6, 7, 8],
        "age_range": "11-14 years",
        "vocabulary_level": "intermediate",
        "sentence_complexity": "compound",
        "visual_emphasis": "medium",
        "activity_duration": "25-35 minutes",
        "reading_level": "middle_school",
        "max_bullets_per_slide": 4,
        "font_size": 20
    },
    "high_school": {
        "grades": [9, 10, 11, 12],
        "age_range": "14-18 years",
        "vocabulary_level": "advanced",
        "sentence_complexity": "complex",
        "visual_emphasis": "low",
        "activity_duration": "45-50 minutes",
        "reading_level": "high_school",
        "max_bullets_per_slide": 5,
        "font_size": 18
    },
    "undergraduate": {
        "grades": [13, 14, 15, 16],
        "age_range": "18-22 years",
        "vocabulary_level": "academic",
        "sentence_complexity": "sophisticated",
        "visual_emphasis": "minimal",
        "activity_duration": "60-90 minutes",
        "reading_level": "undergraduate",
        "max_bullets_per_slide": 6,
        "font_size": 16
    },
    "graduate": {
        "grades": [17, 18, 19, 20],
        "age_range": "22+ years",
        "vocabulary_level": "professional",
        "sentence_complexity": "complex_academic",
        "visual_emphasis": "data_focused",
        "activity_duration": "90-120 minutes",
        "reading_level": "graduate",
        "max_bullets_per_slide": 7,
        "font_size": 14
    }
}


def get_grade_level_category(grade):
    """Determine the category (elementary, middle_school, high_school) for a given grade."""
    for category, config in GRADE_LEVEL_CONFIGS.items():
        if grade in config["grades"]:
            return category
    return "high_school"  # Default fallback


# System Configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_MODELS = {
    "content_generation": "us.amazon.nova-premier-v1:0",
    "image_optimization": "amazon.nova-pro-v1:0",
    "image_generation": "amazon.nova-canvas-v1:0"
}

# Rate limiting settings
RATE_LIMITS = {
    "nova_pro": 30,  # seconds between requests
    "nova_canvas": 30,  # seconds between requests
    "nova_premier": 5   # seconds between requests
}

# Content generation settings
CONTENT_SETTINGS = {
    "max_prompt_length": 8000,
    "max_response_length": 4000,
    "temperature": 0.2,
    "max_retries": 3
}

# Image generation settings
IMAGE_SETTINGS = {
    "default_width": 512,
    "default_height": 512,
    "quality": "standard",
    "max_prompt_length": 200
}
