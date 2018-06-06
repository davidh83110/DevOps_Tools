import boto3
import json
import logging
import time, datetime
from urllib2 import Request, urlopen, URLError, HTTPError
from sendtoslack import send2slack
from constant import Constant

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ecs = boto3.client("ecs",region_name = 'ap-southeast-1')
ec2 = boto3.client("ec2",region_name = 'ap-southeast-1')

def cool_down_check(cluster_name, all_id_list):

    _describe_ecs = ecs.describe_services(
        cluster = cluster_name,
        services = [
            cluster_name
        ]
    )

    _pending_count = _describe_ecs['services'][0]['pending_count']
    _desired_count = _describe_ecs['services'][0]['desired_count']
    _running_count = _describe_ecs['services'][0]['running_count']

    _init_instance_count = ec2.describe_instance_status(Filters=[
            {
                'Name': 'instance-status.status',
                'Values': [
                    'initializing',
                ]
            },
        ],
        InstanceIds=all_id_list)

    if _desired_count == _running_count and _pending_count == 0 and _init_instance_count['InstanceStatuses'] == []:
        return False, _running_count
    else:
        return True, True

def after_scale_to_slack(cluster_name, elements_to_slack):
    
    ### elements_to_slack elements
    # [0] running_count
    # [1] scale_instances_count
    # [2] running_task_count
    # [3] scale_containers_count 
    
    _slack_before_scale_instance_count = int(elements_to_slack[0])
    _slack_after_scale_instance_count = int(elements_to_slack[0])+int(elements_to_slack[1])
    _slack_before_scale_task_count = elements_to_slack[2]
    _slack_after_scale_task_count = elements_to_slack[3]

    value = "Instances increased from %s to %s\nTasks increased from %s to %s" % (_slack_before_scale_instance_count, _slack_after_scale_instance_count, _slack_before_scale_task_count, _slack_after_scale_task_count)
    color = "#36a64f" ## green

    send2slack(cluster_name, value, color)
    return 0

def before_scale_to_slack(cluster_name):
    value = "Starting scale out"
    color = "#F35A00" ## red

    send2slack(cluster_name, value, color)
    return 0

def execute_autoscaling_policy(cluster_name):
    print ('  Starting execute auto scaling %s policy' % cluster_name)
    return 0

def update_ecs_service(cluster_name, containers_num):
    time.sleep( Constant.after_scale_instance_sleep_time ) ## waiting for instances ready
    print ('  Start to update %s environment container number' % cluster_name)
    print ('  New containers number is %d' % containers_num)

    response = ecs.update_service(cluster=cluster_name,service=cluster_name,desiredCount=int(containers_num))
    return 0

def get_ec2_instances_id(cluster_name):
    instance_arn_list=[]
    instance_id_list=[]

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

    response = ec2.describe_instance_status(InstanceIds=all_id_list)
    
    running_ids = []

    if len(response['InstanceStatuses']) == len(all_id_list) :
        execute_autoscaling_policy(cluster_name)
    else :
        for ids in response['InstanceStatuses']:
            running_ids.append(ids['InstanceId'])

    stopping_ids = list(set(all_id_list).difference(set(running_ids)))

    if scale_instances_count == 0 and stopping_ids == []:
        pass
    else:
        wakeup_list = []
        for wakeup_count in range(scale_instances_count):
            wakeup_list.append(stopping_ids[wakeup_count-1])

        print wakeup_list
        ec2.start_instances(InstanceIds=wakeup_list)

    print ('  Ready to update %s desired container in %s environment' % (scale_containers_count,cluster_name))
    update_ecs_service(cluster_name, containers_num)
    return 0


def lambda_handler(event, context):

    ## handle data from SNS
    raw_message = json.loads(event['Records'][0]['Sns']['Message'])
    elb_name = raw_message['Trigger']['Dimensions'][0]['value']

    raw_cluster_name = elb_name.split('-')

    num = Constant.num
    scale_per = Constant.scale_per

    cluster_name = "-".join(raw_cluster_name[0:4]).split('/')[0]

    cluster_elb_list = ['openresty', 'nginx']
    if raw_cluster_name[0] in cluster_elb_list :
        ## openresty and nginx using ELB, 1 instance contain 1 container
        num = 1
        ## ELB should be thread [0:3], or cannot get correct cluster name
        cluster_name = "-".join(raw_cluster_name[0:3]).split('/')[0]    

    all_id_list = get_ec2_instances_id(cluster_name)
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
    _now_running_ins_per = float(running_count)/float(total_count)
    _can_be_start_ins_count = float(total_count) - float(running_count)
    if _can_be_start_ins_count == 0:
        scale_instances_count = 0
    else:
        scale_instances_count = int((total_count)*((_now_running_ins_per)+(scale_per/100.0)))-int(running_count)
        if scale_instances_count > _can_be_start_ins_count:
            scale_instances_count = int(_can_be_start_ins_count)

    scale_containers_count = (scale_instances_count+running_count)*int(num)
        

    print('cluster: ', cluster_name)
    print('scale_containers_count: ', scale_containers_count)
    print('scale_instances_count: ', scale_instances_count)
    

    cool_down, running_task_count = cool_down_check(cluster_name, all_id_list)
    

    if cool_down == False:
        
        before_scale_to_slack(cluster_name)
    
        wakeup_instances(cluster_name, scale_instances_count, scale_containers_count)

        elements_to_slack = [running_count, scale_instances_count, running_task_count, scale_containers_count]
    
        after_scale_to_slack(cluster_name, elements_to_slack)
    
    else:
        print "task still starting"

    return 0




