# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append( '..' ) 

import pandas as pd
import numpy as np
import time 

from llm_eval.bedrock.bedrock_eval import summary_faithfulness_score, summary_qa_score, summarization_score

from llm_core.bedrock_helper import  NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID, SONNET35_MODEL_ID


def get_stats( input_list ):
    avg = np.average( input_list )
    median = np.median( input_list )
    p10 = np.quantile( input_list, 0.1 )
    p90 = np.quantile( input_list, 0.9 )
    p995 = np.quantile( input_list, 0.995 )

    stat_dict = { 'Average': avg, 'Median': median, 'P10': p10, 'P90': p90, 'P995': p995 }

    return stat_dict

exp_name = 'final_json_06022025'
input_folder_path = "../data/test/"
output_folder_path = f"../results/{exp_name}/"

model_family_list = [ 'FINAL' ]

tasks = ["participant_action_items", "meeting_level_action_items","meeting_summary"]


for task in tasks:
    data_path = f"../results/{exp_name}_{task}.csv"
    data_df = pd.read_csv(data_path )

    judge_model_id = SONNET35_MODEL_ID

    model_ids = [NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID]

    df_vis_cols = [ "Average", "Median", "P10", "P90", "P995"]

    summ_df_vis = pd.DataFrame( columns=df_vis_cols )
    qa_df_vis = pd.DataFrame( columns=df_vis_cols )
    faith_df_vis = pd.DataFrame( columns=df_vis_cols )

    for j, model_id in enumerate( model_ids ):
        print( "=============================" )
        print( f"Model: {model_id}" )
        faith_list = []
        # qa_list = []
        # summary_list = []

        for i in range( 1, 31 ):
            print( "-------------------------------" )
            print( f"Task: {task}")
            print( f"Model: {model_id}, {j+1} / {len(model_ids)}")
            print( f"Data {i+1}")

            data_i = data_df.iloc[i]
            transcript = data_i[ 'transcript' ]
            response = data_i[ model_id ]
            # summ_score, qa_score, concsi_score = summarization_score( context=transcript,
            #                                                         summary=response,
            #                                                         model_id=judge_model_id )

            time.sleep(30)
            faith_score, decision_list, reasoning = summary_faithfulness_score( summary=response, 
                                                                            context=transcript,                                                                       
                                                                            model_id=judge_model_id )

            ######################################
            #      Throttling Error Handling     #
            ######################################
            # try:
            #     summ_score, qa_score, concsi_score = summarization_score( context=transcript,
            #                                                             summary=response,
            #                                                             model_id=judge_model_id )
            # except Exception as e:
            #     time.sleep( 60 )
            #     summ_score, qa_score, concsi_score = summarization_score( context=transcript,
            #                                                             summary=response,
            #                                                             model_id=judge_model_id )

            # try:
            #     faith_score, decision_list, reasoning = summary_faithfulness_score( summary=response, 
            #                                                                     context=transcript,                                                                       
            #                                                                     model_id=judge_model_id )
            # except Exception as e:
            #     time.sleep( 60 )
            #     faith_score, decision_list, reasoning = summary_faithfulness_score( summary=response, 
            #                                                                     context=transcript,                                                                       
            #                                                                     model_id=judge_model_id )

            faith_list.append( faith_score )
            # qa_list.append( qa_score )
            # summary_list.append( summ_score )

        faith_stat = get_stats( faith_list )
        # qa_stat = get_stats( qa_list )
        # summ_stat = get_stats( summary_list )

        faith_df_vis.loc[ model_id ] = faith_stat
        # qa_df_vis.loc[ model_id ] = qa_stat
        # summ_df_vis.loc[ model_id ] = summ_stat
        
    faith_df_vis = faith_df_vis.round( 2 )
    faith_df_vis.to_csv( f'../results/{exp_name}_{task}_faithfulness_score.csv' )

    # qa_df_vis = qa_df_vis.round( 2 )
    # qa_df_vis.to_csv( f'../results/{exp_name}_meeting_summary_qa_score.csv' )

    # summ_df_vis = summ_df_vis.round( 2 )
    # summ_df_vis.to_csv( f'../results/{exp_name}_meeting_summary_summ_score.csv' )