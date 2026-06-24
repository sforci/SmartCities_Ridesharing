.PHONY: pdf clean

pdf:
	latexmk -pdf -interaction=nonstopmode main.tex

clean:
	latexmk -C
	rm -rf _minted
