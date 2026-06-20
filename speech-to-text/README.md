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

## Live mode — streaming STT + concept segmentation

Streams audio in real time (OpenAI Realtime), surfaces partial transcripts in
a few hundred ms, and runs an orchestrating agent that watches the growing
transcript and **emits a trigger every time it detects a concept boundary** —
chunking the transcript by meaning and extracting semantics (topic, summary,
intent, entities) per chunk.

```python
from src import run_file
from src.agent.segmenter import ConceptChunk

def on_trigger(c: ConceptChunk):
    print(c.index, c.topic, c.entities)

await run_file("clip.mp3", on_trigger=on_trigger, language="en")
```

`run_file` callbacks: `on_partial(delta)` growing text, `on_final(text)`
finalized utterance, `on_trigger(ConceptChunk)` concept boundary.

CLI demo (paced like a live mic, colored output):

```bash
python demo_realtime.py /path/to/audio.mp3 --language en
python demo_realtime.py /path/to/audio.mp3 --no-partials --fast
```

### Pieces

| Module | Role |
|--------|------|
| `src/realtime/audio.py` | decode any file → PCM16 24kHz, paced chunks (fake live) |
| `src/realtime/transcriber.py` | OpenAI Realtime WS → partial + final events |
| `src/agent/segmenter.py` | LLM judge on finals → `ConceptChunk` triggers |
| `src/orchestrator.py` | wires stream → segmenter (`run_file`) |

Needs `ffmpeg` on PATH. Models: realtime STT `gpt-4o-transcribe` (override
`RT_STT_MODEL`); segmenting agent `gpt-4o-mini` (override `AGENT_MODEL`).
