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

    aligmenNumber = 0
    offfrequencies = {}
    inputFile.seek(0)
    offset = 0
    for line in inputFile:
        aligmenNumber += 1
        alignment = line.rsplit('\t', 1)[0]
        freq = inputDict[len(alignment)][hash(alignment)]
        offfrequencies.setdefault(freq, []).append(offset)
        offset += len(line)
    inputDict.clear()

    if not aligmenNumber:
        return

    tmpFile = getTempFIle(".al_lw.gz")
    reserved = gzip.GzipFile(fileobj=tmpFile, mode="wb", compresslevel=1)
    try:
        alignNum = 0
        for freq in sorted(offfrequencies.iterkeys(), reverse=True):
            for offset in offfrequencies.pop(freq):
                alignNum += 1
                inputFile.seek(offset)
                print >> reserved, "%s\t%x" % \
                      (inputFile.readline().rstrip('\n'), freq)
        reserved.close()
        inputFile.close()
        offfrequencies.clear()

        tmpFile.seek(0)
        reserved = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        numberoflanguages, numberpartitions = None, None
        for line in reserved:
            if numberoflanguages is None:
                numberpartitions = line.count('\t')
                numberoflanguages = numberpartitions - 1
                phraseFreq = [{} for _ in xrange(numberoflanguages)]
            alignment = line.split('\t', numberpartitions)
            freq = int(alignment.pop(), 16)
            alignment.pop() # Remove lexical weights
            for phrase, counts in zip(alignment, phraseFreq):
                phraseHash = hash(phrase)
                counts[phraseHash] = counts.get(phraseHash, 0) + freq
        reserved.close()

        tmpFile.seek(0)
        reserved = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        numberpartitions = numberoflanguages
        try:
            for line in reserved:
                alignmentStr, lexWeights, freq = line.rsplit('\t', 2)
                alignment = alignmentStr.split('\t', numberpartitions)
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