#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2014"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import os

str_example_usage = "Example: pair_samples_from_dir.py -t fastq -p _ -d input_dir -o paired_samples.txt"

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "pair_samples_from_dir.py", description = "Pair samples in a directory and make a samples file.\t"+str_example_usage )
prsr_arguments.add_argument( "-d", "--dir", dest = "str_dir_file" , help = "Directory containing samples." )
prsr_arguments.add_argument( "-t", "--file_type", dest = "str_file_type", help ="Suffix of file to look for." )
prsr_arguments.add_argument( "-o", "--out", dest = "str_sample_file", help = "Sample file" )
prsr_arguments.add_argument( "-p", "--prefix", dest = "str_prefix_sentinel", help = "Sentinel for the end of the prefix which is a key in the sample names that matches paired samples. Eg. _ for test_left.txt and test_right.txt" )
args = prsr_arguments.parse_args()

# End gracefully on the wrong input directory
if not os.path.exists( args.str_dir_file ):
    print "Path does not exist. Path = "+ args.str_dir_file
    exit( 1 )

# Get directory list    
ls_dirs = os.listdir( args.str_dir_file )
i_file_type_len = len( args.str_file_type )

# Reduce to a filtered list of just the file sof a given postfix and sort
ls_dirs = [ s_file for s_file in ls_dirs if len( s_file ) > i_file_type_len ]
ls_dirs = [ s_file for s_file in ls_dirs if s_file[ len( s_file ) - i_file_type_len : ] == args.str_file_type ]
ls_dirs.sort()

# Make pairs
# Holds the paired samples by the prefix key
dict_pairs = dict()
str_prev_key = None
str_prev_sample = None
for str_file in ls_dirs:

    # Get prefix key
    str_cur_key = str_file[ : str_file.index( args.str_prefix_sentinel ) ]
    print str_cur_key
    # If this key matches a previous key, they are pairs, store as such
    if str_prev_key == str_cur_key:
        dict_pairs[ str_cur_key ] = [ os.path.abspath( os.path.join( args.str_dir_file, str_prev_sample ) ),
	                              os.path.abspath( os.path.join( args.str_dir_file, str_file ) ) ]
        str_prev_key = None
        str_prev_sample = None
        continue
    
    # If the key does nto match the previous key, the prevous file has no pair, ignore, and store new key.
    if not str_prev_key == str_cur_key:
        str_prev_key = str_cur_key
        str_prev_sample = str_file
        continue

# Write to file format
# Key\tSample1\tSample2
with open( args.str_sample_file, "w" ) as hndl_output:
    hndl_output.writelines( [ "\t".join( [ str_key ] + dict_pairs[ str_key ] + [ "\n" ] ) 
                             for str_key in dict_pairs.keys() ] )
