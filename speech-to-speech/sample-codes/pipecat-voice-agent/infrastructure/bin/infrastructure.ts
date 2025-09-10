#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { InfrastructureStack } from "../lib/infrastructure-stack";

const app = new cdk.App();

// Get environment from context or default to 'test'
const environment = app.node.tryGetContext("environment") || "test";
const useDefaultVpc = app.node.tryGetContext("useDefaultVpc") !== false;

new InfrastructureStack(app, `PipecatEcsStack-${environment}`, {
  environment: environment,
  useDefaultVpc: useDefaultVpc,

  // Use current CLI configuration for account/region
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },

  // Add tags for resource management
  tags: {
    Project: "Pipecat-Voice-Agent",
    Environment: environment,
    ManagedBy: "CDK",
  },
});
