#!/usr/bin/env python3

# import espp.esppdata
import mkesppdata1

if __name__ == '__main__':
    # obj = espp.esppdata.ESPPData()
    obj = mkesppdata1.CreateESPPData()
    obj.Add_DEPOSIT('2021-03-22', 43.0, 19.6775, 16.3)
    obj.WritePickle('test2.pickle')
