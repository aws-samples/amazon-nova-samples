# Function call with structured JSON

## Deployment Guide

### Prerequisites

Before you begin, ensure all prerequisites are in place. You should have:

* An AWS account
* The AWS CLI installed and configured with your credentials
* The latest LTS version of Node.js
* Requested access to amazon.Nova-pro-v1:0 via Bedrock model access

1) Build CDK project

```
npm install -g typescript
mkdir sample-app && cd sample-app
cdk init sample-app --language typescript
```

2) Copy Sample IaC

* navigate into the newly created entry point file (bin/sample-app-stack.ts) and add the following

```
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { SampleAppStack } from '../lib/sample-app-stack';

const app = new cdk.App();
new SampleAppStack(app, 'SampleAppStack-agi-function-call');
```

* navigate into the newly created stack definition file (lib/sample-app-stack.ts) and add the following

```
import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";

export class SampleAppStack extends Stack {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    /* 
     * IAM (for allowing the sagemaker notebook to call the apigateway/bedrock)
     */

    const iamRoleSagemaker = new iam.Role(this, `iamRoleSagemaker`, {
      assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
    });
    iamRoleSagemaker.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess')
    )
    iamRoleSagemaker.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        resources: [
          "*"
        ],
        actions: [
          "bedrock:*"
        ],
      })
    );

    /* 
     * Sagemaker (for running the notebook)
     */

    const sagemakerNotebook = new sagemaker.CfnNotebookInstance(this, 'sagemakerNotebook', {
      instanceType: 'ml.t3.medium',
      roleArn: iamRoleSagemaker.roleArn
    });

    /* 
     * ApiGateway (for testing the tool calls)
     */

    const apigatewayRestApi = new apigateway.RestApi(this, 'apigatewayRestApi', {
    
    });

    const apigatewayModelRequest = new apigateway.Model(this, "apigatewayModelRequest", {
      restApi: apigatewayRestApi,
      contentType: "application/json",
      description: "To validate the request body",
      modelName: "request",
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'request',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          country: { type: apigateway.JsonSchemaType.STRING },
          dates: { 
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              date_start: { type: apigateway.JsonSchemaType.STRING },
              date_end: { type: apigateway.JsonSchemaType.STRING }
            }
          }
        },
        required: [
          "country",
          "dates"
        ]
      }
    });

    const apigatewayModelResponse = new apigateway.Model(this, "apigatewayModelResponse", {
      restApi: apigatewayRestApi,
      contentType: "application/json",
      description: "To send back to client",
      modelName: "response",
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'request',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          message: { type: apigateway.JsonSchemaType.STRING }
        },
        required: [
          "message"
        ]
      }
    });

    const apigatewayRequestValidator = new apigateway.RequestValidator(this, "apigatewayRequestValidator", {
      restApi: apigatewayRestApi,
      requestValidatorName: 'request',
      validateRequestBody: true
    })

    apigatewayRestApi.root.addMethod('POST', new apigateway.MockIntegration(
      {
        integrationResponses: [
          {
            statusCode: '200',
            responseTemplates: {
              'application/json': JSON.stringify({ message: 'the weather is sunny' })
            }
          }
        ],
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': JSON.stringify({ "statusCode": 200 })
        }
      }
    ), {
      methodResponses: [
        {
          statusCode: '200',
          responseModels: {
            'application/json': apigatewayModelResponse
          }
        }
      ],
      requestModels: {
        'application/json': apigatewayModelRequest
      },
      requestValidator: apigatewayRequestValidator,
      authorizationType: apigateway.AuthorizationType.IAM
    });

    iamRoleSagemaker.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        resources: [
          // `arn:aws:execute-api:${this.region}:${this.account}:${apigatewayRestApi.restApiId}/prod/POST/*`
          `*`
        ],
        actions: [
          "execute-api:*"
        ],
      })
    );
  }
}
```

3) Deploy Infra

```
# set your region
export AWS_REGION=us-east-1

# bootstrap cdk (if this is the first time you’re using the account / region with CDK)
cdk bootstrap

# deploy cdk
cdk deploy
```

4) Setup Notebook

Once the CDK completes the deployment, you will find the a Sagemaker Notebook instance in your Sagemaker AWS Console: 
If we open the demo code provided in our notebook (notebooks/function_call.ipynb), you’ll see an interactive demo that 

* prompts for input
* checks to see “how” it can answer
* creates a payload for the deployed Mock API Gateway
* invokes the downstream Mock API Gateway
* and then uses the response to answer the user request

## Post Activities

Don’t forget to delete all resources created during this tutorial and stop recurring costs, you can do that using the cdk command line:

```
cdk destroy -y
```

