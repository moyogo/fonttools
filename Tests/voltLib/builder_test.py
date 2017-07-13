from fontTools.voltLib.builder import addVOLTFromString, addVOLT
from fontTools.ttLib import TTFont
import difflib
import os
import shutil
import sys
import tempfile
import unittest


def makeTTFont():
    glyphs = """
        .notdef space slash fraction semicolon period comma ampersand
        quotedblleft quotedblright quoteleft quoteright
        zero one two three four five six seven eight nine
        zero.oldstyle one.oldstyle two.oldstyle three.oldstyle
        four.oldstyle five.oldstyle six.oldstyle seven.oldstyle
        eight.oldstyle nine.oldstyle onequarter onehalf threequarters
        onesuperior twosuperior threesuperior ordfeminine ordmasculine
        A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
        a b c d e f g h i j k l m n o p q r s t u v w x y z
        A.sc B.sc C.sc D.sc E.sc F.sc G.sc H.sc I.sc J.sc K.sc L.sc M.sc
        N.sc O.sc P.sc Q.sc R.sc S.sc T.sc U.sc V.sc W.sc X.sc Y.sc Z.sc
        A.alt1 A.alt2 A.alt3 B.alt1 B.alt2 B.alt3 C.alt1 C.alt2 C.alt3
        a.alt1 a.alt2 a.alt3 a.end b.alt c.mid d.alt d.mid
        e.begin e.mid e.end m.begin n.end s.end z.end
        Eng Eng.alt1 Eng.alt2 Eng.alt3
        A.swash B.swash C.swash D.swash E.swash F.swash G.swash H.swash
        I.swash J.swash K.swash L.swash M.swash N.swash O.swash P.swash
        Q.swash R.swash S.swash T.swash U.swash V.swash W.swash X.swash
        Y.swash Z.swash
        f.component
        acutecomb
        f_l c_h c_k c_s c_t f_f f_f_i f_f_l f_i o_f_f_i s_t f_i.begin
        a_n_d T_h T_h.swash germandbls ydieresis yacute breve
        grave acute dieresis macron circumflex cedilla umlaut ogonek caron
        damma hamza sukun kasratan lam_meem_jeem noon.final noon.initial
        by feature lookup sub table
    """.split()
    font = TTFont()
    font.setGlyphOrder(glyphs)
    return font


class BuilderTest(unittest.TestCase):
    # VOLT files in data/*.vtp; output gets compared to data/*.ttx.
    TEST_VOLT_FILES = """
        GlyphData
    """.split()

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        # Python 3 renamed assertRaisesRegexp to assertRaisesRegex,
        # and fires deprecation warnings if a program uses the old name.
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = None
        self.num_tempfiles = 0

    def tearDown(self):
        if self.tempdir:
            shutil.rmtree(self.tempdir)

    @staticmethod
    def getpath(testfile):
        path, _ = os.path.split(__file__)
        return os.path.join(path, "data", testfile)

    def temp_path(self, suffix):
        if not self.tempdir:
            self.tempdir = tempfile.mkdtemp()
        self.num_tempfiles += 1
        return os.path.join(self.tempdir,
                            "tmp%d%s" % (self.num_tempfiles, suffix))

    def read_ttx(self, path):
        lines = []
        with open(path, "r", encoding="utf-8") as ttx:
            for line in ttx.readlines():
                # Elide ttFont attributes because ttLibVersion may change,
                # and use os-native line separators so we can run difflib.
                if line.startswith("<ttFont "):
                    lines.append("<ttFont>" + os.linesep)
                else:
                    lines.append(line.rstrip() + os.linesep)
        return lines


    def expect_ttx(self, font, expected_ttx):
        path = self.temp_path(suffix=".ttx")
        font.saveXML(path, tables=['head', 'name', 'BASE', 'GDEF', 'GSUB',
                                   'GPOS', 'OS/2', 'hhea', 'vhea'])
        actual = self.read_ttx(path)
        expected = self.read_ttx(expected_ttx)
        if actual != expected:
            for line in difflib.unified_diff(
                    expected, actual, fromfile=expected_ttx, tofile=path):
                sys.stderr.write(line)
            self.fail("TTX output is different from expected")

    def build(self, voltfile):
        font = makeTTFont()
        addVOLTFromString(font, voltfile)
        return font

    def check_volt_file(self, name):
        font = makeTTFont()
        addVOLT(font, self.getpath("%s.vtp" % name))
        self.expect_ttx(font, self.getpath("%s.ttx" % name))
        # Make sure we can produce binary OpenType tables, not just XML.
        for tag in ('GDEF', 'GSUB', 'GPOS'):
            if tag in font:
                font[tag].compile(font)


def generate_volt_file_test(name):
    return lambda self: self.check_volt_file(name)


for name in BuilderTest.TEST_VOLT_FILES:
    setattr(BuilderTest, "test_volt_file_%s" % name,
            generate_volt_file_test(name))
