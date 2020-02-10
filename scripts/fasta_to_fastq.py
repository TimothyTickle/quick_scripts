#!/usr/bin/env python

import argparse
from Bio import SeqIO
import os

iEntries = 5000
iCurEntries = 0
sOut = ""

arp = argparse.ArgumentParser( prog = "FastaToFastQ.py", description = "Converts a Fasta to a Fastq file by indicating all quality scores are perfect." )
arp.add_argument( "strFileToConvert", help = "File to convert" )
arp.add_argument( "strFileToWrite", help = "File to write" )
args = arp.parse_args()

with open(args.strFileToWrite, "w") as hndlWrite:
  with open(args.strFileToConvert,"rU") as hndlFastaFile:
    for record in SeqIO.parse(hndlFastaFile, "fasta"):
      sOut = sOut+os.linesep.join(["@"+record.id, str( record.seq ), "+", "".join(["~"] * len( str( record.seq ))) ]) + os.linesep
      iCurEntries = iCurEntries + 1
      if iCurEntries >= iEntries:
        hndlWrite.write(sOut)
        iCurEntries = 0
        sOut = ""
    hndlWrite.write(sOut)



