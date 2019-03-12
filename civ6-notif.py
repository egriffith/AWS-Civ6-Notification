from troposphere import Ref, Template, Output, Parameter
from troposphere.iam import Role, PolicyType
from troposphere.awslambda import Function, Code, Permission, Environment
from troposphere.apigateway import RestApi, Method, MethodResponse, IntegrationResponse, Integration, Stage, Deployment, Resource
from troposphere import GetAtt, Join
from troposphere.sns import Topic
from pathlib import Path

template = Template()
template.set_description("AWS CloudFormation template to spin up an API Gateway, Lambda function, and SNS topic to receive, transform, and retransmit Civilization 6 Play By Cloud notifications.")

SendToSNS = Parameter(
    "SendToSNS",
    Type="String",
    AllowedValues = ["True", "False"],
    Default="False",
    Description="Enabling this will tell the lambda function to send messages to an SNS topic. This can be useful if you want to receive text message or email notifications from the games. For new users of SNS, this setting is free. For existing SNS users, this setting may raise your AWS bill by <$1.00 a month.",
)

SendToDiscord = Parameter(
    "SendToDiscord",
    Type="String",
    AllowedValues = ["True", "False"],
    Default="False",
    Description="Enabling this will tell the lambda function to send messages to a Discord Webhook URL.",
)

DiscordWebhookURL = Parameter(
    "DiscordWebhookURL",
    Type="String",
    Description="Please paste here the URL that Discord provided to you when you created your server's Webhook.",
    NoEcho=True
)

Civ6Notif_GW = RestApi(
    "Civ6NotifGW",
    Name="Civ6Notifications"
    )

Civ6Notif_Role = Role(
    "Civ6NotifLambdaExecutionRole",
    Path="/",
    AssumeRolePolicyDocument={
        "Version":"2012-10-17",
        "Statement": [
            {
                "Action": ["sts:AssumeRole"],
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "lambda.amazonaws.com",
                        "apigateway.amazonaws.com"
                    ]
                }
            }
        ]
    }
)

Civ6Notif_RolePolicy = PolicyType(
    "Civ6NotifRolePolicy",
    PolicyName="Civ6Notif_RolePolicy",
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "*",
                "Effect": "Allow"
            },
            {
                "Action": ["sns:Publish"],
                "Resource": "*",
                "Effect": "Allow"
            },
            {
                "Action": ["lambda:*"],
                "Resource": "*",
                "Effect": "Allow"
            }
        ]
    },
    Roles=[Ref("Civ6NotifLambdaExecutionRole")]
)

Civ6Notif_SNS = Topic(
    "Civ6NotifTopic",
    DisplayName = "Civ6Notification")

code = [
    "from botocore.vendored import requests\n",
    "import json\n",
    "import os\n",
    "import boto3\n",
    "import logging\n",
    "logger = logging.getLogger()\n",
    "logger.setLevel(logging.INFO)\n",
    "\n",
    "def lambda_handler(event, context):\n",
    "\tlogger.INFO('Received event: %s', event)\n"
    "\tmsg = f'It is now {event[\"value2\"]}\\'s turn in Civ6 game {event[\"value1\"]}'\n\n",
    "\tif os.environ['SendToDiscord'] == 'True':\n",
    "\t\tr = requests.post(os.environ['DiscordWebhookURL'],json={'content':msg})\n",
    "\t\tlogger.INFO('%s', r)\n",
    "\n\n",
    "\tif os.environ['SendToSNS'] == 'True':\n",
    "\t\tclient = boto3.client('sns')\n",
    "\t\tclient.publish(TopicArn=os.environ['SNSTopic'],Message=msg,Subject='Civilization 6 Play By Cloud Notifications')\n\n",
    "\treturn {}"
]

Civ6Notif_Lambda = Function(
    "Civ6NotifFunction",
    Code=Code(
        ZipFile=Join("", code)
    ),
    Handler="index.lambda_handler",
    Role=GetAtt("Civ6NotifLambdaExecutionRole", "Arn"),
    Runtime="python3.7",
    Environment=Environment(Variables={
        "SendToSNS":Ref("SendToSNS"),
        "SendToDiscord": Ref("SendToDiscord"),
        "SNSTopic":Join("",
            [
                "arn:aws:sns:",
                Ref("AWS::Region"),
                ":",
                Ref("AWS::AccountId"),
                ":",
                GetAtt("Civ6NotifTopic", "TopicName")
            ]),
        "DiscordWebhookURL": Ref("DiscordWebhookURL")
        }
    )
)


Civ6Notif_LambdaPermission = Permission(
    "Civ6LambdaPermission",
    Action="lambda:InvokeFunction",
    Principal="apigateway.amazonaws.com",
    FunctionName=GetAtt("Civ6NotifFunction","Arn")
)

Civ6Notif_GW_Resource = Resource(
    "Civ6NotifResource",
    RestApiId=Ref(Civ6Notif_GW),
    PathPart="civ6",
    ParentId=GetAtt("Civ6NotifGW", "RootResourceId"),
)

Civ6Notif_PostMethod = Method(
    "Civ6NotifPostMethod",
    DependsOn='Civ6NotifFunction',
    RestApiId=Ref(Civ6Notif_GW),
    AuthorizationType="NONE",
    ResourceId=Ref(Civ6Notif_GW_Resource),
    HttpMethod="POST",
    Integration=Integration(
        Credentials=GetAtt("Civ6NotifLambdaExecutionRole", "Arn"),
        Type="AWS",
        IntegrationHttpMethod='POST',
        IntegrationResponses=[
            IntegrationResponse(
                StatusCode='200'
            )
        ],
        Uri=Join("", [
            "arn:aws:apigateway:",
            Ref("AWS::Region"),
            ":lambda:path/2015-03-31/functions/",
            GetAtt("Civ6NotifFunction", "Arn"),
            "/invocations"
        ])
    ),
    MethodResponses=[
        MethodResponse(
            "CatResponse",
            StatusCode='200'
        )
    ]
)

stage_name = "prod"

Civ6Notif_GW_Deployment = Deployment(
    f'{stage_name}Deployment',
    RestApiId=Ref(Civ6Notif_GW),
    DependsOn="Civ6NotifPostMethod"
)

Civ6Notif_GW_Stage = Stage(
    f'{stage_name}Stage',
    StageName=stage_name,
    RestApiId=Ref(Civ6Notif_GW),
    DeploymentId=Ref(Civ6Notif_GW_Deployment)
)

Civ6Notif_Output_SNS = Output(
    "SNSTopicArn",
    Description="Arn of the SNS topic to subscribe to.",
    Value=Join("",
            [
                "arn:aws:sns:",
                Ref("AWS::Region"),
                ":",
                Ref("AWS::AccountId"),
                ":",
                GetAtt("Civ6NotifTopic", "TopicName")
            ]),
)

Civ6Notif_Output_GW = Output(
    "ApiGatewayEndpoint",
    Description="URL to give to Civ6's settings.",
    Value=Join("",
               [
                   "https://",
                   Ref("Civ6NotifGW"),
                   ".execute-api.",
                   Ref("AWS::Region"),
                   ".amazonaws.com/",
                   stage_name,
                   "/civ6"
               ]
            )
)

template.add_parameter(SendToSNS)
template.add_parameter(SendToDiscord)
template.add_parameter(DiscordWebhookURL)
template.add_resource(Civ6Notif_GW)
template.add_resource(Civ6Notif_SNS)
template.add_resource(Civ6Notif_Role)
template.add_resource(Civ6Notif_RolePolicy)
template.add_resource(Civ6Notif_Lambda)
template.add_resource(Civ6Notif_LambdaPermission)
template.add_resource(Civ6Notif_GW_Resource)
template.add_resource(Civ6Notif_PostMethod)
template.add_resource(Civ6Notif_GW_Stage)
template.add_resource(Civ6Notif_GW_Deployment)
template.add_output(Civ6Notif_Output_SNS)
template.add_output(Civ6Notif_Output_GW)


cf_path = Path(__file__).parent.joinpath("cloudformation").joinpath(Path(__file__).stem + ".yaml")
with open(cf_path, "w") as fh:
    fh.write(template.to_yaml())

cf_path = Path(__file__).parent.joinpath("cloudformation").joinpath(Path(__file__).stem + ".json")
with open(cf_path, "w") as fh:
    fh.write(template.to_json())
