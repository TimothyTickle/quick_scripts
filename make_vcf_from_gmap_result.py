#!/usr/bin/env python

# Constants
CHR_VCF_COMMENT = "#"
CHR_TRANSCRIPT_COMMENT = ">"
LSTR_COMMENTS = [ CHR_VCF_COMMENT, CHR_TRANSCRIPT_COMMENT ]
STR_RESULT_DELIMITER = "\t"

import argparse
import csv
import datetime
import os

prsr_arguments = argparse.ArgumentParser( prog = "mae_vcf_from_gmap_result.py", description = "Output from GMAP is changed to VCF file.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "str_input_file", help = "Input gmap result file." )
prsr_arguments.add_argument( "str_output_file", help = "Output SNP vcf file." )
args = prsr_arguments.parse_args()

# Holds the synthetic transcript name
str_transcript_name = None

# File name base without extension
str_file = os.path.splitext( os.path.basename( args.str_input_file ) )[ 0 ]

# Holds the VCF file a it is being built
lstr_header = [ "##fileformat=VCFv4.2", "##fileDate=" + str( datetime.date.today() ), "##Synthetically derived" ]
lstr_header.append( "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">" )
lstr_header.append( "\t".join( [ "#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", str_file ] ) )
lstr_vcf = []

# Used to complement the bases
sbuff_complement = string.maketrans( "ACGTacgt", "TGCAtgca" )

# Read in gmap result file
with open( args.str_input_file, "r" ) as hndl_gmap:
  for lstr_line in csv.reader( hndl_gmap, delimiter = STR_RESULT_DELIMITER ):
      
      # Ignore blank lines and comments, pull out transcript names
      if not lstr_line:
        continue
      if lstr_line[0][0] in LSTR_COMMENTS:
        if lstr_line[0][0] == CHR_TRANSCRIPT_COMMENT:
          str_transcript_name = lstr_line[ 0 ].split( STR_RESULT_DELIMITER )[ 0 ][ 1: ]
        continue

      # Build up VCF info
      str_chr, str_pos = lstr_line[ 2 ].split(":")
      ## Manage reverse complement information
      str_alt, str_ref = lstr_line[ 0 ].split( "/" )
      if str_chr[ 0 ] == "+":
          str_chr = str_chr[ 1: ]
      if str_chr[ 0 ] == "-":
          str_chr = str_chr[ 1: ]
          str_alt = str_alt.translate( sbuff_complement )
          str_ref = str_ref.translate( sbuff_complement )
      ## Manage VF file name
      if ( len( str_chr ) < 3 ) or not ( str_chr[ 0:3 ].lower() == "chr" ):
        str_chr = "chr" + str_chr
      lstr_vcf.append( "\t".join( [ str_chr, str_pos, str_transcript_name, str_ref.upper(), str_alt.upper(), ".", "PASS", ".", "GT", "0/1" ] ) )

# Write out file
lstr_vcf.sort()
with open( args.str_output_file, "w" ) as hndl_vcf:
  hndl_vcf.write( "\n".join( lstr_header + lstr_vcf ) )
