#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import imageio_ffmpeg, faster_whisper, fugashi, unidic_lite' >/dev/null 2>&1; then
  echo '動画保存と自動字幕の準備をしています（初回のみ）…'
  .venv/bin/python -m pip install -r requirements.txt || echo '自動機能の準備ができませんでした。利用可能な機能で起動します。'
fi
if .venv/bin/python -c 'import faster_whisper, fugashi, unidic_lite' >/dev/null 2>&1; then
  .venv/bin/python tools/prepare_speech.py || echo '音声認識の初回準備を完了できませんでした。字幕は手でも編集できます。'
fi
exec .venv/bin/python server.py "$@"
