#!/usr/bin/env python

# Sanger and illumina 8
str_s_8 = "!\"#$%&'()*+,-./0123456789:"
# Sanger, solexa and illumina 8
str_s_o_8 = ";<=>?"
# Sanger, solexa, illumina 5, illumina 8
str_s_o_3_8 = "@A"
# All sequencers (not discriminant)
str_all = "BCDEFGHIJ"
# Solexa, Illumina 1.3, Illumina 1.5
str_o_3_5 = "KLMNOPQRSTUVWXYZ[\]^_`abcdefgh"
# Not valid
str_not_valid = "ijklmnopqrstuvwxyz{|}~"

set_ascii = set()

i_counter = 0

import argparse

prsr_arguments = argparse.ArgumentParser( prog = "which_fastq_format", description = "Guesses the fastq format of a file.", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( dest = "fastq", action = "store", help = "Input fastq file to guess." )
args = prsr_arguments.parse_args()

with open( args.fastq, "r" ) as hndl_fastq:

  print "Reading file "+args.fastq

  for str_line in hndl_fastq:
    i_counter = i_counter + 1

    if( ( i_counter % 4 ) == 0 ):
      set_ascii = set_ascii.union( set( str_line ) )

set_ascii = set_ascii.difference( set(["\n"]) )
print "The following quality scores were found."
print sorted(list( set_ascii ))

f_s_8 = len( [ 1 for str_quality in str_s_8 if str_quality in set_ascii ])
f_s_o_8 = len( [ 1 for str_quality in str_s_o_8 if str_quality in set_ascii ])
f_s_o_3_8 = len( [ 1 for str_quality in str_s_o_3_8 if str_quality in set_ascii ])
f_o_3_5 = len( [ 1 for str_quality in str_o_3_5 if str_quality in set_ascii ])
f_not_valid = len( [ 1 for str_quality in str_not_valid if str_quality in set_ascii ])

if f_not_valid:
  print "Not valid, contained values too high for fastq quality scores. ie "+str_not_valid

if f_s_8:
  if "J" in set_ascii:
    print "This must be Illumina 1.8+ Phred+33."
  else:
    print "This file may either be Sanger Phred+33 or Illumina 1.8+ Phred+33"
  exit( 0 )

if f_s_o_8:
  if f_s_3_5:
    print "This must be Solexa+64."
    exit(0)
  if "J" in set_ascii:
    print "This is either Solexa+64 or Illumina 1.8+ Phred+33."
    exit( 0 )
  print "This could be either Sanger Phred+33, Solexa+64 or Illumina 1.8+ Phred+33"
  exit( 0 )

if f_s_o_3_8:
  if f_s_8:
    if "J" in set_ascii:
      print "This must be Illumina 1.8+ Phred+33."
      exit( 0 )
    else:
      print "This file may either be Sanger Phred+33 or Illumina 1.8+ Phred+33"
      exit( 0 )
  elif f_s_o_8:
    if "J" in set_ascii:
      print "This file is either Solexa+64 or Illumina 1.8+ Phred+33."
      exit( 0 )
  elif "J" in set_ascii:
    print "This file could be Solexa+64 or Illumina 1.8+ Phred+33."
    exit( 0 )
  print "This file is either Sanger Phred+33, Solexa+64, or Illumina 1.8+ Pred+33."
  exit( 0 )

if f_o_3_5:
  print "This file is either Solexa+64, Illumina 1.3+ Phred+64, or Illumina 1.5+ Phred+64."
  exit( 0 )
print "I have no idea what format this file is in."
