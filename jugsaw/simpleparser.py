import json
from collections import OrderedDict
import numpy as np
import enum, pdb

class JugsawCall(object):
    def __init__(self, fname:str, args, kwargs):
        self.fname = fname
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        args = ", ".join([f"{repr(val)}" for val in self.args.fields])
        kwargs = ", ".join([f"{repr(val)}" for val in self.kwargs.fields])
        return f"{self.fname}({args}; {kwargs})"

    def __eq__(self, target):
        # NOTE: we do not need to check fields as long as their types are the same
        return isinstance(target, JugsawCall) and target.fname == self.fname and all([x==y for x, y in zip(target.args, self.args)]) and all([x==y for x, y in zip(target.kwargs, self.kwargs)])

    __repr__ = __str__

class JDataType(object):
    def __init__(self, name:str, fieldnames:list, fieldtypes:list):
        self.name = name
        self.fieldnames = fieldnames
        self.fieldtypes = fieldtypes

class TypeTable(object):
    def __init__(self, defs:OrderedDict={}):
        self.defs = defs

class Call(object):
    def __init__(self, fname, args, kwargs):
        self.fname = fname
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        args = ', '.join([repr(arg) for arg in self.args])
        kwargs = ', '.join([f'{k} = {repr(self.kwargs[k])}' for k in self.kwargs])
        return f"{self.fname}({args}, {kwargs})"

class Demo(object):
    def __init__(self, fcall, result, meta):
        self.fcall = fcall
        self.result = result
        self.meta = meta

    def __str__(self):
        return f"{self.fcall} = {repr(self.result)}"

def load_app(js):
    obj, tt = js["app"], js["typespec"]
    ############ load app
    name, method_names, method_demos = obj["name"], obj["method_names"], obj["method_demos"]
    demos = OrderedDict()
    for fname in method_names:
        demo = method_demos[fname]
        fcall, result, meta = demo["fcall"], demo["result"], demo["meta"]
        jf = Call(fname, fcall["args"], fcall["kwargs"])
        demos[fname] = Demo(jf, result, meta)
    return (name, demos, tt)

def load_typetable(ast):
    #for obj in ast
    types, typedefs = ast.fields
    defs = makedict(typedefs)
    for type in typedefs:
        elem = defs[type]
        name, fieldnames, fieldtypes = elem.fields
        defs[type] = JDataType(name, fieldnames, fieldtypes)
    return TypeTable(defs)
