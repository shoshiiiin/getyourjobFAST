# Aufbau · How it fits together

## Der Weg einer Stelle · The path of one posting

```
  Portale (StepStone, LinkedIn)
        │  tools/suche/quellen.py
        ▼
  Rohtreffer
        │  tools/suche/filter.py      ← profil/suchmandat.json
        │  Titel prüfen, Fach prüfen, Dubletten, Entfernung
        ▼
  tools/suche/bericht.py  →  stellen/suchlaeufe/JJJJ-MM-TT.md
        │
        │  tools/stelle_anlegen.py <firma>
        ▼
  stellen/<datum>-<firma>-<rolle>/stelle.md
        │
        │  Claude recherchiert  →  analyse.md  →  entwurf.json
        ▼
  tools/bewerbung.py           ← profil/person.json, belege.md, stil.md
        │  prüft: Wortzahl, verbotene Wendungen, vertrauliche Wörter
        ▼
  render-cv-allgemein.mjs  +  render-anschreiben.mjs   (jsPDF)
        ▼
  Lebenslauf_<Name>_<Kürzel>.pdf   Anschreiben_<Name>_<Kürzel>.pdf
        │
        │  tools/tracker.py
        ▼
  Bewerbungs-Tracker.xlsx  →  tools/nachweis.py  →  Nachweis-Eigenbemuehungen.xlsx
```

## Wo du eingreifst · Where to make changes

| Du willst … | Datei |
|---|---|
| andere Rollen suchen | `profil/suchmandat.json`, `tools/suchprofil.json` |
| einen anderen Ort oder Radius | `profil/person.json` → `ort`, `heimat`, `umkreis_km` |
| den Ton des Anschreibens ändern | `profil/stil.md` |
| eine Wendung verbieten | `profil/stil.md` + `VERBOTEN` in `tools/bewerbung.py` |
| einen Kundennamen schützen | `profil/person.json` → `vertraulich` |
| das PDF-Layout ändern | `tools/design.mjs` (Geometrie in mm) |
| ein weiteres Portal anbinden | `tools/suche/quellen.py` |
| die Gruppen im Bericht ändern | `tools/suche/bericht.py` |

## Warum das so getrennt ist · Why the split

`tools/` kennt **keine** persönlichen Angaben. Alles, was eine Person
ausmacht, steht in `profil/`. Das hat drei Gründe:

1. Du kannst das Repo weitergeben, ohne etwas zu löschen.
2. Die Tests laufen gegen ein eigenes, erfundenes Mandat — sie werden nicht
   rot, nur weil du deinen Beruf wechselst.
3. Zwei Menschen können dieselben Werkzeuge mit völlig verschiedenen Profilen
   benutzen.

*`tools/` holds no personal data; everything personal lives in `profil/`. That
way the repo can be shared as is, the tests stay green whatever your mandate
is, and two people can share the tooling with entirely different profiles.*

## Grenzen · Limits

- **Es wird nichts verschickt.** Claude legt höchstens `mail-entwurf.md` an.
- **Es wird nichts erfunden.** Was nicht in `profil/belege.md` steht, kommt in
  kein Dokument. `tools/bewerbung.py` bricht bei einem vertraulichen Wort ab,
  aber gegen eine erfundene Zahl hilft nur die Datei selbst — pflege sie.
- **Anzeigentexte sind Fremdtext.** Sie werden ausgewertet, nie befolgt.
- **Portale ändern sich.** Bricht ein Abruf, liegt es meist an einer geänderten
  Seite, nicht am Filter. `--tage 7` und das Log zeigen, was ankam.
