#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2015"
__credits__ = [ "Timothy Tickle", "Brian Haas" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import datetime
import matplotlib.pyplot as plt
import os
import random
import requests
import time

# Plot color defaults
c_STR_BOX_LINE_COLOR = "blue"
c_STR_BOX_PLOT_COLOR = "cyan"
c_STR_MEDIAN_COLOR = "violet"
c_STR_OUTLIER_COLOR = "orange"

# Read in commandline
prsr_arguments = argparse.ArgumentParser( prog = "test_webservice.py", description = "Quick script to test webservice.", conflict_handler="resolve", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( dest = "str_vcf", help = "VCF files to pull mutations from." )
args_call = prsr_arguments.parse_args()

# Total number of hits
i_total_number_of_hits = 1000

# Make a request
def func_request( str_chr, str_position, str_strand, str_ref, str_mut ):
  str_request = "".join( [ "http://staging.cravat.us/rest/service/query?mutation=",
                           str_chr, "_", str_position, "_", str_strand, "_", str_ref, "_", str_mut ] )
  return( requests.get( str_request ) )


# Read in vcf file and pull info from mutations
def func_read_vcf( str_path ):

  llstr_vcf = []
  with open( str_path, "r" ) as hndl_vcf:
    for str_line in hndl_vcf:
      if not str_line[ 0 ] == "#":
        lstr_line = str_line.split( "\t" )
        llstr_vcf.append( [ lstr_line[ i_token ] for i_token in [ 0, 1, 3, 4 ] ] )
  return( llstr_vcf )


# Read in file
llstr_vcf = func_read_vcf( args_call.str_vcf )

# Holds entries used
lstr_entries = []
# + strand
li_pos_strand = []
# - strand
li_neg_strand = []
# Insertion
li_insert_strand = []
# Deletion
li_delete_strand = []

for i_request in random.sample( range( 0, len( llstr_vcf ) ), i_total_number_of_hits ):

  lstr_cur_entry = llstr_vcf[ i_request ]
  lstr_entries.append( lstr_cur_entry )

  i_start = time.time()
  func_request( str_chr = lstr_cur_entry[ 0 ], str_position = lstr_cur_entry[ 1 ], str_strand = "+",
                str_ref = lstr_cur_entry[ 2 ], str_mut = lstr_cur_entry[ 3 ] )
  i_stop = time.time()
  li_pos_strand.append( round( i_stop - i_start, 2 ) )


  i_start = time.time()
  func_request( str_chr = lstr_cur_entry[ 0 ], str_position = lstr_cur_entry[ 1 ], str_strand = "-",
                str_ref = lstr_cur_entry[ 2 ], str_mut = lstr_cur_entry[ 3 ] )
  i_stop = time.time()
  li_neg_strand.append( round( i_stop - i_start, 2 ) )


  i_start = time.time()
  func_request( str_chr = lstr_cur_entry[ 0 ], str_position = lstr_cur_entry[ 1 ], str_strand = "+",
                str_ref = "-", str_mut = lstr_cur_entry[ 3 ] )
  i_stop = time.time()
  li_insert_strand.append( round( i_stop - i_start, 2 ) )

  i_start = time.time()
  func_request( str_chr = lstr_cur_entry[ 0 ], str_position = lstr_cur_entry[ 1 ], str_strand = "+",
                str_ref = lstr_cur_entry[ 2 ], str_mut = "-" )
  i_stop = time.time()
  li_delete_strand.append( round( i_stop - i_start, 2 ) )


# Write to file
dt_cur = datetime.datetime.now()
str_file_name = "_".join( [ str( dt_cur.month ), str( dt_cur.day ), str( dt_cur.year ), "h", str( dt_cur.hour ), "m", str( dt_cur.minute ), "s", str( dt_cur.second ) ] ) + ".dat" 
with open( str_file_name, "w" ) as hndl_data:
  hndl_data.write( str( lstr_entries ) + "\n" )
  hndl_data.write( str( li_pos_strand ) + "\n" )
  hndl_data.write( str( li_neg_strand ) + "\n" )
  hndl_data.write( str( li_insert_strand ) + "\n" )
  hndl_data.write( str( li_delete_strand ) + "\n" )


# Plot
str_file_plot_name = os.path.splitext( str_file_name )[ 0 ] + ".pdf"

plt_cur = plt.figure()
ax = plt_cur.add_subplot( 111 )
ax.set_xticklabels( [ "Pos", "Neg", "Insert", "Delete" ] )
plt_bp = ax.boxplot( [ li_pos_strand, li_neg_strand, li_insert_strand, li_delete_strand ], patch_artist=True )

# Custom coloring
for patch_box in plt_bp[ "boxes" ]:
  patch_box.set( color = c_STR_BOX_LINE_COLOR, linewidth = 1 )
  patch_box.set( facecolor = c_STR_BOX_PLOT_COLOR )
for patch_whisker in plt_bp[ "whiskers" ]:
  patch_whisker.set( color = c_STR_BOX_LINE_COLOR, linewidth = 2 )
for patch_cap in plt_bp[ "caps" ]:
  patch_cap.set( color = c_STR_BOX_LINE_COLOR, linewidth = 2 )
for patch_median in plt_bp[ "medians" ]:
  patch_median.set( color = c_STR_MEDIAN_COLOR, linewidth = 1 )
for patch_flier in plt_bp[ "fliers" ]:
  patch_flier.set( marker = "o", color = c_STR_OUTLIER_COLOR, alpha = 0.5 )

# X axes
str_x_label = "Request Types"
str_y_label = "Elapse (sec)"

# Annotate plot
plt.title( "Elapse Request Time ( By Type )" )
plt.xlabel( str_x_label )
plt.ylabel( str_y_label )
plt.legend( loc="lower right")
plt.tight_layout()
plt.savefig( str_file_plot_name )
plt.close()
