import json
import logging
import gzip
import zlib
import base64
import boto3
from urllib2 import Request, urlopen, URLError, HTTPError
import time
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

url = 'https://WEB_HOOK_URL'

def execute_result_verify(command_id, cluster_name):

    client_ssm = boto3.client('ssm', region_name = 'ap-southeast-1')
    
    response_ssm = client_ssm.list_command_invocations(CommandId=command_id, Details=True)

    print response_ssm

    instance_count = len(re.findall('\'Output\'', str(response_ssm)))
    print "executed instance count: ", instance_count

    executed_result_list = []

    try:
        for i in range(instance_count):
            execute_result = response_ssm['CommandInvocations'][i]['CommandPlugins'][0]['Output']
            print execute_result
            executed_result_list.append(execute_result)
        print "reload successfully"
        execute_result = "Reload Successfully"
    except:
        print "False, reload failed"
        execute_result = "Reload Failed"

    send2slack(cluster_name, executed_result_list)
    

def send2slack(cluster_name, executed_result_list):
    
    slack_msg = {
        "attachments": [
            {
                "text": "*Nginx Reload - From Lambda*",
                "fields": [
                    {
                        "title": cluster_name,
                        "value": ''.join(executed_result_list),
                        "short": "false"
                    }
                ],
                "color": "#3AA3E3",
                "footer": "Lambda",
                "footer_icon": "https://blog.atj.me/assets/aws-lambda.png",
                "ts": int(time.time())
            }
        ]
    }
    
    req = Request(url, json.dumps(slack_msg))
    response = urlopen(req)
    response.read()
    print 'send to slack sucessfully'
    


def reload_nginx(cluster_name):
    application = cluster_name.split('-')[0]
    
    client = boto3.client('ssm') 
    response = client.send_command(
        Targets=[
            {
                'Key': 'tag:Name',
                'Values': [
                    cluster_name+' - ecsInstance',
                ]
            },
        ],
        DocumentName='AWS-RunShellScript',
        TimeoutSeconds=600,
        Parameters={
            'commands': [
                'docker exec $(docker ps | grep ' + application +' | awk \'{print $1}\') ' + application +' -s reload',
            ]
        }
    )

    print response

    command_id = response['Command']['CommandId']
    print "command id:", command_id

    print "waiting for executing..."
    time.sleep(10)
    
    execute_result_verify(command_id, cluster_name)
    return response, command_id
    

def change_type(out_raw_message):
    
    if str(type(out_raw_message)) == "<type \'unicode\'>":
        raw_message = json.loads(out_raw_message)
        print "This is from SNS"
    else:
        raw_message = out_raw_message
        print "This is from Cloudwatch Event"
    
    return raw_message


def lambda_handler(event, context):
    
    print event
    out_raw_message = event['Records'][0]['Sns']['Message']
    
    raw_message = change_type(out_raw_message)

    elb_name = raw_message['Trigger']['Dimensions'][0]['value']

    raw_cluster_name = elb_name.split('-')
    cluster_name = "-".join(raw_cluster_name[1:4]).split('/')[0]
    print cluster_name

    reload_nginx(cluster_name)

