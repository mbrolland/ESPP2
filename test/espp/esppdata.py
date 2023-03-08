#!/usr/bin/env python3
#
# Create a pickle-file with various charactereistics and contents
# How/where this module is imported decides how the object-hierarchy
# is encoded in the pickle-file, which is important to reproduce the
# original pickle-files.... Yes, there is at least two hierarchies
# used in the wild, where class ESPPData is located in one (at least)
# one of the following two modules:
#
#    espp.esppdata
#    esppdata
#

import pickle
from datetime import datetime

class ESPPData:
    def __init__(self):
        # This order mimics the internal order in the pickle-file for
        # at least one user pickle-file... This aids making sure we
        # create pickle-files like the ones exported by ESPPv1
        self.espp = None
        self.currency = 'USD'
        self.taxPercentage = 15
        self.rawData = dict()
        self.broker = 'Charles Schwab & Co., Inc'

    def Add_DEPOSIT(self, date, qty, price, vpd):
        date = datetime.strptime(date, '%Y-%m-%d').date()
        rec = { 'date': date,
                'fee': 0.0,
                'n': qty,
                'price': price,
                'vpd': vpd }
        key = (date, 'DEPOSIT', qty, price, 260)  # TODO: Seqnum?
        self.rawData[key] = rec

    def WritePickle(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f, protocol=2)

if __name__ == '__main__':
    obj = ESPPData()
    obj.Add_DEPOSIT('2021-03-22', 43.0, 19.6775, 16.3)
    obj.WritePickle('test.pickle')
