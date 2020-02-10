#!/usr/bin/env python

import argparse
from Bio import SeqIO
import os


# Acceptable formats for files and thier extensions
dictFileExtentions = { "abif":"abif", "ace":"ace", "embl":"embl", "fasta":"fasta", "fastq":"fastq", "fastq-sanger":"fastq", "fastq-solexa":"fastq", "fastq-illumina":"fastq", "genbank":"gbff", "gb":"gbff", "ig":"mase", "imgt":"imgt", "phd":"phd", "pir":"pir", "seqxml":"xsd", "sff":"sff", "sff-trim":"sff", "swiss":"swiss", "tab":"txt", "qual":"qual", "uniprot-xml":"xsd"}

# Get commandline
argp = argparse.ArgumentParser( prog = "biofileConversion.py", description = "Converts bioinformatics file formats" )
argp.add_argument( "strFileIn", metavar = "input_file", help = "Input file to convert." )
argp.add_argument( "strFormatIn", metavar = "input_file_format", choices = dictFileExtentions.keys(), help = "Input file format. Choices are " + str(
dictFileExtentions.keys()) )
argp.add_argument( "strFormatOut", metavar = "output_file_format", choices = dictFileExtentions.keys(), help = "Output file format. Choices are " + str(dictFileExtentions.keys()) )
args = argp.parse_args()


# Parse, format, and save
print "Converting file: " + args.strFileIn
print "Input Format: " + args.strFormatIn
print "Output Format: " + args.strFormatOut

iCounts = SeqIO.convert( args.strFileIn, args.strFormatIn, os.path.splitext(args.strFileIn)[0] + "-conv." + dictFileExtentions[args.strFormatOut], args.strFormatOut )
print "Converted %i records" % iCounts

