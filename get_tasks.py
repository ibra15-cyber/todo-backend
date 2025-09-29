import json
import boto3
import os

def handler(event, context):
    print("Event:", json.dumps(event))
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get user ID from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['TABLE_NAME'])
        
        # Query tasks for the specific user
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"USER#{user_id}") & 
                                  boto3.dynamodb.conditions.Key('SK').begins_with('TASK#')
        )
        
        tasks = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(tasks)
        }
        
    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }