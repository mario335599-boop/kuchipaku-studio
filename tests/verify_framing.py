"""Verify complete silhouettes remain inside the video, including moving ornaments."""
import asyncio,json,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def run(url,temp):
 p=Path(temp);im=Image.new('RGBA',(1000,2200));d=ImageDraw.Draw(im);d.ellipse((340,250,680,700),fill='#8abdc4');d.polygon([(350,380),(370,50),(470,310)],fill='#8abdc4');d.polygon([(550,310),(640,60),(675,390)],fill='#8abdc4');d.ellipse((350,600,660,1880),fill='#8abdc4');d.ellipse((300,1780,480,2080),fill='#8abdc4');d.ellipse((550,1780,720,2080),fill='#8abdc4');im.save(p/'whole.png')
 tail=Image.new('RGBA',(280,180));ImageDraw.Draw(tail).ellipse((0,0,280,180),fill='#9cd6cf');tail.save(p/'tail.png')
 mouth=Image.new('RGBA',(50,35));ImageDraw.Draw(mouth).ellipse((10,10,40,30),fill='#27434b');mouth.save(p/'mouth.png')
 m={'format':'lip-sync-studio-character','version':1,'id':'full-body-fixture','name':'全身確認用マスコット','canvas':{'width':1000,'height':2200},'view':{'framing':'full','zoom':1},'layers':[{'id':'core','role':'body','src':'whole.png','pivot':[500,1400],'z':0,'motion':{'amplitude':2,'frequency':1.7}},{'id':'tail','role':'hair','src':'tail.png','x':650,'y':1600,'parent':'core','pivot':[0,90],'z':-1,'motion':{'amplitude':20,'frequency':2}}],'mouth':{'parent':'core','x':480,'y':500,'frames':{v:'mouth.png' for v in ['a','i','u','e','o']}},'accessories':[{'id':'charm','name':'テスト用の飾り','src':'tail.png','parent':'core','x':250,'y':1500,'pivot':[0,0],'scale':.5,'length':200,'swing':20,'lag':.5,'z':30}]}
 with zipfile.ZipFile(p/'mascot.zip','w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('character.json',json.dumps(m));[z.write(p/f,f) for f in ['whole.png','tail.png','mouth.png']]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required']);page=await browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(url);await page.wait_for_function('studio.ready && studio.state.buffer');await page.locator('#characterFile').set_input_files(p/'mascot.zip');await page.wait_for_function("studio.state.model.manifest.id==='full-body-fixture' && !studio.state.importing")
  assert await page.locator('#framing').input_value()=='full';assert await page.locator('#zoom').input_value()=='1'
  await page.locator('#motion').fill('1.6');await page.locator('#motion').dispatch_event('input')
  result=await page.evaluate('''()=>{const m=1.6,p=characterPlacement(m);let box={minX:Infinity,minY:Infinity,maxX:-Infinity,maxY:-Infinity};for(let t=0;t<20;t+=.23)for(const l of [...studio.state.model.manifest.layers,...studio.state.accessories]){const b=visibleBounds(l.image||studio.state.model.images[l.src]);if(!b)continue;const mat=studio.matrixFor(l,t,m,new Map());for(const x of [b.minX,b.maxX])for(const y of [b.minY,b.maxY]){const q=mat.transformPoint(new DOMPoint(x,y)),px=p.x+q.x*p.scale,py=p.y+q.y*p.scale;box.minX=Math.min(box.minX,px);box.maxX=Math.max(box.maxX,px);box.minY=Math.min(box.minY,py);box.maxY=Math.max(box.maxY,py);}}return {box,scale:p.scale};}''')
  b=result['box'];assert b['minX']>=24 and b['maxX']<=516 and b['minY']>=60 and b['maxY']<=780,result
  await page.evaluate("window.previousCaption=studio.state.cues[0].text;studio.state.cues[0].text='全身表示の字幕が複数行になる場合も、足元と重ならないように余白を取って表示します。'");assert await page.evaluate('fullViewBottom()')<780;await page.evaluate('studio.state.cues[0].text=window.previousCaption');await page.locator('#framing').select_option('upper');assert await page.evaluate('characterPlacement(1.6).scale')>result['scale']
  await page.locator('#framing').select_option('full');await page.locator('#zoom').fill('1.3');await page.locator('#zoom').dispatch_event('input');await page.locator('#resetFraming').click();assert await page.locator('#zoom').input_value()=='1'
  async with page.expect_download() as event:await page.locator('#saveProject').click()
  f=await event.value;await f.save_as(p/'project.json');await page.locator('#framing').select_option('custom');await page.locator('#loadProject').set_input_files(p/'project.json');await page.wait_for_function("document.querySelector('#framing').value==='full' && !studio.state.importing")
  async with page.expect_download() as event:await page.locator('#exportCharacter').click()
  f=await event.value;await f.save_as(p/'saved.zip')
  with zipfile.ZipFile(p/'saved.zip') as z:assert json.loads(z.read('character.json'))['view']['framing']=='full'
  await page.evaluate('studio.draw(2.5)');await page.locator('canvas').screenshot(path='/tmp/studio-full-body.png')
  async with page.expect_download(timeout=120000) as event:await page.locator('#export').click()
  f=await event.value;await f.save_as(p/'full-body.mp4');assert (p/'full-body.mp4').stat().st_size>10000
  assert not errors,errors
  print('PASS: ear/foot/tail/ornament bounds within frame across motion; automatic full view; upper crop; reset; project and ZIP persistence; MP4 export',result)
  await browser.close()
if __name__=='__main__':
 with tempfile.TemporaryDirectory() as temp:
  server=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'server.py'),'--port','8770','--no-browser'],stdout=subprocess.DEVNULL)
  try:
   for _ in range(30):
    try:urllib.request.urlopen('http://127.0.0.1:8770',timeout=1);break
    except OSError:time.sleep(.1)
   asyncio.run(run('http://127.0.0.1:8770',temp))
  finally:server.terminate();server.wait()
