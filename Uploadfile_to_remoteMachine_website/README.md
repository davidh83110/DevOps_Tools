***Upload file to remote Machines***

---

Environment: Python 3

Requirements:
```
ssh key which can ssh instances

pip3 install os
pip3 install flask
pip3 install werkzeug
```


Why doing this 
```
For someone who doesn't has the permsiion to access machines but need to upload files in corp. (PIC)

```


Things this program do:
```
- Launch website by flask 
- User upload file from broswer 
- POST to flask 
- Receive file from user's site to local 
- SCP target file to remote machine 
- Return a image to website 
```

***License***

[MIT](./LICENSE)
