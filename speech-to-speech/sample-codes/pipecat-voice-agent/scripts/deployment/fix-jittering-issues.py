#!/usr/bin/env python3
"""
Fix Jittering Issues in Pipecat ECS Deployment

This script addresses common causes of ECS task jittering:
1. Resource allocation optimization
2. Health check configuration tuning
3. Auto-scaling policy adjustments
4. Load balancer target group settings
"""

import boto3
import json
import time
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JitteringFixer:
    """Fix jittering issues in ECS deployment."""

    def __init__(self):
        self.ecs_client = boto3.client("ecs")
        self.elbv2_client = boto3.client("elbv2")
        self.cloudwatch_client = boto3.client("cloudwatch")
        self.application_autoscaling_client = boto3.client("application-autoscaling")

        # Configuration
        self.cluster_name = "pipecat-cluster-test"
        self.service_name = "pipecat-service-test"
        self.target_group_name = "pipecat-alb-test"

    def analyze_current_issues(self) -> Dict[str, Any]:
        """Analyze current deployment issues."""
        logger.info("Analyzing current deployment issues...")

        issues = {
            "service_issues": [],
            "target_group_issues": [],
            "scaling_issues": [],
            "resource_issues": [],
        }

        try:
            # Check ECS service status
            service_response = self.ecs_client.describe_services(
                cluster=self.cluster_name, services=[self.service_name]
            )

            if service_response["services"]:
                service = service_response["services"][0]

                # Check running vs desired count
                running_count = service["runningCount"]
                desired_count = service["desiredCount"]
                pending_count = service["pendingCount"]

                if running_count != desired_count:
                    issues["service_issues"].append(
                        f"Running count ({running_count}) != Desired count ({desired_count})"
                    )

                if pending_count > 0:
                    issues["service_issues"].append(f"Pending tasks: {pending_count}")

                # Check deployment status
                deployments = service.get("deployments", [])
                for deployment in deployments:
                    if deployment["status"] != "PRIMARY":
                        issues["service_issues"].append(
                            f"Non-primary deployment: {deployment['status']}"
                        )

                logger.info(
                    f"Service status: Running={running_count}, Desired={desired_count}, Pending={pending_count}"
                )

            # Check target group health
            target_groups = self.elbv2_client.describe_target_groups(
                Names=[self.target_group_name]
            )

            if target_groups["TargetGroups"]:
                tg = target_groups["TargetGroups"][0]
                tg_arn = tg["TargetGroupArn"]

                # Get target health
                health_response = self.elbv2_client.describe_target_health(
                    TargetGroupArn=tg_arn
                )

                healthy_targets = sum(
                    1
                    for target in health_response["TargetHealthDescriptions"]
                    if target["TargetHealth"]["State"] == "healthy"
                )
                total_targets = len(health_response["TargetHealthDescriptions"])

                if healthy_targets < total_targets:
                    issues["target_group_issues"].append(
                        f"Unhealthy targets: {total_targets - healthy_targets}/{total_targets}"
                    )

                logger.info(
                    f"Target group health: {healthy_targets}/{total_targets} healthy"
                )

                # Check health check settings
                health_check_interval = tg.get("HealthCheckIntervalSeconds", 30)
                health_check_timeout = tg.get("HealthCheckTimeoutSeconds", 5)
                healthy_threshold = tg.get("HealthyThresholdCount", 2)
                unhealthy_threshold = tg.get("UnhealthyThresholdCount", 2)

                if health_check_interval < 30:
                    issues["target_group_issues"].append(
                        f"Health check interval too aggressive: {health_check_interval}s"
                    )

                if unhealthy_threshold < 3:
                    issues["target_group_issues"].append(
                        f"Unhealthy threshold too low: {unhealthy_threshold}"
                    )

        except Exception as e:
            logger.error(f"Error analyzing issues: {str(e)}")
            issues["analysis_errors"] = [str(e)]

        return issues

    def fix_target_group_health_checks(self) -> bool:
        """Optimize target group health check settings."""
        logger.info("Fixing target group health check settings...")

        try:
            # Get target group ARN
            target_groups = self.elbv2_client.describe_target_groups(
                Names=[self.target_group_name]
            )

            if not target_groups["TargetGroups"]:
                logger.error("Target group not found")
                return False

            tg_arn = target_groups["TargetGroups"][0]["TargetGroupArn"]

            # Update health check settings to be less aggressive
            self.elbv2_client.modify_target_group(
                TargetGroupArn=tg_arn,
                HealthCheckIntervalSeconds=30,  # Check every 30 seconds
                HealthCheckTimeoutSeconds=10,  # 10 second timeout
                HealthyThresholdCount=2,  # 2 consecutive successes to be healthy
                UnhealthyThresholdCount=5,  # 5 consecutive failures to be unhealthy
                HealthCheckPath="/health",  # Ensure correct health check path
                HealthCheckProtocol="HTTP",
                HealthCheckPort="traffic-port",
            )

            logger.info("✅ Target group health check settings optimized")
            return True

        except Exception as e:
            logger.error(f"Failed to fix target group health checks: {str(e)}")
            return False

    def optimize_ecs_service_configuration(self) -> bool:
        """Optimize ECS service configuration to reduce jittering."""
        logger.info("Optimizing ECS service configuration...")

        try:
            # Get current service configuration
            service_response = self.ecs_client.describe_services(
                cluster=self.cluster_name, services=[self.service_name]
            )

            if not service_response["services"]:
                logger.error("Service not found")
                return False

            service = service_response["services"][0]

            # Update service with optimized settings
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                deploymentConfiguration={
                    "maximumPercent": 200,  # Allow up to 200% during deployment
                    "minimumHealthyPercent": 50,  # Keep at least 50% healthy during deployment
                    "deploymentCircuitBreaker": {"enable": True, "rollback": True},
                },
                healthCheckGracePeriodSeconds=300,  # 5 minutes grace period for health checks
                enableExecuteCommand=True,
            )

            logger.info("✅ ECS service configuration optimized")
            return True

        except Exception as e:
            logger.error(f"Failed to optimize ECS service: {str(e)}")
            return False

    def update_task_definition_resources(self) -> bool:
        """Update task definition with optimized resource allocation."""
        logger.info("Updating task definition resources...")

        try:
            # Get current task definition
            service_response = self.ecs_client.describe_services(
                cluster=self.cluster_name, services=[self.service_name]
            )

            if not service_response["services"]:
                logger.error("Service not found")
                return False

            current_task_def_arn = service_response["services"][0]["taskDefinition"]

            # Get task definition details
            task_def_response = self.ecs_client.describe_task_definition(
                taskDefinition=current_task_def_arn
            )

            task_def = task_def_response["taskDefinition"]

            # Create new task definition with optimized resources
            new_task_def = {
                "family": task_def["family"],
                "networkMode": task_def["networkMode"],
                "requiresCompatibilities": task_def["requiresCompatibilities"],
                "cpu": "1024",  # Increase CPU to 1 vCPU
                "memory": "3072",  # Increase memory to 3GB
                "executionRoleArn": task_def["executionRoleArn"],
                "taskRoleArn": task_def.get("taskRoleArn"),
                "containerDefinitions": [],
            }

            # Update container definitions with optimized resources
            for container in task_def["containerDefinitions"]:
                updated_container = container.copy()

                # Increase container resources
                updated_container["cpu"] = 1024  # 1 vCPU
                updated_container["memory"] = 2048  # 2GB hard limit
                updated_container["memoryReservation"] = 1536  # 1.5GB soft limit

                # Optimize health check
                if "healthCheck" in updated_container:
                    updated_container["healthCheck"] = {
                        "command": [
                            "CMD-SHELL",
                            "curl -f http://localhost:7860/health || exit 1",
                        ],
                        "interval": 30,
                        "timeout": 10,
                        "retries": 5,
                        "startPeriod": 60,
                    }

                # Add resource limits for stability
                if "ulimits" not in updated_container:
                    updated_container["ulimits"] = [
                        {"name": "nofile", "softLimit": 65536, "hardLimit": 65536}
                    ]

                new_task_def["containerDefinitions"].append(updated_container)

            # Register new task definition
            new_task_response = self.ecs_client.register_task_definition(**new_task_def)
            new_task_def_arn = new_task_response["taskDefinition"]["taskDefinitionArn"]

            # Update service to use new task definition
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                taskDefinition=new_task_def_arn,
            )

            logger.info(f"✅ Task definition updated: {new_task_def_arn}")
            return True

        except Exception as e:
            logger.error(f"Failed to update task definition: {str(e)}")
            return False

    def configure_auto_scaling(self) -> bool:
        """Configure auto-scaling policies to reduce jittering."""
        logger.info("Configuring auto-scaling policies...")

        try:
            resource_id = f"service/{self.cluster_name}/{self.service_name}"

            # Register scalable target
            try:
                self.application_autoscaling_client.register_scalable_target(
                    ServiceNamespace="ecs",
                    ResourceId=resource_id,
                    ScalableDimension="ecs:service:DesiredCount",
                    MinCapacity=2,  # Minimum 2 tasks
                    MaxCapacity=10,  # Maximum 10 tasks
                    RoleArn=f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService",
                )
                logger.info("✅ Scalable target registered")
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Failed to register scalable target: {str(e)}")

            # Create CPU-based scaling policy with less aggressive settings
            try:
                cpu_policy_response = self.application_autoscaling_client.put_scaling_policy(
                    PolicyName=f"{self.service_name}-cpu-scaling",
                    ServiceNamespace="ecs",
                    ResourceId=resource_id,
                    ScalableDimension="ecs:service:DesiredCount",
                    PolicyType="TargetTrackingScaling",
                    TargetTrackingScalingPolicyConfiguration={
                        "TargetValue": 70.0,  # Target 70% CPU utilization
                        "PredefinedMetricSpecification": {
                            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
                        },
                        "ScaleOutCooldown": 300,  # 5 minutes cooldown for scale out
                        "ScaleInCooldown": 600,  # 10 minutes cooldown for scale in
                        "DisableScaleIn": False,
                    },
                )
                logger.info("✅ CPU scaling policy configured")
            except Exception as e:
                logger.warning(f"Failed to create CPU scaling policy: {str(e)}")

            # Create memory-based scaling policy
            try:
                memory_policy_response = self.application_autoscaling_client.put_scaling_policy(
                    PolicyName=f"{self.service_name}-memory-scaling",
                    ServiceNamespace="ecs",
                    ResourceId=resource_id,
                    ScalableDimension="ecs:service:DesiredCount",
                    PolicyType="TargetTrackingScaling",
                    TargetTrackingScalingPolicyConfiguration={
                        "TargetValue": 80.0,  # Target 80% memory utilization
                        "PredefinedMetricSpecification": {
                            "PredefinedMetricType": "ECSServiceAverageMemoryUtilization"
                        },
                        "ScaleOutCooldown": 300,  # 5 minutes cooldown for scale out
                        "ScaleInCooldown": 600,  # 10 minutes cooldown for scale in
                        "DisableScaleIn": False,
                    },
                )
                logger.info("✅ Memory scaling policy configured")
            except Exception as e:
                logger.warning(f"Failed to create memory scaling policy: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Failed to configure auto-scaling: {str(e)}")
            return False

    def create_enhanced_cloudwatch_alarms(self) -> bool:
        """Create enhanced CloudWatch alarms for better monitoring."""
        logger.info("Creating enhanced CloudWatch alarms...")

        try:
            # Task count stability alarm
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=f"{self.service_name}-task-count-stability",
                ComparisonOperator="LessThanThreshold",
                EvaluationPeriods=2,
                MetricName="RunningTaskCount",
                Namespace="AWS/ECS",
                Period=60,
                Statistic="Average",
                Threshold=2.0,
                ActionsEnabled=True,
                AlarmDescription="Alert when running task count drops below 2",
                Dimensions=[
                    {"Name": "ServiceName", "Value": self.service_name},
                    {"Name": "ClusterName", "Value": self.cluster_name},
                ],
                Unit="Count",
                TreatMissingData="breaching",
            )

            # CPU utilization alarm with higher threshold
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=f"{self.service_name}-high-cpu-utilization",
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=3,
                MetricName="CPUUtilization",
                Namespace="AWS/ECS",
                Period=300,
                Statistic="Average",
                Threshold=85.0,
                ActionsEnabled=True,
                AlarmDescription="Alert when CPU utilization exceeds 85% for 15 minutes",
                Dimensions=[
                    {"Name": "ServiceName", "Value": self.service_name},
                    {"Name": "ClusterName", "Value": self.cluster_name},
                ],
                Unit="Percent",
                TreatMissingData="notBreaching",
            )

            # Memory utilization alarm
            self.cloudwatch_client.put_metric_alarm(
                AlarmName=f"{self.service_name}-high-memory-utilization",
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=3,
                MetricName="MemoryUtilization",
                Namespace="AWS/ECS",
                Period=300,
                Statistic="Average",
                Threshold=90.0,
                ActionsEnabled=True,
                AlarmDescription="Alert when memory utilization exceeds 90% for 15 minutes",
                Dimensions=[
                    {"Name": "ServiceName", "Value": self.service_name},
                    {"Name": "ClusterName", "Value": self.cluster_name},
                ],
                Unit="Percent",
                TreatMissingData="notBreaching",
            )

            logger.info("✅ Enhanced CloudWatch alarms created")
            return True

        except Exception as e:
            logger.error(f"Failed to create CloudWatch alarms: {str(e)}")
            return False

    def wait_for_service_stability(self, timeout_minutes: int = 10) -> bool:
        """Wait for service to stabilize after changes."""
        logger.info(
            f"Waiting for service stability (timeout: {timeout_minutes} minutes)..."
        )

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            try:
                service_response = self.ecs_client.describe_services(
                    cluster=self.cluster_name, services=[self.service_name]
                )

                if service_response["services"]:
                    service = service_response["services"][0]
                    running_count = service["runningCount"]
                    desired_count = service["desiredCount"]
                    pending_count = service["pendingCount"]

                    # Check if service is stable
                    deployments = service.get("deployments", [])
                    primary_deployment = next(
                        (d for d in deployments if d["status"] == "PRIMARY"), None
                    )

                    if (
                        running_count == desired_count
                        and pending_count == 0
                        and primary_deployment
                        and primary_deployment.get("rolloutState") == "COMPLETED"
                    ):

                        logger.info(
                            f"✅ Service stabilized: {running_count}/{desired_count} tasks running"
                        )
                        return True

                    logger.info(
                        f"Service status: Running={running_count}, Desired={desired_count}, Pending={pending_count}"
                    )

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.warning(f"Error checking service stability: {str(e)}")
                time.sleep(30)

        logger.warning("Service did not stabilize within timeout period")
        return False

    def run_jittering_fixes(self) -> Dict[str, Any]:
        """Run all jittering fixes."""
        logger.info("=" * 60)
        logger.info("FIXING JITTERING ISSUES")
        logger.info("=" * 60)

        start_time = time.time()
        results = {}

        # Step 1: Analyze current issues
        logger.info("\n1. Analyzing current issues...")
        issues = self.analyze_current_issues()
        results["analysis"] = issues

        # Step 2: Fix target group health checks
        logger.info("\n2. Fixing target group health checks...")
        tg_fixed = self.fix_target_group_health_checks()
        results["target_group_fixed"] = tg_fixed

        # Step 3: Optimize ECS service configuration
        logger.info("\n3. Optimizing ECS service configuration...")
        service_optimized = self.optimize_ecs_service_configuration()
        results["service_optimized"] = service_optimized

        # Step 4: Update task definition resources
        logger.info("\n4. Updating task definition resources...")
        task_def_updated = self.update_task_definition_resources()
        results["task_definition_updated"] = task_def_updated

        # Step 5: Configure auto-scaling
        logger.info("\n5. Configuring auto-scaling...")
        autoscaling_configured = self.configure_auto_scaling()
        results["autoscaling_configured"] = autoscaling_configured

        # Step 6: Create enhanced CloudWatch alarms
        logger.info("\n6. Creating enhanced CloudWatch alarms...")
        alarms_created = self.create_enhanced_cloudwatch_alarms()
        results["alarms_created"] = alarms_created

        # Step 7: Wait for service stability
        logger.info("\n7. Waiting for service stability...")
        service_stable = self.wait_for_service_stability()
        results["service_stable"] = service_stable

        # Calculate results
        total_time = time.time() - start_time
        fixes_applied = sum(
            1 for key, value in results.items() if key != "analysis" and value is True
        )
        total_fixes = len(results) - 1  # Exclude analysis

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("JITTERING FIXES SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Fixes Applied: {fixes_applied}/{total_fixes}")
        logger.info(f"Success Rate: {(fixes_applied/total_fixes)*100:.1f}%")
        logger.info(f"Total Time: {total_time:.2f} seconds")

        # Detailed results
        logger.info("\nDETAILED RESULTS:")
        fix_names = {
            "target_group_fixed": "Target Group Health Checks",
            "service_optimized": "ECS Service Configuration",
            "task_definition_updated": "Task Definition Resources",
            "autoscaling_configured": "Auto-scaling Policies",
            "alarms_created": "CloudWatch Alarms",
            "service_stable": "Service Stability",
        }

        for key, name in fix_names.items():
            status_icon = "✅" if results.get(key) else "❌"
            logger.info(
                f"{status_icon} {name}: {'APPLIED' if results.get(key) else 'FAILED'}"
            )

        # Recommendations
        logger.info("\nRECOMMENDATIONS:")
        if not service_stable:
            logger.info(
                "- Monitor service for the next 15-20 minutes to ensure stability"
            )
        if fixes_applied < total_fixes:
            logger.info("- Review failed fixes and apply manually if needed")
        logger.info("- Monitor CloudWatch metrics for improved stability")
        logger.info("- Consider increasing task count if load is consistently high")

        overall_success = fixes_applied >= (total_fixes * 0.8)  # 80% success rate

        logger.info("\n" + "=" * 60)
        if overall_success:
            logger.info("🎉 JITTERING FIXES: MOSTLY SUCCESSFUL")
        else:
            logger.info("⚠️  JITTERING FIXES: PARTIAL SUCCESS")
        logger.info("=" * 60)

        return {
            "overall_success": overall_success,
            "fixes_applied": fixes_applied,
            "total_fixes": total_fixes,
            "success_rate": (fixes_applied / total_fixes) * 100,
            "total_time": total_time,
            "detailed_results": results,
            "issues_found": issues,
        }


def main():
    """Main function to run jittering fixes."""
    fixer = JitteringFixer()
    results = fixer.run_jittering_fixes()

    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    main()
