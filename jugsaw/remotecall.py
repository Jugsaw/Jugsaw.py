import os
import copy, uuid, time, json
import requests
from typing import Any, Optional
from .simpleparser import load_app, Demo, JugsawCall
from urllib.parse import urljoin
import pdb

class ClientContext(object):
    """
    Client context for storing contextual information.

    ### Attributes
    * `endpoint = "http://localhost:8088/"` is the website serving the application.
    * `project = "unspecified"` is the project or user name.
    * `appname = "unspecified"` is the applicatoin name.
    * `version = "latest"` is the application version number.
    * `headers = {}` is the extra header included in the GET/POST requests.

    ### Examples
    Please check :func:`~jugsaw.request_app` for an example.
    """
    def __init__(self,
            endpoint:str = "http://localhost:8088/",
            localurl:bool = False,
            project:str = "unspecified",
            appname:str = "unspecified",
            version:str = "latest",
            headers:dict = {}):
        self.endpoint = endpoint
        self.localurl = localurl
        self.project = project
        self.appname = appname
        self.version = version
        self.headers = headers

class LazyReturn(object):
    def __init__(self, context, job_id):
        self.context = context
        self.job_id = job_id

    def __call__(self):
        return fetch(self.context, self.job_id)

    def __str__(self):
        return f"LazyReturn: job_id = {self.job_id}"

def request_app_data(context:ClientContext, appname:str):
    context = copy.deepcopy(context)
    context.appname = appname
    r = new_request_demos(context)
    name, demos, tt = load_app(r.json())
    return (name, demos, tt, context)

def call(context:ClientContext, demo:Demo, *args, **kwargs):
    fcall = JugsawCall(demo.fcall.fname, args, kwargs)
    return safe_request(lambda : new_request_job(context, fcall, maxtime=60.0, created_by="jugsaw"))

def safe_request(f):
    try:
        return f()
    except requests.exceptions.HTTPError:
        res = json.read(e.response.body)
        print(res.error)
        raise
    except:
        print("request error not handled!")
        raise

def fetch(context:ClientContext, job_id:str):
    ret = safe_request(lambda : new_request_fetch(context, job_id))
    return ret.json()

def healthz(context:ClientContext):
    path = f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/healthz"
    return json.read(requests.get(urljoin(context.endpoint, path), headers=context.headers).body)


def new_request_job(context:ClientContext, fcall:JugsawCall, job_id:str=str(uuid.uuid4()), maxtime=10.0, created_by="jugsaw"):
    payload = {
        "fname" : fcall.fname,
        "args" : fcall.args,
        "kwargs" : fcall.kwargs
    }
    return jsoncall(context, payload, job_id, maxtime, created_by)

def jsoncall(context:ClientContext, payload, job_id:str=str(uuid.uuid4()), maxtime=10.0, created_by="jugsaw"):
    # create a job
    jobspec = {
            "id": job_id,
            "created_at" : time.time(),
            "created_by" : created_by,
            "maxtime" : maxtime,
            "fcall" : payload
            }
    # create a cloud event
    headers = {"Content-Type" : "application/json",
            "ce-id":str(uuid.uuid4()), "ce-type":"any", "ce-source":"python",
            "ce-specversion":"1.0",
            **context.headers
        }
    data = json.dumps(jobspec)
    method, body = ("POST", urljoin(context.endpoint, f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/func/{payload['fname']}"))
    res = requests.request(method, body, headers=headers, data=data).json()
    if 'job_id' in res:
        return LazyReturn(context, job_id)
    elif 'error' in res:
        raise Exception(f"Got error: {res['error']}")
    else:
        raise Exception(f"Result bad format: {res}")

def new_request_healthz(context:ClientContext):
    method, body = ("GET", urljoin(context.endpoint, 
        f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/healthz"
    ))
    return requests.request(method, body, headers=context.headers)

def new_request_demos(context:ClientContext):
    method, body = ("GET", urljoin(context.endpoint,
        f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/func"
    ))
    return requests.request(method, body, headers=context.headers)

def new_request_fetch(context:ClientContext, job_id:str):
    method, body = ("POST", urljoin(context.endpoint,
        f"v1/job/{job_id}/result"
        ))
    header, data = {"Content-Type": "application/json", **context.headers}, json.dumps({'job_id':job_id})
    return requests.request(method, body, headers=header, data=data)
