"""Check vertical movement in the real preview and both persistence formats."""
import asyncio,json,subprocess,tempfile,time,urllib.request,zipfile
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def run(url,temp):
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,args=['--no-sandbox']);page=await b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(url);await page.wait_for_function('studio.ready && studio.state.buffer')
  base=await page.evaluate('characterPlacement(.7).y')
  await page.locator('#characterY').fill('150');await page.locator('#characterY').dispatch_event('input');assert abs(await page.evaluate('characterPlacement(.7).y')-base-150)<.001;assert await page.locator('#characterYLabel').inner_text()=='下 150'
  await page.locator('#characterY').fill('-100');await page.locator('#characterY').dispatch_event('input');assert abs(await page.evaluate('characterPlacement(.7).y')-base+100)<.001
  await page.locator('#framing').select_option('full');base=await page.evaluate('characterPlacement(.7).y');await page.locator('#characterY').fill('0');await page.locator('#characterY').dispatch_event('input');assert abs(await page.evaluate('characterPlacement(.7).y')-base-100)<.001
  await page.locator('#characterY').fill('80');await page.locator('#characterY').dispatch_event('input')
  async with page.expect_download() as event:await page.locator('#saveProject').click()
  f=await event.value;project=Path(temp)/'project.json';await f.save_as(project);assert json.loads(project.read_text())['options']['characterY']=='80'
  await page.locator('#resetCharacterY').click();assert await page.locator('#characterY').input_value()=='0'
  await page.locator('#loadProject').set_input_files(project);await page.wait_for_function("document.querySelector('#characterY').value==='80' && !studio.state.importing")
  async with page.expect_download() as event:await page.locator('#exportCharacter').click()
  f=await event.value;pack=Path(temp)/'character.zip';await f.save_as(pack)
  with zipfile.ZipFile(pack) as z:assert json.loads(z.read('character.json'))['view']['offsetY']==80
  await page.locator('#characterFile').set_input_files(pack);await page.wait_for_function("!studio.state.importing && document.querySelector('#characterStatus').textContent.includes('反映しました')");assert await page.locator('#characterY').input_value()=='80'
  await page.screenshot(path=str(ROOT/'output/上下位置バー_確認.png'),full_page=True);assert not errors,errors;print('PASS: up/down preview, full framing offset, reset, project restore, character ZIP import/export, no JS errors');await b.close()
if __name__=='__main__':
 with tempfile.TemporaryDirectory() as temp:
  s=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'server.py'),'--port','8773','--no-browser'],stdout=subprocess.DEVNULL)
  try:
   for _ in range(30):
    try:urllib.request.urlopen('http://127.0.0.1:8773');break
    except OSError:time.sleep(.1)
   asyncio.run(run('http://127.0.0.1:8773',temp))
  finally:s.terminate();s.wait()
