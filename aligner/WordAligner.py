__author__ = 'alienpunker'
import sys
from time import time
from CommonUtil import openFile, changeFields, getTempFIle, setProbability, getBestArray
import math
import random
from output import HTMLOutput
from balance import balance

maximumSize = 10000

class WordAligner:
    def __init__(self, inputFilenames):

        self.maxNbLines =0
        self.time = 10
        self.archivos = inputFilenames
        self.numNewAligns = -1
        self.discontiguousFields =''
        self.minSize =1
        self.maxSize=7
        self.dlmn=None
        self.indexer =1
        self.writer = HTMLOutput(sys.stdout, 'utf-8', None)
        self.counter = {}
        self.numAligns = 0
        self.AlignedFile = getTempFIle(".al_lw")
        self.offsets = []
        numLines = None
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
                        assert fileLine == fileLanguages, "There is %i columns " \
                               " instead of %i at line %i in file %s" % \
                               (fileLine, fileLanguages, lineNumber + 1, file.name)
                    fileOffsets.append(offset)
                    offset += len(line)
                if numLines is None:
                    numLines = lineNumber + 1
                else:
                    assert numLines == lineNumber + 1, \
                           "Input files have different number of lines"
                self.offsets.append(getBestArray(fileOffsets))
                del fileOffsets
            self.minLanguages = self.numLang
            narft = changeFields(self.discontiguousFields, self.numLang)
            self.contiguousFields = [(i + 1 not in narft) for i in range(self.numLang)]
            if self.maxNbLines < 1:
                numCorpus = 1
            else:
                numCorpus = int(math.ceil(1. * numLines / self.maxNbLines))
                self.time /= 1. * numCorpus
            lines = range(numLines)
            random.shuffle(lines)
            for numCurpTres in range(numCorpus, 0, -1):
                select = [lines.pop() for _ in range(int(math.ceil(1. * len(lines) / numCurpTres)))]
                select.sort()
                self.prepareCorpus(select)
                self.run(self.time, self.numNewAligns)
            setProbability(self.AlignedFile, self.counter, self.writer)
        finally:
            self.AlignedFile.close()
            for file in self.files:
                file.close()


    def prepareCorpus(self, lines):

        self.corpus = [[] for _ in lines]
        self.words, self.wordLanguages = [], []
        wIds = [{} for _ in range(self.numLang)]
        numLangFlag = 0
        for file, fileOff in zip(self.files, self.offsets):
            for lineId, offsetId in enumerate(lines):
                file.seek(fileOff[offsetId])
                line = self.corpus[lineId]
                for i, sentence in enumerate(file.readline().split('\t')):
                    languageId = i + numLangFlag
                    wordIds = wIds[languageId]
                    for word in sentence.split():
                        wordId = wordIds.get(word)
                        if wordId is None:
                            wordId = len(self.words)
                            wordIds[word] = wordId
                            self.words.append(word)
                            self.wordLanguages.append(languageId)
                        line.append(wordId)
            numLangFlag = languageId + 1

        self.wFr = [0] * len(self.words)

        for line in self.corpus:
            for wordId in set(line):
                self.wFr[wordId] += 1

        self.words.append(self.dlmn)
        self.wordLanguages.append(self.numLang)
        self.wFr.append(max(self.wFr) + 1)

        srtfrqw = sorted(range(len(self.words)), key=self.wFr.__getitem__, reverse=True)
        self.words = [self.words[i] for i in srtfrqw]
        self.wordLanguages = getBestArray([self.wordLanguages[i] for i in srtfrqw], self.numLang)
        new_Pos = [None] * len(self.words)
        for i, wordId in enumerate(srtfrqw):
            new_Pos[wordId] = i
        for i, line in enumerate(self.corpus): # Replace word ids in corpus
            self.corpus[i] = [new_Pos[wordId] for wordId in line]

        self.wFr.sort(reverse=True)
        self.wFr = getBestArray(self.wFr)
        ngramgrw = range(2, self.indexer + 1)
        languagegrw = range(self.numLang)
        allNgramIds = [{} for _ in ngramgrw]
        self.allNgrams = [[] for _ in ngramgrw]
        self.ngramCorpora = [[] for _ in ngramgrw]

        for line in self.corpus:
            sentences = [[] for _ in languagegrw]
            ngramSentences = [set() for _ in ngramgrw]
            for word in line:
                sentences[self.wordLanguages[word]].append(word)
            for s in sentences:
                s = tuple(s)
                lastIdx = len(s) + 1
                for one in range(2, min(self.indexer+1, lastIdx)):
                    ngids = allNgramIds[one-2]
                    ngs = self.allNgrams[one-2]
                    ngsen = ngramSentences[one-2]
                    for i in range(lastIdx - one):
                        ng = s[i:i+one]
                        ngid = ngids.get(ng)
                        if ngid is None:
                            ngid = len(ngs)
                            ngids[ng] = ngid
                            ngs.append(ng)
                        ngsen.add(ngid)
            for one in ngramgrw:
                self.ngramCorpora[one-2].append(sorted(ngramSentences[one-2]))

    def principal(self, k):
        return 1. / (k * math.log(1 - 1. * k / (len(self.corpus) + 1)))

    def run(self, timeout, num_newAlgn):

        numLines = len(self.corpus)
        if numLines > 2:
            nextRandomSize = balance(self.principal, 2, numLines - 1).next
        else:
            nextRandomSize = balance(self.principal, 1,numLines).next

        nssecnd = 0
        nsubach = 0
        nsubachsum = 0
        prevdl = 0
        prevasd = 0
        lstwrt = startTime = time()
        speed = sys.maxint

        print >> sys.stderr, "\rWorking, please wait..."
        tmpFile = getTempFIle(".al")

        try:
            try:
                while speed > num_newAlgn:
                    t = time()
                    if timeout is not None and t - startTime >= timeout:
                        break
                    elapsedTime = t - lstwrt
                    if nsubach >= 1 and elapsedTime >= 1:
                        speed = int(math.ceil((self.numAligns -
                                               prevdl) / elapsedTime))
                        prevdl = self.numAligns
                        lstwrt = t


                    subcorpusSize = nextRandomSize()
                    while subcorpusSize > maximumSize:
                        subcorpusSize = nextRandomSize()
                    if subcorpusSize == 2:
                        nssecnd += 1

                    nsubach += 1
                    nsubachsum += subcorpusSize
                    self.alignwords(random.sample(range(numLines), subcorpusSize),
                               tmpFile)
            except KeyboardInterrupt:
                pass

            if numLines > 2:
                wnum1 = 2 * nssecnd * math.log(1 - 2. / (numLines + 1)) / (numLines * math.log(1 - 1. / (numLines + 1)))
                wnum2 = 2 * nssecnd * math.log(1 - 2. / (numLines + 1)) / (numLines * math.log(1 -  1. * numLines / (numLines + 1)))
                if wnum1:
                    frac1, wnum1 = math.modf(wnum1)
                    wnum1 = int(wnum1)
                    for i in range(numLines):
                        wei = wnum1
                        if random.random() < frac1:
                            wei += 1
                        if wei:
                            self.alignwords([i], tmpFile, wei)
                if wnum2:
                    fracN, wnum2 = math.modf(wnum2)
                    wei = int(wnum2)
                    if random.random() < fracN:
                        wei += 1
                    if wei:
                        self.alignwords(range(numLines), tmpFile, wei)

            tmpFile.seek(0)
            self._weights(tmpFile)
        finally:
            tmpFile.close()
            print >> sys.stderr, "\rDone, please check your output file."

    def _weights(self, inputFile):

        del self.corpus
        diffe = self.numLang - 1
        for line in inputFile:
            print >> self.AlignedFile, "%s\t-" % '\t'.join([' '.join([self.words[int(pra, 16)] for pra in frse.split()]) for frse in line.split('\t', diffe)])


    def alignwords(self, lineIds, outputFile, weight=1):

        corpus = self.corpus
        lnrange = range(self.numLang)

        word_dict = {}
        vw_dict = word_dict.setdefault

        for ytn in range(1, self.indexer + 1):
            if ytn == 1:
                word_ap = {}
                wa_setdefault = word_ap.setdefault
                for lineId in lineIds:
                    for word in corpus[lineId]:
                        vec = wa_setdefault(word, [lineId])
                        if vec[-1] != lineId:
                            vec.append(lineId)
                for word, linesAp in word_ap.iteritems():
                    vw_dict(tuple(linesAp), set()).add(word)
            else:
                ngram_ap = {}
                na_setdefault = ngram_ap.setdefault
                ngramCorpus = self.ngramCorpora[ytn-2]
                for lineId in lineIds:
                    for ngram in ngramCorpus[lineId]:
                        na_setdefault(ngram, []).append(lineId)
                for ngram, linesAp in ngram_ap.iteritems():
                    vw_dict(tuple(linesAp), set()).update(self.allNgrams[ytn-2][ngram])

            minNbWords = self.minLanguages + self.minSize - 1
            for linesAp, wordSet in word_dict.iteritems():
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
                    golpe = [[] for _ in lnrange]
                    contexto = [[] for _ in lnrange]
                    for posicionPalabra, word in enumerate(words):
                        l = self.wordLanguages[word]
                        if word in wordSet:
                            golpe[l].append(posicionPalabra)
                        else:
                            contexto[l].append(posicionPalabra)

                    for candidate in (golpe, contexto):
                        numlang = 0
                        for languageId, prsh in enumerate(candidate):
                            if (self.contiguousFields[languageId] and prsh and prsh[-1] - prsh[0] != len(prsh) - 1):
                                candidate[languageId] = []
                            elif not (self.minSize <= len(prsh)
                                      <= self.maxSize):
                                candidate[languageId] = []

                            if candidate[languageId]:
                                numlang += 1

                        if numlang < self.minLanguages:
                            continue

                        for i, prsh in enumerate(candidate):
                            prev = None
                            newPhrase = []
                            for posicionPalabra in prsh:
                                if self.dlmn and prev is not None and \
                                   posicionPalabra != prev + 1:
                                    newPhrase.append(0)
                                newPhrase.append(words[posicionPalabra])
                                prev = posicionPalabra
                            candidate[i] = newPhrase

                        paraImprii = '\t'.join([' '.join([hex(w)[2:] for w in prsh]) for prsh in candidate])
                        alString = '\t'.join([' '.join([self.words[w] for w in prsh])  for prsh in candidate])
                        valde = self.counter.setdefault(len(alString), {})
                        vendedor = hash(alString)
                        cursor = valde.get(vendedor)
                        if cursor is None:
                            valde[vendedor] = weight
                            print >> outputFile, paraImprii
                            self.numAligns += 1
                        else:
                            valde[vendedor] = cursor + weight


if __name__ == '__main__':

    args =sys.argv[1:]
    falg, temp = not False, None
    from WordAligner import WordAligner
    WordAligner(args)