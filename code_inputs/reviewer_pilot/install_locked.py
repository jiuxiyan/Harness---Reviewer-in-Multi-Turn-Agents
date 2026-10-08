"""Approved isolated installation of the unchanged official core lock; wheels only."""
import hashlib,json,os,pathlib,subprocess,sys,time,tomllib,urllib.parse,shutil
ROOT=pathlib.Path(__file__).resolve().parent
UP=ROOT/'upstream'
lock=tomllib.loads((UP/'uv.lock').read_text())
for package in lock['package']:
 source=package['source']
 if package['name']=='tau2': assert source=={'editable':'.'}
 else: assert source=={'registry':'https://pypi.org/simple'}, (package['name'],source)
private=ROOT/'private_home';private.mkdir(exist_ok=True)
xdg=ROOT/'private_xdg';xdg.mkdir(exist_ok=True)
uv_path=shutil.which('uv')
if not uv_path: raise SystemExit('Install uv from its official source and put it on PATH first.')
uv=pathlib.Path(uv_path)
python=pathlib.Path(sys.executable)
assert uv.is_file() and python.is_file()
env={'PATH':str(uv.parent)+':/usr/bin:/bin','HOME':str(private),'XDG_CONFIG_HOME':str(xdg),'XDG_CACHE_HOME':str(ROOT/'.cache'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8','UV_PROJECT_ENVIRONMENT':str(ROOT/'.venv'),'UV_CACHE_DIR':str(ROOT/'.uv-cache'),'UV_PYTHON_DOWNLOADS':'never','UV_NO_CONFIG':'true'}
# Preserve only the platform's existing noncredentialed installation routing.
for key in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:
 if key in os.environ:
  parsed=urllib.parse.urlparse(os.environ[key]);assert not (parsed.username or parsed.password or parsed.query or parsed.fragment)
  env[key]=os.environ[key]
for key in ['NO_PROXY','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE']:
 if key in os.environ:env[key]=os.environ[key]
cmd=[str(uv),'--no-config','sync','--frozen','--no-dev','--no-default-groups','--no-install-project','--no-build','--no-python-downloads','--python',str(python)]
gap=len(sys.argv)>1 and sys.argv[1]=='gap'
if gap:cmd=[str(uv),'--no-config','pip','install','--python',str(ROOT/'.venv/bin/python'),'--no-deps','--require-hashes','--no-build','-r',str(ROOT/'import_gap_requirements.txt')]
output_prefix='install_gap' if gap else 'install'
before={p:hashlib.sha256((UP/p).read_bytes()).hexdigest() for p in ['pyproject.toml','uv.lock']}
start=time.time()
with (ROOT/(output_prefix+'_stdout.txt')).open('w') as out:
 result=subprocess.run(cmd,cwd=UP,env=env,stdout=out,stderr=subprocess.STDOUT)
after={p:hashlib.sha256((UP/p).read_bytes()).hexdigest() for p in before}
record={'command':cmd,'environment_keys_only':sorted(env),'exit_code':result.returncode,'duration_seconds':time.time()-start,'hashes_before':before,'hashes_after':after,'lock_unchanged':before==after,'venv':str(ROOT/'.venv'),'registry':'https://pypi.org/simple','model_calls_authorized':False}
(ROOT/(output_prefix+'_result.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
print((ROOT/(output_prefix+'_stdout.txt')).read_text()[-5000:])
assert before==after
sys.exit(result.returncode)
