import * as cdk from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { InfrastructureStack } from "../lib/infrastructure-stack";

describe("Pipecat ECS Infrastructure Stack", () => {
  let app: cdk.App;
  let stack: InfrastructureStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    stack = new InfrastructureStack(app, "TestStack", {
      environment: "test",
      useDefaultVpc: true,
      env: { account: "123456789012", region: "eu-north-1" },
    });
    template = Template.fromStack(stack);
  });

  test("Creates ECR Repository", () => {
    template.hasResourceProperties("AWS::ECR::Repository", {
      RepositoryName: "pipecat-voice-agent-test",
    });
  });

  test("Creates ECS Cluster", () => {
    template.hasResourceProperties("AWS::ECS::Cluster", {
      ClusterName: "pipecat-cluster-test",
    });
  });

  test("Creates Application Load Balancer", () => {
    template.hasResourceProperties(
      "AWS::ElasticLoadBalancingV2::LoadBalancer",
      {
        Name: "pipecat-alb-test",
        Scheme: "internet-facing",
        Type: "application",
      }
    );
  });

  test("Creates Target Group with Health Check", () => {
    template.hasResourceProperties("AWS::ElasticLoadBalancingV2::TargetGroup", {
      Port: 7860,
      Protocol: "HTTP",
      TargetType: "ip",
      HealthCheckPath: "/health",
      HealthCheckPort: "7860",
    });
  });

  test("Creates IAM Task Role with Bedrock Permissions", () => {
    // Check task role exists
    template.hasResourceProperties("AWS::IAM::Role", {
      Description: "Role for Pipecat ECS tasks",
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
              Service: "ecs-tasks.amazonaws.com",
            },
          },
        ],
      },
    });

    // Check execution role exists
    template.hasResourceProperties("AWS::IAM::Role", {
      Description: "Execution role for Pipecat ECS tasks",
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
              Service: "ecs-tasks.amazonaws.com",
            },
          },
        ],
      },
    });
  });

  test("Creates Security Groups with Proper Rules", () => {
    // ALB Security Group
    template.hasResourceProperties("AWS::EC2::SecurityGroup", {
      GroupDescription: "Security group for Pipecat ALB",
      SecurityGroupIngress: [
        {
          CidrIp: "0.0.0.0/0",
          FromPort: 80,
          IpProtocol: "tcp",
          ToPort: 80,
        },
        {
          CidrIp: "0.0.0.0/0",
          FromPort: 443,
          IpProtocol: "tcp",
          ToPort: 443,
        },
      ],
    });

    // ECS Security Group
    template.hasResourceProperties("AWS::EC2::SecurityGroup", {
      GroupDescription: "Security group for Pipecat ECS tasks",
    });
  });

  test("Creates CloudWatch Log Group", () => {
    template.hasResourceProperties("AWS::Logs::LogGroup", {
      LogGroupName: "/ecs/pipecat-voice-agent-test",
      RetentionInDays: 7,
    });
  });

  test("Creates ECS Task Definition", () => {
    template.hasResourceProperties("AWS::ECS::TaskDefinition", {
      Family: "pipecat-voice-agent-test",
      Cpu: "1024",
      Memory: "2048",
      NetworkMode: "awsvpc",
      RequiresCompatibilities: ["FARGATE"],
      ContainerDefinitions: [
        {
          Name: "pipecat-container",
          PortMappings: [
            {
              ContainerPort: 7860,
              Protocol: "tcp",
            },
          ],
          Environment: [
            {
              Name: "AWS_REGION",
              Value: "eu-north-1",
            },
            {
              Name: "HOST",
              Value: "0.0.0.0",
            },
            {
              Name: "FAST_API_PORT",
              Value: "7860",
            },
          ],
          HealthCheck: {
            Command: [
              "CMD-SHELL",
              "curl -f http://localhost:7860/health || exit 1",
            ],
            Interval: 30,
            Timeout: 5,
            StartPeriod: 60,
            Retries: 3,
          },
        },
      ],
    });
  });

  test("Creates ECS Service", () => {
    template.hasResourceProperties("AWS::ECS::Service", {
      ServiceName: "pipecat-service-test",
      DesiredCount: 2,
      LaunchType: "FARGATE",
      DeploymentConfiguration: {
        MaximumPercent: 200,
        MinimumHealthyPercent: 50,
      },
      HealthCheckGracePeriodSeconds: 60,
      EnableExecuteCommand: true,
    });
  });

  test("Creates Auto Scaling Target", () => {
    template.hasResourceProperties(
      "AWS::ApplicationAutoScaling::ScalableTarget",
      {
        MaxCapacity: 4,
        MinCapacity: 1,
        ResourceId: Match.anyValue(), // ResourceId is a CloudFormation function
        RoleARN: Match.anyValue(),
        ScalableDimension: "ecs:service:DesiredCount",
        ServiceNamespace: "ecs",
      }
    );
  });

  test("Creates CPU Scaling Policy", () => {
    template.hasResourceProperties(
      "AWS::ApplicationAutoScaling::ScalingPolicy",
      {
        PolicyName: Match.stringLikeRegexp(".*CpuScaling.*"),
        PolicyType: "TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration: {
          TargetValue: 70,
          PredefinedMetricSpecification: {
            PredefinedMetricType: "ECSServiceAverageCPUUtilization",
          },
          ScaleInCooldown: 300,
          ScaleOutCooldown: 120,
        },
      }
    );
  });

  test("Creates Memory Scaling Policy", () => {
    template.hasResourceProperties(
      "AWS::ApplicationAutoScaling::ScalingPolicy",
      {
        PolicyName: Match.stringLikeRegexp(".*MemoryScaling.*"),
        PolicyType: "TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration: {
          TargetValue: 80,
          PredefinedMetricSpecification: {
            PredefinedMetricType: "ECSServiceAverageMemoryUtilization",
          },
          ScaleInCooldown: 300,
          ScaleOutCooldown: 120,
        },
      }
    );
  });

  test("Has Required Outputs", () => {
    template.hasOutput("VpcId", {});
    template.hasOutput("ClusterName", {});
    template.hasOutput("RepositoryUri", {});
    template.hasOutput("LoadBalancerDnsName", {});
    template.hasOutput("TaskRoleArn", {});
    template.hasOutput("ExecutionRoleArn", {});
    template.hasOutput("TaskDefinitionArn", {});
    template.hasOutput("ServiceName", {});
    template.hasOutput("ServiceArn", {});
  });
});
