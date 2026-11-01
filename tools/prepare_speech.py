"""Download/cache recognition weights on first setup, without uploading user audio."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from speech import get_model,reading,MODEL_DIR
if not list(MODEL_DIR.glob('models--Systran--faster-whisper-small/snapshots/*/model.bin')):
 print('音声認識の初回準備をしています。モデルをダウンロードします…',flush=True)
 get_model()
reading('音声の読みを準備します。')
print('音声認識と読みの準備ができました。',flush=True)
