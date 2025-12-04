# Path to Production - Amazon Nova Act on AWS

## Overview

This tutorial series guides you through deploying Amazon Nova Act workflows to production on AWS. You'll learn how to transition from local development to production-scale deployment with AWS IAM authentication, monitoring, and infrastructure management.

Amazon Nova Act is a service to build and manage fleets of reliable AI agents for automating production UI workflows at scale. This path-to-production series focuses on the AWS deployment journey, covering authentication, workflow management, tool integration, and observability.

## Key Principles

### 1. AWS IAM Authentication
Production workflows use AWS IAM authentication instead of API keys, providing:
- Audit trails and fine-grained permissions
- Integration with AWS services (S3, CloudWatch, Lambda)
- Service-linked roles for automated operations
- Compliance with enterprise security policies

### 2. Workflow Definitions
Workflows are defined in AWS and referenced by name, enabling:
- Centralized workflow management in AWS Console
- Version control and deployment tracking
- Separation of workflow logic from infrastructure
- Reusable workflow definitions across environments

### 3. Production-Scale Infrastructure
Deploy workflows to AWS compute services with:
- Built-in monitoring via CloudWatch metrics
- Artifact storage in S3 for traces and logs
- Scalable execution across multiple instances
- Integration with AWS deployment pipelines

### 4. Observability & Debugging
Production workflows include comprehensive observability:
- Step-by-step execution traces
- CloudWatch metrics (invocations, latency, errors)
- S3-stored artifacts for post-execution analysis
- AWS Console for workflow run inspection

## Tutorial Sections

| Section | Description |
|---------|-------------|
| **00-setup** | Configure AWS credentials and verify IAM permissions for Nova Act service access. Establishes AWS CLI authentication and validates required permissions for workflow deployment. |
| **01-workflow-basics** | Create workflow definitions in AWS, use `@workflow` decorator and context manager patterns for local execution with AWS logging, and deploy workflows to AWS infrastructure. |

## Prerequisites

Before starting this tutorial series, ensure you have:

- **AWS Account**: Active AWS account with billing enabled
- **IAM Permissions**: User or role with Nova Act service permissions (see 00-setup)
- **AWS CLI v2**: Installed and configured ([installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **Python 3.10+**: With pip and virtual environment support
- **Nova Act SDK**: Version 3.0.5.0 or later (`pip install nova-act`)

## Getting Started

### Quick Start

1. **Complete Setup** (Section 00)
   ```bash
   cd 00-setup
   ./0_setup_environment.sh
   python 1_setup_aws_credentials.py
   python 2_verify_permissions.py
   ```

2. **Run Your First Workflow** (Section 01)
   ```bash
   cd ../01-workflow-basics
   python 1_workflow_definitions.py
   python 2_workflow_decorator.py
   ```

3. **View Results in AWS Console**
   - Navigate to [Nova Act Console](https://us-east-1.console.aws.amazon.com/nova-act/home)
   - View workflow runs, traces, and metrics

### Learning Path

Each section builds on the previous one:

1. **00-setup**: Foundation - AWS authentication and permissions
2. **01-workflow-basics**: Core concepts - workflow definitions and deployment

## Authentication Methods

### API Key vs AWS IAM

| Feature | API Key | AWS IAM |
|---------|---------|---------|
| **Setup Time** | Instant | 5-10 minutes |
| **Use Case** | Exploration, prototyping | Production deployment |
| **AWS Integration** | None | Full (S3, CloudWatch, Lambda) |
| **Monitoring** | Limited | Comprehensive |
| **Security** | Basic | Enterprise-grade |
| **Cost** | Free tier | AWS usage charges |

**Recommendation**: Use API Key for initial exploration, then switch to AWS IAM for production development.

## Production Deployment Options

### Deployment Methods

1. **IDE Extension** (Quick Start)
   - One-click deployment from VS Code, Cursor, or Kiro
   - Automatic infrastructure provisioning
   - Best for: Individual workflows, rapid iteration

2. **CDK Templates** (Production)
   - Infrastructure-as-code with AWS CDK
   - Customizable compute, networking, security
   - Best for: Enterprise deployments, CI/CD pipelines

3. **Manual Deployment** (Advanced)
   - Direct AWS service integration
   - Full control over infrastructure
   - Best for: Custom architectures, specific requirements

## Model Version Selection

Choose your model version strategy:

- **`nova-act-latest`**: Automatically tracks latest GA model (recommended for development)
- **Specific version** (e.g., `nova-act-v1.0`): Pin to stable release (recommended for production)

Production workflows should pin to specific model versions for predictable behavior and 1-year support guarantee.

## AWS Region Availability

Amazon Nova Act is currently available in:
- **US East (N. Virginia)** - `us-east-1`

All workflows, monitoring, and infrastructure must be deployed in this region.

## Cost Considerations

Nova Act pricing includes:
- **Model invocations**: Per-step charges based on model version
- **AWS infrastructure**: Compute, storage, and data transfer costs
- **CloudWatch**: Metrics and log storage

Visit the [Amazon Nova Act pricing page](https://aws.amazon.com/nova/pricing/) for current rates.

## Support & Resources

### Documentation
- [Nova Act User Guide](https://docs.aws.amazon.com/nova-act/latest/userguide/)
- [AWS Console](https://us-east-1.console.aws.amazon.com/nova-act/home)
- [More GitHub Samples](https://github.com/amazon-agi-labs/nova-act-samples)

