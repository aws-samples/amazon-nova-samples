# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


person_action_system_prompt = """Carefully read a partial transcript of a meeting provided in the <transcript> tags and extract action items of all speakers in the transcript in a bullet list for each speaker. If there are no action items for a speaker, say "No action items". 
"""

###############################################
#          Meeting action prompt              #
###############################################

one_stage_meeting_action_prompt = """ Here's the meeting script that you must extract action items:
<transcript>
{meeting_transcript}
</transcript>

Carefully read the transcript of a meeting provided in the <transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. Follow these rules to generate action items:
- Please write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 15 words.
- Do not generate more than 10 sentences total. Consolidate common-themed action items. 
- Start each bullet point with a verb. The verb should be different than all previous ones to avoid repetition. 
- Verbs with the same or similar meanings should appear MAX twice among all action items.
- Only extract action items specifically mentioned in the transcript. Never make up any action items. 
- If there are no action items identified in the transcript, just write "No Actions".
"""

one_stage_meeting_action_system_prompt_v2 = """Please carefully read the transcript of a meeting provided in the <transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. 
Here are the instruction you must follow to generate action items:
<instructions>
- Please write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 15 words.
- Do not generate more than 10 sentences total. Consolidate common-themed action items. 
- Start each bullet point with a verb. The verb should be different than all previous ones to avoid repetition. 
- Verbs with the same or similar meanings should appear MAX twice among all action items.
- Clearly state the owner for each action item when there is a dedicated owner for an action item
- Merge similar related action items together for conciseness.
- If there are no action items identified in the transcript, just write "No Actions".
- Only extract action items specifically mentioned in the transcript. Never make up any action items. 
</instructions> 
"""

one_stage_meeting_action_usr_prompt_v2 = """Here's the meeting script that you must extract action items:
<transcript>
{meeting_transcript}
</transcript>

Please write only important action items in the <action_items> tags from the meeting. Let's think step by step.
"""

meeting_action_assistant_prompt = "<action_items>"


two_stage_partial_meeting_action_generation_prompt = """Here's the partial meeting script that you must extract action items:
<partial_transcript>
{chapter_transcript}
</partial_transcript>

Carefully read the partial transcript of a meeting provided in the <partial_transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. Follow these rules when aggregating action items:
- Write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 10 words.
- Do not generate more than 5 sentences total. Consolidate common-themed action items.
- If there are no action items identified in the transcript, just write "No Actions". 
- Only extract meeting-level action items, do not extract action items for each participant
"""



two_stage_partial_meeting_action_aggregation_prompt = """You are a professional who excels in extracting concise and clear action items from meeting transcript. You are provided with action items generated from several partial meeting transcripts in <action_items></action_items> tag. 
You task is to aggregate them into a list of final action items for the meeting.  

Follow these rules when aggregating action items:
- Write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 15 words.
- Do not generate more than 10 sentences total. Consolidate common-themed action items. 
- Verbs with the same or similar meanings should appear MAX twice among all action items.
- Only aggregate the provided action items, do not make up new action items
- Only generate meeting-level action items, do not generate participant specific action items.

Here are all the action items generated so far:
<action_items>
{meeting_action_items}
</action_items>"""




###############################################
#          Participant action prompt          #
###############################################

one_stage_participant_action_prompt = """Here's the meeting script that you must extract action items for relevant participants:
<transcript>
{meeting_transcript}
</transcript>

Carefully read the transcript of a meeting provided in the <transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. Follow these rules to generate action items:
- Please write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 15 words.
- Clearly state the owner for each action item.
- Merge related action items for the same owner, especially if the new action item remain under 15 words. 
- Do not generate more than 10 sentences total. 
- If there are no action items identified in the transcript, just write "No Actions".
- Only extract action items specifically mentioned in the transcript. Never make up any action items. 
"""


two_stage_partial_participant_action_generation_prompt = """Here's the partial meeting script that you must extract action items:
<partial_transcript>
{chapter_transcript}
</partial_transcript>

Carefully read the partial transcript of a meeting provided in the <partial_transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. Follow these rules when aggregating action items:
- Write the action items as concisely as possbile in <action_items> tags.
- Start each sentence by stating the owner for the action item. The action item should be different than all previous ones to avoid repetition. 
- The same person should appear MAX twice among all action items.
- Do not generate more than 5 sentences total. Each action item should contain no more than 10 words.
- If there are no action items identified in the transcript, just write "No Actions". 
"""


two_stage_partial_participant_action_aggregation_prompt = """ You are provided with action items generated from several partial meeting transcripts in <action_items></action_items> tag. You task is to aggregate them into a list of final action items for the meeting.  

Follow these rules when aggregating action items:
- Aggregate action items as concisely as possbile in <action_items> tags. Do not provide any reasoning.
- Start each sentence by stating the owner for the action item. The action item should be different than all previous ones to avoid repetition. 
- The same person should appear MAX twice among all action items.
- Do not generate more than 10 sentences total. 
- Each action item should contain no more than 15 words. 
- Only aggregate the provided action items, do not make up new action items.

Here are all the action items generated so far:
<action_items>
{meeting_action_items}
</action_items>"""

one_stage_participant_action_system_prompt_v2 = """Please carefully read the transcript of a meeting provided in the <transcript> tags and extract important action items assigned for follow-up after the meeting in a bullet list. 
Here are the instruction you must follow to generate action items:
<instructions>
- Please write the action items as concisely as possbile in <action_items> tags.
- The content in each bullet point should be easily readable, with no more than 15 words.
- Clearly state the owner for each action item with colon. For example, Owner: Action Item.
- Merge similar related action items together for conciseness.
- Do not generate more than 10 sentences total.
- If there are no action items identified in the transcript, just write "No Actions".
- Only extract action items specifically mentioned in the transcript. Never make up any action items. 
</instructions> 

Here's one example in the format that you must follow for your response:
<action_items>
    * Huw Morris: Continue visiting institutions to discuss Brexit preparedness
    * Marie Knox: Continue co-ordinating with departments on European transition
    * Eluned Morgan: Continue discussions with FE sector on funding review
</action_items>
"""

one_stage_participant_action_usr_prompt_v2 = """Here's the meeting script that you must extract action items for relevant participants:
<transcript>
{meeting_transcript}
</transcript>

Please write only important participants' action items in the <action_items> tags. Let's think step by step.
"""

participant_action_assistant_prompt = "<action_items>"