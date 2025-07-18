# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
sys.path.append( '..' )

from llm_core.bedrock_helper import  NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID

from llm_core.llm_summarizer import input_to_merged_trans

import pandas as pd
import numpy as np
import json

exp_name = 'final_json_06022025'
input_folder_path = "../data/test/"
output_folder_path = f"../results/{exp_name}/"

model_family_list = [ 'FINAL' ]

model_ids = [ NOVA_PREMIER_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_LITE_MODEL_ID,NOVA_MICRO_MODEL_ID]

df_cols = model_ids

summary_latency_df = pd.DataFrame( columns= df_cols )
summary_cost_df = pd.DataFrame( columns= df_cols ) 

action_latency_df = pd.DataFrame( columns= df_cols )
action_cost_df = pd.DataFrame( columns= df_cols ) 

part_action_latency_df = pd.DataFrame( columns= df_cols )
part_action_cost_df = pd.DataFrame( columns= df_cols ) 

for i in range( 1, 31 ):
    row_dict_summary_latency = {}
    row_dict_action_latency = {}
    row_dict_part_action_latency = {}

    row_dict_summary_cost = {}
    row_dict_action_cost = {}
    row_dict_part_action_cost = {}

    for model_family in model_family_list:
        result_file_path = output_folder_path + f"test_{i}_{model_family}.json"

        with open( result_file_path, 'r', encoding='utf-8' ) as f:
            input_data = json.load( f )

        len_gen = len(input_data[ 'participant_action_items' ])

        for j in range( len_gen ):
            summary_j = input_data[ 'meeting_summary' ][ j ]
            model_name_j = summary_j[ 'source' ]
            row_dict_summary_latency[ model_name_j ] = summary_j[ 'latency' ]
            row_dict_summary_cost[ model_name_j ] = summary_j[ 'cost' ]

            action_j = input_data[ 'meeting_level_action_items' ][j]
            model_action_j = action_j[ 'source' ]
            row_dict_action_latency[ model_name_j ] = action_j[ 'latency' ]
            row_dict_action_cost[ model_name_j ] = action_j[ 'cost' ]

            part_action_j = input_data[ 'participant_action_items' ][j]
            model_part_action_j = part_action_j[ 'source' ]
            row_dict_part_action_latency[ model_part_action_j ] = part_action_j[ 'latency' ]
            row_dict_part_action_cost[ model_part_action_j ] = part_action_j[ 'cost' ]

    summary_latency_row = pd.DataFrame([row_dict_summary_latency])
    summary_latency_df = pd.concat( [ summary_latency_df, summary_latency_row ], ignore_index=True)
    summary_cost_row = pd.DataFrame([row_dict_summary_cost])
    summary_cost_df = pd.concat( [ summary_cost_df, summary_cost_row ], ignore_index=True)

    action_latency_row = pd.DataFrame([row_dict_action_latency])
    action_latency_df = pd.concat( [ action_latency_df, action_latency_row ], ignore_index=True)

    action_cost_row = pd.DataFrame([row_dict_action_cost])
    action_cost_df = pd.concat( [ action_cost_df, action_cost_row ], ignore_index=True)

    part_action_latency_row = pd.DataFrame([row_dict_part_action_latency])
    part_action_latency_df = pd.concat( [ part_action_latency_df, part_action_latency_row ], ignore_index=True)
    part_action_cost_row = pd.DataFrame([row_dict_part_action_cost])
    part_action_cost_df = pd.concat( [ part_action_cost_df, part_action_cost_row ], ignore_index=True)

summary_latency_df.to_csv( f'../results/{exp_name}_meeting_summary_latency.csv' )
action_latency_df.to_csv( f'../results/{exp_name}_meeting_level_action_items_latency.csv' )
part_action_latency_df.to_csv( f'../results/{exp_name}_participant_action_items_latency.csv' )

summary_cost_df.to_csv( f'../results/{exp_name}_meeting_summary_cost.csv' )
action_cost_df.to_csv( f'../results/{exp_name}_meeting_level_action_items_cost.csv' )
part_action_cost_df.to_csv( f'../results/{exp_name}_participant_action_items_cost.csv' )


# Summarize latency/cost
df_vis_cols = [ "Average", "Median", "P10", "P90", "P995"]

summary_latency_df_vis = pd.DataFrame( columns=df_vis_cols )
action_latency_df_vis = pd.DataFrame( columns=df_vis_cols )
part_action_latency_df_vis = pd.DataFrame( columns=df_vis_cols )

summary_cost_df_vis = pd.DataFrame( columns=df_vis_cols )
action_cost_df_vis = pd.DataFrame( columns=df_vis_cols )
part_action_cost_df_vis = pd.DataFrame( columns=df_vis_cols )


def get_stats( input_list ):
    avg = np.average( input_list )
    median = np.median( input_list )
    p10 = np.quantile( input_list, 0.1 )
    p90 = np.quantile( input_list, 0.9 )
    p995 = np.quantile( input_list, 0.995 )

    stat_dict = { 'Average': avg, 'Median': median, 'P10': p10, 'P90': p90, 'P995': p995 }

    return stat_dict

for model_id in model_ids:
    summary_latency_stat = get_stats( summary_latency_df[ model_id ].tolist() )
    summary_latency_df_vis.loc[ model_id ] = summary_latency_stat

    action_latency_stat = get_stats( action_latency_df[ model_id ].tolist() )
    action_latency_df_vis.loc[ model_id ] = action_latency_stat

    part_action_latency_stat = get_stats( part_action_latency_df[ model_id ].tolist() )
    part_action_latency_df_vis.loc[ model_id ] = part_action_latency_stat

    summary_cost_stat = get_stats( summary_cost_df[ model_id ].tolist() )
    summary_cost_df_vis.loc[ model_id ] = summary_cost_stat

    action_cost_stat = get_stats( action_cost_df[ model_id ].tolist() )
    action_cost_df_vis.loc[ model_id ] = action_cost_stat

    part_action_cost_stat = get_stats( part_action_cost_df[ model_id ].tolist() )
    part_action_cost_df_vis.loc[ model_id ] = part_action_cost_stat


summary_latency_df_vis = summary_latency_df_vis.round( 2 )
summary_latency_df_vis.to_csv( f'../results/{exp_name}_meeting_summary_latency_stats.csv' )

action_latency_df_vis = action_latency_df_vis.round( 2 )
action_latency_df_vis.to_csv( f'../results/{exp_name}_meeting_action_latency_stats.csv' )

part_action_latency_df_vis = part_action_latency_df_vis.round( 2 )
part_action_latency_df_vis.to_csv( f'../results/{exp_name}_meeting_part_action_latency_stats.csv' )

summary_cost_df_vis = summary_cost_df_vis.mul(100).round( 3 )
summary_cost_df_vis.to_csv( f'../results/{exp_name}_meeting_summary_cost_stats.csv' )

action_cost_df_vis = action_cost_df_vis.mul(100).round( 3 )
action_cost_df_vis.to_csv( f'../results/{exp_name}_meeting_action_cost_stats.csv' )

part_action_cost_df_vis = part_action_cost_df_vis.mul(100).round( 3 )
part_action_cost_df_vis.to_csv( f'../results/{exp_name}_meeting_part_action_cost_stats.csv' )
