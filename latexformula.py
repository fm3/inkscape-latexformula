#! /usr/bin/python

"""
latexformula.py: Inskcape extension to convert LaTeX equation strings to SVG paths

Requirements:
	- inkscape, latex, dvips, pstoedit
	- tested only on linux

Related Work:
	- based on eqtexsvg by Julien Vitard <julienvitard@gmail.com> and 
	  Christoph Schmidt-Hieber <christsc@gmx.de>

License:
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
"""

import inkex, os, tempfile, sys, xml.dom.minidom
	
class LatexFormula(inkex.Effect):

	def __init__(self):
		inkex.Effect.__init__(self)
		self.OptionParser.add_option("-f", "--formula",
						action="store", type="string",
						dest="formula", default="",
						help="LaTeX formula")
		self.OptionParser.add_option("-p", "--preamble",
						action="store", type="string",
						dest="preamble", default="",
						help="TeX Preamble")
						

	def effect(self):
		base_dir = tempfile.mkdtemp("", "inkscape-");
		latex_file = os.path.join(base_dir, "latexformula.tex")
		aux_file   = os.path.join(base_dir, "latexformula.aux")
		log_file   = os.path.join(base_dir, "latexformula.log")
		ps_file    = os.path.join(base_dir, "latexformula.ps")
		dvi_file   = os.path.join(base_dir, "latexformula.dvi")
		svg_file   = os.path.join(base_dir, "latexformula.svg")
		out_file   = os.path.join(base_dir, "latexformula.out")
		err_file   = os.path.join(base_dir, "latexformula.err")
		out_err_file = os.path.join(base_dir, "latexformula.out.err")

		self.create_equation_tex(latex_file, self.options.formula, self.options.preamble)
		
		self.compile_tex_to_dvi(base_dir, latex_file, out_file)
		
		if (self.compiling_tex_failed(dvi_file)):
			self.print_errors(out_file, out_err_file, base_dir)
			sys.exit(1)

		self.convert_dvi_to_ps(dvi_file, ps_file)
		
		self.convert_ps_to_svg(base_dir, ps_file, svg_file, out_file, err_file)

 		self.import_svg(svg_file)

		self.cleanup_temporary_files(base_dir)


	def create_equation_tex(self, filename, equation, additional_header):
		tex = open(filename, 'w')
		tex.write("%% temporary file created by inkscape extension latexformula.py\n")
		tex.write("\\documentclass{article}\n")
		tex.write("\\usepackage{amsmath}\n")
		tex.write("\\usepackage{amssymb}\n")
		tex.write("\\usepackage{amsfonts}\n")
		tex.write(additional_header)
		tex.write("\n\\thispagestyle{empty}\n")
		tex.write("\\begin{document}\n")
		tex.write(equation)
		tex.write("\n\\end{document}\n")
		tex.close()


	def compile_tex_to_dvi(self, base_dir, latex_file, out_file):
		os.system('latex "-output-directory=%s" -halt-on-error "%s" > "%s"' \
			  % (base_dir, latex_file, out_file))

	def convert_dvi_to_ps(self, dvi_file, ps_file):
		os.system('dvips -q -f -E -D 600 -y 5000 -o "%s" "%s"' % (ps_file, dvi_file))

	def convert_ps_to_svg(self, base_dir, ps_file, svg_file, out_file, err_file):
		# cd to base_dir is necessary, because pstoedit writes
		# temporary files to cwd and needs write permissions
		separator = ';'
		if os.name == 'nt':
			separator = '&&'
		os.system('cd "%s" %s pstoedit -f plot-svg -dt -ssp "%s" "%s" > "%s" 2> "%s"' \
				  % (base_dir, separator, ps_file, svg_file, out_file, err_file))

	def compiling_tex_failed(self, dvi_file):
		try:
			os.stat(dvi_file)
			return False
		except OSError:
			return True


	def print_errors(self, out_file, out_err_file, base_dir):
		os.system('cat ' + out_file + " | grep -e 'Error\|l\.[0-9]\|\! ' > " + out_err_file)
		out_err_file_handle = open(out_err_file, 'r')
		print >>sys.stderr, out_err_file_handle.read()
		
		print >>sys.stderr, "Invalid LaTeX input. "
		print >>sys.stderr, "Temporary files were left in:", base_dir
		print >>sys.stderr, ""
		
		out_file_handle = open(out_file, 'r')
		print >>sys.stderr, out_file_handle.read()


	def import_svg(self, filename):
		try:
			doc_width = self.unittouu(self.document.getroot().get('width'))
			doc_height = self.unittouu(self.document.getroot().get('height'))
		except: #old inkscape api (< 0.91)
			doc_width = inkex.unittouu(self.document.getroot().get('width'))
			doc_height = inkex.unittouu(self.document.getroot().get('height'))
		doc_sizeH = min(doc_width, doc_height)
		doc_sizeW = max(doc_width, doc_height)

		def clone_and_rewrite(self, node_in):
			in_tag = node_in.tag.rsplit('}', 1)[-1]
			if in_tag != 'svg':
				node_out = inkex.etree.Element(inkex.addNS(in_tag,'svg'))
				for name in node_in.attrib:
					node_out.set(name, node_in.attrib[name])
			else:
				node_out = inkex.etree.Element(inkex.addNS('g','svg'))
			for c in node_in.iterchildren():
				c_tag = c.tag.rsplit('}',1)[-1]
				if c_tag in ('g', 'path', 'polyline', 'polygon'):
					child = clone_and_rewrite(self, c)
					if c_tag == 'g':
						child.set('transform','matrix('+str(doc_sizeH/700.)+',0,0,'+str(-doc_sizeH/700.)+','+str(-doc_sizeH*0.25)+','+str(doc_sizeW*0.75)+')')
					node_out.append(child)

			return node_out

		doc = inkex.etree.parse(filename)
		svg = doc.getroot()
		group = clone_and_rewrite(self, svg)
		self.current_layer.append(group)


	def cleanup_temporary_files(self, base_dir):
		os.system('rm -r "%s"' % (base_dir))			

if __name__ == '__main__':
	LatexFormula().affect()

