"""Optional IndicXlit adapter built around BhashaBridge's injected engine contract.

This module is intentionally lazy: it does not import IndicXlit unless a caller
explicitly instantiates the adapter and invokes it. It does not download models,
perform network access, or mutate the default backend configuration.
"""

from __future__ import annotations

import importlib
import os
import unicodedata
from typing import Any, Callable


class IndicXlitAdapter:
    """Thin adapter for an optional IndicXlit engine.

    The adapter obeys the existing transliteration contract used by
    BhashaBridge's pipeline: the object exposes .engine_id and .transliterate().
    It remains disabled by default because the engine is only initialized on demand
    and only after explicit dependency injection or configuration.
    """

    def __init__(
        self,
        *,
        module_name: str = "ai4bharat.transliteration",
        engine_factory: Callable[[], Any] | None = None,
        lang_code: str = "te",
        beam_width: int = 4,
        rescore: bool = False,
        src_script_type: str = "roman",
    ) -> None:
        self.engine_id = "indicxlit-optional"
        self.version = "unverified"
        self.module_name = module_name
        self._engine_factory = engine_factory
        self._lang_code = lang_code
        self._beam_width = beam_width
        self._rescore = rescore
        self._src_script_type = src_script_type
        self._engine: Any | None = None
        self._model_loaded = False
        self._load_error: str | None = None

    def _set_runtime_identity(self, engine: Any) -> None:
        if engine is None:
            return
        try:
            runtime_id = getattr(engine, "engine_id")
        except Exception:
            runtime_id = None
        if isinstance(runtime_id, str) and runtime_id.strip():
            self.engine_id = runtime_id.strip()

        version = getattr(engine, "version", None)
        if isinstance(version, str) and version.strip():
            self.version = version.strip()
        elif version is not None:
            self.version = str(version)

    def _initialize_engine(self) -> Any | None:
        if self._engine is not None:
            return self._engine

        if self._engine_factory is not None:
            try:
                engine = self._engine_factory()
            except Exception as exc:  # pragma: no cover - defensive guard
                self._load_error = f"engine_factory raised {type(exc).__name__}."
                return None
            self._engine = engine
            self._model_loaded = engine is not None
            self._set_runtime_identity(engine)
            return engine

        try:
            module = importlib.import_module(self.module_name)
        except Exception as exc:
            self._load_error = f"module import failed ({type(exc).__name__})."
            return None

        xlit_engine = getattr(module, "XlitEngine", None)
        if xlit_engine is None:
            self._load_error = "IndicXlit exposes no XlitEngine factory."
            return None

        try:
            engine = xlit_engine(
                self._lang_code,
                beam_width=self._beam_width,
                rescore=self._rescore,
                src_script_type=self._src_script_type,
            )
        except Exception as exc:
            self._load_error = f"engine initialization failed ({type(exc).__name__})."
            return None

        self._engine = engine
        self._model_loaded = engine is not None
        self._set_runtime_identity(engine)
        return engine

    @staticmethod
    def _is_telugu_candidate(value: object) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        categories = [unicodedata.category(char)[0] for char in value]
        return (
            any(category == "L" for category in categories)
            and all(
                0x0C00 <= ord(char) <= 0x0C7F and category in {"L", "M"}
                for char, category in zip(value, categories, strict=True)
            )
        )

    @staticmethod
    def _normalize_candidate(raw: object) -> str | None:
        if raw is None:
            return None
        if isinstance(raw, dict):
            values = list(raw.values())
            if not values:
                return None
            for candidate in values:
                normalized = IndicXlitAdapter._normalize_candidate(candidate)
                if normalized is not None:
                    return normalized
            return None
        if isinstance(raw, (list, tuple, set)):
            for candidate in raw:
                normalized = IndicXlitAdapter._normalize_candidate(candidate)
                if normalized is not None:
                    return normalized
            return None
        if not isinstance(raw, str):
            return None
        value = raw.strip()
        if not value:
            return None
        return value

    def transliterate(self, text: str) -> str | None:
        """Return a validated Telugu-script candidate or None.

        This method intentionally rejects blank input, non-Telugu outputs, and
        missing dependencies without exposing internals. It represents a machine
        suggestion only and never claims a human-reviewed resource.
        """
        if not isinstance(text, str) or not text.strip():
            return None

        engine = self._initialize_engine()
        if engine is None:
            return None

        try:
            if hasattr(engine, "translit_word"):
                result = engine.translit_word(
                    text,
                    lang_code=self._lang_code,
                    topk=1,
                    transliterate_numerals=False,
                )
            elif hasattr(engine, "transliterate"):
                result = engine.transliterate(text)
            else:
                return None
        except Exception:
            return None

        candidate = self._normalize_candidate(result)
        if candidate is None:
            return None
        if not self._is_telugu_candidate(candidate):
            return None
        return candidate

    def __repr__(self) -> str:
        return (
            f"IndicXlitAdapter(engine_id={self.engine_id!r}, version={self.version!r}, "
            f"lang_code={self._lang_code!r}, model_loaded={self._model_loaded!r})"
        )
