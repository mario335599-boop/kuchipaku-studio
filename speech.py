"""Local speech recognition, timed Japanese phrase segmentation, and kana readings."""
from pathlib import Path
from functools import lru_cache
import io,os,re,threading,wave,math
ROOT=Path(__file__).resolve().parent
MODEL_NAME='small'
MODEL_DIR=ROOT/'.models'
_model=None
_model_lock=threading.Lock()
_tagger=None
_reader_lock=threading.Lock()
os.environ.setdefault('HF_HUB_DISABLE_XET','1')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')

def available():
 import importlib.util
 return all(importlib.util.find_spec(m) is not None for m in ['faster_whisper','fugashi','unidic_lite'])

def get_model():
 global _model
 with _model_lock:
  if _model is None:
   from faster_whisper import WhisperModel
   _model=WhisperModel(MODEL_NAME,device='cpu',compute_type='int8',cpu_threads=min(6,os.cpu_count() or 2),download_root=str(MODEL_DIR))
 return _model

def _hiragana(text):
 return ''.join(chr(ord(c)-96) if 'ァ'<=c<='ヶ' else c for c in text)

@lru_cache(maxsize=512)
def reading(text):
 global _tagger
 with _reader_lock:
  if _tagger is None:
   import fugashi
   _tagger=fugashi.Tagger()
  result=[]
  for token in _tagger(text):
   if token.feature.pos1=='補助記号':continue
   pron=getattr(token.feature,'pron',None) or getattr(token.feature,'kana',None)
   result.append(_hiragana(pron if pron and pron!='*' else token.surface))
  return ''.join(result)

def normal_text(text):
 text=re.sub(r'(?<=[\u3040-\u30ff\u3400-\u9fff])\s+(?=[\u3040-\u30ff\u3400-\u9fff])','',text).strip()
 return re.sub(r'\s+([。、！？!?])',r'\1',text)

def phrase_end(text):
 text=text.rstrip('、,。！？!?」』）) ')
 return bool(re.search(r'(なんて|けれど|けど|から|まで|なら|ので|のに|たら|ても|です|ます|ました|だった|だよ|よ|ね|は|を|に|で|と|も|が|て)$',text))

def make_cues(words,duration):
 """Prefer sentence/clause ends and actual pauses; don't divide by equal durations."""
 cleaned=[];prefix=''
 for w in words:
  text=str(w.get('text',''))
  if not text.strip():continue
  start=max(0,min(duration,float(w['start'])));end=max(start,min(duration,float(w['end'])))
  if cleaned:start=max(cleaned[-1]['end'],start)
  if end<=start:
   if cleaned:cleaned[-1]['text']+=text
   else:prefix+=text
   continue
  cleaned.append({'text':prefix+text,'start':start,'end':end,'probability':float(w.get('probability',1))});prefix=''
 if prefix and not cleaned:cleaned=[{'text':prefix,'start':0,'end':duration,'probability':0}]
 groups=[];pending=[]
 def flush(count=None):
  nonlocal pending
  if not pending:return
  count=count or len(pending);groups.append(pending[:count]);pending=pending[count:]
 for i,w in enumerate(cleaned):
  pending.append(w);text=normal_text(''.join(p['text'] for p in pending));span=pending[-1]['end']-pending[0]['start'];gap=cleaned[i+1]['start']-w['end'] if i+1<len(cleaned) else 0
  if re.search(r'[。！？!?][」』）)]?$',text):flush();continue
  if re.search(r'[、,]$',text) and len(text)>=5 and span>=.5:flush();continue
  if gap>=.65 or gap>=.32 and len(text)>=4 and phrase_end(text):flush();continue
  if len(text)>30 or span>5:
   candidates=[]
   for j in range(1,len(pending)):
    prefix=normal_text(''.join(p['text'] for p in pending[:j]))
    if len(prefix)>=5 and phrase_end(prefix):candidates.append(j)
   if candidates:flush(candidates[-1])
   elif len(text)>42 or span>7:flush(max(1,len(pending)-1))
 flush()
 cues=[]
 for group in groups:
  text=normal_text(''.join(w['text'] for w in group))
  if not text:continue
  start=max(0,group[0]['start']-.035);end=min(duration,group[-1]['end']+.075)
  if cues and start<cues[-1]['end']:cues[-1]['end']=max(cues[-1]['start']+.01,start)
  if end<=start:end=min(duration,start+.03)
  if end<=start:continue
  cues.append({'start':round(start,3),'end':round(end,3),'text':text,'reading':reading(text),'confidence':round(sum(w['probability'] for w in group)/len(group),3),'words':group})
 return cues

def transcribe(data,progress=lambda message:None):
 import numpy as np
 with wave.open(io.BytesIO(data),'rb') as wav:
  if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=16000:raise ValueError('認識用音声は16kHz・モノラルのWAVにしてください。')
  duration=wav.getnframes()/16000
  if not 0<duration<=300:raise ValueError('音声は5分以内にしてください。')
  audio=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
 if not len(audio) or float(np.max(np.abs(audio)))<.0001:return {'cues':[],'duration':duration,'language':'ja'}
 progress('音声認識の準備をしています…')
 model=get_model();progress('音声を聞き取り、文と発声タイミングを確認しています…')
 segments,info=model.transcribe(audio,language='ja',beam_size=5,temperature=0,condition_on_previous_text=False,word_timestamps=True,vad_filter=True,vad_parameters={'min_silence_duration_ms':350,'speech_pad_ms':120},hallucination_silence_threshold=1.0,initial_prompt='日本語の会話です。文の区切りに句読点を付けてください。')
 words=[]
 for segment in segments:
  if segment.no_speech_prob>.8 and segment.avg_logprob<-1.3:continue
  if segment.words:
   words.extend({'text':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in segment.words)
  elif segment.text.strip():words.append({'text':segment.text,'start':segment.start,'end':segment.end,'probability':math.exp(min(0,segment.avg_logprob))})
 progress('話の区切りを整え、口の読みを作っています…')
 return {'cues':make_cues(words,duration),'duration':round(duration,3),'language':info.language,'engine':'faster-whisper-small-local'}
