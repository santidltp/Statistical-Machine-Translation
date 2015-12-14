__author__ = 'alienpunker'


import sys
import bz2
import gzip
from tempfile import NamedTemporaryFile

from array import array



__version__ = '2.5 (May 4th 2011)'
__author__ = 'Adrien Lardilleux <Adrien.Lardilleux@limsi.fr>'
__scriptName__ = 'anymalign'
falg = False
temp = None

def parse_field_numbers(fields, maxFields):



    selection = set()
    for f in fields.split(','):
        if not f:
            continue
        start_end = f.split('-')
        if len(start_end) > 2:
            raise ValueError
        elif len(start_end) == 1 and start_end[0]:
            selection.add(int(start_end[0]))
        else:
            start, end = start_end
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



def make_temp_file(suf=''):

    return NamedTemporaryFile(dir=temp, prefix=__scriptName__,
                              suffix=suf)

def open_compressed(filename):

    if filename.endswith('.gz'):
        return gzip.open(filename, 'rb')
    elif filename.endswith('.bz2'):
        return bz2.BZ2File(filename, 'r')
    else:
        return open(filename, 'rb')


def message(msg, out=sys.stderr):

    if falg:
        out.write(str(msg))

def optimum_array(initialList, maxi=None):

    if maxi is None:
        maxi = max(initialList)
    for typecode in "BHiIlL":
        try:
            array(typecode, [maxi])
        except OverflowError:
            pass
        else:
            return array(typecode, initialList)
    return tuple(initialList)

def set_proba(inputFile, inputDict, writer):

    nbAlignments = 0
    # Sort: read inputFile once to determine where each line begins
    offsetsByFreq = {}
    inputFile.seek(0)
    offset = 0
    for line in inputFile:
        nbAlignments += 1
        alignment = line.rsplit('\t', 1)[0] # Remove lexical weights
        freq = inputDict[len(alignment)][hash(alignment)]
        offsetsByFreq.setdefault(freq, []).append(offset)
        offset += len(line)
    inputDict.clear()   # Release memory

    message("\r%i alignments\n" % nbAlignments)
    if not nbAlignments:
        return

    # Read inputFile once more, according to absolute frequencies, and
    # dump everything into compressed file
    message("Sorting alignments\n")
    # nextPercentage = Progression(nbAlignments).next
    tmpFile = make_temp_file(".al_lw.gz")
    compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="wb", compresslevel=1)
    try:
        alNo = 0
        for freq in sorted(offsetsByFreq.iterkeys(), reverse=True):
            for offset in offsetsByFreq.pop(freq):
                alNo += 1
                inputFile.seek(offset)
                print >> compressedFile, "%s\t%x" % \
                      (inputFile.readline().rstrip('\n'), freq)
                # nextPercentage()
        compressedFile.close()
        inputFile.close()   # Delete temporary input file
        offsetsByFreq.clear()

        message("\rComputing conditional probabilities...\n")
        # nextPercentage = Progression(nbAlignments).next
        tmpFile.seek(0)
        compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        # Count the number of occurrences of all parts of alignments
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
            # nextPercentage()
        compressedFile.close()

        # Output alignments
        tmpFile.seek(0)
        compressedFile = gzip.GzipFile(fileobj=tmpFile, mode="rb")
        message("\rOutputting results...\n")
        # nextPercentage = Progression(nbAlignments).next
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
                # nextPercentage()
            writer.terminate()
        except IOError:
            pass
        message("\r")
    finally:
        tmpFile.close()


def merge(inputFilenames, writer):

    files = []
    counts = {} # Absolute frequencies of alignments
    weightedAlignmentFile = make_temp_file('.al_lw')
    try:
        for f in inputFilenames:
            if f == "-":
                files.append(sys.stdin)
            else:
                files.append(open_compressed(f))
        # Sum up absolute frequencies for alignments
        for inputFile in files:
            for line in inputFile:
                alignment_lw, _, freq = line.rsplit('\t', 2)
                alignment = alignment_lw.rsplit('\t', 1)[0]
                bucket = counts.setdefault(len(alignment), {})
                alignmentHash = hash(alignment)
                previousFreq = bucket.get(alignmentHash)
                if previousFreq is None:
                    bucket[alignmentHash] = int(freq)
                    print >> weightedAlignmentFile, alignment_lw
                else:
                    bucket[alignmentHash] = previousFreq + int(freq)

        weightedAlignmentFile.seek(0)
        set_proba(weightedAlignmentFile, counts, writer)
    finally:
        weightedAlignmentFile.close()
        for f in files:
            f.close()
