'use strict';
// Character packs are data and PNGs only. No package code is executed.
const CharacterPacks=(()=>{
 const parents=new Set(['body','head','arm','hair','decoration']);
 const fail=s=>{throw Error(s);};
 const finite=(n,lo,hi)=>typeof n==='number'&&Number.isFinite(n)&&n>=lo&&n<=hi;
 const safePath=p=>typeof p==='string'&&p.length<160&&!p.startsWith('/')&&!p.includes('\\')&&!p.split('/').some(s=>s==='..'||s==='.'||!s)&&!p.includes(':');
 function validate(manifest){
  const m=JSON.parse(JSON.stringify(manifest));
  if(m.format!=='lip-sync-studio-character'||m.version!==1)fail('口パクスタジオ用のcharacter.json（version: 1）が必要です。');
  if(typeof m.id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(m.id)||typeof m.name!=='string'||!m.name.trim()||m.name.length>80)fail('キャラクターのID・名前を確認してください。');
  if(!m.canvas||!Number.isInteger(m.canvas.width)||!Number.isInteger(m.canvas.height)||!finite(m.canvas.width,64,4096)||!finite(m.canvas.height,64,4096))fail('原稿サイズは64〜4096pxで指定してください。');
  if(!Array.isArray(m.layers)||!m.layers.length||m.layers.length>40)fail('本体の部品を1〜40個で指定してください。');
  if(!Array.isArray(m.accessories))fail('accessoriesは配列で指定してください。飾りがなければ [] にします。');
  if(m.accessories.length>30)fail('アクセサリーは30個までです。');
  const ids=new Set();
  function part(p,accessory=false){
   if(!p||typeof p.id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(p.id)||ids.has(p.id))fail('部品IDが重複しているか、形式が正しくありません。');ids.add(p.id);
   if(!safePath(p.src)||!p.src.toLowerCase().endsWith('.png'))fail('部品にはZIP内の透過PNGの相対パスを指定してください。');
   p.name=typeof p.name==='string'?p.name.slice(0,80):'';
   p.x??=0;p.y??=0;p.scale??=1;p.z??=accessory?40:0;p.pivot??=[0,0];p.parent??=null;
   if(!finite(p.x,-8192,8192)||!finite(p.y,-8192,8192)||!finite(p.scale,.01,5)||!finite(p.z,-1000,1000)||!Array.isArray(p.pivot)||p.pivot.length!==2||!p.pivot.every(n=>finite(n,-8192,8192)))fail('部品「'+p.id+'」の位置・支点・大きさを確認してください。');
   if(!accessory&&!parents.has(p.role))fail('部品「'+p.id+'」のroleをbody / head / arm / hair / decorationから選んでください。');
   p.motion??={};for(const [k,lo,hi,def] of [['amplitude',0,30,0],['frequency',0,10,1.8],['phase',-30,30,0]]){p.motion[k]??=def;if(!finite(p.motion[k],lo,hi))fail('部品の揺れ設定が範囲外です。');}
   if(accessory){p.enabled=p.enabled!==false;p.length??=300;p.swing??=3;p.lag??=.5;if(!finite(p.length,20,1500)||!finite(p.swing,0,30)||!finite(p.lag,-30,30))fail('アクセサリーの揺れ設定を確認してください。');}
  }
  m.layers.forEach(p=>part(p));m.accessories.forEach(p=>part(p,true));
  const layers=new Map(m.layers.map(p=>[p.id,p]));
  for(const p of [...m.layers,...m.accessories]){if(p.parent!==null&&!layers.has(p.parent))fail('取り付け先「'+p.parent+'」がありません。');const seen=new Set([p.id]);let q=p;while(q.parent){if(seen.has(q.parent))fail('部品の取り付け先が循環しています。');seen.add(q.parent);q=layers.get(q.parent);}}
  if(!m.mouth||!layers.has(m.mouth.parent)||!m.mouth.frames)fail('口の取り付け先と母音の画像を指定してください。');
  for(const v of ['a','i','u','e','o'])if(!safePath(m.mouth.frames[v]))fail('口の画像「'+v+'」がありません。');
  if(m.mouth.frames.closed&&!safePath(m.mouth.frames.closed))fail('閉じた口の画像パスを確認してください。');
  for(const p of [m.mouth,...(m.blink?[m.blink]:[])]){p.x??=0;p.y??=0;p.z??=p===m.mouth?31:32;if(!finite(p.x,-8192,8192)||!finite(p.y,-8192,8192)||!finite(p.z,-1000,1000))fail('目・口の位置を確認してください。');if(!layers.has(p.parent))fail('目・口の取り付け先がありません。');if(p.src&&!safePath(p.src))fail('まぶたの画像パスを確認してください。');if(p.width!==undefined&&!finite(p.width,1,4096)||p.height!==undefined&&!finite(p.height,1,4096))fail('目・口のサイズを確認してください。');}
  if(m.blink&&!m.blink.src)fail('まぶたの画像がありません。');
  m.view??={};m.view.framing??='custom';if(!['full','upper','custom'].includes(m.view.framing))fail('画角はfull / upper / customで指定してください。');m.view.top??=45;m.view.offsetY??=0;if(!finite(m.view.offsetY,-960,960))fail('上下の位置は-960〜960で指定してください。');m.view.zoom??=m.view.framing==='custom'?.61:1;if(!finite(m.view.top,-960,960)||!finite(m.view.zoom,.01,5))fail('構図の設定を確認してください。');
  return m;
 }
 function sources(m){return [...new Set([...m.layers.map(x=>x.src),...m.accessories.map(x=>x.src),...Object.values(m.mouth.frames),...(m.blink?[m.blink.src]:[])])];}
 async function prepare(bundle){
  if(!bundle||!bundle.files)fail('キャラクターの画像データがありません。');const manifest=validate(bundle.manifest),files={},images={};let pixels=0,bytes=0;
  for(const path of sources(manifest)){const data=bundle.files[path];if(typeof data!=='string'||!data.startsWith('data:image/png;base64,')||data.length>16e6)fail('画像「'+path+'」がありません、またはPNGではありません。');bytes+=data.length;if(bytes>180e6)fail('素材全体の容量が大きすぎます。');const im=await imageFrom(data);if(im.width>4096||im.height>4096||im.width<1||im.height<1)fail('画像は4096px以内にしてください。');pixels+=im.width*im.height;if(pixels>80e6)fail('部品画像の合計サイズが大きすぎます。');files[path]=data;images[path]=im;}
  return {manifest,files,images};
 }
 function preflight(buffer){const u=new Uint8Array(buffer),d=new DataView(buffer);let end=-1;for(let i=u.length-22;i>=Math.max(0,u.length-65557);i--)if(d.getUint32(i,true)===0x06054b50){end=i;break;}if(end<0)fail('ZIPとして読み込めません。');if(d.getUint16(end+4,true)||d.getUint16(end+6,true))fail('分割ZIPには対応していません。');const count=d.getUint16(end+10,true);let pos=d.getUint32(end+16,true),total=0;if(count>200||count===65535)fail('ZIP内のファイルが多すぎます。');for(let i=0;i<count;i++){if(pos+46>u.length||d.getUint32(pos,true)!==0x02014b50)fail('ZIPの構造が正しくありません。');if(d.getUint16(pos+8,true)&1)fail('パスワード付きZIPは読み込めません。');const size=d.getUint32(pos+24,true);total+=size;if(size>16e6||total>128e6)fail('展開後の素材容量が大きすぎます。');pos+=46+d.getUint16(pos+28,true)+d.getUint16(pos+30,true)+d.getUint16(pos+32,true);}}
 async function fromFile(file){if(file.size>80e6)fail('素材ファイルは80MB以内にしてください。');if(file.name.toLowerCase().endsWith('.json'))return prepare(JSON.parse(await file.text()));const buffer=await file.arrayBuffer();preflight(buffer);const zip=await JSZip.loadAsync(buffer);const candidates=Object.values(zip.files).filter(e=>!e.dir&&!e.name.startsWith('__MACOSX/')&&/(^|\/)character\.json$/.test(e.name));if(candidates.length!==1)fail('ZIP内にcharacter.jsonを1個だけ入れてください。');const entry=candidates[0],text=await entry.async('string');if(text.length>1e6)fail('character.jsonが大きすぎます。');const m=validate(JSON.parse(text));const prefix=entry.name.slice(0,-'character.json'.length),files={};for(const path of sources(m)){const entry=zip.file(prefix+path);if(!entry)fail('ZIPに「'+path+'」がありません。');const data=await entry.async('uint8array');if(data.length>12e6||data.length<24||!data.slice(0,8).every((n,i)=>n===[137,80,78,71,13,10,26,10][i]))fail('「'+path+'」は有効なPNGではありません。');const header=new DataView(data.buffer,data.byteOffset,data.byteLength);if(header.getUint32(16)>4096||header.getUint32(20)>4096)fail('「'+path+'」は4096px以内にしてください。');let str='';for(let i=0;i<data.length;i+=32768)str+=String.fromCharCode(...data.subarray(i,i+32768));files[path]='data:image/png;base64,'+btoa(str);}return prepare({manifest:m,files});}
 async function toZip(model){const z=new JSZip();z.file('character.json',JSON.stringify(model.manifest,null,2));for(const [path,data] of Object.entries(model.files))z.file(path,data.split(',')[1],{base64:true});return z.generateAsync({type:'blob',compression:'DEFLATE'});}
 const serial=model=>({manifest:model.manifest,files:model.files});
 async function database(){return new Promise((res,rej)=>{const r=indexedDB.open('lip-sync-studio',1);r.onupgradeneeded=()=>r.result.createObjectStore('characters',{keyPath:'id'});r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);});}
 async function stored(){const db=await database();return new Promise((res,rej)=>{const t=db.transaction('characters');const r=t.objectStore('characters').getAll();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);t.oncomplete=()=>db.close();});}
 async function persist(model){const db=await database();return new Promise((res,rej)=>{const t=db.transaction('characters','readwrite');t.objectStore('characters').put({id:model.manifest.id,bundle:serial(model)});t.oncomplete=()=>{db.close();res();};t.onerror=()=>{db.close();rej(t.error);};t.onabort=()=>rej(t.error);});}
 return {validate,prepare,fromFile,toZip,serial,stored,persist};
})();
