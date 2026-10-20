# Muster · Templates

Zwei fertige Eingabedateien für die Renderer — genau das, was
`tools/bewerbung.py` aus einem `entwurf.json` erzeugt. Nützlich, wenn du das
Layout ändern willst, ohne jedes Mal eine ganze Bewerbung zu bauen:

```bash
node tools/render-anschreiben.mjs muster/anschreiben-muster.json /tmp/brief.pdf
node tools/render-cv-allgemein.mjs muster/lebenslauf-muster.json /tmp/cv.pdf
```

*Two ready-made renderer inputs — exactly what `tools/bewerbung.py` produces
from a draft. Handy for working on the layout without building a full
application each time.*

Erfundene Person, erfundene Firma. | Fictional person, fictional company.
