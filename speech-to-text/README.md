# Speech-to-text

Audio → transcript via OpenAI.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
```

## Use

```python
from src import transcribe

text = transcribe("clip.mp3")            # file path
text = transcribe(raw_bytes)             # bytes
text = transcribe(open("a.wav", "rb"))   # file-like
text = transcribe("clip.mp3", language="it")  # language hint
```

Returns the transcript as a plain string. Model defaults to
`gpt-4o-mini-transcribe`; override via `STT_MODEL` env or the `model=` arg.
