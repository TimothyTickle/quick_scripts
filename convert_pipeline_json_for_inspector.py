#!/usr/bin/env python

import argparse
import json
import shutil
import os
import sys

# Constants
c_STR_INSPECTOR_TP = "TP"
c_STR_INSPECTOR_FP = "FP"
c_STR_INSPECTOR_FN = "FN"
c_STR_INSPECTOR_RNA_BAM = u"RNA"
c_STR_INSPECTOR_DNA_BAM = u"DNA"

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "convert_pipeline_json_for_inspector.py", description = "Converts the JSON file from the validation pipeline to a file useable for the galaxy inspector.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( dest = "output_dir", help = "Output dir." )
prsr_arguments.add_argument( dest = "input_json", help = "Input JSON file." )
args_call = prsr_arguments.parse_args()

# List of files to make links [ [ str_from_path, str_to_path ] ]
llstr_files = []
# Automatically made updated file
str_output_json = os.path.basename( args_call.input_json )
str_output_json = os.path.join( args_call.output_dir, "pipeline_inspector.json" )

# If the output dir or the updated json file exist, fail.
if os.path.exists( str_output_json ):
  print( "The json file that would be made already exist. Please delete this file or rename it before running this script. File = " + str_output_json )
  sys.exit( 101 )
if os.path.exists( args_call.output_dir ):
  print( "The output directory already exits. Please delete it to move forward. Dir = " + args_call.output_dir )
  sys.exit( 102 )

# Make output dir if it does not exist
if not os.path.exists( args_call.output_dir ):
  os.mkdir( args_call.output_dir )

# Read in JSON file
input_json = None
with open( args_call.input_json, "r" ) as hndl_input_json:
  input_json = json.loads( hndl_input_json.read() )
if not input_json:
  print( "JSON file was empty." )
  sys.exit( 103 )

# Update paths and store links
for str_key, dict_sample in input_json.items():
  print dict_sample
  # In each sample update the sample name to the input dir
  str_dna_bam = dict_sample[ c_STR_INSPECTOR_DNA_BAM ]
  str_dna_bam_new = os.path.join( args_call.output_dir, os.path.basename( str_dna_bam ) )
  str_rna_bam = dict_sample[ c_STR_INSPECTOR_RNA_BAM ]
  str_rna_bam_new = os.path.join( args_call.output_dir, os.path.basename( str_rna_bam ) )

  dict_sample[ c_STR_INSPECTOR_DNA_BAM ] = str_dna_bam_new 
  dict_sample[ c_STR_INSPECTOR_RNA_BAM ] = str_rna_bam_new 

  llstr_files.append( [ str_dna_bam, str_dna_bam_new ] )
  llstr_files.append( [ str_rna_bam, str_rna_bam_new ] )

# Make links
for str_old_file, str_new_file in llstr_files: 
  os.symlink( str_old_file, str_new_file ) 
  os.symlink( str_old_file + ".bai", str_new_file + ".bai" )

# Open handle and write json object to file
with open( str_output_json, "w" ) as hndl_output:
  hndl_output.write( json.dumps( input_json, sort_keys=True, indent=2 ) )
