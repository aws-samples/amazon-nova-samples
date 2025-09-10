import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
//import { KubectlV30Layer } from 'aws-cdk-lib/lambda-layer-kubectl';
import { Construct } from 'constructs';

export interface PipecatEksStackProps extends cdk.StackProps {
  environment: string;
  useDefaultVpc: boolean;
}

export class PipecatEksStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: PipecatEksStackProps) {
    super(scope, id, props);

    const { environment, useDefaultVpc } = props;

    // VPC Configuration
    let vpc: ec2.IVpc;
    if (useDefaultVpc) {
      vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', {
        isDefault: true,
      });
    } else {
      vpc = new ec2.Vpc(this, 'PipecatVpc', {
        maxAzs: 2,
        natGateways: 2,
        subnetConfiguration: [
          {
            cidrMask: 24,
            name: 'Public',
            subnetType: ec2.SubnetType.PUBLIC,
          },
          {
            cidrMask: 24,
            name: 'Private',
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          },
        ],
      });
    }

    // ECR Repositories (reuse existing ones if they exist)
    const voiceAgentRepo = ecr.Repository.fromRepositoryName(
      this,
      'VoiceAgentRepository',
      `pipecat-voice-agent-${environment}`
    );

    const phoneServiceRepo = ecr.Repository.fromRepositoryName(
      this,
      'PhoneServiceRepository',
      `pipecat-phone-service-${environment}`
    );

    // CloudWatch Log Groups
    const appLogGroup = new logs.LogGroup(this, 'ApplicationLogGroup', {
      logGroupName: `/eks/pipecat-voice-agent-${environment}/application`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const phoneLogGroup = new logs.LogGroup(this, 'PhoneLogGroup', {
      logGroupName: `/eks/pipecat-phone-service-${environment}/application`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // EKS Cluster
    const cluster = new eks.Cluster(this, 'PipecatCluster', {
      clusterName: `pipecat-eks-cluster-${environment}`,
      version: eks.KubernetesVersion.V1_31,
      vpc,
      defaultCapacity: 0, // We'll use Fargate
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,
      kubectlLayer: lambda.LayerVersion.fromLayerVersionArn(
        this,
        'KubectlLayer',
        `arn:aws:lambda:${this.region}:017000801446:layer:kubectl:1`
      ),
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.SCHEDULER,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
      ],
    });

    // Fargate Profile
    cluster.addFargateProfile('PipecatFargateProfile', {
      selectors: [
        {
          namespace: 'pipecat',
        },
        {
          namespace: 'kube-system',
          labels: {
            'app.kubernetes.io/name': 'aws-load-balancer-controller',
          },
        },
      ],
      vpc,
      subnetSelection: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
    });

    // Service Account for Pipecat applications
    const pipecatServiceAccount = cluster.addServiceAccount('PipecatServiceAccount', {
      name: 'pipecat-service-account',
      namespace: 'pipecat',
    });

    // Add permissions for Secrets Manager and other AWS services
    pipecatServiceAccount.addToPrincipalPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret',
      ],
      resources: [
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:pipecat/*`,
      ],
    }));

    pipecatServiceAccount.addToPrincipalPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: ['*'],
    }));

    pipecatServiceAccount.addToPrincipalPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
        'logs:DescribeLogStreams',
      ],
      resources: [
        appLogGroup.logGroupArn,
        phoneLogGroup.logGroupArn,
      ],
    }));

    // Install AWS Load Balancer Controller
    const albController = new eks.HelmChart(this, 'AWSLoadBalancerController', {
      cluster,
      chart: 'aws-load-balancer-controller',
      repository: 'https://aws.github.io/eks-charts',
      namespace: 'kube-system',
      values: {
        clusterName: cluster.clusterName,
        serviceAccount: {
          create: true,
          name: 'aws-load-balancer-controller',
          annotations: {
            'eks.amazonaws.com/role-arn': pipecatServiceAccount.role.roleArn,
          },
        },
        region: this.region,
        vpcId: vpc.vpcId,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'EKS Cluster Name',
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
      description: 'EKS Cluster Endpoint',
    });

    new cdk.CfnOutput(this, 'VoiceAgentRepositoryUri', {
      value: voiceAgentRepo.repositoryUri,
      description: 'Voice Agent ECR Repository URI',
    });

    new cdk.CfnOutput(this, 'PhoneServiceRepositoryUri', {
      value: phoneServiceRepo.repositoryUri,
      description: 'Phone Service ECR Repository URI',
    });

    new cdk.CfnOutput(this, 'ApplicationLogGroupName', {
      value: appLogGroup.logGroupName,
      description: 'Application Log Group Name',
    });

    new cdk.CfnOutput(this, 'PhoneLogGroupName', {
      value: phoneLogGroup.logGroupName,
      description: 'Phone Service Log Group Name',
    });

    new cdk.CfnOutput(this, 'KubectlCommand', {
      value: `aws eks update-kubeconfig --region ${this.region} --name ${cluster.clusterName}`,
      description: 'Command to configure kubectl',
    });

    new cdk.CfnOutput(this, 'ServiceAccountArn', {
      value: pipecatServiceAccount.role.roleArn,
      description: 'Pipecat Service Account Role ARN',
    });
  }
}