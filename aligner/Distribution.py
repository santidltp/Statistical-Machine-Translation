__author__ = 'alienpunker'
from array import array
import random

class Distribution:

    def __init__(self, function, start, end):

        values = [function(x) for x in xrange(start, end + 1)]
        fact = 1. / sum(values)
        s = 0.
        for i, v in enumerate(values):
            s += fact * v
            values[i] = s
        self.values = array('f', values)
        self.start = start
        self.nbVal = end + 1 - start

    def next(self):
        """Return new random integer, according to distribution."""
        r = random.random()
        values = self.values
        i = -1
        for i in xrange(self.nbVal):
            if r < values[i]:
                return self.start + i
        return self.start + i    # We should never reach this line

