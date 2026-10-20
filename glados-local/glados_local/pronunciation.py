"""Experimental Japanese reading -> English pseudo spelling; not native Japanese TTS."""
import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache
from pykakasi import kakasi

DICT = Path(__file__).resolve().parents[1] / 'pronunciation.json'
# The English phonemizer has 64 input slots: start/end + three per letter.
MAX_PSEUDO_WORD = (64 - 2) // 3


def normalize_quotes(text):
    # Quotes mark dialogue, not spoken words. Keep word boundaries when removing them.
    text = text.translate(str.maketrans({c: ' ' for c in '\"“”„‟«»‹›「」『』〝〞〟″‶'}))
    text = text.translate(str.maketrans({c: "'" for c in '‘’‚‛′‵ʼ'}))
    # Preserve contractions/possessives such as don't and GLaDOS's.
    text = re.sub(r"(?<![A-Za-z])'|'(?![A-Za-z])", ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def split_long_pseudo_words(text):
    """Bound generated words without dropping letters or splitting vowel groups."""
    def split(match):
        word = match[0]
        if len(word) <= MAX_PSEUDO_WORD:
            return word
        # Approximate syllable boundaries in expanded spellings (ah/ee/oo/etc.).
        units = re.findall(r'[^aeiou]*(?:ah|eh|ee|oh|oo|[aeiou])|[^aeiou]+$',
                           word, re.IGNORECASE)
        chunks, current = [], ''
        for unit in units:
            if current and len(current) + len(unit) > MAX_PSEUDO_WORD:
                chunks.append(current)
                current = ''
            # Custom dictionary entries may contain a single oversized unit.
            while len(unit) > MAX_PSEUDO_WORD:
                chunks.append(unit[:MAX_PSEUDO_WORD])
                unit = unit[MAX_PSEUDO_WORD:]
            current += unit
        if current:
            chunks.append(current)
        return ' '.join(chunks)
    return re.sub(r'[a-zA-Z]+', split, text)


@lru_cache(maxsize=1)
def reader():
    return kakasi()


def parse_dictionary(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or any(not isinstance(k, str) or not k or
            not isinstance(v, str) or not v.strip() or not v.isascii() for k, v in data.items()):
        raise ValueError('辞書は {"日本語": "ASCII pseudo spelling"} 形式で指定してください。')
    return data


def preview(text, language='en', dictionary=None):
    text = unicodedata.normalize('NFKC', text).strip()
    if not text or len(text) > 4000:
        raise ValueError('1セリフは1～4000文字で入力してください。')
    text = normalize_quotes(text)
    if not text:
        raise ValueError('引用符以外の読み上げる文章を入力してください。')
    if language == 'en':
        if not text.isascii():
            raise ValueError('日本語を含む場合はjaを選択してください。')
        return text
    if language != 'ja':
        raise ValueError('language must be en or ja')
    mapping = dictionary if dictionary is not None else parse_dictionary(DICT.read_text(encoding='utf-8'))
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))) if mapping else None
    def romanize(segment):
        words = []
        for token in reader().convert(segment):
            if token['orig'].isascii():
                words.append(token['orig'])
                continue
            word = token['hepburn'].lower()
            # Vowels use English-friendly spellings. Consonants remain approximations.
            word = re.sub(r'[aeiou]', lambda m: {'a':'ah','e':'eh','i':'ee','o':'oh','u':'oo'}[m[0]], word)
            words.append(word)
        return ' '.join(words)
    parts, start = [], 0
    if pattern:
        for match in pattern.finditer(text):
            parts.extend([romanize(text[start:match.start()]), mapping[match[0]]])
            start = match.end()
    parts.append(romanize(text[start:]))
    result = ' '.join(parts).translate(str.maketrans({'。':'.','、':',','！':'!','？':'?','「':'','」':''}))
    result = re.sub(r'\s+', ' ', result).strip()
    if not result.isascii():
        raise ValueError('変換できない文字があります。辞書に読みを登録してください。')
    return split_long_pseudo_words(result)
