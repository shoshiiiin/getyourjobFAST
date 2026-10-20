# getyourjob

**Ein Bewerbungssystem, das sucht, prüft und schreibt — und bei dem du auf
„Senden" drückst.**
*A job-application system that searches, checks and writes — you press send.*

[Deutsch](#deutsch) · [English](#english)

---

## Deutsch

Jeden Werktagmorgen laufen die Portale durch. Was zum eigenen Mandat passt,
landet in einem lesbaren Bericht. Sagst du Claude „Bewerbung für Muster GmbH",
entsteht daraus eine Analyse der Anzeige, ein Anschreiben nach deinen
Stilregeln, ein auf die Stelle zugeschnittener Lebenslauf als PDF und ein
Mail-Entwurf. Der Tracker führt Buch, und für die Agentur für Arbeit fällt der
Nachweis der Eigenbemühungen per Knopfdruck ab.

**Zwei Dinge macht das System bewusst nicht:** Es verschickt nichts, und es
erfindet nichts. Jede Zahl in einem Anschreiben muss in `profil/belege.md`
stehen, sonst bricht der Bau ab.

### Was es kann

**Suchen**

- Werktäglicher Suchlauf über StepStone und LinkedIn (lokal und remote),
  automatisch um 7:30 per LaunchAgent
- Filtert nach deinem Mandat: Wunschrollen, Ausschlussrollen, fremde
  Fachgebiete — alles Konfiguration, nichts davon steht im Code
- Zählt im Volltext, wie oft dein Fachgebiet vorkommt; eine allgemein
  betitelte Stelle zählt nur, wenn die Anzeige das Thema wirklich trägt
- Wirft vorher raus: Personaldienstleister, Firmen aus deinem Tracker und
  jede Anzeige, die ein früherer Lauf schon gesehen hat
- Rechnet die Luftlinie zu deinem Wohnort und liest den Anzeigentext darauf,
  ob Home-Office wirklich zugesagt wird oder nur im Portalfilter steht
- Gruppiert nach Sicherheit der Angabe: zugesagtes Home-Office · im Umkreis ·
  „remote" nur laut Filter · Ort unklar
- Optionale KI-Vorsortierung der Treffer

**Analysieren**

- Recherchiert die Firma und schreibt eine Fit-Analyse:
  Anforderung ↔ dein Beleg ↔ Stärke, Zeile für Zeile
- Zieht die Anforderungen **wörtlich** aus der Anzeige — mit deren eigenen
  Begriffen, nicht umformuliert. Dadurch steht die Sprache der Anzeige
  anschließend in Anschreiben und Lebenslauf: dieselben Schlagworte,
  dieselben Rollenbezeichnungen, dieselben Werkzeugnamen
- **Aber kein Keyword-Stuffing.** Ein Begriff, den deine Belege nicht decken,
  kommt nicht hinein — er bleibt in der Analyse als offener Punkt stehen.
  Das ist der Unterschied zwischen „für den Bewerbungsroboter optimiert" und
  „im Gespräch verteidigbar"

**ATS-Abgleich**

Viele Firmen lassen Bewerbungen zuerst durch ein Applicant Tracking System
laufen, das auf die Begriffe der Anzeige hin vergleicht. Nach jedem Bau sagt
dir eine Zeile, wie es darum steht:

```
ATS: 71 % der Anzeigenbegriffe in den Unterlagen, 2 belegte Lücke(n)
```

Den ganzen Abgleich zeigt:

```bash
tools/.venv/bin/python tools/ats.py stellen/<ordner>
```

Er teilt die Begriffe der Anzeige in drei Gruppen:

| Gruppe | Bedeutung |
|---|---|
| **in deinen Unterlagen** | steht schon drin |
| **fehlt, obwohl belegt** | `belege.md` oder `master-cv.md` decken den Begriff — **hier lohnt eine Änderung** |
| **fehlt und ist nicht belegt** | bleibt draußen, und das ist richtig so |

Die dritte Gruppe ist der Punkt. Ein Keyword-Werkzeug, das dir sagt „bau noch
‚SAP' ein", macht dich im Gespräch angreifbar. Dieses sagt dir, *welche*
fehlenden Begriffe du ehrlich nachtragen kannst — und welche du bewusst
stehen lässt.
- Benennt Risiken, Bewerbungsweg und Frist
- Vergibt eine Passung von 0 bis 100, die im Tracker landet

**Schreiben**

- Anschreiben nach deinen eigenen Stilregeln, höchstens 230 Wörter
- Lebenslauf je Stelle zugeschnitten: Positionierung, Kernkompetenzen und
  welche Bullets überhaupt auftauchen
- Beides als PDF in einem eigenen Layout, mit Foto
- Deutsch oder Englisch
- Mail-Entwurf mit Betreff, Versandtext und Anlagenliste

**Prüfen — hier wird es ernst**

Der Bau bricht ab, statt etwas Schlechtes zu liefern:

- wenn der Brief zu lang ist oder auf Seite 2 läuft
- bei verbotenen Wendungen („Sehr geehrte Damen und Herren", „hiermit bewerbe
  ich mich", „das müsste ich mir noch erarbeiten")
- wenn ein vertrauliches Wort auftaucht — etwa ein Kundenname unter NDA
- und nichts kommt ins Dokument, was nicht in deinen Belegen steht

**Nachhalten**

- Tracker als Excel, Status von „Vorbereitet" bis „Angebot"
- Nachweis der Eigenbemühungen für die Agentur für Arbeit auf Knopfdruck,
  ohne Daten und interne Notizen
- Gesprächsvorbereitung als PDF

**Was es bewusst nicht tut**

- **Es verschickt nichts.** Nie. Auf „Senden" drückst du.
- **Es erfindet nichts.** Keine Zahl ohne Beleg.
- **Es lädt nichts hoch.** Alles läuft lokal. Kein Konto, kein Abo, keine
  Daten auf fremden Servern.

### Womit ich es selbst benutzt habe

Ich habe das System für meine eigene Jobsuche gebaut. Stand Oktober 2026:

| | |
|---|---|
| Bewerbungen versendet | **13** |
| daraus Gespräche | **3** |
| davon noch laufend | **2** — die Entscheidung steht aus |

Das sind meine Zahlen, kein Versprechen. Was ein Anschreiben taugt, hängt an
den Belegen, die du hineingibst, nicht am Werkzeug. Was das System leistet:
Jede Bewerbung ist einzeln auf die Anzeige zugeschnitten statt dreißigmal
dieselbe — und das in Minuten statt in Stunden.

### In fünf Minuten startklar

```bash
git clone https://github.com/shoshiiiin/getyourjobFAST.git
cd getyourjobFAST
```

Dann in Claude Code:

```
/einfuehrung
```

Claude fragt dich nach Beruf, Stadt, Suchradius und Wunschrollen, schreibt
daraus dein Profil und baut zum Schluss eine Probe-Bewerbung, die du ansehen
kannst. Dauert etwa zehn Minuten.

**Ohne Claude Code** geht es genauso:

```bash
/opt/homebrew/bin/python3.11 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
npm install
tools/.venv/bin/python tools/einrichten.py
```

### Vorher ansehen, was herauskommt

Das Repo bringt eine vollständig durchgespielte Beispielbewerbung mit —
erfundene Person, erfundene Firma. Bauen kannst du sie sofort:

```bash
tools/.venv/bin/python tools/bewerbung.py stellen/2026-10-20-muster-projektmanager-digitalisierung --ohne-tracker
```

Danach liegen `Anschreiben_Alex_Beispiel_MUSTER.pdf` und
`Lebenslauf_Alex_Beispiel_MUSTER.pdf` im Ordner. So sieht das Ergebnis aus,
bevor du eine einzige eigene Zeile geschrieben hast.

### Der tägliche Suchlauf

```bash
tools/.venv/bin/python tools/stellensuche.py --tage 7
```

Quellen sind StepStone im Umkreis deines Orts sowie LinkedIn lokal und remote.
Vorher fliegen raus: Titel, die nicht zum Mandat passen, Personaldienstleister
(`tools/suche/ausschluss.json`), Firmen, bei denen du schon beworben bist, und
alles, was ein früherer Lauf schon gesehen hat.

Der Bericht gruppiert nach Sicherheit der Ortsangabe:

| Gruppe | Bedeutung |
|---|---|
| **A** | Home-Office, im Anzeigentext ausdrücklich zugesagt |
| **B** | Höchstens `umkreis_km` von deinem Ort (Luftlinie) |
| **C** | Remote nur laut LinkedIn-Filter — unzuverlässig, vorher klären |
| **D** | Ort nicht bestimmbar |

Täglich automatisch (Mo–Fr 7:30, macOS):

```bash
tools/launchd/install.sh
```

### Eine Bewerbung bauen

1. **Stelle anlegen** — `tools/.venv/bin/python tools/stelle_anlegen.py <firma>`
   nimmt den jüngsten Suchlauf und legt `stellen/<datum>-<firma>-<rolle>/stelle.md` an.
2. **Analysieren** — Claude recherchiert die Firma und schreibt `analyse.md`:
   Aufgabe wörtlich, Tabelle Anforderung ↔ Beleg ↔ Stärke, Risiken,
   Bewerbungsweg, Frist und eine Zeile „Passung NN von 100".
3. **Entwerfen** — `entwurf.json` mit Brief und Lebenslaufauswahl
   (Format im Kopf von `tools/bewerbung.py`).
4. **Bauen** — `tools/.venv/bin/python tools/bewerbung.py stellen/<ordner>`
   prüft Wortzahl und verbotene Wendungen, rendert beide PDFs und trägt die
   Stelle als „Vorbereitet" in den Tracker ein.
5. **Senden** — von dir, nicht vom System.

### Was wo steht

| Datei | Inhalt |
|---|---|
| `profil/person.json` | **Die einzige Datei mit deinen persönlichen Daten.** Name, Kontakt, Anschrift, Ort, Suchradius |
| `profil/suchmandat.json` | Welche Stellentitel zählen (reguläre Ausdrücke) |
| `profil/mandat.md` | Die Regeln deiner Suche in Worten |
| `profil/belege.md` | **Jede Zahl, die behauptet werden darf.** Fehlt sie hier, kommt sie in kein Dokument |
| `profil/stil.md` | Ton und verbotene Wendungen |
| `profil/master-cv.md` | Die vollständige Laufbahn als Fließtext |
| `profil/lebenslauf-allgemein.json` | Der Lebenslauf als Daten (ohne Identität) |
| `tools/suchprofil.json` | Suchbegriffe für die Portale |
| `tools/ats.py` | Begriffsabgleich Anzeige ↔ Unterlagen ↔ Belege |

### Umgebungsvariablen

Lege bei Bedarf eine Datei `.env.local` im Projektordner an:

```
TYPESAFE_API_KEY=
```

Optional. Ist der Schlüssel gesetzt, sortiert [Jev](https://typesafe.sh) die
Treffer eines Suchlaufs vor und schreibt `<suchlauf>.jev.json`. Ohne Schlüssel
läuft alles normal weiter, nur ohne Vorsortierung. **Jev ist eine Vorauswahl,
keine Bewertung** — die Passung entsteht weiter in `analyse.md`.

### Voraussetzungen

Python 3.11+, Node 20+, macOS oder Linux. Der automatische Suchlauf per
LaunchAgent und die Display-Schrift (Arial Black) sind macOS-spezifisch; ohne
sie fällt das Layout auf Helvetica zurück.

### Tests

```bash
tools/.venv/bin/python -m unittest discover -s tools/test
node --test tools/jev/lib.test.mjs
```

### Fallstricke

- Das Bewerbungsfoto gehört nach `profil/anlagen/bewerbungsfoto.jpg`
  (JPEG, 675 × 900). Fehlt es, entstehen die PDFs ohne Foto, mit Warnung.
- jsPDF kann nur WinAnsi — Pfeile und mathematische Zeichen vermeiden.
- Das Anschreiben darf nicht auf Seite 2 laufen. Über 230 Wörter bricht der
  Bau ab, und das ist Absicht.

---

## English

Every weekday morning the job boards get scanned. Whatever fits your mandate
lands in a readable report. Tell Claude "application for Muster GmbH" and you
get an analysis of the posting, a cover letter following your own style rules,
a CV tailored to that role as a PDF, and a draft email. A tracker keeps the
books.

**Two things the system deliberately does not do:** it sends nothing, and it
invents nothing. Every number in a cover letter must appear in
`profil/belege.md`, or the build refuses to run.

### What it does

**Finding**

- A weekday search across StepStone and LinkedIn (local and remote),
  scheduled at 07:30
- Filters by your mandate: target roles, excluded roles, unrelated fields —
  all configuration, none of it in the code
- Drops staffing agencies, companies already in your tracker, and every
  posting an earlier run has seen
- Measures the straight-line distance to your city and reads the posting text
  to tell a real remote promise from a portal checkbox
- Groups by how certain the location is: promised remote · within range ·
  "remote" per filter only · unclear

**Analysing**

- Researches the company and writes a fit analysis:
  requirement ↔ your evidence ↔ strength, line by line
- Lifts the requirements **verbatim** from the posting — its own wording, not
  a paraphrase. The posting's vocabulary therefore ends up in your letter and
  CV: the same keywords, role names and tool names
- **But no keyword stuffing.** A term your evidence does not cover never gets
  in; it stays in the analysis as an open point. That is the difference
  between "optimised for the applicant-tracking system" and "defensible in
  the interview"

**ATS check**

Every build ends with a line telling you how many of the posting's terms made
it into your documents. The full breakdown:

```bash
tools/.venv/bin/python tools/ats.py stellen/<folder>
```

It sorts the posting's terms into three groups: already in your documents ·
**missing although your evidence covers it** (worth fixing) · missing and not
covered (stays out, and rightly so). A keyword tool that tells you to "add
SAP" makes you vulnerable in the interview. This one tells you which missing
terms you can honestly add — and which to leave alone.
- Names the risks, the application route and the deadline
- Scores the fit from 0 to 100, which lands in the tracker

**Writing**

- A cover letter following your own style rules, 230 words maximum
- A CV cut to each role: positioning, core competencies, and which bullets
  appear at all
- Both as PDFs in their own layout, with a photo
- German or English
- A draft email with subject, body and attachment list

**Refusing**

The build stops rather than shipping something weak:

- if the letter runs long or spills onto page two
- on banned phrases (the German equivalents of "To whom it may concern" and
  "I hereby apply")
- if a confidential word appears — a client under NDA, say
- and nothing reaches a document that is not in your evidence file

**Keeping track**

- An Excel tracker, status from "prepared" to "offer"
- A one-click record of applications for the German employment agency,
  stripped of dates and internal notes
- Interview preparation as a PDF

**What it deliberately does not do**

- **It sends nothing.** Ever. You press send.
- **It invents nothing.** No number without evidence.
- **It uploads nothing.** Everything runs locally. No account, no
  subscription, no data on someone else's servers.

### How it has gone for me

I built this for my own job search. As of October 2026:

| | |
|---|---|
| Applications sent | **13** |
| Interviews from those | **3** |
| Still open | **2** — decision pending |

Those are my numbers, not a promise. How good a letter is depends on the
evidence you put in, not on the tool. What the system does give you: every
application is cut to that one posting instead of the same text thirty times
over — in minutes rather than hours.

### Up and running in five minutes

```bash
git clone https://github.com/shoshiiiin/getyourjobFAST.git
cd getyourjobFAST
```

Then in Claude Code:

```
/einfuehrung
```

Claude interviews you about your field, city, search radius and target roles,
writes your profile from the answers, and finishes by building a sample
application you can look at. Takes about ten minutes.

**Without Claude Code** it works the same way:

```bash
python3.11 -m venv tools/.venv
tools/.venv/bin/pip install -r tools/requirements.txt
npm install
tools/.venv/bin/python tools/einrichten.py
```

### See the output first

The repo ships one fully worked example — fictional person, fictional company.
Build it right away:

```bash
tools/.venv/bin/python tools/bewerbung.py stellen/2026-10-20-muster-projektmanager-digitalisierung --ohne-tracker
```

Two PDFs appear in that folder. That is what the output looks like before you
have written a single line of your own.

### A note on language

The system targets the German job market: StepStone, German cover-letter
conventions, and the *Nachweis der Eigenbemühungen* that the German employment
agency asks for. Interface and documentation are bilingual; set
`"sprache": "en"` in a draft to produce an English CV and cover letter from
`profil/lebenslauf-allgemein-en.json`.

### Where things live

| File | Holds |
|---|---|
| `profil/person.json` | **The only file with your personal details.** Name, contact, address, city, search radius |
| `profil/suchmandat.json` | Which job titles count (regular expressions) |
| `profil/mandat.md` | The rules of your search, in prose |
| `profil/belege.md` | **Every number you are allowed to claim.** Not here means not in any document |
| `profil/stil.md` | Tone and banned phrases |
| `profil/master-cv.md` | Full career history in prose |
| `profil/lebenslauf-allgemein.json` | The CV as data (no identity) |
| `tools/suchprofil.json` | Search terms for the job boards |

### Requirements

Python 3.11+, Node 20+, macOS or Linux. The scheduled search (LaunchAgent) and
the display font (Arial Black) are macOS-specific; without them the layout
falls back to Helvetica.

---

## Lizenz · License

MIT. Siehe [LICENSE](LICENSE).

Die Beispielperson „Alex Beispiel", alle Firmen und alle Zahlen in diesem Repo
sind frei erfunden. *The example person, companies and figures are fictional.*
