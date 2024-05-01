import uvloop

from .pn_app import createApp

# To use uvloop as event loop for panel
uvloop.install()


# Fill out with new models
_models = [
    #  [url, title, model]
    ["app", "App", createApp],
]

titles = {m[0]: m[1] for m in _models}
serving = {f"/panel/{m[0]}": m[2] for m in _models}