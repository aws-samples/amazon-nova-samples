# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import List
import json

from .bedrock_helper import get_bedrock_response
from .llm_prompt_bank import person_action_system_prompt
from .bedrock_helper import NOVA_PRO_MODEL_ID


def generate_topic_segmented_meeting_transcript_combined_v2( transcript: str, 
                                max_tokens=2000, 
                                temp=0, 
                                topK=250, 
                                stop_sequences=["Human:"], 
                                model_id = NOVA_PRO_MODEL_ID, 
                                text_only=True ):
    system_prompt = """You are a professional who excels in writing concise and clear executive summaries from meetings in a bulleted format. 
    Your job is to read the given text <transcript> and distill only the most significant discusions and the final high level decisions.  
    
Here are rules you have to follow to summarize the transcript:
1. Do not include any action item that resulted from the <transcript>. 
2. Do not include sentiments of partipants. It is important to keep the tone of the entire summary neutral. Avoid negative sentiments.
3. You MUST only use the information within <transcript> to write the executive summary.
4. Do not include trivial meeting details like how the meeting was conducted.
5. The content in each summary point should be just one sentence in 20 words.
6. Use past tense if applicable.
7. The summary must summarize only the key decisions, key topics, and, if applicable, any updates provided in the given transcript as a whole.
8. The summary must be succinct as a whole and must not describe what an individual said during the meeting.
9. Always start with the most general or introductory summary sentence followed by a bullet list (starting with *) with details, explanations, and supporting points as shown in the below example.
10. The summary generation must not be more 10 sentences total.

Here's an example of the format that your summary must follow:
<summary>
The meeting focused on the design and functional requirements for a new TV remote control, with various team members presenting their research and preferences.

* Presentations were made by the industrial designer, user interface designer, and marketing on the remote control's components, technical functions, and user preferences.
* Key decisions included limiting the remote to TV-only functions, avoiding teletext due to its perceived obsolescence, and prioritizing a simple, user-friendly design.
* Discussion points covered the inclusion of essential buttons such as power, volume, channel, and mute, with additional functions like brightness and contrast to be hidden.
* The team considered innovative features like a clap-activated "find me" function to address common user frustrations.
* Emphasis was placed on speed of delivery and time to market, with any added extras needing to be simple and quick to implement.
</summary>
"""
    usr_msg = f"""Here's the meeting transcript that you must summarize:
<transcript>
{transcript}
</transcript>

Pay close attention to the rules and the format example in the system prompt and then generate your summary strictly following the instruction in the <summary> tags.
"""
    
    assistant_msg = "<summary>"
    
    
    response = get_bedrock_response( usr_msg,  
                                    system=system_prompt,
                                    assistant_message=assistant_msg,
                                    max_tokens=max_tokens, 
                                    temp=temp,
                                    topK=topK, 
                                    stop_sequences=stop_sequences, 
                                    model_id = model_id, 
                                    text_only=text_only )
    return response