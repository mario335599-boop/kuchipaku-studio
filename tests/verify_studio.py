"""Browser integration checks. Dev dependencies: playwright and Pillow."""
import asyncio,base64,copy,json,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

def fixtures(directory):
 p=Path(directory);parts=p/'parts';parts.mkdir()
 def png(name,size,draw):
  im=Image.new('RGBA',size);draw(ImageDraw.Draw(im));im.save(parts/name)
 png('body.png',(320,400),lambda d:d.rounded_rectangle((5,5,315,398),radius=28,fill='#356e91',outline='#b4e3dc',width=8))
 png('head.png',(220,200),lambda d:(d.rounded_rectangle((3,3,217,197),radius=35,fill='#e3bb72'),d.rectangle((40,65,70,90),fill='#19354c'),d.rectangle((150,65,180,90),fill='#19354c')))
 for k in ['a','i','u','e','o','closed']:
  png(k+'.png',(50,35),lambda d,k=k:(d.rectangle((0,0,50,35),fill='#e3bb72'),d.ellipse((5,10,45,12 if k=='closed' else 30),fill='#19354c')))
 png('blink.png',(180,50),lambda d:(d.rectangle((0,0,180,50),fill='#e3bb72'),d.line((20,30,50,30),fill='#19354c',width=3),d.line((130,30,160,30),fill='#19354c',width=3)))
 png('ornament.png',(30,95),lambda d:(d.line((15,0,15,60),fill='#eeeecc',width=3),d.ellipse((2,60,28,90),fill='#f4d458')))
 manifest={'format':'lip-sync-studio-character','version':1,'id':'fixture-no-accessories','name':'テスト用・飾りなし','canvas':{'width':600,'height':900},'view':{'top':100,'zoom':.4},'layers':[{'id':'chassis','name':'機体','role':'body','src':'parts/body.png','x':140,'y':300,'pivot':[160,180],'z':0,'motion':{'amplitude':1,'frequency':2}},{'id':'visor','name':'フェイス','role':'head','src':'parts/head.png','parent':'chassis','x':50,'y':-220,'pivot':[110,180],'z':10,'motion':{'amplitude':2,'frequency':1.8}}],'mouth':{'parent':'visor','x':85,'y':120,'frames':{k:'parts/'+k+'.png' for k in ['a','i','u','e','o','closed']}},'blink':{'parent':'visor','x':20,'y':45,'src':'parts/blink.png'},'accessories':[]}
 def pack(m,name,missing=False):
  with zipfile.ZipFile(p/name,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('bundle/character.json',json.dumps(m,ensure_ascii=False))
   for file in parts.glob('*.png'):
    if missing and file.name=='head.png':continue
    z.write(file,'bundle/parts/'+file.name)
 pack(manifest,'empty.zip')
 m=copy.deepcopy(manifest);m.update(id='fixture-with-accessories',name='テスト用・飾りあり')
 m['accessories']=[{'id':'bell','name':'テストのベル','src':'parts/ornament.png','parent':'visor','pivot':[15,0],'x':200,'y':80,'scale':1,'length':200,'swing':5,'lag':.6,'z':35},{'id':'badge','name':'テストの装飾','src':'parts/ornament.png','parent':'chassis','pivot':[15,0],'x':20,'y':100,'scale':.6,'length':120,'swing':2,'lag':1,'z':40}]
 pack(m,'ornaments.zip');pack(m,'missing.zip',True)
 cycle=copy.deepcopy(m);cycle['layers'][0]['parent']='visor';pack(cycle,'cycle.zip')
 image=Image.new('RGB',(1600,900));d=ImageDraw.Draw(image)
 for x in range(1600):d.line((x,0,x,900),fill=(x*255//1600,80,180))
 image.save(p/'background.png')
 return p

async def run(url,tmp):
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
  page=await browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(url);await page.wait_for_function('studio.ready && studio.state.buffer')
  assert await page.title()=='口パクスタジオ'
  assert await page.locator('#accessories .cue').count()==2
  async def load(name,id):
   await page.locator('#characterFile').set_input_files(tmp/name)
   await page.wait_for_function('(id)=>studio.state.model.manifest.id===id && !studio.state.importing',arg=id)
  await load('empty.zip','fixture-no-accessories');assert await page.locator('#accessories .cue').count()==0
  assert '赤い房' not in await page.locator('#accessories').inner_text()
  await page.evaluate('studio.draw(1.05)');await page.locator('canvas').screenshot(path=str(tmp/'different-character.png'))
  await load('ornaments.zip','fixture-with-accessories');assert await page.locator('#accessories .cue').count()==2
  assert 'テストのベル' in await page.locator('#accessories').inner_text()
  assert await page.locator('#accessories .cue').first.locator('select').input_value()=='visor'
  await page.locator('#accessories .cue').first.locator('input[type=number]').first.fill('220')
  await page.locator('#accessories .cue').first.locator('input[type=number]').first.dispatch_event('change')
  assert await page.evaluate('studio.state.accessories[0].x')==205
  await page.locator('#accessoryFile').set_input_files(tmp/'parts'/'ornament.png');await page.wait_for_function('studio.state.accessories.length===3')
  async with page.expect_download() as event:await page.locator('#exportCharacter').click()
  exported=await event.value;await exported.save_as(tmp/'exported.zip')
  with zipfile.ZipFile(tmp/'exported.zip') as z:
   m=json.loads(z.read('character.json'));assert len(m['accessories'])==3 and m['accessories'][0]['x']==205
   assert m['accessories'][2]['src'] in z.namelist()
  await page.reload();await page.wait_for_function('studio.ready && studio.state.buffer');assert await page.locator('#characterSelect').input_value()=='fixture-with-accessories'
  await load('exported.zip','fixture-with-accessories');assert await page.locator('#accessories .cue').count()==3
  for invalid in ['missing.zip','cycle.zip']:
   await page.locator('#characterFile').set_input_files(tmp/invalid);await page.wait_for_function("document.querySelector('#characterStatus').textContent.includes('読み込めませんでした') && !studio.state.importing")
   assert await page.locator('#characterSelect').input_value()=='fixture-with-accessories'
  colors=[]
  for bg in ['jade','ivory','midnight','sunset','sakura','forest','studio','neon','ocean','green','solid']:
   await page.locator('#bg').select_option(bg);colors.append(await page.evaluate('Array.from(document.querySelector("canvas").getContext("2d").getImageData(10,1000,1,1).data).join()'))
  assert len(set(colors))>=10
  await page.locator('#backgroundFile').set_input_files(tmp/'background.png');await page.wait_for_function('studio.state.background.image!==null')
  assert await page.locator('#bg').input_value()=='image'
  await page.locator('#bgFit').select_option('contain');await page.locator('#bgDim').fill('35');await page.locator('#bgDim').dispatch_event('input')
  async with page.expect_download() as event:await page.locator('#saveProject').click()
  project=await event.value;await project.save_as(tmp/'project.json')
  saved=json.loads((tmp/'project.json').read_text());assert saved['version']==2 and saved['background']['data'].startswith('data:image/png') and len(saved['accessories'])==3
  await page.locator('#characterSelect').select_option('kaman-sample');await page.locator('#clearBackground').click()
  await page.locator('#loadProject').set_input_files(tmp/'project.json');await page.wait_for_function('studio.state.background.image!==null && !studio.state.importing')
  assert await page.locator('#characterSelect').input_value()=='fixture-with-accessories'
  assert await page.locator('#bgDim').input_value()=='35'
  assert await page.locator('#bgFit').input_value()=='contain'
  assert await page.locator('#accessories .cue').count()==3
  async with page.expect_download() as event:await page.locator('#downloadKit').click()
  kit=await event.value;await kit.save_as(tmp/'kit.zip')
  with zipfile.ZipFile(tmp/'kit.zip') as z:assert 'character.example.json' in z.namelist() and 'accessories' in z.read('素材仕様.md').decode()
  # Imported character + uploaded background must survive actual recording.
  async with page.expect_download(timeout=120000) as event:await page.locator('#export').click()
  video=await event.value;await video.save_as(tmp/'imported-character.mp4');assert (tmp/'imported-character.mp4').stat().st_size>10000
  assert 'MP4を保存しました' in await page.locator('#status').inner_text()
  await page.locator('#characterSelect').select_option('kaman-sample');await page.locator('#bg').select_option('sunset');await page.evaluate('studio.draw(2.3)')
  await page.screenshot(path=str(ROOT/'output'/'口パクスタジオ_画面.png'),full_page=True)
  async with page.expect_download(timeout=120000) as event:await page.locator('#export').click()
  video=await event.value;await video.save_as(ROOT/'output'/'口パクスタジオ_動作サンプル.mp4')
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth')<=390
  assert not errors,errors
  print('PASS: different canvas/cropped parts/parent IDs, zero/multiple accessories, ZIP import/export and persistence, invalid ZIP atomic rejection, 11 background presets, uploaded background and full project round-trip, kit ZIP, MP4 recording, mobile layout, no browser errors')
  await browser.close()

if __name__=='__main__':
 with tempfile.TemporaryDirectory(prefix='studio-verification-') as temp:
  tmp=fixtures(temp);server=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'server.py'),'--port','8769','--no-browser'],stdout=subprocess.DEVNULL)
  try:
   for _ in range(30):
    try:urllib.request.urlopen('http://127.0.0.1:8769',timeout=1);break
    except OSError:time.sleep(.1)
   asyncio.run(run('http://127.0.0.1:8769',tmp))
  finally:server.terminate();server.wait()
