"""Write new metadata compactly without changing CORE or global JSON behavior."""
import json
from types import SimpleNamespace


def dumps(value,**kwargs):
    kwargs.pop('indent',None)
    kwargs['separators']=(',',':')
    kwargs['allow_nan']=False
    return json.dumps(value,**kwargs)


def install(core):
    if core.json is not json:raise ValueError('CORE JSON binding was already replaced')
    core.json=SimpleNamespace(loads=json.loads,dumps=dumps)
