# Inkscape Extension: LaTeX Formula

Inskcape extension to convert LaTeX equation strings to SVG paths

## Requirements
- inkscape 1.0 (refer to older commit 2064ea8fdf6164ef1a4ff7343ea496745db07d94 for inkscape 0.92)
- latex, dvips, pstoedit, ghostscript need to be in your PATH

## Installation
- copy `latexformula.inx` and `latexformula.py` to `~/.config/inkscape/extensions/` on linux and `C:\Users\you\AppData\Roaming\inkscape\extensions\` on windows
- restart inkscape

## Usage
- In Inkscape menu, select `Extensions` > `Render` > `LaTeX Formula`
- Enter your formula and optional packages if needed

## Related Work:
- based on eqtexsvg by Julien Vitard <julienvitard@gmail.com> and
  Christoph Schmidt-Hieber <christsc@gmx.de>
