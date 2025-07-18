##  Meeting summarization and action item extraction with Amazon Nova moels

### Codebase
* ```demo```: Contains demo scripts to run the target tasks (summarization, meeting-level action item extraction, and participant-level action items) and evaluation.
    * ```01_script_run_summarizer_batch.py```: Demo script to run batch processing of all target tasks
    * ```02_script_results_to_csv.py```: Demo script to organize output data in JSON to CSV.
    * ```03_script_results_to_csv_latency_cost.py```: Demo script to organize cost and latency.
    * ```04_script_results_quality_eval.py```: Demo script to run the LLM-as-a-Judge evaluation scores (faithfulness and summarization scores).
* ```llm_core```: Contains codes for the target tasks
    * ```bedrock_helper.py```: Bedrock invoke call helper functions via Boto3.
    * ```llm_summarizer.py```: Contains a function that calls a batch processing for all the target tasks and I/O format helper tools.
    * ```llm_summarization.py```: Contains functions for the summarization task.
    * ```llm_meeting_actions.py```: Contains functions for the meeting-level action item extraction task.
    * ```llm_part_actions.py```: Contains functions for the participant-level action item extraction task.
    * ```llm_prompt_bank.py ```: Contains prompts for the modules of all target tasks.
* ```llm_eval/bedrock/bedrock_eval.py```: Contains the LLM-as-a-Judge evaluation score functions (faithfulness, qa, and summarization scores). 

### Models Used
* Amazon Nova Micro, Amazon Nova Lite, Amazon Nova Pro, Amazon Nova Premier
    * temp: 0.0 or 0.5

### Task-wise Functions
* Summarization: ```generate_topic_segmented_meeting_transcript_combined_v2``` in ```llm_core/llm_summarization.py```.
    * Input: Entire transcript + Hyperparameters
    * Output: Transcript Summary
* Meeting-level Action Item Extraction: ```generate_meeting_action_item_v2``` in ```llm_core/lllm_meeting_actions.py```.
    * Input: Entire transcript + Hyperparameters
    * Output: Meeting-level action items
* Participant-level Action Item Extraction: ```generate_person_action_item_v2``` in ```llm_core/llm_part_actions.py```.
    * Input: Entire transcript + Hyperparameters
    * Output: Participant-level Action Items


### License 
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0

