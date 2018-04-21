# from __future__ import print_function

import boto3
import json
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

    return instance_id_list


def wakeup_instances(cluster_name, scale_instances_count, scale_containers_count):

    all_id_list = get_ec2_instances_id(cluster_name)
    containers_num = int(scale_containers_count)

    print ('  Ready to power on %s instance in %s environment' % (scale_instances_count,cluster_name))

    ec2 = boto3.client("ec2",region_name = 'ap-southeast-1')
    response = ec2.describe_instance_status(InstanceIds=all_id_list)

    if len(response['InstanceStatuses']) == len(all_id_list) :
        execute_autoscaling_policy(cluster_name)
    else :
        running_ids=[]
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

    num = 4

    scale_per = 25.0

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

    print(total_count)
    print(running_ids)
    print(running_count)

    # scale_instances_count = int(running_count*int(scale_per/100))-int(running_count)

    scale_instances_count = int((total_count)*((float(running_count)/float(total_count))+(scale_per/100.0)))-int(running_count)

    scale_containers_count = scale_instances_count*int(num)
        

    print(cluster_name)
    print(scale_containers_count)
    print(scale_instances_count)
    
    wakeup_instances(cluster_name, scale_instances_count, scale_containers_count)




