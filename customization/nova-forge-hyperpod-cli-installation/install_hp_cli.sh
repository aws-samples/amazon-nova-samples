#!/usr/bin/env bash
# HyperPod CLI Installer
# This script installs the HyperPod CLI with all dependencies and validation

set -uo pipefail

# Color codes for output (terminal-friendly across themes)
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default installation directory
DEFAULT_INSTALL_DIR="$HOME/hyperpod-cli-env"

# Debug mode flag
DEBUG_MODE=0

# Progress tracking
TOTAL_STEPS=12
CURRENT_STEP=0
STEP_STATUS=()
ANIMATION_PID=0

# Animated dots for running operations
animate_dots() {
    local step_name="$1"
    local dots=("." ".." "...")
    local idx=0
    
    while true; do
        local percent=$((CURRENT_STEP * 100 / TOTAL_STEPS))
        local filled=$((CURRENT_STEP * 40 / TOTAL_STEPS))
        local empty=$((40 - filled))
        
        printf "\r\033[K"
        printf "${GREEN}["
        for ((i=0; i<filled; i++)); do printf "█"; done
        for ((i=0; i<empty; i++)); do printf "░"; done
        printf "]${NC} ${percent}%% "
        printf "${YELLOW}⟳${NC} ${step_name}${dots[$idx]}"
        
        idx=$(( (idx + 1) % 3 ))
        sleep 0.3
    done
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --debug)
                DEBUG_MODE=1
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
HyperPod CLI Installer

Usage: $0 [OPTIONS]

Options:
    --debug     Show verbose output from installation commands
    --help, -h  Show this help message

EOF
}

# Print functions
print_error() {
    printf "${RED}✗ ERROR: %s${NC}\n" "$1" >&2
}

print_warning() {
    printf "${YELLOW}⚠ WARNING: %s${NC}\n" "$1"
}

print_success() {
    printf "${GREEN}✓ %s${NC}\n" "$1"
}

print_info() {
    printf "${CYAN}ℹ %s${NC}\n" "$1"
}

print_step() {
    printf "\n${MAGENTA}${BOLD}%s${NC}\n" "$1"
}

# Progress bar functions
update_progress() {
    local step_name="$1"
    local status="$2"  # "running", "success", "failed"
    
    if [[ "$status" == "running" ]]; then
        # Start animation in background
        if [[ $DEBUG_MODE -eq 0 ]]; then
            animate_dots "$step_name" &
            ANIMATION_PID=$!
        fi
    else
        # Stop animation if running
        if [[ $ANIMATION_PID -ne 0 ]]; then
            kill $ANIMATION_PID 2>/dev/null
            wait $ANIMATION_PID 2>/dev/null
            ANIMATION_PID=0
        fi
        
        # Only increment step counter on completion (success or failed)
        CURRENT_STEP=$((CURRENT_STEP + 1))
        STEP_STATUS[$CURRENT_STEP]="$status"
        
        if [[ $DEBUG_MODE -eq 0 ]]; then
            draw_progress_bar "$step_name" "$status"
        fi
    fi
}

draw_progress_bar() {
    local step_name="$1"
    local status="$2"
    
    local percent=$((CURRENT_STEP * 100 / TOTAL_STEPS))
    local filled=$((CURRENT_STEP * 40 / TOTAL_STEPS))
    local empty=$((40 - filled))
    
    # Clear line and move cursor to beginning
    printf "\r\033[K"
    
    # Draw progress bar with green color
    printf "${GREEN}["
    for ((i=0; i<filled; i++)); do printf "█"; done
    for ((i=0; i<empty; i++)); do printf "░"; done
    printf "]${NC} ${percent}%% "
    
    # Show status icon and step name
    case $status in
        success)
            printf "${GREEN}✓${NC} ${step_name}\n"
            ;;
        failed)
            printf "${RED}✗${NC} ${step_name}\n"
            ;;
    esac
}

# Execute command with optional debug output
exec_cmd() {
    local cmd="$1"
    local error_msg="$2"
    
    if [[ $DEBUG_MODE -eq 1 ]]; then
        print_info "Running: $cmd"
        if eval "$cmd"; then
            return 0
        else
            print_error "$error_msg"
            return 1
        fi
    else
        local temp_log
        temp_log=$(mktemp)
        if eval "$cmd" > "$temp_log" 2>&1; then
            rm -f "$temp_log"
            return 0
        else
            print_error "$error_msg"
            print_info "Last 20 lines of output:"
            tail -n 20 "$temp_log" | sed 's/^/  /'
            rm -f "$temp_log"
            return 1
        fi
    fi
}

# Error handler
error_exit() {
    print_error "$1"
    exit 1
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for active virtual environments
check_active_environments() {
    update_progress "Checking for active environments" "running"
    
    local env_active=0
    local env_type=""
    
    # Check for Python virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        env_active=1
        env_type="Python virtual environment"
    fi
    
    # Check for Conda environment
    if [[ -n "${CONDA_DEFAULT_ENV:-}" ]] && [[ "${CONDA_DEFAULT_ENV}" != "base" ]]; then
        env_active=1
        env_type="Conda environment (${CONDA_DEFAULT_ENV})"
    fi
    
    if [[ $env_active -eq 1 ]]; then
        update_progress "Checking for active environments" "failed"
        printf "\n"
        print_error "Active environment detected: ${env_type}"
        print_error "Please deactivate all virtual environments before running this installer."
        printf "\n"
        print_info "To deactivate:"
        print_info "  - Python venv: run 'deactivate'"
        print_info "  - Conda: run 'conda deactivate'"
        printf "\n"
        exit 1
    fi
    
    update_progress "Checking for active environments" "success"
}

# Check for git-remote-s3
check_git_remote_s3() {
    update_progress "Checking git-remote-s3" "running"
    
    if command_exists git-remote-s3; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_info "git-remote-s3 is already installed"
            git-remote-s3 --version 2>/dev/null || true
        fi
        update_progress "Checking git-remote-s3" "success"
        return 0
    else
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_info "git-remote-s3 not found globally"
            print_info "Will install in virtual environment (recommended)"
        fi
        update_progress "Checking git-remote-s3" "success"
        return 0
    fi
}

# Check AWS credentials
check_aws_credentials() {
    update_progress "Verifying AWS credentials" "running"
    
    if ! command_exists aws; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_warning "AWS CLI is not installed. Skipping credential check."
            print_info "Note: You'll need AWS credentials configured to clone from S3."
        fi
        update_progress "Verifying AWS credentials" "success"
        return 0
    fi
    
    if aws sts get-caller-identity >/dev/null 2>&1; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_success "AWS credentials are configured"
            aws sts get-caller-identity --query 'Account' --output text | xargs -I {} printf "  Account: {}\n"
        fi
        update_progress "Verifying AWS credentials" "success"
    else
        update_progress "Verifying AWS credentials" "failed"
        printf "\n"
        print_error "AWS credentials are not configured or invalid"
        print_info "You need to configure AWS credentials before cloning from S3."
        print_info "Run: aws configure"
        exit 1
    fi
}

# Check Python version
check_python_version() {
    update_progress "Checking Python version" "running"
    
    if ! command_exists python3; then
        update_progress "Checking Python version" "failed"
        printf "\n"
        print_error "python3 is not installed"
        print_info "Please install Python 3.8, 3.9, 3.10, 3.11, or 3.12"
        exit 1
    fi
    
    local python_version
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    
    # Extract major and minor version
    local major minor
    major=$(printf "%s" "$python_version" | cut -d. -f1)
    minor=$(printf "%s" "$python_version" | cut -d. -f2)
    
    if [[ $DEBUG_MODE -eq 1 ]]; then
        print_info "Found Python version: ${python_version}"
    fi
    
    # Strict version check: only allow Python 3.8-3.12
    if [[ "$major" -ne 3 ]]; then
        update_progress "Checking Python version" "failed"
        printf "\n"
        print_error "Python ${python_version} is not supported"
        print_info "Required: Python 3.8, 3.9, 3.10, 3.11, or 3.12"
        printf "\n"
        exit 1
    fi
    
    if [[ "$minor" -lt 8 ]]; then
        update_progress "Checking Python version" "failed"
        printf "\n"
        print_error "Python ${python_version} is too old"
        print_info "Minimum required: Python 3.8"
        print_info "Supported versions: 3.8, 3.9, 3.10, 3.11, 3.12"
        printf "\n"
        exit 1
    fi
    
    if [[ "$minor" -gt 12 ]]; then
        update_progress "Checking Python version" "failed"
        printf "\n"
        print_error "Python ${python_version} is not supported"
        print_info "Maximum supported: Python 3.12"
        print_info "Supported versions: 3.8, 3.9, 3.10, 3.11, 3.12"
        printf "\n"
        print_info "To install a compatible Python version:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_info "  brew install python@3.12"
            print_info "  Then use: python3.12 instead of python3"
        else
            print_info "  Use pyenv or your system package manager"
            print_info "  Example: sudo apt-get install python3.12"
        fi
        printf "\n"
        exit 1
    fi
    
    # Version is in the supported range (3.8-3.12)
    if [[ $DEBUG_MODE -eq 1 ]]; then
        print_success "Python version ${python_version} is compatible"
    fi
    update_progress "Checking Python version" "success"
}

# Check for helm
check_helm() {
    update_progress "Checking Helm" "running"
    
    if command_exists helm; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_info "Helm is installed"
            helm version --short 2>/dev/null || true
        fi
        update_progress "Checking Helm" "success"
    else
        update_progress "Checking Helm" "failed"
        printf "\n"
        print_warning "Helm is not installed"
        print_info "Helm is required to submit jobs to EKS clusters."
        printf "\n"
        print_info "Install with:"
        print_info "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
        printf "\n"
        
        read -p "Continue without Helm? (y/N): " -n 1 -r
        printf "\n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        update_progress "Checking Helm" "success"
    fi
}

# Check for build tools
check_build_tools() {
    update_progress "Checking build tools" "running"
    
    local missing_tools=()
    
    # Check for gcc or clang
    if ! command_exists gcc && ! command_exists clang; then
        missing_tools+=("gcc or clang")
    fi
    
    # Check for Python development headers
    if ! python3 -c "import sysconfig; print(sysconfig.get_path('include'))" &>/dev/null; then
        missing_tools+=("python3-dev")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        update_progress "Checking build tools" "failed"
        printf "\n"
        print_error "Missing required build tools: ${missing_tools[*]}"
        printf "\n"
        print_info "Install with:"
        
        # Detect OS and provide appropriate commands
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_info "  xcode-select --install"
        elif [[ -f /etc/debian_version ]]; then
            print_info "  sudo apt-get install build-essential python3-dev"
        elif [[ -f /etc/redhat-release ]]; then
            print_info "  sudo yum groupinstall 'Development Tools'"
            print_info "  sudo yum install python3-devel"
        else
            print_info "  Install gcc/clang and python development headers for your system"
        fi
        printf "\n"
        
        read -p "Continue anyway? (y/N): " -n 1 -r
        printf "\n"
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    update_progress "Checking build tools" "success"
}

# Get installation directory from user
get_install_directory() {
    if [[ $DEBUG_MODE -eq 0 ]]; then
        # Clear progress bar before interactive prompt
        printf "\n"
    fi
    
    print_step "Installation Directory"
    printf "\n"
    print_info "Default: ${DEFAULT_INSTALL_DIR}"
    read -p "Enter installation directory (press Enter for default): " user_dir
    
    if [[ -z "$user_dir" ]]; then
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    else
        # Expand tilde to home directory
        INSTALL_DIR="${user_dir/#\~/$HOME}"
    fi
    
    print_info "Using: ${INSTALL_DIR}"
    
    # Check if directory exists
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Directory already exists: ${INSTALL_DIR}"
        read -p "Remove it and continue? (y/N): " -n 1 -r
        printf "\n"
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR" || {
                print_error "Failed to remove existing directory"
                exit 1
            }
            print_success "Removed existing directory"
        else
            print_error "Installation aborted by user"
            exit 1
        fi
    fi
    printf "\n"
}

# Create virtual environment
create_virtual_environment() {
    update_progress "Creating virtual environment" "running"
    
    if exec_cmd "python3 -m venv '$INSTALL_DIR'" "Failed to create virtual environment"; then
        update_progress "Creating virtual environment" "success"
    else
        update_progress "Creating virtual environment" "failed"
        exit 1
    fi
    
    # Activate virtual environment
    # shellcheck disable=SC1091
    source "${INSTALL_DIR}/bin/activate" || {
        print_error "Failed to activate virtual environment"
        exit 1
    }
    
    # Upgrade pip silently
    update_progress "Upgrading pip" "running"
    if exec_cmd "pip install --upgrade pip" "Failed to upgrade pip"; then
        update_progress "Upgrading pip" "success"
    else
        # Non-fatal, continue anyway
        update_progress "Upgrading pip" "success"
    fi
}

# Install git-remote-s3 in virtual environment
install_git_remote_s3_venv() {
    update_progress "Installing git-remote-s3" "running"
    
    # Always install in venv to avoid conflicts with system Python/Homebrew
    if exec_cmd "pip install git-remote-s3" "Failed to install git-remote-s3 in virtual environment"; then
        # Verify installation
        if command_exists git-remote-s3; then
            if [[ $DEBUG_MODE -eq 1 ]]; then
                print_info "git-remote-s3 installed successfully in virtual environment"
                git-remote-s3 --version 2>/dev/null || true
            fi
        fi
        update_progress "Installing git-remote-s3" "success"
    else
        update_progress "Installing git-remote-s3" "failed"
        exit 1
    fi
}

# Clone HyperPod CLI from S3
clone_hyperpod_cli() {
    update_progress "Cloning HyperPod CLI" "running"
    
    local s3_url="s3://nova-forge-c7363-206080352451-us-east-1/v1/"
    local clone_dir="${INSTALL_DIR}/HyperPodCLI"
    
    if [[ $DEBUG_MODE -eq 1 ]]; then
        print_info "Cloning from: ${s3_url}"
        print_info "Destination: ${clone_dir}"
    fi
    
    # Check AWS credentials again before cloning
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        update_progress "Cloning HyperPod CLI" "failed"
        printf "\n"
        print_error "AWS credentials are not configured. Cannot clone HyperPod CLI."
        print_info "Run 'aws configure' first."
        exit 1
    fi
    
    # Clone the repository
    local temp_log
    temp_log=$(mktemp)
    
    if [[ $DEBUG_MODE -eq 1 ]]; then
        git clone "$s3_url" "$clone_dir" 2>&1 | tee "$temp_log"
        clone_result=${PIPESTATUS[0]}
    else
        git clone "$s3_url" "$clone_dir" > "$temp_log" 2>&1
        clone_result=$?
    fi
    
    if [[ $clone_result -ne 0 ]]; then
        update_progress "Cloning HyperPod CLI from S3" "failed"
        printf "\n"
        print_error "Failed to clone from S3"
        print_info "Last 20 lines of output:"
        tail -n 20 "$temp_log" | sed 's/^/  /'
        rm -f "$temp_log"
        exit 1
    fi
    
    rm -f "$temp_log"
    
    # Verify the clone
    if [[ ! -d "$clone_dir" ]]; then
        update_progress "Cloning HyperPod CLI from S3" "failed"
        printf "\n"
        print_error "Clone directory not found: ${clone_dir}"
        exit 1
    fi
    
    # Fix the HEAD issue - checkout the default branch
    cd "$clone_dir" || exit 1
    
    # Find available branches and checkout the first one (usually main or master)
    local default_branch
    default_branch=$(git branch -r | grep -v HEAD | head -n 1 | sed 's/.*\///' | xargs)
    
    if [[ -n "$default_branch" ]]; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_info "Checking out branch: ${default_branch}"
        fi
        git checkout "$default_branch" >/dev/null 2>&1 || {
            # Try without remote prefix
            git checkout -b main >/dev/null 2>&1 || true
        }
    fi
    
    cd - > /dev/null || true
    
    # Verify setup files exist
    if [[ ! -f "${clone_dir}/setup.py" ]] && [[ ! -f "${clone_dir}/pyproject.toml" ]]; then
        update_progress "Cloning HyperPod CLI" "failed"
        printf "\n"
        print_error "No setup.py or pyproject.toml found in cloned repository"
        print_info "The repository may be incomplete or incorrectly structured"
        exit 1
    fi
    
    update_progress "Cloning HyperPod CLI" "success"
}

# Install HyperPod CLI locally
install_hyperpod_cli() {
    update_progress "Installing HyperPod CLI" "running"
    
    local cli_dir="${INSTALL_DIR}/HyperPodCLI"
    
    if [[ ! -d "$cli_dir" ]]; then
        update_progress "Installing HyperPod CLI" "failed"
        printf "\n"
        print_error "HyperPod CLI directory not found: ${cli_dir}"
        exit 1
    fi
    
    cd "$cli_dir" || {
        update_progress "Installing HyperPod CLI" "failed"
        printf "\n"
        print_error "Failed to change to HyperPod CLI directory"
        exit 1
    }
    
    if exec_cmd "pip install -e ." "Failed to install HyperPod CLI"; then
        update_progress "Installing HyperPod CLI" "success"
    else
        update_progress "Installing HyperPod CLI" "failed"
        cd - > /dev/null || true
        exit 1
    fi
    
    # Return to original directory
    cd - > /dev/null || true
}

# Run verification script
run_verification() {
    update_progress "Verifying installation" "running"
    
    local cli_dir="${INSTALL_DIR}/HyperPodCLI"
    local verify_script="${cli_dir}/verify_env.sh"
    
    if [[ ! -f "$verify_script" ]]; then
        if [[ $DEBUG_MODE -eq 1 ]]; then
            print_warning "Verification script not found: ${verify_script}"
            print_info "Skipping verification step"
        fi
        update_progress "Verifying installation" "success"
        return 0
    fi
    
    cd "$cli_dir" || {
        update_progress "Verifying installation" "failed"
        return 1
    }
    
    if exec_cmd "bash verify_env.sh" "Environment verification failed"; then
        update_progress "Verifying installation" "success"
        cd - > /dev/null || true
        return 0
    else
        update_progress "Verifying installation" "failed"
        cd - > /dev/null || true
        return 1
    fi
}

# Print final instructions
print_final_instructions() {
    printf "\n\n"
    print_step "Installation Complete! 🎉"
    printf "\n"
    print_success "HyperPod CLI has been successfully installed!"
    printf "\n\n"
    
    print_info "To activate and use the HyperPod CLI:"
    printf "\n"
    printf "  ${BOLD}${GREEN}source ${INSTALL_DIR}/bin/activate${NC}\n"
    printf "  ${GREEN}hyperpod --help${NC}\n"
    printf "\n"
    print_info "When you're done, deactivate with:"
    printf "\n"
    printf "  ${GREEN}deactivate${NC}\n"
    printf "\n"
    print_info "Installation location: ${INSTALL_DIR}"
    print_info "HyperPod CLI source: ${INSTALL_DIR}/HyperPodCLI"
    printf "\n"
    print_info "Note: git-remote-s3 is installed in the virtual environment"
    print_info "      Activate the environment before using git clone with S3 URLs"
    printf "\n"
}

# Main installation flow
main() {
    # Parse command line arguments
    parse_args "$@"
    
    printf "\n"
    printf "${BOLD}${GREEN}"
    printf "╔══════════════════════════════════════════════════════════════════════╗\n"
    printf "║                                                                      ║\n"
    printf "║                    HYPERPOD CLI INSTALLER                            ║\n"
    printf "║                                                                      ║\n"
    printf "╚══════════════════════════════════════════════════════════════════════╝\n"
    printf "${NC}\n"
    
    if [[ $DEBUG_MODE -eq 1 ]]; then
        print_info "Debug mode enabled - showing verbose output"
        printf "\n"
    fi
    
    # Pre-flight checks
    check_active_environments
    check_python_version
    check_build_tools
    check_helm
    check_git_remote_s3
    check_aws_credentials
    
    # Get installation preferences
    get_install_directory
    
    # Perform installation
    create_virtual_environment
    install_git_remote_s3_venv
    clone_hyperpod_cli
    install_hyperpod_cli
    
    # Verify installation
    run_verification
    
    # Show final instructions
    print_final_instructions
    
    exit 0
}

# Run main function
main "$@"
