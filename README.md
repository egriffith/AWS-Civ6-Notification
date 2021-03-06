# AWS-Civ6-Notification
This project contains  json/yaml Cloudformation templates (under the Cloudformation directory), generated by the Troposphere script at the root of the directory. It is used to create an API Gateway endpoint, Lambda function, and SNS topic to be used with Civilization 6's new "Play By Cloud" functionality. 

The lambda code also has the ability to post a message to a Discord Webhook URL.

This cloudformation template spins up the following resources:

1) A Lambda function
2) A Lambda policy allowing it to be invoked by API Gateway.
3) A Lambda Execution IAM role & IAM policy allowing it to post to Cloudwatch Logs, Publish an SNS message, and invoke itself. 
4) An API Gateway end point with a 'civ6' resource, a 'prod' stage and accompanying deployment.
5) An SNS topic to be subscribed to. Though no messages are published to it unless the 'SendToSNS' parameter is set to True.

While 'SendToSNS' and 'SendToDiscord' are configurable independently, one of them to needs to be set to True for this template to be of any value.

If you desire SNS notifications, then please subscribe to the SNS topic ARN that is available under the Template's "Outputs" tab.

Once the template is complete, please copy-paste the Api Gateway endpoint URL that is available under the "Outputs" tab to the Civilization 6 Webhook settings panel in the game.