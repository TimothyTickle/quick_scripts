#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2015"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import gzip
import os

# Constants
VCF_HEADER_CONTIG_MARKER = "##contig=<ID="
VCF_CHR = "chr"
I_VCF_CHR = len( VCF_CHR )

# Indicates if the VCF_CHR should be added
f_add_vcf_chr = None

def func_starts_with( str_starting_token, str_word ):
  i_token = len( str_starting_token )
  if len( str_word ) < i_token:
    return False
  return str_word[ : i_token ] == str_starting_token

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "switch_chr_vcf.py", description = "Adds or removes chr in a vcf file. Switches it from one format to another." )
prsr_arguments.add_argument( dest = "str_input_file" , help = "Input vcf file." )
prsr_arguments.add_argument( dest = "str_output_file", help = "Output vcf file." )
args = prsr_arguments.parse_args()

# Handle normal vcf.gz or vcf files
str_in_ext = os.path.splitext( args.str_input_file )[ 1 ]
str_out_ext = os.path.splitext( args.str_output_file )[ 1 ]
handle_old_vcf = gzip.open( args.str_input_file, "rb" ) if str_in_ext == ".gz" else open( args.str_input_file, "r" )
handle_new_vcf = gzip.open( args.str_output_file, "wb" ) if str_out_ext == ".gz" else open( args.str_output_file, "w" )

# Read through the vcf
# Update the header info ( nomenclature )
# Update the vcf data details ( nomenclature )
for str_line in handle_old_vcf:
  # Update the comments / header in the contig id entries
  if str_line[ 0 ] == "#":
    # Look for contig id
    if func_starts_with( str_starting_token=VCF_HEADER_CONTIG_MARKER, str_word=str_line ):
      # Update contig id
      lstr_contig_tokens = str_line.split( "<ID=" )
      str_name, str_length = lstr_contig_tokens[ 1 ].split( "," )
      if func_starts_with( str_starting_token=VCF_CHR, str_word=str_name ):
        str_name = str_name[ I_VCF_CHR : ] 
        f_add_vcf_chr = False
      else:
        str_name = VCF_CHR + str_name
        f_add_vcf_chr = True
      str_line = lstr_contig_tokens[ 0 ] + "<ID=" + str_name + "," + str_length
    # Store comments
    handle_new_vcf.write( str_line )
  else:
    # Incase there was no contig info in the header
    if f_add_vcf_chr is None:
      f_add_vcf_chr = not func_starts_with( str_starting_token=VCF_CHR, str_word=str_line )
    # Update feature entry
    if f_add_vcf_chr:
      if not func_starts_with( str_starting_token=VCF_CHR, str_word=str_line ):
        str_line = VCF_CHR + str_line
    else:
      if func_starts_with( str_starting_token=VCF_CHR, str_word=str_line ):
        str_line = str_line[ I_VCF_CHR : ]
    handle_new_vcf.write( str_line )
handle_old_vcf.close()
handle_new_vcf.close()
