__FILENAME__ = bdgbroadcall
# Time-stamp: <2013-10-28 00:12:46 Tao Liu>

"""Description: Fine-tuning script to call broad peaks from a single bedGraph track for scores.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import sys
import os
import logging
from MACS2.IO import cBedGraphIO
# ------------------------------------
# constants
# ------------------------------------
logging.basicConfig(level=20,
                    format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )

# ------------------------------------
# Misc functions
# ------------------------------------
error   = logging.critical		# function alias
warn    = logging.warning
debug   = logging.debug
info    = logging.info
# ------------------------------------
# Classes
# ------------------------------------

# ------------------------------------
# Main function
# ------------------------------------
def run( options ):
    info("Read and build bedGraph...")
    bio = cBedGraphIO.bedGraphIO(options.ifile)
    btrack = bio.build_bdgtrack(baseline_value=0)

    info("Call peaks from bedGraph...")
    #(peaks,bpeaks) = btrack.call_broadpeaks (lvl1_cutoff=options.cutoffpeak, lvl2_cutoff=options.cutofflink, min_length=options.minlen, lvl1_max_gap=options.lvl1maxgap, lvl2_max_gap=options.lvl2maxgap)
    bpeaks = btrack.call_broadpeaks (lvl1_cutoff=options.cutoffpeak, lvl2_cutoff=options.cutofflink, min_length=options.minlen, lvl1_max_gap=options.lvl1maxgap, lvl2_max_gap=options.lvl2maxgap)

    info("Write peaks...")
    #nf = open ("%s_c%.1f_l%d_g%d_peaks.encodePeak" % (options.oprefix,options.cutoffpeak,options.minlen,options.lvl1maxgap),"w")
    if options.ofile:
        bf = open( os.path.join( options.outdir, options.ofile ), "w" )
        options.oprefix = options.ofile
    else:
        bf = open ( os.path.join( options.outdir, "%s_c%.1f_C%.2f_l%d_g%d_G%d_broad.bed12" % (options.oprefix,options.cutoffpeak,options.cutofflink,options.minlen,options.lvl1maxgap,options.lvl2maxgap)), "w" )
    bpeaks[1].write_to_gappedPeak(bf, name_prefix=options.oprefix+"_broadRegion")
    info("Done")

########NEW FILE########
__FILENAME__ = bdgcmp
# Time-stamp: <2013-10-28 12:17:33 Tao Liu>

import sys
import os
import logging

from MACS2.IO import cBedGraphIO
from MACS2.OptValidator import opt_validate_bdgcmp as opt_validate

from math import log as mlog

# ------------------------------------
# constants
# ------------------------------------
logging.basicConfig(level=20,
                    format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )

# ------------------------------------
# Misc functions
# ------------------------------------
error   = logging.critical		# function alias
warn    = logging.warning
debug   = logging.debug
info    = logging.info
# ------------------------------------
# Main function
# ------------------------------------

def run( options ):
    options = opt_validate( options )
    scaling_factor = options.sfactor
    pseudo_depth = 1.0/scaling_factor   # not an actual depth, but its reciprocal, a trick to override SPMR while necessary.

    info("Read and build treatment bedGraph...")
    tbio = cBedGraphIO.bedGraphIO(options.tfile)
    tbtrack = tbio.build_bdgtrack()

    info("Read and build control bedGraph...")
    cbio = cBedGraphIO.bedGraphIO(options.cfile)
    cbtrack = cbio.build_bdgtrack()

    info("Build scoreTrackII...")
    sbtrack = tbtrack.make_scoreTrackII_for_macs( cbtrack, depth1 = pseudo_depth, depth2 = pseudo_depth )
    if abs(scaling_factor-1) > 1e-6:
        # Only for the case while your input is SPMR from MACS2 callpeak; Let's override SPMR.
        info("Values in your input bedGraph files will be multiplied by %f ..." % scaling_factor)
        sbtrack.change_normalization_method( ord('M') ) # a hack to override SPMR
    sbtrack.set_pseudocount( options.pseudocount )

    already_processed_method_list = []
    for (i, method) in enumerate(options.method):
        if method in already_processed_method_list:
            continue
        else:
            already_processed_method_list.append( method )

        info("Calculate scores comparing treatment and control by '%s'..." % method)
        if options.ofile:
            ofile = os.path.join( options.outdir, options.ofile[ i ] )
        else:
            ofile = os.path.join( options.outdir, options.oprefix + "_" + method + ".bdg" )
        # build score track
        if method == 'ppois':
            sbtrack.change_score_method( ord('p') )
        elif method == 'qpois':
            sbtrack.change_score_method( ord('q') )
        elif method == 'subtract':
            sbtrack.change_score_method( ord('d') )
        elif method == 'logFE':
            sbtrack.change_score_method( ord('f') )
        elif method == 'FE':
            sbtrack.change_score_method( ord('F') )
        elif method == 'logLR':             # log likelihood
            sbtrack.change_score_method( ord('l') )
        elif method == 'slogLR':             # log likelihood
            sbtrack.change_score_method( ord('s') )
        else:
            raise Exception("Can't reach here!")
        
        info("Write bedGraph of scores...")
        ofhd = open(ofile,"wb")
        sbtrack.write_bedGraph(ofhd,name="%s_Scores" % (method.upper()),description="Scores calculated by %s" % (method.upper()), column = 3)
        info("Finished '%s'! Please check '%s'!" % (method, ofile))

########NEW FILE########
__FILENAME__ = bdgdiff
# Time-stamp: <2013-10-28 01:08:06 Tao Liu>

"""Description: Naive call differential peaks from 4 bedGraph tracks for scores.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import sys
import os
import logging
from MACS2.IO import cBedGraphIO
from MACS2.IO import cScoreTrack

# ------------------------------------
# constants
# ------------------------------------
logging.basicConfig(level=20,
                    format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )

# ------------------------------------
# Misc functions
# ------------------------------------
error   = logging.critical		# function alias
warn    = logging.warning
debug   = logging.debug
info    = logging.info
# ------------------------------------
# Classes
# ------------------------------------

# ------------------------------------
# Main function
# ------------------------------------
def run( options ):
    if options.maxgap >= options.minlen:
        error("MAXGAP should be smaller than MINLEN! Your input is MAXGAP = %d and MINLEN = %d" % (options.maxgap, options.minlen))

    LLR_cutoff = options.cutoff
    ofile_prefix = options.oprefix

    info("Read and build treatment 1 bedGraph...")
    t1bio = cBedGraphIO.bedGraphIO(options.t1bdg)
    t1btrack = t1bio.build_bdgtrack()

    info("Read and build control 1 bedGraph...")
    c1bio = cBedGraphIO.bedGraphIO(options.c1bdg)
    c1btrack = c1bio.build_bdgtrack()

    info("Read and build treatment 2 bedGraph...")
    t2bio = cBedGraphIO.bedGraphIO(options.t2bdg)
    t2btrack = t2bio.build_bdgtrack()

    info("Read and build control 2 bedGraph...")
    c2bio = cBedGraphIO.bedGraphIO(options.c2bdg)
    c2btrack = c2bio.build_bdgtrack()

    depth1 = options.depth1
    depth2 = options.depth2

    if depth1 > depth2:         # scale down condition 1 to size of condition 2
        depth1 = depth2 / depth1
        depth2 = 1.0
    elif depth1 < depth2:       # scale down condition 2 to size of condition 1
        depth2 = depth1/ depth2
        depth1 = 1.0
    else:                       # no need to scale down any
        depth1 = 1.0
        depth2 = 1.0

    twoconditionscore = cScoreTrack.TwoConditionScores( t1btrack,
                                                        c1btrack,
                                                        t2btrack,
                                                        c2btrack,
                                                        depth1,
                                                        depth2 )
    twoconditionscore.build()
    twoconditionscore.finalize()
    (cat1,cat2,cat3) = twoconditionscore.call_peaks(min_length=options.minlen, max_gap=options.maxgap, cutoff=options.cutoff)

    info("Write peaks...")

    ofiles = []
    name_prefix = []
    if options.ofile:
        ofiles = map( lambda x: os.path.join( options.outdir, x ), options.ofile )
        name_prefix = options.ofile
    else:
        ofiles = [ os.path.join( options.outdir, "%s_c%.1f_cond1.bed" % (options.oprefix,options.cutoff)),
                   os.path.join( options.outdir, "%s_c%.1f_cond2.bed" % (options.oprefix,options.cutoff)),
                   os.path.join( options.outdir, "%s_c%.1f_common.bed" % (options.oprefix,options.cutoff))
                   ]
        name_prefix = [ options.oprefix+"_cond1_",
                        options.oprefix+"_cond2_",
                        options.oprefix+"_common_",
                        ]
    
    nf = open( ofiles[ 0 ], 'w' )
    cat1.write_to_bed(nf, name_prefix=name_prefix[ 0 ], name="condition 1", description="unique regions in condition 1", score_column="score")

    nf = open( ofiles[ 1 ], 'w' )
    cat2.write_to_bed(nf, name_prefix=name_prefix[ 1 ], name="condition 2", description="unique regions in condition 2", score_column="score")

    nf = open( ofiles[ 2 ], 'w' )
    cat3.write_to_bed(nf, name_prefix=name_prefix[ 2 ], name="common", description="common regions in both conditions", score_column="score")
    info("Done")



########NEW FILE########
__FILENAME__ = bdgpeakcall
# Time-stamp: <2013-10-27 23:55:20 Tao Liu>

"""Description: Naive call peaks from a single bedGraph track for scores.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------
import sys
import os
import logging
from MACS2.IO import cBedGraphIO
# ------------------------------------
# constants
# ------------------------------------
logging.basicConfig(level=20,
                    format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )

# ------------------------------------
# Misc functions
# ------------------------------------
error   = logging.critical		# function alias
warn    = logging.warning
debug   = logging.debug
info    = logging.info
# ------------------------------------
# Classes
# ------------------------------------

# ------------------------------------
# Main function
# ------------------------------------
def run( options ):
    info("Read and build bedGraph...")
    bio = cBedGraphIO.bedGraphIO(options.ifile)
    btrack = bio.build_bdgtrack(baseline_value=0)

    info("Call peaks from bedGraph...")
    peaks = btrack.call_peaks(cutoff=float(options.cutoff),min_length=int(options.minlen),max_gap=int(options.maxgap),call_summits=options.call_summits)

    info("Write peaks...")
    if options.ofile:
        options.oprefix = options.ofile
        nf = open( os.path.join( options.outdir, options.ofile ), 'w' )
    else:
        nf = open ( os.path.join( options.outdir, "%s_c%.1f_l%d_g%d_peaks.narrowPeak" % (options.oprefix,options.cutoff,options.minlen,options.maxgap)), "w" )
    peaks.write_to_narrowPeak(nf, name=options.oprefix, name_prefix=options.oprefix+"_narrowPeak", score_column="score", trackline=options.trackline)
    info("Done")




########NEW FILE########
__FILENAME__ = callpeak
# Time-stamp: <2013-12-13 11:55:48 Tao Liu>

"""Description: MACS 2 main executable

Copyright (c) 2008,2009 Yong Zhang, Tao Liu <taoliu@jimmy.harvard.edu>
Copyright (c) 2010,2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging
from time import strftime

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate
from MACS2.OutputWriter import *
from MACS2.cProb import binomial_cdf_inv
from MACS2.cPeakModel import PeakModel,NotEnoughPairsException
from MACS2.cPeakDetect import PeakDetect
from MACS2.Constants import *
# ------------------------------------
# Main function
# ------------------------------------
def check_names(treat, control, error_stream):
    """check common chromosome names"""
    tchrnames = set(treat.get_chr_names())
    cchrnames = set(control.get_chr_names())
    commonnames = tchrnames.intersection(cchrnames)
    if len(commonnames)==0:
        error_stream("No common chromosome names can be found from treatment and control! Check your input files! MACS will quit...")
        error_stream("Chromosome names in treatment: %s" % ",".join(sorted(tchrnames)))
        error_stream("Chromosome names in control: %s" % ",".join(sorted(cchrnames)))
        sys.exit()

def run( args ):
    """The Main function/pipeline for MACS.
    
    """
    # Parse options...
    options = opt_validate( args )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error
    #0 output arguments
    info("\n"+options.argtxt)
    options.PE_MODE = options.format in ('BAMPE',)
    if options.PE_MODE: tag = 'fragment' # call things fragments not tags
    else: tag = 'tag'
    
    #1 Read tag files
    info("#1 read %s files...", tag)
    if options.PE_MODE: (treat, control) = load_frag_files_options (options)
    else:       (treat, control) = load_tag_files_options  (options)
    if control is not None: check_names(treat, control, error)
    
    info("#1 %s size = %d", tag, options.tsize)
    tagsinfo  = "# %s size is determined as %d bps\n" % (tag, options.tsize)
    
    t0 = treat.total
    tagsinfo += "# total %ss in treatment: %d\n" % (tag, t0)
    info("#1  total %ss in treatment: %d", tag, t0)
    # not ready yet
#    options.filteringmodel = True
#    if options.filteringmodel:
#        treat.separate_dups()
#        t0 = treat.total + treat.dups.total
#        t1 = treat.total
#        info("#1  Redundant rate of treatment: %.2f", float(t0 - t1) / t0)
#        tagsinfo += "# Redundant rate in treatment: %.2f\n" % (float(t0-t1)/t0)
#    elif options.keepduplicates != "all":
    if options.keepduplicates != "all":
        if options.keepduplicates == "auto":
            info("#1 calculate max duplicate %ss in single position based on binomial distribution...", tag)
            treatment_max_dup_tags = cal_max_dup_tags(options.gsize,t0)
            info("#1  max_dup_tags based on binomial = %d" % (treatment_max_dup_tags))
        else:
            info("#1 user defined the maximum %ss...", tag)
            treatment_max_dup_tags = int(options.keepduplicates)
        if options.PE_MODE:
            info("#1 filter out redundant fragments by allowing at most %d identical fragment(s)", treatment_max_dup_tags)
        else:
            info("#1 filter out redundant tags at the same location and the same strand by allowing at most %d tag(s)", treatment_max_dup_tags)
        treat.separate_dups(treatment_max_dup_tags) # changed 5-29
#        treat.filter_dup(treatment_max_dup_tags)
        t1 = treat.total
        info("#1  %ss after filtering in treatment: %d", tag, t1)
        tagsinfo += "# %ss after filtering in treatment: %d\n" % (tag, t1)
        if options.PE_MODE:
            tagsinfo += "# maximum duplicate fragments in treatment = %d\n" % (treatment_max_dup_tags)
        else:
            tagsinfo += "# maximum duplicate tags at the same position in treatment = %d\n" % (treatment_max_dup_tags)
        info("#1  Redundant rate of treatment: %.2f", float(t0 - t1) / t0)
        tagsinfo += "# Redundant rate in treatment: %.2f\n" % (float(t0-t1)/t0)
    else:
        t1 = t0

    if control is not None:
        c0 = control.total
        tagsinfo += "# total %ss in control: %d\n" % (tag, c0)
        info("#1  total %ss in control: %d", tag, c0)
        # not ready yet
        #if options.filteringmodel:
        #    control.separate_dups()
        #    c0 = treat.total + treat.dups.total
        #    c1 = treat.total
        #    info("#1  Redundant rate of treatment: %.2f", float(c0 - c1) / c0)
        #    tagsinfo += "# Redundant rate in treatment: %.2f\n" % (float(c0-c1)/c0)
        #elif options.keepduplicates != "all":
        if options.keepduplicates != "all":
            if options.keepduplicates == "auto":
                info("#1  for control, calculate max duplicate %ss in single position based on binomial distribution...", tag)
                control_max_dup_tags = cal_max_dup_tags(options.gsize,c0)
                info("#1  max_dup_tags based on binomial = %d" % (control_max_dup_tags))
            else:
                info("#1 user defined the maximum %ss...", tag)
                control_max_dup_tags = int(options.keepduplicates)
            if options.PE_MODE:
                info("#1 filter out redundant fragments by allowing at most %d identical fragment(s)", treatment_max_dup_tags)
            else:
                info("#1 filter out redundant tags at the same location and the same strand by allowing at most %d tag(s)", treatment_max_dup_tags)
#            control.filter_dup(treatment_max_dup_tags)
            control.separate_dups(treatment_max_dup_tags) # changed 5-29
            c1 = control.total
            
            info("#1  %ss after filtering in control: %d", tag, c1)
            tagsinfo += "# %ss after filtering in control: %d\n" % (tag, c1)
            if options.PE_MODE:
                tagsinfo += "# maximum duplicate fragments in control = %d\n" % (treatment_max_dup_tags)
            else:
                tagsinfo += "# maximum duplicate tags at the same position in control = %d\n" % (treatment_max_dup_tags)
            
            info("#1  Redundant rate of control: %.2f" % (float(c0-c1)/c0))
            tagsinfo += "# Redundant rate in control: %.2f\n" % (float(c0-c1)/c0)
        else:
            c1 = c0
    info("#1 finished!")

    #2 Build Model
    info("#2 Build Peak Model...")

    if options.nomodel:
        info("#2 Skipped...")
        if options.PE_MODE:
            options.shiftsize = 0
            options.d = options.tsize
        else:
            options.d=options.shiftsize*2
        info("#2 Use %d as fragment length" % (options.d))
        options.scanwindow=2*options.d  # remove the effect of --bw
    else:
        try:
            peakmodel = PeakModel(treatment = treat,
                                  max_pairnum = MAX_PAIRNUM,
                                  opt = options
                                  )
            info("#2 finished!")
            debug("#2  Summary Model:")
            debug("#2   min_tags: %d" % (peakmodel.min_tags))
            debug("#2   d: %d" % (peakmodel.d))
            debug("#2   scan_window: %d" % (peakmodel.scan_window))
            info("#2 predicted fragment length is %d bps" % peakmodel.d)
            info("#2 alternative fragment length(s) may be %s bps" % ','.join(map(str,peakmodel.alternative_d)))
            info("#2.2 Generate R script for model : %s" % (options.modelR))
            model2r_script(peakmodel,options.modelR,options.name)
            options.d = peakmodel.d
            options.scanwindow= 2*options.d
            if options.d <= 2*options.tsize:
                warn("#2 Since the d (%.0f) calculated from paired-peaks are smaller than 2*tag length, it may be influenced by unknown sequencing problem!" % (options.d))
                if options.onauto:
                    options.d=options.shiftsize*2
                    options.scanwindow=2*options.d 
                    warn("#2 MACS will use %d as shiftsize, %d as fragment length. NOTE: if the d calculated is still acceptable, please do not use --fix-bimodal option!" % (options.shiftsize,options.d))
                else:
                    warn("#2 You may need to consider one of the other alternative d(s): %s" %  ','.join(map(str,peakmodel.alternative_d)))
                    warn("#2 You can restart the process with --nomodel --shiftsize XXX with your choice or an arbitrary number. Nontheless, MACS will continute computing.")
                
        except NotEnoughPairsException:
            if not options.onauto:
                sys.exit(1)
            warn("#2 Skipped...")
            options.d=options.shiftsize*2
            options.scanwindow=2*options.d 
            warn("#2 Since --fix-bimodal is set, MACS will use %d as shiftsize, %d as fragment length" % (options.shiftsize,options.d))


    #3 Call Peaks
    info("#3 Call peaks...")
    if options.nolambda:
        info("# local lambda is disabled!")

    # decide options.tocontrol according to options.tolarge
    if control and options.PE_MODE:
        c1 = c1 * 2
    
    if control:
        if options.downsample:
            # use random sampling to balance treatment and control
            info("#3 User prefers to use random sampling instead of linear scaling.")
            if t1 > c1:
                info("#3 MACS is random sampling treatment %ss...", tag)
                if options.seed < 0:
                    warn("#3 Your results may not be reproducible due to the random sampling!")
                else:
                    info("#3 Random seed (%d) is used." % options.seed)
                treat.sample_num(c1, options.seed)
                info("#3 %d Tags from treatment are kept", treat.total)                
            elif c1 > t1: 
                info("#3 MACS is random sampling control %ss...", tag)
                if options.seed < 0:
                    warn("#3 Your results may not be reproducible due to the random sampling!")
                else:
                    info("#3 Random seed (%d) is used." % options.seed)
                control.sample_num(t1, options.seed)
                info("#3 %d %ss from control are kept", control.total, tag)
            # set options.tocontrol although it would;t matter now
            options.tocontrol = False
        else:
            if options.tolarge:
                if t1 > c1:
                    # treatment has more tags than control, since tolarge is
                    # true, we will scale control to treatment.
                    options.tocontrol = False
                else:
                    # treatment has less tags than control, since tolarge is
                    # true, we will scale treatment to control.
                    options.tocontrol = True
            else:
                if t1 > c1:
                    # treatment has more tags than control, since tolarge is
                    # false, we will scale treatment to control.
                    options.tocontrol = True
                else:
                    # treatment has less tags than control, since tolarge is
                    # false, we will scale control to treatment.
                    options.tocontrol = False

    peakdetect = PeakDetect(treat = treat,
                            control = control,
                            opt = options
                            )
    peakdetect.call_peaks()

    #call refinepeak if needed.
    # if options.refine_peaks:
    #     info("#3 now put back duplicate reads...")
    #     treat.addback_dups()
    #     info("#3 calculate reads balance to refine peak summits...")
    #     refined_peaks = treat.refine_peak_from_tags_distribution ( peakdetect.peaks, options.d, 0 )
    #     info("#3 reassign scores for newly refined peak summits...")
    #     peakdetect.peaks = peakdetect.scoretrack.reassign_peaks( refined_peaks ) # replace
    #     #info("#3 write to file: %s ..." % options.name+"_refined_peaks.encodePeak" )
    #     #refinedpeakfile = open(options.name+"_refined_peaks.encodePeak", "w")
    #     #refined_peaks.write_to_narrowPeak (refinedpeakfile, name_prefix="%s_refined_peak_", name=options.name, score_column=score_column, trackline=options.trackline )

    #diag_result = peakdetect.diag_result()
    #4 output
    #4.1 peaks in XLS
    info("#4 Write output xls file... %s" % (options.peakxls))
    ofhd_xls = open( options.peakxls, "w" )
    ofhd_xls.write("# This file is generated by MACS version %s\n" % (MACS_VERSION))
    ofhd_xls.write(options.argtxt+"\n")

    ofhd_xls.write(tagsinfo)

    ofhd_xls.write("# d = %d\n" % (options.d))
    try:
        ofhd_xls.write("# alternative fragment length(s) may be %s bps\n" % ','.join(map(str,peakmodel.alternative_d)))
    except:
        # when --nomodel is used, there is no peakmodel object. Simply skip this line.
        pass
    if options.nolambda:
        ofhd_xls.write("# local lambda is disabled!\n")
    # pass write method so we can print too, and include name
    peakdetect.peaks.write_to_xls(ofhd_xls, name = options.name)
    ofhd_xls.close()
    #4.2 peaks in BED
    if options.log_pvalue:
        score_column = "pscore"
    elif options.log_qvalue:
        score_column = "qscore"
    #4.2 peaks in narrowPeak
    if not options.broad:
        #info("#4 Write peak bed file... %s" % (options.peakbed))
        #ofhd_bed = open(options.peakbed,"w")
        #peakdetect.peaks.write_to_bed (ofhd_bed, name_prefix="%s_peak_", name = options.name, description="Peaks for %s (Made with MACS v2, " + strftime("%x") + ")", score_column=score_column, trackline=options.trackline)
        #ofhd_bed.close()
        info("#4 Write peak in narrowPeak format file... %s" % (options.peakNarrowPeak))
        ofhd_bed = open( options.peakNarrowPeak, "w" )
        peakdetect.peaks.write_to_narrowPeak (ofhd_bed, name_prefix="%s_peak_", name=options.name, score_column=score_column, trackline=options.trackline )
        ofhd_bed.close()
        #4.2-2 summits in BED
        info("#4 Write summits bed file... %s" % (options.summitbed))
        ofhd_summits = open( options.summitbed, "w" )
        peakdetect.peaks.write_to_summit_bed (ofhd_summits, name_prefix="%s_peak_", name=options.name,
                                              description="Summits for %s (Made with MACS v2, " + strftime("%x") + ")",
                                              score_column=score_column, trackline=options.trackline )
        ofhd_summits.close()
    #4.2 broad peaks in bed12 or gappedPeak
    else:
        info("#4 Write broad peak in broadPeak format file... %s" % (options.peakBroadPeak))
        ofhd_bed = open( options.peakBroadPeak, "w" )
        peakdetect.peaks.write_to_broadPeak (ofhd_bed, name_prefix="%s_peak_", name=options.name, description=options.name, trackline=options.trackline)
        ofhd_bed.close()
        info("#4 Write broad peak in bed12/gappedPeak format file... %s" % (options.peakGappedPeak))
        ofhd_bed = open( options.peakGappedPeak, "w" )
        peakdetect.peaks.write_to_gappedPeak (ofhd_bed, name_prefix="%s_peak_", name=options.name, description=options.name, trackline=options.trackline)
        ofhd_bed.close()

    info("Done!")
    
def cal_max_dup_tags ( genome_size, tags_number, p=1e-5 ):
    """Calculate the maximum duplicated tag number based on genome
    size, total tag number and a p-value based on binomial
    distribution. Brute force algorithm to calculate reverse CDF no
    more than MAX_LAMBDA(100000).
    
    """
    return binomial_cdf_inv(1-p,tags_number,1.0/genome_size)

def load_frag_files_options ( options ):
    """From the options, load treatment fragments and control fragments (if available).

    """
    options.info("#1 read treatment fragments...")

    tp = options.parser(options.tfile[0], buffer_size=options.buffer_size)
    treat = tp.build_petrack()
    treat.sort()
    if len(options.tfile) > 1:
        # multiple input
        for tfile in options.tfile[1:]:
            tp = options.parser(tfile, buffer_size=options.buffer_size)
            treat = tp.append_petrack( treat )
            treat.sort()

    options.tsize = tp.d
    if options.cfile:
        options.info("#1.2 read input fragments...")
        cp = options.parser(options.cfile[0], buffer_size=options.buffer_size)
        control = cp.build_petrack()
        control_d = cp.d
        control.sort()
        if len(options.cfile) > 1:
            # multiple input
            for cfile in options.cfile[1:]:
                cp = options.parser(cfile, buffer_size=options.buffer_size)
                control = cp.append_petrack( control )
                control.sort()
    else:
        control = None
    options.info("#1 mean fragment size is determined as %d bp from treatment" % options.tsize)
#    options.info("#1 fragment size variance is determined as %d bp from treatment" % tp.variance)
    if control is not None:
        options.info("#1 note: mean fragment size in control is %d bp -- value ignored" % control_d)
    return (treat, control)

def load_tag_files_options ( options ):
    """From the options, load treatment tags and control tags (if available).

    """
    options.info("#1 read treatment tags...")
    tp = options.parser(options.tfile[0], buffer_size=options.buffer_size)
    if not options.tsize:           # override tsize if user specified --tsize
        ttsize = tp.tsize()
        options.tsize = ttsize
    treat = tp.build_fwtrack()
    treat.sort()
    if len(options.tfile) > 1:
        # multiple input
        for tfile in options.tfile[1:]:
            tp = options.parser(tfile, buffer_size=options.buffer_size)
            treat = tp.append_fwtrack( treat )
            treat.sort()
    
    if options.cfile:
        options.info("#1.2 read input tags...")
        control = options.parser(options.cfile[0], buffer_size=options.buffer_size).build_fwtrack()
        control.sort()
        if len(options.cfile) > 1:
            # multiple input
            for cfile in options.cfile[1:]:
                cp = options.parser(cfile, buffer_size=options.buffer_size)
                control = cp.append_fwtrack( control )
                control.sort()
    else:
        control = None
    options.info("#1 tag size is determined as %d bps" % options.tsize)
    return (treat, control)

########NEW FILE########
__FILENAME__ = Constants
MACS_VERSION = "2.0.10.2014XXXX"
#MACSDIFF_VERSION = "1.0.4 20110212 (tag:alpha)"
FILTERDUP_VERSION = "1.0.0 20120703"
RANDSAMPLE_VERSION = "1.0.0 20120703"
MAX_PAIRNUM = 1000
MAX_LAMBDA  = 100000
FESTEP      = 20
BUFFER_SIZE = 100000                   # np array will increase at step of 1 million items

from array import array

if array('h',[1]).itemsize == 2:
    BYTE2 = 'h'
else:
    raise Exception("BYTE2 type cannot be determined!")

if array('H',[1]).itemsize == 2:
    UBYTE2 = 'H'
else:
    raise Exception("UBYTE2 (unsigned short) type cannot be determined!")

if array('i',[1]).itemsize == 4:
    BYTE4 = 'i'
elif array('l',[1]).itemsize == 4:
    BYTE4 = 'l'
else:
    raise Exception("BYTE4 type cannot be determined!")

if array('f',[1]).itemsize == 4:
    FBYTE4 = 'f'
elif array('d',[1]).itemsize == 4:
    FBYTE4 = 'd'
else:
    raise Exception("FBYTE4 type cannot be determined!")

########NEW FILE########
__FILENAME__ = cStat
# Time-stamp: <2012-02-29 15:09:27 Tao Liu>

"""Module Description

Copyright (c) 2012 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

from array import array as pyarray
from MACS2.Constants import *
from random import gammavariate as rgamma
from random import seed as rseed
from math import log
import pymc
from pymc import deterministic
# ------------------------------------
# constants
# ------------------------------------
import numpy.random as numpyrand

LOG2E = log(2.718281828459045,2)        # for converting natural log to log2

gfold_dict = {}                         # temporarily save all precomputed gfold

# ------------------------------------
# Misc functions
# ------------------------------------

# BUGFIX FOR PYMC ARGUMENT CHANGE
from inspect import getargspec
PROGRESS_BAR_ENABLED = 'progress_bar' in getargspec(pymc.MCMC.sample)[0]

def MCMCPoissonPosteriorRatio (sample_number, burn, count1, count2):
    """MCMC method to calculate ratio distribution of two Posterior Poisson distributions.

    sample_number: number of sampling. It must be greater than burn, however there is no check.
    burn: number of samples being burned.
    count1: observed counts of condition 1
    count2: observed counts of condition 2

    return: list of log2-ratios
    """
    lam1 = pymc.Uniform('U1',0,10000)   # prior of lambda is uniform distribution
    lam2 = pymc.Uniform('U2',0,10000)   # prior of lambda is uniform distribution    
    poi1 = pymc.Poisson('P1',lam1,value=count1,observed=True) # Poisson with observed value count1
    poi2 = pymc.Poisson('P2',lam2,value=count2,observed=True) # Poisson with observed value count2
    @deterministic
    def ratio (l1=lam1,l2=lam2):
        return log(l1,2) - log(l2,2)
    mcmcmodel  = pymc.MCMC([ratio,lam1,poi1,lam2,poi2])
    mcmcmodel.use_step_method(pymc.AdaptiveMetropolis,[ratio,lam1,lam2,poi1,poi2], delay=20000)
    if PROGRESS_BAR_ENABLED:
        mcmcmodel.sample(iter=sample_number, progress_bar=False, burn=burn)    
    else:
        mcmcmodel.sample(iter=sample_number, burn=burn)    
    return ratio.trace()


def MLEPoissonPosteriorRatio (sample_number, burn, count1, count2):
    """MLE method to calculate ratio distribution of two Posterior Poisson distributions.

    MLE of Posterior Poisson is Gamma(k+1,1) if there is only one observation k.

    sample_number: number of sampling. It must be greater than burn, however there is no check.
    burn: number of samples being burned.
    count1: observed counts of condition 1
    count2: observed counts of condition 2

    return: list of log2-ratios
    """
    rseed(1)
    ratios = pyarray('f',[])
    ra = ratios.append
    for i in xrange(sample_number):
        x1 = rgamma(count1+1,1)
        x2 = rgamma(count2+1,1)
        ra( log(x1,2) - log(x2,2) )
    return ratios[int(burn):]

def get_gfold ( v1, v2, precompiled_get=None, cutoff=0.01, sample_number=10000, burn=500, offset=0, mcmc=False):    
    # try cached gfold in this module first
    if gfold_dict.has_key((v1,v2)):
        return gfold_dict[(v1,v2)]

    # calculate ratio+offset

    # first, get the value from precompiled table
    try:
        V = precompiled_get( v1, v2 )
        if v1 > v2:
            # X >= 0
            ret = max(0,V+offset)
        elif v1 < v2:
            # X < 0
            ret = min(0,V+offset)
        else:
            ret = 0.0
        
    except IndexError:
        if mcmc:
            numpyrand.seed([10])
            P_X = MCMCPoissonPosteriorRatio(sample_number,burn,v1,v2)
            i = int( (sample_number-burn) * cutoff)
        else:
            P_X = MLEPoissonPosteriorRatio(sample_number,0,v1,v2)
            i = int(sample_number * cutoff)            

        P_X = map(lambda x:x+offset,sorted(P_X))
        P_X_mean = float(sum(P_X))/len(P_X)
        
        if P_X_mean >= 0:
            # X >= 0
            ret = max(0,P_X[i])
        elif P_X_mean < 0:
            # X < 0
            ret = min(0,P_X[-1*i])
            
        #print v1,v2,P_X_mean,'-',offset,ret,i,P_X[i],P_X[-i]
    

    gfold_dict[(v1,v2)] = ret
    return ret

#def convert_gfold ( v, cutoff = 0.01, precompiled_gfold=None, mcmc=False ):
def convert_gfold ( v, precompiled_gfold, sample_number=15000, burn=5000, offset=0, cutoff=0.01, mcmc=False):
    """Take (name, count1, count2), try to extract precompiled gfold
    from precompiled_gfold.get; if failed, calculate the gfold using
    MCMC if mcmc is True, or simple MLE solution if mcmc is False.
    """
    ret = []
    retadd = ret.append
    get_func = precompiled_gfold.get
    for i in xrange(len(v[0])):
        rid= v[0][i]
        v1 = int(v[1][i])
        v2 = int(v[2][i])
        # calculate gfold from precompiled table, MCMC or MLE
        gf = get_gfold(v1,v2,precompiled_get=get_func,cutoff=cutoff,sample_number=sample_number,burn=burn,offset=offset,mcmc=mcmc)
        retadd([rid,gf])
    return ret

# ------------------------------------
# Classes
# ------------------------------------

########NEW FILE########
__FILENAME__ = diffpeak
# Time-stamp: <2014-02-24 11:35:25 Tao Liu>

"""Description: MACS 2 main executable

Copyright (c) 2008,2009 Yong Zhang, Tao Liu <taoliu@jimmy.harvard.edu>
Copyright (c) 2010,2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging
from time import strftime

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.IO import cBedGraphIO
from MACS2.IO.cDiffScore import DiffScoreTrackI
from MACS2.IO.cPeakIO import PeakIO
from MACS2.OptValidator import diff_opt_validate
from MACS2.OutputWriter import *
from MACS2.cProb import binomial_cdf_inv
from MACS2.cPeakModel import PeakModel,NotEnoughPairsException
from MACS2.cPeakDetect import PeakDetect
from MACS2.Constants import *
# ------------------------------------
# constants
# ------------------------------------
logging.basicConfig(level=20,
                    format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    stream=sys.stderr,
                    filemode="w"
                    )

# ------------------------------------
# Misc functions
# ------------------------------------
error   = logging.critical		# function alias
warn    = logging.warning
debug   = logging.debug
info    = logging.info
# ------------------------------------
# Main function
# ------------------------------------
def run( args ):
    """The Differential function/pipeline for MACS.
    
    """
    # Parse options...
    options = diff_opt_validate( args )
    #0 output arguments
#    info("\n"+options.argtxt)
 
    ofile_prefix = options.name
    
    # check if tag files exist
    with open(options.t1bdg) as f: pass
    with open(options.c1bdg) as f: pass
    with open(options.t2bdg) as f: pass
    with open(options.c2bdg) as f: pass
    
    if not options.peaks1 == '':
        info("Read peaks for condition 1...")
        p1io = PeakIO()
        with open(options.peaks1, 'rU') as f:
            p1io.read_from_xls(f)

    if not options.peaks2 == '':
        info("Read peaks for condition 2...")
        p2io = PeakIO()
        with open(options.peaks2, 'rU') as f:
            p2io.read_from_xls(f)
    
    #1 Read tag files
    info("Read and build treatment 1 bedGraph...")
    t1bio = cBedGraphIO.bedGraphIO(options.t1bdg)
    t1btrack = t1bio.build_bdgtrack()

    info("Read and build control 1 bedGraph...")
    c1bio = cBedGraphIO.bedGraphIO(options.c1bdg)
    c1btrack = c1bio.build_bdgtrack()

    if len(options.depth) >=2:
        depth1 = options.depth[0]
        depth2 = options.depth[1]
    else:
        depth1 = options.depth[0]
        depth2 = depth1
    
    info("Read and build treatment 2 bedGraph...")
    t2bio = cBedGraphIO.bedGraphIO(options.t2bdg)
    t2btrack = t2bio.build_bdgtrack()

    info("Read and build control 2 bedGraph...")
    c2bio = cBedGraphIO.bedGraphIO(options.c2bdg)
    c2btrack = c2bio.build_bdgtrack()
    
    #3 Call Peaks

    diffscore = DiffScoreTrackI( t1btrack,
                                 c1btrack,
                                 t2btrack,
                                 c2btrack,
                                 depth1, depth2 )
    diffscore.finalize()
    if options.call_peaks:
        diffscore.set_track_score_method(options.track_score_method)
        info("Calling peaks")
        if options.track_score_method == 'p':
            diffscore.call_peaks(cutoff = options.peaks_log_pvalue,
                                 min_length = options.pminlen)
        elif options.track_score_method == 'q':
            diffscore.call_peaks(cutoff = options.peaks_log_qvalue,
                                 min_length = options.pminlen)
        else:
            raise NotImplementedError
    else:
        info("Using existing peaks")
        diffscore.store_peaks(p1io, p2io)
        info("Rebuilding chromosomes")
        diffscore.rebuild_chromosomes()
        diffscore.annotate_peaks()
    
    info("Calling differentially occupied peaks")
    if options.score_method == 'p':
        diffscore.call_diff_peaks(cutoff = options.log_pvalue,
                                  min_length = options.dminlen,
                                  score_method = options.score_method)
    if options.score_method == 'q':
        diffscore.call_diff_peaks(cutoff = options.log_qvalue,
                                  min_length = options.dminlen,
                                  score_method = options.score_method)
#    diffscore.print_some_peaks()
#    diffscore.print_diff_peaks()
    
    info("Write output xls and BED files...")
    ofhd_xls = open( os.path.join( options.outdir, options.peakxls), "w" )
    ofhd_xls.write("# This file is generated by MACS version, using the diffpeak module %s\n" % (MACS_VERSION))
    ofhd_xls.write( options.argtxt+"\n" )
    ofhd_bed = open( os.path.join( options.outdir, options.peakbed), "w" )

    # pass write method so we can print too, and include name
    diffscore.write_peaks(xls=ofhd_xls, bed=ofhd_bed,
                    name = options.name, name_prefix="%s_peak_",
                    description="Peaks for %s (Made with MACS v2, " + strftime("%x") + ")",
                    trackline=options.trackline)
    ofhd_xls.close()
    ofhd_bed.close()
    
    if diffscore.has_peakio():
        info("Write annotated peak xls files...")
        ofhd_xls1 = open( os.path.join( options.outdir, options.peak1xls), "w" )
        ofhd_xls1.write("# This file is generated by MACS version, using the diffpeak module %s\n" % (MACS_VERSION))
        ofhd_xls1.write(options.argtxt+"\n")
        ofhd_xls2 = open( os.path.join( options.outdir, options.peak2xls), "w" )
        ofhd_xls2.write("# This file is generated by MACS version, using the diffpeak module %s\n" % (MACS_VERSION))
        ofhd_xls2.write(options.argtxt+"\n")
        diffscore.write_peaks_by_summit(ofhd_xls1, ofhd_xls2,
                                        name = options.name, name_prefix="%s_peak_")
        ofhd_xls1.close()
        ofhd_xls2.close()
    
    if options.store_bdg:
        info("#4 Write output bedgraph files...")
        ofhd_logLR = open( os.path.join( options.outdir, options.bdglogLR), "w" )
        ofhd_pvalue = open( os.path.join( options.outdir, options.bdgpvalue), "w" )
        ofhd_logFC = open( os.path.join( options.outdir, options.bdglogFC), "w" )
        diffscore.write_bedgraphs(logLR=ofhd_logLR, pvalue=ofhd_pvalue,
                                  logFC=ofhd_logFC, name = options.name,
                                  description=" for %s (Made with MACS v2, " + strftime("%x") + ")",
                                  trackline=options.trackline)
        ofhd_logLR.close()
        ofhd_pvalue.close()
        ofhd_logFC.close()
        
    
def cal_max_dup_tags ( genome_size, tags_number, p=1e-5 ):
    """Calculate the maximum duplicated tag number based on genome
    size, total tag number and a p-value based on binomial
    distribution. Brute force algorithm to calculate reverse CDF no
    more than MAX_LAMBDA(100000).
    
    """
    return binomial_cdf_inv(1-p,tags_number,1.0/genome_size)

def load_frag_files_options ( options ):
    """From the options, load treatment fragments and control fragments (if available).

    """
    options.info("#1 read treatment fragments...")

    tp = options.parser(options.tfile[0])
    treat = tp.build_petrack()
    treat.sort()
    if len(options.tfile) > 1:
        # multiple input
        for tfile in options.tfile[1:]:
            tp = options.parser(tfile)
            treat = tp.append_petrack( treat )
            treat.sort()

    options.tsize = tp.d
    if options.cfile:
        options.info("#1.2 read input fragments...")
        cp = options.parser(options.cfile[0])
        control = cp.build_petrack()
        control_d = cp.d
        control.sort()
        if len(options.cfile) > 1:
            # multiple input
            for cfile in options.cfile[1:]:
                cp = options.parser(cfile)
                control = cp.append_petrack( control )
                control.sort()
    else:
        control = None
    options.info("#1 mean fragment size is determined as %d bp from treatment" % options.tsize)
#    options.info("#1 fragment size variance is determined as %d bp from treatment" % tp.variance)
    if control is not None:
        options.info("#1 note: mean fragment size in control is %d bp -- value ignored" % control_d)
    return (treat, control)

def load_tag_files_options ( options ):
    """From the options, load treatment tags and control tags (if available).

    """
    options.info("#1 read treatment tags...")
    tp = options.parser(options.tfile[0])
    if not options.tsize:           # override tsize if user specified --tsize
        ttsize = tp.tsize()
        options.tsize = ttsize
    treat = tp.build_fwtrack()
    treat.sort()
    if len(options.tfile) > 1:
        # multiple input
        for tfile in options.tfile[1:]:
            tp = options.parser(tfile)
            treat = tp.append_fwtrack( treat )
            treat.sort()
    
    if options.cfile:
        options.info("#1.2 read input tags...")
        control = options.parser(options.cfile[0]).build_fwtrack()
        control.sort()
        if len(options.cfile) > 1:
            # multiple input
            for cfile in options.cfile[1:]:
                cp = options.parser(cfile)
                control = cp.append_fwtrack( control )
                control.sort()
    else:
        control = None
    options.info("#1 tag size is determined as %d bps" % options.tsize)
    return (treat, control)

########NEW FILE########
__FILENAME__ = filterdup
# Time-stamp: <2013-10-28 01:19:30 Tao Liu>

"""Description: Filter duplicate reads depending on sequencing depth.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate_filterdup as opt_validate
from MACS2.cProb import binomial_cdf_inv
from MACS2.Constants import *
# ------------------------------------
# Main function
# ------------------------------------
def run( o_options ):
    """The Main function/pipeline for duplication filter.
    
    """
    # Parse options...
    options = opt_validate( o_options )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error

    if options.outputfile != "stdout":
        outfhd = open( os.path.join( options.outdir, options.outputfile ) ,"w" )
    else:
        outfhd = sys.stdout
    
    #1 Read tag files
    info("read tag files...")
    fwtrack = load_tag_files_options (options)
    
    info("tag size = %d" % options.tsize)
    fwtrack.fw = options.tsize

    t0 = fwtrack.total
    info(" total tags in alignment file: %d" % (t0))
    if options.keepduplicates != "all":
        if options.keepduplicates == "auto":
            info("calculate max duplicate tags in single position based on binomal distribution...")
            max_dup_tags = cal_max_dup_tags(options.gsize,t0)
            info(" max_dup_tags based on binomal = %d" % (max_dup_tags))
            info("filter out redundant tags at the same location and the same strand by allowing at most %d tag(s)" % (max_dup_tags))
        else:
            info("user defined the maximum tags...")
            max_dup_tags = int(options.keepduplicates)
            info("filter out redundant tags at the same location and the same strand by allowing at most %d tag(s)" % (max_dup_tags))

        fwtrack = fwtrack.filter_dup(max_dup_tags)
        t1 = fwtrack.total
        info(" tags after filtering in alignment file: %d" % (t1))
        info(" Redundant rate of alignment file: %.2f" % (float(t0-t1)/t0))
    info("Write to BED file")
    fwtrack.print_to_bed(fhd=outfhd)
    info("finished! Check %s." % options.outputfile)

def cal_max_dup_tags ( genome_size, tags_number, p=1e-5 ):
    """Calculate the maximum duplicated tag number based on genome
    size, total tag number and a p-value based on binomial
    distribution. Brute force algorithm to calculate reverse CDF no
    more than MAX_LAMBDA(100000).
    
    """
    return binomial_cdf_inv(1-p,tags_number,1.0/genome_size)

def load_tag_files_options ( options ):
    """From the options, load alignment tags.

    """
    options.info("read alignment tags...")
    tp = options.parser(options.ifile)

    if not options.tsize:           # override tsize if user specified --tsize
        ttsize = tp.tsize()
        options.tsize = ttsize

    treat = tp.build_fwtrack()
    treat.sort()

    options.info("tag size is determined as %d bps" % options.tsize)
    return treat


########NEW FILE########
__FILENAME__ = BinKeeper
# Time-stamp: <2011-03-14 17:52:00 Tao Liu>

"""Module Description: BinKeeper for Wiggle-like tracks.

Copyright (c) 2008 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import sys
import re
from bisect import insort,bisect_left,bisect_right,insort_right
from array import array
# ------------------------------------
# constants
# ------------------------------------
# to determine the byte size
if array('H',[1]).itemsize == 2:
    BYTE2 = 'H'
else:
    raise Exception("BYTE2 type cannot be determined!")

if array('I',[1]).itemsize == 4:
    BYTE4 = 'I'
elif array('L',[1]).itemsize == 4:
    BYTE4 = 'L'
else:
    raise Exception("BYTE4 type cannot be determined!")

if array('f',[1]).itemsize == 4:
    FBYTE4 = 'f'
elif array('d',[1]).itemsize == 4:
    FBYTE4 = 'd'
else:
    raise Exception("BYTE4 type cannot be determined!")

# ------------------------------------
# Misc functions
# ------------------------------------

# ------------------------------------
# Classes
# ------------------------------------
class BinKeeperI:
    """BinKeeper keeps point data from a chromosome in a bin list.

    Example:
    >>> from taolib.CoreLib.Parser import WiggleIO
    >>> w = WiggleIO('sample.wig')
    >>> bk = w.build_binKeeper()
    >>> bk['chrI'].pp2v(1000,2000) # to extract values in chrI:1000..2000
    """
    def __init__ (self,binsize=8000,chromosomesize=1e9):
        """Initializer.

        Parameters:
        binsize : size of bin in Basepair
        chromosomesize : size of chromosome, default is 1G
        """
        self.binsize = binsize
        self.binnumber = int(chromosomesize/self.binsize)+1
        self.cage = []
        a = self.cage.append
        for i in xrange(self.binnumber):
            a([array(BYTE4,[]),array(FBYTE4,[])])

    def add ( self, p, value ):
        """Add a position into BinKeeper.

        Note: position must be sorted before adding. Otherwise, pp2v
        and pp2p will not work.
        """
        bin = p/self.binsize
        self.cage[bin][0].append(p)
        self.cage[bin][1].append(value)        

    def p2bin (self, p ):
        """Return the bin index for a position.
        
        """
        return p/self.binsize

    def p2cage (self, p):
        """Return the bin containing the position.
        
        """
        return self.cage[p/self.binsize]

    def __pp2cages (self, p1, p2):
        assert p1<=p2
        bin1 = self.p2bin(p1)
        bin2 = self.p2bin(p2)+1
        t = [array(BYTE4,[]),array(FBYTE4,[])]
        for i in xrange(bin1,bin2):
            t[0].extend(self.cage[i][0])
            t[1].extend(self.cage[i][1])            
        return t

    def pp2p (self, p1, p2):
        """Give the position list between two given positions.

        Parameters:
        p1 : start position
        p2 : end position
        Return Value:
        list of positions between p1 and p2.
        """
        (ps,vs) = self.__pp2cages(p1,p2)
        p1_in_cages = bisect_left(ps,p1)
        p2_in_cages = bisect_right(ps,p2)
        return ps[p1_in_cages:p2_in_cages]

    def pp2v (self, p1, p2):
        """Give the value list between two given positions.

        Parameters:
        p1 : start position
        p2 : end position
        Return Value:
        list of values whose positions are between p1 and p2.
        """
        (ps,vs) = self.__pp2cages(p1,p2)
        p1_in_cages = bisect_left(ps,p1)
        p2_in_cages = bisect_right(ps,p2)
        return vs[p1_in_cages:p2_in_cages]


    def pp2pv (self, p1, p2):
        """Give the (position,value) list between two given positions.

        Parameters:
        p1 : start position
        p2 : end position
        Return Value:
        list of (position,value) between p1 and p2.
        """
        (ps,vs) = self.__pp2cages(p1,p2)
        p1_in_cages = bisect_left(ps,p1)
        p2_in_cages = bisect_right(ps,p2)
        return zip(ps[p1_in_cages:p2_in_cages],vs[p1_in_cages:p2_in_cages])


class BinKeeperII:
    """BinKeeperII keeps non-overlapping interval data from a chromosome in a bin list.

    This is especially designed for bedGraph type data.

    """
    def __init__ (self,binsize=8000,chromosomesize=1e9):
        """Initializer.

        Parameters:
        binsize : size of bin in Basepair
        chromosomesize : size of chromosome, default is 1G
        """
        self.binsize = binsize
        self.binnumber = int(chromosomesize/self.binsize)+1
        self.cage = []
        a = self.cage.append
        for i in xrange(self.binnumber):
            a([array(BYTE4,[]),array(BYTE4,[]),array(FBYTE4,[])])

    def add ( self, startp, endp, value ):
        """Add an interval data into BinKeeper.

        Note: position must be sorted before adding. Otherwise, pp2v
        and pp2p will not work.
        """
        startbin = startp/self.binsize
        endbin = endp/self.binsize
        if startbin == endbin:
            # some intervals may only be within a bin
            j = bisect.bisect_left(self.cage[startbin][0],startp)
            self.cage[startbin][0].insert(j,startp)
            self.cage[startbin][1].insert(j,endp)
            self.cage[startbin][2].insert(j,value)
        else:
            # some intervals may cover the end of bins
            # first bin
            j = bisect.bisect_left(self.cage[startbin][0],startp)
            self.cage[startbin][0].insert(j,startp)
            self.cage[startbin][1].insert(j,(startbin+1)*self.binsize)
            self.cage[startbin][2].insert(j,value)
            # other bins fully covered
            for i in xrange(startbin+1,endbin):
                p = i*self.binsize
                j = bisect.bisect_left(self.cage[startbin][0],p)
                self.cage[startbin][0].insert(j,p)
                self.cage[startbin][1].insert(j,(i+1)*self.binsize)
                self.cage[startbin][2].insert(j,value)

                insort_right(self.cage[i][0],i*self.binsize)
                insort_right(self.cage[i][1],(i+1)*self.binsize)
                insort_right(self.cage[i][2],value)
            # last bin -- the start of this bin should be covered
            insort_right(self.cage[endbin][0],endbin*self.binsize)
            insort_right(self.cage[endbin][1],endp)
            insort_right(self.cage[endbin][2],value)

    def p2bin (self, p ):
        """Given a position, return the bin index for a position.
        
        """
        return p/self.binsize

    def p2cage (self, p):
        """Given a position, return the bin containing the position.
        
        """
        return self.cage[p/self.binsize]

    def pp2cages (self, p1, p2):
        """Given an interval, return the bins containing this interval.
        
        """
        assert p1<=p2
        bin1 = self.p2bin(p1)
        bin2 = self.p2bin(p2)
        t = [array(BYTE4,[]),array(BYTE4,[]),array(FBYTE4,[])]
        for i in xrange(bin1,bin2+1):
            t[0].extend(self.cage[i][0])
            t[1].extend(self.cage[i][1])
            t[2].extend(self.cage[i][2])                        
        return t

    def pp2intervals (self, p1, p2):
        """Given an interval, return the intervals list between two given positions.

        Parameters:
        p1 : start position
        p2 : end position
        Return Value:
        A list of intervals start and end positions (tuple) between p1 and p2.

        * Remember, I assume all intervals saved in this BinKeeperII
          are not overlapping, so if there is some overlap, this
          function will not work as expected.
        """
        (startposs,endposs,vs) = self.pp2cages(p1,p2)
        p1_in_cages = bisect_left(startposs,p1)
        p2_in_cages = bisect_right(endposs,p2)
        output_startpos_list = startposs[p1_in_cages:p2_in_cages]
        output_endpos_list = endposs[p1_in_cages:p2_in_cages]

        # check if the bin (p1_in_cages-1) covers p1
        if p1 < endposs[p1_in_cages-1]:
            # add this interval
            output_startpos_list = array(BYTE4,[p1,])+output_startpos_list
            output_endpos_list = array(BYTE4,[endposs[p1_in_cages-1],])+output_endpos_list

        # check if the bin (p2_in_cages+1) covers p2
        if p2 > startposs[p2_in_cages+1]:
            # add this interval
            output_startpos_list = array(BYTE4,[startposs[p2_in_cages+1],])+output_startpos_list
            output_endpos_list = array(BYTE4,[p2,])+output_endpos_list

        return zip(output_startpos_list,output_endpos_list)

    def pp2pvs (self, p1, p2):
        """Given an interval, return the values list between two given positions.

        Parameters:
        p1 : start position
        p2 : end position
        Return Value:

        A list of start, end positions, values (tuple) between p1 and
        p2. Each value represents the value in an interval. Remember
        the interval length and positions are lost in the output.

        * Remember, I assume all intervals saved in this BinKeeperII
          are not overlapping, so if there is some overlap, this
          function will not work as expected.
        """

        (startposs,endposs,vs) = self.pp2cages(p1,p2)
        p1_in_cages = bisect_left(startposs,p1)
        p2_in_cages = bisect_right(endposs,p2)
        output_startpos_list = startposs[p1_in_cages:p2_in_cages]
        output_endpos_list = endposs[p1_in_cages:p2_in_cages]
        output_value_list = vs[p1_in_cages:p2_in_cages]

        # print p1_in_cages,p2_in_cages
        # print vs
        print output_startpos_list
        print output_endpos_list
        print output_value_list

        # check if the bin (p1_in_cages-1) covers p1
        
        if p1_in_cages-1 >= 0 and p1 < self.cage[p1_in_cages-1][1]:
            # add this interval
            output_startpos_list = array(BYTE4,[p1,])+output_startpos_list
            output_endpos_list = array(BYTE4,[self.cage[p1_in_cages-1][1],])+output_endpos_list
            output_value_list = array(BYTE4,[self.cage[p1_in_cages-1][2],])+output_value_list
                

        # check if the bin (p2_in_cages+1) covers p2
        #print p2_in_cages+1,len(self.cage)
        #print p2, self.cage[p2_in_cages+1][0]
        if p2_in_cages+1 < len(self.cage) and p2 > self.cage[p2_in_cages+1][0]:
            # add this interval
            output_startpos_list = output_startpos_list+array(BYTE4,[self.cage[p2_in_cages+1][0],])
            output_endpos_list = output_endpos_list+array(BYTE4,[p2,])
            output_value_list = output_value_list+array(BYTE4,[self.cage[p2_in_cages+1][2],])

        print output_startpos_list
        print output_endpos_list
        print output_value_list

        return zip(output_startpos_list,output_endpos_list,output_value_list)


########NEW FILE########
__FILENAME__ = WiggleIO
# Time-stamp: <2011-05-17 16:11:19 Tao Liu>

"""Module Description

Copyright (c) 2008 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------
import os
import sys
import re
import shutil
from MACS2.IO.cFeatIO import WigTrackI
from MACS2.IO.BinKeeper import BinKeeperI

import time
# ------------------------------------
# constants
# ------------------------------------

# ------------------------------------
# Misc functions
# ------------------------------------

# ------------------------------------
# Classes
# ------------------------------------

class WiggleIO:
    """File Parser Class for Wiggle File.

    Note: Only can be used with the wiggle file generated by pMA2C or
    MACS. This module can not be univerally used.

    Note2: The positions in Wiggle File must be sorted for every
    chromosome.

    Example:
    >>> from Cistrome.CoreLib.Parser import WiggleIO
    >>> w = WiggleIO('sample.wig')
    >>> bk = w.build_binKeeper()
    >>> wtrack = w.build_wigtrack()    
    """
    def __init__ (self,f):
        """f must be a filename or a file handler.
        
        """
        if type(f) == str:
            self.fhd = open(f,"r")
        elif type(f) == file:
            self.fhd = f
        else:
            raise Exception("f must be a filename or a file handler.")

    def build_wigtrack (self):
        """Use this function to return a WigTrackI.

        """
        data = WigTrackI()
        add_func = data.add_loc
        chrom = "Unknown"
        span = 0
        pos_fixed = 0      # pos for fixedStep data 0: variableStep, 1: fixedStep
        for i in self.fhd:
            if i.startswith("track"):
                continue
            elif i.startswith("#"):
                continue
            elif i.startswith("browse"):
                continue
            elif i.startswith("variableStep"): # define line
                pos_fixed = 0
                chromi = i.rfind("chrom=")  # where the 'chrom=' is
                spani = i.rfind("span=")   # where the 'span=' is
                if chromi != -1:
                    chrom = i[chromi+6:].strip().split()[0]
                else:
                    chrom = "Unknown"
                if spani != -1:
                    span = int(i[spani+5:].strip().split()[0])
                else:
                    span = 0
            elif i.startswith("fixedStep"):
                chromi = i.rfind("chrom=")  # where the 'chrom=' is
                starti = i.rfind("start=")  # where the 'chrom=' is
                stepi = i.rfind("step=")  # where the 'chrom=' is
                spani = i.rfind("span=")   # where the 'span=' is
                if chromi != -1:
                    chrom = i[chromi+6:].strip().split()[0]
                else:
                    raise Exception("fixedStep line must define chrom=XX")
                if spani != -1:
                    span = int(i[spani+5:].strip().split()[0])
                else:
                    span = 0
                if starti != -1:
                    pos_fixed = int(i[starti+6:].strip().split()[0])
                    if pos_fixed < 1:
                        raise Exception("fixedStep start must be bigger than 0!")
                else:
                    raise Exception("fixedStep line must define start=XX")
                if stepi != -1:
                    step = int(i[stepi+5:].strip().split()[0])
                else:
                    raise Exception("fixedStep line must define step=XX!")
            else:                       # read data value
                if pos_fixed:           # fixedStep
                    value = i.strip()
                    add_func(chrom,int(pos_fixed),float(value))
                    pos_fixed += step
                else:                   # variableStep
                    try:
                        (pos,value) = i.split()
                    except ValueError:
                        print i,pos_fixed
                    add_func(chrom,int(pos),float(value))
        data.span = span
        self.fhd.seek(0)
        return data

    def build_binKeeper (self,chromLenDict={},binsize=200):
        """Use this function to return a dictionary of BinKeeper
        objects.

        chromLenDict is a dictionary for chromosome length like

        {'chr1':100000,'chr2':200000}

        bin is in bps. for detail, check BinKeeper.
        """
        data = {}
        chrom = "Unknown"
        pos_fixed = 0
        for i in self.fhd:
            if i.startswith("track"):
                continue
            elif i.startswith("browse"):
                continue
            elif i.startswith("#"):
                continue
            elif i.startswith("variableStep"): # define line
                pos_fixed = 0
                chromi = i.rfind("chrom=")  # where the 'chrom=' is
                spani = i.rfind("span=")   # where the 'span=' is
                if chromi != -1:
                    chrom = i[chromi+6:].strip().split()[0]
                else:
                    chrom = "Unknown"
                if spani != -1:
                    span = int(i[spani+5:].strip().split()[0])
                else:
                    span = 0

                chrlength = chromLenDict.setdefault(chrom,250000000) + 10000000
                data.setdefault(chrom,BinKeeperI(binsize=binsize,chromosomesize=chrlength))
                add = data[chrom].add

            elif i.startswith("fixedStep"):
                chromi = i.rfind("chrom=")  # where the 'chrom=' is
                starti = i.rfind("start=")  # where the 'chrom=' is
                stepi = i.rfind("step=")  # where the 'chrom=' is
                spani = i.rfind("span=")   # where the 'span=' is
                if chromi != -1:
                    chrom = i[chromi+6:].strip().split()[0]
                else:
                    raise Exception("fixedStep line must define chrom=XX")
                if spani != -1:
                    span = int(i[spani+5:].strip().split()[0])
                else:
                    span = 0
                if starti != -1:
                    pos_fixed = int(i[starti+6:].strip().split()[0])
                    if pos_fixed < 1:
                        raise Exception("fixedStep start must be bigger than 0!")
                else:
                    raise Exception("fixedStep line must define start=XX")
                if stepi != -1:
                    step = int(i[stepi+5:].strip().split()[0])
                else:
                    raise Exception("fixedStep line must define step=XX!")
                chrlength = chromLenDict.setdefault(chrom,250000000) + 10000000
                data.setdefault(chrom,BinKeeperI(binsize=binsize,chromosomesize=chrlength))
                
                add = data[chrom].add

            else:                       # read data value
                if pos_fixed:           # fixedStep
                    value = i.strip()
                    add(int(pos_fixed),float(value))
                    pos_fixed += step
                else:                   # variableStep
                    try:
                        (pos,value) = i.split()
                    except ValueError:
                        print i,pos_fixed
                    add(int(pos),float(value))

        self.fhd.seek(0)
        return data


########NEW FILE########
__FILENAME__ = OptValidator
# Time-stamp: <2013-10-28 12:21:24 Tao Liu>

"""Module Description

Copyright (c) 2010,2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------
import sys
import os
import re
import logging
from argparse import ArgumentError
from subprocess import Popen, PIPE
from math import log
from MACS2.IO.cParser import BEDParser, ELANDResultParser, ELANDMultiParser, \
                             ELANDExportParser, SAMParser, BAMParser, \
                             BAMPEParser, BowtieParser,  guess_parser
# ------------------------------------
# constants
# ------------------------------------

efgsize = {"hs":2.7e9,
           "mm":1.87e9,
           "ce":9e7,
           "dm":1.2e8}

# ------------------------------------
# Misc functions
# ------------------------------------
def opt_validate ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # gsize
    try:
        options.gsize = efgsize[options.gsize]
    except:
        try:
            options.gsize = float(options.gsize)
        except:
            logging.error("Error when interpreting --gsize option: %s" % options.gsize)
            logging.error("Available shortcuts of effective genome sizes are %s" % ",".join(efgsize.keys()))
            sys.exit(1)

    # format
    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BAMPE":
        options.parser = BAMPEParser
        options.gzip_flag = True
        options.nomodel = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # duplicate reads
    if options.keepduplicates != "auto" and options.keepduplicates != "all":
        if not options.keepduplicates.isdigit():
            logging.error("--keep-dup should be 'auto', 'all' or an integer!")
            sys.exit(1)

    # shiftsize>0
    if options.shiftsize:               # only if --shiftsize is set, it's true
        options.extsize = 2 * options.shiftsize
    else:                               # if --shiftsize is not set
        options.shiftsize = options.extsize / 2
    if options.shiftsize <= 0 :
        logging.error("--extsize must > 1 and --shiftsize must > 0!")
        sys.exit(1)

    # refine_peaks, call_summits can't be combined with --broad
    #if options.broad and (options.refine_peaks or options.call_summits):
    #    logging.error("--broad can't be combined with --refine-peaks or --call-summits!")
    #    sys.exit(1)

    if options.broad and options.call_summits:
        logging.error("--broad can't be combined with --call-summits!")
        sys.exit(1)

    if options.pvalue:
        # if set, ignore qvalue cutoff
        options.log_qvalue = None
        options.log_pvalue = log(options.pvalue,10)*-1
    else:
        options.log_qvalue = log(options.qvalue,10)*-1
        options.log_pvalue = None
    if options.broad:
        options.log_broadcutoff = log(options.broadcutoff,10)*-1
    
    # uppercase the format string 
    options.format = options.format.upper()

    # upper and lower mfold
    options.lmfold = options.mfold[0]
    options.umfold = options.mfold[1]
    if options.lmfold > options.umfold:
        logging.error("Upper limit of mfold should be greater than lower limit!" % options.mfold)
        sys.exit(1)
    
    # output filenames
    options.peakxls = os.path.join( options.outdir, options.name+"_peaks.xls" )
    options.peakbed = os.path.join( options.outdir, options.name+"_peaks.bed" )
    options.peakNarrowPeak = os.path.join( options.outdir, options.name+"_peaks.narrowPeak" )
    options.peakBroadPeak = os.path.join( options.outdir, options.name+"_peaks.broadPeak" )
    options.peakGappedPeak = os.path.join( options.outdir, options.name+"_peaks.gappedPeak" )
    options.summitbed = os.path.join( options.outdir, options.name+"_summits.bed" )
    options.bdg_treat = os.path.join( options.outdir, options.name+"_treat_pileup.bdg" )
    options.bdg_control= os.path.join( options.outdir, options.name+"_control_lambda.bdg" )
    #options.negxls  = os.path.join( options.name+"_negative_peaks.xls" )
    #options.diagxls = os.path.join( options.name+"_diag.xls" )
    options.modelR  = os.path.join( options.outdir, options.name+"_model.r" )
    #options.pqtable  = os.path.join( options.outdir, options.name+"_pq_table.txt" )

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    options.argtxt = "\n".join((
        "# Command line: %s" % " ".join(sys.argv[1:]),\
        "# ARGUMENTS LIST:",\
        "# name = %s" % (options.name),\
        "# format = %s" % (options.format),\
        "# ChIP-seq file = %s" % (options.tfile),\
        "# control file = %s" % (options.cfile),\
        "# effective genome size = %.2e" % (options.gsize),\
        #"# tag size = %d" % (options.tsize),\
        "# band width = %d" % (options.bw),\
        "# model fold = %s\n" % (options.mfold),\
        ))

    if options.pvalue:
        options.argtxt +=  "# pvalue cutoff = %.2e\n" % (options.pvalue)
        options.argtxt +=  "# qvalue will not be calculated and reported as -1 in the final output.\n"
    else:
        options.argtxt +=  "# qvalue cutoff = %.2e\n" % (options.qvalue)

    if options.downsample:
        options.argtxt += "# Larger dataset will be randomly sampled towards smaller dataset.\n"
        if options.seed >= 0:
            options.argtxt += "# Random seed has been set as: %d\n" % options.seed
    else:
        if options.tolarge:
            options.argtxt += "# Smaller dataset will be scaled towards larger dataset.\n"
        else:
            options.argtxt += "# Larger dataset will be scaled towards smaller dataset.\n"

    if options.ratio != 1.0:
	options.argtxt += "# Using a custom scaling factor: %.2e\n" % (options.ratio)
	
    if options.cfile:
        options.argtxt += "# Range for calculating regional lambda is: %d bps and %d bps\n" % (options.smalllocal,options.largelocal)
    else:
        options.argtxt += "# Range for calculating regional lambda is: %d bps\n" % (options.largelocal)

    if options.broad:
        options.argtxt += "# Broad region calling is on\n"
    else:
        options.argtxt += "# Broad region calling is off\n"

    #if options.refine_peaks:
    #    options.argtxt += "# Refining peak for read balance is on\n"
    if options.call_summits:
        options.argtxt += "# Searching for subpeak summits is on\n"

    if options.halfext:
        options.argtxt += "# MACS will make 1/2d size fragments\n"

    if options.do_SPMR and options.store_bdg:
        options.argtxt += "# MACS will save fragment pileup signal per million reads\n"        

    return options

def diff_opt_validate ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # format
    options.gzip_flag = False           # if the input is gzip file
    
#    options.format = options.format.upper()
    # fox this stuff
#    if True: pass
#    elif options.format == "AUTO":
#        options.parser = guess_parser
#    else:
#        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
#        sys.exit(1)
    
    if options.peaks_pvalue:
        # if set, ignore qvalue cutoff
        options.peaks_log_qvalue = None
        options.peaks_log_pvalue = log(options.peaks_pvalue,10)*-1
        options.track_score_method = 'p'
    else:
        options.peaks_log_qvalue = log(options.peaks_qvalue,10)*-1
        options.peaks_log_pvalue = None
        options.track_score_method = 'q'

    if options.diff_pvalue:
        # if set, ignore qvalue cutoff
        options.log_qvalue = None
        options.log_pvalue = log(options.diff_pvalue,10)*-1
        options.score_method = 'p'
    else:
        options.log_qvalue = log(options.diff_qvalue,10)*-1
        options.log_pvalue = None
        options.score_method = 'q'
    
    # output filenames
    options.peakxls = options.name+"_diffpeaks.xls"
    options.peakbed = options.name+"_diffpeaks.bed"
    options.peak1xls = options.name+"_diffpeaks_by_peaks1.xls"
    options.peak2xls = options.name+"_diffpeaks_by_peaks2.xls"
    options.bdglogLR = options.name+"_logLR.bdg"
    options.bdgpvalue = options.name+"_logLR.bdg"
    options.bdglogFC = options.name+"_logLR.bdg"
    
    options.call_peaks = True
    if not (options.peaks1 == '' or options.peaks2 == ''):
        if options.peaks1 == '':
            raise ArgumentError('peaks1', 'Must specify both peaks1 and peaks2, or neither (to call peaks again)')
        elif options.peaks2 == '':
            raise ArgumentError('peaks2', 'Must specify both peaks1 and peaks2, or neither (to call peaks again)')
        options.call_peaks = False
        options.argtxt = "\n".join((
            "# ARGUMENTS LIST:",\
            "# name = %s" % (options.name),\
#            "# format = %s" % (options.format),\
            "# ChIP-seq file 1 = %s" % (options.t1bdg),\
            "# control file 1 = %s" % (options.c1bdg),\
            "# ChIP-seq file 2 = %s" % (options.t2bdg),\
            "# control file 2 = %s" % (options.c2bdg),\
            "# Peaks, condition 1 = %s" % (options.peaks1),\
            "# Peaks, condition 2 = %s" % (options.peaks2),\
            ""
            ))
    else:
        options.argtxt = "\n".join((
            "# ARGUMENTS LIST:",\
            "# name = %s" % (options.name),\
#            "# format = %s" % (options.format),\
            "# ChIP-seq file 1 = %s" % (options.t1bdg),\
            "# control file 1 = %s" % (options.c1bdg),\
            "# ChIP-seq file 2 = %s" % (options.t2bdg),\
            "# control file 2 = %s" % (options.c2bdg),\
            ""
            ))
         
        if options.peaks_pvalue:
            options.argtxt +=  "# treat/control -log10(pvalue) cutoff = %.2e\n" % (options.peaks_log_pvalue)
            options.argtxt +=  "# treat/control -log10(qvalue) will not be calculated and reported as -1 in the final output.\n"
        else:
            options.argtxt +=  "# treat/control -log10(qvalue) cutoff = %.2e\n" % (options.peaks_log_qvalue)
        
    if options.diff_pvalue:
        options.argtxt +=  "# differential pvalue cutoff = %.2e\n" % (options.log_pvalue)
        options.argtxt +=  "# differential qvalue will not be calculated and reported as -1 in the final output.\n"
    else:
        options.argtxt +=  "# differential qvalue cutoff = %.2e\n" % (options.log_qvalue)

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    return options

def opt_validate_diff ( optparser ):
    """Validate options from a OptParser object. (temporarily not used at all)

    This parser is for macsdiffrun.

    Ret: Validated options object.
    """
    (options,args) = optparser.parse_args()

    # gsize
    try:
        options.gsize = efgsize[options.gsize]
    except:
        try:
            options.gsize = float(options.gsize)
        except:
            logging.error("Error when interpreting --gsize option: %s" % options.gsize)
            logging.error("Available shortcuts of effective genome sizes are %s" % ",".join(efgsize.keys()))
            sys.exit(1)


    # treatment file
    if not options.tfile1 or not options.tfile2:       # only required argument
        logging.error("--t1 and --t2 are required!")
        optparser.print_help()
        sys.exit(1)

    # control file
    if not options.cfile1 and not options.cfile2:
        logging.error("At least, either --c1 or --c2 should be set!")
        optparser.print_help()
        sys.exit(1)
    if not options.cfile1 and options.cfile2:
        options.cfile1 = options.cfile2
    elif options.cfile1 and not options.cfile2:
        options.cfile2 = options.cfile1

    # Check file assessibility.
    flag = True
    for fn in (options.tfile1, options.tfile2, options.cfile1, options.cfile2):
        if os.path.isfile(fn):
            pass
        else:
            logging.error("Can't access file: %s" % fn)
            flag = False
    if not flag:
        sys.exit(1)

    # format

    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # duplicate reads
    if options.keepduplicates != "auto" and options.keepduplicates != "all":
        if not options.keepduplicates.isdigit():
            logging.error("--keep-dup should be 'auto', 'all' or an integer!")
            sys.exit(1)

    # shiftsize>0
    if options.shiftsize <=0 :
        logging.error("--shiftsize must > 0!")
        sys.exit(1)

    if options.pvalue:
        # if set, ignore qvalue cutoff
        options.log_qvalue = None
        options.log_pvalue = log(options.pvalue,10)*-1
    else:
        options.log_qvalue = log(options.qvalue,10)*-1
        options.log_pvalue = None

    # uppercase the format string 
    options.format = options.format.upper()

    # upper and lower mfold
    try:
        (options.lmfold,options.umfold) = map(int, options.mfold.split(","))
    except:
        logging.error("mfold format error! Your input is '%s'. It should be like '10,30'." % options.mfold)
        sys.exit(1)
    
    # output filenames
    options.condition1_peakbed = options.name+"_condition1_unique_peaks.bed"
    options.condition2_peakbed = options.name+"_condition2_unique_peaks.bed"
    options.consistent_peakbed = options.name+"_consistent_peaks.bed"
    
    options.zbdg_tr = options.name+"_treat"
    options.zbdg_ctl= options.name+"_control"

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    options.argtxt = "\n".join((
        "# ARGUMENTS LIST:",\
        "# name = %s" % (options.name),\
        "# format = %s" % (options.format),\
        "# ChIP-seq file for condition 1 = %s" % (options.tfile1),\
        "# ChIP-seq file for condition 2 = %s" % (options.tfile2),\
        "# control file for condition 1 = %s" % (options.cfile1),\
        "# control file for condition 2 = %s" % (options.cfile2),\
        "# effective genome size = %.2e" % (options.gsize),\
        "# band width = %d" % (options.bw),\
        "# model fold = %s\n" % (options.mfold),\
        ))

    if options.pvalue:
        options.argtxt +=  "# pvalue cutoff = %.2e\n" % (options.pvalue)
        options.argtxt +=  "# qvalue will not be calculated and reported as -1 in the final output.\n"
    else:
        options.argtxt +=  "# qvalue cutoff = %.2e\n" % (options.qvalue)

    # if options.tolarge:
    #     options.argtxt += "# Smaller dataset will be scaled towards larger dataset.\n"
    # else:
    #     options.argtxt += "# Larger dataset will be scaled towards smaller dataset.\n"

    if options.cfile1 or options.cfile2:
        options.argtxt += "# Range for calculating regional lambda is: %d bps and %d bps\n" % (options.smalllocal,options.largelocal)
    else:
        options.argtxt += "# Range for calculating regional lambda is: %d bps\n" % (options.largelocal)

    return options

def opt_validate_filterdup ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # gsize
    try:
        options.gsize = efgsize[options.gsize]
    except:
        try:
            options.gsize = float(options.gsize)
        except:
            logging.error("Error when interpreting --gsize option: %s" % options.gsize)
            logging.error("Available shortcuts of effective genome sizes are %s" % ",".join(efgsize.keys()))
            sys.exit(1)

    # format

    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # duplicate reads
    if options.keepduplicates != "auto" and options.keepduplicates != "all":
        if not options.keepduplicates.isdigit():
            logging.error("--keep-dup should be 'auto', 'all' or an integer!")
            sys.exit(1)

    # uppercase the format string 
    options.format = options.format.upper()

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    return options

def opt_validate_randsample ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # format

    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # uppercase the format string 
    options.format = options.format.upper()

    # percentage or number
    if options.percentage:
        if options.percentage > 100.0:
            logging.error("Percentage can't be bigger than 100.0. Please check your options and retry!")
            sys.exit(1)
    elif options.number:
        if options.number <= 0:
            logging.error("Number of tags can't be smaller than or equal to 0. Please check your options and retry!")
            sys.exit(1)

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    return options

def opt_validate_refinepeak ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # format

    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # uppercase the format string 
    options.format = options.format.upper()

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    return options

def opt_validate_predictd ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # gsize
    try:
        options.gsize = efgsize[options.gsize]
    except:
        try:
            options.gsize = float(options.gsize)
        except:
            logging.error("Error when interpreting --gsize option: %s" % options.gsize)
            logging.error("Available shortcuts of effective genome sizes are %s" % ",".join(efgsize.keys()))
            sys.exit(1)

    # format
    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BAMPE":
        options.parser = BAMPEParser
        options.gzip_flag = True
        options.nomodel = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # uppercase the format string 
    options.format = options.format.upper()

    # upper and lower mfold
    options.lmfold = options.mfold[0]
    options.umfold = options.mfold[1]
    if options.lmfold > options.umfold:
        logging.error("Upper limit of mfold should be greater than lower limit!" % options.mfold)
        sys.exit(1)
    
    options.modelR  = os.path.join( options.outdir, options.rfile )

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    return options


def opt_validate_pileup ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # format

    options.gzip_flag = False           # if the input is gzip file
    
    options.format = options.format.upper()
    if options.format == "ELAND":
        options.parser = ELANDResultParser
    elif options.format == "BED":
        options.parser = BEDParser
    elif options.format == "ELANDMULTI":
        options.parser = ELANDMultiParser
    elif options.format == "ELANDEXPORT":
        options.parser = ELANDExportParser
    elif options.format == "SAM":
        options.parser = SAMParser
    elif options.format == "BAM":
        options.parser = BAMParser
        options.gzip_flag = True
    elif options.format == "BOWTIE":
        options.parser = BowtieParser
    elif options.format == "AUTO":
        options.parser = guess_parser
    else:
        logging.error("Format \"%s\" cannot be recognized!" % (options.format))
        sys.exit(1)
    
    # uppercase the format string 
    options.format = options.format.upper()

    # logging object
    logging.basicConfig(level=(4-options.verbose)*10,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    # extsize
    if options.extsize <= 0 :
        logging.error("--extsize must > 0!")
        sys.exit(1)

    return options

def opt_validate_bdgcmp ( options ):
    """Validate options from a OptParser object.

    Ret: Validated options object.
    """
    # logging object
    logging.basicConfig(level=20,
                        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        stream=sys.stderr,
                        filemode="w"
                        )
    
    options.error   = logging.critical        # function alias
    options.warn    = logging.warning
    options.debug   = logging.debug
    options.info    = logging.info

    # methods should be valid:

    for method in set(options.method):
        if method not in [ 'ppois', 'qpois', 'subtract', 'logFE', 'FE', 'logLR', 'slogLR' ]:
            logging.error( "Invalid method: %s" % method )
            sys.exit( 1 )

    # # of --ofile must == # of -m

    if options.ofile:
        if len(options.method) != len(options.ofile):
            logging.error("The number and the order of arguments for --ofile must be the same as for -m.")
            sys.exit(1)     

    return options


########NEW FILE########
__FILENAME__ = OutputWriter
# Time-stamp: <2012-10-02 17:14:25 Tao Liu>

"""Module Description

Copyright (c) 2008,2009,2010,2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------
import os
import sys
from array import array
from MACS2.Constants import *

# ------------------------------------
# constants
# ------------------------------------
# to determine the byte size
if array('h',[1]).itemsize == 2:
    BYTE2 = 'h'
else:
    raise Exception("BYTE2 type cannot be determined!")
if array('i',[1]).itemsize == 4:
    BYTE4 = 'i'
elif array('l',[1]).itemsize == 4:
    BYTE4 = 'l'
else:
    raise Exception("BYTE4 type cannot be determined!")

if array('f',[1]).itemsize == 4:
    FBYTE4 = 'f'
elif array('d',[1]).itemsize == 4:
    FBYTE4 = 'd'
else:
    raise Exception("FBYTE4 type cannot be determined!")

# ------------------------------------
# Misc functions
# ------------------------------------
def zwig_write (trackI, subdir, fileprefix, d, log=None,space=10, single=False):
    """Write shifted tags information in wiggle file in a given
    step. Then compress it using 'gzip' program.

    trackI: shifted tags from PeakDetect object
    subdir: directory where to put the wiggle file
    fileprefix: wiggle file prefix
    d     : d length
    log   : logging function, default is sys.stderr.write
    space : space to write tag number on spots, default 10
    """
    if not log:
        log = lambda x: sys.stderr.write(x+"\n")
    chrs = trackI.get_chr_names()
    os.makedirs (subdir)
    step = 10000000 + 2*d

    if single:
        log("write to a wiggle file")
        f = os.path.join(subdir,fileprefix+"_all"+".wig")
        wigfhd = open(f,"w")
        wigfhd.write("track type=wiggle_0 name=\"%s_all\" description=\"Extended tag pileup from MACS version %s for every %d bp\"\n" % (fileprefix.replace('_afterfiting',''), MACS_VERSION, space)) # data type line        
    
    for chrom in chrs:
        if not single:
            f = os.path.join(subdir,fileprefix+"_"+chrom+".wig")
            log("write to "+f+" for chromosome "+chrom)
            wigfhd = open(f,"w")
            # suggested by dawe
            wigfhd.write("track type=wiggle_0 name=\"%s_%s\" description=\"Extended tag pileup from MACS version %s for every %d bp\"\n" % ( fileprefix.replace('_afterfiting',''), chrom, MACS_VERSION, space)) # data type line
        else:
            log("write data for chromosome "+chrom)
            
        wigfhd.write("variableStep chrom=%s span=%d\n" % (chrom,space))
        tags = trackI.get_locations_by_chr(chrom)[0]
        l = len(tags)
        window_counts = array(BYTE4,[0]*step)
        startp = -1*d
        endp   = startp+step
        index_tag = 0
		
        while index_tag<l:
            s = tags[index_tag]-d/2     # start of tag
            e = s+d                     # end of tag
            
            if e < endp:
                # project tag to window_counts line
                ps = s-startp # projection start
                pe = ps+d     # projection end
                for i in xrange(ps,pe):
                    window_counts[i] += 1
                index_tag += 1
            else:
                # write it to zwig file then reset parameters
                # keep this tag for next window
                for i in xrange(d,step-d,space):
                    if window_counts[i] == 0:
                        pass
                    else:
                        wigfhd.write("%d\t%d\n" % (i+startp+1,window_counts[i]))
                # reset
                window_counts_next = array(BYTE4,[0]*step)
                # copy d values from the tail of previous window to next window
                for n,i in enumerate(xrange(step-2*d,step)): # debug
                    window_counts_next[n] = window_counts[i]
                window_counts = window_counts_next
                startp = endp - 2*d
                endp = startp+step
        # last window
        for i in xrange(d,step-d,space):
            if window_counts[i] == 0:
                pass
            else:
                wigfhd.write("%d\t%d\n" % (i+startp+1,window_counts[i]))
        if not single:
            wigfhd.close()
            log("compress the wiggle file using gzip...")
            os.system("gzip "+f)
    if single:
        wigfhd.close()
        log("compress the wiggle file using gzip...")
        os.system("gzip "+f)


def zbdg_write (trackI, subdir, fileprefix, d, log=None, single=False):
    """Write shifted tags information in wiggle file in a given
    step. Then compress it using 'gzip' program.

    trackI: shifted tags from PeakDetect object
    subdir: directory where to put the wiggle file
    fileprefix: wiggle file prefix
    d     : d length
    log   : logging function, default is sys.stderr.write
    space : space to write tag number on spots, default 10
    """
    if not log:
        log = lambda x: sys.stderr.write(x+"\n")
    chrs = trackI.get_chr_names()
    os.makedirs (subdir)
    step = 10000000 + 2*d

    if single:
        log("write to a bedGraph file")
        f = os.path.join(subdir,fileprefix+"_all"+".bdg")
        bdgfhd = open(f,"w")
        bdgfhd.write("track type=bedGraph name=\"%s_all\" description=\"Extended tag pileup from MACS version %s\"\n" % (fileprefix.replace('_afterfiting',''), MACS_VERSION)) # data type line        
    
    for chrom in chrs:
        if not single:
            f = os.path.join(subdir,fileprefix+"_"+chrom+".bdg")
            log("write to "+f+" for chromosome "+chrom)
            bdgfhd = open(f,"w")
            bdgfhd.write("track type=bedGraph name=\"%s_%s\" description=\"Extended tag pileup from MACS version %s\"\n" % (fileprefix.replace('_afterfiting',''), chrom, MACS_VERSION)) # data type line
        else:
            log("write data for chromosome "+chrom)
            
        tags = trackI.get_locations_by_chr(chrom)[0]
        l = len(tags)
        window_counts = array(BYTE4,[0]*step)
        startp = -1*d
        endp   = startp+step
        index_tag = 0
		
        while index_tag<l:
            s = tags[index_tag]-d/2     # start of tag
            e = s+d                     # end of tag
            
            if e < endp:
                # project tag to window_counts line
                ps = s-startp # projection start
                pe = ps+d     # projection end
                for i in xrange(ps,pe):
                    window_counts[i] += 1
                index_tag += 1
            else:
                # write it to zbdg file then reset parameters
                # keep this tag for next window
                prev = window_counts[d]
                left = startp+d
                right = left+1
                for i in xrange(d+1,step-d):
                    if window_counts[i] == prev:
                        # same value, extend
                        right += 1
                    else:
                        # diff value, close
                        if prev != 0:
                            bdgfhd.write("%s\t%d\t%d\t%d\n" % (chrom,left,right,prev))
                        prev = window_counts[i]
                        left = right
                        right = left + 1
                # last bin
                if prev != 0:                
                    bdgfhd.write("%s\t%d\t%d\t%d\n" % (chrom,left,right,prev))
                    
                # reset
                window_counts_next = array(BYTE4,[0]*step)
                # copy d values from the tail of previous window to next window
                for n,i in enumerate(xrange(step-2*d,step)): # debug
                    window_counts_next[n] = window_counts[i]
                window_counts = window_counts_next
                startp = endp - 2*d
                endp = startp+step
        # last window
        prev = window_counts[d]
        left = startp+d
        right = left+1
        for i in xrange(d+1,step-d):
            if window_counts[i] == prev:
                # same value, exrend
                right += 1
            else:
                # diff value, close
                if prev != 0:                
                    bdgfhd.write("%s\t%d\t%d\t%d\n" % (chrom,left,right,prev))
                prev = window_counts[i]
                left = right
                right = left + 1
        # last bin
        if prev != 0:        
            bdgfhd.write("%s\t%d\t%d\t%d\n" % (chrom,left,right,prev))
            
        if not single:
            bdgfhd.close()
            log("compress the bedGraph file using gzip...")
            os.system("gzip "+f)
    if single:
        bdgfhd.close()
        log("compress the bedGraph file using gzip...")
        os.system("gzip "+f)


def model2r_script(model,filename,name):
    rfhd = open(filename,"w")
    p = model.plus_line
    m = model.minus_line
    ycorr = model.ycorr
    xcorr = model.xcorr
    alt_d = model.alternative_d
    #s = model.shifted_line
    d = model.d
    w = len(p)
    norm_p = [0]*w
    norm_m = [0]*w
    #norm_s = [0]*w
    sum_p = sum(p)
    sum_m = sum(m)
    #sum_s = sum(s)
    for i in range(w):
        norm_p[i] = float(p[i])*100/sum_p
        norm_m[i] = float(m[i])*100/sum_m
        #norm_s[i] = float(s[i])*100/sum_s
    rfhd.write("# R script for Peak Model\n")
    rfhd.write("#  -- generated by MACS\n")

    rfhd.write("""p <- c(%s)
m <- c(%s)
ycorr <- c(%s)
xcorr <- c(%s)
altd  <- c(%s)
x <- seq.int((length(p)-1)/2*-1,(length(p)-1)/2)
pdf('%s_model.pdf',height=6,width=6)
plot(x,p,type='l',col=c('red'),main='Peak Model',xlab='Distance to the middle',ylab='Percentage')
lines(x,m,col=c('blue'))
legend('topleft',c('forward tags','reverse tags'),lty=c(1,1,1),col=c('red','blue'))
plot(xcorr,ycorr,type='l',col=c('black'),main='Cross-Correlation',xlab='Lag between + and - tags',ylab='Correlation')
abline(v=altd,lty=2,col=c('red'))
legend('topleft','alternative lag(s)',lty=2,col='red')
legend('right','alt lag(s) : %s',bty='n')
dev.off()
""" % (','.join(map(str,norm_p)),
       ','.join(map(str,norm_m)),
       ','.join(map(str,ycorr)),
       ','.join(map(str,xcorr)),
       ', '.join(map(str,alt_d)),
       name,
       ','.join(map(str,alt_d))
       ))
    rfhd.close()

def diag_write (filename, diag_result):
    ofhd_diag = open(filename,"w")
    a = diag_result[0]
    l = len(a)-2
    s = [90-x*10 for x in range(l)]
    ofhd_diag.write("FC range\t# of Peaks\tcover by sampling %s\n" % ("%\t".join (map(str,s))+"%"))
    format = "%s\t%d"+"\t%.2f"*l+"\n"
    ofhd_diag.write( "".join( [format % tuple(x) for x in diag_result])  )
    ofhd_diag.close()

# ------------------------------------
# Classes
# ------------------------------------

########NEW FILE########
__FILENAME__ = pileup
# Time-stamp: <2013-10-28 01:35:22 Tao Liu>

"""Description: Filter duplicate reads depending on sequencing depth.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate_pileup as opt_validate
from MACS2.OutputWriter import *
from MACS2.cPileup import unified_pileup_bdg   
from MACS2.Constants import *
# ------------------------------------
# Main function
# ------------------------------------
def run( o_options ):
    """The Main function/pipeline for duplication filter.
    
    """
    # Parse options...
    options = opt_validate( o_options )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error
    #0 output arguments
    assert options.format != 'BAMPE', "Pair-end data with BAMPE option currently doesn't work with pileup command. You can pretend your data to be single-end with -f BAM. Please try again!"

    #0 prepare output file
    if options.outputfile != "stdout":
        outfhd = open( os.path.join( options.outdir, options.outputfile ), "w" )
    else:
        outfhd = sys.stdout
    
    #1 Read tag files
    info("# read alignment files...")
    (tsize, treat) = load_tag_files_options  (options)
    
    info("# tag size = %d", tsize)
    
    t0 = treat.total
    info("# total tags in alignment file: %d", t0)

    if options.bothdirection:
        info("# Pileup alignment file, extend each read towards up/downstream direction with %d bps" % options.extsize)        
        treat_btrack = unified_pileup_bdg(treat, options.extsize * 2, 1, directional=False, halfextension=False)
        info("# save bedGraph to %s" % options.outputfile)
        treat_btrack.write_bedGraph( outfhd, "Pileup", "Pileup track with extsize %d on both directions" % options.extsize, trackline=False )
    else:
        info("# Pileup alignment file, extend each read towards downstream direction with %d bps" % options.extsize)
        treat_btrack = unified_pileup_bdg(treat, options.extsize, 1, directional=True, halfextension=False)
        info("# save bedGraph to %s" % options.outputfile)
        treat_btrack.write_bedGraph( outfhd, "Pileup", "Pileup track with extsize %d on 5' directions" % options.extsize, trackline=False )

    info("# Done! Check %s" % options.outputfile)

def load_tag_files_options ( options ):
    """From the options, load alignment tags.

    """
    options.info("# read treatment tags...")
    tp = options.parser(options.ifile[0])
    tsize = tp.tsize()
    treat = tp.build_fwtrack()
    treat.sort()
    if len(options.ifile) > 1:
        # multiple input
        for tfile in options.ifile[1:]:
            tp = options.parser(tfile)
            treat = tp.append_fwtrack( treat )
            treat.sort()

    options.info("tag size is determined as %d bps" % tsize)
    return (tsize, treat)


########NEW FILE########
__FILENAME__ = predictd
# Time-stamp: <2013-10-28 01:31:46 Tao Liu>

"""Description: Filter duplicate reads depending on sequencing depth.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate_predictd as opt_validate
from MACS2.OutputWriter import *
from MACS2.cPeakModel import PeakModel,NotEnoughPairsException
from MACS2.cProb import binomial_cdf_inv
from MACS2.Constants import *
# ------------------------------------
# Main function
# ------------------------------------
def run( o_options ):
    """The Main function/pipeline for duplication filter.
    
    """
    # Parse options...
    options = opt_validate( o_options )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error
    #0 output arguments
    assert options.format != 'BAMPE', "Pair-end data with BAMPE option doesn't work with predictd command. You can pretend your data to be single-end with -f BAM. Please try again!"
    
    #1 Read tag files
    info("# read alignment files...")
    treat = load_tag_files_options  (options)
    
    info("# tag size = %d", options.tsize)
    
    t0 = treat.total
    info("# total tags in alignment file: %d", t0)

    #2 Build Model
    info("# Build Peak Model...")

    try:
        peakmodel = PeakModel(treatment = treat,
                              max_pairnum = MAX_PAIRNUM,
                              opt = options
                              )
        info("# finished!")
        debug("#  Summary Model:")
        debug("#   min_tags: %d" % (peakmodel.min_tags))
        debug("#   d: %d" % (peakmodel.d))
        info("# predicted fragment length is %d bps" % peakmodel.d)
        info("# alternative fragment length(s) may be %s bps" % ','.join(map(str,peakmodel.alternative_d)))
        info("# Generate R script for model : %s" % (options.modelR))
        model2r_script(peakmodel,options.modelR, options.rfile )
        options.d = peakmodel.d

    except NotEnoughPairsException:
        warn("# Can't find enough pairs of symmetric peaks to build model!")

def load_tag_files_options ( options ):
    """From the options, load alignment tags.

    """
    options.info("# read treatment tags...")
    tp = options.parser(options.ifile[0])
    if not options.tsize:           # override tsize if user specified --tsize
        ttsize = tp.tsize()
        options.tsize = ttsize
    treat = tp.build_fwtrack()
    treat.sort()
    if len(options.ifile) > 1:
        # multiple input
        for tfile in options.ifile[1:]:
            tp = options.parser(tfile)
            treat = tp.append_fwtrack( treat )
            treat.sort()

    options.info("tag size is determined as %d bps" % options.tsize)
    return treat


########NEW FILE########
__FILENAME__ = randsample
# Time-stamp: <2013-10-28 01:40:58 Tao Liu>

"""Description: Random sample certain number/percentage of tags.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate_randsample as opt_validate
from MACS2.Constants import *

# ------------------------------------
# Main function
# ------------------------------------
def run( options0 ):
    options = opt_validate( options0 )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error
    #0 check output file
    if options.outputfile:
        outfhd = open( os.path.join( options.outdir, options.outputfile ), "w" )
    else:
        outfhd = sys.stdout
    
    #1 Read tag files
    info("read tag files...")
    fwtrack = load_tag_files_options (options)
    
    info("tag size = %d" % options.tsize)
    fwtrack.fw = options.tsize

    t0 = fwtrack.total
    info(" total tags in alignment file: %d" % (t0))
    if options.number:
        if options.number > t0:
            error(" Number you want is bigger than total number of tags in alignment file! Please specify a smaller number and try again!")
            error(" %.2e > %.2e" % (options.number, t0))
            sys.exit(1)
        info(" Number of tags you want to keep: %.2e" % (options.number))
        options.percentage = float(options.number)/t0*100
    info(" Percentage of tags you want to keep: %.2f%%" % (options.percentage))

    if options.seed >= 0:
        info(" Random seed has been set as: %d" % options.seed )

    fwtrack.sample_percent(options.percentage/100.0, options.seed )

    info(" tags after random sampling in alignment file: %d" % (fwtrack.total))

    info("Write to BED file")
    fwtrack.print_to_bed(fhd=outfhd)
    info("finished! Check %s." % options.outputfile)

def load_tag_files_options ( options ):
    """From the options, load alignment tags.

    """
    options.info("read alignment tags...")
    tp = options.parser(options.tfile)

    if not options.tsize:           # override tsize if user specified --tsize
        ttsize = tp.tsize()
        options.tsize = ttsize

    treat = tp.build_fwtrack()
    treat.sort()

    options.info("tag size is determined as %d bps" % options.tsize)
    return treat


########NEW FILE########
__FILENAME__ = refinepeak
# Time-stamp: <2013-10-28 01:48:32 Tao Liu>

"""Description: Filter duplicate reads depending on sequencing depth.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included
with the distribution).

@status: release candidate
@version: $Id$
@author:  Yong Zhang, Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""

# ------------------------------------
# python modules
# ------------------------------------

import os
import sys
import logging
from collections import Counter

# ------------------------------------
# own python modules
# ------------------------------------
from MACS2.OptValidator import opt_validate_refinepeak as opt_validate
from MACS2.cProb import binomial_cdf_inv
from MACS2.IO.cBedGraphIO import bedGraphIO,genericBedIO
from MACS2.IO.cPeakIO import PeakIO
from MACS2.Constants import *


# ------------------------------------
# Main function
# ------------------------------------
def run( o_options ):
    """The Main function/pipeline for duplication filter.
    
    """
    # Parse options...
    options = opt_validate( o_options )
    # end of parsing commandline options
    info = options.info
    warn = options.warn
    debug = options.debug
    error = options.error

    if options.ofile:
        outputfile = open( os.path.join( options.outdir, options.ofile ), 'w' )
        options.oprefix = options.ofile
    else:
        outputfile = open( os.path.join( options.outdir, "%s_refinepeak.bed" % options.oprefix), "w" )


    peakio = file(options.bedfile)
    peaks = PeakIO()
    for l in peakio:
        fs = l.rstrip().split()
        peaks.add( fs[0], int(fs[1]), int(fs[2]), name=fs[3] )

    peaks.sort()
    
    #1 Read tag files
    info("read tag files...")
    fwtrack = load_tag_files_options (options)
    
    retval = fwtrack.compute_region_tags_from_peaks( peaks, find_summit, window_size = options.windowsize, cutoff = options.cutoff )
    outputfile.write( "\n".join( map(lambda x: "%s\t%d\t%d\t%s\t%.2f" % x , retval) ) )
    info("Done!")
    info("Check output file: %s" % options.oprefix+"_refinepeak.bed")

def find_summit(chrom, plus, minus, peak_start, peak_end, name = "peak", window_size=100, cutoff = 5):
    
    left_sum = lambda strand, pos, width = window_size: sum([strand[x] for x in strand if x <= pos and x >= pos - width])
    right_sum = lambda strand, pos, width = window_size: sum([strand[x] for x in strand if x >= pos and x <= pos + width])
    left_forward = lambda strand, pos: strand.get(pos,0) - strand.get(pos-window_size, 0)
    right_forward = lambda strand, pos: strand.get(pos + window_size, 0) - strand.get(pos, 0)

    watson, crick = (Counter(plus), Counter(minus))
    watson_left = left_sum(watson, peak_start)
    crick_left = left_sum(crick, peak_start)
    watson_right = right_sum(watson, peak_start)
    crick_right = right_sum(crick, peak_start)

    wtd_list = []
    for j in range(peak_start, peak_end+1):
        wtd_list.append(2 * (watson_left * crick_right)**0.5 - watson_right - crick_left)
        watson_left += left_forward(watson, j)
        watson_right += right_forward(watson, j)
        crick_left += left_forward(crick, j)
        crick_right += right_forward(crick,j)

    wtd_max_val = max(wtd_list)
    wtd_max_pos = wtd_list.index(wtd_max_val) + peak_start

    #return (chrom, wtd_max_pos, wtd_max_pos+1, wtd_max_val)

    if wtd_max_val > cutoff:
        return (chrom, wtd_max_pos, wtd_max_pos+1, name+"_R" , wtd_max_val) # 'R'efined
    else:
        return (chrom, wtd_max_pos, wtd_max_pos+1, name+"_F" , wtd_max_val) # 'F'ailed

    #return "{}\t{}\t{}\tRefinePeak_summit\t{:.2f}\n".format(chrom,
    #                                                        wtd_max_pos,
    #                                                        wtd_max_pos+1,
    #                                                        wtd_max_val,)



# def find_summit(bed_file, sam_file, window_size, output_file):
#     def count_by_strand(ialign):
#         pred = lambda x:x.is_reverse
#         watson_5_end = lambda x:x.pos
#         crick_5_end = lambda x:x.aend
#         ialign1, ialign2 = tee(ialign)

#         return (Counter(map(watson_5_end,
#                             ifilterfalse(pred, ialign1))),
#                 Counter(map(crick_5_end,
#                             ifilter(pred, ialign2))))
    
#     left_sum = lambda strand, pos, width = window_size: sum([strand[x] for x in strand if x <= pos and x >= pos - width])
#     right_sum = lambda strand, pos, width = window_size: sum([strand[x] for x in strand if x >= pos and x <= pos + width])
#     left_forward = lambda strand, pos: strand.get(pos,0) - strand.get(pos-window_size, 0)
#     right_forward = lambda strand, pos: strand.get(pos + window_size, 0) - strand.get(pos, 0)
#     samfile = pysam.Samfile(sam_file, "rb" )

#     cnt = 0
#     with open(bed_file) as bfile, open(output_file,"w") as ofile:
#         for i in bfile:
#             i = i.split("\t")
#             chrom = i[0]
#             peak_start = int(i[1])
#             peak_end = int(i[2])
            
#             watson, crick = count_by_strand(samfile.fetch(chrom, peak_start-window_size, peak_end+window_size))
#             watson_left = left_sum(watson, peak_start)
#             crick_left = left_sum(crick, peak_start)
#             watson_right = right_sum(watson, peak_start)
#             crick_right = right_sum(crick, peak_start)

#             wtd_list = []
#             for j in range(peak_start, peak_end+1):
#                 wtd_list.append(2 * sqrt(watson_left * crick_right) - watson_right - crick_left)
#                 watson_left += left_forward(watson, j)
#                 watson_right += right_forward(watson, j)
#                 crick_left += left_forward(crick, j)
#                 crick_right += right_forward(crick,j)

#             wtd_max_val = max(wtd_list)
#             wtd_max_pos = wtd_list.index(wtd_max_val) + peak_start
#             cnt += 1

#             ofile.write("{}\t{}\t{}\tSPP_summit_{}\t{:.2f}\n".format(chrom,
#                                                                      wtd_max_pos,
#                                                                      wtd_max_pos+1,
#                                                                      cnt,
#                                                                      wtd_max_val,))
#     samfile.close()




def load_tag_files_options ( options ):
    """From the options, load alignment tags.

    """
    options.info("read alignment tags...")
    tp = options.parser(options.ifile)

    ttsize = tp.tsize()
    options.tsize = ttsize

    treat = tp.build_fwtrack()
    treat.sort()

    options.info("tag size is determined as %d bps" % options.tsize)
    return treat


########NEW FILE########
__FILENAME__ = test_callsummits
#!/usr/bin/env python
# Time-stamp: <2013-10-18 16:27:40 Tao Liu>

import os
import sys
import unittest

from MACS2.IO.cCallPeakUnit import *
import numpy as np
from MACS2.IO.cPeakIO import PeakIO
from math import factorial
from random import normalvariate

class Test_CallSummits ( unittest.TestCase ):
    
    def setUp( self ):
        self.range             = [   0, 2000 ]
        self.binding_sites     = [ 300, 500, 700 ]
        self.binding_strength  = [ 60,  45,  55 ] # approximate binding affility 
        self.binding_width     = [ 150, 150, 150 ]# binding width, left and right sides are cutting sites
        self.cutting_variation = 50              # variation at the correct cutting sites
        self.tag_size          = 50
        self.test_tags_file    = "random_test.bed"
        self.genome_size       = 10000
        
        self.plus_tags         = [ ]
        self.minus_tags        = [ ]
        
        for i in range( len(self.binding_sites) ):
            j = 0
            while j <= self.binding_strength[ i ]:
                x = int( normalvariate( self.binding_sites[ i ] - self.binding_width[ i ]/2,
                                        self.cutting_variation ) )
                if x > self.range[ 0 ] and x + self.tag_size < self.range[ 1 ]:
                    self.plus_tags.append( x )
                    j += 1
            
            j = 0
            while j <= self.binding_strength[ i ]:
                x = int( normalvariate( self.binding_sites[ i ] + self.binding_width[ i ]/2,
                                        self.cutting_variation ) )
                if x - self.tag_size > self.range[ 0 ] and x < self.range[ 1 ]:
                    self.minus_tags.append( x )
                    j += 1

        self.plus_tags = sorted(self.plus_tags)
        self.minus_tags = sorted(self.minus_tags)

        #print self.plus_tags
        #print self.minus_tags

        self.result_peak = PeakIO()

        # write reads in bed files
        fhd = open( self.test_tags_file, "w" )
        for x in self.plus_tags:
            fhd.write( "chr1\t%d\t%d\t.\t0\t+\n" % ( x, x + self.tag_size ) )
        for x in self.minus_tags:
            fhd.write( "chr1\t%d\t%d\t.\t0\t-\n" % ( x - self.tag_size, x ) )

    def test_pileup ( self ):
        pass


    # def test_wo_subpeak ( self ):
    #     peak_content = self.test_peak_content
    #     tsummit = []
    #     summit_pos   = 0
    #     summit_value = 0
    #     for i in range(len(peak_content)):
    #         (tstart, tend, ttreat_p, tctrl_p, tlist_scores_p) = peak_content[i]
    #         tscore = ttreat_p #self.pqtable[ get_pscore(int(ttreat_p), tctrl_p) ] # use qscore as general score to find summit
    #         if not summit_value or summit_value < tscore:
    #             tsummit = [(tend + tstart) / 2, ]
    #             tsummit_index = [ i, ]
    #             summit_value = tscore
    #         elif summit_value == tscore:
    #             # remember continuous summit values
    #             tsummit.append(int((tend + tstart) / 2))
    #             tsummit_index.append( i )
    #     # the middle of all highest points in peak region is defined as summit
    #     print "wo, all:",tsummit
    #     midindex = int((len(tsummit) + 1) / 2) - 1
    #     summit_pos    = tsummit[ midindex ]
    #     summit_index  = tsummit_index[ midindex ]
    #     print "wo:",summit_pos

    # def test_w_subpeak ( self ):
    #     peak_content = self.test_peak_content

    #     smoothlen = 20

    #     peak_length = peak_content[ -1 ][ 1 ] - peak_content[ 0 ][ 0 ]
            
    #     # Add 10 bp padding to peak region so that we can get true minima
    #     end = peak_content[ -1 ][ 1 ] + 10
    #     start = peak_content[ 0 ][ 0 ] - 10
    #     if start < 0:
    #         start_boundary = 5 + start # this is the offset of original peak boundary in peakdata list.
    #         start = 0
    #     else:
    #         start_boundary = 5 # this is the offset of original peak boundary in peakdata list.

    #     peakdata = np.zeros(end - start, dtype='float32') # save the scores (qscore) for each position in this region
    #     peakindices = np.zeros(end - start, dtype='int32') # save the indices for each position in this region
    #     for i in range(len(peak_content)):
    #         (tstart, tend, ttreat_p, tctrl_p, tlist_scores_p) = peak_content[i]
    #         #tscore = self.pqtable[ get_pscore(int(ttreat_p), tctrl_p) ] # use qscore as general score to find summit
    #         tscore = ttreat_p # use pileup as general score to find summit
    #         m = tstart - start + start_boundary
    #         n = tend - start + start_boundary
    #         peakdata[m:n] = tscore
    #         peakindices[m:n] = i

    #     np.set_printoptions(precision=1, suppress=True)
    #     #print "before smoothed data:", len(peakdata), peakdata
    #     print "maximum points:", np.where(peakdata == peakdata.max())
    #     summit_offsets = maxima(peakdata, smoothlen) # offsets are the indices for summits in peakdata/peakindices array.
    #     print "summit_offsets:", summit_offsets

    #     m = np.searchsorted(summit_offsets, start_boundary)
    #     n = np.searchsorted(summit_offsets, peak_length + start_boundary, 'right')
    #     summit_offsets = summit_offsets[m:n]
    #     print "summit_offsets adjusted:", summit_offsets        
        
    #     summit_offsets = enforce_peakyness(peakdata, summit_offsets)
    #     print "summit_offsets enforced:", summit_offsets        
        
    #     summit_indices = peakindices[summit_offsets] # indices are those point to peak_content
    #     summit_offsets -= start_boundary
    #     print "summit_offsets final:", summit_offsets        

    #     for summit_offset, summit_index in zip(summit_offsets, summit_indices):
    #         print "w:",start+summit_offset

def maxima ( signal, window_size=51 ):
    """return the local maxima in a signal after applying a 2nd order
    Savitsky-Golay (polynomial) filter using window_size specified  
    """
    #data1 = savitzky_golay(signal, window_size, order=2, deriv=1)
    #data2 = savitzky_golay(signal, window_size, order=2, deriv=2)
    #m = np.where(np.diff(np.sign( data1 )) <= -1)[0].astype('int32')

    #data1 = savitzky_golay_order2(signal, window_size, deriv=1)
    data1 = savitzky_golay(signal, window_size, order=2, deriv=1)
    m = np.where( np.diff( np.sign( data1 ) ) <= -1)[0].astype('int32')
    #m = np.where( np.logical_and( data2 < 0 , abs(data1) <= 1e-10) ) [0].astype('int32')
    return m


def savitzky_golay_order2(signal, window_size, deriv=0):
    """Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techhniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.

    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    if window_size % 2 != 1: window_size += 1
    half_window = (window_size - 1) / 2
    # precompute coefficients
    b = np.mat([[1, k, k**2] for k in range(-half_window, half_window+1)],
               dtype='int64')
    m = np.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = signal[0] - np.abs(signal[1:half_window+1][::-1] - signal[0])
    lastvals = signal[-1] + np.abs(signal[-half_window-1:-1][::-1] - signal[-1])
    signal = np.concatenate((firstvals, signal, lastvals))
    ret = np.convolve( m, signal.astype('float64'), mode='valid').astype('float32')
    return ret

def savitzky_golay(y, window_size, order=2, deriv=0, rate=1):

    if window_size % 2 != 1: window_size += 1

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m[::-1], y, mode='valid')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cBedGraph
#!/usr/bin/env python
# Time-stamp: <2012-03-10 20:55:11 Tao Liu>

import os
import sys
import unittest

from MACS2.IO.cBedGraph import *

class Test_bedGraphTrackI_add_loc(unittest.TestCase):

    def setUp(self):
        self.test_regions1 = [("chrY",0,10593155,0.0),
                              ("chrY",10593155,10597655,0.0066254580149)]

    def test_add_loc1(self):
        # make sure the shuffled sequence does not lose any elements
        bdg = bedGraphTrackI()
        for a  in self.test_regions1:
            bdg.add_loc(a[0],a[1],a[2],a[3])

        #self.assertTrue( abs(result - expect) < 1e-5*result)

        #self.assertEqual(result, expect)

        #self.assertEqual(result, expect)

class Test_bedGraphTrackI_overlie(unittest.TestCase):

    def setUp(self):
        self.test_cslregions1 = [("chrY",0,70,0.00),
                              ("chrY",70,80,0.07),
                              ("chrY",80,150,0.00),
                              ("chrY",150,160,0.07),
                              ("chrY",160,190,0.00)]
        self.test_cdregions2 = [("chrY",0,85,0.00),
                             ("chrY",85,90,0.75),
                             ("chrY",90,155,0.00),
                             ("chrY",155,165,0.75),
                             ("chrY",165,200,0.00)]
        self.test_overlie_result = [("chrY",0,70,0.0),
                                    ("chrY",70,80,0.07),
                                    ("chrY",80,85,0.0),
                                    ("chrY",85,90,0.75),
                                    ("chrY",90,150,0.0),
                                    ("chrY",150,155,0.07),
                                    ("chrY",155,165,0.75),
                                    ("chrY",165,190,0.0)]

    def assertEqual_float ( self, a, b, roundn = 5 ):
        self.assertEqual( round( a, roundn ), round( b, roundn ) )

    def test_overlie(self):
        bdg1 = bedGraphTrackI()
        bdg2 = bedGraphTrackI()
        for a in self.test_cslregions1:
            bdg1.safe_add_loc(a[0],a[1],a[2],a[3])

        for a in self.test_cdregions2:
            bdg2.safe_add_loc(a[0],a[1],a[2],a[3])

        bdgb = bdg1.overlie(bdg2)

        chrom = "chrY"
        (p,v) = bdgb.get_data_by_chr(chrom)
        pre = 0
        for i in xrange(len(p)):
            pos = p[i]
            value = v[i]
            self.assertEqual_float( self.test_overlie_result[i][1], pre )
            self.assertEqual_float( self.test_overlie_result[i][2], pos )
            self.assertEqual_float( self.test_overlie_result[i][3], value )            
            pre = pos        


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cFixWidthTrack
#!/usr/bin/env python
# Time-stamp: <2012-05-01 22:09:55 Tao Liu>

import os
import sys
import unittest

from MACS2.IO.cFixWidthTrack import *

class Test_FWTrackIII(unittest.TestCase):

    def setUp(self):

        self.input_regions = [("chrY",0,0 ),
                              ("chrY",90,0 ),
                              ("chrY",150,0 ),
                              ("chrY",70,0 ),
                              ("chrY",80,0 ),
                              ("chrY",85,0 ),
                              ("chrY",85,0 ),
                              ("chrY",85,0 ),
                              ("chrY",85,0 ),                                    
                              ("chrY",90,1 ),
                              ("chrY",150,1 ),
                              ("chrY",70,1 ),
                              ("chrY",80,1 ),
                              ("chrY",80,1 ),
                              ("chrY",80,1 ),
                              ("chrY",85,1 ),
                              ("chrY",90,1 ),                                    
                              ]
        self.fw = 50

    def test_add_loc(self):
        # make sure the shuffled sequence does not lose any elements
        fw = FWTrackIII(fw=self.fw)
        for ( c, p, s ) in self.input_regions:
            fw.add_loc(c, p, s)
        fw.finalize()
        # roughly check the numbers...
        self.assertEqual( fw.total, 17 )         
        self.assertEqual( fw.length(), 17*self.fw )

    def test_filter_dup(self):
        # make sure the shuffled sequence does not lose any elements
        fw = FWTrackIII(fw=self.fw)
        for ( c, p, s ) in self.input_regions:
            fw.add_loc(c, p, s)
        fw.finalize()
        # roughly check the numbers...
        self.assertEqual( fw.total, 17 )      
        self.assertEqual( fw.length(), 17*self.fw )

        # filter out more than 3 tags
        fw2 = fw.filter_dup( 3, keep_original = True )
        # one chrY:85:0 should be removed
        self.assertEqual( fw.total, 17 )
        self.assertEqual( fw2.total, 16 )
        fw = fw2

        # filter out more than 2 tags
        fw2 = fw.filter_dup( 2, keep_original = True )        
        # then, one chrY:85:0 and one chrY:80:- should be removed
        self.assertEqual( fw.total, 16 )
        self.assertEqual( fw2.total, 14 )
        fw = fw2
        
        # filter out more than 1 tag
        fw2 = fw.filter_dup( 1, keep_original = True )
        # then, one chrY:85:0 and one chrY:80:1, one chrY:90:1 should be removed
        self.assertEqual( fw.total, 14 )
        self.assertEqual( fw2.total, 11 )

        # last test for inplace filtering
        fw.filter_dup( 1 )
        self.assertEqual( fw.total, 11 )
        

    def test_sample_num(self):
        # make sure the shuffled sequence does not lose any elements
        fw = FWTrackIII(fw=self.fw)
        for ( c, p, s ) in self.input_regions:
            fw.add_loc(c, p, s)
        fw.finalize()
        # roughly check the numbers...
        self.assertEqual( fw.total, 17 )         
        self.assertEqual( fw.length(), 17*self.fw )        

        fw.sample_num( 10 )
        self.assertEqual( fw.total, 9 )
        
    def test_sample_percent(self):
        # make sure the shuffled sequence does not lose any elements
        fw = FWTrackIII(fw=self.fw)
        for ( c, p, s ) in self.input_regions:
            fw.add_loc(c, p, s)
        fw.finalize()
        # roughly check the numbers...
        self.assertEqual( fw.total, 17 )         
        self.assertEqual( fw.length(), 17*self.fw )        

        fw.sample_percent( 0.5 )
        self.assertEqual( fw.total, 8 )        
        
        #fw.print_to_bed()
        #self.assertTrue( abs(result - expect) < 1e-5*result)

        #self.assertEqual(result, expect)

        #self.assertEqual(result, expect)
        #self.assertEqual_float( result, expect )


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cParser
#!/usr/bin/env python

from MACS2.IO.cParser import BEDParser

#fhd = gzip.open("peakcalling/ChIP_0.1.bam","r")

a_parser = BEDParser("ChIP_0.1.bed.gz")

a = parser.build_fwtrack()

b_parser = BEDParser("Control_0.1.bed.gz")

b = parser.build_fwtrack()


########NEW FILE########
__FILENAME__ = test_cPeakIO_Region
#!/usr/bin/env python
# Time-stamp: <2012-04-29 17:27:36 Tao Liu>

import os
import sys
import unittest

from MACS2.IO.cPeakIO import *

class Test_Region(unittest.TestCase):

    def setUp(self):
        self.test_regions1 = [("chrY",0,100),
                              ("chrY",300,500),
                              ("chrY",700,900),
                              ("chrY",1000,1200),
                              ]
        self.test_regions2 = [("chrY",100,200),
                              ("chrY",300,400),
                              ("chrY",600,800),
                              ("chrY",1200,1300),
                              ]
        self.merge_result_regions = [ ("chrY",0,200),
                                      ("chrY",300,500),
                                      ("chrY",600,900),
                                      ("chrY",1000,1300),
                                      ]
        self.subpeak_n = [1,10,100,1000]



    def test_add_loc1(self):
        # make sure the shuffled sequence does not lose any elements
        self.r1 = Region()
        for a in self.test_regions1:
            self.r1.add_loc(a[0],a[1],a[2])

    def test_add_loc2(self):
        # make sure the shuffled sequence does not lose any elements
        self.r2 = Region()
        for a in self.test_regions2:
            self.r2.add_loc(a[0],a[1],a[2])

    def test_merge(self):
        self.mr = Region()
        for a in self.test_regions1:
            self.mr.add_loc(a[0],a[1],a[2])
        for a in self.test_regions2:
            self.mr.add_loc(a[0],a[1],a[2])            
        self.mr.merge_overlap()
        self.mr.write_to_bed(sys.stdout)

#    def test_subpeak_letters(self):
#        for i in self.subpeak_n:
#            print subpeak_letters(i)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cPileup
#!/usr/bin/env python
# Time-stamp: <2012-04-29 18:25:30 Tao Liu>

"""Module Description: Test functions for pileup functions.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""


import os
import sys
import unittest

from math import log10
from MACS2.cPileup import *
from MACS2.IO.cFixWidthTrack import FWTrackIII

# ------------------------------------
# Main function
# ------------------------------------

class Test_pileup(unittest.TestCase):
    """Unittest for pileup_bdg() in cPileup.pyx.

    """
    def setUp(self):
        self.maxDiff = None
        self.chrom = "chr1"
        self.plus_pos = ( 0, 1, 3, 4, 5 )
        self.minus_pos = ( 5, 6, 8, 9, 10 )
        self.d = 5
        self.scale_factor = 0.5
        self.expect = [ ( 0, 1, 1.0 ),
                        ( 1, 3, 2.0 ),
                        ( 3, 4, 3.0 ),
                        ( 4, 6, 4.0 ),
                        ( 6, 8, 3.0 ),
                        ( 8, 9, 2.0 ),                            
                        ( 9, 10, 1.0 )
                        ]
        self.expect2 = [(0, 1, 13.0),
                        (1, 3, 14.0),
                        (3, 4, 16.0),
                        (4, 6, 18.0),
                        (6, 8, 16.0),
                        (8, 9, 14.0),
                        (9, 10, 13.0)]

        self.d_s = [ 5, 10, 100 ]
        self.scale_factor_s = [ 0.5, 1, 2 ]

    def test_pileup(self):
        # build FWTrackII
        self.fwtrack2 = FWTrackIII()
        for i in self.plus_pos:
            self.fwtrack2.add_loc(self.chrom, i, 0)
        for i in self.minus_pos:
            self.fwtrack2.add_loc(self.chrom, i, 1)            
        self.fwtrack2.finalize()
        
        self.pileup = pileup_bdg(self.fwtrack2, self.d, halfextension=False, scale_factor = self.scale_factor)
        self.result = []
        chrs = self.pileup.get_chr_names()
        for chrom in chrs:
            (p,v) = self.pileup.get_data_by_chr(chrom)
            pnext = iter(p).next
            vnext = iter(v).next
            pre = 0
            for i in xrange(len(p)):
                pos = pnext()
                value = vnext()
                self.result.append( (pre,pos,value) )
                pre = pos
        # check result
        self.assertEqual(self.result, self.expect)

    def test_pileup_w_multiple_d_bdg ( self ):
        # build FWTrackII
        self.fwtrack2 = FWTrackIII(fw=5)
        for i in self.plus_pos:
            self.fwtrack2.add_loc(self.chrom, i, 0)
        for i in self.minus_pos:
            self.fwtrack2.add_loc(self.chrom, i, 1)            
        self.fwtrack2.finalize()
        # pileup test
        self.pileup = pileup_w_multiple_d_bdg(self.fwtrack2, self.d_s, baseline_value=13, halfextension=False, scale_factor_s = self.scale_factor_s)
        self.result = []
        chrs = self.pileup.get_chr_names()
        for chrom in chrs:
            (p,v) = self.pileup.get_data_by_chr(chrom)
            pnext = iter(p).next
            vnext = iter(v).next
            pre = 0
            for i in xrange(len(p)):
                pos = pnext()
                value = vnext()
                self.result.append( (pre,pos,value) )
                pre = pos
        # check result
        self.assertEqual(self.result, self.expect2)
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cProb
#!/usr/bin/env python
# Time-stamp: <2012-03-09 09:50:12 Tao Liu>

"""Module Description: Test functions to calculate probabilities.

Copyright (c) 2011 Tao Liu <taoliu@jimmy.harvard.edu>

This code is free software; you can redistribute it and/or modify it
under the terms of the BSD License (see the file COPYING included with
the distribution).

@status:  experimental
@version: $Revision$
@author:  Tao Liu
@contact: taoliu@jimmy.harvard.edu
"""


import os
import sys
import unittest

from math import log10
from MACS2.cProb import *

# ------------------------------------
# Main function
# ------------------------------------

class Test_factorial(unittest.TestCase):

    def setUp(self):
        self.n1 = 100
        self.n2 = 10
        self.n3 = 1

    def test_factorial_big_n1(self):
        expect = 9.332622e+157
        result = factorial(self.n1)
        self.assertTrue( abs(result - expect) < 1e-5*result)

    def test_factorial_median_n2(self):
        expect = 3628800
        result = factorial(self.n2)
        self.assertEqual(result, expect)

    def test_factorial_small_n3(self):
        expect = 1
        result = factorial(self.n3)
        self.assertEqual(result, expect)

class Test_poisson_cdf(unittest.TestCase):

    def setUp(self):
        # n, lam
        self.n1 = (80,100)
        self.n2 = (200,100)
        self.n3 = (100,1000)
        self.n4 = (1500,1000)

    def test_poisson_cdf_n1(self):
        expect = (round(0.9773508,5),round(0.02264918,5))
        result = (round(poisson_cdf(self.n1[0],self.n1[1],False),5),
                  round(poisson_cdf(self.n1[0],self.n1[1],True),5))
        self.assertEqual( result, expect )

    def test_poisson_cdf_n2(self):
        expect = (round(log10(4.626179e-19),4),
                  round(log10(1),4))
        result = (round(log10(poisson_cdf(self.n2[0],self.n2[1],False)),4),
                  round(log10(poisson_cdf(self.n2[0],self.n2[1],True)),4))
        self.assertEqual( result, expect )

    def test_poisson_cdf_n3(self):
        expect = (round(log10(1),4),
                  round(log10(6.042525e-293),4))
        result = (round(log10(poisson_cdf(self.n3[0],self.n3[1],False)),4),
                  round(log10(poisson_cdf(self.n3[0],self.n3[1],True)),4))
        self.assertEqual( result, expect )

    def test_poisson_cdf_n4(self):
        expect = (round(log10(2.097225e-49),4),
                  round(log10(1),4))
        result = (round(log10(poisson_cdf(self.n4[0],self.n4[1],False)),4),
                  round(log10(poisson_cdf(self.n4[0],self.n4[1],True)),4))
        self.assertEqual( result, expect )

class Test_binomial_cdf(unittest.TestCase):

    def setUp(self):
        # x, a, b
        self.n1 = (20,1000,0.01)
        self.n2 = (200,1000,0.01)

    def test_binomial_cdf_n1(self):
        expect = (round(0.001496482,5),round(0.9985035,5))
        result = (round(binomial_cdf(self.n1[0],self.n1[1],self.n1[2],False),5),
                  round(binomial_cdf(self.n1[0],self.n1[1],self.n1[2],True),5))
        self.assertEqual( result, expect )

    def test_binomial_cdf_n2(self):
        expect = (round(log10(8.928717e-190),4),
                  round(log10(1),4))
        result = (round(log10(binomial_cdf(self.n2[0],self.n2[1],self.n2[2],False)),4),
                  round(log10(binomial_cdf(self.n2[0],self.n2[1],self.n2[2],True)),4))
        self.assertEqual( result, expect )

class Test_binomial_cdf_inv(unittest.TestCase):

    def setUp(self):
        # x, a, b
        self.n1 = (0.1,1000,0.01)
        self.n2 = (0.01,1000,0.01)

    def test_binomial_cdf_inv_n1(self):
        expect = 6
        result = binomial_cdf_inv(self.n1[0],self.n1[1],self.n1[2])
        self.assertEqual( result, expect )

    def test_poisson_cdf_inv_n2(self):
        expect = 3
        result = binomial_cdf_inv(self.n2[0],self.n2[1],self.n2[2])
        self.assertEqual( result, expect )

class Test_binomial_pdf(unittest.TestCase):

    def setUp(self):
        # x, a, b
        self.n1 = (20,1000,0.01)
        self.n2 = (200,1000,0.01)

    def test_binomial_cdf_inv_n1(self):
        expect = round(0.001791878,5)
        result = round(binomial_pdf(self.n1[0],self.n1[1],self.n1[2]),5)
        self.assertEqual( result, expect )

    def test_poisson_cdf_inv_n2(self):
        expect = round(log10(2.132196e-188),4)
        result = binomial_pdf(self.n2[0],self.n2[1],self.n2[2])
        result = round(log10(result),4)
        self.assertEqual( result, expect )

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cScoreTrack
#!/usr/bin/env python
# Time-stamp: <2012-06-09 16:44:48 Tao Liu>

import os
import sys
import unittest
import StringIO
from numpy.testing import assert_equal,  assert_almost_equal, assert_array_equal

from MACS2.IO.cScoreTrack import *

class Test_ScoreTrackII(unittest.TestCase):

    def setUp(self):
        # for initiate scoretrack
        self.test_regions1 = [("chrY",10,100,10),
                              ("chrY",60,10,10),
                              ("chrY",110,15,20),
                              ("chrY",160,5,20),
                              ("chrY",210,20,5)]
        self.treat_edm = 10
        self.ctrl_edm = 5
        # for scoring
        self.p_result = [63.27, 0.38, 0.07, 0.00, 7.09]
        self.q_result = [60.95, 0, 0, 0 ,5.81]
        self.l_result = [57.21, 0.00, -0.40, -3.79, 4.37]
        self.f_result = [0.96, 0.00, -0.12, -0.54, 0.54] # note, pseudo count 1 would be introduced.
        self.d_result = [90.00, 0, -5.00, -15.00, 15.00]
        self.m_result = [10.00, 1.00, 1.50, 0.50, 2.00]
        # for norm
        self.norm_T = np.array([[ 10, 100,  20,   0],
                                [ 60,  10,  20,   0],
                                [110,  15,  40,   0],
                                [160,   5,  40,   0],
                                [210,  20,  10,   0]]).transpose()
        self.norm_C = np.array([[ 10,  50,  10,   0],
                                [ 60,   5,  10,   0],
                                [110,   7.5,  20,   0],
                                [160,   2.5,  20,   0],
                                [210,  10,   5,   0]]).transpose()
        self.norm_M = np.array([[ 10,  10,   2,   0],
                                [ 60,   1,   2,   0],
                                [110,   1.5,   4,   0],
                                [160,   0.5,   4,   0],
                                [210,   2,   1,   0]]).transpose()
        self.norm_N = np.array([[ 10, 100,  10,   0],  # note precision lost
                                [ 60,  10,  10,   0],
                                [110,  15,  20,   0],
                                [160,   5,  20,   0],
                                [210,  20,   5,   0]]).transpose()

        # for write_bedGraph
        self.bdg1 = """chrY	0	10	100.00
chrY	10	60	10.00
chrY	60	110	15.00
chrY	110	160	5.00
chrY	160	210	20.00
"""
        self.bdg2 = """chrY	0	60	10.00
chrY	60	160	20.00
chrY	160	210	5.00
"""
        self.bdg3 = """chrY	0	10	63.27
chrY	10	60	0.38
chrY	60	110	0.07
chrY	110	160	0.00
chrY	160	210	7.09
"""
        # for peak calls
        self.peak1 = """chrY	0	60	peak_1	63.27
chrY	160	210	peak_2	7.09
"""
        self.summit1 = """chrY	5	6	peak_1	63.27
chrY	185	186	peak_2	7.09
"""
        self.xls1    ="""chr	start	end	length	abs_summit	pileup	-log10(pvalue)	fold_enrichment	-log10(qvalue)	name
chrY	1	60	60	6	100.00	63.27	9.18	-1.00	MACS_peak_1
chrY	161	210	50	186	20.00	7.09	3.50	-1.00	MACS_peak_2
"""
        
    def assertEqual_float ( self, a, b, roundn = 5 ):
        self.assertEqual( round( a, roundn ), round( b, roundn ) )

    def test_compute_scores(self):
        s1 = scoreTrackII( self.treat_edm, self.ctrl_edm )
        s1.add_chromosome( "chrY", 5 )
        for a in self.test_regions1:
            s1.add( a[0],a[1],a[2],a[3] )

        s1.set_pseudocount ( 1.0 )

        s1.change_score_method( ord('p') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.p_result )

        s1.change_score_method( ord('q') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.q_result )
        
        s1.change_score_method( ord('l') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.l_result )

        s1.change_score_method( ord('f') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.f_result )

        s1.change_score_method( ord('d') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.d_result )

        s1.change_score_method( ord('m') )
        r = s1.get_data_by_chr("chrY")
        self.assertListEqual( map(lambda x:round(x,2),list(r[3])), self.m_result )

    def test_normalize(self):
        s1 = scoreTrackII( self.treat_edm, self.ctrl_edm )
        s1.add_chromosome( "chrY", 5 )
        for a in self.test_regions1:
            s1.add( a[0],a[1],a[2],a[3] )

        s1.change_normalization_method( ord('T') )
        r = s1.get_data_by_chr("chrY")
        assert_array_equal( r, self.norm_T )

        s1.change_normalization_method( ord('C') )
        r = s1.get_data_by_chr("chrY")
        assert_array_equal( r, self.norm_C )

        s1.change_normalization_method( ord('M') )
        r = s1.get_data_by_chr("chrY")
        assert_array_equal( r, self.norm_M )

        s1.change_normalization_method( ord('N') )
        r = s1.get_data_by_chr("chrY")
        assert_array_equal( r, self.norm_N )

    def test_writebedgraph ( self ):
        s1 = scoreTrackII( self.treat_edm, self.ctrl_edm )
        s1.add_chromosome( "chrY", 5 )
        for a in self.test_regions1:
            s1.add( a[0],a[1],a[2],a[3] )

        s1.change_score_method( ord('p') )

        strio = StringIO.StringIO()
        s1.write_bedGraph( strio, "NAME", "DESC", 1 )
        self.assertEqual( strio.getvalue(), self.bdg1 )
        strio = StringIO.StringIO()        
        s1.write_bedGraph( strio, "NAME", "DESC", 2 )
        self.assertEqual( strio.getvalue(), self.bdg2 )
        strio = StringIO.StringIO()        
        s1.write_bedGraph( strio, "NAME", "DESC", 3 )
        self.assertEqual( strio.getvalue(), self.bdg3 )

    def test_callpeak ( self ):
        s1 = scoreTrackII( self.treat_edm, self.ctrl_edm )
        s1.add_chromosome( "chrY", 5 )
        for a in self.test_regions1:
            s1.add( a[0],a[1],a[2],a[3] )

        s1.change_score_method( ord('p') )
        p = s1.call_peaks( cutoff = 0.10, min_length=10, max_gap=10 )
        strio = StringIO.StringIO()
        p.write_to_bed( strio, trackline = False )
        self.assertEqual( strio.getvalue(), self.peak1 )

        strio = StringIO.StringIO()
        p.write_to_summit_bed( strio, trackline = False )
        self.assertEqual( strio.getvalue(), self.summit1 )

        strio = StringIO.StringIO()
        p.write_to_xls( strio )
        self.assertEqual( strio.getvalue(), self.xls1 )        


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cStat
#!/usr/bin/env python
# Time-stamp: <2012-02-26 19:33:56 Tao Liu>

import os
import sys
import unittest

from math import log10
from MACS2.cStat import *
from pymc.Matplot import mean
import numpy.random as rand


class Test_MCMCPoissonPosteriorRatio(unittest.TestCase):
    def setUp(self):
        self.p1 = [10,5]
        self.p2 = [10,5]
        self.p3 = [10,5]
        self.p4 = [10,5]        

    def test_func(self):
        # call func
        rand.seed([10])
        P = MCMCPoissonPosteriorRatio(15000,5000,self.p1[0],self.p1[1])
        P = sorted(P)
        print self.p1[0],self.p1[1],P[100],mean(P),P[-100]

        rand.seed([10])
        P = MCMCPoissonPosteriorRatio(15000,5000,self.p2[0],self.p2[1])
        P = sorted(P)
        print self.p2[0],self.p2[1],P[100],mean(P),P[-100]

        rand.seed([10])
        P = MCMCPoissonPosteriorRatio(15000,5000,self.p3[0],self.p3[1])
        P = sorted(P)
        print self.p3[0],self.p3[1],P[100],mean(P),P[-100]

        rand.seed([10])
        P = MCMCPoissonPosteriorRatio(15000,5000,self.p4[0],self.p4[1])
        P = sorted(P)
        print self.p4[0],self.p4[1],P[100],mean(P),P[-100]        

        #self.assertTrue( abs(result - expect) < 1e-5*result)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
