import json
import boto3
import os

sns = boto3.client('sns')
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')

def handler(event, context):
    print("PostAuth function triggered with event:", json.dumps(event))
    
    # Get user email and user pool ID from the event
    user_email = event['request']['userAttributes']['email']
    user_pool_id = event['userPoolId']
    
    print(f"Processing user: {user_email} from pool: {user_pool_id}")
    
    try:
        # Subscribe the user's email to the SNS topic
        response = sns.subscribe(
            TopicArn=sns_topic_arn,
            Protocol='email',
            Endpoint=user_email
        )
        print(f"User {user_email} subscribed to SNS topic. Response: {response}")
        
        # Send a welcome email to confirm subscription is working
        welcome_message = f"""
        Welcome to the Todo App!
        
        You have been successfully subscribed to task notifications.
        You will receive emails when your tasks expire.
        
        Thank you for using our service!
        """
        
        sns.publish(
            TopicArn=sns_topic_arn,
            Subject="Welcome to Todo App - Notification Subscription Confirmation",
            Message=welcome_message
        )
        print(f"Welcome email sent to {user_email}")

    except Exception as e:
        print(f"Error in PostAuth function: {e}")
        # Don't fail the authentication process if SNS subscription fails
        # Log the error but allow the user to continue
    
    # Return the event to allow the authentication to proceed
    return event