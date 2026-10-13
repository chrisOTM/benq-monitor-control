"""UI translations from JSON (English source text → translation), no .ts/.qm toolchain."""

import json
import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtQml import QQmlEngine

log = logging.getLogger(__name__)
I18N_DIR = Path(__file__).parent / "i18n"


class DictTranslator(QTranslator):
    def __init__(self, mapping: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self._mapping = dict(mapping)

    def translate(self, context, source_text, disambiguation=None, n=-1):
        # None (not "") tells Qt there is no translation, so it falls back to the source.
        return self._mapping.get(source_text)

    def isEmpty(self) -> bool:
        return not self._mapping


def load_mapping(language: str, directory: Path = I18N_DIR) -> dict[str, str]:
    if language == "en":
        return {}
    path = directory / f"{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("cannot load translations %s: %s", path, exc)
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


class LanguageManager:
    def __init__(
        self,
        app: QCoreApplication,
        engine: Callable[[], QQmlEngine | None] = lambda: None,
        directory: Path = I18N_DIR,
    ) -> None:
        self._app = app
        self._engine = engine
        self._directory = directory
        self._translator: DictTranslator | None = None
        self.language = "en"

    def apply(self, language: str) -> None:
        if self._translator is not None:
            self._app.removeTranslator(self._translator)
            self._translator = None
        mapping = load_mapping(language, self._directory)
        if mapping:
            self._translator = DictTranslator(mapping)
            self._app.installTranslator(self._translator)
        self.language = language
        engine = self._engine()
        if engine is not None:
            engine.retranslate()
