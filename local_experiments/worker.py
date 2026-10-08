"""Private subprocess entry point. Invoked by the public CLI with a minimal env."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_experiments.config import load
from local_experiments.storage import Store,RunFailure,write_json
from local_experiments.provider import Client,live_client

def main():
 config_path,mode,output=sys.argv[1:]
 config=load(config_path)
 os.umask(0o077)
 store=Store(output,config,mode)
 try:
  # Build the explicit client before imports. No credentials are loaded in dry-run.
  if mode=='dry-run':
   from local_experiments.mock import MockTransport
   client=Client(config,store,MockTransport(),{r:'mock-'+r for r in ('actor','reviewer','user')})
  elif mode=='live':
   client=live_client(config,store)
   # Upstream never receives the provider credential; our transport alone owns it.
   os.environ.pop('MODEL_API_KEY',None)
  else: raise RunFailure('invalid_mode')
  from local_experiments.provenance import verify_upstream
  verify_upstream()
  pilot=ROOT/'code_inputs/reviewer_pilot'
  sys.path.insert(0,str(pilot))
  if mode=='dry-run':
   import no_api_guard as guard
  sys.path.insert(0,str(pilot/'upstream/src'))
  from loguru import logger
  logger.remove()
  import tau2
  if mode=='dry-run': guard.finish_upstream_guards()
  # Never delegate generation/evaluation to the benchmark's default API stack.
  def denied(*args,**kwargs): raise RunFailure('unsupported_native_model_path')
  for name,module in list(sys.modules.items()):
   if name.startswith('tau2.') and hasattr(module,'generate'): module.generate=denied
  from local_experiments.engine import run
  store.save('capabilities.json',{'official_domain':'telecom','scope':'single assistant READ intervention; text half-duplex; exposed development tasks','supported_arms':['B_bare','B','A','P0','P','R','C'],'unsupported_arms':['S'],'supported_stages':['wire-smoke','natural-pilot'],'confirmatory':False,'provider_acceptance_measured':False,'formal_model_experiments':0})
  run(config,store,client)
  return 0
 except BaseException as exc:
  status=str(exc) if isinstance(exc,RunFailure) else ('user_interrupted' if isinstance(exc,KeyboardInterrupt) else 'implementation_error')
  # Do not expose arbitrary provider errors, request headers, endpoint, or text.
  if not (store.root/'status.json').exists():
   write_json(store.root/'status.json',{'status':status,'error_type':type(exc).__name__,'evidence_kind':store.evidence,'real_model_calls':0 if mode=='dry-run' else getattr(locals().get('client'),'calls',0)})
  print(status,file=sys.stderr)
  return 2

if __name__=='__main__': raise SystemExit(main())
