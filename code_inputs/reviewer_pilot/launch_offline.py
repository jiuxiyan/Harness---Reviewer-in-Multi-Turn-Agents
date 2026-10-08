"""Parent launcher: no upstream imports. Child gets a private, secret-free environment."""
import json,os,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
mode=sys.argv[1] if len(sys.argv)>1 else 'import'
for p in ['private_home','private_xdg','private_cache','private_hf','results']:(R/p).mkdir(exist_ok=True)
env={'PATH':str(R/'.venv/bin')+':/usr/bin:/bin','HOME':str(R/'private_home'),'XDG_CONFIG_HOME':str(R/'private_xdg'),'XDG_CACHE_HOME':str(R/'private_cache'),'HF_HOME':str(R/'private_hf'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','TAU2_DATA_DIR':str(R/'upstream/data'),'PYTHON_DOTENV_DISABLED':'1','LITELLM_MODE':'PRODUCTION','LITELLM_LOCAL_MODEL_COST_MAP':'true','LITELLM_DISABLE_LAZY_LOADING':'false','HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false','PYTHONHASHSEED':'0'}
cmd=[str(R/'.venv/bin/python'),'-I',str(R/'backend_worker.py'),*sys.argv[1:]]
result=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
print(result.stdout)
if result.stderr:print(result.stderr,file=sys.stderr)
sys.exit(result.returncode)
