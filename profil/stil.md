# Stil · Style

> **DE** — Wie ein Anschreiben klingt und was nie darin steht. `tools/bewerbung.py`
> prüft die Verbote automatisch und bricht ab, wenn eines auftaucht.
>
> **EN** — How a cover letter should read and what must never appear in it.
> `tools/bewerbung.py` enforces the bans and refuses to build on a hit.

## Ton · Tone

Kurz, konkret, ohne Floskeln. Höchstens **230 Wörter** — darüber läuft der Brief
auf Seite zwei und das Werkzeug bricht ab.

Jeder Absatz trägt eine Behauptung und einen Beleg. Zahlen vor Adjektiven:
„Durchlaufzeit um ein Drittel gesenkt" statt „deutliche Verbesserung erzielt".

Aufbau: Haken zur Firma (warum gerade die) · zwei bis drei Belege · ein
konkretes Angebot, was man in den ersten Monaten übernimmt.

## Verboten · Banned

Diese Wendungen prüft `tools/bewerbung.py` als reguläre Ausdrücke:

| Wendung | Warum |
|---|---|
| „Sehr geehrte Damen und Herren" | Zeigt, dass niemand recherchiert wurde |
| „Hiermit bewerbe ich mich" | Leerlauf, kostet die erste Zeile |
| „X bringe ich nicht mit" | Lenkt auf die Lücke statt auf die Stärke |
| „das müsste ich mir erarbeiten / lernen" | dito |
| „Ein Studium habe ich nicht" | dito |
| „Damit habe ich bisher nicht gearbeitet" | dito |
| Einstieg mit „Offen gesagt …" | Entschuldigungshaltung |

Dazu kommt jedes Wort aus `profil/person.json` → `vertraulich`: Kundennamen
unter NDA, die in keinem Dokument auftauchen dürfen.

**Die Regel dahinter:** Wer eine Anforderung nicht erfüllt, schreibt nicht
darüber. Weder entschuldigend noch trotzig. Der Platz gehört dem, was man kann.

## English

Same rules apply to English applications (`"sprache": "en"`): under 230 words,
one claim plus one piece of evidence per paragraph, no apologising for gaps.
