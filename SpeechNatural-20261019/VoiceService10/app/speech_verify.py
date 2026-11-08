"""Local speech completeness checks; no transcript is logged or persisted."""
from __future__ import annotations
import re

_DIGITS = dict(zip('零〇一二两三四五六七八九', (0,0,1,2,2,3,4,5,6,7,8,9)))
_UNITS = {'十':10,'百':100,'千':1000,'万':10000,'亿':100000000}
_CN = '零〇一二两三四五六七八九十百千万亿'

def _integer(text: str) -> int:
    total = part = number = 0
    if not any(ch in _UNITS for ch in text):
        return int(''.join(str(_DIGITS[ch]) for ch in text))
    for ch in text:
        if ch in _DIGITS:
            number = _DIGITS[ch]
        else:
            unit = _UNITS[ch]
            if unit >= 10000:
                total += (part + number) * unit; part = number = 0
            else:
                part += (number or 1) * unit; number = 0
    return total + part + number

def canonical(text: str) -> str:
    text = text.lower().replace('摄氏','').replace('百分之','')
    # Clock minutes use integer notation; do not consume 三十 as a decimal.
    text = re.sub('(['+_CN+']+)点(['+_CN+']+)分',
        lambda m:str(_integer(m[1]))+'点'+str(_integer(m[2]))+'分',text)
    text = re.sub('(['+_CN+']+)(?:点(['+_CN+']+))?',
        lambda m: str(_integer(m[1])) + ('.'+''.join(str(_DIGITS[ch]) for ch in m[2]) if m[2] and all(ch in _DIGITS for ch in m[2]) else ''), text)
    text = re.sub(r'(\d+)成',lambda m:str(int(m[1])*10)+'%',text)
    text = re.sub(r'(\d+)点半',r'\1点30分',text)
    return text

def numbers(text: str) -> list[str]:
    # Ignore the colloquial 一 in 一会儿/一下, which ASR may omit naturally.
    text = canonical(text)
    found = []
    for match in re.finditer(r'\d+(?:\.\d+)?',text):
        suffix = text[match.end():match.end()+1]
        if suffix in ('会','下'):
            continue
        found.append(str(float(match[0])))
    return found

def _key(text: str) -> str:
    text = canonical(text)
    return ''.join(ch for ch in text if '\u4e00' <= ch <= '\u9fff' and ch not in '儿点半分整')

def _lcs(a: str,b: str) -> int:
    row=[0]*(len(b)+1)
    for char in a:
        previous=0
        for j,other in enumerate(b,1):
            old=row[j];row[j]=previous+1 if char==other else max(row[j],row[j-1]);previous=old
    return row[-1]

def speech_completeness(expected: str, recognized: str) -> float:
    if not recognized.strip():
        return 0.0
    expected_numbers=numbers(expected);actual_numbers=numbers(recognized)
    if any(value not in actual_numbers for value in expected_numbers):
        return 0.0
    key=_key(expected)
    # Chinese ASR cannot reliably validate arbitrary English names. Check the
    # surrounding Chinese and numeric content, without vetoing an English word.
    return _lcs(key,_key(recognized))/len(key) if key else 1.0
