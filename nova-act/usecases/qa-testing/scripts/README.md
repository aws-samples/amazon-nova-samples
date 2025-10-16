# CloudFormation Scripts

This directory contains utility scripts for managing your CloudFormation stack and CloudFront distribution.

## Scripts

### 1. `invalidate-cloudfront.sh` ✅
**Purpose**: Invalidate CloudFront cache to ensure updated content is visible immediately.

**Usage**:
```bash
./invalidate-cloudfront.sh
```

**What it does**:
- Automatically finds your CloudFormation stack
- Extracts the CloudFront Distribution ID from stack outputs
- Verifies the distribution exists
- Creates a cache invalidation for all files (`/*`)
- Provides tracking information and console links

**Example Output**:
```
Found CloudFront Distribution ID: E39035B19DGDMB
✅ Invalidation created successfully!

Invalidation Details:
- ID: I2B2IA2I0ZYHZP9B5OF6UFYKC
- Status: InProgress
- Distribution: E39035B19DGDMB
- Paths: /*
```

### 2. `update-stack.sh`
**Purpose**: Update your CloudFormation stack with security enhancements.

**Usage**:
```bash
./update-stack.sh
```

**What it does**:
- Creates a change set to preview modifications
- Shows exactly what will be changed before execution
- Applies security fixes (S3 encryption, secure transport, etc.)
- Includes Checkov skip annotations for intentionally excluded items

### 3. `fix-deployment.sh`
**Purpose**: Complete stack recreation (delete and recreate).

**Usage**:
```bash
./fix-deployment.sh
```

**Note**: This script deletes and recreates the entire stack. Use `update-stack.sh` for safer updates.

## Quick Reference

### Just Invalidate CloudFront Cache
```bash
cd qa-testing-acbt-nova-act/scripts
./invalidate-cloudfront.sh
```

### Update Stack with Security Fixes
```bash
cd qa-testing-acbt-nova-act/scripts
./update-stack.sh
```

### Check Invalidation Status
```bash
aws cloudfront get-invalidation --distribution-id YOUR_DISTRIBUTION_ID --id YOUR_INVALIDATION_ID
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- `jq` installed for JSON parsing
- CloudFormation stack must exist and be in a stable state

## Troubleshooting

### "No CloudFront distribution found"
- Check if `CreateCloudFront` parameter is set to `true` in your stack
- Verify the stack has completed deployment successfully

### "Distribution does not exist"
- The distribution ID may be incorrect
- Check your AWS region and credentials
- Verify you have CloudFront permissions

### "Unknown options: false" (update-stack.sh)
- This was a parameter parsing issue that has been fixed
- Ensure you're using the latest version of the script

## Cost Considerations

- CloudFront invalidations: First 1,000 paths per month are free, then $0.005 per path
- Stack updates: No additional charges for CloudFormation operations
- Resource modifications: May incur charges based on the resources being updated
