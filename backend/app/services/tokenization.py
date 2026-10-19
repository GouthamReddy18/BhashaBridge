import unicodedata

from app.schemas.analysis import Token


def _is_word_character(character: str) -> bool:
    """Recognize Unicode letters, numbers, and combining marks in words."""
    return unicodedata.category(character)[0] in {"L", "N", "M"}


def tokenize(text: str) -> list[Token]:
    """Tokenize Unicode word spans and individual non-word symbols.

    Offsets are Python Unicode code-point positions in `text`; starts are
    inclusive and ends exclusive. Apostrophes remain inside a word only when
    surrounded by word characters. Other non-whitespace characters (including
    punctuation and symbols) are emitted individually as punctuation tokens.
    """
    tokens: list[Token] = []
    cursor = 0
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue

        start = cursor
        if _is_word_character(text[cursor]):
            cursor += 1
            while cursor < len(text):
                if _is_word_character(text[cursor]):
                    cursor += 1
                    continue
                if (
                    text[cursor] in {"'", chr(0x2019)}
                    and cursor + 1 < len(text)
                    and _is_word_character(text[cursor - 1])
                    and _is_word_character(text[cursor + 1])
                ):
                    cursor += 1
                    continue
                break
            kind = "word"
        else:
            cursor += 1
            kind = "punctuation"

        tokens.append(
            Token(
                index=len(tokens),
                text=text[start:cursor],
                start=start,
                end=cursor,
                kind=kind,
            )
        )
    return tokens
