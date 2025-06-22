#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { InfraStack } from '../lib/infra-stack';

const app = new cdk.App();
new InfraStack(app, 'S3FilePortalStack', {
  /* This is required for stacks with Edge Lambdas */
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: 'us-east-1' 
  },
  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});