#!/usr/bin/env python3
"""Verify actual tool-call output, not just /health. No external API calls."""
import json
import urllib.request
body = {
 'model': 'nemotron-cad', 'messages': [{'role':'user','content':'Call record_check with status candidate. Do not answer in prose.'}],
 'tools': [{'type':'function','function':{'name':'record_check','description':'Record a check',
 'parameters':{'type':'object','properties':{'status':{'type':'string','enum':['candidate']}},'required':['status']}}}],
 'tool_choice':'required', 'max_tokens':1024, 'temperature':0}
r = urllib.request.Request('http://127.0.0.1:8002/v1/chat/completions',
                           data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
with urllib.request.urlopen(r, timeout=180) as response: data=json.load(response)
call = data['choices'][0]['message']['tool_calls'][0]['function']
assert call['name'] == 'record_check'
assert json.loads(call['arguments']) == {'status':'candidate'}
print(json.dumps({'status':'passed','check':'nemotron_tool_call'}))
