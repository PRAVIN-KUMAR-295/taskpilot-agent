# TaskPilot Agent — AWS Deployment Guide

This guide details the step-by-step procedure to transition TaskPilot Agent from the local development environment to production AWS infrastructure.

---

## Architecture Readiness Checklist

- [x] **Local Implementation:** Fully working local FastAPI server with modular agent orchestrator, SQLite database, and vanilla JS SPA.
- [x] **Zero-Key Offline Fallback:** LocalProvider delivers 100% deterministic demo execution without external keys.
- [x] **AWS Bedrock Provider:** Pre-wired via `boto3` in `backend/agent/providers.py` with automatic credential detection.
- [x] **DynamoDB Mapping:** Complete Single-Table NoSQL schema designed in `aws/architecture.md`.
- [x] **Cognito Migration Path:** JWT token generation and validation structures aligned with standard Cognito claims.

---

## 1. Prerequisites

- AWS CLI v2 installed and configured (`aws configure`)
- AWS SAM CLI or AWS CDK installed
- Node.js 18+ and Python 3.11+
- Amazon Bedrock model access granted in your AWS Region (e.g., `us-east-1` or `us-west-2`) for Anthropic Claude 3.5 Sonnet or Amazon Titan.

---

## 2. Backend Deployment (AWS Lambda + API Gateway)

We package the FastAPI application using the `Mangum` ASGI adapter:

### 2.1 Lambda Handler Entrypoint (`backend/lambda_handler.py`)

```python
from mangum import Mangum
from main import app

# AWS Lambda Entrypoint
handler = Mangum(app, lifespan="off")
```

### 2.2 AWS SAM Template (`template.yaml`)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: TaskPilot Agent Serverless Backend

Globals:
  Function:
    Timeout: 30
    MemorySize: 512
    Runtime: python3.11
    Environment:
      Variables:
        AWS_REGION: !Ref AWS::Region
        BEDROCK_MODEL_ID: 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        JWT_SECRET: !Ref JWTSecretParameter

Parameters:
  JWTSecretParameter:
    Type: String
    NoEcho: true
    Description: Secret key for signing JWT tokens

Resources:
  TaskPilotApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./backend
      Handler: lambda_handler.handler
      Policies:
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: '*'
            - Effect: Allow
              Action:
                - dynamodb:PutItem
                - dynamodb:GetItem
                - dynamodb:UpdateItem
                - dynamodb:DeleteItem
                - dynamodb:Query
                - dynamodb:Scan
              Resource: !GetAtt TaskPilotTable.Arn
      Events:
        ApiRoot:
          Type: HttpApi
          Properties:
            Path: /{proxy+}
            Method: ANY

  TaskPilotTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: TaskPilotStore
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1_PK
          AttributeType: S
        - AttributeName: GSI1_SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1_PK
              KeyType: HASH
            - AttributeName: GSI1_SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL

Outputs:
  ApiUrl:
    Description: HTTP API Endpoint URL
    Value: !Sub 'https://${ServerlessHttpApi}.execute-api.${AWS::Region}.amazonaws.com'
```

### 2.3 Deploy Command

```bash
sam build
sam deploy --guided
```

---

## 3. Frontend Deployment (AWS Amplify Hosting)

Deploying the Single-Page Application (SPA) to AWS Amplify:

### 3.1 Via Amplify CLI

```bash
# Initialize Amplify in frontend directory
cd frontend
amplify init
amplify add hosting
amplify publish
```

### 3.2 Via AWS S3 + CloudFront

1. Create an S3 Bucket:
```bash
aws s3 mb s3://taskpilot-agent-frontend --region us-east-1
```
2. Sync the frontend static assets:
```bash
aws s3 sync ./frontend s3://taskpilot-agent-frontend --acl public-read
```
3. Create a CloudFront Distribution pointing to the S3 bucket with HTTPS redirection and custom domain.

---

## 4. Amazon Bedrock Permissions Setup

Attach the following policy to the Lambda execution role to enable AI reasoning:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*:*:foundation-model/amazon.titan-text-express-v1"
      ]
    }
  ]
}
```

---

## 5. Amazon Cognito Authentication Setup

1. **Create User Pool:**
   ```bash
   aws cognito-idp create-user-pool --pool-name taskpilot-users \
       --auto-verified-attributes email \
       --username-attributes email
   ```
2. **Create User Pool Client:**
   ```bash
   aws cognito-idp create-user-pool-client --user-pool-id <POOL_ID> \
       --client-name taskpilot-spa-client \
       --no-generate-secret
   ```
3. Set environment variables on the backend:
   ```bash
   COGNITO_USER_POOL_ID=<POOL_ID>
   COGNITO_APP_CLIENT_ID=<CLIENT_ID>
   ```

---

## 6. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AWS_REGION` | `us-east-1` | AWS Region for Bedrock and DynamoDB |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Target model in Amazon Bedrock |
| `JWT_SECRET` | `taskpilot-agent-super-secret-jwt-key-2026` | Key used for signing session tokens |
| `JWT_EXPIRATION_MINUTES`| `1440` | Token expiration duration (24 hours) |
| `AI_PROVIDER` | `auto` | Choose `bedrock`, `openai`, `local`, or `auto` |
| `DATABASE_PATH` | `data/taskpilot.db` | Local SQLite path (maps to DynamoDB in cloud) |
