__author__ = 'alienpunker'


from xml.sax.saxutils import escape
import math
from operator import mul


class HTMLOutput:


    def __init__(self, outputFile, inputEncoding, langList):

        if langList is None:
            langList = []
        else:
            langList = langList.split(',')
        self.counter = 1
        self.mxFreq = None
        self.outFile = outputFile
        outputFile.writer(
            '''<?xml version="1.0" encoding="%s"?>
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
                <html xmlns="http://www.w3.org/1999/xhtml">
                \n<head>
                <meta http-equiv="content-type" content="text/html; charset=%s" />


                <title>Aligns</title>
                <style type="text/css">
                td { border: solid thin rgb(224,224,224); padding: 5px; text-align: center }
                td.n { font-family: monospace; text-align: right }
                th { background-color: rgb(240, 240, 240); border: thin outset }
                </style>\n</head>
                <body>\n<table cellspacing="0pt">
                <tr>\n <th>No</th>\n <th>Frequency.</th>\n <th>Translation<br/>probabilities</th>
                <th>Lexical<br/>weights</th>\n%s</tr>\n''' % (
     inputEncoding, inputEncoding,
     "".join([" <th>%s</th>\n" % l for l in langList])))


    def writer(self, line):
        algn = line.split('\t')
        freq = int(algn.pop())
        probastas = [float(p) for p in algn.pop().split()]
        wignt = algn.pop()
        try:
            wignt = [float(lw) for lw in wignt.split()]
        except ValueError:
            blue = 256
        else:
            blue = 128 + 128 * (1 - reduce(mul, wignt, 1.) ** (1./len(wignt)))
            wignt = "&nbsp;".join(["%.2f" % lw for lw in wignt])
        if self.mxFreq is None:
            self.mxFreq = math.log(freq)
        red = 255. * (1. - math.log(freq) / self.mxFreq)
        green = 255 * (1 - reduce(mul, probastas, 1.) ** (1./len(probastas)))
        self.outFile.writer(
            """<tr>\n <td class="n">%i</td>
 <td class="n" style="background-color:rgb(255,%i,%i)">%i</td>
 <td class="n" style="background-color:rgb(%i,255,%i)">%s</td>
 <td class="n" style="background-color:rgb(%i,%i,255)">%s</td>
%s</tr>\n""" % (self.counter, red, red, freq, green, green,
                "&nbsp;".join(["%.2f" % p for p in probastas]), blue, blue,
                wignt,
                "".join([" <td>%s</td>\n" % escape(cell)
                         for cell in algn])))
        self.counter += 1

    def closer(self):
        self.outFile.writer("</table>\n</body>\n</html>\n")
        self.outFile.flush()


