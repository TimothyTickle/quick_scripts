#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2014"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import csv
import glob
import os


# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "rename_files.py", description = "Rename files giving a mapping file, an extension to keep, and potentially a directory make links in if not renaming.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "-x", "--extension", metavar = "search_extension", dest = "str_extension", default = None, required = True, help = "Extension to grep file to update." )
prsr_arguments.add_argument( "-m", "--map_file", dest = "str_mapping_file", required = True, help = "Mapping file (new_token\told_token)." )
prsr_arguments.add_argument( "-i", "--input_dir", metavar = "input_dir", dest = "str_read_directory", required = True, help = "The dir to look for files to update." )
prsr_arguments.add_argument( "-l", "--link_dir", metavar = "link_dir", dest = "str_link_directory", help = "If given, files will not be renamed but links will be made in this dir." )
prsr_arguments.add_argument( "-d", "--mode", metavar = "mode", dest = "str_mode", default = "flat", help = "Mode to run in. 'flat' = look in input directory, 'mut_bam' - rename recal bams in an RNA mutation directory structure. This is highly specific and mostly for me.")
args = prsr_arguments.parse_args()

# Constants
C_CHR_MAP_DELIMITER = "\t"
STR_MODE_STANDARD = "flat"
STR_MODE_RNA_MUT_BAM = "mut_bam"
STR_MODE_RNA_MUT_BAM_FILE = "recalibrated.bam"
STR_MODE_RNA_MUT_BAI_FILE = "recalibrated.bai"
STR_MODE_RNA_MUT_BAM_FOLDER_START = "misc"

# Hold the mappings { file name key: new name key }
dict_mappings = {}

# Read in mapping file
with open( args.str_mapping_file, "r" ) as hndl_open_file:
  cur_csv_reader = csv.reader( hndl_open_file, delimiter=C_CHR_MAP_DELIMITER )
  dict_mappings = dict([ [ lstr_mapping[1],lstr_mapping[0]]  for lstr_mapping in cur_csv_reader ])

# Read in contents of directory of files given an extension
lstr_files = None
# Flat / standard mode
args.str_mode = args.str_mode.lower()
if args.str_mode == STR_MODE_STANDARD:
  lstr_files = glob.glob( args.str_read_directory + os.sep + "*" + args.str_extension )
# RNA mut bam pipeline
elif args.str_mode == STR_MODE_RNA_MUT_BAM:
    lstr_files = []
    lstr_roots = os.listdir( args.str_read_directory )
    for str_root_dir in lstr_roots:
      if os.path.isdir( os.path.join( args.str_read_directory, str_root_dir ) ):
        lstr_run_files = os.listdir( os.path.join( args.str_read_directory, str_root_dir ) )
        lstr_run_files = [ os.path.join( args.str_read_directory, str_root_dir, str_file ) for str_file in lstr_run_files if os.path.isdir( os.path.join( args.str_read_directory, str_root_dir, str_file ) ) ]
        if not len( lstr_run_files ) == 1:
          print "ERROR, incomplete results!!! Could not explicitly find the bam folder for " + str_root_dir
          continue
        lstr_misc_files = os.listdir( lstr_run_files[0] )
        if STR_MODE_RNA_MUT_BAM_FILE in lstr_misc_files:
          lstr_files.append( os.path.join( lstr_run_files[0], STR_MODE_RNA_MUT_BAM_FILE ) )
          lstr_files.append( os.path.join( lstr_run_files[0], STR_MODE_RNA_MUT_BAI_FILE ) )

if args.str_link_directory:
  if not (os.path.exists(args.str_link_directory) or os.path.isdir(args.str_link_directory)):
    os.mkdir( args.str_link_directory )

lstr_mapping_keys = sorted( dict_mappings.keys(),reverse = True )
for str_original_file in lstr_files:
  str_rename = None
  # Update file name
  # Search for tokens
  # Go for largest matching token that starts at the beginning of the file name.
  for str_key in lstr_mapping_keys:
    if str_key in str_original_file:
      if args.str_mode == STR_MODE_STANDARD:
        if os.path.basename( str_original_file ).index( str_key ) == 0:
          str_rename = str_original_file.replace( str_key, dict_mappings[ str_key ] )
          break
      elif args.str_mode == STR_MODE_RNA_MUT_BAM:
        str_file_dir = str_original_file.split( os.path.sep )[-3]
        if str_file_dir == str_key:
          str_rename = os.sep.join( str_original_file.split( os.path.sep  )[:-1] ) + os.path.sep +  dict_mappings[ str_key ] + os.path.splitext( str_original_file )[1]
	  break

  if not str_rename:
    if args.str_mode == STR_MODE_STANDARD:
      print "Did not update "+str_original_file
      str_rename = str_original_file
    elif args.str_mode == STR_MODE_RNA_MUT_BAM:
      lstr_rename_tokens = str_original_file.split( os.path.sep  )
      str_rename = os.sep.join( lstr_rename_tokens[:-1] ) + os.path.sep + lstr_rename_tokens[-3] + os.path.splitext( str_original_file )[1]
      print "Did not find mapping for file. Updated from / with:"
      print str_original_file
      print lstr_rename_tokens[-3] + os.path.splitext( str_original_file )[1]

  # Update the names
  # Either rename files or make output file of links
  if str_rename:
    if args.str_link_directory:
      os.symlink( str_original_file, args.str_link_directory + os.sep + os.path.basename( str_rename ) )
#    else:
#      os.rename( str_original_file, str_rename )
