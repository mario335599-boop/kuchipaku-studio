'use strict';
const library=new Map();
const CHARACTER_EXAMPLE={format:'lip-sync-studio-character',version:1,id:'my-character',name:'キャラクター名',canvas:{width:1024,height:1536},view:{framing:'full',top:45,zoom:1,offsetY:0},layers:[{id:'body',name:'胴体',role:'body',src:'parts/body.png',parent:null,pivot:[512,900],z:10,motion:{amplitude:.2,frequency:1.7,phase:0}},{id:'head',name:'頭',role:'head',src:'parts/head.png',parent:'body',pivot:[512,450],z:20,motion:{amplitude:.7,frequency:1.8,phase:.4}}],mouth:{parent:'head',x:0,y:0,z:21,frames:{closed:'parts/mouth-closed.png',a:'parts/mouth-a.png',i:'parts/mouth-i.png',u:'parts/mouth-u.png',e:'parts/mouth-e.png',o:'parts/mouth-o.png'}},blink:{parent:'head',x:0,y:0,z:22,src:'parts/eyes-closed.png'},accessories:[]};
const CHARACTER_SPEC=`# 口パクスタジオ キャラクター素材形式 v1

ZIPのルートにcharacter.jsonを1個、相対パスで参照する透過PNGを入れます。フォルダー1階層に包むZIPも読み込めます。実行ファイルやJavaScriptは不要です。
formatはlip-sync-studio-character、versionは1です。idは英数字・ハイフン・アンダースコア、nameは表示するキャラ名。canvasは制作原稿の幅・高さ。推奨1024×1536、各辺64〜4096px。

layers: 最大40個。本体部品ごとにid（全体で重複禁止）、name、role（body/head/arm/hair/decoration）、src、parent、x/y（省略0）、scale（省略1）、pivot:[x,y]、z（小さいほど奥）、motion:{amplitude:角度,frequency:ラジアン毎秒,phase:位相}を指定します。
parentは別の本体部品のidまたはnull。循環は禁止。子は親の移動・回転に追従します。画像内のpivotを中心に回転し、x/yは親のローカル座標に対する画像左上です。推奨：全PNGを同じ1024×1536原稿の位置にそろえ、x/y=0、scale=1にすると配置ずれを防げます。切り抜いた小さいPNGの場合は画像自身の原点・支点と親の座標を整えます。

mouth: parentは頭の部品id。x/yは親座標上の位置。framesにa/i/u/e/oと、可能ならclosedのPNGパスを指定。width/heightは省略時に実画像の大きさ。headは開いた目と閉じた口を含む通常顔です。口フレームは通常の口の周囲も自然に覆う置換パッチにします。フレーム外は透明。全原稿サイズにそろえる場合はx/y=0。
blink: parent、src、x/yを指定。閉じた両目と、その下の通常の目を完全に覆う局所パッチ。元のまぶた・肌・前髪と自然につなぎ、フレーム外は透明。全原稿サイズならx/y=0。blinkを省略すると瞬きなし。

accessories: そのキャラクターに実際に付いている、独立して揺れる飾りだけを配列にします。飾りなしは必ず[]。名前や個数を固定しません。本体と同じid/name/src/parent/x/y/scale/pivot/zに加えてlength（20〜1500、長いほど遅い）、swing（0〜30度）、lag（位相、通常0〜2）、enabled:trueを指定。取り付け先は本体部品のidかnull。飾りの裏の服や髪は補完して、本体に元の飾りを残さないこと。ネックレス等の固定部分と揺れる部分は必要に応じて分けます。

アクセサリー例（必要な場合のみ。名前と値は画像から判断して変更）:
{"id":"ornament-1","name":"画像から判別した飾り名","src":"parts/ornament-1.png","parent":"body","x":0,"y":0,"scale":1,"pivot":[600,1000],"z":30,"length":300,"swing":3,"lag":0.7,"enabled":true}

view.framingはfull（全身）、upper（上半身へ寄る）、custom（素材の指定どおり）。マスコットや全身キャラはfullとzoom:1を指定し、耳・足先・尾・翼・可動アクセサリーをすべて含む全身素材を用意してください。fullは透明な余白を除く部品の範囲と揺れの余裕を計算し、字幕の上に全身を収めます。upperは素材の上部へ寄せます。full/upperではzoomは自動調整に対する倍率（通常1）。customではview.topが原稿上端（540×960の画面座標）、view.zoomが横1024基準の倍率です。zoomは0.01〜5。view.offsetYは自動調整後の上下移動（-960〜960、標準0、正は下、540×960画面の単位）。出力の画面比率は9:16です。全身素材がない上半身の絵から、アプリ側で足などを生成することはありません。

PNGは1枚12MB以内、1辺4096px以内、合計8000万画素以内。ZIP80MB以内、展開後128MB以内、200ファイル以内。本体40個、アクセサリー30個まで。背景画像・音声・字幕はキャラZIPに入れず、アプリで別に選びます。

キットのpack_character.pyは、python pack_character.py 素材フォルダー --output character.zip で準備した素材を検証・ZIP化できます。

ZIPの実ファイル、参照先、透明性、通常顔、母音5種、瞬き、部品の重なりと支点を検証し、実際のPNGと設定がそろって初めて完成としてください。見本JSONだけのZIPを完成品としないでください。
`;
const CHARACTER_PROMPT=`添付した三面図・キャラクターシートを基に、「口パクスタジオ」で動かせるキャラクター素材ZIPを実際に作り、ダウンロードできる完成ファイルとして渡してください。制作キットを添付した場合は、その仕様とcharacter.example.jsonを使ってください。

・キャラの顔・髪型・衣装・色・質感を保つ。上半身だけにする固定ルールは設けない。マスコット・デフォルメキャラ・動物など全身を使うキャラは、頭頂・耳・手足・足先・尾・翼・飾りまで欠けない正面の全身素材を作り、view.framing:"full", view.zoom:1を指定する。人型でも全身指定があれば同じ。上半身の指定がある場合だけ、その画角の素材を作る。
・頭・胴体・左右の腕・可動する髪や布を部品化する。不要な部品は増やさない。下の画像も補完し、回転しても隙間や元の部品が二重に出ない重なりを持たせる。
・閉じた口と「あ・い・う・え・お」の口、閉じたまぶたを、顔の同じ位置に自然につながる置換部品として作る。口や目の周囲の肌に色の境目を出さず、前髪を壊さない。
・アクセサリーは画像から個別に判別する。実際に付いている揺れるものだけを、1個ずつ透過PNGに分け、画像から判断した名前・取り付け先・支点・長さ・揺れ幅・遅れを設定する。刺繍や固定模様は揺れるアクセサリーにしない。付いていなければaccessories:[]。本体には元の飾りを残さない。
・同じ原稿サイズ・同じ位置に透明PNGをそろえる方式を推奨。全体画像をそのまま重ねて二重の顔や腕にしない。画像生成と画像処理が必要なら使用して仕上げる。
・ZIPのルートにcharacter.jsonを1個、その設定から参照される実在する透過PNGを同梱する。コード、背景、音声は入れない。完成前に参照先・JSON・画像の表示・透明部分・部品位置を検証し、合成見本も見せる。
・このチャットで画像生成やファイル作成を使えない場合は、完成したふりや空のZIPを出さず、利用できない機能と必要な次の作業を明示する。使える場合は素材作成からZIPの完成まで進める。

以下が読み込み仕様です。
${CHARACTER_SPEC}

最小構造の例（位置や部品はキャラに合わせて変更し、実際のPNGをすべて作ること）:
${JSON.stringify(CHARACTER_EXAMPLE,null,2)}`;
$('characterPrompt').value=CHARACTER_PROMPT;
function characterMessage(text){$('characterStatus').textContent=text;}
function refreshCharacters(){const select=$('characterSelect');select.replaceChildren();for(const model of library.values()){const o=document.createElement('option');o.value=model.manifest.id;o.textContent=model.manifest.name;select.append(o);}if(state.model)select.value=state.model.manifest.id;}
function selectPreparedModel(model,accessories){stop();pauseAt=0;state.time=0;state.model=model;library.set(model.manifest.id,model);state.accessories=accessories;refreshCharacters();renderAccessories();$('framing').value=model.manifest.view.framing;$('zoom').value=model.manifest.view.zoom;$('characterY').value=model.manifest.view.offsetY||0;updateCharacterPositionLabel();$('characterName').textContent=model.manifest.name;$('characterSummary').textContent=model.manifest.layers.length+' 部品 · アクセサリー '+accessories.length+' 個';try{localStorage.setItem('lip-sync-studio-selected',model.manifest.id);}catch{}draw(0);}
async function activateModel(model){const accessories=await prepareAccessories(model.manifest.accessories.map(a=>({...a,builtin:true})),model);selectPreparedModel(model,accessories);}
async function importCharacter(file){if(state.recording||state.importing)return;state.importing=true;lock(true);characterMessage('キャラクター素材を確認しています…');try{const model=await CharacterPacks.fromFile(file);await activateModel(model);let saved=true;try{await CharacterPacks.persist(model);}catch{saved=false;}characterMessage(model.manifest.name+' を反映しました。'+(saved?'次回も選択できます。':'この画面では使えます。次回は素材ZIPを読み込み直してください。'));}catch(e){characterMessage('読み込めませんでした：'+e.message);}finally{state.importing=false;lock(false);$('characterFile').value='';}}
$('characterFile').onchange=e=>{if(e.target.files[0])importCharacter(e.target.files[0]);};
$('characterSelect').onchange=async e=>{if(state.importing||state.recording)return;try{await activateModel(library.get(e.target.value));characterMessage('キャラクターを切り替えました。音声・字幕・背景は引き続き使えます。');}catch(e){characterMessage(e.message);refreshCharacters();}};
$('copyPrompt').onclick=async()=>{try{await navigator.clipboard.writeText(CHARACTER_PROMPT);characterMessage('プロンプトをコピーしました。ChatGPTにキャラクターシートと一緒に貼り付けてください。');}catch{$('promptDetails').open=true;$('characterPrompt').focus();$('characterPrompt').select();characterMessage('プロンプトを選択しました。コピーしてChatGPTに貼り付けてください。');}};
$('downloadPrompt').onclick=()=>download(new Blob([CHARACTER_PROMPT],{type:'text/plain;charset=utf-8'}),'口パクスタジオ_素材作成プロンプト.txt');
$('downloadKit').onclick=async()=>{const zip=new JSZip();zip.file('はじめに.txt',CHARACTER_PROMPT);zip.file('素材仕様.md',CHARACTER_SPEC);zip.file('character.example.json',JSON.stringify(CHARACTER_EXAMPLE,null,2));zip.file('pack_character.py',PACK_CHARACTER_SCRIPT);download(await zip.generateAsync({type:'blob',compression:'DEFLATE'}),'口パクスタジオ_キャラ制作キット.zip');};
$('exportCharacter').onclick=async()=>{try{const bundle=CharacterPacks.serial(state.model),manifest=JSON.parse(JSON.stringify(bundle.manifest)),files={...bundle.files};manifest.view={...manifest.view,framing:$('framing').value,zoom:+$('zoom').value,offsetY:+$('characterY').value};manifest.accessories=state.accessories.map(({image,data,builtin,...a})=>{if(!builtin){a.src='custom/'+a.id+'.png';files[a.src]=data;}return a;});const model=await CharacterPacks.prepare({manifest,files});download(await CharacterPacks.toZip(model),manifest.id+'_キャラクター素材.zip');characterMessage('調整した飾りも含めて、キャラクター素材ZIPを保存しました。');}catch(e){characterMessage('保存できませんでした：'+e.message);}};
function dropZone(el,accept){el.addEventListener('dragover',e=>{e.preventDefault();e.stopPropagation();el.classList.add('dragging');});el.addEventListener('dragleave',()=>el.classList.remove('dragging'));el.addEventListener('drop',e=>{e.preventDefault();e.stopPropagation();el.classList.remove('dragging');if(e.dataTransfer.files[0])accept(e.dataTransfer.files[0]);});el.addEventListener('paste',e=>{const file=Array.from(e.clipboardData.items).find(i=>i.kind==='file')?.getAsFile();if(file){e.preventDefault();e.stopPropagation();accept(file);}});}
dropZone($('characterDrop'),importCharacter);
async function clipboardFile(accept,test,onFailure){try{if(!navigator.clipboard?.read)throw Error();for(const item of await navigator.clipboard.read()){const type=item.types.find(test);if(type){const blob=await item.getType(type);const name=type.includes('zip')?'character.zip':type.includes('json')?'character.json':type.startsWith('audio/')?'audio.'+(type.includes('wav')||type.includes('wave')?'wav':type.split('/')[1]):'background.'+(type.split('/')[1]||'png');await accept(new File([blob],name,{type}));return;}}throw Error();}catch{onFailure();}}
$('pasteCharacter').onclick=()=>clipboardFile(importCharacter,t=>/zip|json/.test(t),()=>{characterMessage('この枠を選んで貼り付けるか、完成したZIPをダウンロードしてドロップしてください。');$('characterDrop').focus();});

function drawBackground(theme){
 ctx.save();ctx.fillStyle='#10231f';ctx.fillRect(0,0,540,960);
 if(theme==='image'&&state.background.image){const im=state.background.image,fit=$('bgFit').value;const scale=(fit==='contain'?Math.min:Math.max)(540/im.width,960/im.height);const w=im.width*scale,h=im.height*scale,x=(540-w)*+$('bgX').value/100,y=(960-h)*+$('bgY').value/100;ctx.drawImage(im,x,y,w,h);ctx.fillStyle='rgba(0,0,0,'+(+$('bgDim').value/100)+')';ctx.fillRect(0,0,540,960);}
 else if(theme==='green'||theme==='solid'){ctx.fillStyle=theme==='green'?'#00c85a':$('bgColor').value;ctx.fillRect(0,0,540,960);}
 else{const themes={jade:['#142d2a','#071512','#d3bf91'],ivory:['#ede4d5','#cec1aa','#65563d'],midnight:['#16213d','#070c1b','#c7d3f0'],sunset:['#efa77c','#65435f','#ffe7cf'],sakura:['#f2dce7','#b79bb8','#624a64'],forest:['#617361','#142a23','#e1dbb1'],studio:['#f5f3ed','#c7cbd0','#4f5a63'],neon:['#282044','#071b30','#a7e7ed'],ocean:['#75bac4','#0f465d','#e3f4e9']};const palette=themes[theme]||themes.jade,g=ctx.createLinearGradient(0,0,540,960);g.addColorStop(0,palette[0]);g.addColorStop(1,palette[1]);ctx.fillStyle=g;ctx.fillRect(0,0,540,960);if(theme==='studio'){ctx.fillStyle='#ffffff33';for(let i=0;i<3;i++)ctx.fillRect(40+i*175,0,80,960);}else if(theme==='neon'){ctx.strokeStyle='#82cfe522';ctx.lineWidth=1;for(let i=0;i<12;i++){ctx.beginPath();ctx.moveTo(0,100+i*82);ctx.lineTo(540,100+i*82);ctx.stroke();}}else{ctx.strokeStyle=palette[2]+'33';ctx.lineWidth=1;for(const r of [225,240]){ctx.beginPath();ctx.arc(270,385,r,0,Math.PI*2);ctx.stroke();}ctx.fillStyle=palette[2]+'44';for(let i=0;i<28;i++){ctx.beginPath();ctx.arc((i*167+27)%540,80+(i*97)%800,1.2,0,7);ctx.fill();}}ctx.fillStyle=palette[2];ctx.textAlign='center';ctx.font='13px sans-serif';ctx.fillText(state.model?.manifest.name||'',270,30);}
 ctx.restore();
}
async function prepareBackground(data,filename='背景画像'){if(typeof data!=='string'||!/^data:image\/(png|jpeg|webp);base64,/.test(data)||data.length>24e6)throw Error('背景は15MB以内のPNG・JPEG・WebPで選んでください。');const image=await imageFrom(data);if(image.width>8192||image.height>8192||image.width*image.height>40e6)throw Error('背景は1辺8192px、合計4000万画素以内で選んでください。');return {data,image,filename:typeof filename==='string'?filename.slice(0,160):'背景画像'};}
async function importBackground(file){if(state.recording||state.importing)return;try{if(file.size>15e6||!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('背景は15MB以内のPNG・JPEG・WebPで選んでください。');const data=await new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(file);});const bg=await prepareBackground(data,file.name);state.background=bg;$('bg').value='image';updateBackgroundControls();draw(state.time);$('backgroundStatus').textContent='背景画像を反映しました。';}catch(e){$('backgroundStatus').textContent=e.message;}finally{$('backgroundFile').value='';}}
function updateBackgroundControls(){$('imageBackgroundControls').hidden=$('bg').value!=='image';$('solidBackgroundControls').hidden=$('bg').value!=='solid';$('backgroundName').textContent=state.background.filename||'背景画像はまだ読み込まれていません';}
$('backgroundFile').onchange=e=>{if(e.target.files[0])importBackground(e.target.files[0]);};
dropZone($('backgroundDrop'),importBackground);
$('pasteBackground').onclick=()=>clipboardFile(importBackground,t=>['image/png','image/jpeg','image/webp'].includes(t),()=>{$('backgroundStatus').textContent='背景の枠を選んで画像を貼り付けるか、画像ファイルを選んでください。';$('backgroundDrop').focus();});
$('clearBackground').onclick=()=>{state.background={data:null,image:null,filename:''};$('bg').value='jade';updateBackgroundControls();draw(state.time);$('backgroundStatus').textContent='背景画像を解除しました。';};
$('bg').onchange=()=>{updateBackgroundControls();draw(state.time);};for(const id of ['bgFit','bgX','bgY','bgDim','bgColor'])$(id).oninput=()=>draw(state.time);
(async()=>{try{let model=await CharacterPacks.prepare(DEFAULT_CHARACTER);library.set(model.manifest.id,model);try{for(const saved of await CharacterPacks.stored()){try{const m=await CharacterPacks.prepare(saved.bundle);library.set(m.manifest.id,m);}catch{}}const selected=localStorage.getItem('lip-sync-studio-selected');model=library.get(selected)||model;}catch{}await activateModel(model);ready=true;renderCues();if(SAMPLE_AUDIO){await loadAudio(Uint8Array.from(atob(SAMPLE_AUDIO),c=>c.charCodeAt(0)).buffer);}else{state.duration=0;state.cues=[];$('seek').max=0;$('audioName').textContent='音声を読み込んでください';renderCues();}await document.fonts.ready;draw(0);updateBackgroundControls();characterMessage('ZIPを読み込むと、そのキャラクターの部品とアクセサリーが反映されます。');try{if(location.protocol==='http:'){const r=await fetch('/capabilities');mp4=!!(await r.json()).mp4;}}catch{}$('status').textContent='準備できました。'+(mp4?' MP4保存が使えます。':' WebMで保存できます。');}catch(e){$('status').textContent='読み込みに失敗しました：'+e.message;characterMessage(e.message);}})();
