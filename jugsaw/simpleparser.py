import lark, json
from collections import OrderedDict
import numpy as np
import enum, pdb

####################### Object
# the JSON grammar in EBNF format
# dict is not allowed
class JugsawObject(object):
    def __init__(self, typename:str, fields:list):
        self.typename = typename
        self.fields = fields

    def __str__(self):
        fields = ", ".join([f"{repr(val)}" for val in self.fields])
        return f"{self.typename}({fields})"

    def __eq__(self, target):
        # NOTE: we do not need to check fields as long as their types are the same
        return isinstance(target, JugsawObject) and target.typename == self.typename and all([x==y for x, y in zip(target.fields, self.fields)])

    __repr__ = __str__


class JugsawList(object):
    def __init__(self, storage:list):
        self.storage = storage

    def __str__(self):
        return str(self.storage)

    def __eq__(self, target):
        # NOTE: we do not need to check fields as long as their types are the same
        return isinstance(target, JugsawList) and all([x==y for x, y in zip(target.storage, self.storage)])

    __repr__ = __str__

class JugsawCall(object):
    def __init__(self, fname:str, args:JugsawObject, kwargs:JugsawObject):
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


# Convert the grammar into a JugsawIR tree.
class JugsawTransformer(lark.Transformer):
    def expr(self, items):
        return items[0]
    def untyped(self, items):
        return JugsawObject("unspecified", items)
    def object(self, items):
        return JugsawObject(items[0], items[1:])
    def call(self, items):
        return JugsawCall(items[0], items[1], items[2])
    def list(self, items):
        return JugsawList(items)
    # primitive types
    def string(self, items):
        return json.loads(items[0])
    def number(self, items):
        return float(items[0])
    def true(self, items):
        return True
    def false(self, items):
        return False
    def null(self, items):
        return None

class JDataType(object):
    def __init__(self, name:str, fieldnames:list, fieldtypes:list):
        self.name = name
        self.fieldnames = fieldnames
        self.fieldtypes = fieldtypes

class TypeTable(object):
    def __init__(self, defs:OrderedDict={}):
        self.defs = defs

# constants
# parse an object
jp = lark.Lark.open("jugsawir.lark", rel_to=__file__, start='expr', parser='lalr', transformer=JugsawTransformer())

def ir2adt(ir:str):
    return jp.parse(ir)

############################ adt to py
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

def load_app(s:str):
    obj, typesadt = ir2adt(s).storage
    tt = load_typetable(typesadt)
    ############ load app
    name, method_names, _method_demos = obj.fields
    method_demos = makedict(_method_demos)
    demos = OrderedDict()
    for fname in method_names.fields[1].storage:
        (fcall, result, meta) = method_demos[fname].fields
        jf = Call(fname, fcall.args.fields, OrderedDict(zip(aslist(tt.defs[fcall.kwargs.typename].fieldnames), fcall.kwargs.fields)))
        demos[fname] = Demo(jf, result, makedict(meta))
    return (name, demos, tt)

# showing demo python inputs
def adt2py(adt):
    if isinstance(adt, JugsawObject):
        return tuple([adt2py(x) for x in adt.fields])
    elif isinstance(adt, list):
        return [adt2py(x) for x in adt]
    elif isdirectrepresentable(adt):
        return adt
    else:
        raise Exception(f"{type(adt)} can not be parsed to python object!")

def aslist(obj):
    return obj.storage

def makedict(adt):
    pairs = aslist(adt.fields[0])
    return OrderedDict([(pair.fields[0], pair.fields[1]) for pair in pairs])

def load_typetable(ast:JugsawObject):
    #for obj in ast
    types, typedefs = ast.fields
    defs = makedict(typedefs)
    for type in defs:
        elem = defs[type]
        name, fieldnames, fieldtypes = elem.fields
        defs[type] = JDataType(name, fieldnames, fieldtypes)
    return TypeTable(defs)

# convert a Jugsaw tree to a dict
def isdirectrepresentable(obj):
    return (obj is None) or any([isinstance(obj, tp) for tp in (int, str, float, bool)])

def py2adt(obj, demo):
    if isinstance(obj, str) and isinstance(demo, JugsawObject) and demo.typename == "JugsawIR.JEnum":
        return JugsawObject("JugsawIR.JEnum", [demo.fields[0], obj, demo.fields[2]])
    elif isdirectrepresentable(obj):
        return obj
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict) or isinstance(obj, OrderedDict):
        eldemo = make_element_demo(aslist(demo.fields[0]))
        return JugsawObject("JugsawIR.JDict", [JugsawList([py2adt(item, eldemo) for item in obj.items()])])
    elif isinstance(obj, list):
        if isinstance(demo, JugsawList):
            eldemo = make_element_demo(demo.storage)
        else:
            eldemo = make_element_demo(aslist(demo.fields[1]))
        return JugsawObject("JusawIR.JArray", [JugsawList([len(obj)]), JugsawList([py2adt(x, eldemo) for x in obj])])
    elif isinstance(obj, np.ndarray):
        vec = np.reshape(obj, -1, order="F")
        eldemo = make_element_demo(aslist(demo.fields[1]))
        return JugsawObject("JugsawIR.JArray", [JugsawList(list(obj.shape)), JugsawList([py2adt(x, eldemo) for x in vec])])
    elif isinstance(obj, tuple):
        return JugsawObject("Core.Tuple", [py2adt(x, demox) for x, demox in zip(obj, demo.fields)])
    elif isinstance(obj, enum.Enum):
        return JugsawObject("JugsawIR.JEnum", [type(obj).__name__, obj.name, JugsawList([str(x.name) for x in type(obj)])])
    elif isinstance(obj, complex):
        return JugsawObject("Base.Complex", [obj.real, obj.imag])
    else:
        return JugsawObject(demo.typename, [getattr(obj, x) for x in obj.__dict__.keys()])

def make_element_demo(x:list):
    if len(x) > 0:
        return x[0]
    else:
        return None

###################### ADT to IR
def adt2ir(x):
    return json.dumps(_adt2ir(x))

def _adt2ir(x):
    if isinstance(x, JugsawObject):
        return make_object(x.typename, [_adt2ir(v) for v in x.fields])
    elif isinstance(x, JugsawCall):
        return make_call(x.fname, _adt2ir(x.args), _adt2ir(x.kwargs))
    elif isinstance(x, JugsawList):
        return ['list', *[_adt2ir(v) for v in x.storage]]
    elif isdirectrepresentable(x):
        return x
    else:
        raise Exception(f"type can not be casted to IR, got: {x} of type {type(x)}")

def make_object(T:str, fields:list):
    if T == 'unspecified':
        return ["untyped", *fields]
    else:
        return ["object", T, *fields]
def make_call(fname:str, args:JugsawObject, kwargs:JugsawObject):
    return ["call", fname, args, kwargs]

if __name__ == "__main__":
    import pdb
    res = jp.parse("""
            {"type" : "Jugsaw.People{Core.Int}", "fields" : [32]}
            """)
    print(res)
    assert res == JugsawObject("Jugsaw.People{Core.Int}", [32])
    res = jp.parse("""
            {"type":"Jugsaw.TP", "fields":[]}
            """)
    print(res)
    assert res == JugsawObject("Jugsaw.TP", [])
    with open("../../../jl/Jugsaw/test/testapp/demos.json", "r") as f:
        s = f.read()
    print(load_app(s))

    assert py2dict(3.0) == 3.0
    assert py2dict("3.0") == "3.0"
    assert py2dict({"x":3}) == {"fields": [["x"], [3]]}
    assert py2dict(2+5j) == {"fields": [2, 5]}
    assert py2dict(np.array([[1, 2, 3], [4, 5, 6]])) == {"fields": [[2, 3], [1, 4, 2, 5, 3, 6]]}
    class Color(enum.Enum):
        RED = 1
        GREEN = 2
        BLUE = 3
    assert py2dict([1, Color.RED]) == [1, {"fields":["Color", "RED", ["RED", "GREEN", "BLUE"]]}]
    
    obj = JugsawObject("Jugsaw.TP", [])
    assert py2dict(obj) == {"fields" : ["Jugsaw.TP", []]}
