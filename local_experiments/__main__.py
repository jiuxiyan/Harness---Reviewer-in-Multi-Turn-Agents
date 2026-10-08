"""Explicit local CLI. Imports no benchmark or provider client by default."""
import argparse
import json
import sys
from .config import ConfigError,load
from .storage import RunFailure

def main(argv=None):
 p=argparse.ArgumentParser(prog='python -m local_experiments')
 commands=p.add_subparsers(dest='command',required=True)
 sub=commands.add_parser('recovery-plan');sub.add_argument('--input-dir',required=True);sub.add_argument('--output-file',required=True)
 sub=commands.add_parser('resume');sub.add_argument('--config',required=True);sub.add_argument('--input-dir',required=True);sub.add_argument('--decisions',required=True);sub.add_argument('--output-dir',required=True);sub.add_argument('--mode',choices=('dry-run','live'),default='dry-run')
 for name in ('validate','run'):
  sub=commands.add_parser(name);sub.add_argument('--config',required=True)
  if name=='run':
   sub.add_argument('--mode',choices=('dry-run','live'),default='dry-run');sub.add_argument('--output-dir',required=True)
 sub=commands.add_parser('freeze');sub.add_argument('--config',required=True);sub.add_argument('--output-file',required=True)
 for name in ('analyze','export'):
  sub=commands.add_parser(name);sub.add_argument('--input-dir',required=True);sub.add_argument('--output-dir',required=True)
 args=p.parse_args(argv)
 try:
  if args.command=='recovery-plan':
   from .recovery import plan
   print(json.dumps(plan(args.input_dir,args.output_file)));return 0
  if args.command=='resume':
   from .launcher import launch
   load(args.config)
   return launch(args.config,args.mode,args.output_dir,(args.input_dir,args.decisions))
  if args.command=='freeze':
   from .freeze import seal
   print(json.dumps(seal(load(args.config,require_freeze=False),args.output_file)));return 0
  if args.command in ('validate','run'):
   c=load(args.config)
   if args.command=='validate':
    print(json.dumps({'configuration_valid':True,'execution_validated':False,'stage':c['stage'],'arms':c['arms']}));return 0
   from .launcher import launch
   return launch(args.config,args.mode,args.output_dir)
  from .analysis import analyze,export
  result=(analyze if args.command=='analyze' else export)(args.input_dir,args.output_dir)
  print(json.dumps(result,sort_keys=True));return 0
 except (ConfigError,RunFailure) as e: print(str(e),file=sys.stderr);return 2
 except (OSError,ValueError,KeyError,TypeError): print('Invalid or unavailable local input/output',file=sys.stderr);return 2

if __name__=='__main__': raise SystemExit(main())
