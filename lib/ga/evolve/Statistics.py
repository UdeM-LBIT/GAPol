"""

:mod:`Statistics` -- statistical structure module
==========================================================================

This module have the class which is reponsible to keep statistics of each
generation. This class is used by the adapters and other statistics dump objects.

"""


class Statistics(object):
    """ Statistics Class - A class bean-like to store the statistics

    The statistics hold by this class are:

    **rawMax, rawMin, rawAve**
       Maximum, minimum and average of raw scores

    **rawDev, rawVar**
       Standard Deviation and Variance of raw scores

    **fitMax, fitMin, fitAve**
       Maximum, mininum and average of fitness scores

    **rawTot, fitTot**
       The total (sum) of raw scores and the fitness scores

    Example:
       >>> stats = ga_engine.getStatistics()
       >>> st["rawMax"]
       10.2
    """

    def __init__(self):
        """ The Statistics Class creator """

        # 'fit' means 'fitness'
        self.internalDict = {
            "rawMax": [],
            "rawMin": [],
            "rawAve": [],
            "rawDev": [],
            "rawMed": [],
            "rawVar": [],
            "fitMax": 0.0,
            "fitMin": 0.0,
            "fitAve": 0.0
        }

        self.descriptions = {
            "rawMax": "Maximum raw score for each evaluator",
            "rawMin": "Minimum raw score for evaluator",
            "rawAve": "Average of raw score for each evaluator",
            "rawDev": "Standard deviation of raw scores, for each evaluator",
            "rawVar": "Raw scores variance for each evaluator",
            "fitMax": "Maximum fitness",
            "fitMin": "Minimum fitness",
            "fitAve": "Fitness average",
        }

    
    def getRawScore(self, ind=0):
        rawdict = {
            "rawMax": self["rawMax"][ind],
            "rawMin": self["rawMin"][ind],
            "rawAve": self["rawAve"][ind],
            "rawDev": self["rawDev"][ind],
            "rawVar": self["rawVar"][ind]
        }
        return rawdict
        

    def __getitem__(self, key):
        """ Return the specific statistic by key """
        return self.internalDict[key]

    def __setitem__(self, key, value):
        """ Set the statistic """
        self.internalDict[key] = value

    def __len__(self):
        """ Return the length of internal stats dictionary """
        return len(self.internalDict)

    def __repr__(self):
        """ Return a string representation of the statistics """
        strBuff = "- Statistics\n"
        for k, v in self.internalDict.items():
            if isinstance(v, list):
                v = "[" + ", ".join(["%.2f"%vv for vv in v]) + "]"
            else:
                v = "%.2f"%v
            strBuff += "\t%-45s = %s\n" % (self.descriptions.get(k, k), v)
        return strBuff

    def asTuple(self):
        """ Returns the stats as a python tuple """
        return tuple(self.internalDict.values())

    def clear(self):
        """ Set all statistics to zero """
        for k,v in self.internalDict.items():
            if isinstance(v, list):
                self.internalDict[k] = []
            else:
                self.internalDict[k] = 0.0

    def items(self):
        """ Return a tuple (name, value) for all stored statistics """
        return self.internalDict.items()

    def clone(self):
        """ Instantiate a new Statistic class with the same contents """
        clone_stat = Statistics()
        self.copy(clone_stat)
        return clone_stat

    def copy(self, obj):
        """ Copy the values to the obj variable of the same class

        :param obj: the Statistics object destination

        """
        obj.internalDict = self.internalDict.copy()
        obj.descriptions = self.descriptions.copy()
