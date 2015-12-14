
import os
import sys
import optparse
from time import time
import Aligner

import bz2
import gzip
from xml.sax.saxutils import escape
from tempfile import NamedTemporaryFile

import math
import random
from array import array
from operator import mul
from bisect import bisect_left
from output import PlainWriter, MosesWriter, HTMLWriter
try:
    import Distribution

except Exception as e:
    print e

__version__ = '2.5 (May 4th 2011)'
__author__ = 'Adrien Lardilleux <Adrien.Lardilleux@limsi.fr>'
__scriptName__ = 'anymalign'
__verbose__ = False
__tmpDir__ = None

MAX_SUBCORPUS_SIZE = 100000



###############################################################################
# Utility functions
###############################################################################

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

    return NamedTemporaryFile(dir=__tmpDir__, prefix=__scriptName__,
                              suffix=suf)

def open_compressed(filename):

    if filename.endswith('.gz'):
        return gzip.open(filename, 'rb')
    elif filename.endswith('.bz2'):
        return bz2.BZ2File(filename, 'r')
    else:
        return open(filename, 'rb')
    

def message(msg, out=sys.stderr):

    if __verbose__:
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


class CoocDB:

    def __init__(self, nbWords):

        self.pairs = [None] * nbWords
        self.freqs = [None] * nbWords
    
    def add(self, sourceWord, cooc):

        targets = sorted(cooc)
        self.pairs[sourceWord] = optimum_array(targets, targets[-1])
        self.freqs[sourceWord] = optimum_array([cooc[tw] for tw in targets])
    
    def get(self, sourceWord, targetWord):

        return self.freqs[sourceWord][bisect_left(self.pairs[sourceWord],
                                                  targetWord)]



###############################################################################
# Function shared by Aligner class and merge() function
###############################################################################

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


###############################################################################
# Merge alignment files
###############################################################################

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


###############################################################################
# Main program
###############################################################################

def main():


    """Process command line options."""
    parser = optparse.OptionParser(version=__version__,
                                   description="""esssoidjfdijfa""",
                                   usage='''no usage''')

    parser.add_option('-m', '--merge', default=False, action='store_true',
                      help="""Do not align. Input files are
pre-generated alignment files (plain text format) to be merged into a
single alignment file.""")
    parser.add_option('-T', '--temp-dir', dest='dir', default=None,
                      help="""(compatible with -m) Where to write
temporary files. Default is OS dependant.""")
    parser.add_option('-q', '--quiet', default=False, action='store_true',
                      help="""(compatible with -m) Do not show
                      progress information on standard error.""")

    alterGroup = optparse.OptionGroup(parser,
                                      "Options to alter alignment behaviour")
    alterGroup.add_option('-a', '--new-alignments', dest='nb_al', type='int',
                      default=-1, help="""Stop alignment when number of
new alignments per second is lower than NB_AL. Specify -1 to run
indefinitely. [default: %default]""")
    alterGroup.add_option('-i', '--index-ngrams', dest='index_n', type='int',
                      default=1, help="""Consider n-grams up to
n=INDEX_N as tokens. Increasing this value increases the number of
long n-grams output, but slows the program down and requires more
memory [default: %default]""")
    alterGroup.add_option('-S', '--max-sentences', dest="nb_sent", default=0,
                          type='int', help="""Maximum number of
sentences (i.e. input lines) to be loaded in memory at once. Specify 0
for all-in-memory. [default: %default]""")
    alterGroup.add_option('-t', '--timeout', dest='nb_sec', type='float',
                          default=-1, help="""Stop alignment after
NB_SEC seconds elapsed. Specify -1 to run indefinitely. [default:
%default]""")
    alterGroup.add_option('-w', '--weight', default=False, action='store_true',
                      help="""Compute lexical weights (requires
additional computation time and memory).""")
    parser.add_option_group(alterGroup)

    filteringGroup = optparse.OptionGroup(parser, "Filtering options")
    filteringGroup.add_option('-D', '--discontiguous-fields', dest='fields',
                              default='', help="""Allow discontiguous
sequences (like "give up" in "give it up") in languages at positions
specified by FIELDS. FIELDS is a comma-separated list of integers
(1-based), runs of fields can be specified by a dash (e.g.
"1,3-5").""")
    filteringGroup.add_option('-l', '--min-languages', dest='nb_lang',
                              type='int', default=None, help="""Keep
only those alignments that contain words in at least MIN_LANGUAGES
languages (i.e. columns). Default is to cover all languages.""")
    filteringGroup.add_option('-n', '--min-ngram', dest='min_n', type='int',
                              default=1, help="""Filter out any
alignment that contains an N-gram with N < MIN_N. [default:
%default]""")
    filteringGroup.add_option('-N', '--max-ngram', dest='max_n', type='int',
                              default=7, help="""Filter out any
alignment that contains an N-gram with N > MAX_N (0 for no
limit). [default: %default]""")
    parser.add_option_group(filteringGroup)

    formattingGroup = optparse.OptionGroup(parser, "Output formatting options")
    formattingGroup.add_option('-d', '--delimiter', dest='delim', type='str',
                               default='', help="""Delimiter for
discontiguous sequences. This can be any string. No delimiter is shown
by default. Implies -D- (allow discontinuities in all languages) if -D
option is not specified.""")
    formattingGroup.add_option('-e', '--input-encoding', dest='encoding',
                               default='utf-8', help="""(compatible
with -m) Input encoding. This is useful only for HTML and TMX output
formats (see -o option). [default: %default]""")
    formattingGroup.add_option('-L', '--languages', dest='lang', type='str',
                               default=None, help="""(compatible with
-m) Input languages. LANG is a comma separated list of language
identifiers (e.g. "en,fr,ar"). This is useful only for HTML (table
headers) and TMX (<xml:lang>) output formats (see -o option).""")
    formattingGroup.add_option('-o', '--output-format', dest='format',
                               type='str', default='plain',
                               help="""(compatible with -m) Output
format. Possible values are "plain", "moses", "html", and "tmx".
[default: %default]""")
    parser.add_option_group(formattingGroup)

    options, args = parser.parse_args()
            
    if args.count("-") > 1:
        parser.error('Standard input "-" can only be read once')
    if not args:    # Read standard input
        args = ["-"]

    global __verbose__, __tmpDir__
    __verbose__, __tmpDir__ = not options.quiet, options.dir
    if 'psyco' in globals():
        message("Using psyco module\n")

    format = options.format.lower()
    if "plain".startswith(format):
        writer = PlainWriter(sys.stdout)
    elif "moses".startswith(format):
        writer = MosesWriter(sys.stdout)
    elif "html".startswith(format):
        writer = HTMLWriter(sys.stdout, options.encoding, options.lang)

    else:
        parser.error("Unknown output format for option -o")

    if options.merge:
        merge(args, writer)
    else:
        try:    # Check whether the -D option value is well formed
            parse_field_numbers(options.fields, 0)
        except ValueError:
            parser.error("Invalid field list for option -D")
        if options.delim and not options.fields:
            options.fields = "-"
        if options.max_n <= 0:
            options.max_n = sys.maxint
        if options.index_n < 1:
            parser.error("-i option must be positive")
        if options.index_n > options.max_n:
            parser.error(
                "-i option value should not be greater than that of -N")


        from Aligner import Aligner as Aligner
        Aligner(args, writer, options.nb_al, options.nb_sent, options.nb_sec,
                options.weight, options.fields, options.nb_lang, options.min_n,
                options.max_n, options.delim, options.index_n)


if __name__ == '__main__':
    try:
        import psyco
    except ImportError:
        pass
    else:
        # Allow KeyboardInterrupt to be raised in main loop
        psyco.cannotcompile(Aligner.run)
        psyco.full()


    main()