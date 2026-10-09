"""Report actual runner OS/CPU/Python without reading environment variables."""
import argparse
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--os',required=True,choices=('Linux','Darwin'))
p.add_argument('--arch',required=True,choices=('x86_64','arm64'))
a=p.parse_args()
report={'kind':'platform_facts','system':platform.system(),'release':platform.release(),
        'macos_version':platform.mac_ver()[0] or None,'machine':platform.machine(),
        'python_version':platform.python_version(),'python_bits':struct.calcsize('P')*8,
        'cpu':platform.processor(),'expected_system':a.os,'expected_machine':a.arch}
if report['system']=='Darwin':
 report['cpu']=subprocess.check_output(['/usr/sbin/sysctl','-n','machdep.cpu.brand_string'],text=True).strip()
assert report['system']==a.os and report['machine']==a.arch,report
assert sys.version_info[:2]==(3,12) and report['python_bits']==64,report
Path('results').mkdir(exist_ok=True)
Path('results/platform.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,sort_keys=True))
