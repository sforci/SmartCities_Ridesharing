# ridesharing_report

Lab report LaTeX per il progetto Smart Cities RideSharing (Chicago).

## Contenuto

- `main.tex` — documento principale (rho-class)
- `rho.bib` — bibliografia
- `rho-class/` — class file (incluso, nessun install globale richiesto)
- `example.py` — esempio codice per il listing

## Compilazione locale

Requisiti: TeX Live (o MacTeX) con `pdflatex`, `biber`, e i font Fira Sans / Fira Mono / STIX2 (inclusi in TeX Live recente).

```bash
cd ridesharing_report
pdflatex main.tex
biber main
pdflatex main.tex
pdflatex main.tex
```

Oppure, con `latexmk`:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

Il PDF generato è `main.pdf`.

## Overleaf

1. Carica l'intera cartella `ridesharing_report` come progetto.
2. Imposta il compiler su **pdfLaTeX**.
3. Compila: Overleaf gestisce automaticamente `biber`.

## Note

- Il template usa `listings` (non `minted`): nessun Python/Pygments o `--shell-escape` richiesto.
- Aggiungi le figure esportate dal notebook in `figures/` e referenziale in `main.tex`.
- Aggiorna autori e email in `main.tex` prima della consegna.
