#!/usr/bin/env python3
"""Loopback-only static app with optional local WebM -> MP4 conversion."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse, json, os, shutil, subprocess, tempfile, webbrowser, math
from urllib.parse import urlsplit
import speech, speech_jobs
ROOT = Path(__file__).resolve().parent
PUBLIC_WEB_ORIGIN='https://mario335599-boop.github.io'

def ffmpeg_path():
    found = shutil.which('ffmpeg')
    if found: return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
    def allowed_origin(self):
        host=self.headers.get('Host','')
        try: hostname=urlsplit('http://'+host).hostname
        except ValueError: return False
        return hostname in ('127.0.0.1','localhost','::1') and self.headers.get('Origin') in (None,'null','http://'+host,PUBLIC_WEB_ORIGIN)
    def end_headers(self):
        if self.headers.get('Origin') in ('null',PUBLIC_WEB_ORIGIN) and (self.path in ('/capabilities','/transcribe','/reading','/convert') or self.path.startswith('/transcribe/')):
            self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
            self.send_header('Vary','Origin')
        super().end_headers()
    def json_response(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_OPTIONS(self):
        if not self.allowed_origin():self.send_error(403);return
        self.send_response(204);self.send_header('Access-Control-Allow-Private-Network','true');self.send_header('Access-Control-Allow-Methods','GET, POST, DELETE, OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type, X-Studio-Client, X-Video-Duration');self.end_headers()
    def do_DELETE(self):
        if not self.allowed_origin():self.send_error(403);return
        if self.path.startswith('/transcribe/'):
            self.json_response({'cancelled':speech_jobs.cancel(self.path.split('/')[-1])})
        else:self.send_error(404)
    def do_GET(self):
        if not self.allowed_origin():self.send_error(403);return
        if self.path.startswith('/transcribe/'):
            result=speech_jobs.get(self.path.split('/')[-1]);self.json_response(result or {'message':'認識結果が見つかりません。'},200 if result else 404);return
        if self.path == '/capabilities':
            data = json.dumps({'mp4': bool(ffmpeg_path()),'transcription':speech.available(),'reading':speech.available()}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(data)
        elif self.path.startswith(('/.venv','/.git','/.models','/server.py','/speech.py','/speech_jobs.py','/start.sh','/__pycache__')):
            self.send_error(404)
        else: super().do_GET()
    def do_POST(self):
        if not self.allowed_origin():self.send_error(403);return
        if self.path in ('/transcribe','/reading'):
            if not speech.available():self.json_response({'message':'自動字幕の準備が必要です。起動ファイルから開き直してください。'},503);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=(2_100_000 if self.path=='/transcribe' else 16000):raise ValueError('音声や文章の容量を確認してください。')
                data=self.rfile.read(size)
                if self.path=='/reading':
                    text=json.loads(data).get('text','')
                    if not isinstance(text,str) or len(text)>2000:raise ValueError('文章は2000文字以内にしてください。')
                    self.json_response({'reading':speech.reading(text)})
                else:self.json_response({'id':speech_jobs.create(data)},202)
            except (ValueError,KeyError,json.JSONDecodeError) as e:self.json_response({'message':str(e)},400)
            except Exception:self.json_response({'message':'読みの生成に失敗しました。読み欄を直接修正できます。'},503)
            return
        if self.path != '/convert': self.send_error(404); return
        binary = ffmpeg_path()
        if not binary: self.send_error(503, 'MP4 encoder unavailable'); return
        try:
            size = int(self.headers.get('Content-Length','0'))
            duration = float(self.headers.get('X-Video-Duration','0'))
            if not 0 < size <= 120_000_000 or not math.isfinite(duration) or not 0 < duration <= 60.1:
                self.send_error(400); return
            with tempfile.TemporaryDirectory(prefix='kaman-') as temp:
                src, dst = Path(temp)/'input.webm', Path(temp)/'output.mp4'
                src.write_bytes(self.rfile.read(size))
                p = subprocess.run([binary,'-v','error','-y','-i',str(src),'-t',str(duration),'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-vf','fps=30','-c:a','aac','-b:a','192k','-movflags','+faststart',str(dst)], capture_output=True, timeout=120)
                if p.returncode: self.send_error(422, 'Video conversion failed'); return
                data=dst.read_bytes()
            self.send_response(200);self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        except (ValueError, subprocess.TimeoutExpired): self.send_error(400, 'Invalid or timed out conversion')
    def log_message(self, format, *args): pass

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8768);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print('口パクスタジオ: '+url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
