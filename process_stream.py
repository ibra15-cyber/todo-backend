# process_stream.py - UPDATED VERSION
import json
import boto3
import os
from datetime import datetime, timedelta, timezone

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')
sns = boto3.client('sns')

# Environment variables
TABLE_NAME = os.environ.get('TABLE_NAME', 'TodoAppTable')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
table = dynamodb.Table(TABLE_NAME)

# Rule Naming Convention
RULE_NAME_PREFIX = "TodoAppTaskExpiry"
EXPIRY_HANDLER_ARN = os.environ.get('EXPIRY_HANDLER_ARN')

def get_task_details(dynamodb_item):
    """Converts a DynamoDB item dictionary to a standard Python dictionary."""
    task = {
        'PK': dynamodb_item.get('PK', {}).get('S'),
        'SK': dynamodb_item.get('SK', {}).get('S'),
        'taskId': dynamodb_item.get('taskId', {}).get('S'),
        'userId': dynamodb_item.get('userId', {}).get('S'),
        'description': dynamodb_item.get('description', {}).get('S'),
        'status': dynamodb_item.get('status', {}).get('S'),
        'deadline': dynamodb_item.get('deadline', {}).get('S'),
    }
    # Filter out None values
    return {k: v for k, v in task.items() if v is not None}

def schedule_expiry_event(task, context):
    """Schedules an EventBridge rule to expire a PENDING task at its deadline."""
    
    if not EXPIRY_HANDLER_ARN:
        print("EXPIRY_HANDLER_ARN not set. Cannot schedule event.")
        return

    # 1. Calculate the run time for EventBridge
    deadline_dt = datetime.fromisoformat(task['deadline']).astimezone(timezone.utc)
    
    # Check if the deadline is in the future
    if deadline_dt <= datetime.now(timezone.utc):
        print(f"Task {task['taskId']} deadline is in the past. Skipping schedule.")
        return

    # Use proper cron expression for EventBridge
    cron_expression = f"cron({deadline_dt.minute} {deadline_dt.hour} {deadline_dt.day} {deadline_dt.month} ? {deadline_dt.year})"
    rule_name = f"{RULE_NAME_PREFIX}-{task['taskId']}"

    # 2. Define the Target (ExpiryHandlerFunction)
    input_data = {
        'taskId': task['taskId'],
        'userId': task['userId'],
        'pk': task['PK'],
        'sk': task['SK']
    }
    
    try:
        # Put Rule
        events.put_rule(
            Name=rule_name,
            ScheduleExpression=cron_expression,
            State='ENABLED',
            Description=f"Expires task {task['taskId']} for user {task['userId']}."
        )

        # Put Target (Link the rule to ExpiryHandlerFunction)
        events.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': 'ExpiryLambdaTarget',
                    'Arn': EXPIRY_HANDLER_ARN,
                    'Input': json.dumps(input_data)
                }
            ]
        )
        print(f"Successfully scheduled expiry for Task {task['taskId']} at {cron_expression}")
        
    except Exception as e:
        print(f"Error scheduling event for task {task['taskId']}: {e}")

def cancel_expiry_event(task_id):
    """Cancels the scheduled EventBridge rule."""
    rule_name = f"{RULE_NAME_PREFIX}-{task_id}"
    
    try:
        # 1. Remove Targets first
        targets_response = events.list_targets_by_rule(Rule=rule_name)
        if targets_response['Targets']:
            events.remove_targets(
                Rule=rule_name,
                Ids=[target['Id'] for target in targets_response['Targets']]
            )
        
        # 2. Delete Rule
        events.delete_rule(Name=rule_name)
        print(f"Successfully cancelled expiry event for Task {task_id}")
        
    except events.exceptions.ResourceNotFoundException:
        print(f"Rule {rule_name} not found (may have already been deleted)")
    except Exception as e:
        # Log and ignore error if the rule doesn't exist
        if 'ResourceNotFoundException' not in str(e):
            print(f"Error cancelling event for task {task_id}: {e}")

def expire_and_notify_task(task_id, user_id, pk, sk):
    """Handles the actual expiry logic: updates DynamoDB and sends SNS notification."""
    
    def format_date_for_email(iso_date_string):
        """Convert ISO date string to human-readable format for emails"""
        try:
            date_obj = datetime.fromisoformat(iso_date_string.replace('Z', '+00:00'))
            return date_obj.strftime('%B %d, %Y at %I:%M %p')
        except:
            return iso_date_string
    
    try:
        # 1. Check current status
        response = table.get_item(Key={'PK': pk, 'SK': sk})
        task = response.get('Item')

        if not task or task['status'] != 'Pending':
            print(f"Task {task_id} either not found or already processed (Status: {task.get('status', 'N/A')}).")
            return

        # 2. Update status to 'Expired' in DynamoDB
        table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression="SET #s = :expired, GSI1PK = :expired",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':expired': 'Expired'}
        )
        print(f"Task {task_id} status updated to Expired.")
        
        # 3. Send SNS Notification
        sns_arn = os.environ['SNS_TOPIC_ARN']
        
        # Format the deadline for human readability
        formatted_deadline = format_date_for_email(task.get('deadline', ''))
        
        message = (
            f"ALERT: Your To-Do Task has Expired!\n\n"
            f"Task: {task.get('description', 'Untitled Task')}\n"
            f"Task ID: {task_id}\n"
            f"Deadline: {formatted_deadline}\n\n"
            f"This task was due and has been automatically marked as expired. "
            f"Please log in to the Todo App to review your tasks."
        )
        
        sns.publish(
            TopicArn=sns_arn,
            Subject=f"Task Expired: {task['description']}",
            Message=message
        )
        print(f"Expiry notification sent for Task {task_id}.")

    except Exception as e:
        print(f"Error during task expiry process for {task_id}: {e}")

def handler(event, context):
    print(f"Raw event received: {json.dumps(event)}")
    
    # ----------------------------------------------------------------------
    # 1. Check if the invocation is from EventBridge (Task Expiry Trigger)
    # ----------------------------------------------------------------------
    if 'source' in event and event['source'] == 'aws.events':
        print("Invoked by EventBridge Rule for Task Expiry.")
        
        # EventBridge sends the input data differently - it might be in the 'detail' field
        # or it might be the entire event structure
        if 'detail' in event and event['detail']:
            # Input data is in the 'detail' field (common EventBridge pattern)
            task_data = event['detail']
        else:
            # Input data is the entire event (direct JSON input)
            task_data = event
        
        print(f"Task data extracted: {json.dumps(task_data)}")
        
        # Safely extract task data with defaults
        task_id = task_data.get('taskId')
        user_id = task_data.get('userId')
        pk = task_data.get('pk')
        sk = task_data.get('sk')
        
        if not all([task_id, user_id, pk, sk]):
            print(f"Missing required task data: taskId={task_id}, userId={user_id}, pk={pk}, sk={sk}")
            return {'statusCode': 400, 'body': 'Missing task data'}
        
        expire_and_notify_task(task_id, user_id, pk, sk)
        return {'statusCode': 200, 'body': 'Expiry check complete.'}

    # ----------------------------------------------------------------------
    # 2. Invocation is from SQS (DynamoDB Stream Event)
    # ----------------------------------------------------------------------
    print(f"Invoked by SQS with {len(event['Records'])} records from DynamoDB Stream.")
    
    for record in event['Records']:
        try:
            # SQS Record contains the DynamoDB Stream event as a string in the 'body'
            ddb_event = json.loads(record['body'])
            event_name = ddb_event.get('eventName')
            
            # Extract item details based on event type
            if event_name == 'INSERT':
                new_image = ddb_event['dynamodb'].get('NewImage')
                task = get_task_details(new_image)
                old_task = None
            elif event_name == 'MODIFY':
                new_image = ddb_event['dynamodb'].get('NewImage')
                old_image = ddb_event['dynamodb'].get('OldImage')
                task = get_task_details(new_image)
                old_task = get_task_details(old_image)
            elif event_name == 'REMOVE':
                old_image = ddb_event['dynamodb'].get('OldImage')
                task = get_task_details(old_image)
                old_task = None
            else:
                continue

            # Skip processing if not a Task Item
            if not task or not task.get('SK', '').startswith('TASK#'):
                continue
                
            task_id = task['taskId']
            
            # --- Logic for INSERT/MODIFY/REMOVE Events ---
            if event_name == 'INSERT' and task['status'] == 'Pending':
                # New task: schedule the expiry event
                schedule_expiry_event(task, context)
                
            elif event_name == 'MODIFY':
                # Get new status from the updated task
                new_status = task.get('status')
                old_status = old_task.get('status') if old_task else None
                
                # Check for status change to 'Completed' or 'Expired'
                if old_status == 'Pending' and new_status in ['Completed', 'Expired']:
                    # Task completed/expired: cancel the scheduled event
                    cancel_expiry_event(task_id)
                    
                # NEW LOGIC: Check if deadline changed while status remains Pending
                elif new_status == 'Pending' and old_status == 'Pending':
                    old_deadline = old_task.get('deadline') if old_task else None
                    new_deadline = task.get('deadline')
                    
                    if old_deadline and new_deadline and old_deadline != new_deadline:
                        print(f"Deadline changed for task {task_id}. Rescheduling expiry event.")
                        # Cancel existing event and schedule new one with updated deadline
                        cancel_expiry_event(task_id)
                        schedule_expiry_event(task, context)
                        
            elif event_name == 'REMOVE':
                # Task was deleted: cancel the scheduled event
                cancel_expiry_event(task_id)
                
        except Exception as e:
            print(f"Error processing SQS record: {e}")
            # IMPORTANT: Re-raise the exception to trigger SQS FIFO retry
            raise
    
    return {'statusCode': 200, 'body': 'Stream processing complete.'}