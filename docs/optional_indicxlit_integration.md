# Optional IndicXlit integration

BhashaBridge treats IndicXlit as an optional transliteration capability, not as a required backend dependency.

## Why it is optional

- The default pipeline already works without an external transliteration model.
- The transliteration seam in the backend is disabled unless explicitly enabled.
- BhashaBridge treats transliteration results as machine-generated suggestions only, never as reviewed annotation or provenance.

## Local repository and model requirements

The local IndicXlit checkout is in `C:\Users\ADMIN\Desktop\semester5\IndicXlit`.

The repository documents a fairseq-based transliteration stack and expects model assets for the selected language/package variant. The public package entry point is:

```python
from ai4bharat.transliteration import XlitEngine
```

The actual constructor used by the project is:

```python
XlitEngine(lang2use="all", beam_width=4, rescore=True, model_type="transformer", src_script_type="roman")
```

The Telugu language target is `te` and the inference method is `translit_word(..., lang_code="te", topk=1, transliterate_numerals=False)` for word-level use.

## Compatibility limits

This repository intentionally does not install IndicXlit or its heavy model stack during normal BhashaBridge development. The default backend requirements remain unchanged.

The adapter used by BhashaBridge is only a compatibility shim. It does not initialize model assets automatically, does not fetch downloads, and does not permit network calls during startup.

## How to configure it after independent approval

After a separate environment has been approved and installed, inject the adapter explicitly when calling the analysis pipeline:

```python
from app.services.indicxlit_adapter import IndicXlitAdapter

engine = IndicXlitAdapter(lang_code="te")

analysis = analyze(
    request,
    transliteration_enabled=True,
    transliteration_engine=engine,
)
```

This keeps the default configuration off while allowing an approved, explicit integration.

## Available adapter vs loaded model

An adapter may be available as a Python object without a model being successfully loaded.

The backend distinguishes between:

- adapter/object presence
- safe, valid output generation
- actual engine identity and version metadata, when available

A successfully loaded model is never assumed from an import alone.

## Human-review boundary

Any model output remains a machine suggestion only. It does not replace human annotation, provenance, or reviewer validation. BhashaBridge still requires reviewer evidence and promotion gates before research evaluation.
