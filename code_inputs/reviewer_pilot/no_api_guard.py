"""Process-local fail-closed guards for offline preparation; not a kernel sandbox."""
import os
import pathlib
import socket
import sys
import threading
EVENTS=[]
EXPECTED=[]
TESTING=False
class GuardViolation(BaseException):
    pass

def deny(kind):
    def blocked(*args,**kwargs):
        row={'kind':kind}
        (EXPECTED if TESTING else EVENTS).append(row)
        raise GuardViolation(kind)
    return blocked

def audit(event,args):
    if event.startswith(('socket.connect','socket.getaddrinfo','socket.gethostby','socket.sendto','socket.sendmsg','subprocess.Popen','os.system','os.exec','os.posix_spawn','os.fork')):
        deny('audit:'+event)()
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        name=os.fsdecode(args[0])
        if pathlib.Path(name).name=='.env':deny('dotenv:file-read')()

def profile(frame,event,arg):
    if event!='call':return
    module=frame.f_globals.get('__name__','') or ''
    name=frame.f_code.co_name
    if module.startswith('litellm') and name in {'completion','acompletion','embedding','aembedding','text_completion','atext_completion','responses','aresponses','image_generation','aimage_generation'}:
        deny('model-profile:'+module+'.'+name)()
    if module.startswith('tau2.') and name in {'generate','generate_next_message','_generate_next_message'}:
        deny('model-profile:'+module+'.'+name)()
    if module.startswith('openai') and name in {'request','_load_client'}:
        deny('model-profile:'+module+'.'+name)()
    if module.startswith('dotenv') and name in {'find_dotenv','dotenv_values','_get_stream'}:
        deny('dotenv-profile:'+name)()

sys.addaudithook(audit)
sys.setprofile(profile)
threading.setprofile(profile)
socket.socket.connect=deny('socket.connect')
socket.socket.connect_ex=deny('socket.connect_ex')
socket.socket.sendto=deny('socket.sendto')
socket.socket.sendmsg=deny('socket.sendmsg')
socket.create_connection=deny('socket.create_connection')
socket.getaddrinfo=deny('socket.getaddrinfo')

# HTTP classes are kept intact, but their transport entrypoints fail closed.
import httpx
httpx.Client.send=deny('httpx.Client.send')
httpx.AsyncClient.send=deny('httpx.AsyncClient.send')
import requests
requests.Session.request=deny('requests.Session.request')
requests.Session.send=deny('requests.Session.send')
import dotenv
import dotenv.main
dotenv.find_dotenv=dotenv.main.find_dotenv=deny('dotenv.find_dotenv')
dotenv.dotenv_values=dotenv.main.dotenv_values=deny('dotenv.dotenv_values')
assert os.environ['PYTHON_DOTENV_DISABLED']=='1'
assert dotenv.load_dotenv() is False
import litellm
import litellm.main
litellm.telemetry=False
litellm.disable_hf_tokenizer_download=True
litellm.success_callback=[]
litellm.failure_callback=[]
for mod in [litellm,litellm.main]:
    for name in ['completion','acompletion','embedding','aembedding','text_completion','atext_completion','responses','aresponses','image_generation','aimage_generation']:
        if hasattr(mod,name) and callable(getattr(mod,name)):
            setattr(mod,name,deny('model:'+mod.__name__+'.'+name))
import openai
import openai._base_client
openai._base_client.SyncAPIClient.request=deny('openai.sync.request')
openai._base_client.AsyncAPIClient.request=deny('openai.async.request')
openai._load_client=deny('openai._load_client')

def finish_upstream_guards():
    # The profiler protected by-value aliases throughout import. Replace aliases too.
    for module_name,module in list(sys.modules.items()):
        if module_name.startswith('tau2.'):
            if hasattr(module,'generate') and callable(module.generate):
                module.generate=deny('model:'+module_name+'.generate')
    import tau2.config as config
    assert config.LLM_CACHE_ENABLED is False and config.USE_LANGFUSE is False

def negative_tests():
    global TESTING
    TESTING=True
    tests=[('model',lambda:litellm.completion(model='offline-denial-sentinel',messages=[])),('network',lambda:socket.create_connection(('example.invalid',443))),('dotenv',lambda:dotenv.find_dotenv())]
    rows=[]
    try:
        for name,fn in tests:
            try:fn()
            except GuardViolation:rows.append({'test':name,'blocked':True})
            else:raise AssertionError('Guard did not block '+name)
    finally:TESTING=False
    return rows
