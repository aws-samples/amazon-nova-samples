"""
Content Analyzer Module

Analyzes generated content for age-appropriateness, quality, readability,
and educational standards alignment.
"""

import re
import logging
from datetime import datetime

# Handle optional dependencies gracefully
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyze generated content for age-appropriateness and quality."""
    
    def __init__(self):
        self.grade_reading_levels = {
            1: (1, 2), 2: (2, 3), 3: (3, 4), 4: (4, 5), 5: (5, 6),
            6: (6, 7), 7: (7, 8), 8: (8, 9),
            9: (9, 10), 10: (10, 11), 11: (11, 12), 12: (12, 13)
        }
    
    def analyze_content_quality(self, content, target_grade, standards=None):
        """Comprehensive content quality analysis."""
        if not content or not isinstance(content, str):
            return {"error": "Invalid content provided"}
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "target_grade": target_grade,
            "content_length": len(content),
            "word_count": len(content.split()),
            "readability": self.analyze_readability(content, target_grade),
            "vocabulary": self.analyze_vocabulary(content, target_grade),
            "structure": self.analyze_structure(content),
            "age_appropriateness": self.assess_age_appropriateness(content, target_grade),
            "standards_alignment": self.assess_standards_alignment(content, standards) if standards else None
        }
        
        # Overall quality score (0-100)
        analysis["overall_quality_score"] = self.calculate_quality_score(analysis)
        
        return analysis
    
    def analyze_readability(self, content, target_grade):
        """Analyze readability metrics."""
        if not TEXTSTAT_AVAILABLE:
            return {"error": "textstat library not available - install with: pip install textstat"}
            
        try:
            flesch_score = textstat.flesch_reading_ease(content)
            flesch_grade = textstat.flesch_kincaid_grade(content)
            automated_readability = textstat.automated_readability_index(content)
            
            target_range = self.grade_reading_levels.get(target_grade, (target_grade, target_grade + 1))
            
            return {
                "flesch_reading_ease": flesch_score,
                "flesch_kincaid_grade": flesch_grade,
                "automated_readability_index": automated_readability,
                "target_grade_range": target_range,
                "grade_appropriate": target_range[0] <= flesch_grade <= target_range[1] + 2,
                "readability_assessment": self.get_readability_assessment(flesch_score)
            }
        except Exception as e:
            return {"error": f"Readability analysis failed: {str(e)}"}
    
    def get_readability_assessment(self, flesch_score):
        """Convert Flesch score to readability assessment."""
        if flesch_score >= 90:
            return "Very Easy"
        elif flesch_score >= 80:
            return "Easy"
        elif flesch_score >= 70:
            return "Fairly Easy"
        elif flesch_score >= 60:
            return "Standard"
        elif flesch_score >= 50:
            return "Fairly Difficult"
        elif flesch_score >= 30:
            return "Difficult"
        else:
            return "Very Difficult"
    
    def analyze_vocabulary(self, content, target_grade):
        """Analyze vocabulary complexity."""
        try:
            if NLTK_AVAILABLE:
                words = nltk.word_tokenize(content.lower())
                words = [word for word in words if word.isalpha()]
            else:
                # Simple fallback tokenization
                words = [word.lower() for word in re.findall(r'\b[a-zA-Z]+\b', content)]
            
            # Basic vocabulary analysis
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            unique_words = len(set(words))
            vocabulary_diversity = unique_words / len(words) if words else 0
            
            return {
                "total_words": len(words),
                "unique_words": unique_words,
                "vocabulary_diversity": vocabulary_diversity,
                "average_word_length": avg_word_length,
                "complexity_appropriate": self.assess_vocabulary_complexity(avg_word_length, target_grade)
            }
        except Exception as e:
            return {"error": f"Vocabulary analysis failed: {str(e)}"}
    
    def assess_vocabulary_complexity(self, avg_word_length, target_grade):
        """Assess if vocabulary complexity is appropriate for grade level."""
        from ..utils.config import get_grade_level_category
        
        grade_category = get_grade_level_category(target_grade)
        
        if grade_category == "elementary":
            return 3.0 <= avg_word_length <= 5.5
        elif grade_category == "middle_school":
            return 4.0 <= avg_word_length <= 6.5
        else:  # high_school
            return 4.5 <= avg_word_length <= 8.0
    
    def analyze_structure(self, content):
        """Analyze content structure and organization."""
        try:
            if NLTK_AVAILABLE:
                sentences = nltk.sent_tokenize(content)
            else:
                # Simple sentence splitting fallback
                sentences = re.split(r'[.!?]+', content)
                sentences = [s.strip() for s in sentences if s.strip()]
                
            avg_sentence_length = sum(len(sentence.split()) for sentence in sentences) / len(sentences) if sentences else 0
            
            return {
                "sentence_count": len(sentences),
                "average_sentence_length": avg_sentence_length,
                "has_bullet_points": '•' in content or '-' in content,
                "has_questions": '?' in content,
                "structure_score": min(100, max(0, 100 - abs(avg_sentence_length - 15) * 2))  # Optimal around 15 words
            }
        except Exception as e:
            return {"error": f"Structure analysis failed: {str(e)}"}
    
    def assess_age_appropriateness(self, content, target_grade):
        """Assess age appropriateness of content."""
        from ..utils.config import get_grade_level_category, GRADE_LEVEL_CONFIGS
        
        grade_category = get_grade_level_category(target_grade)
        config = GRADE_LEVEL_CONFIGS[grade_category]
        
        # Check for age-inappropriate content
        inappropriate_topics = [
            'violence', 'death', 'drugs', 'alcohol', 'weapons',
            'mature themes', 'adult content'
        ]
        
        content_lower = content.lower()
        found_inappropriate = [topic for topic in inappropriate_topics if topic in content_lower]
        
        return {
            "grade_category": grade_category,
            "target_age_range": config["age_range"],
            "inappropriate_content_found": found_inappropriate,
            "is_age_appropriate": len(found_inappropriate) == 0,
            "engagement_level": self.assess_engagement_level(content, grade_category)
        }
    
    def assess_engagement_level(self, content, grade_category):
        """Assess how engaging the content is for the target age group."""
        engagement_indicators = {
            "elementary": ['fun', 'play', 'game', 'story', 'picture', 'color', 'imagine'],
            "middle_school": ['explore', 'discover', 'experiment', 'challenge', 'project', 'team'],
            "high_school": ['analyze', 'evaluate', 'research', 'debate', 'career', 'future', 'real-world']
        }
        
        indicators = engagement_indicators.get(grade_category, [])
        content_lower = content.lower()
        found_indicators = [indicator for indicator in indicators if indicator in content_lower]
        
        return {
            "engagement_indicators_found": found_indicators,
            "engagement_score": min(100, len(found_indicators) * 20)
        }
    
    def assess_standards_alignment(self, content, standards):
        """Assess alignment with educational standards."""
        if not standards:
            return None
        
        # This is a simplified implementation
        # In a real system, this would use a comprehensive standards database
        alignment_score = 0
        content_lower = content.lower()
        
        for standard in standards:
            # Simple keyword matching (would be more sophisticated in practice)
            if any(keyword in content_lower for keyword in standard.get('keywords', [])):
                alignment_score += 1
        
        return {
            "standards_checked": len(standards),
            "standards_aligned": alignment_score,
            "alignment_percentage": (alignment_score / len(standards)) * 100 if standards else 0
        }
    
    def calculate_quality_score(self, analysis):
        """Calculate overall quality score based on various metrics."""
        score = 0
        
        # Readability score (30%)
        if 'readability' in analysis and 'grade_appropriate' in analysis['readability']:
            score += 30 if analysis['readability']['grade_appropriate'] else 10
        
        # Vocabulary appropriateness (25%)
        if 'vocabulary' in analysis and 'complexity_appropriate' in analysis['vocabulary']:
            score += 25 if analysis['vocabulary']['complexity_appropriate'] else 10
        
        # Structure quality (20%)
        if 'structure' in analysis and 'structure_score' in analysis['structure']:
            score += (analysis['structure']['structure_score'] / 100) * 20
        
        # Age appropriateness (25%)
        if 'age_appropriateness' in analysis and 'is_age_appropriate' in analysis['age_appropriateness']:
            score += 25 if analysis['age_appropriateness']['is_age_appropriate'] else 0
        
        return min(100, max(0, score))
