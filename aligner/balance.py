__author__ = 'alienpunker'
from array import array
import random

class balance:

    def __init__(self, function, beg, fin):
        iVal = [function(x) for x in range(beg, fin + 1)]
        factur = 1. / sum(iVal)
        s = 0.
        for i, v in enumerate(iVal):
            s += factur * v
            iVal[i] = s
        self.values = array('f', iVal)
        self.start = beg
        self.numVal = fin + 1 - beg

    def next(self):
        r = random.random()
        values = self.values
        i = -1
        for i in range(self.numVal):
            if r < values[i]:
                return self.start + i
        return self.start + i

