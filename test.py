import jugsaw

context = jugsaw.ClientContext(endpoint="http://0.0.0.0:8088")
app = jugsaw.request_app(context, "testapp")

res = app.greet("Jugsaw")
print(res())

res2 = jugsaw.jsoncall(context, {      
        "fname": "greet",
        "args": [   
            "Jugsaw"
        ],
        "kwargs": {}
    })
print(res2)
print(res2())

import pdb
pdb.set_trace()
