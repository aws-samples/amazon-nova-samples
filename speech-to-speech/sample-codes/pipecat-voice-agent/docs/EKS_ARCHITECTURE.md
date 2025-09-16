# EKS Architecture Overview

## Network Flow
```
Internet → NLB (TLS Listener) → Target Group → Kubernetes Pod (Fargate)
```

## Key Components

### EKS Cluster Configuration
- **Region:** us-east-1
- **Kubernetes Version:** v1.31
- **Node Type:** t3.medium (Fargate serverless)
- **OS:** Amazon Linux 2023.7.20250512
- **Container Runtime:** containerd://1.7.27
- **Architecture:** amd64

### Networking
- **VPC:** Custom VPC with public/private subnets
- **Subnets:** Multi-AZ deployment (2 AZs)
- **Security Groups:** Restrictive ingress/egress rules
- **Load Balancer:** Network Load Balancer (Layer 4)

### Security
- **IRSA:** IAM Roles for Service Accounts
- **Secrets:** AWS Secrets Manager integration
- **TLS:** Certificate Manager for HTTPS
- **Non-root:** Container runs as user 1001

### Data Flow

#### Phone Call Flow:
```
📞 Phone Call → Twilio → Webhook → NLB → EKS Pod → Nova Sonic
```

#### WebRTC Flow:
```
🌐 Browser → NLB → EKS Pod → Daily.co Room
```

## Key Features
- ✅ Dual Voice Channels: Phone calls (Twilio) + Web chat (Daily.co)
- ✅ Serverless: Fargate eliminates node management
- ✅ Scalable: Kubernetes horizontal pod autoscaling
- ✅ Secure: IRSA, Secrets Manager, TLS termination
- ✅ Resilient: Multi-AZ deployment with health checks