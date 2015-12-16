__author__ = 'alienpunker'


import sys
import gzip
from tempfile import NamedTemporaryFile

from array import array



falg = False
temp = None
name = ""

def changeFields(fields, maxFields):
    selection = set()
    for field in fields.split(','):
        if not field:
            continue
        starter = field.split('-')
        if len(starter) > 2:
            raise ValueError
        elif len(starter) == 1 and starter[0]:
            selection.add(int(starter[0]))
        else:
            start, end = starter
            if start:
                start = int(start)
            else:
                start = 1
            if end:
                end = int(end)
            else:
                end = maxFields
            selection.update(xrange(start, end + 1))
    return selection



def getTempFIle(suf=''):
    return NamedTemporaryFile(dir=temp, prefix=name, suffix=suf)

def openFile(filename):
    return open(filename, 'rb')



def getBestArray(list, maxi=None):

    if maxi is None:
        maxi = max(list)
    for typecode in "BHiIlL":
        try:
            array(typecode, [maxi])
        except OverflowError:
            pass
        else:
            return array(typecode, list)
    return tuple(list)


def setProbability(inputFile, inputDict, writer):

    nbAlignments = 0
    offfrequencies = {}
    inputFile.seek(0)
    offset = 0
    for line in inputFile:
        nbAlignments += 1
        alignment = line.rsplit('\t', 1)[0] # Remove lexical weights
        freq = inputDict[len(alignment)][hash(alignment)]
        offfrequencies.setdefault(freq, []).append(offset)
        offset += len(line)
    inputDict.clear()   # Release memory

    if not nbAlignments:
        return

    tmpFile = getTempFIle(".al_lw.gz")
    compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="wb", compresslevel=1)
    try:
        alNo = 0
        for freq in sorted(offfrequencies.iterkeys(), reverse=True):
            for offset in offfrequencies.pop(freq):
                alNo += 1
                inputFile.seek(offset)
                print >> compressedFile, "%s\t%x" % \
                      (inputFile.readline().rstrip('\n'), freq)
        compressedFile.close()
        inputFile.close()
        offfrequencies.clear()

        tmpFile.seek(0)
        compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        nbLanguages, nbSplits = None, None
        for line in compressedFile:
            if nbLanguages is None:
                nbSplits = line.count('\t')
                nbLanguages = nbSplits - 1
                phraseFreq = [{} for _ in xrange(nbLanguages)]
            alignment = line.split('\t', nbSplits)
            freq = int(alignment.pop(), 16)
            alignment.pop() # Remove lexical weights
            for phrase, counts in zip(alignment, phraseFreq):
                phraseHash = hash(phrase)
                counts[phraseHash] = counts.get(phraseHash, 0) + freq
        compressedFile.close()

        tmpFile.seek(0)
        compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        nbSplits = nbLanguages
        try:
            for line in compressedFile:
                alignmentStr, lexWeights, freq = line.rsplit('\t', 2)
                alignment = alignmentStr.split('\t', nbSplits)
                freq = int(freq, 16)
                probas = ' '.join(["%f" % (1. * freq / counts[hash(phrase)])
                                   for phrase, counts
                                   in zip(alignment, phraseFreq)])
                writer.write("%s\t%s\t%s\t%i\n" % (alignmentStr, lexWeights,
                                                   probas, freq))
            writer.terminate()
        except IOError:
            pass
    finally:
        tmpFile.close()