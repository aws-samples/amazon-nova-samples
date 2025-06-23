# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from llm_core.bedrock_helper import get_bedrock_response
from llm_core.bedrock_helper import SONNET35_MODEL_ID,
import numpy as np
import time
from typing import List

FAITHFULNESS_SYSTEM_PROMPT = """Consider the given context in <context> tags and following statements in a summary provided in <summary> tags, then determine whether they are supported by the information present in the context. 
Provide a brief explanation for each statement before arriving at the verdict. 
The verdict must be only yes or no in one word. 
If a statement is only partially true, or uncertain considering the context, its verdict is no. 
You must provide the list of the vertdicts in order at the end with a prefix "Final Verdicts: " in one line sentence. 
Strictly follow the specified format as shown in the below example.

<example>
<context>
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
</context>
<summary>
1. John is majoring in Biology.\n2. John is taking a course on Artificial Intelligence.\n3. John is a dedicated student.\n4. John has a part-time job.\n5. John is interested in computer programming.\n
</summary>

Assistant:
<reasoning>
1. John is majoring in Biology.
Explanation: John's major is explicitly mentioned as Computer Science. There is no information suggesting he is majoring in Biology.  Verdict: No.
2. John is taking a course on Artificial Intelligence.
Explanation: The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI. Verdict: No.
3. John is a dedicated student.
Explanation: The prompt states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication. Verdict: Yes.
4. John has a part-time job.
Explanation: There is no information given in the context about John having a part-time job. Therefore, it cannot be deduced that John has a part-time job.  Verdict: No.
5. John is interested in computer programming.
Explanation: The context states that John is pursuing a degree in Computer Science, which implies an interest in computer programming. Verdict: Yes.
</reasoning>

<verdict>
No. No. Yes. No. Yes. 
</verdict>
</example>
"""

def build_faithfulness_prompt( summary, context ):
    '''
    Helper function to build a faithfulness score template. 
    '''

    prompt = f'''Here's the context:
<context>
{context}
</context>

Here's the summary that you need to evaluate based on the context:
<summary>
{summary}
</summary>
'''
    
    return prompt


def summary_faithfulness_score_response( summary: str,
                                        context: str, 
                                        max_tokens=4000,
                                        temp=0.1,
                                        topK=50,
                                        stop_sequences=["Human:", "</verdict>"],
                                        model_id = SONNET35_MODEL_ID,
                                        text_only=True ):
    '''
    Summary faithfulness score 
    '''
    input_prompt = build_faithfulness_prompt( summary, context )

    response = get_bedrock_response( user_message=input_prompt, 
                                    system=FAITHFULNESS_SYSTEM_PROMPT, 
                                    assistant_message="<reasoning>",
                                    max_tokens=max_tokens,
                                    temp=temp,
                                    topK= topK,
                                    stop_sequences=stop_sequences,
                                    model_id=model_id,
                                    text_only=text_only )

    return response

def summary_parse_verdicts( response ):
    final_verdict_sep_list = [ 'Final Verdicts: ', 'Final verdict for each statement in order: ', 'Final verdicts in order: ', '<verdict>\n', '<verdict>' ]
    verdict_sep_found = False
    answer_sep_list = [ '. ', ', ' ]
    answer_sep_found = False
    
    for final_verdict_sep in final_verdict_sep_list:
        if response.find( final_verdict_sep ) == -1:
            continue
        else:
            reasons = response.split( final_verdict_sep )[ 0 ] 
            verdicts = response.split( final_verdict_sep )[ 1 ]
            verdicts = verdicts.replace("</verdict>", "" )
            verdicts = verdicts.strip()

            for answer_sep in answer_sep_list:
                if verdicts.find( answer_sep ) == -1:
                    continue
                else:
                    verdicts_list = verdicts.split( answer_sep )
                    answer_sep_found = True
                    break
                
            verdict_sep_found = True
            break
    
    if not (verdict_sep_found and answer_sep_found):
        print( response )
        raise ValueError( 'LLM response did not fit the specified format' )
    
    return verdicts_list, reasons

def summary_score_from_verdicts( verdicts_list ):
    decision_list = []
    
    for i in range( len( verdicts_list ) ):
        if verdicts_list[ i ].lower() in ['yes', '\nyes', 'yes.', '\nyes.', 'yes.\n', 'yes,', '\nyes,', 'yes,\n', 'yes.\n</verdict>', 'yes.</verdict>', 'yes\n</verdict>', 'yes</verdict>'  ]:
            decision_list.append( 1 )
        elif verdicts_list[ i ].lower() in ['no', '\nno', 'no.', '\nno.', 'no.\n', 'no,', '\nno,', 'no,\n', 'no.\n</verdict>', 'no.</verdict>', 'no\n</verdict>', 'no</verdict>']:
            decision_list.append( 0 )
        else:
            decision_list.append( np.NAN )
    
    score = np.nanmean( decision_list )

    return score, decision_list

def summary_faithfulness_score( summary: str,
                               context: str, 
                               max_tokens=4000,
                               temp=0.1,
                               topK=50,
                               stop_sequences=["Human:", "</verdict>"],
                               model_id = SONNET35_MODEL_ID,
                               text_only=True,
                               verbose=True ):
    '''
    Faithfulness score from the RAGAS package with Bedrock FMs.
    Reference: https://github.com/explodinggradients/ragas/blob/main/src/ragas/metrics/faithfulnes.py
    '''
    response = summary_faithfulness_score_response( summary = summary, 
                                                   context=context, 
                                                   max_tokens=max_tokens, 
                                                   temp=temp, 
                                                   topK=topK, 
                                                   stop_sequences=stop_sequences, 
                                                   model_id=model_id, 
                                                   text_only=text_only)
    if verbose:
        print( "=================================================" )
        print( response )
                
    verdicts_list, reasons = summary_parse_verdicts( response )
    
    if verbose:
        print( verdicts_list )
    
    faith_score, decision_list = summary_score_from_verdicts( verdicts_list )
    
    return faith_score, decision_list, reasons


######################## 
#       QA Score       #
######################## 

QA_QUESTION_GENERATION_SYSTEM_PROMPT = """Generate 8-10 key questions and their answers strictly considering a meeting transcript in <context> tags.
The key questions must cover the most important discussion items of the current meeting provided in the meeting transcript for the meeting summary.
The answers must be concise, no more than 5 words, while covering enough details to answer a question and relevant to the discussion in the meeting.
Strictly follow the specified format as shown in the below example.

<example>
<context>
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
</context>

Assistant:
<qa_pair>
1. Question: Which university is John a student at? Answer: XYZ University
2. Question: What is John's major? Answer: Computer Science
3. Question: What is one of the courses John is enrolled this semester? Answer: Data Structures
4. Question: What does John spend a significant amount of time? Answer: studying
5. Question: Where does John often stay late? Answer: library
</qa_pair>
</example>
"""
def build_question_generation_prompt( context ):
    '''
    Helper function to build a question generation template for QA score.
    '''

    prompt = f'''Here's the context:
<context>
{context}
</context>
'''
    
    return prompt

def qa_question_generation( context: str, 
                           max_tokens=4000,
                           temp=0.1,
                           topK=50,
                           stop_sequences=["Human:", "</qa_pair>"],
                           model_id = SONNET35_MODEL_ID,
                           text_only=True ):
    '''
    Questions generation function for QA score. Generate questions from the context.
    '''
    input_prompt = build_question_generation_prompt( context )

    response = get_bedrock_response( user_message=input_prompt, 
                                    system=QA_QUESTION_GENERATION_SYSTEM_PROMPT, 
                                    assistant_message="<qa_pair>",
                                    max_tokens=max_tokens,
                                    temp=temp,
                                    topK= topK,
                                    stop_sequences=stop_sequences,
                                    model_id=model_id,
                                    text_only=text_only )
    
    question_list, answer_list = q2_parse_question_answer( response )
    
    return question_list, answer_list
     

def q2_parse_question_answer( question_answer: str ):
    '''
    Helper function for Q2 score. Parse questions and answers from the generated Q&A pairs.
    
    Args:
        question_answer (str): Generated Q&A 
    Returns:
        question_list (List[str]): List of questions
        answer_list (List[str]): List of answers
    '''
    question_answer = question_answer.replace( "<qa_pair>\n", "")
    question_answer = question_answer.replace( "\n</qa_pair>", "")
    question_answer = question_answer.replace( "<qa_pair>", "")
    question_answer = question_answer.replace( "</qa_pair>", "")

    qa_lines = question_answer.split( '\n' )
    qa_lines = list(filter(None, qa_lines))
    
    question_list = [] 
    answer_list = []
    
    for qa_line in qa_lines:
        if qa_line.find( 'Question: ' ) == -1 or qa_line.find( 'Answer: ' ) == -1:
            continue
        q_split = qa_line.split( 'Question: ' )
        qa_split = q_split[-1].split( 'Answer: ' )
        question = qa_split[0]
        answer = qa_split[1]
        
        question_list.append( question )
        answer_list.append( answer )
    
    return question_list, answer_list

QA_ANSWER_SUMMARY_SYSTEM_PROMPT = """Answer the given questions from a meeting transcript strictly considering the given summary of the meeting in <summary> tags.
The answers must be concise, no more than 5 words, while covering enough details to answer a question.
Strictly follow the specified format as shown in the below example.

<example>
<summary>
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
</summary>

<questions>
Which university is John a student at?, What is John's major?, What is one of the courses John is enrolled this semester?, What does John spend a significant amount of time?, Where does John often stay late?
</questions>

Assistant:
<qa_pair>
1. Question: Which university is John a student at? Answer: XYZ University
2. Question: What is John's major? Answer: Computer Science
3. Question: What is one of the courses John is enrolled this semester? Answer: Data Structures
4. Question: What does John spend a significant amount of time? Answer: studying
5. Question: Where does John often stay late? Answer: library
</qa_pair>
</example>
"""
def build_answer_generation_prompt( question_list, summary ):
    '''
    Helper function to build a question generation template for QA score.
    '''
    questions = ', '.join( question_list ) + '\n'

    prompt = f'''Here are questions and summary:
<questions>
{questions}
</questions>
<summary>
{summary}
</summary>
'''
    
    return prompt


def qa_answer_from_summary( question_list: List[str],
                           summary, 
                           max_tokens=4000,
                           temp=0.1,
                           topK=50,
                           stop_sequences=["Human:", "</qa_pair>"],
                           model_id = SONNET35_MODEL_ID,
                           text_only=True ):
    '''
    Helper function for Q2 score. Get answers from the generated questions based on GT.
        
    Args:
        question_list (List[str]): List of generated questions.
        gt_knowledge (str): Ground truth knowledge
        agent_fm (str): Bedrock agent to use. 'claude', 'claude_v2', 'titan'
    
    Returns:
        question_list (List[str]): List of answers from GT.
    '''
    
    input_prompt = build_answer_generation_prompt( question_list, summary )

    response = get_bedrock_response( user_message=input_prompt, 
                                    system=QA_ANSWER_SUMMARY_SYSTEM_PROMPT, 
                                    assistant_message="<qa_pair>",
                                    max_tokens=max_tokens,
                                    temp=temp,
                                    topK= topK,
                                    stop_sequences=stop_sequences,
                                    model_id=model_id,
                                    text_only=text_only )
    
    _, answer_list = q2_parse_question_answer( response )
    
    return answer_list

QA_ANSWER_COMPARISON_SYSTEM_PROMPT = """Strictly considering the given context of a meeting transcript in <context> tags and questions in <questions> tags, 
compare the given two sets of answers. Answer Yes when the corresponding answers in the two sets have the same meaning, otherwise answer No. 
Do not deviate from the specified format provided in the example in <example> tags.

<example>
<context>
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
</context>

<questions>
Which university is John a student at?, What is John's major?, What is one of the courses John is enrolled this semester?, What does John spend a significant amount of time?, Where does John often stay late?
</questions>

<answer_1>
XYZ University, Computer Science, Data Structures, studying, university library
</answer_1>

<answer_2>
CAT University, Computer Science, DS, partying, library
<answer_2>

Assistant:
<verdict>
No, Yes, Yes, No, Yes
</verdict>
</example>
"""

def build_qa_score_answer_comparison_prompt( context, 
                                            question_list, 
                                            context_answer_list, 
                                            summary_answer_list ):
    questions = ', '.join( question_list )
    answer_1 = ', '.join( context_answer_list )
    answer_2 = ', '.join( summary_answer_list )

    prompt = f"""Here are the context, the set of questions and two sets of answers:
<context>
{context}
</context>
<questions>
{questions}
</questions>

<answer_1>
{answer_1}
</answer_1>

<answer_2>
{answer_2}
</answer_2>
"""
    return prompt

def qa_score_answer_comparison( context,
                               question_list,
                               summary_answer_list, 
                               context_answer_list, 
                               max_tokens=4000,
                               temp=0.1,
                               topK=50,
                               stop_sequences=["Human:", "</verdict>"],
                               model_id = SONNET35_MODEL_ID,
                               text_only=True,
                               verbose=True ):
    '''
    QA score. Answer comparison function
    '''

    input_prompt = build_qa_score_answer_comparison_prompt( context, question_list, context_answer_list, summary_answer_list )

    response = get_bedrock_response( user_message=input_prompt, 
                                    system=QA_ANSWER_COMPARISON_SYSTEM_PROMPT, 
                                    # assistant_message="<verdict>",
                                    max_tokens=max_tokens,
                                    temp=temp,
                                    topK= topK,
                                    stop_sequences=stop_sequences,
                                    model_id=model_id,
                                    text_only=text_only )

    verdicts_list, reasons = summary_parse_verdicts( response )
    
    if verbose:
        print( verdicts_list )
    
    qa_score, decision_list = summary_score_from_verdicts( verdicts_list )
    
    return qa_score, decision_list, reasons

def summary_qa_score( summary, 
                     context, 
                     max_tokens=4000,
                     temp=0.1,
                     topK=50,
                     stop_sequences=["Human:", "</verdict>"],
                     model_id = SONNET35_MODEL_ID,
                     text_only=True,
                     verbose=True ):
    '''
    Summary QA score. Measure the coverage of summary with questions generated from meeting transcript.
    Modified version.
    Reference: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/summarization_score/
    '''
    
    question_list, context_answer_list = qa_question_generation( context=context,
                                                        max_tokens=max_tokens,
                                                        temp=temp,
                                                        topK= topK,
                                                        stop_sequences=stop_sequences,
                                                        model_id=model_id,
                                                        text_only=text_only )

    print( question_list )
    print( context_answer_list )
    print( len( question_list ) )
    print( len( context_answer_list ) )
    print( summary )

    summary_answer_list = qa_answer_from_summary( question_list,
                                                 summary,
                                                 max_tokens=max_tokens,
                                                 temp=temp,
                                                 topK= topK,
                                                 stop_sequences=stop_sequences,
                                                 model_id=model_id,
                                                 text_only=text_only )

    print( summary_answer_list )
    print( len( summary_answer_list ) )

    qa_score, decision_list, reasons = qa_score_answer_comparison( context,
                                                                  question_list,
                                                                  summary_answer_list, 
                                                                  context_answer_list, 
                                                                  max_tokens=max_tokens,
                                                                  temp=temp,
                                                                  topK=topK,
                                                                  stop_sequences=stop_sequences,
                                                                  model_id=model_id,
                                                                  text_only=text_only,
                                                                  verbose=verbose)
    
    return qa_score, decision_list, reasons


def conciseness_score( summary, context ):
    '''
    Conciseness score
    Reference: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/summarization_score/
    '''
    len_context = len( context )
    len_summary = len( summary )

    conciseness_score = 1 - min( len_context, len_summary ) / len_context

    return conciseness_score

def summarization_score( summary,
                        context,
                        qa_weight=0.5,
                        max_tokens=4000,
                        temp=0.1,
                        topK=50,
                        stop_sequences=["Human:", "</verdict>"],
                        model_id = SONNET35_MODEL_ID,
                        text_only=True,
                        verbose=True ):
    '''
    Summarization score.
    Reference: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/summarization_score/
    '''

    qa_score, _, _ = summary_qa_score( summary, 
                                      context, 
                                      max_tokens=max_tokens,
                                      temp=temp,
                                      topK=topK,
                                      stop_sequences=stop_sequences,
                                      model_id = model_id,
                                      text_only=text_only,
                                      verbose=verbose )
    
    concsi_score = conciseness_score( summary, context )
    summ_score = qa_weight * qa_score + (1-qa_weight) * concsi_score

    return summ_score, qa_score, concsi_score