import os
import copy, uuid, time, json
import requests
from typing import Any, Optional
from .simpleparser import load_app, Demo, JugsawObject, adt2ir, ir2adt, py2adt, JugsawCall
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

    ### Examples
    Please check :func:`~jugsaw.request_app` for an example.
    """
    def __init__(self,
            endpoint:str = "http://localhost:8088/",
            localurl:bool = False,
            project:str = "unspecified",
            appname:str = "unspecified",
            version:str = "latest"):
        self.endpoint = endpoint
        self.localurl = localurl
        self.project = project
        self.appname = appname
        self.version = version

class LazyReturn(object):
    def __init__(self, context, job_id, demo_result):
        self.context = context
        self.job_id = job_id
        self.demo_result = demo_result

    def __call__(self):
        return fetch(self.context, self.job_id, self.demo_result)

def request_app_data(context:ClientContext, appname:str):
    context = copy.deepcopy(context)
    context.appname = appname
    r = new_request_demos(context)
    name, demos, tt = load_app(r.text)
    return (name, demos, tt, context)

def call(context:ClientContext, demo:Demo, *args, **kwargs):
    args_adt = JugsawObject("unspecified", [py2adt(arg, demo_arg) for (arg, demo_arg) in zip(args, demo.fcall.args)])
    kwargs_dict = demo.fcall.kwargs.copy()
    for k, v in kwargs.items():
        kwargs_dict[k] = py2adt(v, demo.fcall.kwargs[k])
    kwargs_adt = JugsawObject("unspecified", list(kwargs_dict.values()))
    assert len(args_adt.fields) == len(demo.fcall.args)
    assert len(kwargs_adt.fields) == len(demo.fcall.kwargs)
    fcall = JugsawCall(demo.fcall.fname, args_adt, kwargs_adt)
    job_id = str(uuid.uuid4())
    safe_request(lambda : new_request_job(context, job_id, fcall, maxtime=60.0, created_by="jugsaw"))
    return LazyReturn(context, job_id, demo.result)

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

def fetch(context:ClientContext, job_id:str, demo_result):
    ret = safe_request(lambda : new_request_fetch(context, job_id))
    return ir2adt(str(ret.text))

def healthz(context:ClientContext):
    path = f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/healthz"
    return json.read(requests.get(urljoin(context.endpoint, path)).body)


def new_request_job(context:ClientContext, job_id:str, fcall:JugsawCall, maxtime=10.0, created_by="jugsaw"):
    # create a job
    jobspec = JugsawObject("Jugsaw.JobSpec", [job_id, round(time.time()), created_by,
        maxtime, fcall.fname, fcall.args, fcall.kwargs])
    ir = adt2ir(jobspec)
    print(ir)
    # NOTE: UGLY!
    # create a cloud event
    header = {"Content-Type" : "application/json",
            "ce-id":str(uuid.uuid4()), "ce-type":"any", "ce-source":"python",
            "ce-specversion":"1.0"
        }
    data = json.dumps(ir)
    method, body = ("POST", urljoin(context.endpoint, f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/func/{fcall.fname}"))
    return requests.request(method, body, headers=header, data=data)

def new_request_healthz(context:ClientContext):
    method, body = ("GET", urljoin(context.endpoint, 
        f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/healthz"
    ))
    return requests.request(method, body)

def new_request_demos(context:ClientContext):
    method, body = ("GET", urljoin(context.endpoint,
        f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/func"
    ))
    return requests.request(method, body)

def new_request_fetch(context:ClientContext, job_id:str):
    method, body = ("POST", urljoin(context.endpoint,
        f"v1/job/{job_id}/result"
        ))
    header, data = {"Content-Type": "application/json"}, json.dumps({'job_id':job_id})
    return requests.request(method, body, headers=header, data=data)

def new_request_api(context:ClientContext, fcall:JugsawCall, lang:str):
    ir = adt2ir(JugsawObject("unspecified", [context.endpoint, fcall]))
    method, body = ("GET", urljoin(context.endpoint,
        f"v1/proj/{context.project}/app/{context.appname}/ver/{context.version}/func/{fcall.fname}/api/{lang}"
        ), {"Content-Type": "application/json"}, ir)
    return requests.request(method, body)
