#!/usr/bin/env python

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2014"
__credits__ = [ "Timothy Tickle" ]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@broadinstitute.org"
__status__ = "Development"

import argparse
import quickplots.barChart as barChart
import csv
import quickplots.histogram as histogram
import json
import os
import quickplots.quickPlot as qp
import quickplots.roc as roc
import quickplots.vennDiagram as vennDiagram

# Analysis modes / tools available
str_compare_vcfs_for_tp_fp = "COMPARE_TP_FP"
str_plot_vcf_metrics_distributions = "VCF_METRICS_DISTRIBUTION"
C_LSTR_MODES = [ str_compare_vcfs_for_tp_fp, str_plot_vcf_metrics_distributions ]

def func_read_depth_chr_loc( hndl_depth_file, dict_locations_of_interest ):
    """
    Read depth information.
    Expected Chromosome\tlocation\tdepth
    """
    # Read only global locations that are in the calls
    # Global_loc    Contig_loc      Read_depth
    #
    ##? Chromosome location depth
    #chr1    13883   3 
    i_entries = 0
    dict_total_variants_depth = {}
    i_zero_entries = 0
    
    for ls_total_depth_file in hndl_depth_file:
        # Skip blanks and headers
        if len( ls_total_depth_file ) == 0:
            continue
        
        str_variant = ":".join( ls_total_depth_file[0:2] )
        if str_variant in dict_locations_of_interest:
            if str_variant in dict_total_variants_depth:
                print "Duplicate entry found in depth file entry = "+ str_variant
                exit( 1 )

            #{ 'chr:loc': i_read_depth }
            if int( ls_total_depth_file[ 2 ] ) == 0:
                print [str_variant, "0"]
            dict_total_variants_depth[ str_variant ] = int( ls_total_depth_file[ 2 ] )
            if int( ls_total_depth_file[ 2 ] ) == 0:
                i_zero_entries = i_zero_entries + 1
        i_entries = i_entries + 1

        if i_entries % 1000000 == 0:
            print " Lines: " + str( i_entries )
    #{ 'chr:loc': i_read_depth }
    print "The number of positions found with 0 depth is " + str( i_zero_entries )
    return dict_total_variants_depth


def func_write_depth_file( dict_depth, hndl_write_depth_file ):
    """
    Write a depth file to disk.
    This is useful because the depth file is large.
    Allows us to only read once the full file and then write
    just the data we need in case it needs to be reran.
    """
    
    hndl_write_depth_file.writelines( [ "\t".join( str_chr.split(":") + [ str( int_depth ), "\n" ] ) for str_chr, int_depth in dict_depth.iteritems() ] )


def func_read_true_variants_chr_loc( hndl_gmap_true_file ):
    """
    Read in a gmap format 9 minimized list of variants.
    
    Returns a set of the chr:loc ids
    """
    
    sstr_variants = set()
    # ['g/C', '1652129990', 'chr9:112970278']
    for lstr_variants in hndl_gmap_true_file:
        # Skip blanks and headers
        if len( lstr_variants ) == 0:
            continue
        if lstr_variants[ 0 ][ 0 ] in [ "#", ">" ]:
            continue
        sstr_variants.add( lstr_variants[ 2 ] )

    return sstr_variants


def func_read_vcf_chr_loc( hndle_vcf_file, dict_positives ):
    """
    Parse a vcf file and keep locations for false and true positives.
    A reference for positives is given.
    """
    
    sstr_tp = set()
    sstr_fp = set()
    
    dict_vcf_depth = {}
    
    for lstr_vcf_line in hndle_vcf_file:
        if lstr_vcf_line[ 0 ][ 0 ] == "#":
            continue
        str_vcf_contig, str_vcf_location = lstr_vcf_line[ 0:2 ]
        if len( str_vcf_contig ) < 4 or ( not str_vcf_contig[0:3].lower() == "chr" ):
            str_vcf_contig = "chr"+str_vcf_contig
        str_variant = ":".join( [ str_vcf_contig, str_vcf_location ] )
        if str_variant in dict_positives:
            sstr_tp.add( str_variant )
        else:
            sstr_fp.add( str_variant )
            
        # Get depth
        str_comments = lstr_vcf_line[ 7 ]
        ls_comment_elements = str_comments.split(";")
        i_zero_count = 0
        for str_comment_elements in ls_comment_elements:
            if str_comment_elements[ 0 : 3 ] == "DP=":
                dict_vcf_depth[ str_variant ] = int( str_comment_elements.split( "=" )[ 1 ] )
                i_zero_count = i_zero_count + 1
    print "The number of variants with depth of zero found is " + str( i_zero_count )

    #chr6:24809943
    #chr1:204506593
    return [ sstr_fp, sstr_tp, dict_vcf_depth ]


def func_compare_vcf_to_gold_standard( args ):

    # Indicates if depth is read from sam or vcf files
    f_vcf_depth = args.hndl_depth_file is None

    # Check for depth file
#    if not  args.hndl_depth_file:
#        print "Please supply a depth total file."
#        exit( 1 )
    if not  args.hndl_positives_file:
        print "Please supply a true variants total file."
        exit( 1 )
    
    # File names
    str_left_file = os.path.basename( args.hndle_left_file.name )
    str_right_file = os.path.basename( args.hndle_right_file.name )
    
    # Make output dir if it does not exit
    if not os.path.exists( args.str_output_dir ):
        os.mkdir( args.str_output_dir )
        
    # Holds the depth information from either the sam/bam depth file or vcf
    dict_all_depth = {}
    
    print "Read true variants"
    #chr11:117070292
    sstr_positives = func_read_true_variants_chr_loc( csv.reader( args.hndl_positives_file, delimiter = "\t" ) )
    dict_positives = dict( [ [ str_pos, None] for str_pos in sstr_positives ] )
    print "True positives: " + str( len( sstr_positives ) )
    
    print "Read VCF file 1"
    print args.hndle_left_file.name
    sstr_reader_left_false_positives, sstr_reader_left_true_positives, dict_vcf_depth_left = func_read_vcf_chr_loc( csv.reader( args.hndle_left_file, delimiter = "\t" )
, dict_positives )
    sstr_reader_left_false_negatives = sstr_positives - sstr_reader_left_true_positives
    if f_vcf_depth:
        dict_all_depth = dict_vcf_depth_left
    print "File Left. FP Count: "  + str( len(  sstr_reader_left_false_positives ) ) + " TP Count: " + str( len( sstr_reader_left_true_positives ) )
    
    print 'Read VCF file 2'
    print args.hndle_right_file.name
    sstr_reader_right_false_positives, sstr_reader_right_true_positives, dict_vcf_update_right = func_read_vcf_chr_loc( csv.reader( args.hndle_right_file, delimiter = "\t" ), dict_positives )
    sstr_reader_right_false_negatives = sstr_positives - sstr_reader_right_true_positives
    if f_vcf_depth:
        dict_all_depth.update( dict_vcf_update_right )
    print "File Right. FP Count: "  + str( len( sstr_reader_right_false_positives ) ) + " TP Count: " + str( len( sstr_reader_right_true_positives ) )

    if not f_vcf_depth:
        print "Read in Depth information"
        dict_locations_of_interest = {}
        for str_variant in sstr_reader_left_false_positives:
            dict_locations_of_interest[ str_variant ] = None
        for str_variant in sstr_reader_left_false_negatives:
            dict_locations_of_interest[ str_variant ] = None
        for str_variant in sstr_reader_right_false_positives:
            dict_locations_of_interest[ str_variant ] = None
        for str_variant in sstr_reader_right_false_negatives:
            dict_locations_of_interest[ str_variant ] = None
        #{ 'chr:loc': i_read_depth }

        dict_all_depth = func_read_depth_chr_loc( csv.reader( args.hndl_depth_file, delimiter = "\t" ), dict_locations_of_interest )
        hndle_write_depth_file = open( os.path.join( args.str_output_dir, "depth_of_interest.tsv" ), "w" )
        func_write_depth_file( dict_all_depth, hndle_write_depth_file )
        hndle_write_depth_file.close()
    
    print "Calculate groupings"
    # Calculate true positives in each data set
    dict_tp_left = dict( [ [ str_pos_left, None] for str_pos_left in sstr_reader_left_true_positives ] )
    print "File Left: TP Count: " + str( len( sstr_reader_left_true_positives ) )
    dict_tp_right = dict( [ [ str_pos_right, None] for str_pos_right in sstr_reader_right_true_positives ] )
    print "File Right: TP Count: " + str( len( sstr_reader_right_true_positives ) )

    print "Starting plotting"
    # Plotting objects
    bar_cur = barChart.BarChart()
    hist_cur = histogram.Histogram()
    roc_cur = roc.PositiveROC()
    venn_cur = vennDiagram.VennDiagram()
    

    ### ROC plots of TPR vs FPR by read depth
    # Make a series for both files
    # Positives = All possible alignments
    # True Positives = In both VCF and gmap gold standard alignment
    # True Negatives = Not in vcf or gmap gold stanard
    # False Positive = In VCF and not gmap
    # False Negative = Not in VCF file but in Gmap
    # "data" : [ [true,true,1],[true,true,1]
    # This is not a true ROC
    # The False negatives should be all bases not a variant but this would not be an informative plot. Instead the negatives are the positives as well.
    # So this will be giving the ratio of ( TP/Positives or Traditional TPR ) and FP/Positives
    # First index: Positive = All found in gmap gold, False = all positions in the gmap read depth + all found in vcf as FP
    # Second index: is if the base was predicted to be a positive or negative, in this case, if found in gmap gold
    # Third index: use depth to vary
    # [ [ actual, predicted, value_to_vary ],...]
    print "Start Roc"
    llf_left_measurements = [ [ True, str_left_all in dict_tp_left, dict_all_depth.get( str_left_all, 0 ) ]
                for str_left_all in set( dict_positives.keys() ) ]
#    for s_looking_key in set( dict_positives.keys() ):
#        if s_looking_key not in dict_all_depth:
#            print s_looking_key
    print "length left positives "+str(len(llf_left_measurements))
    i_l_roc_tp, i_l_roc_fp, i_l_roc_depth_tp, i_l_roc_depth_fp = 0,0,0,0
    for l_left_pos_data in llf_left_measurements:
        if l_left_pos_data[1]:
            i_l_roc_tp = i_l_roc_tp + 1
            if l_left_pos_data[2] == 0:
                i_l_roc_depth_tp = i_l_roc_depth_tp + 1
        else:
            i_l_roc_fp = i_l_roc_fp + 1
            if l_left_pos_data[2] == 0:
                i_l_roc_depth_fp = i_l_roc_depth_fp + 1
    print "roc left tp = "+str(i_l_roc_tp)
    print "roc left fp = "+str(i_l_roc_fp)
    print "roc left tp zero = "+str( i_l_roc_depth_tp )
    print "roc left fp zero = "+str( i_l_roc_depth_fp )
    llf_left_measurements = llf_left_measurements + [ [ False, True, dict_all_depth.get( str_left_all, 0 ) ]
                for str_left_all in sstr_reader_left_false_positives ]
    l_false_left = [ [ False, True, dict_all_depth.get( str_left_all, 0 ) ]
                for str_left_all in sstr_reader_left_false_positives ]
    i_l_roc_depth_fn = 0
    for l_left_false_data in l_false_left:
        if l_left_false_data[2] == 0:
            i_l_roc_depth_fn = i_l_roc_depth_fn + 1
    print "roc left fn zero = "+str( i_l_roc_depth_fn )
    llf_right_measurements = [ [ True, str_right_all in dict_tp_right, dict_all_depth.get( str_right_all, 0 ) ]
                for str_right_all in set( dict_positives.keys() ) ]
    llf_right_measurements = llf_right_measurements + [ [ False, True, dict_all_depth.get( str_right_all, 0 ) ]
                for str_right_all in sstr_reader_right_false_positives ]

    dict_ROC = { qp.c_STR_TITLE : "Performance by Read Depth",
                 qp.c_STR_DATA : [ 
                 { qp.c_C_PLOT_COLOR : "cyan", qp.c_STR_DATA_LABEL : str_left_file, qp.c_STR_DATA : llf_left_measurements },
                 { qp.c_C_PLOT_COLOR : "orange", qp.c_STR_DATA_LABEL : str_right_file, qp.c_STR_DATA : llf_right_measurements } 
                 ] }
    with open( os.path.join( args.str_output_dir, "ROC_compare.json" ), "w" ) as str_roc_compare:
        json.dump( dict_ROC, str_roc_compare )
    roc_cur.func_plot(dict_ROC, os.path.join( args.str_output_dir, "ROC_compare.pdf" ) )
    llf_left_measurements = None
    llf_right_measurements = None

    #### Plot venn diagrams
    # Plot the TP (chr:#)
    dict_venn_tp = { qp.c_STR_TITLE: "True Positives",
                     qp.c_STR_DATA : [ { qp.c_STR_DATA : list(sstr_reader_left_true_positives),
                                         qp.c_C_PLOT_COLOR : "r",
                                         qp.c_STR_DATA_LABEL : "TP ("+str_left_file+")" },
                                       { qp.c_STR_DATA : list(sstr_reader_right_true_positives),
                                         qp.c_C_PLOT_COLOR : "b",
                                         qp.c_STR_DATA_LABEL : "TP ("+str_right_file+")" } ]
                     }
    with open( os.path.join( args.str_output_dir, "Venn_TP.json" ), "w" ) as str_venn_tp:
        json.dump( dict_venn_tp, str_venn_tp )
    venn_cur.func_plot(dict_venn_tp, os.path.join( args.str_output_dir, "Venn_TP.pdf" ) )
    
    # False positives (chr:#)
    dict_venn_fp = { qp.c_STR_TITLE: "False Positives",
                    qp.c_STR_DATA : [ { qp.c_STR_DATA : list(sstr_reader_left_false_positives),
                                       qp.c_C_PLOT_COLOR : "r",
                                       qp.c_STR_DATA_LABEL : "FP ("+str_left_file+")" },
                                     { qp.c_STR_DATA : list(sstr_reader_right_false_positives),
                                       qp.c_C_PLOT_COLOR : "b",
                                       qp.c_STR_DATA_LABEL : "FP ("+str_right_file+")" } ]
                     }
    with open( os.path.join( args.str_output_dir, "Venn_FP.json" ), "w" ) as str_venn_fp:
        json.dump( dict_venn_fp, str_venn_fp )
    venn_cur.func_plot(dict_venn_fp, os.path.join( args.str_output_dir, "Venn_FP.pdf" ) )

    # False negatives (chr:#)
    dict_venn_fn = { qp.c_STR_TITLE: "False Negatives",
                    qp.c_STR_DATA : [ { qp.c_STR_DATA : list(sstr_reader_left_false_negatives),
                                       qp.c_C_PLOT_COLOR : "r",
                                       qp.c_STR_DATA_LABEL : "FN ("+str_left_file+")" },
                                     { qp.c_STR_DATA : list(sstr_reader_right_false_negatives),
                                       qp.c_C_PLOT_COLOR : "b",
                                       qp.c_STR_DATA_LABEL : "FN ("+str_right_file+")" } ]
                     }
    with open( os.path.join( args.str_output_dir, "Venn_FN.json" ), "w" ) as str_venn_fn:
        json.dump( dict_venn_fn, str_venn_fn )
    venn_cur.func_plot(dict_venn_fn, os.path.join( args.str_output_dir, "Venn_FN.pdf" ) )
    

    #### Histograms of read depth
    # General Distributions
    # Plot background variant distribution for positives
    dict_background_true_variants = { qp.c_STR_TITLE : "True variant read depth distribution",
                                      qp.c_STR_X_AXIS : "Depth",
                                      qp.c_STR_Y_AXIS : "Count",
                                      qp.c_STR_BINS : "40",
                                      qp.c_STR_DATA : [ { qp.c_STR_DATA : [ dict_all_depth.get(str_positive, 0) for str_positive in sstr_positives ],
                                                          qp.c_C_PLOT_COLOR : "g",
                                                          qp.c_STR_DATA_LABEL : "True Variants Only" } ]
                                    }
    with open( os.path.join( args.str_output_dir, "positives_depth.json" ), "w" ) as str_variant:
        json.dump( dict_background_true_variants, str_variant )
    hist_cur.func_plot( dict_background_true_variants, os.path.join( args.str_output_dir, "positives_depth.pdf" ) )
      
    # Distribution of all read depths
    dict_background_true_variants = { qp.c_STR_TITLE : "Read depth distribution",
                                      qp.c_STR_X_AXIS : "Depth",
                                      qp.c_STR_Y_AXIS : "Count",
                                      qp.c_STR_BINS : "40",
                                      qp.c_STR_DATA : [ { qp.c_STR_DATA : dict_all_depth.values(),
                                                          qp.c_C_PLOT_COLOR : "grey",
                                                          qp.c_STR_DATA_LABEL : "All Bases" } ]
                                    }
#     with open( os.path.join( args.str_output_dir, "all_depth.json" ), "w" ) as str_variant:
#         json.dump( dict_background_true_variants, str_variant )
    hist_cur.func_plot( dict_background_true_variants, os.path.join( args.str_output_dir, "all_depth.pdf" ) )

    # Plot the TP read depth
    # Get depth counts
    # Then plot full plot
    # Then plot a "zoomed in" plot where we chop off the y axis ignoring the first couple big values
    # [[str_depth,str_count],...] 
    lstr_depth_tp_left = [ dict_all_depth.get(str_left_true_positive, 0) for str_left_true_positive in sstr_reader_left_true_positives ]
    lstr_depth_tp_left = [ [ str( str_left_depth ), lstr_depth_tp_left.count( str_left_depth ) ] for str_left_depth in set( lstr_depth_tp_left ) ]
    lstr_depth_tp_right = [ dict_all_depth.get(str_right_true_positive, 0) for str_right_true_positive in sstr_reader_right_true_positives ]
    lstr_depth_tp_right = [ [ str( str_right_depth ), lstr_depth_tp_right.count( str_right_depth ) ] for str_right_depth in set( lstr_depth_tp_right ) ]
    dict_tp_depth = { qp.c_STR_TITLE : "Read depth of true positives",
                      qp.c_STR_X_AXIS : "Read depth",
                      qp.c_STR_Y_AXIS : "Count",
                      qp.c_STR_BINS : "40",
                      qp.c_STR_SORT : qp.c_STR_SORT_NUMERICALLY,
                      qp.c_STR_DATA : [ { qp.c_STR_DATA : [ i_count for str_depth, i_count in lstr_depth_tp_left ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth for str_depth, i_count in lstr_depth_tp_left ],
                                          qp.c_STR_DATA_LABEL : "TP "+str_left_file,
                                          qp.c_C_PLOT_COLOR : "r" },
                                        { qp.c_STR_DATA : [ i_count  for str_depth, i_count in lstr_depth_tp_right ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth  for str_depth, i_count in lstr_depth_tp_right ],
                                          qp.c_STR_DATA_LABEL : "TP "+str_right_file,
                                          qp.c_C_PLOT_COLOR : "b" } ] 
                     }
    with open( os.path.join( args.str_output_dir, "TP_depth.json" ), "w" ) as str_tp_depth:
        json.dump( dict_tp_depth, str_tp_depth )
    bar_cur.func_plot(dict_tp_depth, os.path.join( args.str_output_dir, "TP_depth.pdf" ) )
    # Zoomed in version (use a max y lim of the third highest value ( skipping one for each list's max, assuming of course )
    dict_tp_depth[ qp.c_STR_Y_LIMIT ] = sorted( set( [ i_count for str_depth, i_count in lstr_depth_tp_left + lstr_depth_tp_right ] ), reverse = True )[ 2 ] * 1.05
    bar_cur.func_plot(dict_tp_depth, os.path.join( args.str_output_dir, "TP_zoom_depth.pdf" ) )
    exit(0)
    
    # Plot the FN read depth
    # Get depth counts
    # Then plot full plot
    # Then plot a "zoomed in" plot where we chop off the y axis ignoring the first couple big values
    # [[str_depth,str_count],...] 
    lstr_depth_fn_left = [ dict_all_depth.get(str_left_false_negative, 0) for str_left_false_negative in sstr_reader_left_false_negatives ]
    lstr_depth_fn_left = [ [ str( str_left_depth ), lstr_depth_fn_left.count( str_left_depth ) ] for str_left_depth in set( lstr_depth_fn_left ) ]
    lstr_depth_fn_right = [ dict_all_depth.get(str_right_false_negative, 0) for str_right_false_negative in sstr_reader_right_false_negatives ]
    lstr_depth_fn_right = [ [ str( str_right_depth ), lstr_depth_fn_right.count( str_right_depth ) ] for str_right_depth in set( lstr_depth_fn_right ) ]
    dict_fn_depth = { qp.c_STR_TITLE : "Read depth of false negatives",
                      qp.c_STR_X_AXIS : "Read depth",
                      qp.c_STR_Y_AXIS : "Count",
                      qp.c_STR_BINS : "40",
                      qp.c_STR_SORT : qp.c_STR_SORT_NUMERICALLY,
                      qp.c_STR_DATA : [ { qp.c_STR_DATA : [ i_count for str_depth, i_count in lstr_depth_fn_left ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth for str_depth, i_count in lstr_depth_fn_left ],
                                          qp.c_STR_DATA_LABEL : "FN "+str_left_file,
                                          qp.c_C_PLOT_COLOR : "r" },
                                        { qp.c_STR_DATA : [ i_count  for str_depth, i_count in lstr_depth_fn_right ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth  for str_depth, i_count in lstr_depth_fn_right ],
                                          qp.c_STR_DATA_LABEL : "FN "+str_right_file,
                                          qp.c_C_PLOT_COLOR : "b" } ] 
                     }
    with open( os.path.join( args.str_output_dir, "FN_depth.json" ), "w" ) as str_fn_depth:
        json.dump( dict_fn_depth, str_fn_depth )
    bar_cur.func_plot(dict_fn_depth, os.path.join( args.str_output_dir, "FN_depth.pdf" ) )
    # Zoomed in version (use a max y lim of the third highest value ( skipping one for each list's max, assuming of course )
    dict_fn_depth[ qp.c_STR_Y_LIMIT ] = sorted( set( [ i_count for str_depth, i_count in lstr_depth_fn_left + lstr_depth_fn_right ] ), reverse = True )[ 2 ] * 1.05
    bar_cur.func_plot(dict_fn_depth, os.path.join( args.str_output_dir, "FN_zoom_depth.pdf" ) )


    # Plot the FP read depth
    # Get depth counts
    # Then plot full plot
    # Then plot a "zoomed in" plot where we chop off the y axis ignoring the first couple big values
    # [[str_depth,str_count],...] 
    lstr_depth_fp_left = [ dict_all_depth.get(str_left_false_positive, 0) for str_left_false_positive in sstr_reader_left_false_positives ]
    lstr_depth_fp_left = [ [ str( str_left_depth ), lstr_depth_fp_left.count( str_left_depth ) ] for str_left_depth in set( lstr_depth_fp_left ) ]
    lstr_depth_fp_right = [ dict_all_depth.get(str_right_false_positive, 0) for str_right_false_positive in sstr_reader_right_false_positives ]
    lstr_depth_fp_right = [ [ str( str_right_depth ), lstr_depth_fp_right.count( str_right_depth ) ] for str_right_depth in set( lstr_depth_fp_right ) ]
    dict_fp_depth = { qp.c_STR_TITLE : "Read depth of false positives",
                      qp.c_STR_X_AXIS : "Read depth",
                      qp.c_STR_Y_AXIS : "Count",
                      qp.c_STR_BINS : "40",
                      qp.c_STR_SORT : qp.c_STR_SORT_NUMERICALLY,
                      qp.c_STR_DATA : [ { qp.c_STR_DATA : [ i_count for str_depth, i_count in lstr_depth_fp_left ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth for str_depth, i_count in lstr_depth_fp_left ],
                                          qp.c_STR_DATA_LABEL : "FP "+str_left_file,
                                          qp.c_C_PLOT_COLOR : "r" },
                                        { qp.c_STR_DATA : [ i_count  for str_depth, i_count in lstr_depth_fp_right ],
                                          qp.c_STR_X_TICK_LABEL : [ str_depth  for str_depth, i_count in lstr_depth_fp_right ],
                                          qp.c_STR_DATA_LABEL : "FP "+str_right_file,
                                          qp.c_C_PLOT_COLOR : "b" } ] 
                     }
    with open( os.path.join( args.str_output_dir, "FP_depth.json" ), "w" ) as str_fp_depth:
        json.dump( dict_fp_depth, str_fp_depth )
    bar_cur.func_plot(dict_fp_depth, os.path.join( args.str_output_dir, "FP_depth.pdf" ) )
    # Zoomed in version (use a max y lim of the third highest value ( skipping one for each list's max, assuming of course )
    dict_fp_depth[ qp.c_STR_Y_LIMIT ] = sorted( set( [ i_count for str_depth, i_count in lstr_depth_fp_left + lstr_depth_fp_right ] ), reverse = True )[ 2 ] * 1.05
    bar_cur.func_plot(dict_fp_depth, os.path.join( args.str_output_dir, "FP_zoom_depth.pdf" ) )


def func_show_tp_metric_distribution( args ):
    """ 
    Show the distribution of vcf metrics given known calls.
    This helps understand if a metric discriminates the TP / FP / TN / FN classification
    """
    
    # Read in truth file
    sstr_positives = func_read_true_variants_chr_loc( csv.reader( args.hndl_positives_file, delimiter = "\t" ) )
    dict_positives = dict( [ [ str_pos, None] for str_pos in sstr_positives ] )
    print "True positives: " + str( len( sstr_positives ) )
    
    # Read in metrics of the vcf file binning into TP / FP/ TN / FN and plotting.
    dict_metrics = dict()
    
    for lstr_vcf_line in csv.reader( args.hndle_left_file, delimiter = "\t" ):
        if lstr_vcf_line[ 0 ][ 0 ] == "#":
            continue
        # Make global id for variant
        str_vcf_contig, str_vcf_location = lstr_vcf_line[ 0:2 ]
        str_vcf_qual = float( lstr_vcf_line[ 5 ] )
        str_annotations = lstr_vcf_line[ 7 ]
        if len( str_vcf_contig ) < 4 or ( not str_vcf_contig[0:3].lower() == "chr" ):
            str_vcf_contig = "chr"+str_vcf_contig
        str_variant = ":".join( [ str_vcf_contig, str_vcf_location ] )
        
        # Get metrics from annotations
        lstr_annotations = str_annotations.split(";")
        for str_annotation in lstr_annotations:
            str_ann_key, str_ann_value = str_annotation.split("=")
            # The values may be per allele if there are multiple allele
            # In this case they are delimited by a comma
            for str_allele_ann_value in str_ann_value.split(","):
                str_allele_ann_value = float( str_allele_ann_value )

                dict_qual = dict_metrics.setdefault(str_ann_key,{})
                if str_variant in dict_positives:
                    dict_qual.setdefault("tp",[]).append( str_allele_ann_value )
                else:
                    dict_qual.setdefault("fp",[]).append( str_allele_ann_value )
            
        # Put values in TP / FP bins
        dict_qual = dict_metrics.setdefault("qual",{})
        if str_variant in dict_positives:
            dict_qual.setdefault("tp",[]).append( str_vcf_qual )
        else:
            dict_qual.setdefault("fp",[]).append( str_vcf_qual )
            
    # Plot values
    hist_cur = histogram.Histogram()
    for str_collected_metric in dict_metrics:
        dict_collected_metric = dict_metrics[ str_collected_metric ]
        if len( dict_collected_metric.get("tp",[]) ):
            dict_qual_tp = { qp.c_STR_TITLE : str_collected_metric+" Distribution",
                                      qp.c_STR_X_AXIS : str_collected_metric,
                                      qp.c_STR_Y_AXIS : "Count",
                                      qp.c_STR_BINS : "40",
                                      qp.c_STR_DATA : [ { qp.c_STR_DATA : dict_collected_metric["tp"],
                                                          qp.c_C_PLOT_COLOR : "orange",
                                                          qp.c_STR_DATA_LABEL : "True Pos" },
                                                         { qp.c_STR_DATA : dict_collected_metric["fp"],
                                                          qp.c_C_PLOT_COLOR : "green",
                                                          qp.c_STR_DATA_LABEL : "False Pos" } ]
                                    }
            hist_cur.func_plot( dict_qual_tp, os.path.join( args.str_output_dir, str_collected_metric+"_TP.pdf" ) )
    

# Parse arguments
prsr_arguments = argparse.ArgumentParser( prog = "compare_variant_calling_false_calls.py", description = "Compare results from variant calling pipelines", formatter_class = argparse.ArgumentDefaultsHelpFormatter )
prsr_arguments.add_argument( "-o", "--output_directory", metavar = "out_dir", required = True, dest = "str_output_dir", help = "Directory to output files" )
prsr_arguments.add_argument( "-d", "--depth_file", metavar = "depth_file", default = None, dest = "hndl_depth_file", type = argparse.FileType( "Ur" ), help = "File with read depth information (gmap 9 depth file).")
prsr_arguments.add_argument( "-t", "--truth_file", metavar = "truth_file", default = None, dest = "hndl_positives_file", type = argparse.FileType( "Ur" ), help = "File with only true variants (gmap 9 min file).")
prsr_arguments.add_argument( "-m", "--mode", metavar = "analysis_mode", default = None, required = True, dest = "str_mode", help = "Indicates the type of analysis to perform. Select from "+ ",".join( C_LSTR_MODES ) )
prsr_arguments.add_argument( "-l", "--left", dest = "hndle_left_file", type = argparse.FileType( 'Ur' ), help = "File to compare (Left file). VCF file.")
prsr_arguments.add_argument( "-r", "--right", dest = "hndle_right_file", type = argparse.FileType( 'Ur' ), help = "File to compare (Left file). VCF file.")

lstr_args = prsr_arguments.parse_args()

if lstr_args.str_mode == str_compare_vcfs_for_tp_fp:
    func_compare_vcf_to_gold_standard( lstr_args )
if lstr_args.str_mode == str_plot_vcf_metrics_distributions:
    func_show_tp_metric_distribution( lstr_args )