# expiry_handler.py - UPDATED WITH BETTER DATE FORMATTING
import json
import boto3
import os
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
TABLE_NAME = os.environ.get('TABLE_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
table = dynamodb.Table(TABLE_NAME)

def format_date_for_email(iso_date_string):
    """Convert ISO date string to human-readable format for emails"""
    try:
        date_obj = datetime.fromisoformat(iso_date_string.replace('Z', '+00:00'))
        # Format as: September 29, 2025 at 3:09 PM
        return date_obj.strftime('%B %d, %Y at %I:%M %p')
    except:
        # Fallback to original format if parsing fails
        return iso_date_string

def handler(event, context):
    print(f"Expiry Handler invoked for event: {json.dumps(event)}")
    
    # The event payload comes directly from EventBridge target input
    # It should be: {'taskId': 'xxx', 'userId': 'xxx', 'pk': 'xxx', 'sk': 'xxx'}
    task_id = event.get('taskId')
    user_id = event.get('userId')
    pk = event.get('pk')
    sk = event.get('sk')
    
    if not all([task_id, user_id, pk, sk]):
        print(f"Error: Missing required task data in event: {event}")
        return {'statusCode': 400, 'body': 'Missing task data'}

    # 1. Conditionally Update Task Status in DynamoDB
    # Only update to 'Expired' if the status is still 'Pending'
    try:
        update_response = table.update_item(
            Key={
                'PK': pk,
                'SK': sk
            },
            UpdateExpression="SET #s = :expired, GSI1PK = :expired",
            ConditionExpression=Attr('status').eq('Pending'),
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':expired': 'Expired'},
            ReturnValues="ALL_NEW"
        )
        
        # 2. If Update was successful, send SNS Notification
        task_details = update_response['Attributes']
        print(f"Task {task_id} successfully expired. Notifying user.")

        # Format the deadline for human readability
        formatted_deadline = format_date_for_email(task_details.get('deadline', ''))
        
        message = (
            f"ALERT: Your To-Do Task has Expired!\n\n"
            f"Task: {task_details.get('description', 'Untitled Task')}\n"
            f"Task ID: {task_id}\n"
            f"Deadline: {formatted_deadline}\n\n"
            f"This task was due and has been automatically marked as expired. "
            f"Please log in to the Todo App to review your tasks."
        )
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Task Expired: {task_details.get('description', 'Untitled Task')}",
            Message=message
        )
        print(f"Expiry notification sent for Task {task_id}")
        
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # This is expected if the user manually marked it 'Completed' or 'Deleted'
        print(f"Task {task_id} status was not 'Pending'. No update performed and no email sent.")
        
    except Exception as e:
        print(f"Error processing task expiry for {task_id}: {e}")
        # Re-raise to trigger Lambda retry if necessary
        raise

    return {'statusCode': 200, 'body': 'Expiry process completed.'}