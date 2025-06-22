import boto3
import os
import json
from botocore.exceptions import ClientError
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    bucket_name = os.environ['S3_BUCKET_NAME']
    
    # Get filename from query string parameters
    try:
        filename = event['queryStringParameters']['filename']
        content_type = event['queryStringParameters'].get('contentType', 'application/octet-stream')
    except (KeyError, TypeError):
        logger.error("'filename' query parameter is missing.")
        return {
            'statusCode': 400,
            'headers': {
                "Access-Control-Allow-Origin" : "*",
                "Access-Control-Allow-Methods" : "GET,PUT,OPTIONS",
                "Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({'error': 'filename query parameter is required'})
        }

    try:
        logger.info(f"Generating pre-signed URL for {filename} in bucket {bucket_name}")
        # Generate a pre-signed URL for the S3 object
        response = s3_client.generate_presigned_url('put_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': filename,
                                                            'ContentType': content_type},
                                                    ExpiresIn=300) # 5 minutes
    except ClientError as e:
        logger.error(f"Failed to generate pre-signed URL: {e}")
        return {
            'statusCode': 500,
            'headers': {
                "Access-Control-Allow-Origin" : "*",
                "Access-Control-Allow-Methods" : "GET,PUT,OPTIONS",
                "Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
            },
            'body': json.dumps({'error': 'Failed to generate pre-signed URL'})
        }

    logger.info(f"Successfully generated pre-signed URL: {response}")

    # Return the pre-signed URL
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin" : "*", # Required for CORS
            "Access-Control-Allow-Methods" : "GET,PUT,OPTIONS",
            "Access-Control-Allow-Headers" : "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
        },
        'body': json.dumps({'url': response})
    } 