import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
// import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigw from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as path from 'path';

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here

    // example resource
    // const queue = new sqs.Queue(this, 'InfraQueue', {
    //   visibilityTimeout: cdk.Duration.seconds(300)
    // });

    const fileHostingBucket = new s3.Bucket(this, 'FileHostingBucket', {
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For easy cleanup in dev, might change for prod
      autoDeleteObjects: true, // For easy cleanup in dev
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // Lambda@Edge for listing files
    const listFilesFunction = new cloudfront.experimental.EdgeFunction(this, 'ListFilesFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'list-files-function')),
    });

    listFilesFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['s3:ListBucket'],
      resources: [fileHostingBucket.bucketArn],
    }));

    listFilesFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: ['arn:aws:logs:*:*:*'],
    }));

    // Lambda for pre-signed URL
    const presignedUrlFunction = new lambda.Function(this, 'PresignedUrlFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'presigned-url-function')),
      environment: {
        S3_BUCKET_NAME: fileHostingBucket.bucketName,
      },
    });

    fileHostingBucket.grantPut(presignedUrlFunction);

    // API Gateway for pre-signed URL Lambda
    const httpApi = new apigw.HttpApi(this, 'HttpApi', {
      corsPreflight: {
        allowHeaders: ['*'],
        allowMethods: [apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.PUT, apigw.CorsHttpMethod.OPTIONS],
        allowOrigins: ['*'],
      },
    });

    httpApi.addRoutes({
      path: '/upload-url',
      methods: [apigw.HttpMethod.GET],
      integration: new HttpLambdaIntegration('PresignedUrlIntegration', presignedUrlFunction),
    });

    // Lambda@Edge for adding Content-Disposition: attachment
    const addContentDispositionFunction = new cloudfront.experimental.EdgeFunction(this, 'AddContentDispositionFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', 'lambda', 'add-content-disposition')),
    });

    // CloudFront Distribution
    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(fileHostingBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        edgeLambdas: [
          {
            functionVersion: listFilesFunction.currentVersion,
            eventType: cloudfront.LambdaEdgeEventType.ORIGIN_REQUEST,
          },
        ],
      },
      additionalBehaviors: {
        '/upload-url*': {
          origin: new origins.HttpOrigin(cdk.Fn.select(2, cdk.Fn.split('/', httpApi.url!)), {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
          }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        },
        '/download*': {
          origin: new origins.S3Origin(fileHostingBucket),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
          edgeLambdas: [
            {
              functionVersion: addContentDispositionFunction.currentVersion,
              eventType: cloudfront.LambdaEdgeEventType.ORIGIN_RESPONSE,
            },
          ],
        },
      },
    });

    new cdk.CfnOutput(this, 'CloudFrontURL', {
      value: `https://${distribution.distributionDomainName}`,
      description: 'The distribution URL',
    });
  }
}
