# TodoPro Backend - Serverless Task Management API

A robust, scalable AWS serverless backend for a modern todo application. Built with AWS SAM and featuring real-time task management, automated expiry system, and secure user authentication.

## 🚀 Features

- **🔐 Secure Authentication** - AWS Cognito with JWT tokens and user pools
- **📝 Task Management** - Full CRUD operations with DynamoDB
- **⏰ Smart Expiry System** - EventBridge scheduled task expiration with automatic status updates
- **📧 Real-time Notifications** - SNS email alerts for expired tasks and welcome messages
- **🔄 Event-Driven Architecture** - DynamoDB Streams + SQS FIFO processing for reliable event handling
- **🌐 RESTful API** - Fully documented endpoints with CORS support
- **📊 Real-time Updates** - Stream processing for immediate task status changes

## 🏗️ Architecture

![Architecture Diagram](https://via.placeholder.com/800x400/667eea/ffffff?text=Serverless+Todo+Backend+Architecture)

The backend implements an event-driven microservices architecture:

```
Frontend → API Gateway → Lambda Functions → DynamoDB
                                     ↓
                            DynamoDB Streams
                                     ↓
                            Stream Router (Lambda)
                                     ↓
                            SQS FIFO Queue
                                     ↓
                         Process Stream (Lambda)
                                     ↓
                 EventBridge Rules ←→ Expiry Handler
                                     ↓
                            SNS Notifications
```

## 🛠️ Tech Stack

- **Framework**: AWS SAM (Serverless Application Model)
- **Database**: Amazon DynamoDB with Global Secondary Indexes
- **Compute**: AWS Lambda (Python 3.9)
- **Authentication**: Amazon Cognito User Pool & Identity Pool
- **Messaging**: Amazon SNS + SQS FIFO
- **Scheduling**: Amazon EventBridge
- **API**: Amazon API Gateway with CORS
- **Infrastructure as Code**: AWS CloudFormation via SAM

## 📋 API Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/tasks` | Create new task | ✅ Required |
| `GET` | `/tasks` | List user tasks | ✅ Required |
| `PUT` | `/tasks/{taskId}` | Update task | ✅ Required |
| `DELETE` | `/tasks/{taskId}` | Delete task | ✅ Required |
| `OPTIONS` | `/tasks` | CORS preflight | ❌ Public |

## 🚀 Deployment

### Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.9+

### Quick Deployment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd todo-backend
   ```

2. **Build the application**
   ```bash
   sam build
   ```

3. **Deploy to AWS**
   ```bash
   sam deploy --guided
   ```
   
   Follow the interactive prompts to set:
   - Stack Name: `todo-backend`
   - AWS Region: `eu-west-1` (or your preferred region)
   - Confirm changes: `Y`
   - Deployment preferences: Accept defaults

### Environment Variables

The deployment will output important configuration values:

```javascript
// Frontend configuration
const awsConfig = {
  Auth: {
    userPoolId: 'YOUR_USER_POOL_ID',
    userPoolClientId: 'YOUR_USER_POOL_CLIENT_ID', 
    identityPoolId: 'YOUR_IDENTITY_POOL_ID',
    region: 'eu-west-1'
  },
  API: {
    endpoints: [
      {
        name: 'TodoAPI',
        endpoint: 'YOUR_API_GATEWAY_URL'
      }
    ]
  }
};
```

## 📁 Project Structure

```
backend/
├── template.yaml                 # SAM infrastructure definition
├── samconfig.toml               # SAM deployment configuration
├── create_task.py               # Lambda: Create new tasks
├── get_tasks.py                 # Lambda: Retrieve user tasks
├── update_task.py               # Lambda: Update task details
├── delete_task.py               # Lambda: Delete tasks
├── cors_handler.py              # Lambda: Handle CORS preflight
├── stream_router.py             # Lambda: Route DynamoDB streams to SQS
├── process_stream.py            # Lambda: Process task events & schedule expiry
├── expiry_handler.py            # Lambda: Handle task expiration
├── post_auth.py                 # Lambda: Post-authentication hooks
└── README.md
```

## 🔧 Core Components

### Authentication Flow
1. User signs up/in via Cognito User Pool
2. Post-authentication Lambda subscribes user to SNS notifications
3. JWT tokens issued for API access
4. Identity Pool provides temporary AWS credentials

### Task Lifecycle Management
1. **Task Creation**: Tasks stored in DynamoDB with `Pending` status
2. **Expiry Scheduling**: EventBridge rule created for task deadline
3. **Status Updates**: Real-time processing via DynamoDB streams
4. **Automatic Expiry**: Tasks automatically marked expired at deadline
5. **Notifications**: SNS emails sent for expired tasks

### Event Processing Pipeline
1. DynamoDB Stream captures all table changes
2. Stream Router forwards events to SQS FIFO queue
3. Process Stream Lambda handles:
   - New tasks: Schedule expiry events
   - Updated tasks: Reschedule/cancel expiry events
   - Deleted tasks: Cancel scheduled expiry events

## 🎯 Key Features Explained

### Smart Task Expiry
- EventBridge rules scheduled for each task's deadline
- Conditional updates ensure only pending tasks are expired
- Automatic cleanup of scheduled events when tasks are completed/deleted

### Reliable Notifications
- SNS topic for all user communications
- Welcome emails on user registration
- Expiry notifications with formatted task details
- Fault-tolerant design (failures don't block auth flow)

### Scalable Architecture
- Serverless components auto-scale with demand
- FIFO queue ensures ordered processing
- Global secondary indexes enable efficient queries
- Pay-per-use pricing model

## 🔒 Security

- **JWT Authentication**: All API endpoints require valid Cognito tokens
- **IAM Roles**: Least privilege principles for Lambda functions
- **Resource Policies**: Fine-grained access control
- **Data Isolation**: User data partitioned by user ID in DynamoDB

## 📊 Monitoring & Logging

- AWS CloudWatch Logs for all Lambda functions
- DynamoDB Streams for data change tracking
- SQS metrics for queue performance
- EventBridge rules for scheduled task monitoring

## 🚨 Troubleshooting

### Common Issues

1. **Deployment Failures**
   - Verify AWS CLI credentials and permissions
   - Check SAM CLI version compatibility
   - Review CloudFormation stack events

2. **Authentication Issues**
   - Verify Cognito User Pool configuration
   - Check CORS settings in API Gateway
   - Validate JWT token expiration

3. **Task Expiry Not Working**
   - Check EventBridge rule creation in logs
   - Verify Lambda permissions for EventBridge
   - Confirm SNS topic ARN configuration

### Debugging Tips

- Enable detailed logging in Lambda functions
- Check CloudWatch Logs for each component
- Verify DynamoDB stream status
- Monitor SQS queue metrics

## 🔄 API Usage Examples

### Create Task
```javascript
const response = await fetch(`${API_ENDPOINT}/tasks`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    description: 'Complete project documentation',
    deadline: '2024-12-31T23:59:00Z'
  })
});
```

### Get User Tasks
```javascript
const response = await fetch(`${API_ENDPOINT}/tasks`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## 📈 Scaling Considerations

- **DynamoDB**: Configured with on-demand capacity
- **Lambda**: Concurrent execution limits may need adjustment
- **SQS**: FIFO queue provides exactly-once processing
- **API Gateway**: Built-in throttling and caching options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Check AWS CloudWatch logs for debugging
- Review SAM documentation
- Open an issue in the repository

---

**Built with ❤️ using AWS Serverless Technologies**