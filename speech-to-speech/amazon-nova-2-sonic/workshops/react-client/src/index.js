// https://docs.amplify.aws/javascript/build-a-backend/restapi/customize-authz/
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { Amplify } from 'aws-amplify';
import { getCurrentUser } from 'aws-amplify/auth';

// Set to null for local deployment
let env = null;
//let env = process.env.NODE_ENV;

let awsconfig = {
  "aws_project_region": env === "production"?"[[[COGNITO_REGION]]]": process.env.REACT_APP_COGNITO_REGION,
  "aws_cognito_identity_pool_id": env === "production"? "[[[COGNITO_IDENTITY_POOL_ID]]]": process.env.REACT_APP_COGNITO_IDENTITY_POOL_ID,
  "aws_cognito_region": env === "production"? "[[[COGNITO_REGION]]]" : process.env.REACT_APP_COGNITO_REGION,
  "aws_user_pools_id": env === "production"? "[[[COGNITO_USER_POOL_ID]]]" : process.env.REACT_APP_COGNITO_USER_POOL_ID,
  "aws_user_pools_web_client_id": env === "production"? "[[[COGNITO_USER_POOL_CLIENT_ID]]]" : process.env.REACT_APP_COGNITO_USER_POOL_CLIENT_ID,
  "oauth": {},
  "aws_cognito_username_attributes": [],
  "aws_cognito_social_providers": [],
  "aws_cognito_signup_attributes": [
      "EMAIL"
  ],
  "aws_cognito_mfa_configuration": "OFF",
  "aws_cognito_mfa_types": [
      "SMS"
  ],
  "aws_cognito_password_protection_settings": {
      "passwordPolicyMinLength": 8,
      "passwordPolicyCharacters": []
  },
  "aws_cognito_verification_mechanisms": [
      "EMAIL"
  ]
};

Amplify.configure(awsconfig);
const existingConfig = Amplify.getConfig();


Amplify.configure({
  ...existingConfig,
  API: {
    ...existingConfig.API,
    REST: {
      ...existingConfig.API?.REST,
      BdaService: {
        //endpoint: env === "production"?"[[[APIGATEWAY_BASE_URL_BDA_SRV]]]": process.env.REACT_APP_APIGATEWAY_BASE_URL_BDA_SRV,
        //region: env === "production"?"[[[COGNITO_REGION]]]": process.env.REACT_APP_COGNITO_REGION
        endpoint: process.env.REACT_APP_APIGATEWAY_BASE_URL_BDA_SRV,
        region: process.env.REACT_APP_COGNITO_REGION
      },
      NovaService: {
        //endpoint: env === "production"?"[[[APIGATEWAY_BASE_URL_NOVA_SRV]]]": process.env.REACT_APP_APIGATEWAY_BASE_URL_NOVA_SRV,
        //region: env === "production"?"[[[COGNITO_REGION]]]": process.env.REACT_APP_COGNITO_REGION
        endpoint: process.env.REACT_APP_APIGATEWAY_BASE_URL_NOVA_SRV,
        region: process.env.REACT_APP_COGNITO_REGION
      }
    },
  }
});

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
    <App />
);
