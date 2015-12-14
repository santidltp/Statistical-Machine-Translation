__author__ = 'alienpunker'
import sys
from time import time
from CommonUtil import open_file, parse_field_numbers, getTempFIle, setProbability, best_array
import math
import random
from Distribution import Distribution



maximumSize = 10000



class Aligner:


    def __init__(self, inputFilenames, writer, nbNewAlignments, maxNbLines,
                 timeout, doLexWeight, discontiguousFields, minLanguages,
                 minSize, maxSize, delimiter, indexN):

        self.minSize = minSize
        self.maxSize = maxSize
        if delimiter:
            self.delimiter = delimiter
        else:
            self.delimiter = None
        self.indexN = max(indexN, 1)
        if doLexWeight:
            self.weightFunc = self._lexical_weight
        else:
            self.weightFunc = self._dummy_weight
        self.counts = {}
        self.nbAlignments = 0   # = sum(len(c) for c in self.counts)
        self.files = []
        self.weightedAlignmentFile = getTempFIle(".al_lw")
        try:
            for f in inputFilenames:
                if f == "-":
                    inFile = getTempFIle(".stdin")
                    inFile.writelines(sys.stdin)
                    inFile.seek(0)
                    self.files.append(inFile)
                else:
                    self.files.append(open_file(f))
            self.offsets = []
            nbLines = None
            self.nbLanguages = 0
            for f in self.files:
                offset = 0
                fileOffsets = []
                fileLanguages = None
                lineId = -1
                for lineId, line in enumerate(f):
                    fl = line.count('\t') + 1
                    if fileLanguages is None:
                        fileLanguages = fl
                        self.nbLanguages += fl
                    else:
                        assert fl == fileLanguages, "Found %i columns " \
                               " instead of %i at line %i in file %s" % \
                               (fl, fileLanguages, lineId + 1, f.name)
                    fileOffsets.append(offset)
                    offset += len(line)
                if nbLines is None:
                    nbLines = lineId + 1
                else:
                    assert nbLines == lineId + 1, \
                           "Input files have different number of lines"
                self.offsets.append(best_array(fileOffsets))
                del fileOffsets
            # message("Input corpus: %i languages, %i lines\n" %
            #         (self.nbLanguages, nbLines))

            if minLanguages is None:
                self.minLanguages = self.nbLanguages
            else:
                self.minLanguages = minLanguages

            ncf = parse_field_numbers(discontiguousFields, self.nbLanguages)
            self.contiguousFields = [(i + 1 not in ncf)
                                     for i in range(self.nbLanguages)]

            if timeout < 0:
                timeout = None

            if maxNbLines < 1:
                nbCorpora = 1
            else:
                nbCorpora = int(math.ceil(1. * nbLines / maxNbLines))
                # message("Split input corpus into %i subcorpora" % nbCorpora)
                if timeout is not None:
                    timeout /= 1. * nbCorpora
                    # message(" (timeout: %.2fs each)" % timeout)
                # message("\n")
            lines = range(nbLines)
            random.shuffle(lines)
            for nbCorpToDo in range(nbCorpora, 0, -1):
                # if nbCorpora > 1:
                    # message("\r%i subcorpora remaining\n" % nbCorpToDo)
                selection = [lines.pop() for _ in
                             range(int(math.ceil(1. * len(lines) /
                                                  nbCorpToDo)))]
                selection.sort()    # Speed up disk access
                self.set_corpus(selection)
                self.run(timeout, nbNewAlignments)
            setProbability(self.weightedAlignmentFile, self.counts, writer)
        finally:
            self.weightedAlignmentFile.close()
            for f in self.files:
                f.close()



    def set_corpus(self, lines):

        self.corpus = [[] for _ in lines]
        self.allWords, self.wordLanguages = [], []
        allWordIds = [{} for _ in range(self.nbLanguages)]
        nbLanguagesDone = 0
        # Read files sequentially, rather than in parallel (faster)
        for f, fileOffsets in zip(self.files, self.offsets):
            for lineId, offsetId in enumerate(lines):
                f.seek(fileOffsets[offsetId])
                line = self.corpus[lineId]
                for i, sentence in enumerate(f.readline().split('\t')):
                    languageId = i + nbLanguagesDone
                    wordIds = allWordIds[languageId]
                    for word in sentence.split():
                        wordId = wordIds.get(word)
                        if wordId is None:
                            wordId = len(self.allWords)
                            wordIds[word] = wordId
                            self.allWords.append(word)
                            self.wordLanguages.append(languageId)
                        line.append(wordId)
            nbLanguagesDone = languageId + 1

        # Compute word frequencies
        self.wordFreq = [0] * len(self.allWords)
        for line in self.corpus:
            for wordId in set(line):
                self.wordFreq[wordId] += 1

        # Add discontinuity delimiter
        self.allWords.append(self.delimiter)
        self.wordLanguages.append(self.nbLanguages)
        self.wordFreq.append(max(self.wordFreq) + 1)

        # Reassign word ids: smallest id for most frequent word
        sortedByFreq = sorted(range(len(self.allWords)),
                              key=self.wordFreq.__getitem__, reverse=True)
        self.allWords = [self.allWords[i] for i in sortedByFreq]
        self.wordLanguages = best_array([self.wordLanguages[i]
                                            for i in sortedByFreq],
                                           self.nbLanguages)
        newPos = [None] * len(self.allWords)
        for i, wordId in enumerate(sortedByFreq):
            newPos[wordId] = i
        for i, line in enumerate(self.corpus): # Replace word ids in corpus
            self.corpus[i] = [newPos[wordId] for wordId in line]

        self.wordFreq.sort(reverse=True)
        self.wordFreq = best_array(self.wordFreq)


        ngramRange = range(2, self.indexN + 1)
        languageRange = range(self.nbLanguages)

        allNgramIds = [{} for _ in ngramRange]
        self.allNgrams = [[] for _ in ngramRange]
        self.ngramCorpora = [[] for _ in ngramRange]

        for line in self.corpus:
            sentences = [[] for _ in languageRange]
            ngramSentences = [set() for _ in ngramRange]
            for word in line:
                sentences[self.wordLanguages[word]].append(word)
            for s in sentences:
                s = tuple(s)
                lastIdx = len(s) + 1
                for n in range(2, min(self.indexN+1, lastIdx)):
                    ngramIds = allNgramIds[n-2]
                    ngrams = self.allNgrams[n-2]
                    ngramSentence = ngramSentences[n-2]
                    for i in range(lastIdx - n):
                        ngram = s[i:i+n]
                        ngramId = ngramIds.get(ngram)
                        if ngramId is None:
                            ngramId = len(ngrams)
                            ngramIds[ngram] = ngramId
                            ngrams.append(ngram)
                        ngramSentence.add(ngramId)
            for n in ngramRange:
                self.ngramCorpora[n-2].append(sorted(ngramSentences[n-2]))


    def main_distribution(self, k):

        return 1. / (k * math.log(1 - 1. * k / (len(self.corpus) + 1)))
        #return 1. / (math.log(1 - 1. * k / (len(self.corpus) + 1)))
        #return 1


    def run(self, timeout, nbNewAlignments):

        nbLines = len(self.corpus)
        if nbLines > 2: # Speed up by not using subcorpora of size 1 or nbLines
            nextRandomSize = Distribution(                self.main_distribution,
                2,              # Never get sample size = 1
                nbLines - 1     # Never get sample size = nbLines
                ).next
        else:   # Use the theoritically correct distribution
            nextRandomSize = Distribution(
                self.main_distribution,
                1,
                nbLines
                ).next

        nb2 = 0     # Number of subcorpora of size 2
        nbSubcorporaDone = 0
        subcorporaDoneSum = 0 # for calculating average size
        previousNbAl = 0
        previousWriteLen = 0
        lastWriteTime = startTime = time()
        speed = sys.maxint

        print >> sys.stderr, "\rAligning... (ctrl-c to interrupt)"
        # Do not compress this temp file ! Some alignments are not actually
        # written with KeyboardInterrupt (may be because of psyco)
        tmpFile = getTempFIle(".al")
        try:
            try:
                while speed > nbNewAlignments:
                    t = time()
                    if timeout is not None and t - startTime >= timeout:
                        break
                    elapsedTime = t - lastWriteTime
                    if nbSubcorporaDone >= 1 and elapsedTime >= 1:
                        speed = int(math.ceil((self.nbAlignments -
                                               previousNbAl) / elapsedTime))
                        #proba = (1 - 2. / (nbLines + 1)) ** (2 * nb2)
                        toWrite = "(%i subcorpora, avg=%.2f) " \
                                  "%i alignments, %i al/s" % \
                                  (nbSubcorporaDone,
                                   1. * subcorporaDoneSum / nbSubcorporaDone,
                                   self.nbAlignments, speed)
                        # message("\r%s%s" % (toWrite," " * (previousWriteLen -
                        #                                    len(toWrite))))
                        previousWriteLen = len(toWrite)
                        previousNbAl = self.nbAlignments
                        lastWriteTime = t


                    subcorpusSize = nextRandomSize()
                    while subcorpusSize > maximumSize:
                        subcorpusSize = nextRandomSize()
                    if subcorpusSize == 2:
                        nb2 += 1

                    nbSubcorporaDone += 1
                    subcorporaDoneSum += subcorpusSize
                    self.align(random.sample(range(nbLines), subcorpusSize),
                               tmpFile)
            except KeyboardInterrupt:
                toWrite = "(%i subcorpora, avg=%.2f) Alignment interrupted! " \
                          "Proceeding..." % (nbSubcorporaDone,
                                             1. * subcorporaDoneSum
                                             / nbSubcorporaDone)
            else:
                toWrite = "(%i subcorpora, avg=%.2f) Alignment done, " \
                          "proceeding... " % (nbSubcorporaDone,
                                              1. * subcorporaDoneSum
                                              / nbSubcorporaDone)
            print >> sys.stderr, "\r%s%s" % \
                  (toWrite, " " * (previousWriteLen - len(toWrite)))

            if nbLines > 2:
                # Add alignments from subcorpora of sizes 1 and nbLines
                weight1 = 2 * nb2 * math.log(1 - 2. / (nbLines + 1)) \
                          / (nbLines * math.log(1 - 1. / (nbLines + 1)))
                weightN = 2 * nb2 * math.log(1 - 2. / (nbLines + 1)) \
                          / (nbLines * math.log(1 -
                                                1. * nbLines / (nbLines + 1)))
                if weight1:
                    frac1, weight1 = math.modf(weight1)
                    weight1 = int(weight1)
                    for i in range(nbLines):
                        w = weight1
                        if random.random() < frac1:
                            w += 1
                        if w:
                            self.align([i], tmpFile, w)
                if weightN:
                    fracN, weightN = math.modf(weightN)
                    w = int(weightN)
                    if random.random() < fracN:
                        w += 1
                    if w:
                        self.align(range(nbLines), tmpFile, w)

            tmpFile.seek(0)
            self.weightFunc(tmpFile)
        finally:
            tmpFile.close()


    def align(self, lineIds, outputFile, weight=1):


        corpus = self.corpus
        languageRange = range(self.nbLanguages)
        ngramRange = range(2, self.indexN + 1)

        vec_word = {}   # {tuple(int): set(int)}
        vw_setdefault = vec_word.setdefault

        for n in range(1, self.indexN + 1):


            if n == 1:
                word_ap = {}
                wa_setdefault = word_ap.setdefault
                for lineId in lineIds:
                    for word in corpus[lineId]:
                        vec = wa_setdefault(word, [lineId])
                        if vec[-1] != lineId:
                            vec.append(lineId)
                # Group words according to the lines they appear on.
                for word, linesAp in word_ap.iteritems():
                    vw_setdefault(tuple(linesAp), set()).add(word)
            else:
                ngram_ap = {}
                na_setdefault = ngram_ap.setdefault
                ngramCorpus = self.ngramCorpora[n-2]
                for lineId in lineIds:
                    for ngram in ngramCorpus[lineId]:
                        na_setdefault(ngram, []).append(lineId)
                for ngram, linesAp in ngram_ap.iteritems():
                    vw_setdefault(tuple(linesAp), set()
                                  ).update(self.allNgrams[n-2][ngram])

            # Above part was changed with new option "-i", rest is identical


            minNbWords = self.minLanguages + self.minSize - 1
            for linesAp, wordSet in vec_word.iteritems():
                # Check if there are enough words
                if len(wordSet) < minNbWords:
                    continue

                # Check if there are words in at least minLanguages
                l = set()
                for word in wordSet:
                    l.add(self.wordLanguages[word])
                    if len(l) == self.minLanguages:
                        break
                if len(l) < self.minLanguages:
                    continue

                #wordSet = set(wordSet) # Now it is a a set already

                for lineId in linesAp:
                    words = corpus[lineId]
                    perfect = [[] for _ in languageRange]
                    context = [[] for _ in languageRange]
                    for wordPos, word in enumerate(words):
                        l = self.wordLanguages[word]
                        if word in wordSet:
                            perfect[l].append(wordPos)
                        else:
                            context[l].append(wordPos)

                    for candidate in (perfect, context):
                        nbLanguages = 0
                        for languageId, phrase in enumerate(candidate):
                            # Check for contiguity
                            if (self.contiguousFields[languageId] and phrase
                                and phrase[-1] - phrase[0] != len(phrase) - 1):
                                candidate[languageId] = []
                            # Check for length
                            elif not (self.minSize <= len(phrase)
                                      <= self.maxSize):
                                candidate[languageId] = []

                            if candidate[languageId]:
                                nbLanguages += 1

                        if nbLanguages < self.minLanguages:
                            continue

                        for i, phrase in enumerate(candidate):
                            prev = None
                            newPhrase = []
                            for wordPos in phrase:
                                if self.delimiter and prev is not None and \
                                   wordPos != prev + 1:
                                    newPhrase.append(0)
                                newPhrase.append(words[wordPos])
                                prev = wordPos
                            candidate[i] = newPhrase

                        stringToPrint = '\t'.join([' '.join([hex(w)[2:]
                                                             for w in phrase])
                                                   for phrase in candidate])
                        alString = '\t'.join([' '.join([self.allWords[w]
                                                            for w in phrase])
                                                  for phrase in candidate])
                        bucket = self.counts.setdefault(len(alString), {})
                        alHash = hash(alString)
                        alFreq = bucket.get(alHash)
                        if alFreq is None:
                            bucket[alHash] = weight
                            print >> outputFile, stringToPrint
                            self.nbAlignments += 1
                        else:
                            bucket[alHash] = alFreq + weight


    def _dummy_weight(self, inputFile):

        del self.corpus # We don't need it anymore
        nbSplits = self.nbLanguages - 1
        for line in inputFile:
            print >> self.weightedAlignmentFile, "%s\t-" % \
                  '\t'.join([' '.join([self.allWords[int(word, 16)]
                                       for word in phrase.split()])
                             for phrase in line.split('\t', nbSplits)])



