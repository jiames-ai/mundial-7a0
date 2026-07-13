from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString


ROOT = Path(__file__).resolve().parent
LOCALES = {
    "en": ("English", "en"),
    "de": ("Deutsch", "de"),
    "ja": ("日本語", "ja"),
    "pt": ("Português", "pt"),
    "es": ("Español", "es"),
    "fr": ("Français", "fr"),
    "it": ("Italiano", "it"),
    "tr": ("Türkçe", "tr"),
    "zh": ("简体中文", "zh-CN"),
}
SOURCE_FILES = [
    ROOT / "index.html",
    ROOT / "privacy" / "index.html",
    ROOT / "terms" / "index.html",
    ROOT / "contact" / "index.html",
    ROOT / "disclaimer" / "index.html",
]
COUNTRY_SOURCE_CHUNK = ROOT / "_next" / "static" / "chunks" / "3y5tmxwirstbg.js"
EXCLUDED = {
    "$", "/$", "EN", "ES", "PT", "DE", "JA", "FR", "IT", "TR", "ZH",
    "Neuer", "C. Alberto", "Beckenbauer", "Moore", "R. Carlos", "Gérson",
    "Pelé", "Maradona", "Messi", "Ronaldo", "C. Ronaldo", "X", "f", "·",
    "—", "▾", ".", "4,009", "/11",
}
DYNAMIC_STRINGS = [
    "Drawn",
    "World Cup {year}",
    "Not convinced? Reroll · {count} left",
    "Another country",
    "Another World Cup",
    "Pick one player",
    "Add to {position}",
    "Coach's report",
    "Pick available",
    "Strongest legal pick",
    "Compare top legal picks",
    "Roll a squad. The report will identify the strongest legal pick and explain how the XI is taking shape.",
    "Draft complete",
    "Simulate tournament",
    "Tournament simulation",
    "Group stage",
    "Round of 16",
    "Quarter-final",
    "Semi-final",
    "Final",
    "Champion",
    "Eliminated",
    "Your team",
    "Penalty shootout",
    "advanced",
    "eliminated",
    "average",
    "Generating image...",
    "Share image",
    "Link copied!",
    "Share link",
    "Play again",
    "Post result",
    "Replay",
    "See card",
    "Stream",
    "Settings",
    "Language",
]
SEPARATOR = "<<<SPLIT_7A0>>>"
POSITION_OVERRIDES = {
    "en": {"GOL": "GK", "LD": "RB", "ZAG": "CB", "LE": "LB", "MEI": "CM", "PD": "RW", "CA": "ST", "PE": "LW", "World Cup": "World Cup", "Drawn": "Drawn", "Roll": "Roll"},
    "de": {"GOL": "TW", "LD": "RV", "ZAG": "IV", "LE": "LV", "MEI": "ZM", "PD": "RA", "CA": "ST", "PE": "LA", "World Cup": "Weltmeisterschaft", "Drawn": "Ausgelost", "Roll": "Auslosen", "Not convinced? Reroll · {count} left": "Nicht zufrieden? Neu ziehen · noch {count}"},
    "ja": {"GOL": "GK", "LD": "RSB", "ZAG": "CB", "LE": "LSB", "MEI": "CM", "PD": "RW", "CA": "CF", "PE": "LW", "World Cup": "ワールドカップ", "Drawn": "抽選結果", "Roll": "抽選", "Not convinced? Reroll · {count} left": "納得できない？再抽選・残り{count}回"},
    "pt": {"GOL": "GOL", "LD": "LD", "ZAG": "ZAG", "LE": "LE", "MEI": "MEI", "PD": "PD", "CA": "CA", "PE": "PE", "World Cup": "Copa do Mundo", "Drawn": "Sorteado", "Roll": "Sortear", "Not convinced? Reroll · {count} left": "Não gostou? Sortear novamente · {count} restantes"},
    "es": {"GOL": "POR", "LD": "LD", "ZAG": "DFC", "LE": "LI", "MEI": "MC", "PD": "ED", "CA": "DC", "PE": "EI", "World Cup": "Copa del Mundo", "Drawn": "Sorteado", "Roll": "Sortear", "Not convinced? Reroll · {count} left": "¿No te convence? Volver a sortear · quedan {count}"},
    "fr": {"GOL": "GB", "LD": "DD", "ZAG": "DC", "LE": "DG", "MEI": "MC", "PD": "AD", "CA": "BU", "PE": "AG", "World Cup": "Coupe du monde", "Drawn": "Tirage", "Roll": "Tirer", "Not convinced? Reroll · {count} left": "Pas convaincu ? Relancer · encore {count}"},
    "it": {"GOL": "POR", "LD": "TD", "ZAG": "DC", "LE": "TS", "MEI": "CC", "PD": "AD", "CA": "ATT", "PE": "AS", "World Cup": "Coppa del Mondo", "Drawn": "Estratto", "Roll": "Estrai", "Not convinced? Reroll · {count} left": "Non ti convince? Estrai di nuovo · {count} rimasti"},
    "tr": {"GOL": "KL", "LD": "SĞB", "ZAG": "STP", "LE": "SLB", "MEI": "OS", "PD": "SĞK", "CA": "SF", "PE": "SLK", "World Cup": "Dünya Kupası", "Drawn": "Çekildi", "Roll": "Çek", "Not convinced? Reroll · {count} left": "Beğenmediniz mi? Yeniden çek · {count} hak kaldı"},
    "zh": {"GOL": "门将", "LD": "右后卫", "ZAG": "中后卫", "LE": "左后卫", "MEI": "中场", "PD": "右边锋", "CA": "中锋", "PE": "左边锋", "World Cup": "世界杯", "Drawn": "已抽取", "Roll": "抽取", "Not convinced? Reroll · {count} left": "不满意？重新抽取 · 剩余 {count} 次"},
}


def normalize(value: str) -> str:
    return " ".join(value.split())


def collect_strings() -> list[str]:
    strings: list[str] = []

    def add(value: str | None) -> None:
        if not value:
            return
        value = normalize(value)
        if not value or value in EXCLUDED or value in strings:
            return
        if value.isnumeric() or re.fullmatch(r"[0-9-]+", value):
            return
        strings.append(value)

    for path in SOURCE_FILES:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        for node in soup.descendants:
            if isinstance(node, NavigableString):
                add(str(node))
        for tag in soup.find_all(True):
            for attribute in ("aria-label", "title", "alt", "placeholder"):
                add(tag.get(attribute))
            if tag.name == "meta" and (
                tag.get("name") in {"description", "twitter:title", "twitter:description"}
                or tag.get("property") in {"og:title", "og:description"}
            ):
                add(tag.get("content"))
        add(soup.title.string if soup.title and soup.title.string else None)
    for value in DYNAMIC_STRINGS:
        add(value)
    chunk = COUNTRY_SOURCE_CHUNK.read_text(encoding="utf-8")
    for country in re.findall(r'\b[A-Z]{3}:\{en:"([^"]+)"', chunk):
        add(country)
    return strings


def protected(value: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal index
        token = f"ZXQPH{index}QXZ"
        index += 1
        placeholders[token] = match.group(0)
        return token

    return re.sub(r"\{([a-zA-Z0-9_]+)\}", replace, value), placeholders


def translate_batch(values: list[str], target: str) -> list[str]:
    safe_values: list[str] = []
    placeholder_sets: list[dict[str, str]] = []
    for value in values:
        safe, placeholders = protected(value)
        safe_values.append(safe)
        placeholder_sets.append(placeholders)
    query = f"\n{SEPARATOR}\n".join(safe_values)
    params = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "en",
        "tl": target,
        "dt": "t",
        "q": query,
    })
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                data = json.load(response)
            translated = "".join(segment[0] for segment in data[0])
            parts = [part.strip() for part in translated.split(SEPARATOR)]
            if len(parts) != len(values):
                raise RuntimeError(f"translation batch split mismatch: {len(parts)} != {len(values)}")
            result: list[str] = []
            for part, placeholders in zip(parts, placeholder_sets):
                for token, original in placeholders.items():
                    part = part.replace(token, original)
                result.append(normalize(part))
            return result
        except Exception as error:  # noqa: BLE001
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"translation failed: {last_error}")


def batches(values: list[str], max_chars: int = 3200):
    batch: list[str] = []
    size = 0
    for value in values:
        extra = len(value) + len(SEPARATOR) + 2
        if batch and size + extra > max_chars:
            yield batch
            batch = []
            size = 0
        batch.append(value)
        size += extra
    if batch:
        yield batch


def main() -> None:
    strings = collect_strings()
    output = ROOT / "i18n"
    output.mkdir(exist_ok=True)
    for locale, (native_name, target) in LOCALES.items():
        if locale == "en":
            translated = list(strings)
        else:
            translated = []
            for batch in batches(strings):
                translated.extend(translate_batch(batch, target))
                time.sleep(0.1)
        catalog = {
            "locale": locale,
            "nativeName": native_name,
            "strings": dict(zip(strings, translated, strict=True)),
        }
        catalog["strings"].update(POSITION_OVERRIDES[locale])
        (output / f"{locale}.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{locale}: {len(strings)} strings")


if __name__ == "__main__":
    main()
