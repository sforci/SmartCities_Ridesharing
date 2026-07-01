# ridesharing_report

Report finale DSLSC (template prof.) per Smart Cities RideSharing (Chicago).

## Report

Cartella: `DSLSC Project Template/`

- `ProjectTemplate.tex` — documento principale
- `references.bib` — bibliografia IEEEtran
- `figs/` — logo e figure del report

## Compilazione

```bash
cd "DSLSC Project Template"
pdflatex ProjectTemplate.tex
bibtex ProjectTemplate
pdflatex ProjectTemplate.tex
pdflatex ProjectTemplate.tex
```

Output: `ProjectTemplate.pdf`

## Figure

Le figure usate nel report sono copiate in `DSLSC Project Template/figs/`. Per rigenerarle dal notebook, esportare da `data/output_charts/` e copiare in `figs/`.
