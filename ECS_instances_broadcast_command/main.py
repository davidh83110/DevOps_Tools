import boto3
import os
import paramiko 
import re


def find_ecs_instance_id(cluster_name):

    instance_arn_list=[]
    instance_id_list=[]

    ecs = boto3.client("ecs",region_name = 'ap-southeast-1')
    response_ecs = ecs.list_container_instances(cluster=cluster_name)

    for arn in response_ecs['containerInstanceArns']:
        instances_arn = arn.split('/')
        instance_arn_list.append(instances_arn[1]) 

    response = ecs.describe_container_instances(cluster=cluster_name,containerInstances=instance_arn_list)

    for ec2_id in response['containerInstances']:
        instance_id_list.append(ec2_id['ec2InstanceId'])

    print("Instance ID List")
    print(instance_id_list)
    return instance_id_list


def find_ecs_instance_ip(cluster_name):
    
    instance_ip_list=[]

    instance_id_list = find_ecs_instance_id(cluster_name)

    for ec2_id in instance_id_list:
        ec2 = boto3.resource('ec2')
        
        instance = ec2.Instance(ec2_id)
        privateIp = instance.private_ip_address
        instance_ip_list.append(privateIp)
        
    print("Instance IP List")
    print(instance_ip_list)
    return instance_ip_list


def broadcast_command(cluster_name, command):

    count = 0

    instance_ip_list = find_ecs_instance_ip(cluster_name)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print('Connected, start command....')

    for ip in instance_ip_list:
        print(ip)
        try:
            ssh.connect(ip, username="ec2-user", timeout=10)
            stdin,stdout,stderr = ssh.exec_command(command)
            stdout=stdout.readlines()
            for line in stdout:
                print(line)
            print('------------')
            ssh.close()
        except:
            count += 1
            print(count)
            print('timeout / stopped / Authorized Fail \n------------')
    print('end')


if __name__ == '__main__':
    cluster_name = 'CLUSTER_NAME'
    command = 'cat /var/log/system.log | grep "error" \n'

    broadcast_command(cluster_name, command)

