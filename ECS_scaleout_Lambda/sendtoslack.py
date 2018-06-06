from urllib2 import Request, urlopen, URLError, HTTPError
import json

def send2slack(cluster_name, value, color):

    url = 'https://hooks.slack.com/services/T024JSFJH/B46PU833L/I7hLeeeee'

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
                        "title": "Status",
                        "value": value,
                        "short": "true"
                    }
                ],
                "color": color
            }
        ]
    }
    
    req = Request(url, json.dumps(slack_msg))
    response = urlopen(req)
    response.read()
    print 'send to slack sucessfully'
