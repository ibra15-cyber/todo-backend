# update_task.py - FIXED DATE PARSING
import json
import boto3
import os
from datetime import datetime, timezone
import re

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'TodoAppTable')
table = dynamodb.Table(table_name)

def handler(event, context):
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token',
        'Content-Type': 'application/json'
    }
    
    try:
        # Extract user ID from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Extract task ID from path parameters
        task_id = event['pathParameters']['taskId']
        
        # Parse request body
        body = json.loads(event['body'])
        
        print(f"Updating task {task_id} for user {user_id}")
        print(f"Update data: {body}")

        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}
        
        if 'description' in body:
            update_parts.append("description = :desc")
            expression_values[':desc'] = body['description']
        
        if 'status' in body:
            update_parts.append("#s = :status")
            expression_names['#s'] = 'status'
            expression_values[':status'] = body['status']
        
        if 'deadline' in body:
            # FIXED: Better date parsing that handles multiple formats
            try:
                deadline_input = body['deadline']
                print(f"Parsing deadline: {deadline_input}")
                
                # Handle different date formats
                if deadline_input.endswith('Z'):
                    # Handle Zulu time format: 2025-09-29T18:56:00.000Z
                    deadline_dt = datetime.fromisoformat(deadline_input.replace('Z', '+00:00'))
                elif '+' in deadline_input:
                    # Handle timezone offset format: 2025-09-29T18:55:00+00:00
                    deadline_dt = datetime.fromisoformat(deadline_input)
                else:
                    # Assume UTC if no timezone specified
                    deadline_dt = datetime.fromisoformat(deadline_input).replace(tzinfo=timezone.utc)
                
                # Ensure UTC timezone
                if deadline_dt.tzinfo is None:
                    deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                else:
                    deadline_dt = deadline_dt.astimezone(timezone.utc)
                
                # Format to ISO string with timezone
                formatted_deadline = deadline_dt.isoformat()
                print(f"Formatted deadline: {formatted_deadline}")
                
                update_parts.append("deadline = :deadline")
                update_parts.append("GSI1SK = :gsi1sk")
                expression_values[':deadline'] = formatted_deadline
                expression_values[':gsi1sk'] = formatted_deadline
                
            except ValueError as e:
                print(f"Invalid deadline format: {body['deadline']}, error: {e}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'message': f'Invalid deadline format: {str(e)}'})
                }
        
        if not update_parts:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'No fields to update'})
            }
        
        update_expression = "SET " + ", ".join(update_parts)
        
        # Prepare update parameters
        update_params = {
            'Key': {
                'PK': f"USER#{user_id}",
                'SK': f"TASK#{task_id}"
            },
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': "ALL_NEW"
        }
        
        # Only add ExpressionAttributeNames if we have them
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        # Perform the update
        print(f"Update params: {update_params}")
        response = table.update_item(**update_params)
        
        print(f"Update successful: {response['Attributes']}")
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response['Attributes'])
        }
        
    except Exception as e:
        print(f"Update error: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Traceback: {traceback_str}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Failed to update task',
                'error': str(e)
            })
        }