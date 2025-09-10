import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as logs from "aws-cdk-lib/aws-logs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as sns from "aws-cdk-lib/aws-sns";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import { Construct } from "constructs";

export interface PipecatEcsStackProps extends cdk.StackProps {
  environment?: string;
  useDefaultVpc?: boolean;
  domainName?: string;  // Optional domain name for HTTPS
  certificateArn?: string;  // Optional certificate ARN
}

export class InfrastructureStack extends cdk.Stack {
  public readonly vpc: ec2.IVpc;
  public readonly cluster: ecs.Cluster;
  public readonly repository: ecr.IRepository;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;
  public readonly taskRole: iam.Role;
  public readonly executionRole: iam.Role;

  constructor(scope: Construct, id: string, props?: PipecatEcsStackProps) {
    super(scope, id, props);

    const environment = props?.environment || "test";
    const useDefaultVpc = props?.useDefaultVpc ?? true;

    // VPC Configuration
    if (useDefaultVpc) {
      this.vpc = ec2.Vpc.fromLookup(this, "DefaultVpc", {
        isDefault: true,
      });
    } else {
      this.vpc = new ec2.Vpc(this, "PipecatVpc", {
        maxAzs: 2,
        natGateways: 1,
        subnetConfiguration: [
          {
            cidrMask: 24,
            name: "Public",
            subnetType: ec2.SubnetType.PUBLIC,
          },
          {
            cidrMask: 24,
            name: "Private",
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
        ],
      });
    }

    // ECR Repository for container images
    // Use existing ECR repository
    this.repository = ecr.Repository.fromRepositoryName(
      this,
      "PipecatRepository",
      `pipecat-voice-agent-${environment}`
    );

    // ECS Cluster
    this.cluster = new ecs.Cluster(this, "PipecatCluster", {
      clusterName: `pipecat-cluster-${environment}`,
      vpc: this.vpc,
      enableFargateCapacityProviders: true,
    });

    // CloudWatch Log Groups for different log types
    const applicationLogGroup = new logs.LogGroup(
      this,
      "PipecatApplicationLogGroup",
      {
        logGroupName: `/ecs/pipecat-voice-agent-${environment}/application`,
        retention: logs.RetentionDays.TWO_WEEKS, // Longer retention for application logs
        removalPolicy: cdk.RemovalPolicy.DESTROY,
      }
    );

    const accessLogGroup = new logs.LogGroup(this, "PipecatAccessLogGroup", {
      logGroupName: `/ecs/pipecat-voice-agent-${environment}/access`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const errorLogGroup = new logs.LogGroup(this, "PipecatErrorLogGroup", {
      logGroupName: `/ecs/pipecat-voice-agent-${environment}/error`,
      retention: logs.RetentionDays.ONE_MONTH, // Longer retention for error logs
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Main log group for backward compatibility
    const logGroup = applicationLogGroup;

    // Secrets for Daily API Key, AWS Credentials, and Twilio
    const dailyApiKeySecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "DailyApiKeySecret",
      "pipecat/daily-api-key"
    );

    const awsCredentialsSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "AwsCredentialsSecret",
      "pipecat/aws-credentials"
    );

    const twilioCredentialsSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "TwilioCredentialsSecret",
      "pipecat/twilio-credentials"
    );

    // IAM Roles - FIXED: Added Nova Sonic bidirectional streaming permission
    this.taskRole = new iam.Role(this, "PipecatTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "Role for Pipecat ECS tasks",
      inlinePolicies: {
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:InvokeModelWithBidirectionalStream", // ADDED: Nova Sonic support
                "bedrock:ListFoundationModels", // ADDED: For Nova Sonic testing
              ],
              resources: [
                `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-sonic-v1:0`,
                `arn:aws:bedrock:${this.region}::foundation-model/*`, // ADDED: For broader access
              ],
            }),
          ],
        }),
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["secretsmanager:GetSecretValue"],
              resources: [
                `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pipecat/*`,
                dailyApiKeySecret.secretArn,
                awsCredentialsSecret.secretArn,
                twilioCredentialsSecret.secretArn,
              ],
            }),
          ],
        }),
      },
    });

    this.executionRole = new iam.Role(this, "PipecatExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "Execution role for Pipecat ECS tasks",
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
      inlinePolicies: {
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["secretsmanager:GetSecretValue"],
              resources: [
                `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pipecat/*`,
                dailyApiKeySecret.secretArn,
                awsCredentialsSecret.secretArn,
                twilioCredentialsSecret.secretArn,
              ],
            }),
          ],
        }),
      },
    });

    // Security Groups
    const albSecurityGroup = new ec2.SecurityGroup(this, "AlbSecurityGroup", {
      vpc: this.vpc,
      description: "Security group for Pipecat ALB",
      allowAllOutbound: true,
    });

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      "Allow HTTP traffic from anywhere"
    );

    albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      "Allow HTTPS traffic from anywhere"
    );

    const ecsSecurityGroup = new ec2.SecurityGroup(this, "EcsSecurityGroup", {
      vpc: this.vpc,
      description: "Security group for Pipecat ECS tasks",
      allowAllOutbound: true,
    });

    ecsSecurityGroup.addIngressRule(
      albSecurityGroup,
      ec2.Port.tcp(7860),
      "Allow traffic from ALB to ECS tasks"
    );

    // Application Load Balancer
    this.loadBalancer = new elbv2.ApplicationLoadBalancer(
      this,
      "PipecatLoadBalancer",
      {
        vpc: this.vpc,
        internetFacing: true,
        securityGroup: albSecurityGroup,
        loadBalancerName: `pipecat-alb-${environment}`,
      }
    );

    // Target Group (will be used by ECS service)
    const targetGroup = new elbv2.ApplicationTargetGroup(
      this,
      "PipecatTargetGroup",
      {
        vpc: this.vpc,
        port: 7860,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          enabled: true,
          path: "/health",
          protocol: elbv2.Protocol.HTTP,
          port: "7860",
          healthyHttpCodes: "200",
          interval: cdk.Duration.seconds(30),
          timeout: cdk.Duration.seconds(10), // Increased timeout
          healthyThresholdCount: 2,
          unhealthyThresholdCount: 5, // More tolerant of failures
        },
        // WebSocket support configuration
        protocolVersion: elbv2.ApplicationProtocolVersion.HTTP1,
        stickinessCookieDuration: cdk.Duration.seconds(86400), // 24 hours for WebSocket sessions
      }
    );

    // Configure target group attributes for WebSocket support
    const cfnTargetGroup = targetGroup.node
      .defaultChild as elbv2.CfnTargetGroup;
    cfnTargetGroup.addPropertyOverride("TargetGroupAttributes", [
      {
        Key: "stickiness.enabled",
        Value: "true",
      },
      {
        Key: "stickiness.type",
        Value: "lb_cookie",
      },
      {
        Key: "stickiness.lb_cookie.duration_seconds",
        Value: "86400",
      },
      {
        Key: "load_balancing.algorithm.type",
        Value: "least_outstanding_requests",
      },
    ]);

    // ALB Listeners - HTTP and HTTPS
    this.loadBalancer.addListener("PipecatHttpListener", {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [targetGroup],
    });

    // Add HTTPS listener if certificate is provided
    if (props?.certificateArn) {
      const certificate = acm.Certificate.fromCertificateArn(
        this,
        "PipecatCertificate", 
        props.certificateArn
      );

      this.loadBalancer.addListener("PipecatHttpsListener", {
        port: 443,
        protocol: elbv2.ApplicationProtocol.HTTPS,
        certificates: [certificate],
        defaultTargetGroups: [targetGroup],
      });
    }

    // ECS Task Definition with optimized resources for stability
    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      "PipecatTaskDefinition",
      {
        family: `pipecat-voice-agent-${environment}`,
        cpu: 2048, // 2 vCPU - increased for better performance
        memoryLimitMiB: 4096, // 4 GB - increased to prevent OOM kills
        taskRole: this.taskRole,
        executionRole: this.executionRole,
      }
    );

    // Container Definition
    const container = taskDefinition.addContainer("PipecatContainer", {
      image: ecs.ContainerImage.fromEcrRepository(this.repository, "latest"),
      containerName: "pipecat-container",
      logging: ecs.LogDrivers.awsLogs({
        logGroup: applicationLogGroup,
        streamPrefix: "ecs",
        datetimeFormat: "%Y-%m-%d %H:%M:%S",
        multilinePattern: "^\\d{4}-\\d{2}-\\d{2}",
      }),
      environment: {
        AWS_REGION: this.region,
        HOST: "0.0.0.0",
        FAST_API_PORT: "7860",
        ENVIRONMENT: environment,
        LOG_LEVEL: "INFO",
        GRACEFUL_SHUTDOWN_TIMEOUT: "30",
        BOT_CLEANUP_INTERVAL: "300",
        MEMORY_CLEANUP_THRESHOLD: "0.8",
        HEALTH_CHECK_INTERVAL: "30",
        HEALTH_CHECK_RETRIES: "5",
        ENABLE_REQUEST_POOLING: "true",
        MAX_REQUEST_POOL_SIZE: "100",
        REQUEST_TIMEOUT: "30",
        // External domain for WebSocket URLs - use ALB DNS if no custom domain
        EXTERNAL_DOMAIN: props?.domainName || this.loadBalancer.loadBalancerDnsName,
        FORCE_HTTPS: props?.certificateArn ? "true" : "false",
      },
      secrets: {
        // Daily.co API credentials
        DAILY_API_KEY: ecs.Secret.fromSecretsManager(
          dailyApiKeySecret,
          "DAILY_API_KEY"
        ),
        DAILY_API_URL: ecs.Secret.fromSecretsManager(
          dailyApiKeySecret,
          "DAILY_API_URL"
        ),

        // AWS credentials for Bedrock access (alternative to IAM roles)
        AWS_ACCESS_KEY_ID: ecs.Secret.fromSecretsManager(
          awsCredentialsSecret,
          "AWS_ACCESS_KEY_ID"
        ),
        AWS_SECRET_ACCESS_KEY: ecs.Secret.fromSecretsManager(
          awsCredentialsSecret,
          "AWS_SECRET_ACCESS_KEY"
        ),

        // Twilio API credentials
        TWILIO_ACCOUNT_SID: ecs.Secret.fromSecretsManager(
          twilioCredentialsSecret,
          "TWILIO_ACCOUNT_SID"
        ),
        TWILIO_AUTH_TOKEN: ecs.Secret.fromSecretsManager(
          twilioCredentialsSecret,
          "TWILIO_AUTH_TOKEN"
        ),
        TWILIO_PHONE_NUMBER: ecs.Secret.fromSecretsManager(
          twilioCredentialsSecret,
          "TWILIO_PHONE_NUMBER"
        ),
        TWILIO_API_SID: ecs.Secret.fromSecretsManager(
          twilioCredentialsSecret,
          "TWILIO_API_SID"
        ),
        TWILIO_API_SECRET: ecs.Secret.fromSecretsManager(
          twilioCredentialsSecret,
          "TWILIO_API_SECRET"
        ),
      },
      healthCheck: {
        command: [
          "CMD-SHELL",
          "curl -f http://localhost:7860/health || exit 1",
        ],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10), // Increased timeout
        startPeriod: cdk.Duration.seconds(120), // Longer startup period
        retries: 5, // More retries before marking unhealthy
      },
    });

    // Port mapping
    container.addPortMappings({
      containerPort: 7860,
      protocol: ecs.Protocol.TCP,
      name: "http",
    });

    // ECS Service with optimized deployment configuration
    const service = new ecs.FargateService(this, "PipecatService", {
      cluster: this.cluster,
      taskDefinition: taskDefinition,
      serviceName: `pipecat-service-${environment}`,
      desiredCount: 3, // Increased to 3 tasks for better stability
      minHealthyPercent: 66, // Keep 2/3 healthy during deployments
      maxHealthyPercent: 200,
      healthCheckGracePeriod: cdk.Duration.seconds(300), // 5 minutes grace period
      securityGroups: [ecsSecurityGroup],
      vpcSubnets: useDefaultVpc
        ? {
            // For default VPC, use public subnets since private subnets may not exist
            subnetType: ec2.SubnetType.PUBLIC,
          }
        : {
            // For custom VPC, use private subnets with NAT gateway
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
      assignPublicIp: useDefaultVpc, // Assign public IP when using public subnets
      enableExecuteCommand: true, // For debugging
      circuitBreaker: { rollback: true }, // Enable deployment circuit breaker
    });

    // Attach service to target group
    service.attachToApplicationTargetGroup(targetGroup);

    // Auto Scaling Configuration with more conservative settings
    const scaling = service.autoScaleTaskCount({
      minCapacity: 2, // Minimum 2 tasks for HA
      maxCapacity: 6, // Increased max capacity
    });

    // Scale based on CPU utilization with higher threshold
    scaling.scaleOnCpuUtilization("CpuScaling", {
      targetUtilizationPercent: 75, // Higher threshold to reduce jittering
      scaleInCooldown: cdk.Duration.minutes(10), // Longer cooldown to prevent flapping
      scaleOutCooldown: cdk.Duration.minutes(3),
    });

    // Scale based on memory utilization with higher threshold
    scaling.scaleOnMemoryUtilization("MemoryScaling", {
      targetUtilizationPercent: 85, // Higher threshold
      scaleInCooldown: cdk.Duration.minutes(10), // Longer cooldown
      scaleOutCooldown: cdk.Duration.minutes(3),
    });

    // CloudWatch Monitoring and Alarms
    this.setupMonitoring(
      service,
      this.loadBalancer,
      targetGroup,
      environment,
      applicationLogGroup,
      accessLogGroup,
      errorLogGroup
    );

    // Create separate phone service infrastructure
    this.createPhoneService(
      environment,
      useDefaultVpc,
      applicationLogGroup,
      accessLogGroup,
      errorLogGroup,
      dailyApiKeySecret,
      awsCredentialsSecret,
      twilioCredentialsSecret,
      ecsSecurityGroup
    );

    // Store references as class properties for use by other constructs
    (this as any).targetGroup = targetGroup;
    (this as any).ecsSecurityGroup = ecsSecurityGroup;
    (this as any).logGroup = logGroup;
    (this as any).applicationLogGroup = applicationLogGroup;
    (this as any).accessLogGroup = accessLogGroup;
    (this as any).errorLogGroup = errorLogGroup;
    (this as any).dailyApiKeySecret = dailyApiKeySecret;
    (this as any).taskDefinition = taskDefinition;
    (this as any).service = service;

    // Outputs
    new cdk.CfnOutput(this, "VpcId", {
      value: this.vpc.vpcId,
      description: "VPC ID for the Pipecat deployment",
    });

    new cdk.CfnOutput(this, "ClusterName", {
      value: this.cluster.clusterName,
      description: "ECS Cluster name",
    });

    new cdk.CfnOutput(this, "RepositoryUri", {
      value: this.repository.repositoryUri,
      description: "ECR Repository URI for Pipecat container images",
    });

    new cdk.CfnOutput(this, "LoadBalancerDnsName", {
      value: this.loadBalancer.loadBalancerDnsName,
      description: "DNS name of the Application Load Balancer",
    });

    new cdk.CfnOutput(this, "TaskRoleArn", {
      value: this.taskRole.roleArn,
      description: "ARN of the ECS task role",
    });

    new cdk.CfnOutput(this, "ExecutionRoleArn", {
      value: this.executionRole.roleArn,
      description: "ARN of the ECS execution role",
    });

    new cdk.CfnOutput(this, "TaskDefinitionArn", {
      value: taskDefinition.taskDefinitionArn,
      description: "ARN of the ECS task definition",
    });

    new cdk.CfnOutput(this, "ServiceName", {
      value: service.serviceName,
      description: "Name of the ECS service",
    });

    new cdk.CfnOutput(this, "ServiceArn", {
      value: service.serviceArn,
      description: "ARN of the ECS service",
    });

    // MOVED: Log Group Outputs to main constructor where variables are in scope
    new cdk.CfnOutput(this, "ApplicationLogGroupName", {
      value: applicationLogGroup.logGroupName,
      description: "CloudWatch Log Group for application logs",
    });

    new cdk.CfnOutput(this, "AccessLogGroupName", {
      value: accessLogGroup.logGroupName,
      description: "CloudWatch Log Group for access logs",
    });

    new cdk.CfnOutput(this, "ErrorLogGroupName", {
      value: errorLogGroup.logGroupName,
      description: "CloudWatch Log Group for error logs",
    });
  }

  private setupMonitoring(
    service: ecs.FargateService,
    loadBalancer: elbv2.ApplicationLoadBalancer,
    targetGroup: elbv2.ApplicationTargetGroup,
    environment: string,
    applicationLogGroup: logs.LogGroup,
    accessLogGroup: logs.LogGroup,
    errorLogGroup: logs.LogGroup
  ) {
    // SNS Topic for alerts (optional - can be used for notifications)
    const alertTopic = new sns.Topic(this, "PipecatAlerts", {
      topicName: `pipecat-alerts-${environment}`,
      displayName: `Pipecat Voice Agent Alerts - ${environment}`,
    });

    // ECS Service Metrics and Alarms

    // CPU Utilization Alarm
    const cpuAlarm = new cloudwatch.Alarm(this, "HighCpuUtilization", {
      alarmName: `pipecat-high-cpu-${environment}`,
      alarmDescription: "ECS service CPU utilization is high",
      metric: service.metricCpuUtilization({
        period: cdk.Duration.minutes(5),
        statistic: cloudwatch.Stats.AVERAGE,
      }),
      threshold: 80,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Memory Utilization Alarm
    const memoryAlarm = new cloudwatch.Alarm(this, "HighMemoryUtilization", {
      alarmName: `pipecat-high-memory-${environment}`,
      alarmDescription: "ECS service memory utilization is high",
      metric: service.metricMemoryUtilization({
        period: cdk.Duration.minutes(5),
        statistic: cloudwatch.Stats.AVERAGE,
      }),
      threshold: 85,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Task Count Alarm (for service availability)
    const taskCountAlarm = new cloudwatch.Alarm(this, "LowTaskCount", {
      alarmName: `pipecat-low-task-count-${environment}`,
      alarmDescription: "ECS service has too few running tasks",
      metric: new cloudwatch.Metric({
        namespace: "AWS/ECS",
        metricName: "RunningTaskCount",
        dimensionsMap: {
          ServiceName: service.serviceName,
          ClusterName: service.cluster.clusterName,
        },
        period: cdk.Duration.minutes(1),
        statistic: cloudwatch.Stats.AVERAGE,
      }),
      threshold: 1,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    });

    // Application Load Balancer Metrics and Alarms

    // Target Response Time Alarm
    const responseTimeAlarm = new cloudwatch.Alarm(this, "HighResponseTime", {
      alarmName: `pipecat-high-response-time-${environment}`,
      alarmDescription: "Application response time is high",
      metric: targetGroup.metricTargetResponseTime({
        period: cdk.Duration.minutes(5),
        statistic: cloudwatch.Stats.AVERAGE,
      }),
      threshold: 5, // 5 seconds
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // HTTP 5xx Error Rate Alarm
    const http5xxAlarm = new cloudwatch.Alarm(this, "High5xxErrorRate", {
      alarmName: `pipecat-high-5xx-errors-${environment}`,
      alarmDescription: "High rate of HTTP 5xx errors",
      metric: loadBalancer.metricHttpCodeTarget(
        elbv2.HttpCodeTarget.TARGET_5XX_COUNT,
        {
          period: cdk.Duration.minutes(5),
          statistic: cloudwatch.Stats.SUM,
        }
      ),
      threshold: 10, // 10 errors in 5 minutes
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Unhealthy Host Count Alarm
    const unhealthyHostAlarm = new cloudwatch.Alarm(this, "UnhealthyHosts", {
      alarmName: `pipecat-unhealthy-hosts-${environment}`,
      alarmDescription: "Unhealthy targets detected",
      metric: targetGroup.metricUnhealthyHostCount({
        period: cdk.Duration.minutes(1),
        statistic: cloudwatch.Stats.AVERAGE,
      }),
      threshold: 0,
      evaluationPeriods: 2,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Custom CloudWatch Dashboard
    const dashboard = new cloudwatch.Dashboard(this, "PipecatDashboard", {
      dashboardName: `pipecat-voice-agent-${environment}`,
      widgets: [
        [
          // ECS Service Metrics
          new cloudwatch.GraphWidget({
            title: "ECS Service - CPU & Memory Utilization",
            left: [
              service.metricCpuUtilization({
                period: cdk.Duration.minutes(5),
                label: "CPU Utilization (%)",
              }),
            ],
            right: [
              service.metricMemoryUtilization({
                period: cdk.Duration.minutes(5),
                label: "Memory Utilization (%)",
              }),
            ],
            width: 12,
            height: 6,
          }),
        ],
        [
          // Task Count and Health
          new cloudwatch.GraphWidget({
            title: "ECS Service - Task Count",
            left: [
              new cloudwatch.Metric({
                namespace: "AWS/ECS",
                metricName: "RunningTaskCount",
                dimensionsMap: {
                  ServiceName: service.serviceName,
                  ClusterName: service.cluster.clusterName,
                },
                period: cdk.Duration.minutes(1),
                label: "Running Tasks",
              }),
            ],
            width: 6,
            height: 6,
          }),
          // ALB Response Time
          new cloudwatch.GraphWidget({
            title: "Load Balancer - Response Time",
            left: [
              targetGroup.metricTargetResponseTime({
                period: cdk.Duration.minutes(5),
                label: "Response Time (seconds)",
              }),
            ],
            width: 6,
            height: 6,
          }),
        ],
        [
          // HTTP Status Codes
          new cloudwatch.GraphWidget({
            title: "Load Balancer - HTTP Status Codes",
            left: [
              loadBalancer.metricHttpCodeTarget(
                elbv2.HttpCodeTarget.TARGET_2XX_COUNT,
                {
                  period: cdk.Duration.minutes(5),
                  label: "2xx Success",
                }
              ),
              loadBalancer.metricHttpCodeTarget(
                elbv2.HttpCodeTarget.TARGET_4XX_COUNT,
                {
                  period: cdk.Duration.minutes(5),
                  label: "4xx Client Error",
                }
              ),
              loadBalancer.metricHttpCodeTarget(
                elbv2.HttpCodeTarget.TARGET_5XX_COUNT,
                {
                  period: cdk.Duration.minutes(5),
                  label: "5xx Server Error",
                }
              ),
            ],
            width: 6,
            height: 6,
          }),
          // Target Health
          new cloudwatch.GraphWidget({
            title: "Target Group - Health Status",
            left: [
              targetGroup.metricHealthyHostCount({
                period: cdk.Duration.minutes(1),
                label: "Healthy Targets",
              }),
              targetGroup.metricUnhealthyHostCount({
                period: cdk.Duration.minutes(1),
                label: "Unhealthy Targets",
              }),
            ],
            width: 6,
            height: 6,
          }),
        ],
      ],
    });

    // Store references for potential use by other constructs
    (this as any).alertTopic = alertTopic;
    (this as any).dashboard = dashboard;
    (this as any).alarms = {
      cpu: cpuAlarm,
      memory: memoryAlarm,
      taskCount: taskCountAlarm,
      responseTime: responseTimeAlarm,
      http5xx: http5xxAlarm,
      unhealthyHosts: unhealthyHostAlarm,
    };

    // Output dashboard URL
    new cdk.CfnOutput(this, "DashboardUrl", {
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${dashboard.dashboardName}`,
      description: "CloudWatch Dashboard URL for monitoring",
    });

    new cdk.CfnOutput(this, "AlertTopicArn", {
      value: alertTopic.topicArn,
      description:
        "SNS Topic ARN for alerts (subscribe to receive notifications)",
    });

    // REMOVED: Log Group Outputs moved to main constructor
  }

  private createPhoneService(
    environment: string,
    useDefaultVpc: boolean,
    applicationLogGroup: logs.LogGroup,
    accessLogGroup: logs.LogGroup,
    errorLogGroup: logs.LogGroup,
    dailyApiKeySecret: secretsmanager.ISecret,
    awsCredentialsSecret: secretsmanager.ISecret,
    twilioCredentialsSecret: secretsmanager.ISecret,
    ecsSecurityGroup: ec2.SecurityGroup
  ) {
    // ECR Repository for phone service container images
    // Use existing phone service ECR repository
    const phoneRepository = ecr.Repository.fromRepositoryName(
      this,
      "PipecatPhoneRepository",
      `pipecat-phone-service-${environment}`
    );

    // CloudWatch Log Group for phone service
    const phoneLogGroup = new logs.LogGroup(this, "PipecatPhoneLogGroup", {
      logGroupName: `/ecs/pipecat-phone-service-${environment}/application`,
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM Roles for phone service (same permissions as main service)
    const phoneTaskRole = new iam.Role(this, "PipecatPhoneTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "Role for Pipecat Phone ECS tasks",
      inlinePolicies: {
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:InvokeModelWithBidirectionalStream", // Nova Sonic support
                "bedrock:ListFoundationModels", // For Nova Sonic testing
              ],
              resources: [
                `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-sonic-v1:0`,
                `arn:aws:bedrock:${this.region}::foundation-model/*`, // For broader access
              ],
            }),
          ],
        }),
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["secretsmanager:GetSecretValue"],
              resources: [
                `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pipecat/*`,
                dailyApiKeySecret.secretArn,
                awsCredentialsSecret.secretArn,
                twilioCredentialsSecret.secretArn,
              ],
            }),
          ],
        }),
      },
    });

    const phoneExecutionRole = new iam.Role(this, "PipecatPhoneExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      description: "Execution role for Pipecat Phone ECS tasks",
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
      inlinePolicies: {
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["secretsmanager:GetSecretValue"],
              resources: [
                `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pipecat/*`,
                dailyApiKeySecret.secretArn,
                awsCredentialsSecret.secretArn,
                twilioCredentialsSecret.secretArn,
              ],
            }),
          ],
        }),
      },
    });

    // ECS Task Definition for phone service with optimized resources
    const phoneTaskDefinition = new ecs.FargateTaskDefinition(
      this,
      "PipecatPhoneTaskDefinition",
      {
        family: `pipecat-phone-service-${environment}`,
        cpu: 2048, // 2 vCPU - same as main service for Nova Sonic
        memoryLimitMiB: 4096, // 4 GB - same as main service
        taskRole: phoneTaskRole,
        executionRole: phoneExecutionRole,
      }
    );

    // Container Definition for phone service
    const phoneContainer = phoneTaskDefinition.addContainer(
      "PipecatPhoneContainer",
      {
        image: ecs.ContainerImage.fromEcrRepository(phoneRepository, "latest"),
        containerName: "pipecat-phone-container",
        logging: ecs.LogDrivers.awsLogs({
          logGroup: phoneLogGroup,
          streamPrefix: "ecs",
          datetimeFormat: "%Y-%m-%d %H:%M:%S",
          multilinePattern: "^\\d{4}-\\d{2}-\\d{2}",
        }),
        environment: {
          AWS_REGION: this.region,
          HOST: "0.0.0.0",
          FAST_API_PORT: "7860",
          ENVIRONMENT: environment,
          LOG_LEVEL: "INFO",
          GRACEFUL_SHUTDOWN_TIMEOUT: "30",
          BOT_CLEANUP_INTERVAL: "300",
          MEMORY_CLEANUP_THRESHOLD: "0.8",
          HEALTH_CHECK_INTERVAL: "30",
          HEALTH_CHECK_RETRIES: "5",
          ENABLE_REQUEST_POOLING: "true",
          MAX_REQUEST_POOL_SIZE: "100",
          REQUEST_TIMEOUT: "30",
          SERVICE_TYPE: "phone", // Distinguish from main service
          FORCE_HTTPS: "true", // Force wss:// for Twilio WebSocket connections
        },
        secrets: {
          // Daily.co API credentials (for potential WebRTC fallback)
          DAILY_API_KEY: ecs.Secret.fromSecretsManager(
            dailyApiKeySecret,
            "DAILY_API_KEY"
          ),
          DAILY_API_URL: ecs.Secret.fromSecretsManager(
            dailyApiKeySecret,
            "DAILY_API_URL"
          ),

          // AWS credentials for Bedrock access
          AWS_ACCESS_KEY_ID: ecs.Secret.fromSecretsManager(
            awsCredentialsSecret,
            "AWS_ACCESS_KEY_ID"
          ),
          AWS_SECRET_ACCESS_KEY: ecs.Secret.fromSecretsManager(
            awsCredentialsSecret,
            "AWS_SECRET_ACCESS_KEY"
          ),

          // Twilio API credentials (primary for phone service)
          TWILIO_ACCOUNT_SID: ecs.Secret.fromSecretsManager(
            twilioCredentialsSecret,
            "TWILIO_ACCOUNT_SID"
          ),
          TWILIO_AUTH_TOKEN: ecs.Secret.fromSecretsManager(
            twilioCredentialsSecret,
            "TWILIO_AUTH_TOKEN"
          ),
          TWILIO_PHONE_NUMBER: ecs.Secret.fromSecretsManager(
            twilioCredentialsSecret,
            "TWILIO_PHONE_NUMBER"
          ),
          TWILIO_API_SID: ecs.Secret.fromSecretsManager(
            twilioCredentialsSecret,
            "TWILIO_API_SID"
          ),
          TWILIO_API_SECRET: ecs.Secret.fromSecretsManager(
            twilioCredentialsSecret,
            "TWILIO_API_SECRET"
          ),
        },
        healthCheck: {
          command: [
            "CMD-SHELL",
            "curl -f http://localhost:7860/health || exit 1",
          ],
          interval: cdk.Duration.seconds(30),
          timeout: cdk.Duration.seconds(10),
          startPeriod: cdk.Duration.seconds(120), // Longer startup period for Nova Sonic
          retries: 5,
        },
      }
    );

    // Port mapping for phone service
    phoneContainer.addPortMappings({
      containerPort: 7860,
      protocol: ecs.Protocol.TCP,
      name: "http",
    });

    // Create separate ALB for phone service (Twilio needs public access)
    const phoneAlbSecurityGroup = new ec2.SecurityGroup(
      this,
      "PhoneAlbSecurityGroup",
      {
        vpc: this.vpc,
        description: "Security group for Pipecat Phone ALB (Twilio webhooks)",
        allowAllOutbound: true,
      }
    );

    // Allow HTTP traffic from anywhere (Twilio webhooks)
    phoneAlbSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      "Allow HTTP traffic from Twilio webhooks"
    );

    // Allow HTTPS traffic from anywhere (optional, for production)
    phoneAlbSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      "Allow HTTPS traffic from Twilio webhooks"
    );

    // Create separate security group for phone service ECS tasks
    const phoneEcsSecurityGroup = new ec2.SecurityGroup(
      this,
      "PhoneEcsSecurityGroup",
      {
        vpc: this.vpc,
        description: "Security group for Pipecat Phone ECS tasks",
        allowAllOutbound: true,
      }
    );

    phoneEcsSecurityGroup.addIngressRule(
      phoneAlbSecurityGroup,
      ec2.Port.tcp(7860),
      "Allow traffic from Phone ALB to Phone ECS tasks"
    );

    // Application Load Balancer for phone service
    const phoneLoadBalancer = new elbv2.ApplicationLoadBalancer(
      this,
      "PipecatPhoneLoadBalancer",
      {
        vpc: this.vpc,
        internetFacing: true,
        securityGroup: phoneAlbSecurityGroup,
        loadBalancerName: `pipecat-phone-alb-${environment}`,
      }
    );

    // Target Group for phone service
    const phoneTargetGroup = new elbv2.ApplicationTargetGroup(
      this,
      "PipecatPhoneTargetGroup",
      {
        vpc: this.vpc,
        port: 7860,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetType: elbv2.TargetType.IP,
        healthCheck: {
          enabled: true,
          path: "/health",
          protocol: elbv2.Protocol.HTTP,
          port: "7860",
          healthyHttpCodes: "200",
          interval: cdk.Duration.seconds(30),
          timeout: cdk.Duration.seconds(10),
          healthyThresholdCount: 2,
          unhealthyThresholdCount: 5,
        },
        // WebSocket support configuration
        protocolVersion: elbv2.ApplicationProtocolVersion.HTTP1,
        stickinessCookieDuration: cdk.Duration.seconds(86400), // 24 hours for WebSocket sessions
      }
    );

    // Configure phone target group attributes for WebSocket support
    const cfnPhoneTargetGroup = phoneTargetGroup.node
      .defaultChild as elbv2.CfnTargetGroup;
    cfnPhoneTargetGroup.addPropertyOverride("TargetGroupAttributes", [
      {
        Key: "stickiness.enabled",
        Value: "true",
      },
      {
        Key: "stickiness.type",
        Value: "lb_cookie",
      },
      {
        Key: "stickiness.lb_cookie.duration_seconds",
        Value: "86400",
      },
      {
        Key: "load_balancing.algorithm.type",
        Value: "least_outstanding_requests",
      },
    ]);

    // ALB Listeners for phone service (HTTP and HTTPS)
    phoneLoadBalancer.addListener("PipecatPhoneListener", {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
      defaultTargetGroups: [phoneTargetGroup],
    });

    // Add HTTPS listener (requires certificate)
    // Uncomment and configure when you have a domain and certificate
    /*
    const certificate = acm.Certificate.fromCertificateArn(
      this,
      "PhoneServiceCertificate",
      "arn:aws:acm:region:account:certificate/certificate-id"
    );

    phoneLoadBalancer.addListener("PipecatPhoneHttpsListener", {
      port: 443,
      protocol: elbv2.ApplicationProtocol.HTTPS,
      certificates: [certificate],
      defaultTargetGroups: [phoneTargetGroup],
    });
    */

    // ECS Service for phone service with appropriate scaling
    const phoneService = new ecs.FargateService(this, "PipecatPhoneService", {
      cluster: this.cluster,
      taskDefinition: phoneTaskDefinition,
      serviceName: `pipecat-phone-service-${environment}`,
      desiredCount: 2, // Start with 2 tasks for phone service
      minHealthyPercent: 50, // Allow 1 task to be down during deployments
      maxHealthyPercent: 200,
      healthCheckGracePeriod: cdk.Duration.seconds(300), // 5 minutes grace period
      securityGroups: [phoneEcsSecurityGroup], // Use phone-specific security group
      vpcSubnets: useDefaultVpc
        ? {
            subnetType: ec2.SubnetType.PUBLIC,
          }
        : {
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
      assignPublicIp: useDefaultVpc,
      enableExecuteCommand: true, // For debugging
      circuitBreaker: { rollback: true },
    });

    // Attach phone service to phone target group
    phoneService.attachToApplicationTargetGroup(phoneTargetGroup);

    // Auto Scaling Configuration for phone service
    const phoneScaling = phoneService.autoScaleTaskCount({
      minCapacity: 1, // Minimum 1 task for phone service
      maxCapacity: 4, // Max 4 tasks for phone service
    });

    // Scale based on CPU utilization
    phoneScaling.scaleOnCpuUtilization("PhoneCpuScaling", {
      targetUtilizationPercent: 75,
      scaleInCooldown: cdk.Duration.minutes(10),
      scaleOutCooldown: cdk.Duration.minutes(3),
    });

    // Scale based on memory utilization
    phoneScaling.scaleOnMemoryUtilization("PhoneMemoryScaling", {
      targetUtilizationPercent: 85,
      scaleInCooldown: cdk.Duration.minutes(10),
      scaleOutCooldown: cdk.Duration.minutes(3),
    });

    // Store phone service references
    (this as any).phoneRepository = phoneRepository;
    (this as any).phoneTaskDefinition = phoneTaskDefinition;
    (this as any).phoneService = phoneService;
    (this as any).phoneTaskRole = phoneTaskRole;
    (this as any).phoneExecutionRole = phoneExecutionRole;
    (this as any).phoneLogGroup = phoneLogGroup;
    (this as any).phoneLoadBalancer = phoneLoadBalancer;
    (this as any).phoneTargetGroup = phoneTargetGroup;

    // Outputs for phone service
    new cdk.CfnOutput(this, "PhoneRepositoryUri", {
      value: phoneRepository.repositoryUri,
      description:
        "ECR Repository URI for Pipecat phone service container images",
    });

    new cdk.CfnOutput(this, "PhoneTaskDefinitionArn", {
      value: phoneTaskDefinition.taskDefinitionArn,
      description: "ARN of the phone service ECS task definition",
    });

    new cdk.CfnOutput(this, "PhoneServiceName", {
      value: phoneService.serviceName,
      description: "Name of the phone service ECS service",
    });

    new cdk.CfnOutput(this, "PhoneServiceArn", {
      value: phoneService.serviceArn,
      description: "ARN of the phone service ECS service",
    });

    new cdk.CfnOutput(this, "PhoneTaskRoleArn", {
      value: phoneTaskRole.roleArn,
      description: "ARN of the phone service ECS task role",
    });

    new cdk.CfnOutput(this, "PhoneExecutionRoleArn", {
      value: phoneExecutionRole.roleArn,
      description: "ARN of the phone service ECS execution role",
    });

    new cdk.CfnOutput(this, "PhoneLogGroupName", {
      value: phoneLogGroup.logGroupName,
      description: "CloudWatch Log Group for phone service logs",
    });

    new cdk.CfnOutput(this, "PhoneLoadBalancerDnsName", {
      value: phoneLoadBalancer.loadBalancerDnsName,
      description:
        "DNS name of the Phone Service Application Load Balancer (for Twilio webhooks)",
    });

    new cdk.CfnOutput(this, "TwilioWebhookUrl", {
      value: `http://${phoneLoadBalancer.loadBalancerDnsName}/incoming-call`,
      description:
        "Twilio webhook URL - configure this in your Twilio phone number settings",
    });
  }
}
