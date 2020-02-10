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

# Constants
# Actions supported by the script
C_STR_COMPARE = "compare"
C_STR_COMPRESS = "compress"
C_STR_READ_DEPTH = "depth"
LSTR_ACTION_CHOICES = [ C_STR_COMPRESS ]#, C_STR_COMPARE, C_STR_READ_DEPTH ]

# Describes the GMAP format files
c_delimiter = "\t"
lstr_entry_header = [ ">", "#" ]
C_INT_GLOBAL_POSITION_INDEX = 1
C_INT_LOCAL_INDEX = 2
C_INT_VARIANT_INDEX = 0

# Errors
C_STR_MISSING_IN_GMAP = "missing_in_mapping"
C_STR_MISSING_IN_VCF = "missing_in_vcf"


def func_calculate_read_depth( args_user ):
    """
    Calculate read depth from alignments form gmap format 9 file.
    * The accuracy of this is bound by the accuracy of the mappings *
    
    * args_user : Args
                : Arguments passed in by user
    """

    # If a minimized gmap format 9 formated file of alignments is given only those will be measured.
    f_targeted_variants = True if args_user.hndle_min_file else False

    # Convert handles to csv reader / writers
    csv_reader = csv.reader( args_user.hndle_gmap_file, delimiter = c_delimiter )
    csv_writer = csv.writer( args_user.hndle_output_file, delimiter = c_delimiter )
    csv_min_reader = csv.reader( args_user.hndle_min_file, delimiter = c_delimiter ) if f_targeted_variants else None

    # Holds the locations to count
    dict_read_depth = {}
    
    # Variant locations, will only focus on these locations
    dict_variant_locations = {}
    
    # Check of multiple alignment per read
    str_previous_header = ""
    set_headers = set()
    
    # Read in the variant locations
    # Variant       Global_loc      Contig_loc
    #>NM_001012993-hB        1278    297     135
    #g/C     1652129990      chr9:112970278
    if f_targeted_variants:
        for lstr_min_line in csv_min_reader:
      
            # Skip blanks
            if len( lstr_min_line ) == 0:
                continue
            if lstr_min_line[ 0 ][ 0 ] in lstr_entry_header:
                continue
         
            dict_variant_locations[ lstr_min_line[ 1 ] ] = None

    # Count read depths for only variants (too big to do this way otherwise)
    for lsLine in csv_reader:
        # Skip blanks
        if len( lsLine ) == 0:
            continue
        # Skip header lines
        # But make sure that duplicate lines do not exist
        if lsLine[ 0 ][ 0 ] in lstr_entry_header:
            if lsLine[ 0 ] == str_previous_header:
                continue
            if lsLine[ 0 ] in set_headers:
                print "Found duplicate header. Error"
                print " ".join( lsLine )
                return False
            else:
                set_headers.add( lsLine[ 0 ] )
                str_previous_header = lsLine[ 0 ]
            continue
        
        # Get loc information
        str_contig, str_global = lsLine[ 2 ].split(" ")[ :2 ]
        if f_targeted_variants:
            if not str_global in dict_variant_locations:
                continue
        # Format the contig
        if str_contig[0] in [ "-", "+" ]:
            str_contig = str_contig[1:]

        # Refer to the location as this string that will be written to file
        str_locs = c_delimiter.join( [ str_global, str_contig ] )
        dict_read_depth[ str_locs ] = dict_read_depth.get( str_locs, 0 ) + 1

    # Write info about document
    csv_writer.writerows( [ [ "# Global_loc", "Contig_loc", "Read_depth" ], [] ] )
    csv_writer.writerows( [ str_key.split( c_delimiter ) + [ str( i_value ) ] for str_key, i_value in dict_read_depth.iteritems() ] )


def func_compare( args_user ):
    """
    Compare the format 9 gmap mapping to a vcf file.
    
    * args_user : Args
                : Arguments passed in by user
    """

    # Check for vcf file
    if not args_user.str_vcf_file:
        print "Please provide a VCF file to compare to the GMAP format 9 file"
        exit( 1 )

    # True/False * Negative/Positives
    i_true_positives = 0
    i_false_positives = 0
    i_false_negatives = 0
    
    # Metrics
    i_gmap_variants_read = 0
    i_vcf_variants_read = 0

    # Read in the gmap file
    csv_reader_map = csv.reader( args_user.hndle_gmap_file, delimiter = c_delimiter )

    # { 3233232 : [ chr1, chr2 ]}
    dict_mapping = {}
    for ls_line_f9 in csv_reader_map:
        if len( ls_line_f9 ) == 0 or ls_line_f9[ 0 ] [ 0 ] in [ "#", ">" ]:
            continue

        str_chr, str_loc = ls_line_f9[ C_INT_LOCAL_INDEX ].split(":")
        dict_mapping.setdefault( str_loc, set( [ ] ) ).add( str_chr )
        i_gmap_variants_read = i_gmap_variants_read + 1

    # Read in the vcf file
    csv_reader_vcf = csv.reader( open( args_user.str_vcf_file, "r" ), delimiter = c_delimiter )
    csv_writer_output = csv.writer( args_user.hndle_output_file, delimiter = c_delimiter )
    
    # Read through the vcf file
    for lsLine in csv_reader_vcf:
        
        # Optionally parse with whitespace
        if len( lsLine ) == 1:
            lsLine = [ str_piece for str_piece in lsLine[ 0 ].split(" ") if str_piece ]

        # Skip header
        if lsLine[0][0] == "#":
            continue
        
        # Read body
        str_vcf_chr, str_vcf_loc = lsLine[ 0 : 2 ]
        i_vcf_variants_read = i_vcf_variants_read + 1
        
        # See if the location is in the Mapping results
        # { 12323 : [ chr1, chr2 ] }
        if str_vcf_loc in dict_mapping:
            if str_vcf_chr in dict_mapping[ str_vcf_loc ]:
                # Found, remove from the dict
                dict_mapping[ str_vcf_loc ].remove( str_vcf_chr )
                i_true_positives = i_true_positives + 1
                continue
        
        # If not in the mapping results write to file
        # chr1 312312312 missing_in_gmap
        i_false_positives = i_false_positives + 1
        csv_writer_output.writerow( [ str_vcf_chr, str_vcf_loc, C_STR_MISSING_IN_GMAP ] )

    # Anything left over in the mapping file should be indicated as well
    # As false negative and then written to file
    for set_chr_loc in dict_mapping.itervalues():
        i_false_negatives = i_false_negatives + len( set_chr_loc )
    csv_writer_output.writerows( [ [ str_chr, str_loc, C_STR_MISSING_IN_VCF ] for str_loc in dict_mapping 
                                  for str_chr in dict_mapping[ str_loc ] ] )

    # Write out the rates
    csv_writer_output.writerows( [ [ "True_Positives", i_true_positives],
                                  [ "False_Positives ( Only in vcf )", i_false_positives ],
                                  [ "False_Positive_Rate", float( i_false_positives )/float( i_true_positives + i_false_positives )],
                                  [ "False_Negatives ( Only in GMAP )", i_false_negatives ],
                                  [ "GMAP variants Count", i_gmap_variants_read ] ] )


def func_impute_locations( li_known_locations, li_predicted_locations ):
    """ Takes a complete list of known location indices and an incomplete list of predicted locations indices
        and tries to impute values for any location known but not predicted.
    """
    # If the predicted location are equal to the known locations in length,
    # All were predicted an no imputation is needed.
    if len( li_known_locations ) == len( li_predicted_locations ):
        return li_predicted_locations
    # If there are no predictions, there is no way to impute
    if len( li_predicted_locations ) < 2:
        return li_predicted_locations
    # Sort both lists
    li_known_locations.sort()
    li_predicted_locations.sort()
    # Get differences in the locations
    li_known_differences = []
    if len( li_known_locations ) > 1:
        li_known_differences = [ li_known_locations[ i_location_index + 1 ] - li_known_locations[ i_location_index ] 
                            for i_location_index in xrange(len( li_known_locations ) - 1 ) ]
    li_predicted_differences = []
    if len( li_predicted_locations ) > 1:
        li_predicted_differences = [ li_predicted_locations[ i_location_index + 1 ] - li_predicted_locations[ i_location_index ]
                            for i_location_index in xrange( len( li_predicted_locations ) - 1 ) ]
    print li_known_differences
    print li_predicted_differences
    # Use as a reference the location the known location differences
    # try to line the two sequences of differences up.
    # Align left
    i_predicted_diff_index_start = 0
    i_known_diff_index_start = 0
    if li_known_differences[ 0 ] == li_predicted_differences[ 0 ]:
        print "align left"
        return func_impute_sequence( li_predicted_locations, li_predicted_differences, li_known_differences, i_predicted_diff_index_start, i_known_diff_index_start )
    # Align right
    elif li_known_differences[ -1 ] == li_predicted_differences[ -1 ]:
        print "align right"
        return func_impute_sequence( li_predicted_locations, li_predicted_differences, li_known_differences, f_reverse = True )
    # Try somewhere in the middle
    # Get unique values in differences in both known and predicted
    else:
        print "Guess from the middle."
        # Get unique values in predicted differences
        li_unique_values = [ i_differences for i_differences in li_predicted_differences if li_predicted_differences.count( i_differences ) ]
        for i_unique_value in li_unique_values:
            if li_known_differences.count( i_unique_value ) == 1:
                print "unique value"
                print i_unique_value
                i_predicted_diff_index_start = li_predicted_differences.index( i_unique_value )
                i_known_diff_index_start = li_known_differences.index( i_unique_value )
                return func_impute_sequence_from_middle( li_predicted_locations, li_predicted_differences, li_known_differences, i_predicted_diff_index_start = i_predicted_diff_index_start, i_known_diff_index_start = i_known_diff_index_start)
    
        
def func_impute_sequence( li_predicted_locations, li_predicted_differences, li_known_differences, i_predicted_diff_index_start = 0, i_known_diff_index_start = 0, f_reverse = False):
    # Flip the sequences to work from right to left instead of left to right
    if f_reverse:
        li_predicted_locations.reverse()
        li_predicted_differences.reverse()
        li_known_differences.reverse()
    # Difference between the start sites
    i_start_diff = i_known_diff_index_start - i_predicted_diff_index_start
    # Check sequence from left to right
    print [ not li_known_differences[ i_predicted_index + i_start_diff ] == li_predicted_differences[ i_predicted_index ]
          for i_predicted_index in xrange( i_predicted_diff_index_start, len( li_predicted_differences ) ) ]
    if not sum( [ not li_known_differences[ i_predicted_index + i_start_diff ] == li_predicted_differences[ i_predicted_index ] 
          for i_predicted_index in xrange( i_predicted_diff_index_start, len( li_predicted_differences ) ) ] ):
        # Update the predictions to the right if there are missing values
        print "range"
        print len( li_predicted_locations )
        print len( li_predicted_locations ) + ( len( li_known_differences ) - len( li_predicted_differences ) )
        for i_impute_index in xrange( len( li_predicted_locations ), len( li_predicted_locations ) + ( len( li_known_differences ) - len( li_predicted_differences ) ) ):
            print [ "index", i_impute_index ]
            if f_reverse:
                li_predicted_locations = li_predicted_locations + [ li_predicted_locations[ i_impute_index -1 ] - li_known_differences[ i_impute_index - 1 ] ]
            else:
                li_predicted_locations = li_predicted_locations + [ li_predicted_locations[ i_impute_index -1 ] + li_known_differences[ i_impute_index - 1 ] ]
    else:
        print "Does not fully match"
    if f_reverse:
        print "reverse"
        li_predicted_locations.sort()
        li_predicted_differences.sort()
        li_known_differences.sort()
    return li_predicted_locations


def func_impute_sequence_from_middle( li_predicted_locations, li_predicted_differences, li_known_differences, i_predicted_diff_index_start = 0, i_known_diff_index_start = 0, f_reverse = False):
    # Total number of predicted locations
    i_predicted_difference_length = len( li_predicted_differences )
    i_known_pred_diff = i_predicted_diff_index_start - i_known_diff_index_start
    #Check the sequence from left to right
    if sum( [ not li_predicted_differences[ i_forward_predicted_site ] == li_known_differences[ i_forward_predicted_site + i_known_pred_diff ]
                 for i_forward_predicted_site in xrange( i_predicted_diff_index_start, i_predicted_difference_length ) ] ):
        print "Does not fully match forward."
    # Check the sequence from right to left
    if sum( [ not li_predicted_differences[ i_backward_predicted_site ] == li_known_differences[ i_backward_predicted_site + i_known_pred_diff]
                 for i_backward_predicted_site in xrange( 0, i_predicted_diff_index_start ) ] ):
        print "Does not fully match backwards."
    # Impute forward
    print "forward"
    print "i_predicted_diff_index_start"
    print i_predicted_diff_index_start
    print "len( li_known_differences ) - 1"
    print len( li_known_differences ) - 1
    for i_imput_forward_index in xrange( i_predicted_diff_index_start, len( li_known_differences ) - 1 ):
        print "i_imput_forward_index"
        print i_imput_forward_index
        print "li_predicted_locations[ i_imput_forward_index ]"
        print li_predicted_locations[ i_imput_forward_index ]
        print "known difference index"
        print i_imput_forward_index - 1
        print "known difference"
        print li_known_differences[ i_imput_forward_index + i_known_pred_diff]
        li_predicted_locations = li_predicted_locations + [ li_predicted_locations[ i_imput_forward_index ] + li_known_differences[ i_imput_forward_index - i_known_pred_diff] ]
    # Impute backwards
    print "li_predicted_locations"
    print li_predicted_locations
    print "backwards"
    for i_impute_backward_index in xrange( 0, i_known_diff_index_start ):
        print "i_impute_backward_index"
        print i_impute_backward_index
        print "li_predicted_locations[ i_impute_backward_index ]"
        print li_predicted_locations[ i_impute_backward_index ]
        print "li_known_differences[ i_impute_backward_index - i_known_pred_diff - 1]"
        print li_known_differences[ i_impute_backward_index - i_known_pred_diff - 1]
        print "i_known_pred_diff"
        print i_known_pred_diff
        li_predicted_locations = [ li_predicted_locations[ i_impute_backward_index ] - li_known_differences[ i_impute_backward_index - i_known_pred_diff - 1 ] ] + li_predicted_locations
    return li_predicted_locations
    
# func_impute_locations([1,3,6,10,15],[3,6,10])

def func_compress( args_user ):
    """
    Read in gmap format 9 and minimize the size of the file.
    
    Removes anything aligned to a sequence that should have had no alignment ( Header has space delimited location )
    Removes any base that is not a variant
    Removes any base that is a variant but is blank ( ours are indicated with a lower case letter )
    
    * args_user : Args
                : Arguments passed in by user
    """

    # Convert handles to csv reader / writers
    csv_reader = csv.reader( args_user.hndle_gmap_file, delimiter = c_delimiter )
    csv_writer = csv.writer( args_user.hndle_output_file, delimiter = c_delimiter )

    lstr_buffer = []
    lstr_header = ""
    
    # Keep the headers so we can check if there are duplicate alignments
    lstr_found_headers = []
    
    # Keep tract of aligns, misaligns, and duplicate alignments
    i_alignments = 0
    i_false_alignments = 0
    i_misalignments = 0
    i_duplicate_alignments = 0
    i_guessed_alignments = 0

    # Write info about document
    csv_writer.writerows( [ [ "# >Entry" ],[ "# Variant", "Global_loc", "Contig_loc", "Original_read_loc" ], [] ] )

    for lsLine in csv_reader:
        # Skip spaces
        if len( lsLine ) == 0:
            continue
        
        # Check if the line is a header
        f_header = lsLine[0][0] in lstr_entry_header

        # Handle headers
        # If one exists already
        # then switch out header and buffer
        # Else add header
        if f_header:
            
            # First bit of the header that indicates the transcript
            str_header_transcript = lsLine[0].split(" ")[ 0 ]
            
            # If the header entry is the exact as before
            # Gmap is continuing the same alignment
            # and just repeated the header
            if " ".join( lstr_header ) == lsLine[ 0 ]:
                continue
            
            # Store the header and check for duplicates
            # Check here not the full header, just the transcript
            # but report the full header
            if str_header_transcript in lstr_found_headers:
                i_duplicate_alignments = i_duplicate_alignments + 1
                print " ".join( [ "Duplicate header:", lsLine[0] ] )
            else:
                lstr_found_headers.append( str_header_transcript )
            
            # If it is a header and is not the first time setting
            if len( lstr_header ):
                if len( lstr_header ) > 1:
                    lstr_alignment_info = func_write_compress_results( csv_writer, csv_reader, lstr_header, lstr_buffer, i_alignments )
                    i_alignments = i_alignments + lstr_alignment_info[ 0 ]
                    i_misalignments = i_misalignments + lstr_alignment_info[ 1 ]
                    i_false_alignments = i_false_alignments + lstr_alignment_info[ 2 ]
                    i_guessed_alignments = i_guessed_alignments + lstr_alignment_info[ 3 ]
                lstr_buffer = []
                lstr_header = lsLine[0].split(" ")
            # If it is a header and is the first time setting
            else:
                lstr_header = lsLine[0].split(" ")
                lstr_buffer = []
            # Move on to next line
            continue

        # Only read if you have a header
        if lstr_header:
            # Only keep the variants that differ
            c_variant = lsLine[ 1 ].split(" ")[ -1 ]
            str_contig, str_global, c_reference = lsLine[ 2 ].split(" ")[ :3 ]
            # Format the contig
#            if str_contig[0] in [ "-", "+" ]:
#                str_contig = str_contig[1:]
            if not c_variant == c_reference and not c_variant == "" and not c_reference == "" and c_variant.islower():
                lstr_buffer.append( [ "/".join( [ c_variant, c_reference ] ), str_global, str_contig ] )
        else:
            print "Found variant data without a header..."
            print c_delimiter.join( lsLine )

    if len( lstr_header ) > 1:
        lstr_alignment_info = func_write_compress_results( csv_writer, csv_reader, lstr_header, lstr_buffer, i_alignments )
        i_alignments = i_alignments + lstr_alignment_info[ 0 ]
        i_misalignments = i_misalignments + lstr_alignment_info[ 1 ]
        i_false_alignments = i_false_alignments + lstr_alignment_info[ 2 ]
        i_guessed_alignments = i_guessed_alignments + lstr_alignment_info[ 3 ]
        
    # Print summary
    print "#### Summary ####"
    print "Alignments found: " + str( i_alignments ) 
    print "Alignments not found: " + str( i_misalignments )
    print "False alignments: " + str( i_false_alignments )
    print "Duplicate header ( includes non-variant containing headers ): " + str( i_duplicate_alignments )
    print "Guesses made: " + str( i_guessed_alignments )
    

def func_write_compress_results( csv_writer, csv_reader, lstr_header, lstr_buffer, i_alignments ):
    
    i_guessed_alignments = 0
    # Write the last header and associated information
    # Document if the correct number of entries were found per entry
    if not len( lstr_buffer ) == ( len( lstr_header ) - 1 ):
        print " ". join( [ c_delimiter.join( lstr_header ),
            "should have had ", str( len( lstr_header ) - 1 ),
            "entries but found", str( len( lstr_buffer ) ),
            "entries instead." ] )
#        print "Attempting to impute the missing locations."
#        li_predicted_locations = [ int( lstr_variant[ 1 ] ) for lstr_variant in lstr_buffer ]
#        print li_predicted_locations
#        li_new_predicted_locations = func_impute_locations( li_known_locations = [ int( str_location ) for str_location in lstr_header[1:] ], li_predicted_locations = li_predicted_locations )
#        print li_new_predicted_locations
##        # If some locations were predicted, update the buffer
#       if len( li_new_predicted_locations ) > len( li_predicted_locations ):
#            for i_prediction_index in xrange( len( li_new_predicted_locations ) ):
#                if not li_new_predicted_locations[ i_prediction_index ] in li_predicted_locations:
#                    lstr_buffer.append( [ "guess/guess", li_new_predicted_locations[ i_prediction_index ], "guess:guess" ])
#                    i_guessed_alignments = i_guessed_alignments + 1
        
    csv_writer.writerow( lstr_header )
    csv_writer.writerows( lstr_buffer )
    i_actual_alignments = len( lstr_buffer )
    i_expected_alignments = len( lstr_header ) - 1
    i_alignments = min( i_actual_alignments, i_expected_alignments )
    i_misalignments = max( 0, i_expected_alignments - i_actual_alignments )
    i_false_alignments = max( 0, i_actual_alignments - i_expected_alignments )
    return [i_alignments, i_misalignments, i_false_alignments, i_guessed_alignments]

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "gmap_format_9.py", description = "Tools to work with GMAP format 9 files", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "-a", "--action", metavar = "Action", dest = "str_action", choices = LSTR_ACTION_CHOICES, required = True, help = "Specified the action to occur. Options are " + " ".join( LSTR_ACTION_CHOICES ) )
prsr_arguments.add_argument( "-c", "--vcf", metavar = "VCF_file", default = None, dest = "str_vcf_file", help = "VCF file used with certain actions (like compare)." )
prsr_arguments.add_argument( "-m","--min_file", metavar = "Minimized_file", default = None, dest = "hndle_min_file", type = argparse.FileType('Ur'), help = "GMAP 9 formatted and minimized file using the compress option in this script." )
prsr_arguments.add_argument( dest = "hndle_gmap_file", type = argparse.FileType( 'Ur' ), help = "GMAP alignment file using format 9 ( Table format )." )
prsr_arguments.add_argument( dest = "hndle_output_file", type = argparse.FileType( 'w' ), help = "Output file to write to ( will write over the file )." )
args = prsr_arguments.parse_args()

dict_actions = { C_STR_COMPRESS: func_compress, C_STR_COMPARE: func_compare, C_STR_READ_DEPTH: func_calculate_read_depth }
dict_actions[ args.str_action ]( args )
