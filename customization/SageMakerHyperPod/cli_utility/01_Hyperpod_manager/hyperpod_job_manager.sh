#!/bin/bash

# HyperPod Job Manager
# A comprehensive tool for managing HyperPod jobs including submission, monitoring, and administration

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Formatting helpers
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Default values
JOB_NAME=""
NAMESPACE="kubeflow"
ACTION="monitor"
CLUSTER_NAME=""
CLUSTER_ID=""
RIG_NAME=""

# Container configuration arrays
declare -a CONTAINER_NAMES=("nova-sft" "nova-dpo" "nova-ppo" "nova-cpt" "nova-eval")
declare -a CONTAINER_URIS=(
    "708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-SFT-latest"
    "708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-DPO-latest"
    "078496829476.dkr.ecr.us-west-2.amazonaws.com/nova-fine-tune-repo:HP-PPO-latest"
    "078496829476.dkr.ecr.us-west-2.amazonaws.com/nova-fine-tune-repo:HP-CPT-latest"
    "708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-evaluation-repo:SM-HP-Eval-latest"
)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --job_name)
            JOB_NAME="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --action)
            ACTION="$2"
            shift 2
            ;;
        --cluster_name|--cluster-name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --cluster_id|--cluster-id)
            CLUSTER_ID="$2"
            shift 2
            ;;
        --rig_name|--rig-name)
            RIG_NAME="$2"
            shift 2
            ;;
        *)
            # For backward compatibility, handle positional arguments
            if [ -z "$JOB_NAME" ]; then
                JOB_NAME="$1"
            elif [ "$NAMESPACE" = "kubeflow" ]; then
                NAMESPACE="$1"
            elif [ "$ACTION" = "monitor" ]; then
                ACTION="$1"
            fi
            shift
            ;;
    esac
done

# Show usage if required parameters are missing
if [ -z "$JOB_NAME" ] && [ "$ACTION" != "submit" ] && [ "$ACTION" != "list" ]; then
    print_header "HyperPod Job Manager - Usage"
    echo "A comprehensive tool for managing HyperPod jobs"
    echo ""
    echo "Flags:"
    echo "  --job_name <name>      Job name (required for monitor/cancel)"
    echo "  --namespace <ns>       Kubernetes namespace (default: kubeflow)"
    echo "  --action <action>      Action to perform (default: monitor)"
    echo "  --cluster-name <name>  Cluster name for CloudWatch logs"
    echo "  --cluster-id <id>      Cluster ID for CloudWatch logs"
    echo "  --rig-name <name>      RIG name for CloudWatch logs"
    echo ""
    echo "Actions:"
    echo "  submit   - Submit a new job (interactive)"
    echo "  monitor  - Monitor job status and logs"
    echo "  list     - List all jobs"
    echo "  cancel   - Cancel a running job"
    echo ""
    echo "Examples:"
    echo "  # Submit new job"
    echo "  $0 --action submit"
    echo ""
    echo "  # Monitor job with logs"
    echo "  $0 --job_name my-job --action monitor --cluster-name my-cluster --cluster-id cluster123 --rig-name my-rig"
    echo ""
    echo "  # List all jobs"
    echo "  $0 --action list"
    echo ""
    echo "  # Cancel job"
    echo "  $0 --job_name my-job --action cancel"
    exit 1
fi

# Function to show available containers
show_containers() {
    print_section "Available Containers"
    for i in "${!CONTAINER_NAMES[@]}"; do
        echo -e "  ${CYAN}$i)${NC} ${CONTAINER_NAMES[$i]}"
        echo "     ${CONTAINER_URIS[$i]}"
        echo ""
    done
}

# Function to submit a new job
submit_job() {
    print_header "Submit New HyperPod Job"
    
    # Get job parameters interactively
    echo -e "${CYAN}Job Configuration${NC}"
    read -p "Enter run name (used to generate job name): " RUN_NAME
    if [ -z "$RUN_NAME" ]; then
        print_error "Run name is required!"
        exit 1
    fi
    
    read -p "Enter namespace [$NAMESPACE]: " INPUT_NAMESPACE
    if [ -n "$INPUT_NAMESPACE" ]; then
        NAMESPACE=$INPUT_NAMESPACE
    fi
    
    read -p "Enter recipe path: " RECIPE_PATH
    if [ -z "$RECIPE_PATH" ]; then
        print_error "Recipe path is required!"
        exit 1
    fi
    
    echo ""
    show_containers
    read -p "Choose container (enter key from above or 'custom' for custom URI): " CONTAINER_KEY
    
    if [ "$CONTAINER_KEY" = "custom" ]; then
        read -p "Enter custom container URI: " CONTAINER_URI
    else
        CONTAINER_URI=${CONTAINER_URIS[$CONTAINER_KEY]}
        if [ -z "$CONTAINER_URI" ]; then
            print_warning "Invalid container key! Using default."
            CONTAINER_URI="763104351884.dkr.ecr.us-west-2.amazonaws.com/huggingface-pytorch-training:2.0.0-transformers4.28.1-gpu-py310-cu118-ubuntu20.04-sagemaker"
        fi
        
        # Special handling for evaluation container
        if [ "$CONTAINER_KEY" = "4" ]; then
            print_section "Evaluation Configuration"
            read -p "Enter model manifest path (s3://.../manifest.json): " MODEL_PATH
            if [ -z "$MODEL_PATH" ]; then
                print_error "Model manifest path is required for evaluation!"
                exit 1
            fi
            EVAL_PARAMS="\"recipes.run.model_name_or_path\": \"$MODEL_PATH\""
            
            read -p "Using custom evaluation data? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                read -p "Enter evaluation data S3 path: " EVAL_DATA_PATH
                if [ -z "$EVAL_DATA_PATH" ]; then
                    print_error "Evaluation data path is required!"
                    exit 1
                fi
                EVAL_PARAMS="$EVAL_PARAMS, \"recipes.run.data_s3_path\": \"$EVAL_DATA_PATH\""
            fi
            
            # Store for later use in ADDITIONAL_PARAMS
            if [ -n "$ADDITIONAL_PARAMS" ]; then
                ADDITIONAL_PARAMS="$EVAL_PARAMS, $ADDITIONAL_PARAMS"
            else
                ADDITIONAL_PARAMS="$EVAL_PARAMS"
            fi
        fi
    fi
    
    print_section "Resource Configuration"
    read -p "Enter instance type (e.g., ml.p4d.24xlarge): " INSTANCE_TYPE
    if [ -z "$INSTANCE_TYPE" ]; then
        print_error "Instance type is required!"
        exit 1
    fi
    
    print_section "S3 Configuration (Optional)"
    read -p "Enter input S3 data path: " INPUT_S3_DATA
    read -p "Enter output S3 path: " OUTPUT_S3_PATH
    read -p "Enter tensorboard S3 path: " TENSORBOARD_S3_PATH
    
    print_section "Additional Parameters"
    echo "Enter additional parameters in JSON format, or press Enter to skip"
    echo "Example: \"recipes.training_config.model\": 1e-4, \"recipes.training_config.trainer.max_epochs\": 1"
    read -p "Additional parameters: " ADDITIONAL_PARAMS
    
    # Build the override parameters JSON
    OVERRIDE_PARAMS="{"
    OVERRIDE_PARAMS="$OVERRIDE_PARAMS\"instance_type\": \"$INSTANCE_TYPE\""
    OVERRIDE_PARAMS="$OVERRIDE_PARAMS, \"container\": \"$CONTAINER_URI\""
    OVERRIDE_PARAMS="$OVERRIDE_PARAMS, \"recipes.run.name\": \"$RUN_NAME\""
    
    if [ -n "$INPUT_S3_DATA" ]; then
        OVERRIDE_PARAMS="$OVERRIDE_PARAMS, \"recipes.run.data_s3_path\": \"$INPUT_S3_DATA\""
    fi
    
    if [ -n "$OUTPUT_S3_PATH" ]; then
        OVERRIDE_PARAMS="$OVERRIDE_PARAMS, \"recipes.run.output_s3_path\": \"$OUTPUT_S3_PATH\""
    fi
    
    if [ -n "$TENSORBOARD_S3_PATH" ]; then
        OVERRIDE_PARAMS="$OVERRIDE_PARAMS, \"recipes.run.tensorboard_s3_path\": \"$TENSORBOARD_S3_PATH\""
    fi
    
    if [ -n "$ADDITIONAL_PARAMS" ]; then
        OVERRIDE_PARAMS="$OVERRIDE_PARAMS, $ADDITIONAL_PARAMS"
    fi
    
    OVERRIDE_PARAMS="$OVERRIDE_PARAMS}"
    
    # Create configs directory if it doesn't exist
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    CONFIGS_DIR="$SCRIPT_DIR/configs"
    mkdir -p "$CONFIGS_DIR"

    # Generate timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    # Create config JSON
    CONFIG_JSON="{"
    CONFIG_JSON="$CONFIG_JSON\"run_name\": \"$RUN_NAME\","
    CONFIG_JSON="$CONFIG_JSON\"namespace\": \"$NAMESPACE\","
    CONFIG_JSON="$CONFIG_JSON\"recipe_path\": \"$RECIPE_PATH\","
    CONFIG_JSON="$CONFIG_JSON\"override_parameters\": $OVERRIDE_PARAMS,"
    CONFIG_JSON="$CONFIG_JSON\"submission_time\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    CONFIG_JSON="$CONFIG_JSON\"status\": \"submitted\","
    CONFIG_JSON="$CONFIG_JSON\"last_updated\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\""
    CONFIG_JSON="$CONFIG_JSON}"

    # Show the final command
    print_section "Job Submission Command"
    FINAL_COMMAND="hyperpod start-job --namespace $NAMESPACE --recipe $RECIPE_PATH --override-parameters '$OVERRIDE_PARAMS'"
    echo "$FINAL_COMMAND"
    echo ""
    
    # Confirm execution
    read -p "Execute this command? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_section "Submitting Job"
        # Execute the command and capture output
        SUBMISSION_OUTPUT=$(eval "$FINAL_COMMAND")
        SUBMISSION_STATUS=$?

        if [ $SUBMISSION_STATUS -eq 0 ]; then
            echo "$SUBMISSION_OUTPUT"
            # Extract job name from output
            JOB_NAME=$(echo "$SUBMISSION_OUTPUT" | grep -oE 'NAME: [^[:space:]]+' | cut -d' ' -f2)
            if [ -n "$JOB_NAME" ]; then
                # Save config with job name and timestamp
                CONFIG_FILE="$CONFIGS_DIR/${JOB_NAME}_${TIMESTAMP}.json"
                echo "$CONFIG_JSON" > "$CONFIG_FILE"
                print_success "Configuration saved to: $CONFIG_FILE"
                print_success "Job submitted successfully! Actual job name: $JOB_NAME"
                echo ""
                print_section "Next Steps"
                echo "Monitor your job with:"
                echo "$0 --job_name $JOB_NAME --namespace $NAMESPACE --action monitor"
            else
                print_warning "Job submission attempted but couldn't parse job name from output."
                print_warning "Check submission results and use actual job name for monitoring."
            fi
        else
            print_error "Job submission failed with status: $SUBMISSION_STATUS"
            print_error "Check the error output above for details."
        fi
    else
        print_warning "Job submission cancelled."
        echo "You can copy and modify the command above if needed."
    fi
}

case $ACTION in
    "list")
        print_header "HyperPod Jobs"
        hyperpod list-jobs --namespace $NAMESPACE
        exit 0
        ;;
    "cancel")
        print_header "Cancel Job: $JOB_NAME"
        hyperpod cancel-job --job-name $JOB_NAME --namespace $NAMESPACE
        print_success "Job cancellation requested."
        ;;
    "submit")
        submit_job
        exit 0
        ;;
    "monitor")
        print_header "Job Status"
        JOB_STATUS=$(hyperpod list-jobs --namespace $NAMESPACE)
        echo "$JOB_STATUS"

        # Update config file with current status if it exists
        CONFIG_FILES=("$SCRIPT_DIR/configs"/*"$JOB_NAME"*.json)
        if [ -f "${CONFIG_FILES[0]}" ]; then
            CONFIG_FILE="${CONFIG_FILES[0]}"
            # Extract job status from hyperpod output
            CURRENT_STATUS=$(echo "$JOB_STATUS" | grep "$JOB_NAME" | awk '{print $2}')
            if [ -n "$CURRENT_STATUS" ]; then
                # Update the config file with new status
                TMP_FILE=$(mktemp)
                jq --arg status "$CURRENT_STATUS" \
                   --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
                   '.status = $status | .last_updated = $time' "$CONFIG_FILE" > "$TMP_FILE"
                mv "$TMP_FILE" "$CONFIG_FILE"
                print_success "Updated job status in config: $CONFIG_FILE"
            fi
        fi

        print_section "Pod Status: $JOB_NAME"
        hyperpod list-pods --job-name $JOB_NAME --namespace $NAMESPACE
        
        print_section "Pod Details"
        # Get pod names and describe each one
        POD_NAMES=$(hyperpod list-pods --job-name $JOB_NAME --namespace $NAMESPACE | jq -r '.pods[].PodName')
        
        for pod in $POD_NAMES; do
            print_section "Pod: $pod"
            kubectl describe pod $pod -n $NAMESPACE
        done
        
        # CloudWatch Logs section
        if [ -n "$CLUSTER_NAME" ] && [ -n "$CLUSTER_ID" ] && [ -n "$RIG_NAME" ]; then
            print_header "CloudWatch Logs"
            LOG_GROUP="/aws/sagemaker/Clusters/$CLUSTER_NAME/$CLUSTER_ID"
            LOG_STREAM_PREFIX="SagemakerHyperPodTrainingJob/$RIG_NAME"
            
            print_section "Log Configuration"
            echo "Log Group: $LOG_GROUP"
            echo "Stream prefix: $LOG_STREAM_PREFIX"
            
            # Get all log streams for the rig - try different approaches
            print_section "Log Streams"
            
            # Method 1: Try with exact prefix
            LOG_STREAMS=$(aws logs describe-log-streams \
                --log-group-name "$LOG_GROUP" \
                --log-stream-name-prefix "$LOG_STREAM_PREFIX" \
                --order-by LastEventTime \
                --descending \
                --query 'logStreams[].logStreamName' \
                --output text 2>/dev/null)
            
            # Method 2: If no streams found, try without prefix and filter
            if [ -z "$LOG_STREAMS" ] || [ "$LOG_STREAMS" = "None" ]; then
                print_warning "No streams found with prefix, trying broader search..."
                ALL_STREAMS=$(aws logs describe-log-streams \
                    --log-group-name "$LOG_GROUP" \
                    --order-by LastEventTime \
                    --descending \
                    --query 'logStreams[].logStreamName' \
                    --output text 2>/dev/null)
                
                # Filter streams that contain our rig name
                LOG_STREAMS=$(echo "$ALL_STREAMS" | tr '\t' '\n' | grep "SagemakerHyperPodTrainingJob/$RIG_NAME" | tr '\n' '\t')
            fi
            
            if [ -n "$LOG_STREAMS" ] && [ "$LOG_STREAMS" != "None" ]; then
                print_success "Found log streams:"
                echo "$LOG_STREAMS" | tr '\t' '\n' | sed 's/^/  - /'
                
                print_section "Recent Logs (Last 100 lines per stream)"
                
                # Process each log stream
                for stream in $(echo "$LOG_STREAMS" | tr '\t' '\n'); do
                    if [ -n "$stream" ]; then
                        print_section "Log Stream: $stream"
                        
                        # Try different approaches to get logs
                        LOGS_FOUND=false
                        
                        # Method 1: Get most recent events (default behavior)
                        echo "Fetching recent logs..."
                        LOGS=$(aws logs get-log-events \
                            --log-group-name "$LOG_GROUP" \
                            --log-stream-name "$stream" \
                            --limit 100 \
                            --query 'events[].message' \
                            --output text 2>/dev/null)
                        
                        if [ -n "$LOGS" ] && [ "$LOGS" != "None" ] && [ "$LOGS" != "" ]; then
                            echo "$LOGS" | head -100
                            LOGS_FOUND=true
                        fi
                        
                        # Method 2: If no logs, try from beginning
                        if [ "$LOGS_FOUND" = false ]; then
                            print_warning "No recent logs, trying from beginning of stream..."
                            LOGS=$(aws logs get-log-events \
                                --log-group-name "$LOG_GROUP" \
                                --log-stream-name "$stream" \
                                --start-from-head true \
                                --limit 100 \
                                --query 'events[].message' \
                                --output text 2>/dev/null)
                            
                            if [ -n "$LOGS" ] && [ "$LOGS" != "None" ] && [ "$LOGS" != "" ]; then
                                echo "$LOGS" | head -100
                                LOGS_FOUND=true
                            fi
                        fi
                        
                        # Method 3: If still no logs, try with time range (last 7 days)
                        if [ "$LOGS_FOUND" = false ]; then
                            print_warning "No logs found, trying extended time range (last 7 days)..."
                            START_TIME=$(($(date +%s) * 1000 - 604800000))  # 7 days ago in milliseconds
                            
                            LOGS=$(aws logs get-log-events \
                                --log-group-name "$LOG_GROUP" \
                                --log-stream-name "$stream" \
                                --start-time $START_TIME \
                                --limit 100 \
                                --query 'events[].message' \
                                --output text 2>/dev/null)
                            
                            if [ -n "$LOGS" ] && [ "$LOGS" != "None" ] && [ "$LOGS" != "" ]; then
                                echo "$LOGS" | head -100
                                LOGS_FOUND=true
                            fi
                        fi
                        
                        # If still no logs, show diagnostic info
                        if [ "$LOGS_FOUND" = false ]; then
                            print_warning "No log messages found - checking stream details..."
                            
                            # Show stream metadata
                            aws logs describe-log-streams \
                                --log-group-name "$LOG_GROUP" \
                                --log-stream-name-prefix "$stream" \
                                --query 'logStreams[0]' \
                                --output table 2>/dev/null
                            
                            print_section "Troubleshooting"
                            echo "This could be due to:"
                            echo "  • Logs haven't been written yet"
                            echo "  • AWS CLI permissions issue"
                            echo "  • Stream name mismatch"
                            echo "  • Logs are in a different time range"
                        fi
                    fi
                done
            else
                print_error "No log streams found for rig: $RIG_NAME"
                print_section "Debugging Information"
                echo "Log group: $LOG_GROUP"
                echo "Expected stream pattern: SagemakerHyperPodTrainingJob/$RIG_NAME/<instance_id>"
                echo ""
                print_section "Available Log Streams"
                echo "Showing most recent streams in log group:"
                aws logs describe-log-streams \
                    --log-group-name "$LOG_GROUP" \
                    --order-by LastEventTime \
                    --descending \
                    --max-items 10 \
                    --query 'logStreams[].logStreamName' \
                    --output text 2>/dev/null | tr '\t' '\n' | sed 's/^/  - /'
                    
                echo ""
                print_warning "If you see your streams above but they don't match the expected pattern,"
                echo "please check the rig_name parameter or stream naming convention."
            fi
        elif [ -n "$CLUSTER_NAME" ] || [ -n "$CLUSTER_ID" ] || [ -n "$RIG_NAME" ]; then
            print_section "CloudWatch Logs Configuration"
            print_warning "To view CloudWatch logs, provide all required parameters:"
            echo "  cluster-name: ${CLUSTER_NAME:-"<not set>"}"
            echo "  cluster-id: ${CLUSTER_ID:-"<not set>"}"
            echo "  rig-name: ${RIG_NAME:-"<not set>"}"
            echo ""
            echo "Example:"
            echo "$0 --job_name $JOB_NAME --namespace $NAMESPACE --action monitor --cluster-name <name> --cluster-id <id> --rig-name <name>"
        fi
        ;;
esac
