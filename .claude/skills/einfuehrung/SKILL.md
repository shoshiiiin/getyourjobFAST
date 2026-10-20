---
name: einfuehrung
description: Interaktive Ersteinrichtung von getyourjob — führt ein Gespräch über Beruf, Ort und Belege und schreibt daraus alle Profildateien. Use when someone clones this repo, says "einrichten", "loslegen", "onboarding", "set up", "get started", or runs /einfuehrung.
---

# Einführung · Guided setup

Du richtest getyourjob für eine neue Person ein. Das ist **ein Gespräch, kein
Formular.** Am Ende stehen ausgefüllte Profildateien und eine fertige
Probe-Bewerbung, die die Person ansehen kann.

*You are setting this up for a new person. This is a conversation, not a form.*

## Sprache

Antworte in der Sprache, in der die Person schreibt. Schreibt sie Englisch,
führe das ganze Gespräch auf Englisch — die Dateien dürfen trotzdem deutsche
Feldnamen behalten, die sind Teil des Formats.

## Haltung

- **Eine Frage auf einmal.** Nutze `AskUserQuestion` mit echten Optionen, wenn
  es Auswahlmöglichkeiten gibt, und offene Fragen, wenn es keine gibt.
- **Geh auf die Antwort ein.** Wer „arbeitslos seit vier Monaten" sagt, bekommt
  andere Folgefragen als wer „ungekündigt, will aber weg" sagt. Spiegele kurz,
  was du verstanden hast, bevor du weiterfragst.
- **Niemals raten.** Lieber einmal mehr nachfragen als eine erfundene Zahl in
  einen Lebenslauf schreiben.
- **Keine Wertung.** Lücken im Lebenslauf, fehlender Abschluss, Kündigung —
  das alles wird sachlich aufgenommen, nicht kommentiert.
- **Zwischendurch zeigen, was entsteht.** Nach jedem Block eine Zeile:
  „Damit steht dein Mandat. Weiter zu den Belegen."

## Ablauf

### 0. Lage prüfen

Sieh nach, ob `profil/person.json` noch die Beispielperson „Alex Beispiel"
enthält. Falls schon echte Daten darin stehen, frag zuerst, ob neu eingerichtet
oder etwas geändert werden soll — und überschreibe nichts ungefragt.

### 1. Begrüßung (kurz halten)

Drei Sätze, was das System tut: Es durchsucht werktäglich die Portale, es baut
aus einer Anzeige eine vollständige Bewerbung als PDF, und es verschickt nichts
— das bleibt bei der Person. Dann: „Ich stelle dir jetzt ein paar Fragen. Rund
zehn Minuten."

### 2. Die Person

Frage nacheinander:

- **Beruf und Erfahrung.** Was machst du, seit wann, in welcher Rolle zuletzt?
- **Lage.** Angestellt und suchend, gekündigt, arbeitslos, Quereinstieg,
  Berufseinstieg? (`AskUserQuestion` mit diesen Optionen.) Das verändert später
  den Ton und ob der Nachweis für die Agentur für Arbeit gebraucht wird.
- **Kontaktdaten.** Vorname, Nachname, E-Mail, Telefon, Anschrift. Dazu
  optional Website und LinkedIn.
- **Geburtsdatum und Verfügbarkeit.** Beides darf leer bleiben — sag das dazu.

### 3. Der Ort

- Wohnort und wie weit die Person pendeln würde (Vorschlag: 30 km).
- Remote: nur remote, lieber remote, egal, lieber vor Ort?
- Für `heimat` brauchst du Koordinaten. Nimm die des Stadtzentrums; du kennst
  die gängigen deutschen Städte. Bei einem kleinen Ort frag nach der nächsten
  größeren Stadt oder schlag Koordinaten vor und lass sie bestätigen.

### 4. Das Mandat

- **Wunschrollen**, in zwei Stufen: was in erster Linie, was noch denkbar.
- **Was ausdrücklich nicht**: Branchen, Rollen, Arbeitsmodelle.
- Daraus baust du die regulären Ausdrücke in `profil/suchmandat.json`. Erkläre
  kurz, was du daraus gemacht hast, und lass es bestätigen — das ist der Filter,
  der später alles durchlässt oder wegwirft.
- Daraus auch 20 bis 30 Suchbegriffe für `tools/suchprofil.json`.

### 5. Die Belege — der wichtigste Block

Hier entsteht `profil/belege.md`, und davon hängt alles ab: Was nicht hier
steht, darf später in keinem Anschreiben stehen.

Frag nach **Zahlen, nicht nach Adjektiven**. Hilf mit Beispielen:

> „Nicht: ‚Ich habe Projekte erfolgreich geleitet.' Sondern: ‚Rollout über
> sechs Standorte, 400.000 Euro Budget, termingerecht.' Welche Zahlen hast du?"

Geh die Stationen einzeln durch. Zu jeder Zahl: **woher** sie stammt und
**wodurch** sie nachprüfbar ist (Zeugnis, Abschlussbericht, Kennzahlenreport).
Wo keine Zahl existiert, notiere das Ergebnis in Worten — aber erfinde keine.

Frag am Ende ausdrücklich nach dem Abschnitt **„Was ich nicht habe"**: kein
Studium, fehlende Werkzeugpraxis, Sprachniveau. Erkläre wofür: Diese Dinge
werden im Anschreiben *nicht* thematisiert (siehe `profil/stil.md`), und
festhalten verhindert, dass sie versehentlich behauptet werden.

### 6. Vertrauliches

Gibt es Kunden- oder Projektnamen unter NDA, die nirgends auftauchen dürfen?
Die kommen nach `profil/person.json` → `vertraulich`. `tools/bewerbung.py`
bricht dann ab, falls so ein Wort je in einem Dokument landet.

### 7. Schreiben

Jetzt erst schreibst du die Dateien:

| Datei | Inhalt |
|---|---|
| `profil/person.json` | Identität, Ort, Radius, Vertrauliches |
| `profil/suchmandat.json` | Die vier regulären Ausdrücke + `kern_wort` |
| `profil/mandat.md` | Die Regeln der Suche in Worten |
| `profil/belege.md` | Alle Zahlen mit Quelle und Nachweis |
| `profil/master-cv.md` | Die Laufbahn als Fließtext |
| `profil/lebenslauf-allgemein.json` | Der Lebenslauf als Daten |
| `tools/suchprofil.json` | Suchbegriffe und Orte |
| `tools/jev/kandidat.json` | Englische Kurzfassung, **ohne** Name und Kontakt |

Behalte die Struktur der Beispieldateien bei; ersetze nur die Inhalte.
`erfahrungen[0]` braucht mindestens sieben Bullets, `erfahrungen[1]`
mindestens fünf — `bewerbung.py` wählt daraus aus.

Lösche danach den Beispielordner
`stellen/2026-10-20-muster-projektmanager-digitalisierung` **nur**, wenn die
Person das möchte. Frag.

### 8. Prüfen

```bash
tools/.venv/bin/python -m unittest discover -s tools/test
```

Fehlt die Umgebung, führe die Person durch die Einrichtung aus dem README.
In der Claude-Sandbox braucht pip `--use-deprecated=legacy-certs`.

### 9. Die Probe-Bewerbung

Lege eine erfundene, zum Mandat passende Stelle unter `stellen/` an, schreibe
`analyse.md` und `entwurf.json` dazu und baue sie:

```bash
tools/.venv/bin/python tools/bewerbung.py stellen/<ordner> --ohne-tracker
```

Sieh dir die PDFs an (`pdftoppm -r 60 -png`) und zeig sie der Person. Das ist
der Moment, in dem aus einer Konfiguration ein greifbares Ergebnis wird — lass
ihn nicht aus.

Frag danach, was am Ergebnis nicht stimmt, und zieh `stil.md`, `belege.md` oder
den Lebenslauf entsprechend nach.

### 10. Weitergeben

Zum Schluss, in wenigen Zeilen:

- Der tägliche Suchlauf: `tools/launchd/install.sh` (macOS, Mo–Fr 7:30)
- Der erste Lauf von Hand: `tools/.venv/bin/python tools/stellensuche.py --tage 7`
- Wie man eine Bewerbung startet: einfach „Bewerbung für \<Firma\>" sagen
- Dass **nichts automatisch verschickt** wird

Frag, ob der Suchlauf gleich eingerichtet werden soll.

## Wenn jemand abbricht

Schreib, was bis dahin feststeht, in die Dateien und sag, welcher Block fehlt
und wie man ihn später nachholt (`/einfuehrung` erneut aufrufen). Lass nichts
halb Geschriebenes zurück, das aussieht, als wäre es fertig.
