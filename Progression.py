__author__ = 'alienpunker'
class Progression:
    """Display progress percentage.

    -- self.step: float
        Base value to be added at each update.
    -- self.progress: float
        Current percentage, between 0. and 100.
    -- self.lastWrite: float
        The last displayed value.
    """

    def __init__(self, maxi):
        """Initializer.

        -- maxi: int
            Number of expected updates.
        """
        self.step = 100. / maxi
        self.progress = 0.
        self.lastWrite = -1

    def next(self, val=1):
        """Increase percentage and refresh display if needed.

        -- val: int
            Number of actual updates to be performed.
        """
        self.progress += val * self.step
        newWrite = int(round(self.progress))
        if newWrite != self.lastWrite:
            self.lastWrite = newWrite
            message("\r%3i%%" % newWrite)
