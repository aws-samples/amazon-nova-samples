"""
Clean Syllabus Extractor Utility

Pure Nova-based syllabus extraction with no fallbacks or mock data.
Ensures authentic demonstration of Nova's capabilities.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

# Handle optional dependencies gracefully
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from IPython.display import display, Markdown
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

from .text_sanitizer import sanitize_text

# Configure logging
logger = logging.getLogger(__name__)


class SyllabusExtractionError(Exception):
    """Custom exception for syllabus extraction errors."""
    pass


class CleanSyllabusExtractor:
    """
    Clean syllabus extraction system with no fallbacks or mock data.
    Guarantees pure Nova-generated content or clear error messages.
    """
    
    def __init__(self, bedrock_client=None):
        if not PDF_AVAILABLE:
            raise ImportError("PyMuPDF not available - install with: pip install PyMuPDF")
        
        self.bedrock_client = bedrock_client
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_topics_extracted': 0
        }
    
    def extract_topics(self, pdf_path: str, topic_count: int = 5, 
                      grade_level: int = 8, subject: str = "general",
                      custom_instructions: str = "") -> List[str]:
        """
        Extract topics from PDF using Nova with no fallbacks.
        
        Args:
            pdf_path: Path to PDF file
            topic_count: Number of topics to extract
            grade_level: Target grade level
            subject: Subject area
            custom_instructions: Additional instructions
            
        Returns:
            List of Nova-generated topics
            
        Raises:
            SyllabusExtractionError: If extraction fails for any reason
        """
        self.extraction_stats['total_extractions'] += 1
        
        # Validate inputs
        self._validate_inputs(pdf_path, topic_count)
        
        # Extract text from PDF
        pdf_text = self._extract_pdf_text(pdf_path)
        
        # Create Nova prompt
        prompt = self._create_extraction_prompt(
            pdf_text, topic_count, grade_level, subject, custom_instructions
        )
        
        # Get Nova response
        nova_response = self._call_nova(prompt, grade_level, subject)
        
        # Parse Nova response
        topics = self._parse_nova_response(nova_response, topic_count)
        
        # Validate and clean topics
        clean_topics = self._validate_and_clean_topics(topics, topic_count)
        
        self.extraction_stats['successful_extractions'] += 1
        self.extraction_stats['average_topics_extracted'] = (
            (self.extraction_stats['average_topics_extracted'] * 
             (self.extraction_stats['successful_extractions'] - 1) + len(clean_topics)) /
            self.extraction_stats['successful_extractions']
        )
        
        return clean_topics
    
    def _validate_inputs(self, pdf_path: str, topic_count: int) -> None:
        """Validate input parameters."""
        if not self.bedrock_client:
            raise SyllabusExtractionError(
                "Bedrock client not initialized. Please run the authentication section first."
            )
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise SyllabusExtractionError(
                "PDF file not found. Please upload a valid PDF file first."
            )
        
        if not isinstance(topic_count, int) or topic_count < 1 or topic_count > 20:
            raise SyllabusExtractionError(
                f"Invalid topic count: {topic_count}. Must be between 1 and 20."
            )
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            
            for page in doc:
                all_text += page.get_text()
            
            doc.close()
            
            if not all_text.strip():
                raise SyllabusExtractionError(
                    "PDF appears to be empty or contains no extractable text."
                )
            
            print(f"📄 Extracted {len(all_text):,} characters from PDF")
            return all_text
            
        except Exception as e:
            raise SyllabusExtractionError(f"Failed to extract text from PDF: {str(e)}")
    
    def _create_extraction_prompt(self, pdf_text: str, topic_count: int, 
                                grade_level: int, subject: str, 
                                custom_instructions: str) -> str:
        """Create optimized Nova prompt for topic extraction."""
        # Limit text to prevent token overflow
        text_sample = pdf_text[:10000]
        
        prompt = f"""Based on this document, identify exactly {topic_count} main topics and list them separated by commas.

DOCUMENT CONTENT:
{text_sample}

INSTRUCTIONS:
- Identify exactly {topic_count} main topics from this document
- Each topic should be 3-8 words maximum
- Separate each topic with a comma
- Do NOT use numbers, bullets, or dashes
- Do NOT add explanations or descriptions
- Just list the topics separated by commas
- Focus on the most important and distinct topics

TARGET AUDIENCE: Grade {grade_level} students
SUBJECT AREA: {subject}

EXAMPLE FORMAT: Topic One, Topic Two, Topic Three, Topic Four

Your response with exactly {topic_count} topics separated by commas:"""

        if custom_instructions:
            prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"
        
        return prompt
    
    def _call_nova(self, prompt: str, grade_level: int, subject: str) -> Dict[str, Any]:
        """Call Nova for content generation."""
        try:
            result = self.bedrock_client.generate_content(
                prompt,
                grade_level=grade_level,
                subject=subject
            )
            
            if not result or 'content' not in result:
                raise SyllabusExtractionError(
                    "Nova returned empty or invalid response."
                )
            
            return result
            
        except Exception as e:
            raise SyllabusExtractionError(f"Nova content generation failed: {str(e)}")
    
    def _parse_nova_response(self, nova_response: Dict[str, Any], 
                           expected_count: int) -> List[str]:
        """Parse Nova response to extract topics."""
        content = nova_response['content'].strip()
        
        if not content:
            raise SyllabusExtractionError(
                "Nova returned empty content. Please try again with different instructions."
            )
        
        print(f"📝 Nova Response: '{content}'")
        
        # Check for comma separation
        if ',' not in content:
            raise SyllabusExtractionError(
                f"Nova did not follow comma-separation format. "
                f"Response: '{content[:100]}...'\n"
                f"Please try again - Nova should return comma-separated topics."
            )
        
        # Split by commas and clean
        raw_topics = [topic.strip() for topic in content.split(',')]
        
        if not raw_topics:
            raise SyllabusExtractionError(
                "Failed to parse any topics from Nova response."
            )
        
        print(f"🔍 Parsed {len(raw_topics)} topics from Nova response")
        return raw_topics
    
    def _validate_and_clean_topics(self, topics: List[str], 
                                 expected_count: int) -> List[str]:
        """Validate and clean extracted topics."""
        clean_topics = []
        
        for i, topic in enumerate(topics):
            if not topic or len(topic.strip()) < 3:
                continue
            
            # Clean the topic
            clean_topic = self._clean_single_topic(topic)
            
            if clean_topic and clean_topic not in clean_topics:
                clean_topics.append(clean_topic)
                print(f"   ✅ Topic {len(clean_topics)}: '{clean_topic}'")
        
        # Validate we got reasonable results
        if not clean_topics:
            raise SyllabusExtractionError(
                "No valid topics could be extracted from Nova response. "
                "Please try again with different content or instructions."
            )
        
        # Check if we got significantly fewer topics than expected
        if len(clean_topics) < max(1, expected_count // 2):
            raise SyllabusExtractionError(
                f"Only extracted {len(clean_topics)} topics, expected {expected_count}. "
                f"Nova may not have understood the format. Please try again."
            )
        
        # Trim to exact count if we got more than expected
        if len(clean_topics) > expected_count:
            print(f"📝 Got {len(clean_topics)} topics, trimming to {expected_count}")
            clean_topics = clean_topics[:expected_count]
        
        return clean_topics
    
    def _clean_single_topic(self, topic: str) -> str:
        """Clean a single topic string."""
        # Remove any numbers or bullets that might have snuck in
        clean_topic = re.sub(r'^\d+\.?\s*', '', topic)  # Remove leading numbers
        clean_topic = re.sub(r'^[-•*]\s*', '', clean_topic)  # Remove bullets
        clean_topic = clean_topic.strip()
        
        # Apply text sanitization
        sanitized_topic = sanitize_text(clean_topic, mode='comprehensive')
        
        return sanitized_topic
    
    def display_results(self, topics: List[str], title: str = "Nova-Generated Syllabus") -> None:
        """Display extraction results."""
        print(f"\n📊 Successfully extracted {len(topics)} topics")
        
        # Console display
        print(f"\n📋 {title}:")
        print("=" * 70)
        for i, topic in enumerate(topics, 1):
            print(f"{i:2d}. {topic}")
        print("=" * 70)
        
        # Jupyter display if available
        if IPYTHON_AVAILABLE:
            display(Markdown(f"## 📋 {title}"))
            syllabus_markdown = "\n".join(f"{i}. **{topic}**" for i, topic in enumerate(topics, 1))
            display(Markdown(syllabus_markdown))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return self.extraction_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset extraction statistics."""
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_topics_extracted': 0
        }


# Global extractor instance
_global_extractor: Optional[CleanSyllabusExtractor] = None


def setup_syllabus_extraction(bedrock_client) -> CleanSyllabusExtractor:
    """
    Set up clean syllabus extraction.
    
    Args:
        bedrock_client: Initialized Bedrock client
        
    Returns:
        CleanSyllabusExtractor instance
    """
    global _global_extractor
    
    _global_extractor = CleanSyllabusExtractor(bedrock_client)
    return _global_extractor


def extract_syllabus_topics(pdf_path: str, topic_count: int = 5,
                          grade_level: int = 8, subject: str = "general",
                          custom_instructions: str = "") -> List[str]:
    """
    Extract syllabus topics with no fallbacks.
    
    Args:
        pdf_path: Path to PDF file
        topic_count: Number of topics to extract
        grade_level: Target grade level
        subject: Subject area
        custom_instructions: Additional instructions
        
    Returns:
        List of Nova-generated topics
        
    Raises:
        SyllabusExtractionError: If extraction fails
    """
    if not _global_extractor:
        raise SyllabusExtractionError(
            "Syllabus extractor not initialized. Call setup_syllabus_extraction() first."
        )
    
    return _global_extractor.extract_topics(
        pdf_path, topic_count, grade_level, subject, custom_instructions
    )


class SyllabusExtractorTracker:
    """
    Class-based interface for syllabus extraction (similar to other tracker patterns).
    """
    
    @classmethod
    def setup(cls, bedrock_client) -> CleanSyllabusExtractor:
        """Set up syllabus extraction."""
        return setup_syllabus_extraction(bedrock_client)
    
    @classmethod
    def extract(cls, pdf_path: str, topic_count: int = 5,
               grade_level: int = 8, subject: str = "general",
               custom_instructions: str = "") -> List[str]:
        """Extract topics."""
        return extract_syllabus_topics(
            pdf_path, topic_count, grade_level, subject, custom_instructions
        )
    
    @classmethod
    def stats(cls) -> Dict[str, Any]:
        """Get extraction statistics."""
        if not _global_extractor:
            return {'error': 'Extractor not initialized'}
        return _global_extractor.get_stats()
    
    @classmethod
    def display(cls, topics: List[str], title: str = "Nova-Generated Syllabus") -> None:
        """Display results."""
        if not _global_extractor:
            print("Error: Extractor not initialized")
            return
        _global_extractor.display_results(topics, title)


# Quick setup function for notebook cells
def quick_extraction_setup(bedrock_client):
    """
    Ultra-simple setup function for notebook cells.
    
    Args:
        bedrock_client: Initialized Bedrock client
        
    Returns:
        tuple: (extractor, extract_function, display_function)
    """
    extractor = setup_syllabus_extraction(bedrock_client)
    return extractor, extract_syllabus_topics, extractor.display_results
