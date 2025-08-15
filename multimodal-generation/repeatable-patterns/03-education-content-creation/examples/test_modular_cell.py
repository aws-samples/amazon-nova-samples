"""
Test Modular Cell - Demonstrates the new modular architecture

This replaces a complex notebook cell with clean imports and simple function calls.
"""

# Import our new modular components
from src.core.token_counter import create_token_counter
from src.core.bedrock_client import create_bedrock_client
from src.utils.config import GRADE_LEVEL_CONFIGS, get_grade_level_category
from src.utils.standards import StandardsDatabase
from src.content.analyzer import ContentAnalyzer

def initialize_system():
    """Initialize all system components - replaces complex initialization cell."""
    print("🚀 Initializing Enhanced Curriculum System...")
    
    # Create token counter
    token_counter = create_token_counter()
    print("✅ Token Counter initialized")
    
    # Create standards database
    standards_db = StandardsDatabase()
    print("✅ Standards Database initialized")
    
    # Create content analyzer
    content_analyzer = ContentAnalyzer()
    print("✅ Content Analyzer initialized")
    
    print(f"📊 System ready with {len(GRADE_LEVEL_CONFIGS)} grade level configurations")
    
    return {
        'token_counter': token_counter,
        'standards_db': standards_db,
        'content_analyzer': content_analyzer
    }

def demonstrate_grade_level_config(grade_level=8):
    """Demonstrate grade level configuration - replaces complex config cell."""
    print(f"🎓 Grade Level Configuration for Grade {grade_level}")
    
    category = get_grade_level_category(grade_level)
    config = GRADE_LEVEL_CONFIGS[category]
    
    print(f"   Category: {category}")
    print(f"   Age Range: {config['age_range']}")
    print(f"   Vocabulary Level: {config['vocabulary_level']}")
    print(f"   Max Bullets: {config['max_bullets_per_slide']}")
    print(f"   Font Size: {config['font_size']}pt")
    
    return category, config

def demonstrate_standards_lookup(grade_level=8, subject="mathematics"):
    """Demonstrate standards lookup - replaces complex standards cell."""
    print(f"📚 Educational Standards for Grade {grade_level} {subject.title()}")
    
    standards_db = StandardsDatabase()
    standards = standards_db.get_standards_for_grade(grade_level, subject)
    
    print(f"   Found {len(standards)} standards:")
    for standard in standards[:3]:  # Show first 3
        print(f"   • {standard['code']}: {standard['description'][:60]}...")
    
    return standards

def demonstrate_content_analysis(sample_content, grade_level=8):
    """Demonstrate content analysis - replaces complex analysis cell."""
    print(f"🔍 Content Analysis for Grade {grade_level}")
    
    analyzer = ContentAnalyzer()
    analysis = analyzer.analyze_content_quality(sample_content, grade_level)
    
    print(f"   Content Length: {analysis['content_length']} characters")
    print(f"   Word Count: {analysis['word_count']} words")
    print(f"   Quality Score: {analysis['overall_quality_score']}/100")
    
    if 'readability' in analysis and 'readability_assessment' in analysis['readability']:
        print(f"   Readability: {analysis['readability']['readability_assessment']}")
    
    return analysis

def main():
    """Main demonstration function - replaces multiple complex cells."""
    print("=" * 60)
    print("🎯 ENHANCED CURRICULUM SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    # Initialize system (replaces Cell 1: Complex initialization)
    components = initialize_system()
    print()
    
    # Demonstrate grade configuration (replaces Cell 2: Grade selection)
    category, config = demonstrate_grade_level_config(8)
    print()
    
    # Demonstrate standards lookup (replaces Cell 3: Standards retrieval)
    standards = demonstrate_standards_lookup(8, "mathematics")
    print()
    
    # Demonstrate content analysis (replaces Cell 4: Content analysis)
    sample_content = """
    Exponents are mathematical expressions that show repeated multiplication. 
    When we have a number like 2^3, it means 2 × 2 × 2 = 8. 
    The base is 2 and the exponent is 3. 
    Understanding exponents helps us work with very large and very small numbers efficiently.
    """
    
    analysis = demonstrate_content_analysis(sample_content, 8)
    print()
    
    print("✅ Demonstration complete!")
    print("💡 Each function above replaces a complex notebook cell with clean, modular code.")
    
    return {
        'components': components,
        'config': config,
        'standards': standards,
        'analysis': analysis
    }

if __name__ == "__main__":
    results = main()
