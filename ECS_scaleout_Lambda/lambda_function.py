# from __future__ import print_function

import boto3
import json
import logging
import time, datetime
from urllib2 import Request, urlopen, URLError, HTTPError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def cold_down_check(cluster_name):
    ecs = boto3.client("ecs",region_name = 'ap-southeast-1')
    __describe_ecs = ecs.describe_services(
        cluster = cluster_name,
        services = [
            cluster_name
        ]
    )

    __pendingCount = __describe_ecs['services'][0]['pendingCount']
    __desiredCount = __describe_ecs['services'][0]['desiredCount']
    __runningCount = __describe_ecs['services'][0]['runningCount']

    if __desiredCount == __runningCount and __pendingCount == 0:
        return True, __runningCount
    else:
        return False
        

def send2slack(cluster_name, running_count, scale_instances_count, running_task_count, scale_containers_count):
    url = 'https://hooks.slack.com/services/WEBHOOKURLTOKEN'

    ## todo: add headers on post request
    headers = {
        'Content-type':'application/json'
    }
    
    slack_msg = {
        "attachments": [
            {
                "text": "ECS/SCALE-OUT - From Lambda",
                "fields": [
                    {
                        "title": "Project",
                        "value": cluster_name,
                        "short": "true"
                    },
                    {
                        "title": "Counts",
                        "value": "Instances increased from %s to %s\nTasks increased from %s to %s" % (running_count, int(running_count)+int(scale_instances_count), running_task_count, scale_containers_count),
                        "short": "true"
                    }
                ],
                "color": "#F35A00"
            }
        ]
    }
    
    req = Request(url, json.dumps(slack_msg))
    response = urlopen(req)
    response.read()
    print 'send to slack sucessfully'


def execute_autoscaling_policy(cluster_name):
    print ('  Starting execute auto scaling %s policy' % cluster_name)

def update_ecs_service(cluster_name, containers_num):
    time.sleep( 90 )
    print ('  Start to update %s environment container number' % cluster_name)
    print ('  New containers number is %d' % containers_num)
    ecs = boto3.client("ecs",region_name = 'ap-southeast-1')
    response = ecs.update_service(cluster=cluster_name,service=cluster_name,desiredCount=int(containers_num))

def get_ec2_instances_id(cluster_name):
    instance_arn_list=[]
    instance_id_list=[]

    ecs = boto3.client("ecs",region_name = 'ap-southeast-1')
    response = ecs.list_container_instances(cluster=cluster_name)

    for arn in response['containerInstanceArns']:
        instances_arn = arn.split('/')
        instance_arn_list.append(instances_arn[1]) 

    response = ecs.describe_container_instances(cluster=cluster_name,containerInstances=instance_arn_list)

    for ec2_id in response['containerInstances']:
        instance_id_list.append(ec2_id['ec2InstanceId'])
    print instance_id_list

    return instance_id_list


def wakeup_instances(cluster_name, scale_instances_count, scale_containers_count):

    all_id_list = get_ec2_instances_id(cluster_name)
    containers_num = int(scale_containers_count)

    print ('  Ready to power on %s instance in %s environment' % (scale_instances_count,cluster_name))

    ec2 = boto3.client("ec2",region_name = 'ap-southeast-1')
    response = ec2.describe_instance_status(InstanceIds=all_id_list)
    
    running_ids = []

    if len(response['InstanceStatuses']) == len(all_id_list) :
        execute_autoscaling_policy(cluster_name)
    else :
        for ids in response['InstanceStatuses']:
            running_ids.append(ids['InstanceId'])

    stopping_ids = list(set(all_id_list).difference(set(running_ids)))

    wakeup_list = []
    for wakeup_count in range(scale_instances_count):
        wakeup_list.append(stopping_ids[wakeup_count-1])

    print wakeup_list
    ec2.start_instances(InstanceIds=wakeup_list)

    print ('  Ready to update %s desired container in %s environment' % (scale_containers_count,cluster_name))
    update_ecs_service(cluster_name, containers_num)


def lambda_handler(event, context):

    raw_message = json.loads(event['Records'][0]['Sns']['Message'])
    elb_name = raw_message['Trigger']['Dimensions'][0]['value']

    raw_cluster_name = elb_name.split('-')

    ### CUSTOMIZE HERE
    num = 4
    scale_per = 25.0
    ###

    cluster_name = "-".join(raw_cluster_name[0:4]).split('/')[0]
    if raw_cluster_name[0] == 'openresty':
        num = 1
        cluster_name = "-".join(raw_cluster_name[0:3]).split('/')[0]    


    all_id_list = get_ec2_instances_id(cluster_name)
    ec2 = boto3.client("ec2",region_name = 'ap-southeast-1')
    response = ec2.describe_instance_status(InstanceIds=all_id_list)

    running_ids=[]
    for ids in response['InstanceStatuses']:
        running_ids.append(ids['InstanceId'])

    total_count = int(len(all_id_list))
    running_count = int(len(running_ids))
    task_running_count = int(running_count*num)

    print('total_instances_count: ', total_count)
    print('total_running_instances_count: ', running_count)
    print('total_task_count: ', task_running_count)


    ### (total_ins * ((running_ins/total_ins)+SCALE_PER/100)) - running_ins 
    scale_instances_count = int((total_count)*((float(running_count)/float(total_count))+(scale_per/100.0)))-int(running_count)

    scale_containers_count = scale_instances_count*int(num)
        

    print('cluster: ', cluster_name)
    print('scale_containers_count: ', scale_containers_count)
    print('scale_instances_count: ', scale_instances_count)
    
    cold_down = cold_down_check(cluster_name)[0]
    running_task_count = cold_down_check(cluster_name)[1]
    

    if cold_down == True:
    
        wakeup_instances(cluster_name, scale_instances_count, scale_containers_count)
    
        send2slack(cluster_name, running_count, scale_instances_count, running_task_count, scale_containers_count)
    
    else:
        print "task still starting"




