# Troubleshooting Guide

Common issues and solutions for the Pipecat Voice AI Agent deployment.

## General Issues

### Container Fails to Start

**Symptoms:**
- ECS tasks stop immediately
- Health checks fail
- Container exits with error code

**Solutions:**
1. Check environment variables in AWS Secrets Manager
2. Verify IAM permissions for ECS task role
3. Check CloudWatch logs for detailed error messages
4. Ensure Docker image was built and pushed correctly

```bash
# Check ECS service events
aws ecs describe-services --cluster pipecat-cluster-test --services pipecat-service-test

# Check CloudWatch logs
aws logs tail /ecs/pipecat-voice-agent-test/application --follow
```

### Health Checks Failing

**Symptoms:**
- Load balancer shows unhealthy targets
- Service restarts frequently

**Solutions:**
1. Verify `/health` endpoint is responding
2. Check if Daily API key is valid
3. Ensure AWS credentials have proper permissions
4. Verify network connectivity

```bash
# Test health endpoint directly
curl http://your-alb-dns-name/health

# Check target group health
aws elbv2 describe-target-health --target-group-arn your-target-group-arn
```

## Phone Service Issues

### Twilio Webhook Errors

**Symptoms:**
- Phone calls don't connect to AI
- Twilio shows webhook errors
- SSL certificate errors

**Solutions:**
1. **SSL Certificate Issues:**
   - Ensure load balancer has valid SSL certificate
   - Use AWS Certificate Manager for automatic SSL
   - Avoid self-signed certificates
   - Use standard HTTPS port (443)

2. **Webhook Configuration:**
   ```bash
   # Test webhook endpoint
   curl -X POST https://your-domain.com/incoming-call \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "CallSid=test&From=+1234567890&To=+0987654321"
   ```

3. **Network Connectivity:**
   - Ensure security groups allow inbound HTTPS (443)
   - Verify load balancer is internet-facing
   - Check DNS resolution

### Nova Sonic Integration Issues

**Symptoms:**
- Voice synthesis not working
- Speech recognition errors
- AWS Bedrock access denied

**Solutions:**
1. **AWS Permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

2. **Region Availability:**
   - Ensure Nova Sonic is available in your AWS region
   - Check AWS Bedrock service status

3. **Credentials:**
   - Verify AWS credentials in Secrets Manager
   - Test Bedrock access manually

## EKS-Specific Issues

### Pods Stuck in Pending

**Symptoms:**
- Pods don't start
- `kubectl get pods` shows Pending status

**Solutions:**
1. Check Fargate profile selectors
2. Verify namespace matches Fargate profile
3. Check resource requests vs. Fargate capacity

```bash
# Check pod events
kubectl describe pods -n pipecat

# Check Fargate profiles
aws eks describe-fargate-profile --cluster-name pipecat-eks-cluster-test --fargate-profile-name default
```

### LoadBalancer Not Getting External IP

**Symptoms:**
- Service shows `<pending>` for EXTERNAL-IP
- Can't access application from internet

**Solutions:**
1. Install AWS Load Balancer Controller
2. Check service annotations
3. Verify IAM permissions for load balancer controller

```bash
# Check service status
kubectl get services -n pipecat

# Check load balancer controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

### IRSA Permission Issues

**Symptoms:**
- Pods can't access AWS services
- Access denied errors in logs

**Solutions:**
1. Verify service account annotations
2. Check IAM role trust policy
3. Ensure OIDC provider is configured

```bash
# Check service account
kubectl describe serviceaccount pipecat-service-account -n pipecat

# Test AWS access from pod
kubectl exec -it deployment/pipecat-phone-service -n pipecat -- aws sts get-caller-identity
```

## WebRTC Issues

### Daily.co Connection Problems

**Symptoms:**
- Can't join voice rooms
- WebRTC connection fails
- Browser shows connection errors

**Solutions:**
1. **API Key Issues:**
   - Verify Daily API key is valid
   - Check API key permissions
   - Ensure key is properly stored in Secrets Manager

2. **Network Issues:**
   - Check firewall settings
   - Verify WebRTC ports are open
   - Test from different networks

3. **Browser Issues:**
   - Enable microphone permissions
   - Use HTTPS (required for WebRTC)
   - Try different browsers

## Monitoring and Debugging

### Enable Debug Logging

Add to environment variables:
```bash
LOG_LEVEL=DEBUG
```

### CloudWatch Queries

Useful CloudWatch Insights queries:

```sql
# Find errors in logs
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

# Monitor health check failures
fields @timestamp, @message
| filter @message like /health/
| sort @timestamp desc
| limit 50
```

### Performance Monitoring

```bash
# Check ECS service metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=pipecat-service-test \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

## Getting Help

1. **Check CloudWatch Logs:** Always start with application logs
2. **Review AWS Service Health:** Check AWS status page
3. **Test Components Individually:** Isolate the problem
4. **Use AWS Support:** For infrastructure issues
5. **Check Pipecat Documentation:** For framework-specific issues

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Daily API key not found` | Missing or invalid API key | Check Secrets Manager |
| `SSL certificate verify failed` | Invalid SSL certificate | Use trusted CA certificate |
| `Access denied` | IAM permissions | Review and update IAM policies |
| `Connection timeout` | Network/firewall issue | Check security groups |
| `Pod has unbound immediate PersistentVolumeClaims` | Storage issue | Check PVC configuration |