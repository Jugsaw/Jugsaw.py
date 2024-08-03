import jugsaw

token_access = "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"
headers = {"Authorization": f"Bearer {token_access}"}
context = jugsaw.ClientContext(endpoint="https://giggleliu-omeinsumcontractionorders-jl.hf.space", headers=headers)

app = jugsaw.request_app(context, "helloworld")

import pdb
pdb.set_trace()
lazyreturn = app.optimize_contraction_order([[1, 2], [2, 3]], [1, 3], {1:10, 2:10, 3:20}, {})
result = lazyreturn()   # fetch result
print(result)
