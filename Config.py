#!/usr/bin/env python3

import os
import argparse

IsVerbose = False

# ----------------------------------------------------------------------
# Function to parse input arguments
# ----------------------------------------------------------------------

def parse_args():

    parser = argparse.ArgumentParser(description = 'Configure IPE Makefiles')

    parser.add_argument('-name', \
                        help = 'job name', \
                        default = 'boring_name')

    parser.add_argument('-v',  \
                        action='store_true', default = False, \
                        help = 'set verbose to true')
    
    args = parser.parse_args()

    return args

# ----------------------------------------------------------------------
# run system command
# ----------------------------------------------------------------------

def run_command(command):
    if (IsVerbose):
        print("   -> Running Command : ")
        print("      ", command)
    os.system(command)
    return True

# ----------------------------------------------------------------------
# clone electrodynamics library (or update it)
# ----------------------------------------------------------------------

def get_electrodynamics(ieDir = "ext/Electrodynamics"):

    didWork = True
    
    # Check if the above ran successfully
    if (not os.path.exists(ieDir)):

        command = \
            "git clone git@github.com:GITMCode/Electrodynamics.git " + ieDir
        if (IsVerbose):
            print("-> Attempting to clone GITMCode/Electrodynamics with ssh.")
        run_command(command)

        # If this fails, the script will *not* crash.
        #   therefore, need to check if it was successful:
        if (os.path.exists(ieDir)):
            print("-> Electrodynamics was cloned successfully!")
        else:
            
            print("-> git clone with SSH failed. Trying HTTPS...")
            command = \
                "git clone https://github.com/GITMCode/Electrodynamics.git " \
                + ieDir
            run_command(command)
            # If this fails, the script will exit with an error message
            if (os.path.exists(ieDir)):
                print("-> Electrodynamics (https) was cloned successfully!")
            else:
                print("-> git clone with HTTPS failed. Giving up...")
                return False
    else:
        print(" --> " + ieDir + " already exists.")
        command = "git -C " + ieDir + " pull"
        run_command(command)
    command = "touch " + ieDir + "/src/Makefile.DEPEND";
    if (IsVerbose):
        print(" --> creating DEPEND file in electrodynamics:")
    run_command(command)

    return didWork

# ----------------------------------------------------------------------
# clone indices library (or update it)
# ----------------------------------------------------------------------

def get_indices(ioDir = "ext/srcIndices"):

    didWork = True
    
    # Check if the above ran successfully
    if (not os.path.exists(ioDir)):

        command = \
            "git clone git@github.com:GITMCode/srcIndices.git " + ieDir
        if (IsVerbose):
            print("-> Attempting to clone GITMCode/srcIndices with ssh.")
        run_command(command)

        # If this fails, the script will *not* crash.
        #   therefore, need to check if it was successful:
        if (os.path.exists(ioDir)):
            print("-> srcIndices was cloned successfully!")
        else:
            
            print("-> git clone with SSH failed. Trying HTTPS...")
            command = \
                "git clone https://github.com/GITMCode/srcIndices.git " \
                + ioDir
            run_command(command)
            # If this fails, the script will exit with an error message
            if (os.path.exists(ioDir)):
                print("-> srcIndices (https) was cloned successfully!")
            else:
                print("-> git clone with HTTPS failed. Giving up...")
                return False
    else:
        print(" --> " + ioDir + " already exists.")
        command = "git -C " + ioDir + " pull"
        run_command(command)
    command = "touch " + ioDir + "/src/Makefile.DEPEND";
    if (IsVerbose):
        print(" --> creating DEPEND file in srcIndices/src:")
    run_command(command)

    return didWork

# ----------------------------------------------------------------------
# 
# ----------------------------------------------------------------------

def make_makefile_dirs(mainDir):

    baselineDirsFile = mainDir + '/build/Makefile.dirs.base'
    dirsFile = mainDir + '/build/Makefile.dirs'
    baseDirString = 'BASEDIR = ' + mainDir
    
    if (IsVerbose):
        print(' -> Reading file : ', baselineDirsFile)
    fpin = open(baselineDirsFile, 'r')
    allLines = fpin.readlines()
    fpin.close()

    command = 'rm -f ' + dirsFile
    run_command(command)
    if (IsVerbose):
        print(' -> Writing file : ', dirsFile)
    fpout = open(dirsFile, 'w')
    fpout.write('\n')
    fpout.write(baseDirString + '\n')
    fpout.write('\n')
    for line in allLines:
        fpout.write(line)
    fpout.close()
    return dirsFile
    
# ----------------------------------------------------------------------
# main code:
# ----------------------------------------------------------------------

args = parse_args()
if (args.v):
    IsVerbose = True

mainDir = os.getcwd()

makefileDirs = make_makefile_dirs(mainDir)

mileDir = 'ext/Electrodynamics'

didWork = get_electrodynamics(ieDir = mileDir)
if (not didWork):
    print('Downloading electrodynamics library failed!')
    exit()

command = \
    'cd ' + mileDir + '/build ; ' + \
    'rm -f Makefile.dirs ; ' + \
    'ln -s ' + makefileDirs + ' .'
run_command(command)

ioDir = "ext/srcIndices"
didWork = get_indices(ioDir = ioDir)
if (not didWork):
    print('Downloading indices library failed!')
    exit()
command = \
    'cd ' + ioDir + '/build ; ' + \
    'rm -f Makefile.dirs ; ' + \
    'ln -s ' + makefileDirs + ' .'
run_command(command)

command = 'rm -f Makefile'
run_command(command)

command = 'ln -s build/Makefile.um.maindir ./Makefile'
run_command(command)

