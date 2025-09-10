#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PipecatEksStack } from '../lib/pipecat-eks-stack';

const app = new cdk.App();

const environment = app.node.tryGetContext('environment') || 'test';
const useDefaultVpc = app.node.tryGetContext('useDefaultVpc') === 'true';

new PipecatEksStack(app, `PipecatEksStack-${environment}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'eu-north-1',
  },
  environment,
  useDefaultVpc,
});