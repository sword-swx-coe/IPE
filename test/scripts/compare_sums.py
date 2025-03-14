#!/usr/bin/env python
from netCDF4 import Dataset
from sys import argv
from os.path import exists
import numpy as np

if len(argv) != 3:
    print('Usage: compare_sums.py outputfile referencefile')
    exit
a = Dataset(argv[1])
f = open(argv[2],'r')
f.readline() # skip header
lines = f.readlines()
b = {}
for line in lines:
    key, value = line.split()
    b[key] = value

print('{:<29} {:<18} {:<18} {:<18}'.format('variable_name', 'sum_of_squares', 'reference', '|difference|/reference'))
for key in a.variables.keys():
    var = np.float64(a.variables[key][:])
    sum2 = np.sum(var**2)
    ref  = np.float64(b[key])
    print('{:<28} {:+18.10e} {:+18.10e} {:+18.10e}'.format(key, sum2, ref,
                                                           abs(sum2-ref)/ref))


if __name__ == '__main__':
    try:
        main()
    except:
        pass
