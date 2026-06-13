# WER test fixtures (Phase 4 PR 4-1)

Drop sample audio here to exercise the real faster-whisper WER test on the GPU host:

- `<name>.wav` — a short English utterance (accented-English samples recommended)
- `<name>.txt` — the ground-truth reference transcript for that clip (optional;
  without it the test only asserts a non-empty transcription + correct schema)

Aim for ~5 clips. Then run on the GPU host:

```bash
RUN_GPU_TESTS=1 pytest -m gpu tests/test_whisper_faster_whisper.py -v
```

The test asserts WER ≤ 0.25 against each reference and that the response schema
(`{text, language, segments, confidence}`) is unchanged from the openai-whisper
implementation.
