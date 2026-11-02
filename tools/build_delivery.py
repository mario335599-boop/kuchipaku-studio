"""Bundle a single offline HTML and a source distribution without requiring Node."""
from pathlib import Path
import json,re,zipfile,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'assets/character-kit.js').write_text('const PACK_CHARACTER_SCRIPT='+json.dumps((ROOT/'tools/pack_character.py').read_text(),ensure_ascii=False)+';\n')
html=(ROOT/'index.html').read_text()
def version_script(m):
 path=m.group(1).split('?')[0]
 digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()[:12]
 return '<script src="'+path+'?v='+digest+'"></script>'
html=re.sub(r'<script src="([^"]+)"></script>',version_script,html)
(ROOT/'index.html').write_text(html)
def inline(m):
 text=(ROOT/m.group(1).split('?')[0]).read_text().replace('</script','<\\/script')
 return '<script>\n'+text+'\n</script>'
html=re.sub(r'<script src="([^"]+)"></script>',inline,html)
(ROOT/'口パクスタジオ.html').write_text(html)
# Keep an already-shared local link useful after the rename.
(ROOT/'カーマン口パクスタジオ.html').write_text(html)
shutil.copyfile(ROOT/'start.sh',ROOT/'口パクスタジオを起動.sh')
(ROOT/'口パクスタジオを起動.sh').chmod(0o755)
files=['index.html','app.js','speech-ui.js','framing.js','model.js','studio-ui.js','server.py','speech.py','speech_jobs.py','start.sh','口パクスタジオを起動.sh','requirements.txt','口パクスタジオ.html','使い方.md','キャラクター素材の仕様.md','ChatGPT用プロンプト.txt','素材生成プロンプト.txt','口パクスタジオ_キャラ制作キット.zip','assets/default-character.js','assets/character-kit.js','vendor/jszip.min.js','vendor/JSZip-LICENSE.markdown','character-packs/カーマン_キャラクター素材.zip','tools/pack_character.py','tools/prepare_speech.py','tools/build_delivery.py','tests/verify_studio.py','tests/verify_framing.py','tests/verify_speech.py','tests/verify_position.py','output/自動字幕_確認画面.png','output/口パクスタジオ_画面.png','output/口パクスタジオ_動作サンプル.mp4']
with zipfile.ZipFile(ROOT.parent/'口パクスタジオ_更新版一式.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in files:
  f=ROOT/name
  if f.exists():z.write(f,Path('口パクスタジオ')/name)
print('Built 口パクスタジオ.html and 口パクスタジオ_更新版一式.zip')
