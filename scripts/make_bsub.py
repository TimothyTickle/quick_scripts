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

str_placeholder = "###"

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "make_bsub.py", description = "Helps make many bsub commands.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "-c", "--command", metavar = "Command_Template", dest = "str_command_template", default = None, required = True, help = "The command to bsub with " + str_placeholder + " which will be replaced by sample names." )
prsr_arguments.add_argument( "-e", "--email", dest = "f_email", action = "store_true", default = False, help = "If this flag is given an email will be generated to you for EACH command given containing the status of the run." )
prsr_arguments.add_argument( "-g", "--group", type = int, metavar = "Group_Size", dest = "i_group_size", default = 10, help = "The number of bsub commands per file made." )
prsr_arguments.add_argument( "-m", "--memory", metavar = "Memory", dest = "str_memory", default = "8", help = "The amount of memory in GB needed." )
prsr_arguments.add_argument( "-o", "--out", metavar = "Output_File", dest = "str_out_file", default = "output_bsub", help = "The base name of the sh file(s) that will be created." )
prsr_arguments.add_argument( "-q", "--queue", metavar = "Queue", dest = "str_queue", default = "regevlab", help = "The queue to bsub in." )
prsr_arguments.add_argument( "-s", "--samples", metavar = "Sample_File", dest = "str_sample_file", default = None, required = True,  help = "The file containing samples. One sample name per line (abs paths if needed should be in the file)." )
args = prsr_arguments.parse_args()

ls_str_commands = []

# Read sample file and create commands based on sample list.
with open( args.str_sample_file, "r" ) as hndl_open_file:
  for str_sample in hndl_open_file:

    # Trim off endline
    str_sample = str_sample.replace( os.linesep, "" )

    # Start command
    str_command = "bsub -q " + args.str_queue + " -R rusage[mem=" + args.str_memory + "] "

    # Add email if requested
    if args.f_email:
      str_command = str_command + "-N "

    # Add error and out files
    str_command = str_command + "-e " + str_sample + ".err -o " + str_sample + ".out "

    # Make command
    # Add command
    str_command = str_command + args.str_command_template.replace( str_placeholder, str_sample )

    ls_str_commands.append( str_command )

# Write commands to ( multiple sh scripts to run )
i_file_index = 0
hndl_out = open( args.str_out_file + str( i_file_index ) + ".sh", "w" )
i_file_index = i_file_index + 1

# Write files
for i_index in xrange( 0, len( ls_str_commands ) ):
  hndl_out.write( ls_str_commands[ i_index ] + os.linesep )
  if ( ( i_index + 1 ) % args.i_group_size ) == 0:
    hndl_out.close()
    hndl_out = open( args.str_out_file + str( i_file_index ) + ".sh", "w" )
    i_file_index = i_file_index + 1
hndl_out.close()
  

