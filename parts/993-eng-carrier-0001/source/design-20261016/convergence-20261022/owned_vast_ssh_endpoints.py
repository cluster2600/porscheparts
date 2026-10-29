"""Read the approved Vast wrapper's direct/proxy metadata for one owned lease."""
import re


def owned_ssh_endpoints(response, instance_id):
    if not isinstance(response,dict)or response.get('instance_id')!=instance_id:
        raise ValueError('SSH endpoint metadata does not identify the owned instance')
    if not all(key in response for key in ('direct','proxy')):
        raise ValueError('Approved wrapper direct/proxy endpoint schema required')
    result=[]
    for key in ('direct','proxy'):
        endpoint=response[key]
        if endpoint is None:continue
        if not isinstance(endpoint,dict):raise ValueError('Invalid endpoint record')
        host=endpoint.get('host');port=endpoint.get('port')
        if host is None or port is None:continue
        if not isinstance(host,str)or not re.fullmatch(r'[A-Za-z0-9.-]+',host)or type(port)is not int or not 0<port<65536:
            raise ValueError('Invalid SSH host or port metadata')
        result.append(dict(host=host,port=port,source=endpoint.get('source',key)))
    return result
