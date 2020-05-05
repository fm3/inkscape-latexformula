#!/usr/bin/env python3

# For more information visit https://github.com/fm3/inkscape-latexformula

import inkex, os, tempfile, sys, xml.dom.minidom, shutil, re
from lxml import etree

if os.name == 'nt':
    import subprocess

class LatexFormula(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        self.arg_parser.add_argument("-f", "--formula",
                        action="store", type=str,
                        dest="formula", default="",
                        help="LaTeX formula")
        self.arg_parser.add_argument("-p", "--preamble",
                        action="store", type=str,
                        dest="preamble", default="",
                        help="TeX Preamble")
        self.arg_parser.add_argument("-s", "--fontsize",
                        action="store", type=float,
                        dest="fontsize", default=10.0,
                        help="Font size (pt)")

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

        self.create_equation_tex(latex_file, self.options.formula, self.options.preamble)

        self.compile_tex_to_dvi(base_dir, latex_file, out_file)

        if (self.compiling_tex_failed(dvi_file)):
            self.print_errors(out_file, base_dir)
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
        tex.write("\\usepackage{tikz}\n")
        tex.write(additional_header)
        tex.write("\n\\thispagestyle{empty}\n")
        tex.write("\\begin{document}\n")
        tex.write("\\begin{tikzpicture}\\fill[green] (0,0) rectangle (1,1);\\end{tikzpicture}\n\n")
        tex.write(equation)
        tex.write("\n\\end{document}\n")
        tex.close()

    def compile_tex_to_dvi(self, base_dir, latex_file, out_file):
        self.run_command('latex "-output-directory=%s" -halt-on-error "%s" > "%s"' \
              % (base_dir, latex_file, out_file))

    def convert_dvi_to_ps(self, dvi_file, ps_file):
        self.run_command('dvips -q -f -E -D 600 -y 5000 -o "%s" "%s"' % (ps_file, dvi_file))

    def convert_ps_to_svg(self, base_dir, ps_file, svg_file, out_file, err_file):
        # cd to base_dir is necessary, because pstoedit writes
        # temporary files to cwd and needs write permissions
        separator = ';'
        if os.name == 'nt':
            separator = '&&'
        self.run_command('cd "%s" %s pstoedit -f plot-svg -dt -ssp "%s" "%s" > "%s" 2> "%s"' \
                  % (base_dir, separator, ps_file, svg_file, out_file, err_file))

    def compiling_tex_failed(self, dvi_file):
        try:
            os.stat(dvi_file)
            return False
        except OSError:
            return True

    def print_errors(self, out_file, base_dir):
        out_file_handle = open(out_file, 'r')
        out_content = out_file_handle.read()

        err_regex = re.compile(r"Error|l\.[0-9]|! ")
        for line in out_content.splitlines():
            if err_regex.match(line):
                print(line, file=sys.stderr)

        print("\nInvalid LaTeX input.\nTemporary files were left in: {} \n\n{}".format(base_dir, out_content), file=sys.stderr)

    def to_document_unit(self, value, unit=""):
        literal = str(value) + unit
        try:
            return self.svg.unittouu(literal)
        except: #old inkscape api
            return inkex.unittouu(literal)

    def import_svg(self, filename):

        def clone_and_rewrite(self, node_in):
            in_tag = node_in.tag.rsplit('}', 1)[-1]
            if in_tag == 'svg':
                node_out = etree.Element(inkex.addNS('g', 'svg'))
            else:
                node_out = etree.Element(inkex.addNS(in_tag, 'svg'))
                for name in node_in.attrib:
                    node_out.set(name, node_in.attrib[name])
            for c in node_in.iterchildren():
                c_tag = c.tag.rsplit('}',1)[-1]
                if c_tag in ('g', 'path', 'polyline', 'polygon'):
                    if not self.is_helper_rect(c):
                        child = clone_and_rewrite(self, c)
                        if c_tag == 'g':
                            child.set('transform','%s matrix(%f,0,0,-%f,-%f,%f)' % \
                                (self.layer_untransform(), self.scale,self.scale,self.anchorX*self.scale, self.anchorY*self.scale))
                            child.set('latex_formula', self.options.formula)
                        node_out.append(child)
            return node_out

        svg_root = etree.parse(filename).getroot()
        self.find_anchor_recursive(svg_root)

        group = clone_and_rewrite(self, svg_root)
        self.svg.get_current_layer().append(group)

    def layer_untransform(self):
        translate_regex = re.compile('translate\((.*),(.*)\)')
        if 'transform' in self.svg.get_current_layer().attrib:
            match = re.match(translate_regex, self.svg.get_current_layer().attrib['transform'])
            if (match):
                return 'translate(%f,%f)' % (-float(match.group(1)), -float(match.group(2)))
        return ''

    def is_helper_rect(self, node):
        return 'fill' in node.attrib and node.attrib['fill'] == 'lime'

    def find_anchor_recursive(self, node):
        if self.is_helper_rect(node):
            coords = node.attrib['points'].strip().replace(' ', ',').split(',')
            self.scale = self.to_document_unit(1.0, "cm") / (float(coords[4]) - float(coords[0]))
            self.scale *= self.options.fontsize / 10.0
            self.anchorX = float(coords[0])
            self.anchorY = float(coords[1])
            return
        for child in node.iterchildren():
            self.find_anchor_recursive(child)

    def cleanup_temporary_files(self, base_dir):
        shutil.rmtree(base_dir)

    def run_command(self, command):
        if os.name == 'nt':
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(command, creationflags=CREATE_NO_WINDOW, shell=True).wait()
        else:
            os.system(command)


if __name__ == '__main__':
    LatexFormula().run()
