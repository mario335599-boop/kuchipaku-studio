#!/usr/bin/env python3
"""Validate a prepared character directory and package its referenced PNG assets. Python standard library only."""
import argparse,json,struct,zipfile
from pathlib import Path

def build(folder,output):
 root=Path(folder).resolve();manifest=json.loads((root/'character.json').read_text(encoding='utf-8'))
 if manifest.get('format')!='lip-sync-studio-character' or manifest.get('version')!=1:raise ValueError('format/versionが違います')
 if not manifest.get('name') or not manifest.get('id'):raise ValueError('キャラ名とIDが必要です')
 layers=manifest.get('layers',[]);accessories=manifest.get('accessories')
 if not 1<=len(layers)<=40 or not isinstance(accessories,list) or len(accessories)>30:raise ValueError('部品とアクセサリーの配列を確認してください')
 ids=[p['id'] for p in layers+accessories]
 if len(set(ids))!=len(ids):raise ValueError('部品IDが重複しています')
 parents={p['id']:p for p in layers};sources=[]
 for p in layers+accessories:
  sources.append(p['src']);seen={p['id']};parent=p.get('parent')
  while parent:
   if parent not in parents or parent in seen:raise ValueError('取り付け先が存在しないか循環しています')
   seen.add(parent);parent=parents[parent].get('parent')
 mouth=manifest['mouth']
 if mouth.get('parent') not in parents:raise ValueError('口の取り付け先がありません')
 for vowel in ['a','i','u','e','o']:sources.append(mouth['frames'][vowel])
 if mouth['frames'].get('closed'):sources.append(mouth['frames']['closed'])
 if manifest.get('blink'):
  if manifest['blink'].get('parent') not in parents:raise ValueError('目の取り付け先がありません')
  sources.append(manifest['blink']['src'])
 files={};pixels=0;total=0
 for name in set(sources):
  if not isinstance(name,str) or '\\' in name or ':' in name or any(p in ('.','..','') for p in name.split('/')):raise ValueError('相対パスが正しくありません')
  path=(root/name).resolve()
  if not path.is_relative_to(root):raise ValueError('素材フォルダーの外は参照できません')
  data=path.read_bytes()
  if data[:8]!=b'\x89PNG\r\n\x1a\n' or len(data)<33:raise ValueError(name+' はPNGではありません')
  width,height=struct.unpack('>II',data[16:24]);pixels+=width*height;total+=len(data)
  if max(width,height)>4096 or len(data)>12_000_000:raise ValueError(name+' が大きすぎます')
  if data[25] not in (4,6) and b'tRNS' not in data:raise ValueError(name+' には透過情報が必要です')
  files[name]=data
 if pixels>80_000_000 or total>128_000_000:raise ValueError('素材全体のサイズが大きすぎます')
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
  archive.writestr('character.json',json.dumps(manifest,ensure_ascii=False,indent=2))
  for name,data in sorted(files.items()):archive.writestr(name,data)
 print(str(output)+'：'+str(len(files))+' PNG、'+str(len(accessories))+' アクセサリー')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('folder');parser.add_argument('--output',default='character.zip');args=parser.parse_args()
 try:build(args.folder,args.output)
 except (ValueError,KeyError,OSError,json.JSONDecodeError) as e:parser.exit(1,'素材を確認してください: '+str(e)+'\n')
