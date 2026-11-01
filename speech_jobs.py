"""Bounded local speech jobs so the editor stays responsive while recognition runs."""
from concurrent.futures import ThreadPoolExecutor
import secrets,threading,time
import speech
_lock=threading.Lock()
_jobs={}
_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='studio-speech')

def create(data):
 with _lock:
  now=time.monotonic()
  for key in list(_jobs):
   if _jobs[key]['status'] not in ('queued','running') and now-_jobs[key]['created']>1800:del _jobs[key]
  if sum(j['status'] in ('queued','running') for j in _jobs.values())>=3:raise ValueError('音声を処理中です。少し待ってからやり直してください。')
  key=secrets.token_urlsafe(18);_jobs[key]={'status':'queued','message':'音声認識を待っています…','created':now}
 def progress(message):
  with _lock:
   if _jobs[key]['status']!='cancelled':_jobs[key].update(status='running',message=message)
 def run():
  with _lock:
   if _jobs[key]['status']=='cancelled':return
  try:
   result=speech.transcribe(data,progress)
   with _lock:
    if _jobs[key]['status']!='cancelled':_jobs[key].update(status='done',message='文字起こしが終わりました。',result=result)
  except Exception as exc:
   message=str(exc) if isinstance(exc,ValueError) else '音声認識を開始できませんでした。初回の準備を確認し、音声を選び直すか再実行してください。'
   with _lock:
    if _jobs[key]['status']!='cancelled':_jobs[key].update(status='error',message=message)
 _executor.submit(run)
 return key

def get(key):
 with _lock:
  job=_jobs.get(key)
  return {k:v for k,v in job.items() if k!='created'} if job else None

def cancel(key):
 with _lock:
  if key not in _jobs:return False
  _jobs[key].update(status='cancelled',message='文字起こしを取り消しました。');_jobs[key].pop('result',None)
  return True
