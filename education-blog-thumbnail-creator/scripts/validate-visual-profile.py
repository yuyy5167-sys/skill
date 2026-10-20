#!/usr/bin/env python3
"""Validate immutable cream-manga-mustard profile contract; no image quality claims."""
from pathlib import Path
import argparse,hashlib,json,re,sys

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check-references',action='store_true');args=ap.parse_args()
    root=Path(__file__).resolve().parents[1];p=root/'references/cream-manga-mustard-v1.json';x=json.loads(p.read_text(encoding='utf-8'));errors=[]
    expected={'profile_id':'cream-manga-mustard-v1','revision':1,'h2_direct_style_images_allowed':False,'trial_images_are_approved_examples':False}
    for k,v in expected.items():
        if x.get(k)!=v:errors.append(f'{k}: expected {v!r}')
    fixed=x['fixed_prompt'].replace('\r\n','\n').replace('\r','\n').rstrip('\n')+'\n';sha=hashlib.sha256(fixed.encode()).hexdigest()
    if sha!=x['fixed_prompt_sha256']:errors.append('JSON fixed_prompt SHA mismatch')
    md=(root/'references/cream-manga-mustard-v1.md').read_text(encoding='utf-8');m=re.search(r'```text\n(.*?)```',md,re.S)
    if not m or m.group(1)!=fixed:errors.append('Markdown fixed block differs from JSON')
    if sha not in md:errors.append('Markdown declared SHA missing')
    if not {'thumbnail','section_image'}<=set(x['assets']):errors.append('both asset types required')
    for e in x['approved_examples']+x['profile_character_references']:
        if e['role'] not in ['character_sheet','style_example','composition_guide','comparison_image']:errors.append('unknown reference role '+e['role'])
        if not re.fullmatch('[0-9a-f]{64}',e['sha256']):errors.append('invalid SHA '+e['id'])
        if args.check_references:
            f=Path(e['path'])
            if not f.is_file():errors.append('missing reference '+str(f))
            elif hashlib.sha256(f.read_bytes()).hexdigest()!=e['sha256']:errors.append('changed reference '+str(f))
    out={'result':'fail' if errors else 'pass','profile_id':x['profile_id'],'revision':x['revision'],'fixed_prompt_sha256':sha,'references_checked':args.check_references,'errors':errors};print(json.dumps(out,ensure_ascii=False,indent=2));return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
