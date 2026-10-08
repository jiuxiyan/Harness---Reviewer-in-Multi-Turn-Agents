"""Launch official code without inheriting credentials during offline runs."""
import os
from pathlib import Path
import subprocess
import sys
from .config import ROOT
from .storage import RunFailure

def launch(config_path,mode,output,recovery=None):
 pilot=ROOT/'code_inputs/reviewer_pilot'
 python=pilot/'.venv/bin/python'
 if not python.is_file(): raise RunFailure('Install pinned CPU dependencies using the documented setup commands')
 output=Path(output).resolve()
 if output.exists(): raise RunFailure('Output directory already exists; choose a fresh run directory')
 env={'PATH':str(python.parent)+':/usr/bin:/bin','HOME':str(output/'private/home'),
      'XDG_CONFIG_HOME':str(output/'private/xdg'),'XDG_CACHE_HOME':str(output/'private/cache'),
      'HF_HOME':str(output/'private/hf'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
      'TAU2_DATA_DIR':str(pilot/'upstream/data'),'PYTHON_DOTENV_DISABLED':'1',
      'LITELLM_MODE':'PRODUCTION','LITELLM_LOCAL_MODEL_COST_MAP':'true',
      'LITELLM_DISABLE_LAZY_LOADING':'false','HF_HUB_OFFLINE':'1',
      'HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false','PYTHONHASHSEED':'0',
      'PYTHONDONTWRITEBYTECODE':'1'}
 if mode=='live':
  # Explicit opt-in only. Preserve normal proxy/TLS routing; never disable checks.
  for key in ('MODEL_API_BASE_URL','MODEL_API_KEY','ACTOR_MODEL','REVIEWER_MODEL','USER_MODEL',
              'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy',
              'SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE'):
   if key in os.environ: env[key]=os.environ[key]
 return subprocess.run([str(python),'-I','-B',str(ROOT/'local_experiments/worker.py'),str(Path(config_path).resolve()),mode,str(output),*(list(map(str,recovery)) if recovery else [])],env=env,cwd=ROOT).returncode
