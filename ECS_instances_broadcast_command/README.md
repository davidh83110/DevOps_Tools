***AWS ECS instances broadcast command tool***

---

Environment: Python 3

Requirements:
```
aws_access_key_id
aws_secret_access_key
ssh key which can ssh instances you wanna execute broadcast command
Python3

pip3 install boto3
pip3 install os
pip3 install paramiko
pip3 install re 
```

Things this program do:
```
- Show all ECS instances ID
- Show all ECS instances ip
- Login to each instances and execute broadcast command
```

---

## License

[MIT](./LICENSE)

