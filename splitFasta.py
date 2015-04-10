#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2014"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import os.path


# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "splitFasta.py", description = "Splits a multi fasta file into one file per fasta" )
prsr_arguments.add_argument( "str_fasta_file" , help = "Multi-fasta file to split." )
args = prsr_arguments.parse_args()


with open( args.str_fasta_file, "r" ) as hndl_fasta:

    str_file_base = os.path.splitext( os.path.basename( args.str_fasta_file ) )[0]
    lstr_content = []
    f_write = False
    i_counter = 1
    for str_line in hndl_fasta:
        if str_line[0] == ">":
            f_write = True
        else:
            f_write = False
        if f_write and len( lstr_content ) > 0:
            with open( "".join( [ str_file_base, "_", str( i_counter ), ".fasta" ] ), "w"  ) as hndl_write:
                hndl_write.writelines( lstr_content )
                lstr_content = []
                i_counter += 1
        lstr_content.append( str_line )
        
    if len( lstr_content ) > 0:
            with open( "".join( [ str_file_base, "_", str( i_counter ), ".fasta" ] ), "w"  ) as hndl_write:
                hndl_write.writelines( lstr_content )