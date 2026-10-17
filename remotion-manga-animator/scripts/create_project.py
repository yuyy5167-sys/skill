#!/usr/bin/env python3
"""Copy an isolated manga entry point without overwriting an existing project."""
import argparse
import json
import shutil
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project',required=True)
parser.add_argument('--mode',choices=('new','existing'),required=True)
args=parser.parse_args()
root=Path(args.project).expanduser().resolve()
template=Path(__file__).resolve().parents[1]/'assets'/'remotion-template'
if args.mode=='new' and root.exists() and any(p.name!='tmp' for p in root.iterdir()):
    parser.error('New project must be empty except for tmp/. Use existing mode for an existing project.')
if args.mode=='existing' and not (root/'package.json').is_file():
    parser.error('Existing mode requires package.json; inspect the project before adding the manga entry.')
files=[p for p in template.rglob('*') if p.is_file()]
if args.mode=='existing':
    files=[p for p in files if p.relative_to(template).parts[0] in ('src','scripts','public')]
conflicts=[str(p.relative_to(template)) for p in files if (root/p.relative_to(template)).exists()]
if conflicts:
    parser.error('No files were changed. Existing destinations: '+', '.join(conflicts))
root.mkdir(parents=True,exist_ok=True)
(root/'tmp').mkdir(exist_ok=True)
for src in files:
    dest=root/src.relative_to(template);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
expected=json.loads((template/'package.json').read_text())['dependencies']
pkg=json.loads((root/'package.json').read_text())
declared={**pkg.get('dependencies',{}),**pkg.get('devDependencies',{})}
print(json.dumps({'project':str(root),'mode':args.mode,'files':len(files),'entry':'src/manga-animation/index.tsx','missing_dependencies':[k for k in expected if k not in declared],'declared_remotion_versions':{k:v for k,v in declared.items() if k=='remotion' or k.startswith('@remotion/')},'next':'Install compatible dependencies if needed, replace sample assets and config, then run node scripts/manga/prepare.mjs and node scripts/manga/validate.mjs.'},ensure_ascii=False,indent=2))
