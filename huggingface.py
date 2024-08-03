import json, requests, time, uuid
from urllib.parse import urljoin

class ClientContext(object):
    def __init__(self,
            endpoint:str,
            token_access:str,
            ):
        self.endpoint = endpoint
        self.token_access = token_access


def jsoncall(context:ClientContext, payload, job_id:str=str(uuid.uuid4()), maxtime=10.0):
    project = "unspecified"
    appname = "helloworld"
    version = "latest"
    # create a job
    jobspec = {
            "id": job_id,
            "created_at" : time.time(),
            "created_by" : "jugsaw",
            "maxtime" : maxtime,
            "fcall" : payload
            }
    # create a cloud event
    headers = {"Content-Type" : "application/json",
            "ce-id":str(uuid.uuid4()), "ce-type":"any", "ce-source":"python",
            "ce-specversion":"1.0",
            "Authorization": f"Bearer {context.token_access}"
        }
    data = json.dumps(jobspec)
    method, body = ("POST", urljoin(context.endpoint, f"v1/proj/{project}/app/{appname}/ver/{version}/func/{payload['fname']}"))
    res = requests.request(method, body, headers=headers, data=data).json()
    if 'job_id' in res:
        return job_id
    elif 'error' in res:
        raise Exception(f"Got error: {res['error']}")
    else:
        raise Exception(f"Result bad format: {res}")

def fetch(context:ClientContext, job_id:str):
    method, body = ("POST", urljoin(context.endpoint,
        f"v1/job/{job_id}/result"
        ))
    header = {"Content-Type": "application/json", "Authorization": f"Bearer {context.token_access}"}
    data = json.dumps({'job_id':job_id})
    return requests.request(method, body, headers=header, data=data).json()

token_access = "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"
context = ClientContext(endpoint="https://giggleliu-omeinsumcontractionorders-jl.hf.space", token_access=token_access)
payload = {
    "fname": "optimize_contraction_order",
    "args" : [[[1, 2], [2, 3], [3, 4]], [1, 4], {"1": 2, "2": 3, "3": 4, "4" : 5}, {}],
    "kwargs" : {}
}

job_id = jsoncall(context, payload)
result = fetch(context, job_id)
print(result)
