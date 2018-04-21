***AWS Lambda Function with SNS for ECS Cluster Auto Scaling***

---

Environment: Python2.7

`This is a Lambda Serverless function for auto scaling ECS instances and container count by Cloudwatch Alarm`

Trigger by SNS 
And CloudWatch Alarm trigger SNS 

For ECS cluster auto scaling instances and tasks(containers)
Auto start instances which are already registered in cluster but stopped.
When instances status is running will increase desired task count by percent. 



***License***

[MIT](./LICENSE)
