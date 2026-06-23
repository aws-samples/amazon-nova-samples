"""
Enhanced Bedrock Client Module

Provides comprehensive Bedrock client functionality with error handling,
content analysis, and grade-level specific content generation.
"""

import boto3
import json
import time
import random
import base64
import re
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedBedrockClient:
    """Enhanced Bedrock client with comprehensive error handling and content analysis."""
    
    def __init__(self, region, credentials=None):
        if credentials:
            self.client = boto3.client(
                'bedrock-runtime', 
                region_name=region,
                aws_access_key_id=credentials['access_key'],
                aws_secret_access_key=credentials['secret_key'],
                aws_session_token=credentials.get('session_token')
            )
        else:
            self.client = boto3.client('bedrock-runtime', region_name=region)
        
        # Import dependencies to avoid circular imports
        from ..utils.error_handler import BedrockErrorHandler, EnhancedBedrockError
        from ..content.analyzer import ContentAnalyzer
        from ..utils.standards import StandardsDatabase
        from ..utils.config import GRADE_LEVEL_CONFIGS, get_grade_level_category
        
        self.error_handler = BedrockErrorHandler()
        self.content_analyzer = ContentAnalyzer()
        self.standards_db = StandardsDatabase()
        self.region = region
    
    def enhance_prompt_for_grade_level(self, base_prompt, grade_level, standards=None, subject="mathematics"):
        """Enhance prompt with grade-level specific context and standards."""
        from ..utils.config import GRADE_LEVEL_CONFIGS, get_grade_level_category
        
        grade_category = get_grade_level_category(grade_level)
        config = GRADE_LEVEL_CONFIGS[grade_category]
        
        # Get relevant standards if not provided
        if not standards:
            standards = self.standards_db.get_standards_for_grade(grade_level, subject)
        
        enhanced_prompt = f"""
EDUCATIONAL CONTEXT:
- Target Grade Level: {grade_level} ({grade_category})
- Target Age Range: {config['age_range']}
- Vocabulary Level: {config['vocabulary_level']}
- Reading Level: {config['reading_level']}
- Maximum Bullet Points: {config['max_bullets_per_slide']}

EDUCATIONAL STANDARDS TO ALIGN WITH:
{self._format_standards_for_prompt(standards)}

CONTENT REQUIREMENTS:
- Use {config['sentence_complexity']} sentence structures
- Include {config['visual_emphasis']} visual emphasis
- Design for {config['activity_duration']} attention span
- Ensure age-appropriate language and examples
- Align content with the specified educational standards

ORIGINAL REQUEST:
{base_prompt}

Please generate content that meets all the above requirements and is specifically appropriate for grade {grade_level} students.
        """.strip()
        
        return enhanced_prompt
    
    def _format_standards_for_prompt(self, standards):
        """Format standards for inclusion in prompts."""
        if not standards:
            return "No specific standards provided."
        
        formatted = []
        for standard in standards[:3]:  # Limit to top 3 to avoid prompt bloat
            formatted.append(f"- {standard['code']}: {standard['description']}")
        
        return "\n".join(formatted)
    
    def generate_content(self, prompt, grade_level, standards=None, model_id="us.amazon.nova-premier-v1:0", subject="mathematics"):
        """Generate content with comprehensive analysis and error handling."""
        from ..utils.error_handler import EnhancedBedrockError
        
        # Enhance prompt with grade-level context
        enhanced_prompt = self.enhance_prompt_for_grade_level(prompt, grade_level, standards, subject)
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating content for grade {grade_level} using model {model_id}")
            
            response = self.client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": enhanced_prompt}]}],
                inferenceConfig={"temperature": 0.2}
            )
            
            processing_time = time.time() - start_time
            raw_content = response['output']['message']['content'][-1]['text']
            
            # Sanitize the content to remove markdown and special characters
            sanitized_content = self.sanitize_text_content(raw_content)
            
            # Analyze generated content (use sanitized version)
            content_analysis = self.content_analyzer.analyze_content_quality(
                sanitized_content, grade_level, standards
            )
            
            # Validate standards alignment
            standards_validation = self._validate_standards_alignment(sanitized_content, standards)
            
            result = {
                "content": sanitized_content,  # Return sanitized content
                "raw_content": raw_content,   # Keep original for debugging
                "metadata": {
                    "model_id": model_id,
                    "grade_level": grade_level,
                    "processing_time": processing_time,
                    "prompt_length": len(enhanced_prompt),
                    "response_length": len(sanitized_content),
                    "sanitization_applied": raw_content != sanitized_content
                },
                "quality_analysis": content_analysis,
                "standards_validation": standards_validation,
                "enhanced_prompt_used": enhanced_prompt
            }
            
            if raw_content != sanitized_content:
                logger.info(f"Content sanitized: removed markdown/special characters")
            
            logger.info(f"Content generated successfully. Quality score: {content_analysis.get('overall_quality_score', 'N/A')}")
            return result
            
        except Exception as e:
            error_details = self.error_handler.handle_bedrock_error(
                e, enhanced_prompt, model_id, 
                {"grade_level": grade_level, "subject": subject}
            )
            raise EnhancedBedrockError(error_details)
    
    def _validate_standards_alignment(self, content, standards):
        """Validate how well content aligns with educational standards."""
        if not standards:
            return {"message": "No standards provided for validation"}
        
        content_lower = content.lower()
        aligned_standards = []
        
        for standard in standards:
            keyword_matches = sum(1 for keyword in standard.get('keywords', []) 
                                if keyword.lower() in content_lower)
            
            if keyword_matches > 0:
                aligned_standards.append({
                    "standard_code": standard['code'],
                    "keyword_matches": keyword_matches,
                    "alignment_strength": "strong" if keyword_matches >= 2 else "partial"
                })
        
        return {
            "total_standards_checked": len(standards),
            "aligned_standards_count": len(aligned_standards),
            "alignment_percentage": (len(aligned_standards) / len(standards)) * 100,
            "aligned_standards": aligned_standards
        }
    
    def sanitize_text_content(self, text):
        """Sanitize text content by removing markdown formatting and special characters."""
        if not text or not isinstance(text, str):
            return text
        
        # Remove markdown formatting
        sanitized = text
        
        # Remove markdown headers (# ## ###)
        sanitized = re.sub(r'^#+\s*', '', sanitized, flags=re.MULTILINE)
        
        # Remove markdown bold (**text** or __text__)
        sanitized = re.sub(r'\*\*(.*?)\*\*', r'\1', sanitized)
        sanitized = re.sub(r'__(.*?)__', r'\1', sanitized)
        
        # Remove markdown italic (*text* or _text_)
        sanitized = re.sub(r'\*(.*?)\*', r'\1', sanitized)
        sanitized = re.sub(r'_(.*?)_', r'\1', sanitized)
        
        # Remove markdown links [text](url)
        sanitized = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', sanitized)
        
        # Remove markdown code blocks (```code```)
        sanitized = re.sub(r'```.*?```', '', sanitized, flags=re.DOTALL)
        
        # Remove inline code (`code`)
        sanitized = re.sub(r'`([^`]+)`', r'\1', sanitized)
        
        # Remove bullet points and list markers
        sanitized = re.sub(r'^[\s]*[-*+•]\s*', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'^\s*\d+\.\s*', '', sanitized, flags=re.MULTILINE)
        
        # Remove other special characters that cause issues in PowerPoint
        # Keep only alphanumeric, spaces, basic punctuation, and common symbols
        sanitized = re.sub(r'[^\w\s.,!?;:()\-\'\"&%$@#+=/\\]+', ' ', sanitized)
        
        # Clean up multiple spaces and newlines
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip()
        
        return sanitized

    def sanitize_content_list(self, content_list):
        """Sanitize a list of content items (like bullet points)."""
        if not content_list:
            return content_list
        
        sanitized_list = []
        for item in content_list:
            if isinstance(item, str):
                sanitized_item = self.sanitize_text_content(item)
                if sanitized_item:  # Only add non-empty items
                    sanitized_list.append(sanitized_item)
            else:
                sanitized_list.append(item)
        
        return sanitized_list

    def sanitize_image_prompt(self, prompt):
        """Sanitize image prompt by removing special characters and markdown formatting."""
        if not prompt:
            return "educational illustration"
        
        # Remove markdown formatting
        sanitized = prompt
        
        # Remove markdown headers (# ## ###)
        sanitized = re.sub(r'^#+\s*', '', sanitized, flags=re.MULTILINE)
        
        # Remove markdown bold (**text** or __text__)
        sanitized = re.sub(r'\*\*(.*?)\*\*', r'\1', sanitized)
        sanitized = re.sub(r'__(.*?)__', r'\1', sanitized)
        
        # Remove markdown italic (*text* or _text_)
        sanitized = re.sub(r'\*(.*?)\*', r'\1', sanitized)
        sanitized = re.sub(r'_(.*?)_', r'\1', sanitized)
        
        # Remove markdown links [text](url)
        sanitized = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', sanitized)
        
        # Remove markdown code blocks (```code```)
        sanitized = re.sub(r'```.*?```', '', sanitized, flags=re.DOTALL)
        
        # Remove inline code (`code`)
        sanitized = re.sub(r'`([^`]+)`', r'\1', sanitized)
        
        # Remove bullet points and list markers
        sanitized = re.sub(r'^[\s]*[-*+•]\s*', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'^\s*\d+\.\s*', '', sanitized, flags=re.MULTILINE)
        
        # Remove special characters that might cause issues
        # Keep only alphanumeric, spaces, basic punctuation
        sanitized = re.sub(r'[^\w\s.,!?;:()\-\'\"]+', ' ', sanitized)
        
        # Clean up multiple spaces and newlines
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip()
        
        # Ensure prompt is not too long (Nova Canvas has limits)
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rsplit(' ', 1)[0]  # Cut at word boundary
        
        # Ensure we have a valid prompt
        if not sanitized or len(sanitized.strip()) < 3:
            sanitized = "educational illustration"
        
        return sanitized

    def create_optimized_canvas_prompt(self, topic, context_text="", grade_level=8, model_id="amazon.nova-pro-v1:0"):
        """Use Nova Pro to create an optimized prompt for Nova Canvas with person identification."""
        from ..utils.config import GRADE_LEVEL_CONFIGS, get_grade_level_category
        
        try:
            # Get grade level configuration for age-appropriate content
            grade_category = get_grade_level_category(grade_level)
            config = GRADE_LEVEL_CONFIGS[grade_category]
            
            # Create a prompt for Nova Pro to generate the Canvas prompt with person identification
            pro_prompt = f"""You are an expert at creating prompts for Nova Canvas image generation. Create an optimized prompt for Nova Canvas to generate an educational illustration.

TOPIC: {topic}
CONTEXT: {context_text if context_text else "No additional context provided"}
TARGET AUDIENCE: Grade {grade_level} students ({config['age_range']})

IMPORTANT: If the topic or context mentions any proper names of people:
1. Use the context to identify who the person is
2. Create a visual description of the person instead of using their name
3. Include relevant historical period, typical clothing, setting, and appearance
4. Focus on visual elements that Nova Canvas can render

For example:
- Instead of "Adam Smith": "An 18th century Scottish philosopher and economist, middle-aged man with powdered wig typical of the 1700s, formal period clothing, scholarly appearance"
- Instead of "Marie Curie": "Early 20th century female scientist, professional attire of the 1900s, laboratory setting, determined expression"

Create a Nova Canvas prompt following these best practices:
1. Subject: Clear description of the main subject/concept (replace names with descriptions)
2. Environment: Setting or background context
3. Position/pose: How subjects should be positioned (if applicable)
4. Lighting: Lighting description for visual appeal
5. Camera position/framing: Viewpoint and composition
6. Visual style: Specify "educational illustration" or similar appropriate style

Requirements:
- Make it educational and age-appropriate for {config['age_range']}
- Replace any proper names with visual descriptions
- Use clear, descriptive language
- Keep it concise but comprehensive
- Focus on visual elements that support learning
- Avoid any inappropriate content

Format your response as a single, well-structured prompt ready for Nova Canvas.
Do NOT include explanations or additional text - just the optimized prompt."""

            # Use Nova Pro to create the optimized Canvas prompt
            response = self.client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": pro_prompt}]}],
                inferenceConfig={"temperature": 0.3}  # Slightly higher for creativity
            )
            
            optimized_prompt = response['output']['message']['content'][-1]['text'].strip()
            
            # Sanitize the optimized prompt
            sanitized_prompt = self.sanitize_image_prompt(optimized_prompt)
            
            logger.info(f"Nova Pro created optimized Canvas prompt with person identification for: {topic}")
            
            return {
                "optimized_prompt": sanitized_prompt,
                "original_prompt": optimized_prompt,
                "topic": topic,
                "context": context_text,
                "grade_level": grade_level,
                "person_identification_applied": any(name.istitle() and len(name) > 2 for name in topic.split() + context_text.split())
            }
            
        except Exception as e:
            logger.error(f"Error creating optimized Canvas prompt: {e}")
            # Fallback to basic prompt
            fallback_prompt = f"Educational illustration of {topic}, clean and engaging visual for grade {grade_level} students"
            return {
                "optimized_prompt": self.sanitize_image_prompt(fallback_prompt),
                "original_prompt": fallback_prompt,
                "topic": topic,
                "context": context_text,
                "grade_level": grade_level,
                "fallback_used": True
            }

    def generate_image_with_optimized_prompt(self, topic, context_text="", grade_level=8, canvas_model_id="amazon.nova-canvas-v1:0"):
        """Generate image using Nova Premier to create optimized Nova Canvas prompt."""
        from ..utils.error_handler import EnhancedBedrockError
        
        try:
            # Step 1: Use Nova Pro to create optimized Canvas prompt
            print(f"   🧠 Using Nova Pro to optimize Canvas prompt...")
            prompt_data = self.create_optimized_canvas_prompt(topic, context_text, grade_level)
            
            optimized_prompt = prompt_data["optimized_prompt"]
            
            if prompt_data.get("fallback_used"):
                print(f"   ⚠️ Using fallback prompt (Nova Premier unavailable)")
            else:
                print(f"   ✅ Nova Premier created optimized prompt")
            
            # Log the optimization for transparency
            logger.info(f"Optimized Canvas prompt: {optimized_prompt[:200]}...")
            
            # Step 2: Use the optimized prompt with Nova Canvas
            print(f"   🎨 Generating image with Nova Canvas...")
            
            canvas_req = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": optimized_prompt},
                "imageGenerationConfig": {
                    "seed": random.randint(0, 9999999),
                    "quality": "standard",
                    "width": 512,
                    "height": 512,
                    "numberOfImages": 1
                }
            }
            
            response = self.client.invoke_model(
                modelId=canvas_model_id,
                body=json.dumps(canvas_req).encode('utf-8'),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'images' in response_body:
                image_data = base64.b64decode(response_body["images"][0])
            elif 'image' in response_body:
                image_data = base64.b64decode(response_body["image"])
            else:
                raise Exception("No image data in response")
            
            return {
                "image_data": image_data,
                "prompt_data": prompt_data,
                "success": True
            }
                
        except Exception as e:
            # Enhanced error handling with prompt details
            error_context = {
                "topic": topic,
                "context_text": context_text,
                "grade_level": grade_level,
                "optimized_prompt": prompt_data.get("optimized_prompt", "N/A") if 'prompt_data' in locals() else "N/A"
            }
            error_details = self.error_handler.handle_bedrock_error(
                e, 
                prompt_data.get("optimized_prompt", topic) if 'prompt_data' in locals() else topic, 
                canvas_model_id, 
                error_context
            )
            raise EnhancedBedrockError(error_details)

    def generate_image_with_context(self, topic, context_text="", model_id="amazon.nova-canvas-v1:0"):
        """Generate image with enhanced context including full syllabus line and following sentences."""
        from ..utils.error_handler import EnhancedBedrockError
        
        try:
            # Create comprehensive image prompt with full context
            if context_text:
                # Include both topic and context in the image prompt
                full_context_prompt = f"An educational illustration representing: {topic}. Context: {context_text}. Style appropriate for educational content. Clean, simple, and engaging visual."
            else:
                # Fallback to topic only if no context provided
                full_context_prompt = f"An educational illustration representing: {topic}. Style appropriate for educational content. Clean, simple, and engaging visual."
            
            # Sanitize the complete prompt (including context)
            sanitized_prompt = self.sanitize_image_prompt(full_context_prompt)
            
            # Log the enhancement for debugging
            if context_text:
                logger.info(f"Image prompt enhanced with context: '{topic}' + context")
            else:
                logger.info(f"Image prompt without additional context: '{topic}'")
            
            canvas_req = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": sanitized_prompt},
                "imageGenerationConfig": {
                    "seed": random.randint(0, 9999999),
                    "quality": "standard",
                    "width": 512,
                    "height": 512,
                    "numberOfImages": 1
                }
            }
            
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(canvas_req).encode('utf-8'),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'images' in response_body:
                return base64.b64decode(response_body["images"][0])
            elif 'image' in response_body:
                return base64.b64decode(response_body["image"])
            else:
                raise Exception("No image data in response")
                
        except Exception as e:
            # Include both original and sanitized prompts in error details
            error_context = {
                "topic": topic,
                "context_text": context_text,
                "full_prompt": full_context_prompt if 'full_context_prompt' in locals() else "N/A",
                "sanitized_prompt": sanitized_prompt if 'sanitized_prompt' in locals() else "N/A"
            }
            error_details = self.error_handler.handle_bedrock_error(e, full_context_prompt if 'full_context_prompt' in locals() else topic, model_id, error_context)
            raise EnhancedBedrockError(error_details)

    def generate_image(self, prompt, model_id="amazon.nova-canvas-v1:0"):
        """Generate image with enhanced error handling and prompt sanitization."""
        from ..utils.error_handler import EnhancedBedrockError
        
        try:
            # Sanitize the prompt to remove special characters and markdown
            sanitized_prompt = self.sanitize_image_prompt(prompt)
            
            # Log the sanitization for debugging
            if prompt != sanitized_prompt:
                logger.info(f"Image prompt sanitized: '{prompt}' -> '{sanitized_prompt}'")
            
            canvas_req = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": sanitized_prompt},
                "imageGenerationConfig": {
                    "seed": random.randint(0, 9999999),
                    "quality": "standard",
                    "width": 512,
                    "height": 512,
                    "numberOfImages": 1
                }
            }
            
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(canvas_req).encode('utf-8'),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'images' in response_body:
                return base64.b64decode(response_body["images"][0])
            elif 'image' in response_body:
                return base64.b64decode(response_body["image"])
            else:
                raise Exception("No image data in response")
                
        except Exception as e:
            error_details = self.error_handler.handle_bedrock_error(e, sanitized_prompt if 'sanitized_prompt' in locals() else prompt, model_id, {"original_prompt": prompt})
            raise EnhancedBedrockError(error_details)


def create_bedrock_client(region, credentials=None):
    """Factory function to create a new Bedrock client instance."""
    return EnhancedBedrockClient(region, credentials)
