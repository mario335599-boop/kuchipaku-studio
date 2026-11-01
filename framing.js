'use strict';
// Bounds use visible pixels, then expand conservatively over each joint's full swing.
const alphaBoundsCache=new WeakMap();
let framingCache={model:null,key:null,bounds:null};
function visibleBounds(image){
 if(alphaBoundsCache.has(image))return alphaBoundsCache.get(image);
 const c=document.createElement('canvas');c.width=image.width;c.height=image.height;const x=c.getContext('2d',{willReadFrequently:true});x.drawImage(image,0,0);const data=x.getImageData(0,0,c.width,c.height).data;let minX=c.width,minY=c.height,maxX=-1,maxY=-1;
 for(let y=0;y<c.height;y++)for(let xx=0;xx<c.width;xx++)if(data[(y*c.width+xx)*4+3]>=8){minX=Math.min(minX,xx);maxX=Math.max(maxX,xx+1);minY=Math.min(minY,y);maxY=Math.max(maxY,y+1);}
 const b=maxX<0?null:{minX,minY,maxX,maxY};alphaBoundsCache.set(image,b);c.width=c.height=1;return b;
}
function expandJointBounds(box,part,m){
 const scale=part.scale??1,[px,py]=part.pivot??[0,0],a=(part.length!==undefined?(part.swing||0)*1.7:(part.motion?.amplitude||0))*m*Math.PI/180;
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 for(const xx of [box.minX,box.maxX])for(const yy of [box.minY,box.maxY]){const x=(xx-px)*scale,y=(yy-py)*scale,phi=Math.atan2(y,x),angles=[-a,a];for(let k=-2;k<=2;k++)for(const v of [k*Math.PI-phi,Math.PI/2+k*Math.PI-phi])if(v>=-a&&v<=a)angles.push(v);for(const angle of angles){const rx=x*Math.cos(angle)-y*Math.sin(angle)+(part.x||0)+px*scale,ry=x*Math.sin(angle)+y*Math.cos(angle)+(part.y||0)+py*scale;minX=Math.min(minX,rx);maxX=Math.max(maxX,rx);minY=Math.min(minY,ry);maxY=Math.max(maxY,ry);}}
 return {minX,minY,maxX,maxY};
}
function characterBounds(m){
 const model=state.model,manifest=model.manifest,key=JSON.stringify([m,state.accessories.map(({id,x,y,pivot,scale,swing,lag,length,parent,enabled})=>({id,x,y,pivot,scale,swing,lag,length,parent,enabled}))]);
 if(framingCache.model===model&&framingCache.key===key)return framingCache.bounds;
 const parents=new Map(manifest.layers.map(p=>[p.id,p]));let result=null;
 for(const part of [...manifest.layers,...state.accessories.filter(p=>p.enabled)]){const image=part.image||model.images[part.src];let box=visibleBounds(image);if(!box)continue;let current=part;while(current){box=expandJointBounds(box,current,m);current=current.parent?parents.get(current.parent):null;}if(!result)result={...box};else{result.minX=Math.min(result.minX,box.minX);result.minY=Math.min(result.minY,box.minY);result.maxX=Math.max(result.maxX,box.maxX);result.maxY=Math.max(result.maxY,box.maxY);}}
 result??={minX:0,minY:0,maxX:manifest.canvas.width,maxY:manifest.canvas.height};framingCache={model,key,bounds:result};return result;
}
let subtitleBoundsCache={key:null,bottom:780};
function fullViewBottom(){
 if(!$('captions').checked)return 920;
 const key=JSON.stringify(state.cues.map(c=>c.text));if(subtitleBoundsCache.key===key)return subtitleBoundsCache.bottom;
 ctx.save();ctx.font='bold 29px "Noto Sans CJK JP", "Yu Gothic", sans-serif';let lines=1;for(const cue of state.cues)lines=Math.max(lines,wrap(cue.text||'',460).length);ctx.restore();
 const bottom=Math.max(220,Math.min(780,843-(lines-1)*39-29-26));subtitleBoundsCache={key,bottom};return bottom;
}
function characterPlacement(m){
 const manifest=state.model.manifest,mode=$('framing').value,zoom=+$('zoom').value,offsetY=+$('characterY').value||0;
 if(mode==='custom'){const scale=zoom*1024/manifest.canvas.width;return {scale,x:270-manifest.canvas.width/2*scale,y:manifest.view.top+offsetY};}
 const bounds={...characterBounds(m)};if(mode==='upper')bounds.maxY=bounds.minY+(bounds.maxY-bounds.minY)*.64;
 const top=60,bottom=fullViewBottom(),width=Math.max(1,bounds.maxX-bounds.minX),height=Math.max(1,bounds.maxY-bounds.minY),scale=.94*Math.min(492/width,(bottom-top)/height)*zoom;
 return {scale,x:270-(bounds.minX+bounds.maxX)/2*scale,y:(top+bottom)/2-(bounds.minY+bounds.maxY)/2*scale+offsetY};
}
$('framing').onchange=()=>{$('zoom').value=$('framing').value==='custom'?state.model.manifest.view.zoom:1;draw(state.time);};
$('resetFraming').onclick=()=>{$('zoom').value=$('framing').value==='custom'?state.model.manifest.view.zoom:1;draw(state.time);};

function updateCharacterPositionLabel(){const n=+$('characterY').value||0;$('characterYLabel').textContent=n===0?'中央':(n<0?'上 ':'下 ')+Math.abs(n);}
$('characterY').oninput=()=>{updateCharacterPositionLabel();draw(state.time);};
$('resetCharacterY').onclick=()=>{$('characterY').value=0;updateCharacterPositionLabel();draw(state.time);};
