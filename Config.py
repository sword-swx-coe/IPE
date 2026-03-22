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

    # Check if the above ran successfully
    if (not os.path.exists(ieDir)):

        command = \
            "git clone git\@github.com:GITMCode/Electrodynamics.git " + ieDir
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
                exit();
    else:
        print(" --> " + ieDir + " already exists.")
        command = "git -C " + ieDir + " pull"
        run_command(command)
    command = "touch " + ieDir + "/src/Makefile.DEPEND";
    if (isVerbose):
        print(" --> creating DEPEND file in electrodynamics:")
    run_command($command)

    return

# ----------------------------------------------------------------------
# clone electrodynamics library (or update it)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# main code:
# ----------------------------------------------------------------------

args = parse_args()

