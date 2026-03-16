"""
Content Generation Module

Handles comprehensive content and image generation with rate limiting,
context extraction, and quality analysis.
"""

import os
import time
import logging
from datetime import datetime

# Handle optional dependencies gracefully
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Comprehensive content generator with rate limiting, context extraction,
    and quality analysis.
    """
    
    def __init__(self, bedrock_client, token_counter, grade_level=8, subject="general"):
        self.bedrock_client = bedrock_client
        self.token_counter = token_counter
        self.grade_level = grade_level
        self.subject = subject
        self.rate_limiter = RateLimiter()
        
    def generate_all(self, topics, context_text="", pdf_path=None, max_topics=None):
        """
        Generate content and images for all topics with optimized rate limiting.
        
        Args:
            topics: List of topic strings
            context_text: Additional context text
            pdf_path: Path to PDF for context extraction
            max_topics: Maximum number of topics to process
            
        Returns:
            tuple: (slide_contents, slide_images, slide_titles, slide_contexts)
        """
        if not self.bedrock_client:
            print("❌ Bedrock client not initialized")
            return [], [], [], []
        
        # Limit topics if specified
        if max_topics:
            topics = topics[:max_topics]
        
        print(f"🎯 Generating content for {len(topics)} topics (Grade {self.grade_level})")
        print(f"📚 Subject: {self.subject}")
        print("=" * 60)
        
        # Initialize containers
        slide_contents = []
        slide_images = []
        slide_titles = []
        slide_contexts = []
        
        # Extract PDF context if available
        pdf_context = self._extract_pdf_context(pdf_path) if pdf_path else ""
        
        # Process each topic
        for i, topic in enumerate(topics):
            current_topic_num = i + 1
            is_final_topic = (current_topic_num == len(topics))
            
            print(f"\n🔄 Processing topic {current_topic_num}/{len(topics)}: {topic}")
            
            try:
                # Generate content for this topic
                content_result = self._generate_topic_content(
                    topic, pdf_context, context_text, is_final_topic
                )
                
                # Generate image for this topic
                image_result = self._generate_topic_image(
                    topic, content_result.get('context', ''), is_final_topic
                )
                
                # Store results
                slide_contents.append(content_result['bullets'])
                slide_images.append(image_result.get('image_data'))
                slide_titles.append(topic)
                slide_contexts.append(content_result.get('context', ''))
                
                print(f"   ✅ Topic completed successfully")
                
            except Exception as e:
                print(f"   ❌ Error processing topic: {e}")
                logger.error(f"Error processing topic '{topic}': {e}")
                
                # Add minimal content for failed topics
                slide_contents.append([f"Topic: {topic}"])
                slide_images.append(None)
                slide_titles.append(topic)
                slide_contexts.append("")
        
        print(f"\n🎉 Generation complete!")
        print(f"📊 Results: {len(slide_contents)} slides, {len([img for img in slide_images if img])} images")
        
        # Print token summary
        self.token_counter.print_summary()
        
        return slide_contents, slide_images, slide_titles, slide_contexts
    
    def _extract_pdf_context(self, pdf_path):
        """Extract text context from PDF file."""
        if not PYMUPDF_AVAILABLE:
            print("⚠️ PyMuPDF not available - PDF context extraction disabled")
            return ""
        
        if not os.path.exists(pdf_path):
            print(f"⚠️ PDF file not found: {pdf_path}")
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            for page in doc:
                all_text += page.get_text()
            doc.close()
            
            print(f"📄 Loaded {len(all_text):,} characters from PDF")
            return all_text
            
        except Exception as e:
            print(f"⚠️ Could not load PDF context: {e}")
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    def _find_topic_context(self, topic, pdf_context):
        """Find relevant context for a topic from PDF content."""
        if not pdf_context:
            return ""
        
        topic_words = topic.lower().split()
        sentences = pdf_context.split('.')
        relevant_sentences = []
        
        # Find sentences containing topic keywords
        for sentence in sentences[:100]:  # Limit search for performance
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in topic_words if len(word) > 3):
                relevant_sentences.append(sentence.strip())
                if len(relevant_sentences) >= 3:
                    break
        
        context = '. '.join(relevant_sentences)
        if context:
            print(f"   📖 Found context: {len(context)} characters")
        
        return context
    
    def _generate_topic_content(self, topic, pdf_context, additional_context, is_final_topic):
        """Generate content for a single topic."""
        # Find specific context for this topic
        topic_context = self._find_topic_context(topic, pdf_context)
        
        # Combine all available context
        full_context = f"{topic_context} {additional_context}".strip()
        
        # Create enhanced prompt
        enhanced_prompt = f"""Create educational content about {topic} for Grade {self.grade_level} students.

STRUCTURE YOUR RESPONSE:
1. Start with 3-5 key bullet points (short, concise facts)
2. Follow with detailed explanations and context
3. Include examples and applications

TOPIC: {topic}
CONTEXT: {full_context[:500] if full_context else 'General educational context'}
GRADE LEVEL: {self.grade_level}
SUBJECT: {self.subject}

Make the content engaging and appropriate for the grade level."""
        
        # Generate content using Bedrock client
        result = self.bedrock_client.generate_content(
            enhanced_prompt,
            grade_level=self.grade_level,
            subject=self.subject
        )
        
        # Extract and log token usage
        if 'usage' in result:
            usage = result['usage']
            input_tokens = usage.get('inputTokens', 0)
            output_tokens = usage.get('outputTokens', 0)
        else:
            input_tokens = self.token_counter.estimate_tokens_from_content(enhanced_prompt, 'nova-premier')[0]
            output_tokens = self.token_counter.estimate_tokens_from_content(result.get('content', ''), 'nova-premier')[1]
        
        self.token_counter.log_token_usage('nova-premier', input_tokens, output_tokens, 'content_generation')
        
        content = result['content']
        quality = result.get('quality_analysis', {})
        
        print(f"   📊 Content Quality: {quality.get('overall_quality_score', 'N/A')}/100")
        
        # Parse content into bullets and notes
        if content:
            bullets, notes = self._parse_educational_content(content, topic)
        else:
            bullets = [f"Key concept: {topic}"]
            notes = f"Educational content about {topic} for Grade {self.grade_level} students."
        
        return {
            'bullets': bullets,
            'notes': notes,
            'context': topic_context,
            'quality': quality
        }
    
    def _generate_topic_image(self, topic, context, is_final_topic):
        """Generate optimized image for a topic."""
        print(f"   🎨 Starting optimized image generation...")
        
        try:
            # Rate limit Nova Pro request
            self.rate_limiter.wait_if_needed("nova-pro", is_final_topic)
            
            # Generate optimized image using Bedrock client
            result = self.bedrock_client.generate_image_with_optimized_prompt(
                topic, context, self.grade_level
            )
            
            if result and 'prompt_data' in result:
                # Track Nova Pro usage (optimization)
                optimization_prompt = f"Optimize image prompt for {topic}"
                optimized_response = result['prompt_data'].get('optimized_prompt', '')
                
                pro_input, pro_output = self.token_counter.extract_tokens_from_response(
                    {'input': optimization_prompt, 'output': optimized_response}, 
                    'nova-pro'
                )
                self.token_counter.log_token_usage('nova-pro', pro_input, pro_output, 'image_optimization')
                
                # Track Nova Canvas usage (image generation)
                canvas_input, canvas_output = self.token_counter.extract_tokens_from_response(
                    {'input': optimized_response, 'output': 'image_generated'}, 
                    'nova-canvas'
                )
                self.token_counter.log_token_usage('nova-canvas', canvas_input, canvas_output, 'image_generation')
            
            if result and 'image_data' in result:
                print(f"   ✅ Nova Pro optimized prompt created")
                
                # Rate limit Nova Canvas request
                self.rate_limiter.wait_if_needed("nova-canvas", is_final_topic)
                print(f"   🎨 Generating image with Nova Canvas...")
                print(f"   ✅ Optimized image generated successfully")
                
                return result
            else:
                print(f"   ❌ Image generation failed")
                return {'image_data': None, 'error': 'Image generation failed'}
                
        except Exception as e:
            print(f"   ❌ Image generation error: {e}")
            logger.error(f"Image generation error for topic '{topic}': {e}")
            return {'image_data': None, 'error': str(e)}
    
    def _parse_educational_content(self, content, topic):
        """Parse educational content into bullets and detailed notes."""
        if not content:
            return [f"Key concept: {topic}"], f"Educational content about {topic}."
        
        lines = content.split('\n')
        bullets = []
        notes_lines = []
        
        # Simple parsing logic - extract bullet points and detailed text
        in_bullets = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this looks like a bullet point
            if (line.startswith('•') or line.startswith('-') or line.startswith('*') or
                (len(line.split()) < 15 and ':' not in line)):
                bullets.append(line.lstrip('•-* '))
                in_bullets = True
            else:
                # This is detailed text
                notes_lines.append(line)
                in_bullets = False
        
        # Ensure we have at least some bullets
        if not bullets:
            # Extract first few sentences as bullets
            sentences = content.split('.')[:4]
            bullets = [s.strip() for s in sentences if s.strip()]
        
        # Limit bullets based on grade level
        from ..utils.config import get_grade_level_category, GRADE_LEVEL_CONFIGS
        grade_category = get_grade_level_category(self.grade_level)
        max_bullets = GRADE_LEVEL_CONFIGS[grade_category]['max_bullets_per_slide']
        bullets = bullets[:max_bullets]
        
        # Create notes from remaining content
        notes = ' '.join(notes_lines) if notes_lines else content
        
        return bullets, notes


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self):
        self.last_request_times = {}
        self.rate_limits = {
            'nova-pro': 30,      # seconds between requests
            'nova-canvas': 30,   # seconds between requests
            'nova-premier': 5    # seconds between requests
        }
    
    def wait_if_needed(self, service, is_final_request=False):
        """Wait if needed to respect rate limits."""
        if service not in self.rate_limits:
            return
        
        current_time = time.time()
        last_time = self.last_request_times.get(service, 0)
        time_since_last = current_time - last_time
        
        required_wait = self.rate_limits[service]
        
        # Optimize for final requests (reduce wait time)
        if is_final_request:
            required_wait = max(5, required_wait // 2)
        
        if time_since_last < required_wait:
            wait_time = required_wait - time_since_last
            print(f"   ⏱️ Rate limiting: waiting {wait_time:.1f}s for {service}")
            time.sleep(wait_time)
        
        self.last_request_times[service] = time.time()
    
    def set_topic_info(self, current_topic, total_topics):
        """Set current topic information for optimization."""
        # This can be used for more sophisticated rate limiting
        pass


def create_content_generator(bedrock_client, token_counter, grade_level=8, subject="general"):
    """Factory function to create a content generator."""
    return ContentGenerator(bedrock_client, token_counter, grade_level, subject)
