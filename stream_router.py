import json
import boto3
import os

# Initialize SQS client
sqs = boto3.client('sqs')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')

def handler(event, context):
    """
    Receives events from the DynamoDB Stream and forwards them to the SQS FIFO queue.
    """
    if not SQS_QUEUE_URL:
        print("SQS_QUEUE_URL environment variable is not set.")
        raise ValueError("SQS Queue URL missing.")

    entries = []
    
    # Process each DynamoDB record in the batch
    for record in event['Records']:
        # The entire DDB stream record is the payload for SQS
        message_body = json.dumps(record)
        
        # Use the eventID as the MessageDeduplicationId and MessageGroupId for SQS FIFO
        # The eventID is guaranteed to be unique within the stream for a specific update.
        message_id = record['eventID']

        entries.append({
            'Id': message_id,
            'MessageBody': message_body,
            'MessageDeduplicationId': message_id,
            'MessageGroupId': 'TaskProcessingGroup' # All messages go to the same group for ordered processing
        })

    if not entries:
        print("No records to send.")
        return {'statusCode': 200, 'body': 'No records processed.'}

    # Send messages in batches to SQS (max 10 messages per request)
    try:
        response = sqs.send_message_batch(
            QueueUrl=SQS_QUEUE_URL,
            Entries=entries
        )
        
        if 'Failed' in response and response['Failed']:
            print(f"Failed to send some messages: {response['Failed']}")
            # Re-raise exception to retry the DDB stream batch
            raise Exception("Failed to send all messages to SQS.")

        print(f"Successfully routed {len(entries)} records to SQS.")
        return {'statusCode': 200, 'body': 'Messages routed successfully.'}
        
    except Exception as e:
        print(f"Error sending batch to SQS: {e}")
        # Re-raise the exception to trigger the DDB stream retry mechanism
        raise