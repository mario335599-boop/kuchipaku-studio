"""Real local recognition + editable subtitle workflow. Dev dependency: Playwright."""
import asyncio,base64,json,subprocess,tempfile,time,urllib.request,sys,wave
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def check_segment_rules():
 # Run in the application environment, including zero-duration Japanese tokens.
 script='''import speech,json
words=[{'text':'私','start':0,'end':0},{'text':'は','start':0,'end':.2},{'text':'話します。','start':.2,'end':1.2},{'text':'次の文です。','start':2.1,'end':3.2}]
c=speech.make_cues(words,4)
assert ''.join(x['text'] for x in c)=='私は話します。次の文です。',c
assert len(c)==2 and c[0]['end']<c[1]['start'],c
assert speech.reading('検証は終わったよ。').startswith('けんしょーわ')
print('PASS: zero-duration words retained, sentence/pause boundaries, Japanese reading')'''
 subprocess.run([str(ROOT/'.venv/bin/python'),'-c',script],check=True)

async def run(url,temp):
 temp=Path(temp)
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required']);page=await browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(url);await page.wait_for_function('studio.ready && studio.state.buffer')
  before_revision=await page.evaluate('studio.state.audioRevision')
  await page.locator('#audioFile').set_input_files(ROOT/'assets/sample.wav')
  await page.wait_for_function('(revision)=>studio.state.audioRevision>revision && !studio.state.transcribing && studio.state.cues.length>0',arg=before_revision,timeout=120000)
  cues=await page.evaluate('studio.state.cues');print('REAL RECOGNITION',json.dumps([{k:c[k] for k in ['start','end','text','reading']} for c in cues],ensure_ascii=False))
  assert len(cues)>=2 and all(c['reading'] for c in cues)
  assert '終わった' in ''.join(c['text'] for c in cues)
  assert all(a['end']<=b['start'] for a,b in zip(cues,cues[1:]))
  first=page.locator('#cues .cue').first
  await first.locator('.text').fill('検証は終わったよ。');await page.wait_for_function("studio.state.cues[0].reading.startsWith('けんしょーわ')")
  await first.locator('.reading').fill('けんしょーわおわったよ');await first.locator('.text').fill('検証は終わったよ！');await page.wait_for_timeout(650);assert await first.locator('.reading').input_value()=='けんしょーわおわったよ'
  await first.get_by_text('この区間を聴く',exact=True).click();await page.wait_for_timeout(400);assert await page.evaluate('studio.state.playing');await page.wait_for_timeout(1300);assert not await page.evaluate('studio.state.playing')
  # Explicit retry must preserve edited captions until the user applies it.
  before=await first.locator('.text').input_value();await page.locator('#retryTranscription').click();await page.wait_for_function('!studio.state.transcribing && !document.querySelector("#applyTranscription").hidden',timeout=120000);assert await first.locator('.text').input_value()==before
  await page.locator('#applyTranscription').click();await page.locator('#undoTranscription').click();assert await first.locator('.text').input_value()==before
  # A split made at the cursor and a merge preserve editable speech intervals.
  await first.locator('.text').evaluate('(e)=>e.setSelectionRange(3,3)');n=await page.locator('#cues .cue').count();await first.get_by_text('ここで分割',exact=True).click();assert await page.locator('#cues .cue').count()==n+1
  await page.locator('#cues .cue').first.get_by_text('次と結合',exact=True).click();assert await page.locator('#cues .cue').count()==n
  # Test file drop and direct file paste, not only the file picker.
  payload=base64.b64encode((ROOT/'assets/sample.wav').read_bytes()).decode()
  for event in ['drop','paste']:
   previous=await page.evaluate('studio.state.audioRevision')
   await page.evaluate('''({data,event})=>{const dt=new DataTransfer();dt.items.add(new File([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],'sample.wav',{type:'audio/wav'}));document.querySelector('#audioDrop').dispatchEvent(event==='drop'?new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}):new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}''',{'data':payload,'event':event})
   await page.wait_for_function('(n)=>studio.state.audioRevision>n',arg=previous)
   await page.wait_for_function('!studio.state.transcribing && studio.state.cues.length>0',timeout=120000)
  # Silence replaces old subtitles with no invented text.
  silent=temp/'silence.wav'
  with wave.open(str(silent),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\x00\x00'*32000)
  await page.locator('#audioFile').set_input_files(silent);await page.wait_for_function('!studio.state.transcribing && studio.state.duration===2',timeout=120000);assert await page.locator('#cues .cue').count()==0
  assert '話し声を検出できませんでした' in await page.locator('#transcriptionStatus').inner_text()
  # Edits during recognition survive the late response.
  await page.locator('#audioFile').set_input_files(ROOT/'assets/sample.wav');await page.wait_for_function('studio.state.transcribing');await page.locator('#addCue').click();await page.locator('#cues .cue').first.locator('.text').fill('処理中の手入力を保持');await page.wait_for_function('!studio.state.transcribing',timeout=120000);assert await page.locator('#cues .cue').first.locator('.text').input_value()=='処理中の手入力を保持'
  await page.locator('#applyTranscription').click();await page.wait_for_function('studio.state.cues.length>=2')
  await page.locator('#cues .cue').first.locator('.text').fill('検証は終わったよ。');await page.wait_for_function("studio.state.cues[0].reading.startsWith('けんしょーわ')")
  await page.screenshot(path=str(ROOT/'output/自動字幕_確認画面.png'),full_page=True)
  async with page.expect_download(timeout=120000) as event:await page.locator('#export').click()
  file=await event.value;await file.save_as(temp/'recognised.mp4');assert (temp/'recognised.mp4').stat().st_size>10000
  assert not errors,errors
  print('PASS: real ASR, semantic pauses, correction and kana refresh, manual reading retained, phrase replay, retry/undo, split/merge, WAV drop/paste, silence, edits protected during ASR, MP4 export')
  await browser.close()
if __name__=='__main__':
 check_segment_rules()
 with tempfile.TemporaryDirectory() as temp:
  server=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'server.py'),'--port','8772','--no-browser'],stdout=subprocess.DEVNULL)
  try:
   for _ in range(40):
    try:urllib.request.urlopen('http://127.0.0.1:8772',timeout=1);break
    except OSError:time.sleep(.1)
   asyncio.run(run('http://127.0.0.1:8772',temp))
  finally:server.terminate();server.wait()
