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
        self.maximumFrequency = None
        self.outputFile = outputFile
        outputFile.write(
            '''<?xml version="1.0" encoding="%s"?>
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
                <html xmlns="http://www.w3.org/1999/xhtml">
                \n<head>
                <meta http-equiv="content-type" content="text/html; charset=%s" />


                <title>alignerTron.py: output</title>
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


    def write(self, line):

        alignment = line.split('\t')
        freq = int(alignment.pop())
        probas = [float(p) for p in alignment.pop().split()]
        lexWeights = alignment.pop()
        try:
            lexWeights = [float(lw) for lw in lexWeights.split()]
        except ValueError:
            blue = 256
        else:
            blue = 128 + 128 * (1 - reduce(mul, lexWeights, 1.) ** (1./len(lexWeights)))
            lexWeights = "&nbsp;".join(["%.2f" % lw for lw in lexWeights])
        if self.maximumFrequency is None:
            self.maximumFrequency = math.log(freq)
        red = 255. * (1. - math.log(freq) / self.maximumFrequency)
        green = 255 * (1 - reduce(mul, probas, 1.) ** (1./len(probas)))
        self.outputFile.write(
            """<tr>\n <td class="n">%i</td>
 <td class="n" style="background-color:rgb(255,%i,%i)">%i</td>
 <td class="n" style="background-color:rgb(%i,255,%i)">%s</td>
 <td class="n" style="background-color:rgb(%i,%i,255)">%s</td>
%s</tr>\n""" % (self.counter, red, red, freq, green, green,
                "&nbsp;".join(["%.2f" % p for p in probas]), blue, blue,
                lexWeights,
                "".join([" <td>%s</td>\n" % escape(cell)
                         for cell in alignment])))
        self.counter += 1

    def terminate(self):
        """Terminates writing (close HTML tags)."""
        self.outputFile.write("</table>\n</body>\n</html>\n")
        self.outputFile.flush()


