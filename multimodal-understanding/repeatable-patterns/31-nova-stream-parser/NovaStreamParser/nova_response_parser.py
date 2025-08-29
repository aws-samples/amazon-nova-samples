import re

class NovaResponseParser:
    """
    Parses streaming responses from Nova LLM service by processing text chunks and extracting
    content between answer tags. This parser maintains state between chunks to handle
    responses that may be split across multiple chunks.
    """

    def __init__(self, target_tag_name):
        self.tag = []
        self.inside_tag = False
        self.target_tag_name = target_tag_name
        self.target_start_tag = f"<{target_tag_name}>"
        self.target_end_tag = f"</{target_tag_name}>"
        self.text_chunks = []
        self.is_found_target_start_tag = False
        self.is_found_target_end_tag = False
        self.inside_tag_content = False
    
    def reset(self):
        self.tag = []
        self.inside_tag = False
        self.text_chunks = []
        self.is_found_target_start_tag = False
        self.is_found_target_end_tag = False
        self.inside_tag_content = False
        

    def _remove_tags_from_text(self, text):
        """
        Removes specified tags and all content contained within them from a given text.
        
        Args:
            text (str): The input text to process
            tag_name (str): The name of the tag to remove (without angle brackets)
        
        Returns:
            str: Text with specified tags and their content removed
        """
        # Create a pattern that matches the specified tag and its content
        # This handles both standard and self-closing tags
        pattern = rf'<{self.target_tag_name}>.*?</{self.target_tag_name}>'
        
        # Replace matches with empty string
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        return cleaned_text

    def process_chunk(self, chunk, text_chunk, callback):
        """
        Processes an individual text chunk from the Nova response stream. This method
        handles the parsing of XML-style tags and extracts content between answer tags.

        Args:
            text_chunk: The raw text chunk to process. Must not be null.

        Returns:
            Processed answer chunk or None if no answer is available
        """
        if text_chunk is None:
            raise ValueError("text_chunk cannot be None")

        self.text_chunks.append(text_chunk)

        for curr in text_chunk:
            if self.inside_tag:
                self.tag.append(curr)
                
            if curr == '<':
                self.inside_tag = True
                self.tag = []
                self.tag.append(curr)
                
            elif curr == '>':
                self.inside_tag = False

                if ''.join(self.tag) == self.target_start_tag:
                    self.inside_tag_content = True
                    self.is_found_target_start_tag = True
                    self.tag = []
                        
                elif ''.join(self.tag) == self.target_end_tag:
                    self.is_found_target_end_tag = True
                    self.inside_tag = False
                    self.inside_tag_content = False
                else:
                    self.inside_tag = False
                    self.tag = []
        
        if (self.is_found_target_start_tag and self.is_found_target_end_tag):
            text = ''.join(self.text_chunks)
            clean_text = self._remove_tags_from_text(text)
            result = callback(chunk, clean_text)
            self.reset()
            return result

        elif not self.inside_tag_content and not self.inside_tag:
            # This must come after the above if statement
            text = ''.join(self.text_chunks)
            result = callback(chunk, text)
            self.reset()
            return result

        return None