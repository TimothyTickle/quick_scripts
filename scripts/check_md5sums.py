#!/usr/bin/env python

######################################
# This checks md5sums of files
# Need the md5sum of files (formatted as md5sum outputs it)
# Need a file with the correct md5sums (md5sum\tsample)
######################################

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2014"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import csv
import os

# Indices for checking
I_INDEX_MD5 = 0
I_INDEX_FILE = 1

# MD5sum file delimiter
STR_DELIMIT = " "

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "check_md5sum.py", description = "Creates initial star aligner index for the rnaseq mutation pipeline", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "-c", "--check", metavar = "Check_file", dest = "str_check_file", required = True, help = "File of md5sums to check. md5sum file (delimited by space)." )
prsr_arguments.add_argument( "-t", "--truth", metavar = "Truth_file", dest = "str_truth_file", required = True, help = "File of md5sums which are true to check against. md5sum file (delimited by space)." )
args = prsr_arguments.parse_args()

print( "START check_md5sum.py" )

dict_truth_values = None
lstr_output = []
i_oks = 0
i_fails = 0
i_file_not_found = 0
STR_FILE_NOT_FOUND = "FILE NOT IN TRUTH FILE"

# File to output check results
str_out_file = args.str_check_file + ".check.txt"

# Read in truth
with open( args.str_truth_file,'r') as hndl_truth_file:
  csv_truth = csv.reader( hndl_truth_file, delimiter = STR_DELIMIT )
  dict_truth_values = dict([ [lstr_values[1], lstr_values[0]] for lstr_values in csv_truth ])
  print( "Read in truth file of " + str( len( dict_truth_values ) ) + " unique entries." )

# Check against truth and make output
with open( args.str_check_file, 'r' ) as hndl_check_file:
  csv_check = csv.reader( hndl_check_file, delimiter = STR_DELIMIT )
  for lstr_checking in csv_check:
    str_md5sum_truth = dict_truth_values.get( lstr_checking[ I_INDEX_FILE ], STR_FILE_NOT_FOUND )
    if lstr_checking[ I_INDEX_MD5 ] == str_md5sum_truth:
      lstr_output.append( "OK "+lstr_checking[ I_INDEX_FILE ] )
      i_oks = i_oks + 1
    elif( str_md5sum_truth == STR_FILE_NOT_FOUND ):
      lstr_output.append( "FAIL ("+STR_FILE_NOT_FOUND+") "+lstr_checking[ I_INDEX_FILE ] )
      i_file_not_found = i_file_not_found + 1
    else: 
      lstr_output.append( "FAIL (md5sum) "+lstr_checking[ I_INDEX_FILE ] )
      i_fails = i_fails + 1

print( "Writting results to "+str_out_file+"." )
with open( str_out_file, 'w' ) as hndl_out:
  hndl_out.write( "OK:   " + str( i_oks ) + os.linesep )
  hndl_out.write( "Fail (md5sum): " + str( i_fails ) + os.linesep)
  hndl_out.write( "Fail (" + STR_FILE_NOT_FOUND + "): " + str( i_file_not_found ) + os.linesep )
  hndl_out.write( os.linesep.join( lstr_output ) )

print( "END check_md5sum.py" )
