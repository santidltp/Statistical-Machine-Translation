__author__ = 'alienpunker'
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
from CommonUtil import optimum_array,message, merge, parse_field_numbers
from bisect import bisect_left
from output import  HTMLOutput
try:
    import Distribution

except Exception as e:
    print e


__scriptName__ = 'anymalign'
__verbose__ = False
__tmpDir__ = None

MAX_SUBCORPUS_SIZE = 100000





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



def main():


    """Process command line options."""
    parser = optparse.OptionParser(version="",
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
    if "html".startswith(format):
        writer = HTMLOutput(sys.stdout, options.encoding, options.lang)

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