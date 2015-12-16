__author__ = 'alienpunker'
import sys
from time import time
from CommonUtil import openFile, changeFields, getTempFIle, setProbability, getBestArray
import math
import random
from output import HTMLOutput
from Distribution import Distribution



maximumSize = 10000



class WordAligner:

# -1,0, -1,
#             False, '', None, 1,
#             7, '', 1)
    def __init__(self, inputFilenames):

        self.maxNbLines =0
        self.timeout = 10
        self.nbNewAlignments = -1
        self.discontiguousFields =''
        self.minLanguages = None
        self.minSize =1
        self.maxSize=7
        self.delimiter=None
        self.indexN =1
        self.writer = HTMLOutput(sys.stdout, 'utf-8', None)


        self.counts = {}
        self.nbAlignments = 0
        self.weightedAlignmentFile = getTempFIle(".al_lw")
        self.offsets = []
        nbLines = None
        self.numLang = 0


        try:
            self.files =[openFile(file) for file in inputFilenames]





            for file in self.files:
                offset = 0
                fileOffsets = []
                fileLanguages = None
                lineNumber = -1
                for lineNumber, line in enumerate(file):
                    fileLine = line.count('\t') + 1
                    if fileLanguages is None:
                        fileLanguages = fileLine
                        self.numLang += fileLine
                    else:
                        assert fileLine == fileLanguages, "Found %i columns " \
                               " instead of %i at line %i in file %s" % \
                               (fileLine, fileLanguages, lineNumber + 1, file.name)
                    fileOffsets.append(offset)
                    offset += len(line)
                if nbLines is None:
                    nbLines = lineNumber + 1
                else:
                    assert nbLines == lineNumber + 1, \
                           "Input files have different number of lines"
                self.offsets.append(getBestArray(fileOffsets))
                del fileOffsets












            if self.minLanguages is None:
                self.minLanguages = self.numLang
            else:
                self.minLanguages = self.minLanguages

            ncf = changeFields(self.discontiguousFields, self.numLang)
            self.contiguousFields = [(i + 1 not in ncf)
                                     for i in range(self.numLang)]

            if self.timeout < 0:
                self.timeout = None

            if self.maxNbLines < 1:
                nbCorpora = 1
            else:
                nbCorpora = int(math.ceil(1. * nbLines / self.maxNbLines))
                if self.timeout is not None:
                    self.timeout /= 1. * nbCorpora
            lines = range(nbLines)
            random.shuffle(lines)
            for nbCorpToDo in range(nbCorpora, 0, -1):
                selection = [lines.pop() for _ in
                             range(int(math.ceil(1. * len(lines) /
                                                  nbCorpToDo)))]
                selection.sort()    # Speed up disk access
                self.set_corpus(selection)
                self.run(self.timeout, self.nbNewAlignments)
            setProbability(self.weightedAlignmentFile, self.counts, self.writer)
        finally:
            self.weightedAlignmentFile.close()
            for file in self.files:
                file.close()























    def set_corpus(self, lines):

        self.corpus = [[] for _ in lines]
        self.allWords, self.wordLanguages = [], []
        allWordIds = [{} for _ in range(self.numLang)]
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
        self.wordLanguages.append(self.numLang)
        self.wordFreq.append(max(self.wordFreq) + 1)

        # Reassign word ids: smallest id for most frequent word
        sortedByFreq = sorted(range(len(self.allWords)),
                              key=self.wordFreq.__getitem__, reverse=True)
        self.allWords = [self.allWords[i] for i in sortedByFreq]
        self.wordLanguages = getBestArray([self.wordLanguages[i]
                                            for i in sortedByFreq],
                                           self.numLang)
        newPos = [None] * len(self.allWords)
        for i, wordId in enumerate(sortedByFreq):
            newPos[wordId] = i
        for i, line in enumerate(self.corpus): # Replace word ids in corpus
            self.corpus[i] = [newPos[wordId] for wordId in line]

        self.wordFreq.sort(reverse=True)
        self.wordFreq = getBestArray(self.wordFreq)


        ngramRange = range(2, self.indexN + 1)
        languageRange = range(self.numLang)

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
                        toWrite = "(%i subcorpora, avg=%.2f) " \
                                  "%i alignments, %i al/s" % \
                                  (nbSubcorporaDone,
                                   1. * subcorporaDoneSum / nbSubcorporaDone,
                                   self.nbAlignments, speed)
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
                    self.alignwords(random.sample(range(nbLines), subcorpusSize),
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
                            self.alignwords([i], tmpFile, w)
                if weightN:
                    fracN, weightN = math.modf(weightN)
                    w = int(weightN)
                    if random.random() < fracN:
                        w += 1
                    if w:
                        self.alignwords(range(nbLines), tmpFile, w)

            tmpFile.seek(0)
            self._dummy_weight(tmpFile)
        finally:
            tmpFile.close()


    def alignwords(self, lineIds, outputFile, weight=1):


        corpus = self.corpus
        languageRange = range(self.numLang)

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


            minNbWords = self.minLanguages + self.minSize - 1
            for linesAp, wordSet in vec_word.iteritems():
                if len(wordSet) < minNbWords:
                    continue

                l = set()
                for word in wordSet:
                    l.add(self.wordLanguages[word])
                    if len(l) == self.minLanguages:
                        break
                if len(l) < self.minLanguages:
                    continue

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

        del self.corpus
        nbSplits = self.numLang - 1
        for line in inputFile:
            print >> self.weightedAlignmentFile, "%s\t-" % \
                  '\t'.join([' '.join([self.allWords[int(word, 16)]
                                       for word in phrase.split()])
                             for phrase in line.split('\t', nbSplits)])



