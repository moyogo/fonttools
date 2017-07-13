from __future__ import absolute_import
from fontTools.misc.py23 import UnicodeIO, tounicode
from fontTools.voltLib.error import VoltLibError
from fontTools.voltLib.parser import Parser
from fontTools.otlLib import builder as otl
# from fontTools.ttLib import newTable, getTableModule
from fontTools.ttLib import newTable
# from fontTools.ttLib.tables import otBase, otTables
from fontTools.ttLib.tables import otTables


def addVOLT(font, voltfile):
    builder = Builder(font, voltfile)
    builder.build()


def addVOLTFromString(font, volt):
    voltfile = UnicodeIO(tounicode(volt))
    addVOLT(font, voltfile)


class Builder(object):
    def __init__(self, font, voltfile):
        self.font = font
        self.file = voltfile
        self.glyphMap = font.getReverseGlyphMap()
        # for table 'GDEF'
        self.attachPoints_ = {}  # "a" --> {3, 7}
        self.ligCaretCoords_ = {}  # "f_f_i" --> {300, 600}
        self.ligCaretPoints_ = {}  # "f_f_i" --> {3, 7}
        self.glyphClassDefs_ = {}  # "fi" --> (2, (file, line, column))
        self.markAttach_ = {}  # "acute" --> (4, (file, line, column))
        self.markAttachClassID_ = {}  # frozenset({"acute", "grave"}) --> 4
        self.markFilterSets_ = {}  # frozenset({"acute", "grave"}) --> 4

    def build(self):
        self.parseTree = Parser(self.file).parse()
        self.parseTree.build(self)
        gdef = self.buildGDEF()
        if gdef:
            self.font["GDEF"] = gdef
        elif "GDEF" in self.font:
            del self.font["GDEF"]

    def buildGDEF(self):
        gdef = otTables.GDEF()
        gdef.GlyphClassDef = self.buildGDEFGlyphClassDef_()
        gdef.AttachList = \
            otl.buildAttachList(self.attachPoints_, self.glyphMap)
        gdef.LigCaretList = \
            otl.buildLigCaretList(self.ligCaretCoords_, self.ligCaretPoints_,
                                  self.glyphMap)
        gdef.MarkAttachClassDef = self.buildGDEFMarkAttachClassDef_()
        gdef.MarkGlyphSetsDef = self.buildGDEFMarkGlyphSetsDef_()
        gdef.Version = 0x00010002 if gdef.MarkGlyphSetsDef else 0x00010000
        if any((gdef.GlyphClassDef, gdef.AttachList, gdef.LigCaretList,
                gdef.MarkAttachClassDef, gdef.MarkGlyphSetsDef)):
            result = newTable("GDEF")
            result.table = gdef
            return result
        else:
            return None

    def buildGDEFGlyphClassDef_(self):
        inferredGlyphClass = {}
        # for lookup in self.lookups_:
        #     inferredGlyphClass.update(lookup.inferGlyphClasses())
        # for markClass in self.parseTree.markClasses.values():
        #     for markClassDef in markClass.definitions:
        #         for glyph in markClassDef.glyphSet():
        #             inferredGlyphClass[glyph] = 3
        if self.glyphClassDefs_:
            classes = {g: c for (g, (c, _)) in self.glyphClassDefs_.items()}
        else:
            classes = inferredGlyphClass
        if classes:
            result = otTables.GlyphClassDef()
            result.classDefs = classes
            return result
        else:
            return None

    def buildGDEFMarkAttachClassDef_(self):
        classDefs = {g: c for g, (c, _) in self.markAttach_.items()}
        if not classDefs:
            return None
        result = otTables.MarkAttachClassDef()
        result.classDefs = classDefs
        return result

    def buildGDEFMarkGlyphSetsDef_(self):
        sets = []
        for glyphs, id_ in sorted(self.markFilterSets_.items(),
                                 key=lambda item: item[1]):
            sets.append(glyphs)
        return otl.buildMarkGlyphSetsDef(sets, self.glyphMap)


    def setGlyphClass(self, location, glyph, glyphClass):
        oldClass, oldLocation = self.glyphClassDefs_.get(glyph, (None, None))
        if oldClass and oldClass != glyphClass:
            raise VoltLibError(
                "Glyph %s was assigned to a different class at %s:%s:%s" %
                (glyph, oldLocation[0], oldLocation[1], oldLocation[2]),
                location)
        self.glyphClassDefs_[glyph] = (glyphClass, location)
