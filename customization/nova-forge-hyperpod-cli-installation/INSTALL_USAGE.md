# HyperPod CLI Installer — Usage Notes

## Prerequisites

### 1. Authenticate with your AWS account (default profile)

Before running the installer, you must have valid AWS credentials configured in your **default** profile. The installer clones the HyperPod CLI source from an S3 bucket and will fail without active credentials.

To configure or verify your credentials:

```bash
# Configure credentials (if not already set up)
aws configure

# Verify your credentials are working
aws sts get-caller-identity
```

You should see output with your Account ID, UserId, and ARN. If you get an error, re-run `aws configure` or refresh your session credentials before proceeding.

### 2. Deactivate all virtual environments

The installer creates its own isolated Python virtual environment. Running it from within an existing virtual environment (Python `venv`, `conda`, `virtualenv`, `pyenv-virtualenv`, `poetry shell`, etc.) can cause conflicts and unexpected behavior.

Before running the installer, make sure no virtual environment is active:

```bash
# If you're in a Python venv or virtualenv:
deactivate

# If you're in a Conda environment:
conda deactivate

# If you're in a Poetry shell:
exit
```

You can confirm no environment is active by checking that your shell prompt has no environment prefix (e.g., `(myenv)`) and running:

```bash
echo $VIRTUAL_ENV        # Should be empty
echo $CONDA_DEFAULT_ENV  # Should be empty or "base"
```

### 3. Python version

You need Python **3.8, 3.9, 3.10, or 3.11** installed. Python 3.12+ is not supported.

```bash
python3 --version
```

If you need to install a compatible version on macOS:

```bash
brew install python@3.11
```

### 4. Build tools

A C compiler (`gcc` or `clang`) and Python development headers are required. On macOS:

```bash
xcode-select --install
```

On Debian/Ubuntu:

```bash
sudo apt-get install build-essential python3-dev
```

### 5. Helm (for EKS clusters)

Helm is required to submit training jobs to EKS clusters. Check if it's installed:

```bash
helm version
```

If not installed:

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Running the Installer

```bash
bash install_hp_cli.sh
```

The installer will prompt you for an installation directory. Press Enter to accept the default (`~/hyperpod-cli-env`), or type a custom path.

### Debug mode

For verbose output during installation:

```bash
bash install_hp_cli.sh --debug
```

## What the Installer Does

1. Checks for active virtual environments (exits if one is found)
2. Validates your Python version and build tools
3. Verifies AWS credentials
4. Creates a new Python virtual environment at your chosen directory
5. Installs `git-remote-s3` (needed to clone from S3)
6. Clones the HyperPod CLI source from S3
7. Installs the HyperPod CLI in editable mode (`pip install -e .`)
8. Runs the bundled verification script (if available)

## Using the HyperPod CLI After Installation

Each time you want to use the CLI, activate the virtual environment first:

```bash
source ~/hyperpod-cli-env/bin/activate
hyperpod --help
```

When you're done:

```bash
deactivate
```

## Installed Directory Layout

After installation, the HyperPod CLI source repository (including default recipes and configuration files) is located inside the installation directory:

```
~/hyperpod-cli-env/          # Virtual environment root (or your custom path)
├── bin/                     # Python venv binaries (activate, hyperpod, etc.)
├── lib/                     # Python packages
└── HyperPodCLI/             # Full cloned repository
    ├── recipes/             # Default recipes
    ├── setup.py
    ├── verify_env.sh
    └── ...
```

To browse the default recipes or other repo contents:

```bash
ls ~/hyperpod-cli-env/HyperPodCLI/
```

If you chose a custom installation directory, substitute `~/hyperpod-cli-env` with your chosen path.

## Troubleshooting

| Issue | Fix |
|---|---|
| `AWS credentials are not configured or invalid` | Run `aws configure` or refresh your session, then retry |
| `Active environment detected` | Run `deactivate` or `conda deactivate` and retry |
| `Python X.Y is not supported` | Install Python 3.8–3.11 and ensure `python3` points to it |
| `Failed to clone from S3` | Verify your AWS credentials have access to the S3 bucket and that `git-remote-s3` is working |
| Installation directory already exists | The installer will ask to remove it — say yes to start fresh, or choose a different path |
| `helm: command not found` when submitting a job | Install Helm: `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` |
