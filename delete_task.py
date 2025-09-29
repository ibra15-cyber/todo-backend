import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'TodoAppTable')
table = dynamodb.Table(table_name)

def handler(event, context):
    # CORS headers - ADD THIS SECTION
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token',
        'Content-Type': 'application/json'
    }
    
    try:
        task_id = event['pathParameters']['taskId']
        user_id = event['requestContext']['authorizer']['claims']['sub']

        table.delete_item(
            Key={
                'PK': f"USER#{user_id}",
                'SK': f"TASK#{task_id}"
            },
            ConditionExpression=Key('SK').eq(f"TASK#{task_id}")
        )
        
        return {
            'statusCode': 204,
            'headers': cors_headers,  # ADD THIS
            'body': ''
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': cors_headers,  # ADD THIS
            'body': json.dumps({'message': 'Failed to delete task.'})
        }