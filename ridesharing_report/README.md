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

## Figures

Run the notebook first so charts are saved under `data/output_charts/`. The report loads them via `\graphicspath{{../data/output_charts/}}`.

Required files: `tui_2024.png`, `tui_sdvi_maps_2024.png`, `tui_vs_hsvi_2024.png`, `tui_vs_sdvi_2024.png`.

## Note

- Figures are read from `../data/output_charts/` after running the notebook.
- The template uses `listings` (not `minted`): no Python/Pygments or `--shell-escape` required.
