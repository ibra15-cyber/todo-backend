import json
import boto3
import os
import uuid
from datetime import datetime, timezone

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
        body = json.loads(event['body'])
        description = body.get('description')
        deadline = body.get('deadline')

        user_id = event['requestContext']['authorizer']['claims']['sub']

        if not description or not deadline:
            return {
                'statusCode': 400,
                'headers': cors_headers,  # ADD THIS
                'body': json.dumps({'message': 'Description and deadline are required.'})
            }

        # Validate and format deadline
        try:
            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            formatted_deadline = deadline_dt.isoformat()
        except ValueError:
            return {
                'statusCode': 400,
                'headers': cors_headers,  # ADD THIS
                'body': json.dumps({'message': 'Invalid deadline format. Use ISO format.'})
            }

        task_id = str(uuid.uuid4())

        item = {
            'PK': f"USER#{user_id}",
            'SK': f"TASK#{task_id}",
            'GSI1PK': 'Pending',
            'GSI1SK': formatted_deadline,
            'taskId': task_id,
            'userId': user_id,
            'description': description,
            'date': datetime.now(timezone.utc).isoformat(),
            'status': 'Pending',
            'deadline': formatted_deadline
        }

        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'headers': cors_headers,  # ADD THIS
            'body': json.dumps(item)
        }
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,  # ADD THIS
            'body': json.dumps({'message': 'Failed to create task.'})
        }