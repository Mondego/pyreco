__FILENAME__ = callable
"""Examine callable regions following genome mapping of short reads.

Identifies callable analysis regions surrounded by larger regions lacking
aligned bases. This allows parallelization of smaller chromosome chunks
through post-processing and variant calling, with each sub-section
mapping handled separately.

Regions are split to try to maintain relative uniformity across the
genome and avoid extremes of large blocks or large numbers of
small blocks.
"""
import contextlib
import copy
import operator
import os
import sys

import numpy
import pysam
try:
    import pybedtools
except ImportError:
    pybedtools = None
import toolz as tz

from bcbio import bam, broad, utils
from bcbio.bam import ref
from bcbio.log import logger
from bcbio.distributed import multi, prun
from bcbio.distributed.split import parallel_split_combine
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, shared
from bcbio.provenance import do
from bcbio.variation import multi as vmulti

def parallel_callable_loci(in_bam, ref_file, config):
    num_cores = config["algorithm"].get("num_cores", 1)
    config = copy.deepcopy(config)
    config["algorithm"]["memory_adjust"] = {"direction": "decrease", "magnitude": 2}
    data = {"work_bam": in_bam, "config": config,
            "reference": {"fasta": {"base": ref_file}}}
    parallel = {"type": "local", "cores": num_cores, "module": "bcbio.distributed"}
    items = [[data]]
    with prun.start(parallel, items, config, multiplier=int(num_cores)) as runner:
        split_fn = shared.process_bam_by_chromosome("-callable.bed", "work_bam")
        out = parallel_split_combine(items, split_fn, runner,
                                     "calc_callable_loci", "combine_bed",
                                     "callable_bed", ["config"])[0]
    return out[0]["callable_bed"]

@multi.zeromq_aware_logging
def calc_callable_loci(data, region=None, out_file=None):
    """Determine callable bases for an input BAM in the given region.

    We also identify super high depth regions (7x more than the set maximum depth) to
    avoid calling in since these are repetitive centromere and telomere regions that spike
    memory usage.
    """
    if out_file is None:
        out_file = "%s-callable.bed" % os.path.splitext(data["work_bam"])[0]
    max_depth = utils.get_in(data, ("config", "algorithm", "coverage_depth_max"), 10000)
    depth = {"max": max_depth * 7 if max_depth > 0 else sys.maxint - 1,
             "min": utils.get_in(data, ("config", "algorithm", "coverage_depth_min"), 4)}
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            ref_file = tz.get_in(["reference", "fasta", "base"], data)
            region_file, calc_callable = _regions_for_coverage(data, region, ref_file, tx_out_file)
            if calc_callable:
                _group_by_ctype(_get_coverage_file(data["work_bam"], ref_file, region_file, depth,
                                                   tx_out_file, data),
                                depth, region_file, tx_out_file)
            # special case, do not calculate if we are in a chromosome not covered by BED file
            else:
                os.move(region_file, tx_out_file)
    return [{"callable_bed": out_file, "config": data["config"], "work_bam": data["work_bam"]}]

def _group_by_ctype(bed_file, depth, region_file, out_file):
    """Group adjacent callable/uncallble regions into defined intervals.

    Uses tips from bedtools discussion:
    https://groups.google.com/d/msg/bedtools-discuss/qYDE6XF-GRA/2icQtUeOX_UJ
    https://gist.github.com/arq5x/b67196a46db5b63bee06
    """
    def assign_coverage(feat):
        feat.name = _get_ctype(int(feat.name), depth)
        return feat
    full_out_file = "%s-full%s" % utils.splitext_plus(out_file)
    with open(full_out_file, "w") as out_handle:
        for line in open(pybedtools.BedTool(bed_file).each(assign_coverage)
                                                     .groupby(g=[1, 4], c=[1, 2, 3, 4],
                                                              ops=["first", "first", "max", "first"]).fn):
            out_handle.write("\t".join(line.split("\t")[2:]))
    pybedtools.BedTool(full_out_file).intersect(region_file).saveas(out_file)

def _get_coverage_file(in_bam, ref_file, region_file, depth, base_file, data):
    """Retrieve summary of coverage in a region.
    Requires positive non-zero mapping quality at a position, matching GATK's
    CallableLoci defaults.
    """
    out_file = "%s-genomecov.bed" % utils.splitext_plus(base_file)[0]
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            bam.index(in_bam, data["config"])
            fai_file = ref.fasta_idx(ref_file, data["config"])
            sambamba = config_utils.get_program("sambamba", data["config"])
            bedtools = config_utils.get_program("bedtools", data["config"])
            max_depth = depth["max"] + 1
            cmd = ("{sambamba} view -F 'mapping_quality > 0' -L {region_file} -f bam -l 0 {in_bam} | "
                   "{bedtools} genomecov -ibam stdin -bga -g {fai_file} -max {max_depth} "
                   "> {tx_out_file}")
            do.run(cmd.format(**locals()), "Bedtools genomecov", data)
    return out_file

def _get_ctype(count, depth):
    if count == 0:
        return "NO_COVERAGE"
    elif count < depth["min"]:
        return "LOW_COVERAGE"
    elif count > depth["max"]:
        return "EXCESSIVE_COVERAGE"
    else:
        return "CALLABLE"

def _regions_for_coverage(data, region, ref_file, out_file):
    """Retrieve BED file of regions we need to calculate coverage in.
    """
    variant_regions = utils.get_in(data, ("config", "algorithm", "variant_regions"))
    ready_region = shared.subset_variant_regions(variant_regions, region, out_file)
    custom_file = "%s-coverageregions.bed" % utils.splitext_plus(out_file)[0]
    if not ready_region:
        get_ref_bedtool(ref_file, data["config"]).saveas(custom_file)
        return custom_file, True
    elif os.path.isfile(ready_region):
        return ready_region, True
    elif isinstance(ready_region, (list, tuple)):
        c, s, e = ready_region
        pybedtools.BedTool("%s\t%s\t%s\n" % (c, s, e), from_string=True).saveas(custom_file)
        return custom_file, True
    else:
        def add_nocoverage(feat):
            if variant_regions is not None:
                feat.name = "NO_COVERAGE"
            return feat
        assert isinstance(ready_region, basestring)
        get_ref_bedtool(ref_file, data["config"], ready_region).saveas().each(add_nocoverage).saveas(custom_file)
        return custom_file, variant_regions is None

def sample_callable_bed(bam_file, ref_file, config):
    """Retrieve callable regions for a sample subset by defined analysis regions.
    """
    out_file = "%s-callable_sample.bed" % os.path.splitext(bam_file)[0]
    with shared.bedtools_tmpdir({"config": config}):
        callable_bed = parallel_callable_loci(bam_file, ref_file, config)
        input_regions_bed = config["algorithm"].get("variant_regions", None)
        if not utils.file_uptodate(out_file, callable_bed):
            with file_transaction(out_file) as tx_out_file:
                callable_regions = pybedtools.BedTool(callable_bed)
                filter_regions = callable_regions.filter(lambda x: x.name == "CALLABLE")
                if input_regions_bed:
                    if not utils.file_uptodate(out_file, input_regions_bed):
                        input_regions = pybedtools.BedTool(input_regions_bed)
                        filter_regions.intersect(input_regions).saveas(tx_out_file)
                else:
                    filter_regions.saveas(tx_out_file)
    return out_file

def get_ref_bedtool(ref_file, config, chrom=None):
    """Retrieve a pybedtool BedTool object with reference sizes from input reference.
    """
    broad_runner = broad.runner_from_config(config)
    ref_dict = broad_runner.run_fn("picard_index_ref", ref_file)
    ref_lines = []
    with contextlib.closing(pysam.Samfile(ref_dict, "r")) as ref_sam:
        for sq in ref_sam.header["SQ"]:
            if not chrom or sq["SN"] == chrom:
                ref_lines.append("%s\t%s\t%s" % (sq["SN"], 0, sq["LN"]))
    return pybedtools.BedTool("\n".join(ref_lines), from_string=True)

def _get_nblock_regions(in_file, min_n_size):
    """Retrieve coordinates of regions in reference genome with no mapping.
    These are potential breakpoints for parallelizing analysis.
    """
    out_lines = []
    with open(in_file) as in_handle:
        for line in in_handle:
            contig, start, end, ctype = line.rstrip().split()
            if (ctype in ["REF_N", "NO_COVERAGE", "EXCESSIVE_COVERAGE", "LOW_COVERAGE"] and
                  int(end) - int(start) > min_n_size):
                out_lines.append("%s\t%s\t%s\n" % (contig, start, end))
    return pybedtools.BedTool("\n".join(out_lines), from_string=True)

def _combine_regions(all_regions, ref_regions):
    """Combine multiple BEDtools regions of regions into sorted final BEDtool.
    """
    chrom_order = {}
    for i, x in enumerate(ref_regions):
        chrom_order[x.chrom] = i
    def wchrom_key(x):
        chrom, start, end = x
        return (chrom_order[chrom], start, end)
    all_intervals = []
    for region_group in all_regions:
        for region in region_group:
            all_intervals.append((region.chrom, int(region.start), int(region.stop)))
    all_intervals.sort(key=wchrom_key)
    bed_lines = ["%s\t%s\t%s" % (c, s, e) for (c, s, e) in all_intervals]
    return pybedtools.BedTool("\n".join(bed_lines), from_string=True)

def _add_config_regions(nblock_regions, ref_regions, config):
    """Add additional nblock regions based on configured regions to call.
    Identifies user defined regions which we should not be analyzing.
    """
    input_regions_bed = config["algorithm"].get("variant_regions", None)
    if input_regions_bed:
        input_regions = pybedtools.BedTool(input_regions_bed)
        # work around problem with single region not subtracted correctly.
        if len(input_regions) == 1:
            str_regions = str(input_regions[0]).strip()
            input_regions = pybedtools.BedTool("%s\n%s" % (str_regions, str_regions),
                                               from_string=True)
        input_nblock = ref_regions.subtract(input_regions)
        if input_nblock == ref_regions:
            raise ValueError("Input variant_region file (%s) "
                             "excludes all genomic regions. Do the chromosome names "
                             "in the BED file match your genome (chr1 vs 1)?" % input_regions_bed)
        all_intervals = _combine_regions([input_nblock, nblock_regions], ref_regions)
        return all_intervals.merge()
    else:
        return nblock_regions

class NBlockRegionPicker:
    """Choose nblock regions reasonably spaced across chromosomes.

    This avoids excessively large blocks and also large numbers of tiny blocks
    by splitting to a defined number of blocks.

    Assumes to be iterating over an ordered input file and needs re-initiation
    with each new file processed as it keeps track of previous blocks to
    maintain the splitting.
    """
    def __init__(self, ref_regions, config):
        self._end_buffer = 250
        self._chr_last_blocks = {}
        target_blocks = int(config["algorithm"].get("nomap_split_targets", 2000))
        self._target_size = self._get_target_size(target_blocks, ref_regions)
        self._ref_sizes = {x.chrom: x.stop for x in ref_regions}

    def _get_target_size(self, target_blocks, ref_regions):
        size = 0
        for x in ref_regions:
            size += (x.end - x.start)
        return size // target_blocks

    def include_block(self, x):
        """Check for inclusion of block based on distance from previous.
        """
        last_pos = self._chr_last_blocks.get(x.chrom, 0)
        # Region excludes an entire chromosome, typically decoy/haplotypes
        if last_pos < self._end_buffer and x.stop >= self._ref_sizes.get(x.chrom, 0) - self._end_buffer:
            return True
        # Do not split on smaller decoy and haplotype chromosomes
        elif self._ref_sizes.get(x.chrom, 0) <= self._target_size:
            return False
        elif (x.start - last_pos) > self._target_size:
            self._chr_last_blocks[x.chrom] = x.stop
            return True
        else:
            return False

    def expand_block(self, feat):
        """Expand any blocks which are near the start or end of a contig.
        """
        chrom_end = self._ref_sizes.get(feat.chrom)
        if chrom_end:
            if feat.start < self._end_buffer:
                feat.start = 0
            if feat.stop >= chrom_end - self._end_buffer:
                feat.stop = chrom_end
        return feat

def block_regions(in_bam, ref_file, config):
    """Find blocks of regions for analysis from mapped input BAM file.

    Identifies islands of callable regions, surrounding by regions
    with no read support, that can be analyzed independently.
    """
    min_n_size = int(config["algorithm"].get("nomap_split_size", 100))
    with shared.bedtools_tmpdir({"config": config}):
        callable_bed = parallel_callable_loci(in_bam, ref_file, config)
        nblock_bed = "%s-nblocks%s" % os.path.splitext(callable_bed)
        callblock_bed = "%s-callableblocks%s" % os.path.splitext(callable_bed)
        if not utils.file_uptodate(nblock_bed, callable_bed):
            ref_regions = get_ref_bedtool(ref_file, config)
            nblock_regions = _get_nblock_regions(callable_bed, min_n_size)
            nblock_regions = _add_config_regions(nblock_regions, ref_regions, config)
            nblock_regions.saveas(nblock_bed)
            if len(ref_regions.subtract(nblock_regions)) > 0:
                ref_regions.subtract(nblock_bed).merge(d=min_n_size).saveas(callblock_bed)
            else:
                raise ValueError("No callable regions found from BAM file. Alignment regions might "
                                 "not overlap with regions found in your `variant_regions` BED: %s" % in_bam)
    return callblock_bed, nblock_bed, callable_bed

def _write_bed_regions(data, final_regions, out_file, out_file_ref):
    ref_file = tz.get_in(["reference", "fasta", "base"], data)
    ref_regions = get_ref_bedtool(ref_file, data["config"])
    noanalysis_regions = ref_regions.subtract(final_regions)
    final_regions.saveas(out_file)
    noanalysis_regions.saveas(out_file_ref)

def _analysis_block_stats(regions):
    """Provide statistics on sizes and number of analysis blocks.
    """
    prev = None
    between_sizes = []
    region_sizes = []
    for region in regions:
        if prev and prev.chrom == region.chrom:
            between_sizes.append(region.start - prev.end)
        region_sizes.append(region.end - region.start)
        prev = region
    def descriptive_stats(xs):
        if len(xs) < 2:
            return xs
        parts = ["min: %s" % min(xs),
                 "5%%: %s" % numpy.percentile(xs, 5),
                 "25%%: %s" % numpy.percentile(xs, 25),
                 "median: %s" % numpy.percentile(xs, 50),
                 "75%%: %s" % numpy.percentile(xs, 75),
                 "95%%: %s" % numpy.percentile(xs, 95),
                 "99%%: %s" % numpy.percentile(xs, 99),
                 "max: %s" % max(xs)]
        return "\n".join(["  " + x for x in parts])
    logger.info("Identified %s parallel analysis blocks\n" % len(region_sizes) +
                "Block sizes:\n%s\n" % descriptive_stats(region_sizes) +
                "Between block sizes:\n%s\n" % descriptive_stats(between_sizes))
    if len(region_sizes) == 0:
        raise ValueError("No callable analysis regions found in all samples")

def _needs_region_update(out_file, samples):
    """Check if we need to update BED file of regions, supporting back compatibility.
    """
    nblock_files = [x["regions"]["nblock"] for x in samples if "regions" in x]
    # For older approaches and do not create a new set of analysis
    # regions, since the new algorithm will re-do all BAM and variant
    # steps with new regions
    for nblock_file in nblock_files:
        test_old = nblock_file.replace("-nblocks", "-analysisblocks")
        if os.path.exists(test_old):
            return False
    # Check if any of the local files have changed so we need to refresh
    for noblock_file in nblock_files:
        if not utils.file_uptodate(out_file, noblock_file):
            return True
    return False

def _combine_excessive_coverage(samples, ref_regions, min_n_size):
    """Provide a global set of regions with excessive coverage to avoid.
    """
    flag = "EXCESSIVE_COVERAGE"
    ecs = (pybedtools.BedTool(x["regions"]["callable"]).filter(lambda x: x.name == flag)
           for x in samples if "regions" in x)
    merge_ecs = _combine_regions(ecs, ref_regions).saveas()
    if len(merge_ecs) > 0:
        return merge_ecs.merge(d=min_n_size).filter(lambda x: x.stop - x.start > min_n_size).saveas()
    else:
        return merge_ecs

def combine_sample_regions(*samples):
    """Create batch-level sets of callable regions for multi-sample calling.

    Intersects all non-callable (nblock) regions from all samples in a batch,
    producing a global set of callable regions.
    """
    # back compatibility -- global file for entire sample set
    global_analysis_file = os.path.join(samples[0]["dirs"]["work"], "analysis_blocks.bed")
    if utils.file_exists(global_analysis_file) and not _needs_region_update(global_analysis_file, samples):
        global_no_analysis_file = os.path.join(os.path.dirname(global_analysis_file), "noanalysis_blocks.bed")
    else:
        global_analysis_file = None
    out = []
    analysis_files = []
    with shared.bedtools_tmpdir(samples[0]):
        for batch, items in vmulti.group_by_batch(samples).items():
            if global_analysis_file:
                analysis_file, no_analysis_file = global_analysis_file, global_no_analysis_file
            else:
                analysis_file, no_analysis_file = _combine_sample_regions_batch(batch, items)
            for data in items:
                if analysis_file:
                    analysis_files.append(analysis_file)
                    data["config"]["algorithm"]["callable_regions"] = analysis_file
                    data["config"]["algorithm"]["non_callable_regions"] = no_analysis_file
                out.append([data])
        assert len(out) == len(samples)
        final_regions = pybedtools.BedTool(analysis_files[0])
        _analysis_block_stats(final_regions)
    return out

def _combine_sample_regions_batch(batch, items):
    """Combine sample regions within a group of batched samples.
    """
    config = items[0]["config"]
    work_dir = utils.safe_makedir(os.path.join(items[0]["dirs"]["work"], "regions"))
    analysis_file = os.path.join(work_dir, "%s-analysis_blocks.bed" % batch)
    no_analysis_file = os.path.join(work_dir, "%s-noanalysis_blocks.bed" % batch)
    if not utils.file_exists(analysis_file) or _needs_region_update(analysis_file, items):
        # Combine all nblocks into a final set of intersecting regions
        # without callable bases. HT @brentp for intersection approach
        # https://groups.google.com/forum/?fromgroups#!topic/bedtools-discuss/qA9wK4zN8do
        bed_regions = [pybedtools.BedTool(x["regions"]["nblock"])
                       for x in items if "regions" in x]
        if len(bed_regions) == 0:
            analysis_file, no_analysis_file = None, None
        else:
            nblock_regions = reduce(operator.add, bed_regions)
            ref_file = tz.get_in(["reference", "fasta", "base"], items[0])
            ref_regions = get_ref_bedtool(ref_file, config)
            min_n_size = int(config["algorithm"].get("nomap_split_size", 100))
            ec_regions = _combine_excessive_coverage(items, ref_regions, min_n_size)
            if len(ec_regions) > 0:
                nblock_regions = nblock_regions.cat(ec_regions, d=min_n_size)
            block_filter = NBlockRegionPicker(ref_regions, config)
            final_nblock_regions = nblock_regions.filter(
                block_filter.include_block).each(block_filter.expand_block).saveas()
            final_regions = ref_regions.subtract(final_nblock_regions).merge(d=min_n_size)
            _write_bed_regions(items[0], final_regions, analysis_file, no_analysis_file)
    return analysis_file, no_analysis_file

########NEW FILE########
__FILENAME__ = counts
"""Utilities to examine BAM counts in defined regions.

These are useful for plotting comparisons between BAM files to look at
differences in defined or random regions.
"""

import random
import collections

import pysam

class NormalizedBam:
    """Prepare and query an alignment BAM file for normalized read counts.
    """
    def __init__(self, name, fname, picard, quick=False):
        self.name = name
        self._bam = pysam.Samfile(fname, "rb")
        picard.run_fn("picard_index", fname)
        if quick:
            self._total = 1e6
        else:
            self._total = sum(1 for r in self._bam.fetch() if not r.is_unmapped)
            print name, self._total

    def all_regions(self):
        """Get a tuple of all chromosome, start and end regions.
        """
        regions = []
        for sq in self._bam.header["SQ"]:
            regions.append((sq["SN"], 1, int(sq["LN"])))
        return regions

    def read_count(self, space, start, end):
        """Retrieve the normalized read count in the provided region.
        """
        read_counts = 0
        for read in self._bam.fetch(space, start, end):
            read_counts += 1
        return self._normalize(read_counts, self._total)

    def coverage_pileup(self, space, start, end):
        """Retrieve pileup coverage across a specified region.
        """
        return ((col.pos, self._normalize(col.n, self._total))
                for col in self._bam.pileup(space, start, end))

    def _normalize(self, count, total):
        """Normalize to reads per million.
        """
        return float(count) / float(total) * 1e6

def random_regions(base, n, size):
    """Generate n random regions of 'size' in the provided base spread.
    """
    spread = size // 2
    base_info = collections.defaultdict(list)
    for space, start, end in base:
        base_info[space].append(start + spread)
        base_info[space].append(end - spread)
    regions = []
    for _ in range(n):
        space = random.choice(base_info.keys())
        pos = random.randint(min(base_info[space]), max(base_info[space]))
        regions.append([space, pos-spread, pos+spread])
    return regions


########NEW FILE########
__FILENAME__ = cram
"""Handle conversions to/from CRAM reference based compression.

http://www.ebi.ac.uk/ena/about/cram_toolkit
"""
import os
import subprocess

from bcbio import utils
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

def illumina_qual_bin(in_file, ref_file, out_dir, config):
    """Uses CRAM to perform Illumina 8-bin approaches to existing BAM files.

    Bins quality scores according to Illumina scheme:

    http://www.illumina.com/Documents/products/whitepapers/whitepaper_datacompression.pdf

    Also fixes output header to remove extra run groups added by CRAM during conversion.
    """
    index_file = ref_file + ".fai"
    assert os.path.exists(index_file), "Could not find FASTA reference index: %s" % index_file
    out_file = os.path.join(out_dir, "%s-qualbin%s" % os.path.splitext(os.path.basename(in_file)))
    resources = config_utils.get_resources("cram", config)
    jvm_opts = " ".join(resources.get("jvm_opts", ["-Xmx750m", "-Xmx2g"]))
    cram_jar = config_utils.get_jar("cramtools",
                                    config_utils.get_program("cram", config, "dir"))
    samtools = config_utils.get_program("samtools", config)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            orig_header = "%s-header.sam" % os.path.splitext(out_file)[0]
            header_cmd = "{samtools} view -H -o {orig_header} {in_file}"
            cmd = ("java {jvm_opts} -jar {cram_jar} cram --input-bam-file {in_file} "
                   " --reference-fasta-file {ref_file} --preserve-read-names "
                   " --capture-all-tags --lossy-quality-score-spec '*8' "
                   "| java {jvm_opts} -jar {cram_jar} bam --output-bam-format "
                   "  --reference-fasta-file {ref_file} "
                   "| {samtools} reheader {orig_header} - "
                   "> {tx_out_file}")
            logger.info("Quality binning with CRAM")
            subprocess.check_call(header_cmd.format(**locals()), shell=True)
            subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

def compress(in_bam, ref_file, config):
    """Compress a BAM file to CRAM, binning quality scores. Indexes CRAM file.
    """
    out_file = "%s.cram" % os.path.splitext(in_bam)[0]
    resources = config_utils.get_resources("cram", config)
    jvm_opts = " ".join(resources.get("jvm_opts", ["-Xms1500m", "-Xmx3g"]))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cmd = ("cramtools {jvm_opts} cram "
                   "--input-bam-file {in_bam} "
                   "--capture-all-tags "
                   "--ignore-tags 'BD:BI' "
                   "--reference-fasta-file {ref_file} "
                   "--lossy-quality-score-spec '*8' "
                   "--output-cram-file {tx_out_file}")
            subprocess.check_call(cmd.format(**locals()), shell=True)
    index(out_file)
    return out_file

def index(in_cram):
    """Ensure CRAM file has a .crai index file using cram_index from scramble.
    """
    if not utils.file_exists(in_cram + ".crai"):
        with file_transaction(in_cram + ".crai") as tx_out_file:
            tx_in_file = os.path.splitext(tx_out_file)[0]
            utils.symlink_plus(in_cram, tx_in_file)
            cmd = "cram_index {tx_in_file}"
            subprocess.check_call(cmd.format(**locals()), shell=True)

########NEW FILE########
__FILENAME__ = fastq
"""Utilities for working with fastq files.
"""

from itertools import izip, product
import os
import random
import gzip

from Bio import SeqIO

from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio import utils


@utils.memoize_outfile(stem=".groom")
def groom(in_file, in_qual="fastq-sanger", out_dir=None, out_file=None):
    """
    Grooms a FASTQ file into sanger format, if it is not already in that
    format. Use fastq-illumina for Illumina 1.3-1.7 qualities and
    fastq-solexa for the original solexa qualities. When in doubt, your
    sequences are probably fastq-sanger.

    """
    if in_qual == "fastq-sanger":
        logger.info("%s is already in Sanger format." % (in_file))
        return out_file
    with file_transaction(out_file) as tmp_out_file:
        count = SeqIO.convert(in_file, in_qual, tmp_out_file, "fastq-sanger")
    logger.info("Converted %d reads in %s to %s." % (count, in_file, out_file))
    return out_file

@utils.memoize_outfile(stem=".fixed")
def filter_single_reads_by_length(in_file, quality_format, min_length=20,
                                  out_file=None):
    """
    removes reads from a fastq file which are shorter than a minimum
    length

    """
    logger.info("Removing reads in %s thare are less than %d bases."
                % (in_file, min_length))
    in_iterator = SeqIO.parse(in_file, quality_format)
    out_iterator = (record for record in in_iterator if
                    len(record.seq) > min_length)
    with file_transaction(out_file) as tmp_out_file:
        with open(tmp_out_file, "w") as out_handle:
            SeqIO.write(out_iterator, out_handle, quality_format)
    return out_file

def filter_reads_by_length(fq1, fq2, quality_format, min_length=20):
    """
    removes reads from a pair of fastq files that are shorter than
    a minimum length. removes both ends of a read if one end falls
    below the threshold while maintaining the order of the reads

    """

    logger.info("Removing reads in %s and %s that "
                "are less than %d bases." % (fq1, fq2, min_length))
    fq1_out = utils.append_stem(fq1, ".fixed")
    fq2_out = utils.append_stem(fq2, ".fixed")
    fq1_single = utils.append_stem(fq1, ".singles")
    fq2_single = utils.append_stem(fq2, ".singles")
    if all(map(utils.file_exists, [fq1_out, fq2_out, fq2_single, fq2_single])):
        return [fq1_out, fq2_out]

    fq1_in = SeqIO.parse(fq1, quality_format)
    fq2_in = SeqIO.parse(fq2, quality_format)

    out_files = [fq1_out, fq2_out, fq1_single, fq2_single]

    with file_transaction(out_files) as tmp_out_files:
        fq1_out_handle = open(tmp_out_files[0], "w")
        fq2_out_handle = open(tmp_out_files[1], "w")
        fq1_single_handle = open(tmp_out_files[2], "w")
        fq2_single_handle = open(tmp_out_files[3], "w")

        for fq1_record, fq2_record in izip(fq1_in, fq2_in):
            if len(fq1_record.seq) >= min_length and len(fq2_record.seq) >= min_length:
                fq1_out_handle.write(fq1_record.format(quality_format))
                fq2_out_handle.write(fq2_record.format(quality_format))
            else:
                if len(fq1_record.seq) > min_length:
                    fq1_single_handle.write(fq1_record.format(quality_format))
                if len(fq2_record.seq) > min_length:
                    fq2_single_handle.write(fq2_record.format(quality_format))
        fq1_out_handle.close()
        fq2_out_handle.close()
        fq1_single_handle.close()
        fq2_single_handle.close()

    return [fq1_out, fq2_out]

def rstrip_extra(fname):
    """Strip extraneous, non-discriminative filename info from the end of a file.
    """
    to_strip = ("_R", "_", "fastq", ".", "-")
    while fname.endswith(to_strip):
        for x in to_strip:
            if fname.endswith(x):
                fname = fname[:len(fname) - len(x)]
                break
    return fname

def combine_pairs(input_files):
    """ calls files pairs if they are completely the same except
    for one has _1 and the other has _2 returns a list of tuples
    of pairs or singles.
    From bipy.utils (https://github.com/roryk/bipy/blob/master/bipy/utils.py)
    Adjusted to allow different input paths or extensions for matching files.
    """
    PAIR_FILE_IDENTIFIERS = set(["1", "2"])

    pairs = []
    used = set([])
    for in_file in input_files:
        if in_file in used:
            continue
        for comp_file in input_files:
            if comp_file in used or comp_file == in_file:
                continue
            a = rstrip_extra(utils.splitext_plus(os.path.basename(in_file))[0])
            b = rstrip_extra(utils.splitext_plus(os.path.basename(comp_file))[0])
            if len(a) != len(b):
                continue
            s = dif(a,b)
            if len(s) > 1:
                continue #there is only 1 difference
            if (a[s[0]] in PAIR_FILE_IDENTIFIERS and
                  b[s[0]] in PAIR_FILE_IDENTIFIERS):

                if b[s[0]- 1] in ("R", "_", "-"):

                            used.add(in_file)
                            used.add(comp_file)
                            if b[s[0]] == "2":
                                pairs.append([in_file, comp_file])
                            else:
                                pairs.append([comp_file, in_file])
                            break
        if in_file not in used:
            pairs.append([in_file])
            used.add(in_file)

    return pairs

def dif(a, b):
    """ copy from http://stackoverflow.com/a/8545526 """
    return [i for i in range(len(a)) if a[i] != b[i]]


def is_fastq(in_file):
    fastq_ends = [".fq", ".fastq"]
    zip_ends = [".gzip", ".gz"]
    base, first_ext = os.path.splitext(in_file)
    second_ext = os.path.splitext(base)[1]
    if first_ext in fastq_ends:
        return True
    elif second_ext + first_ext in product(fastq_ends, zip_ends):
        return True
    else:
        return False

def downsample(f1, f2, data, N, quick=False):
    """ get N random headers from a fastq file without reading the
    whole thing into memory
    modified from: http://www.biostars.org/p/6544/
    quick=True will just grab the first N reads rather than do a true
    downsampling
    """
    if quick:
        rand_records = range(N)
    else:
        records = sum(1 for _ in open(f1)) / 4
        N = records if N > records else N
        rand_records = random.sample(xrange(records), N)

    fh1 = open(f1)
    fh2 = open(f2) if f2 else None
    outf1 = os.path.splitext(f1)[0] + ".subset" + os.path.splitext(f1)[1]
    outf2 = os.path.splitext(f2)[0] + ".subset" + os.path.splitext(f2)[1] if f2 else None

    if utils.file_exists(outf1):
        if not outf2:
            return outf1, outf2
        elif utils.file_exists(outf2):
            return outf1, outf2

    out_files = (outf1, outf2) if outf2 else (outf1)

    with file_transaction(out_files) as tx_out_files:
        if isinstance(tx_out_files, basestring):
            tx_out_f1 = tx_out_files
        else:
            tx_out_f1, tx_out_f2 = tx_out_files
        sub1 = open(tx_out_f1, "w")
        sub2 = open(tx_out_f2, "w") if outf2 else None
        rec_no = - 1
        for rr in rand_records:
            while rec_no < rr:
                rec_no += 1
                for i in range(4): fh1.readline()
                if fh2:
                    for i in range(4): fh2.readline()
            for i in range(4):
                sub1.write(fh1.readline())
                if sub2:
                    sub2.write(fh2.readline())
            rec_no += 1
        fh1.close()
        sub1.close()
        if f2:
            fh2.close()
            sub2.close()

    return outf1, outf2

def estimate_read_length(fastq_file, quality_format="fastq-sanger", nreads=1000):
    """
    estimate average read length of a fastq file
    """

    in_handle = SeqIO.parse(fastq_file, quality_format)
    read = in_handle.next()
    average = len(read.seq)
    for _ in range(nreads):
        try:
            average = (average + len(in_handle.next().seq)) / 2
        except StopIteration:
            break
    in_handle.close()
    return average

def open_fastq(in_file):
    """ open a fastq file, using gzip if it is gzipped
    """
    _, ext = os.path.splitext(in_file)
    if ext == ".gz":
        return gzip.open(in_file, 'rb')
    if ext in [".fastq", ".fq"]:
        return open(in_file, 'r')


########NEW FILE########
__FILENAME__ = ref
"""Manipulation functionality to deal with reference files.
"""
import collections

from bcbio import utils
from bcbio.pipeline import config_utils
from bcbio.provenance import do

def fasta_idx(in_file, config):
    """Retrieve samtools style fasta index.
    """
    fasta_index = in_file + ".fai"
    if not utils.file_exists(fasta_index):
        samtools = config_utils.get_program("samtools", config)
        cmd = "{samtools} faidx {in_file}"
        do.run(cmd.format(**locals()), "samtools faidx")
    return fasta_index

def file_contigs(ref_file, config):
    """Iterator of reference contigs and lengths from a reference file.
    """
    ContigInfo = collections.namedtuple("ContigInfo", "name size")
    with open(fasta_idx(ref_file, config)) as in_handle:
        for line in (l for l in in_handle if l.strip()):
            name, size = line.split()[:2]
            yield ContigInfo(name, size)

########NEW FILE########
__FILENAME__ = trim
"""Provide trimming of input reads from Fastq or BAM files.
"""
import os
import sys
import tempfile

from bcbio.utils import (file_exists, safe_makedir,
                         replace_suffix, append_stem, is_pair,
                         replace_directory, map_wrap)
from bcbio.log import logger
from bcbio.bam import fastq
from bcbio.provenance import do
from Bio.Seq import Seq
from itertools import izip, repeat
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils


SUPPORTED_ADAPTERS = {
    "illumina": ["AACACTCTTTCCCT", "AGATCGGAAGAGCG"],
    "truseq": ["AGATCGGAAGAG"],
    "polya": ["AAAAAAAAAAAAA"],
    "nextera": ["AATGATACGGCGA", "CAAGCAGAAGACG"]}

ALIENTRIMMER_ADAPTERS = {
    "truseq": ["AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACATCACGATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACCGATGTATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACTTAGGCATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACTGACCAATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACACAGTGATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACGCCAATATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACCAGATCATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACACTTGAATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACGATCAGATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACTAGCTTATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACGGCTACATCTCGTATGCCGTCTTCTGCTTG",
               "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACCTTGTAATCTCGTATGCCGTCTTCTGCTTG"],
    "illumina": ["ACACTCTTTCCCTACACGACGCTCTTCCGATCT",
                 "GATCGGAAGAGCACACGTCTGAACTCCAGTCAC",
                 "GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT"],
    "polya": ["AAAAAAAAAAAAA"],
    "nextera": ["AATGATACGGCGACCACCGAGATCTACACTAGATCGCTCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACCTCTCTATTCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACTATCCTCTTCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACAGAGTAGATCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACGTAAGGAGTCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACACTGCATATCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACAAGGAGTATCGTCGGCAGCGTC",
                "AATGATACGGCGACCACCGAGATCTACACCTAAGCCTTCGTCGGCAGCGTC",
                "CAAGCAGAAGACGGCATACGAGATTCGCCTTAGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATCTAGTACGGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATTTCTGCCTGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATGCTCAGGAGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATAGGAGTCCGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATCATGCCTAGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATGTAGAGAGGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATCCTCTCTGGTCTCGTGGGCTCGG"
                "CAAGCAGAAGACGGCATACGAGATAGCGTAGCGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATCAGCCTCGGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATTGCCTCTTGTCTCGTGGGCTCGG",
                "CAAGCAGAAGACGGCATACGAGATTCCTCTACGTCTCGTGGGCTCGG"]}

QUALITY_FLAGS = {5: ['"E"', '"&"'],
                 20: ['"T"', '"5"']}

def trim_adapters(fastq_files, dirs, config):
    QUALITY_CUTOFF = 5
    to_trim = _get_sequences_to_trim(config, ALIENTRIMMER_ADAPTERS)
    resources = config_utils.get_resources("AlienTrimmer", config)
    try:
        jarpath = config_utils.get_program("AlienTrimmer", config, "dir")
    # fall back on Cutadapt if AlienTrimmer is not installed
    # XXX: remove after it has been live for a while
    except:
        return trim_read_through(fastq_files, dirs, config)
    jarfile = config_utils.get_jar("AlienTrimmer", jarpath)
    jvm_opts = " ".join(resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"]))
    base_cmd = ("java -jar {jvm_opts} {jarfile} -k 10 -l 20 ")
    fastq1 = fastq_files[0]
    supplied_quality_format = _get_quality_format(config)
    cores = config["algorithm"].get("num_cores", 0)
    out_files = _get_read_through_trimmed_outfiles(fastq_files, dirs)
    fastq1_out = out_files[0]
    if supplied_quality_format == "illumina":
        quality_flag = QUALITY_FLAGS[QUALITY_CUTOFF][0]
    else:
        quality_flag = QUALITY_FLAGS[QUALITY_CUTOFF][1]
    quality_flag = '-q ' + quality_flag
    if len(fastq_files) == 1:
        if file_exists(fastq1_out):
            return [fastq1_out]
        base_cmd += ("-i {fastq1} -o {tx_fastq1_out} -c {temp_file} "
                     "{quality_flag}")
        message = "Trimming %s from %s with AlienTrimmer." % (to_trim, fastq1)
    else:
        fastq2 = fastq_files[1]
        fastq2_out = out_files[1]
        if all(map(file_exists, [fastq1_out, fastq2_out])):
            return [fastq1_out, fastq2_out]
        base_cmd += ("-if {fastq1} -ir {fastq2} -of {tx_fastq1_out} "
                     "-or {tx_fastq2_out} -c {temp_file} {quality_flag}")
        message = ("Trimming %s from %s and %s with AlienTrimmer."
                   % (to_trim, fastq1, fastq2))
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp_file = temp.name
        for adapter in to_trim:
            temp.write(adapter + "\n")
        temp.close()


    if len(fastq_files) == 1:
        with file_transaction(fastq1_out) as tx_fastq1_out:
            do.run(base_cmd.format(**locals()), message)
        return [fastq1_out]
    else:
        with file_transaction([fastq1_out, fastq2_out]) as tx_out_files:
            tx_fastq1_out = tx_out_files[0]
            tx_fastq2_out = tx_out_files[1]
            do.run(base_cmd.format(**locals()), message)
        return [fastq1_out, fastq2_out]


def trim_read_through(fastq_files, dirs, lane_config):
    """
    for small insert sizes, the read length can be longer than the insert
    resulting in the reverse complement of the 3' adapter being sequenced.
    this takes adapter sequences and trims the only the reverse complement
    of the adapter

    MYSEQUENCEAAAARETPADA -> MYSEQUENCEAAAA (no polyA trim)

    """
    quality_format = _get_quality_format(lane_config)
    to_trim = _get_sequences_to_trim(lane_config, SUPPORTED_FORMATS)
    out_files = _get_read_through_trimmed_outfiles(fastq_files, dirs)
    fixed_files = append_stem(out_files, ".fixed")
    if all(map(file_exists, fixed_files)):
        return fixed_files
    logger.info("Trimming %s from the 3' end of reads in %s using "
                "cutadapt." % (", ".join(to_trim),
                               ", ".join(fastq_files)))
    cores = lane_config["algorithm"].get("num_cores", 1)
    out_files = _cutadapt_trim(fastq_files, quality_format,
                               to_trim, out_files, cores)

    fixed_files = remove_short_reads(out_files, dirs, lane_config)
    return fixed_files

def remove_short_reads(fastq_files, dirs, lane_config):
    """
    remove reads from a single or pair of fastq files which fall below
    a length threshold (30 bases)

    """
    min_length = int(lane_config["algorithm"].get("min_read_length", 20))
    supplied_quality_format = _get_quality_format(lane_config)
    if supplied_quality_format == "illumina":
        quality_format = "fastq-illumina"
    else:
        quality_format = "fastq-sanger"

    if is_pair(fastq_files):
        fastq1, fastq2 = fastq_files
        out_files = fastq.filter_reads_by_length(fastq1, fastq2, quality_format, min_length)
    else:
        out_files = [fastq.filter_single_reads_by_length(fastq_files[0],
                                                         quality_format, min_length)]
    map(os.remove, fastq_files)
    return out_files

def _get_read_through_trimmed_outfiles(fastq_files, dirs):
    out_dir = os.path.join(dirs["work"], "trim")
    safe_makedir(out_dir)
    out_files = replace_directory(append_stem(fastq_files, "_trimmed"),
                                  out_dir)
    return out_files

def _get_sequences_to_trim(lane_config, builtin):
    builtin_adapters = _get_builtin_adapters(lane_config, builtin)
    polya = builtin_adapters.get("polya", [None])[0]
    # allow for trimming of custom sequences for advanced users
    custom_trim = lane_config["algorithm"].get("custom_trim", [])
    builtin_adapters = {k: v for k, v in builtin_adapters.items() if
                        k != "polya"}
    trim_sequences = custom_trim
    # for unstranded RNA-seq, libraries, both polyA and polyT can appear
    # at the 3' end as well
    if polya:
        trim_sequences += [polya, str(Seq(polya).reverse_complement())]

    # also trim the reverse complement of the adapters
    for _, v in builtin_adapters.items():
        trim_sequences += [str(Seq(sequence)) for sequence in v]
        trim_sequences += [str(Seq(sequence).reverse_complement()) for
                           sequence in v]
    return trim_sequences


def _cutadapt_trim(fastq_files, quality_format, adapters, out_files, cores):
    """Trimming with cutadapt, using version installed with bcbio-nextgen.

    Uses the system executable to find the version next to our Anaconda Python.
    TODO: Could we use cutadapt as a library to avoid this?
    """
    if quality_format == "illumina":
        quality_base = "64"
    else:
        quality_base = "33"

    # --times=2 tries twice remove adapters which will allow things like:
    # realsequenceAAAAAAadapter to remove both the poly-A and the adapter
    # this behavior might not be what we want; we could also do two or
    # more passes of cutadapt
    cutadapt = os.path.join(os.path.dirname(sys.executable), "cutadapt")
    base_cmd = [cutadapt, "--times=" + "2", "--quality-base=" + quality_base,
                "--quality-cutoff=5", "--format=fastq", "--minimum-length=0"]
    adapter_cmd = map(lambda x: "--adapter=" + x, adapters)
    base_cmd.extend(adapter_cmd)
    if all(map(file_exists, out_files)):
        return out_files
    with file_transaction(out_files) as tmp_out_files:
        if isinstance(tmp_out_files, basestring):
            tmp_out_files = [tmp_out_files]
        map(_run_cutadapt_on_single_file, izip(repeat(base_cmd), fastq_files,
                                               tmp_out_files))
    return out_files

@map_wrap
def _run_cutadapt_on_single_file(base_cmd, fastq_file, out_file):
    stat_file = replace_suffix(out_file, ".trim_stats.txt")
    with open(stat_file, "w") as stat_handle:
        cmd = list(base_cmd)
        cmd.extend(["--output=" + out_file, fastq_file])
        do.run(cmd, "Running cutadapt on %s." % (fastq_file), None)


def _get_quality_format(lane_config):
    SUPPORTED_FORMATS = ["illumina", "standard"]
    quality_format = lane_config["algorithm"].get("quality_format",
                                                  "standard").lower()
    if quality_format not in SUPPORTED_FORMATS:
        logger.error("quality_format is set to an unsupported format. "
                     "Supported formats are %s."
                     % (", ".join(SUPPORTED_FORMATS)))
        exit(1)
    return quality_format

def _get_builtin_adapters(lane_config, builtin):
    chemistries = lane_config["algorithm"].get("adapters", [])
    adapters = {chemistry: builtin[chemistry] for
                chemistry in chemistries if chemistry in builtin}
    return adapters

########NEW FILE########
__FILENAME__ = metrics
"""Handle running, parsing and manipulating metrics available through Picard.
"""
import contextlib
import glob
import json
import os
import subprocess

from bcbio.utils import tmpfile, file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.broad.picardrun import picard_rnaseq_metrics

import pysam

class PicardMetricsParser(object):
    """Read metrics files produced by Picard analyses.

    Metrics info:
    http://picard.sourceforge.net/picard-metric-definitions.shtml
    """
    def __init__(self):
        pass

    def get_summary_metrics(self, align_metrics, dup_metrics,
            insert_metrics=None, hybrid_metrics=None, vrn_vals=None,
            rnaseq_metrics=None):
        """Retrieve a high level summary of interesting metrics.
        """
        with open(align_metrics) as in_handle:
            align_vals = self._parse_align_metrics(in_handle)
        if dup_metrics:
            with open(dup_metrics) as in_handle:
                dup_vals = self._parse_dup_metrics(in_handle)
        else:
            dup_vals = {}
        (insert_vals, hybrid_vals, rnaseq_vals) = (None, None, None)
        if insert_metrics and file_exists(insert_metrics):
            with open(insert_metrics) as in_handle:
                insert_vals = self._parse_insert_metrics(in_handle)
        if hybrid_metrics and file_exists(hybrid_metrics):
            with open(hybrid_metrics) as in_handle:
                hybrid_vals = self._parse_hybrid_metrics(in_handle)
        if rnaseq_metrics and file_exists(rnaseq_metrics):
            with open(rnaseq_metrics) as in_handle:
                rnaseq_vals = self._parse_rnaseq_metrics(in_handle)

        return self._tabularize_metrics(align_vals, dup_vals, insert_vals,
                hybrid_vals, vrn_vals, rnaseq_vals)

    def extract_metrics(self, metrics_files):
        """Return summary information for a lane of metrics files.
        """
        extension_maps = dict(
            align_metrics=(self._parse_align_metrics, "AL"),
            dup_metrics=(self._parse_dup_metrics, "DUP"),
            hs_metrics=(self._parse_hybrid_metrics, "HS"),
            insert_metrics=(self._parse_insert_metrics, "INS"),
            rnaseq_metrics=(self._parse_rnaseq_metrics, "RNA"))
        all_metrics = dict()
        for fname in metrics_files:
            ext = os.path.splitext(fname)[-1][1:]
            try:
                parse_fn, prefix = extension_maps[ext]
            except KeyError:
                parse_fn = None
            if parse_fn:
                with open(fname) as in_handle:
                    for key, val in parse_fn(in_handle).iteritems():
                        if not key.startswith(prefix):
                            key = "%s_%s" % (prefix, key)
                        all_metrics[key] = val
        return all_metrics

    def _tabularize_metrics(self, align_vals, dup_vals, insert_vals,
                            hybrid_vals, vrn_vals, rnaseq_vals):
        out = []
        # handle high level alignment for paired values
        paired = insert_vals is not None

        total = align_vals["TOTAL_READS"]
        align_total = int(align_vals["PF_READS_ALIGNED"])
        out.append(("Total", _add_commas(str(total)),
                    ("paired" if paired else "")))
        out.append(self._count_percent("Aligned",
                                       align_vals["PF_READS_ALIGNED"], total))
        if paired:
            out.append(self._count_percent("Pairs aligned",
                                           align_vals["READS_ALIGNED_IN_PAIRS"],
                                           total))
            align_total = int(align_vals["READS_ALIGNED_IN_PAIRS"])
            dup_total = dup_vals.get("READ_PAIR_DUPLICATES")
            if dup_total is not None:
                out.append(self._count_percent("Pair duplicates",
                                               dup_vals["READ_PAIR_DUPLICATES"],
                                               align_total))
            std = insert_vals.get("STANDARD_DEVIATION", "?")
            std_dev = "+/- %.1f" % float(std.replace(",", ".")) if (std and std != "?") else ""
            out.append(("Insert size",
                "%.1f" % float(insert_vals["MEAN_INSERT_SIZE"].replace(",", ".")), std_dev))
        if hybrid_vals:
            out.append((None, None, None))
            out.extend(self._tabularize_hybrid(hybrid_vals))
        if vrn_vals:
            out.append((None, None, None))
            out.extend(self._tabularize_variant(vrn_vals))
        if rnaseq_vals:
            out.append((None, None, None))
            out.extend(self._tabularize_rnaseq(rnaseq_vals))
        return out

    def _tabularize_variant(self, vrn_vals):
        out = []
        out.append(("Total variations", vrn_vals["total"], ""))
        out.append(("In dbSNP", "%.1f\%%" % vrn_vals["dbsnp_pct"], ""))
        out.append(("Transition/Transversion (all)", "%.2f" %
            vrn_vals["titv_all"], ""))
        out.append(("Transition/Transversion (dbSNP)", "%.2f" %
            vrn_vals["titv_dbsnp"], ""))
        out.append(("Transition/Transversion (novel)", "%.2f" %
            vrn_vals["titv_novel"], ""))
        return out

    def _tabularize_rnaseq(self, rnaseq_vals):
        out = []
        out.append(("5' to 3' bias",
                    rnaseq_vals["MEDIAN_5PRIME_TO_3PRIME_BIAS"], ""))
        out.append(("Percent of bases in coding regions",
                    rnaseq_vals["PCT_CODING_BASES"], ""))
        out.append(("Percent of bases in intergenic regions",
                    rnaseq_vals["PCT_INTERGENIC_BASES"], ""))
        out.append(("Percent of bases in introns",
                    rnaseq_vals["PCT_INTRONIC_BASES"], ""))
        out.append(("Percent of bases in mRNA",
                    rnaseq_vals["PCT_MRNA_BASES"], ""))
        out.append(("Percent of bases in rRNA",
                    rnaseq_vals["PCT_RIBOSOMAL_BASES"], ""))
        out.append(("Percent of bases in UTRs",
                    rnaseq_vals["PCT_UTR_BASES"], ""))
        return out


    def _tabularize_hybrid(self, hybrid_vals):
        out = []

        def try_float_format(in_string, float_format, multiplier=1.):
            in_string = in_string.replace(",", ".")
            try:
                out_string = float_format % (float(in_string) * multiplier)
            except ValueError:
                out_string = in_string

            return out_string

        total = hybrid_vals["PF_UQ_BASES_ALIGNED"]

        out.append(self._count_percent("On bait bases",
            hybrid_vals["ON_BAIT_BASES"], total))
        out.append(self._count_percent("Near bait bases",
            hybrid_vals["NEAR_BAIT_BASES"], total))
        out.append(self._count_percent("Off bait bases",
            hybrid_vals["OFF_BAIT_BASES"], total))
        out.append(("Mean bait coverage", "%s" %
            try_float_format(hybrid_vals["MEAN_BAIT_COVERAGE"], "%.1f"), ""))
        out.append(self._count_percent("On target bases",
            hybrid_vals["ON_TARGET_BASES"], total))
        out.append(("Mean target coverage", "%sx" %
            try_float_format(hybrid_vals["MEAN_TARGET_COVERAGE"], "%d"), ""))
        out.append(("10x coverage targets", "%s\%%" %
            try_float_format(hybrid_vals["PCT_TARGET_BASES_10X"], "%.1f", 100.0), ""))
        out.append(("Zero coverage targets", "%s\%%" %
            try_float_format(hybrid_vals["ZERO_CVG_TARGETS_PCT"], "%.1f", 100.0), ""))
        out.append(("Fold enrichment", "%sx" %
            try_float_format(hybrid_vals["FOLD_ENRICHMENT"], "%d"), ""))

        return out

    def _count_percent(self, text, count, total):
        if float(total) > 0:
            percent = "(%.1f\%%)" % (float(count) / float(total) * 100.0)
        else:
            percent = ""
        return (text, _add_commas(str(count)), percent)

    def _parse_hybrid_metrics(self, in_handle):
        want_stats = ["PF_UQ_BASES_ALIGNED", "ON_BAIT_BASES",
                "NEAR_BAIT_BASES", "OFF_BAIT_BASES",
                "ON_TARGET_BASES",
                "MEAN_BAIT_COVERAGE",
                "MEAN_TARGET_COVERAGE",
                "FOLD_ENRICHMENT",
                "ZERO_CVG_TARGETS_PCT",
                "BAIT_SET",
                "GENOME_SIZE",
                "HS_LIBRARY_SIZE",
                "BAIT_TERRITORY",
                "TARGET_TERRITORY",
                "PCT_SELECTED_BASES",
                "FOLD_80_BASE_PENALTY",
                "PCT_TARGET_BASES_2X",
                "PCT_TARGET_BASES_10X",
                "PCT_TARGET_BASES_20X",
                "HS_PENALTY_20X"
                ]
        header = self._read_off_header(in_handle)
        info = in_handle.readline().rstrip("\n").split("\t")
        vals = self._read_vals_of_interest(want_stats, header, info)
        return vals

    def _parse_align_metrics(self, in_handle):
        half_stats = ["TOTAL_READS", "PF_READS_ALIGNED",
                "READS_ALIGNED_IN_PAIRS"]
        std_stats = ["PF_HQ_ALIGNED_Q20_BASES",
                "PCT_READS_ALIGNED_IN_PAIRS", "MEAN_READ_LENGTH"]
        want_stats = half_stats + std_stats
        header = self._read_off_header(in_handle)
        while 1:
            info = in_handle.readline().rstrip("\n").split("\t")
            if len(info) <= 1:
                break
            vals = self._read_vals_of_interest(want_stats, header, info)
            if info[0].lower() == "pair":
                new_vals = dict()
                for item, val in vals.iteritems():
                    if item in half_stats:
                        new_vals[item] = str(int(val) // 2)
                    else:
                        new_vals[item] = val
                vals = new_vals
        return vals

    def _parse_dup_metrics(self, in_handle):
        if in_handle.readline().find("picard.metrics") > 0:
            want_stats = ["READ_PAIRS_EXAMINED", "READ_PAIR_DUPLICATES",
                    "PERCENT_DUPLICATION", "ESTIMATED_LIBRARY_SIZE"]
            header = self._read_off_header(in_handle)
            info = in_handle.readline().rstrip("\n").split("\t")
            vals = self._read_vals_of_interest(want_stats, header, info)
            return vals
        else:
            vals = {}
            for line in in_handle:
                metric, val = line.rstrip().split("\t")
                vals[metric] = val
            return vals

    def _parse_insert_metrics(self, in_handle):
        want_stats = ["MEDIAN_INSERT_SIZE", "MIN_INSERT_SIZE",
                "MAX_INSERT_SIZE", "MEAN_INSERT_SIZE", "STANDARD_DEVIATION"]
        header = self._read_off_header(in_handle)
        info = in_handle.readline().rstrip("\n").split("\t")
        vals = self._read_vals_of_interest(want_stats, header, info)
        return vals

    def _parse_rnaseq_metrics(self, in_handle):
        want_stats = ["PCT_RIBOSOMAL_BASES", "PCT_CODING_BASES", "PCT_UTR_BASES",
                      "PCT_INTRONIC_BASES", "PCT_INTERGENIC_BASES",
                      "PCT_MRNA_BASES", "PCT_USABLE_BASES", "MEDIAN_5PRIME_BIAS",
                      "MEDIAN_3PRIME_BIAS", "MEDIAN_5PRIME_TO_3PRIME_BIAS"]
        header = self._read_off_header(in_handle)
        info = in_handle.readline().rstrip("\n").split("\t")
        vals = self._read_vals_of_interest(want_stats, header, info)
        return vals

    def _read_vals_of_interest(self, want, header, info):
        want_indexes = [header.index(w) for w in want]
        vals = dict()
        for i in want_indexes:
            vals[header[i]] = info[i]
        return vals

    def _read_off_header(self, in_handle):
        while 1:
            line = in_handle.readline()
            if line.startswith("## METRICS"):
                break
        return in_handle.readline().rstrip("\n").split("\t")


class PicardMetrics(object):
    """Run reports using Picard, returning parsed metrics and files.
    """
    def __init__(self, picard, tmp_dir):
        self._picard = picard
        self._tmp_dir = tmp_dir
        self._parser = PicardMetricsParser()

    def report(self, align_bam, ref_file, is_paired, bait_file, target_file,
               variant_region_file, config):
        """Produce report metrics using Picard with sorted aligned BAM file.
        """
        dup_metrics = self._get_current_dup_metrics(align_bam)
        align_metrics = self._collect_align_metrics(align_bam, ref_file)
        # Prefer the GC metrics in FastQC instead of Picard
        # gc_graph, gc_metrics = self._gc_bias(align_bam, ref_file)
        gc_graph = None
        insert_graph, insert_metrics, hybrid_metrics = (None, None, None)
        if is_paired:
            insert_graph, insert_metrics = self._insert_sizes(align_bam)
        if bait_file and target_file:
            assert os.path.exists(bait_file), (bait_file, "does not exist!")
            assert os.path.exists(target_file), (target_file, "does not exist!")
            hybrid_metrics = self._hybrid_select_metrics(align_bam,
                                                         bait_file, target_file)
        elif (variant_region_file and
              config["algorithm"].get("coverage_interval", "").lower() in ["exome"]):
            assert os.path.exists(variant_region_file), (variant_region_file, "does not exist")
            hybrid_metrics = self._hybrid_select_metrics(
                align_bam, variant_region_file, variant_region_file)

        vrn_vals = self._variant_eval_metrics(align_bam)
        summary_info = self._parser.get_summary_metrics(align_metrics,
                dup_metrics, insert_metrics, hybrid_metrics,
                vrn_vals)
        graphs = []
        if gc_graph and os.path.exists(gc_graph):
            graphs.append((gc_graph, "Distribution of GC content across reads"))
        if insert_graph and os.path.exists(insert_graph):
            graphs.append((insert_graph, "Distribution of paired end insert sizes"))
        return summary_info, graphs

    def _get_current_dup_metrics(self, align_bam):
        """Retrieve duplicate information from input BAM file.
        """
        metrics_file = "%s.dup_metrics" % os.path.splitext(align_bam)[0]
        if not file_exists(metrics_file):
            dups = 0
            with contextlib.closing(pysam.Samfile(align_bam, "rb")) as bam_handle:
                for read in bam_handle:
                    if (read.is_paired and read.is_read1) or not read.is_paired:
                        if read.is_duplicate:
                            dups += 1
            with open(metrics_file, "w") as out_handle:
                out_handle.write("# custom bcbio-nextgen metrics\n")
                out_handle.write("READ_PAIR_DUPLICATES\t%s\n" % dups)
        return metrics_file

    def _check_metrics_file(self, bam_name, metrics_ext):
        """Check for an existing metrics file for the given BAM.
        """
        base, _ = os.path.splitext(bam_name)
        try:
            int(base[-1])
            can_glob = False
        except ValueError:
            can_glob = True
        check_fname = "{base}{maybe_glob}.{ext}".format(
            base=base, maybe_glob="*" if can_glob else "", ext=metrics_ext)
        glob_fnames = glob.glob(check_fname)
        if len(glob_fnames) > 0:
            return glob_fnames[0]
        else:
            return "{base}.{ext}".format(base=base, ext=metrics_ext)

    def _hybrid_select_metrics(self, dup_bam, bait_file, target_file):
        """Generate metrics for hybrid selection efficiency.
        """
        metrics = self._check_metrics_file(dup_bam, "hs_metrics")
        if not file_exists(metrics):
            with bed_to_interval(bait_file, dup_bam) as ready_bait:
                with bed_to_interval(target_file, dup_bam) as ready_target:
                    with file_transaction(metrics) as tx_metrics:
                        opts = [("BAIT_INTERVALS", ready_bait),
                                ("TARGET_INTERVALS", ready_target),
                                ("INPUT", dup_bam),
                                ("OUTPUT", tx_metrics)]
                        try:
                            self._picard.run("CalculateHsMetrics", opts)
                        # HsMetrics fails regularly with memory errors
                        # so we catch and skip instead of aborting the
                        # full process
                        except subprocess.CalledProcessError:
                            return None
        return metrics

    def _variant_eval_metrics(self, dup_bam):
        """Find metrics for evaluating variant effectiveness.
        """
        base, ext = os.path.splitext(dup_bam)
        end_strip = "-dup"
        base = base[:-len(end_strip)] if base.endswith(end_strip) else base
        mfiles = glob.glob("%s*eval_metrics" % base)
        if len(mfiles) > 0:
            with open(mfiles[0]) as in_handle:
                # pull the metrics as JSON from the last line in the file
                for line in in_handle:
                    pass
                metrics = json.loads(line)
            return metrics
        else:
            return None

    def _gc_bias(self, dup_bam, ref_file):
        gc_metrics = self._check_metrics_file(dup_bam, "gc_metrics")
        gc_graph = "%s-gc.pdf" % os.path.splitext(gc_metrics)[0]
        if not file_exists(gc_metrics):
            with file_transaction(gc_graph, gc_metrics) as \
                     (tx_graph, tx_metrics):
                opts = [("INPUT", dup_bam),
                        ("OUTPUT", tx_metrics),
                        ("CHART", tx_graph),
                        ("R", ref_file)]
                self._picard.run("CollectGcBiasMetrics", opts)
        return gc_graph, gc_metrics

    def _insert_sizes(self, dup_bam):
        insert_metrics = self._check_metrics_file(dup_bam, "insert_metrics")
        insert_graph = "%s-insert.pdf" % os.path.splitext(insert_metrics)[0]
        if not file_exists(insert_metrics):
            with file_transaction(insert_graph, insert_metrics) as \
                     (tx_graph, tx_metrics):
                opts = [("INPUT", dup_bam),
                        ("OUTPUT", tx_metrics),
                        ("H", tx_graph)]
                self._picard.run("CollectInsertSizeMetrics", opts)
        return insert_graph, insert_metrics

    def _collect_align_metrics(self, dup_bam, ref_file):
        align_metrics = self._check_metrics_file(dup_bam, "align_metrics")
        if not file_exists(align_metrics):
            with file_transaction(align_metrics) as tx_metrics:
                opts = [("INPUT", dup_bam),
                        ("OUTPUT", tx_metrics),
                        ("R", ref_file)]
                self._picard.run("CollectAlignmentSummaryMetrics", opts)
        return align_metrics


def _add_commas(s, sep=','):
    """Add commas to output counts.

    From: http://code.activestate.com/recipes/498181
    """
    if len(s) <= 3:
        return s

    return _add_commas(s[:-3], sep) + sep + s[-3:]


@contextlib.contextmanager
def bed_to_interval(orig_bed, bam_file):
    """Add header and format BED bait and target files for Picard if necessary.
    """
    with open(orig_bed) as in_handle:
        line = in_handle.readline()
    if line.startswith("@"):
        yield orig_bed
    else:
        bam_handle = pysam.Samfile(bam_file, "rb")
        with contextlib.closing(bam_handle):
            header = bam_handle.text
        with tmpfile(dir=os.path.dirname(orig_bed), prefix="picardbed") as tmp_bed:
            with open(tmp_bed, "w") as out_handle:
                out_handle.write(header)
                with open(orig_bed) as in_handle:
                    for line in in_handle:
                        parts = line.rstrip().split("\t")
                        if len(parts) == 3:
                            parts.append("+")
                            parts.append("a")
                        out_handle.write("\t".join(parts) + "\n")
            yield tmp_bed


class RNASeqPicardMetrics(PicardMetrics):

    def report(self, align_bam, ref_file, gtf_file, is_paired=False, rrna_file="null"):
        """Produce report metrics for a RNASeq experiment using Picard
        with a sorted aligned BAM file.

        """

        # collect duplication metrics
        dup_metrics = self._get_current_dup_metrics(align_bam)
        align_metrics = self._collect_align_metrics(align_bam, ref_file)
        insert_graph, insert_metrics = (None, None)
        if is_paired:
            insert_graph, insert_metrics = self._insert_sizes(align_bam)

        rnaseq_metrics = self._rnaseq_metrics(align_bam, gtf_file, rrna_file)

        summary_info = self._parser.get_summary_metrics(align_metrics,
                                                dup_metrics,
                                                insert_metrics=insert_metrics,
                                                rnaseq_metrics=rnaseq_metrics)
        graphs = []
        if insert_graph and file_exists(insert_graph):
            graphs.append((insert_graph,
                           "Distribution of paired end insert sizes"))
        return summary_info, graphs

    def _rnaseq_metrics(self, align_bam, gtf_file, rrna_file):
        metrics = self._check_metrics_file(align_bam, "rnaseq_metrics")
        if not file_exists(metrics):
            with file_transaction(metrics) as tx_metrics:
                picard_rnaseq_metrics(self._picard, align_bam, gtf_file,
                                      rrna_file, tx_metrics)

        return metrics

########NEW FILE########
__FILENAME__ = picardrun
"""Convenience functions for running common Picard utilities.
"""
import os
import collections
from contextlib import closing

import pysam

from bcbio.utils import curdir_tmpdir, file_exists
from bcbio.distributed.transaction import file_transaction


def picard_rnaseq_metrics(picard, align_bam, ref, ribo="null", out_file=None):
    """ Collect RNASeq metrics for a bam file """
    base, ext = os.path.splitext(align_bam)
    if out_file is None:
        out_file = "%s.metrics" % (base)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", align_bam),
                        ("OUTPUT", tx_out_file),
                        ("TMP_DIR", tmp_dir),
                        ("REF_FLAT", ref),
                        ("STRAND_SPECIFICITY", "NONE"),
                        ("ASSUME_SORTED", "True"),
                        ("RIBOSOMAL_INTERVALS", ribo)]

                picard.run("CollectRnaSeqMetrics", opts)
    return out_file

def picard_insert_metrics(picard, align_bam, out_file=None):
    """ Collect insert size metrics for a bam file """
    base, ext = os.path.splitext(align_bam)
    if out_file is None:
        out_file = "%s-insert-metrics.txt" % (base)
    histogram = "%s-insert-histogram.pdf" % (base)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", align_bam),
                        ("OUTPUT", tx_out_file),
                        ("HISTOGRAM_FILE", histogram),
                        ("TMP_DIR", tmp_dir)]
                picard.run("CollectInsertSizeMetrics", opts)
    return out_file


def picard_sort(picard, align_bam, sort_order="coordinate",
                out_file=None, compression_level=None, pipe=False):
    """Sort a BAM file by coordinates.
    """
    base, ext = os.path.splitext(align_bam)
    if out_file is None:
        out_file = "%s-sort%s" % (base, ext)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", align_bam),
                        ("OUTPUT", out_file if pipe else tx_out_file),
                        ("TMP_DIR", tmp_dir),
                        ("SORT_ORDER", sort_order)]
                if compression_level:
                    opts.append(("COMPRESSION_LEVEL", compression_level))
                picard.run("SortSam", opts, pipe=pipe)
    return out_file

def picard_merge(picard, in_files, out_file=None,
                 merge_seq_dicts=False):
    """Merge multiple BAM files together with Picard.
    """
    if out_file is None:
        out_file = "%smerge.bam" % os.path.commonprefix(in_files)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("OUTPUT", tx_out_file),
                        ("SORT_ORDER", "coordinate"),
                        ("MERGE_SEQUENCE_DICTIONARIES",
                         "true" if merge_seq_dicts else "false"),
                        ("USE_THREADING", "true"),
                        ("TMP_DIR", tmp_dir)]
                for in_file in in_files:
                    opts.append(("INPUT", in_file))
                picard.run("MergeSamFiles", opts)
    return out_file

def picard_index(picard, in_bam):
    index_file = "%s.bai" % in_bam
    alt_index_file = "%s.bai" % os.path.splitext(in_bam)[0]
    if not file_exists(index_file) and not file_exists(alt_index_file):
        with file_transaction(index_file) as tx_index_file:
            opts = [("INPUT", in_bam),
                    ("OUTPUT", tx_index_file)]
            picard.run("BuildBamIndex", opts)
    return index_file if file_exists(index_file) else alt_index_file

def picard_reorder(picard, in_bam, ref_file, out_file):
    """Reorder BAM file to match reference file ordering.
    """
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", in_bam),
                        ("OUTPUT", tx_out_file),
                        ("REFERENCE", ref_file),
                        ("ALLOW_INCOMPLETE_DICT_CONCORDANCE", "true"),
                        ("TMP_DIR", tmp_dir)]
                picard.run("ReorderSam", opts)
    return out_file

def picard_fix_rgs(picard, in_bam, names):
    """Add read group information to BAM files and coordinate sort.
    """
    out_file = "%s-fixrgs.bam" % os.path.splitext(in_bam)[0]
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", in_bam),
                        ("OUTPUT", tx_out_file),
                        ("SORT_ORDER", "coordinate"),
                        ("RGID", names["rg"]),
                        ("RGLB", names.get("library", "unknown")),
                        ("RGPL", names["pl"]),
                        ("RGPU", names["pu"]),
                        ("RGSM", names["sample"]),
                        ("TMP_DIR", tmp_dir)]
                picard.run("AddOrReplaceReadGroups", opts)
    return out_file

def picard_downsample(picard, in_bam, ds_pct, random_seed=None):
    out_file = "%s-downsample%s" % os.path.splitext(in_bam)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", in_bam),
                        ("OUTPUT", tx_out_file),
                        ("PROBABILITY", "%.3f" % ds_pct),
                        ("TMP_DIR", tmp_dir)]
                if random_seed:
                    opts += [("RANDOM_SEED", str(random_seed))]
                picard.run("DownsampleSam", opts)
    return out_file

def picard_index_ref(picard, ref_file):
    """Provide a Picard style dict index file for a reference genome.
    """
    dict_file = "%s.dict" % os.path.splitext(ref_file)[0]
    if not file_exists(dict_file):
        with file_transaction(dict_file) as tx_dict_file:
            opts = [("REFERENCE", ref_file),
                    ("OUTPUT", tx_dict_file)]
            picard.run("CreateSequenceDictionary", opts)
    return dict_file

def picard_fastq_to_bam(picard, fastq_one, fastq_two, out_dir, names, order="queryname"):
    """Convert fastq file(s) to BAM, adding sample, run group and platform information.
    """
    out_bam = os.path.join(out_dir, "%s-fastq.bam" %
                           os.path.splitext(os.path.basename(fastq_one))[0])
    if not file_exists(out_bam):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_bam) as tx_out_bam:
                opts = [("FASTQ", fastq_one),
                        ("READ_GROUP_NAME", names["rg"]),
                        ("SAMPLE_NAME", names["sample"]),
                        ("PLATFORM_UNIT", names["pu"]),
                        ("PLATFORM", names["pl"]),
                        ("TMP_DIR", tmp_dir),
                        ("OUTPUT", tx_out_bam),
                        ("SORT_ORDER", order)]
                if fastq_two:
                    opts.append(("FASTQ2", fastq_two))
                picard.run("FastqToSam", opts)
    return out_bam

def picard_bam_to_fastq(picard, in_bam, fastq_one, fastq_two=None):
    """Convert BAM file to fastq.
    """
    if not file_exists(fastq_one):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(fastq_one) as tx_out1:
                opts = [("INPUT", in_bam),
                        ("FASTQ", tx_out1),
                        ("TMP_DIR", tmp_dir)]
                if fastq_two is not None:
                    opts += [("SECOND_END_FASTQ", fastq_two)]
                picard.run("SamToFastq", opts)
    return (fastq_one, fastq_two)

def picard_sam_to_bam(picard, align_sam, fastq_bam, ref_file,
                      is_paired=False):
    """Convert SAM to BAM, including unmapped reads from fastq BAM file.
    """
    to_retain = ["XS", "XG", "XM", "XN", "XO", "YT"]
    if align_sam.endswith(".sam"):
        out_bam = "%s.bam" % os.path.splitext(align_sam)[0]
    elif align_sam.endswith("-align.bam"):
        out_bam = "%s.bam" % align_sam.replace("-align.bam", "")
    else:
        raise NotImplementedError("Input format not recognized")
    if not file_exists(out_bam):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_bam) as tx_out_bam:
                opts = [("UNMAPPED", fastq_bam),
                        ("ALIGNED", align_sam),
                        ("OUTPUT", tx_out_bam),
                        ("REFERENCE_SEQUENCE", ref_file),
                        ("TMP_DIR", tmp_dir),
                        ("PAIRED_RUN", ("true" if is_paired else "false")),
                        ]
                opts += [("ATTRIBUTES_TO_RETAIN", x) for x in to_retain]
                picard.run("MergeBamAlignment", opts)
    return out_bam

def picard_formatconverter(picard, align_sam):
    """Convert aligned SAM file to BAM format.
    """
    out_bam = "%s.bam" % os.path.splitext(align_sam)[0]
    if not file_exists(out_bam):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_bam) as tx_out_bam:
                opts = [("INPUT", align_sam),
                        ("OUTPUT", tx_out_bam),
                        ("TMP_DIR", tmp_dir)]
                picard.run("SamFormatConverter", opts)
    return out_bam

def picard_mark_duplicates(picard, align_bam, remove_dups=False):
    base, ext = os.path.splitext(align_bam)
    base = base.replace(".", "-")
    dup_bam = "%s-dup%s" % (base, ext)
    dup_metrics = "%s-dup.dup_metrics" % base
    if not file_exists(dup_bam):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(dup_bam, dup_metrics) as (tx_dup_bam, tx_dup_metrics):
                opts = [("INPUT", align_bam),
                        ("OUTPUT", tx_dup_bam),
                        ("TMP_DIR", tmp_dir),
                        ("REMOVE_DUPLICATES", "true" if remove_dups else "false"),
                        ("METRICS_FILE", tx_dup_metrics)]
                if picard.get_picard_version("MarkDuplicates") >= 1.82:
                    opts += [("PROGRAM_RECORD_ID", "null")]
                picard.run("MarkDuplicates", opts, memscale={"direction": "decrease", "magnitude": 2})
    return dup_bam, dup_metrics

def picard_fixmate(picard, align_bam):
    """Run Picard's FixMateInformation generating an aligned output file.
    """
    base, ext = os.path.splitext(align_bam)
    out_file = "%s-sort%s" % (base, ext)
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                opts = [("INPUT", align_bam),
                        ("OUTPUT", tx_out_file),
                        ("TMP_DIR", tmp_dir),
                        ("SORT_ORDER", "coordinate")]
                picard.run("FixMateInformation", opts)
    return out_file

def picard_idxstats(picard, align_bam):
    """Retrieve alignment stats from picard using BamIndexStats.
    """
    opts = [("INPUT", align_bam)]
    stdout = picard.run("BamIndexStats", opts, get_stdout=True)
    out = []
    AlignInfo = collections.namedtuple("AlignInfo", ["contig", "length", "aligned", "unaligned"])
    for line in stdout.split("\n"):
        if line:
            parts = line.split()
            if len(parts) == 2:
                _, unaligned = parts
                out.append(AlignInfo("nocontig", 0, 0, int(unaligned)))
            elif len(parts) == 7:
                contig, _, length, _, aligned, _, unaligned = parts
                out.append(AlignInfo(contig, int(length), int(aligned), int(unaligned)))
            else:
                raise ValueError("Unexpected output from BamIndexStats: %s" % line)
    return out

def bed2interval(align_file, bed, out_file=None):
    """Converts a bed file to an interval file for use with some of the
    Picard tools by grabbing the header from the alignment file, reording
    the bed file columns and gluing them together.

    align_file can be in BAM or SAM format.
    bed needs to be in bed12 format:
    http://genome.ucsc.edu/FAQ/FAQformat.html#format1.5

    """

    base, ext = os.path.splitext(align_file)
    if out_file is None:
        out_file = base + ".interval"

    with closing(pysam.Samfile(align_file, "r" if ext.endswith(".sam") else "rb")) as in_bam:
        header = in_bam.text

    def reorder_line(line):
        splitline = line.strip().split("\t")
        reordered = "\t".join([splitline[0], splitline[1] + 1, splitline[2],
                               splitline[5], splitline[3]])
        return reordered + "\n"

    with file_transaction(out_file) as tx_out_file:
        with open(bed) as bed_handle:
            with open(tx_out_file, "w") as out_handle:
                out_handle.write(header)
                for line in bed_handle:
                    out_handle.write(reorder_line(line))
    return out_file

########NEW FILE########
__FILENAME__ = clargs
"""Parsing of command line arguments into parallel inputs.
"""

def to_parallel(args, module="bcbio.distributed"):
    """Convert input arguments into a parallel dictionary for passing to processing.
    """
    ptype, cores = _get_cores_and_type(args.numcores, getattr(args, "paralleltype", None),
                                       args.scheduler)
    parallel = {"type": ptype, "cores": cores,
                "scheduler": args.scheduler, "queue": args.queue,
                "tag": args.tag, "module": module,
                "resources": args.resources, "timeout": args.timeout,
                "retries": args.retries,
                "run_local": args.queue == "localrun"}
    return parallel

def _get_cores_and_type(numcores, paralleltype, scheduler):
    """Return core and parallelization approach from command line providing sane defaults.
    """
    if scheduler is not None:
        paralleltype = "ipython"
    if paralleltype is None:
        paralleltype = "local"
    if not numcores or int(numcores) < 1:
        numcores = 1
    return paralleltype, int(numcores)

########NEW FILE########
__FILENAME__ = clusterk
"""Distributed execution on AWS spot instances using Clusterk.

http://www.clusterk.com/
https://clusterk.atlassian.net/wiki/display/DOC/Public+Documentation
"""
import contextlib

from bcbio.log import logger

@contextlib.contextmanager
def create(parallel):
    """Create a queue based on the provided parallel arguments.

    TODO Startup/tear-down. Currently using default queue for testing
    """
    queue = {k: v for k, v in parallel.items() if k in ["queue", "cores_per_job", "mem"]}
    yield queue

def runner(queue, parallel):
    """Run individual jobs on an existing queue.
    """
    def run(fn_name, items):
        logger.info("clusterk: %s" % fn_name)
        assert "wrapper" in parallel, "Clusterk requires bcbio-nextgen-vm wrapper"
        fn = getattr(__import__("{base}.clusterktasks".format(base=parallel["module"]),
                                fromlist=["clusterktasks"]),
                     parallel["wrapper"])
        wrap_parallel = {k: v for k, v in parallel.items() if k in set(["fresources", "pack"])}
        out = []
        for data in [fn(fn_name, queue, parallel.get("wrapper_args"), wrap_parallel, x) for x in items]:
            if data:
                out.extend(data)
        return out
    return run

########NEW FILE########
__FILENAME__ = ipython
"""Distributed execution using an IPython cluster.

Uses IPython parallel to setup a cluster and manage execution:

http://ipython.org/ipython-doc/stable/parallel/index.html

Cluster implementation from ipython-cluster-helper:

https://github.com/roryk/ipython-cluster-helper
"""
import json
import os
import zlib

import toolz as tz

from bcbio import utils
from bcbio.log import logger, get_log_dir
from bcbio.pipeline import config_utils
from bcbio.provenance import diagnostics

from cluster_helper import cluster as ipython_cluster

def create(parallel, dirs, config):
    """Create a cluster based on the provided parallel arguments.

    Returns an IPython view on the cluster, enabling processing on jobs.
    """
    profile_dir = utils.safe_makedir(os.path.join(dirs["work"], get_log_dir(config), "ipython"))
    return ipython_cluster.cluster_view(parallel["scheduler"].lower(), parallel["queue"],
                                        parallel["num_jobs"], parallel["cores_per_job"],
                                        profile=profile_dir, start_wait=parallel["timeout"],
                                        extra_params={"resources": parallel["resources"],
                                                      "mem": parallel["mem"],
                                                      "tag": parallel.get("tag"),
                                                      "run_local": parallel.get("run_local")},
                                        retries=parallel.get("retries"))

def _get_ipython_fn(fn_name, parallel):
    import_fn_name = parallel.get("wrapper", fn_name)
    return getattr(__import__("{base}.ipythontasks".format(base=parallel["module"]),
                              fromlist=["ipythontasks"]),
                   import_fn_name)

def _zip_args(items, config):
    """Compress and JSON encode arguments before sending to IPython, if configured.
    """
    if tz.get_in(["algorithm", "compress_msg"], config):
        #print [len(json.dumps(x)) for x in items]
        items = [zlib.compress(json.dumps(x, separators=(',', ':')), 9) for x in items]
        #print [len(x) for x in items]
    return items

def runner(view, parallel, dirs, config):
    """Run a task on an ipython parallel cluster, allowing alternative queue types.

    view provides map-style access to an existing Ipython cluster.
    """
    def run(fn_name, items):
        out = []
        items = [x for x in items if x is not None]
        items = diagnostics.track_parallel(items, fn_name)
        fn = _get_ipython_fn(fn_name, parallel)
        logger.info("ipython: %s" % fn_name)
        if len(items) > 0:
            items = [config_utils.add_cores_to_config(x, parallel["cores_per_job"], parallel) for x in items]
            if "wrapper" in parallel:
                wrap_parallel = {k: v for k, v in parallel.items() if k in set(["fresources"])}
                items = [[fn_name] + parallel.get("wrapper_args", []) + [wrap_parallel] + list(x) for x in items]
            items = _zip_args(items, config)
            for data in view.map_sync(fn, items, track=False):
                if data:
                    out.extend(data)
        return out
    return run

########NEW FILE########
__FILENAME__ = ipythontasks
"""Ipython parallel ready entry points for parallel execution
"""
import contextlib
import json
import zlib

from IPython.parallel import require

from bcbio import chipseq, structural
from bcbio.bam import callable
from bcbio.ngsalign import alignprep
from bcbio.pipeline import (archive, config_utils, disambiguate, sample, lane, qcsummary, shared,
                            variation, rnaseq)
from bcbio.provenance import system
from bcbio.variation import (bamprep, coverage, genotype, ensemble, multi, population,
                             recalibrate, validate, vcfutils)
from bcbio.log import logger, setup_local_logging

@contextlib.contextmanager
def _setup_logging(args):
    config = None
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        args = args[0]
    for arg in args:
        if config_utils.is_nested_config_arg(arg):
            config = arg["config"]
            break
        elif config_utils.is_std_config_arg(arg):
            config = arg
            break
        elif isinstance(arg, (list, tuple)) and config_utils.is_nested_config_arg(arg[0]):
            config = arg[0]["config"]
            break
    if config is None:
        raise NotImplementedError("No config found in arguments: %s" % args[0])
    handler = setup_local_logging(config, config.get("parallel", {}))
    try:
        yield None
    except:
        logger.exception("Unexpected error")
        raise
    finally:
        if hasattr(handler, "close"):
            handler.close()

def _unzip_args(args):
    """Unzip arguments if passed as compressed JSON string.
    """
    if len(args) == 1 and isinstance(args[0], basestring):
        return [json.loads(zlib.decompress(args[0]))]
    else:
        return args

@require(lane)
def process_lane(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(lane.process_lane, *args)

@require(lane)
def trim_lane(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(lane.trim_lane, *args)

@require(lane)
def process_alignment(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(lane.process_alignment, *args)

@require(alignprep)
def prep_align_inputs(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(alignprep.create_inputs, *args)

@require(lane)
def postprocess_alignment(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(lane.postprocess_alignment, *args)

@require(sample)
def merge_sample(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(sample.merge_sample, *args)

@require(sample)
def delayed_bam_merge(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(sample.delayed_bam_merge, *args)

@require(sample)
def recalibrate_sample(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(sample.recalibrate_sample, *args)

@require(recalibrate)
def prep_recal(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(recalibrate.prep_recal, *args)

@require(multi)
def split_variants_by_sample(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(multi.split_variants_by_sample, *args)

@require(bamprep)
def piped_bamprep(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(bamprep.piped_bamprep, *args)

@require(variation)
def postprocess_variants(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(variation.postprocess_variants, *args)

@require(qcsummary)
def pipeline_summary(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(qcsummary.pipeline_summary, *args)

@require(rnaseq)
def generate_transcript_counts(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(rnaseq.generate_transcript_counts, *args)

@require(rnaseq)
def run_cufflinks(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(rnaseq.run_cufflinks, *args)

@require(shared)
def combine_bam(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(shared.combine_bam, *args)

@require(callable)
def combine_sample_regions(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(callable.combine_sample_regions, *args)

@require(genotype)
def variantcall_sample(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(genotype.variantcall_sample, *args)

@require(vcfutils)
def combine_variant_files(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(vcfutils.combine_variant_files, *args)

@require(vcfutils)
def concat_variant_files(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(vcfutils.concat_variant_files, *args)

@require(vcfutils)
def merge_variant_files(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(vcfutils.merge_variant_files, *args)

@require(population)
def prep_gemini_db(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(population.prep_gemini_db, *args)

@require(structural)
def detect_sv(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(structural.detect_sv, *args)

@require(ensemble)
def combine_calls(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(ensemble.combine_calls, *args)

@require(validate)
def compare_to_rm(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(validate.compare_to_rm, *args)

@require(coverage)
def coverage_summary(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(coverage.summary, *args)

@require(disambiguate)
def run_disambiguate(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(disambiguate.run, *args)

@require(system)
def machine_info(*args):
    args = _unzip_args(args)
    return system.machine_info()

@require(chipseq)
def clean_chipseq_alignment(*args):
    args = _unzip_args(args)
    return chipseq.machine_info()

@require(archive)
def archive_to_cram(*args):
    args = _unzip_args(args)
    with _setup_logging(args):
        return apply(archive.to_cram, *args)

########NEW FILE########
__FILENAME__ = multi
"""Run tasks in parallel on a single machine using multiple cores.
"""
import functools

try:
    import joblib
except ImportError:
    joblib = False

from bcbio.distributed import resources
from bcbio.log import logger, setup_local_logging
from bcbio.pipeline import config_utils
from bcbio.provenance import diagnostics, system

def runner(parallel, config):
    """Run functions, provided by string name, on multiple cores on the current machine.
    """
    def run_parallel(fn_name, items):
        items = [x for x in items if x is not None]
        if len(items) == 0:
            return []
        items = diagnostics.track_parallel(items, fn_name)
        logger.info("multiprocessing: %s" % fn_name)
        fn = get_fn(fn_name, parallel)
        if "wrapper" in parallel:
            wrap_parallel = {k: v for k, v in parallel.items() if k in set(["fresources"])}
            items = [[fn_name] + parallel.get("wrapper_args", []) + [wrap_parallel] + list(x) for x in items]
        return run_multicore(fn, items, config, parallel=parallel)
    return run_parallel

def get_fn(fn_name, parallel):
    taskmod = "multitasks"
    imodule = parallel.get("module", "bcbio.distributed")
    import_fn_name = parallel.get("wrapper", fn_name)
    return getattr(__import__("{base}.{taskmod}".format(base=imodule, taskmod=taskmod),
                              fromlist=[taskmod]),
                   import_fn_name)

def zeromq_aware_logging(f):
    """Ensure multiprocessing logging uses ZeroMQ queues.

    ZeroMQ and local stdout/stderr do not behave nicely when intertwined. This
    ensures the local logging uses existing ZeroMQ logging queues.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        config = None
        for arg in args:
            if config_utils.is_std_config_arg(arg):
                config = arg
                break
            elif config_utils.is_nested_config_arg(arg):
                config = arg["config"]
            elif isinstance(arg, (list, tuple)) and config_utils.is_nested_config_arg(arg[0]):
                config = arg[0]["config"]
                break
        assert config, "Could not find config dictionary in function arguments."
        if config.get("parallel", {}).get("log_queue") and not config.get("parallel", {}).get("wrapper"):
            handler = setup_local_logging(config, config["parallel"])
        else:
            handler = None
        try:
            out = f(*args, **kwargs)
        finally:
            if handler and hasattr(handler, "close"):
                handler.close()
        return out
    return wrapper

def run_multicore(fn, items, config, parallel=None):
    """Run the function using multiple cores on the given items to process.
    """
    if parallel is None or "num_jobs" not in parallel:
        if parallel is None:
            parallel = {"type": "local", "cores": config["algorithm"].get("num_cores", 1)}
        sysinfo = system.get_info({}, parallel)
        parallel = resources.calculate(parallel, items, sysinfo, config,
                                       parallel.get("multiplier", 1),
                                       max_multicore=int(parallel.get("max_multicore", sysinfo["cores"])))
    items = [config_utils.add_cores_to_config(x, parallel["cores_per_job"]) for x in items]
    if joblib is None:
        raise ImportError("Need joblib for multiprocessing parallelization")
    out = []
    for data in joblib.Parallel(parallel["num_jobs"])(joblib.delayed(fn)(x) for x in items):
        if data:
            out.extend(data)
    return out

########NEW FILE########
__FILENAME__ = multitasks
"""Multiprocessing ready entry points for sample analysis.
"""
from bcbio import structural, utils, chipseq
from bcbio.bam import callable
from bcbio.ngsalign import alignprep
from bcbio.pipeline import (archive, disambiguate, lane, qcsummary, sample, shared, variation,
                            rnaseq)
from bcbio.variation import (bamprep, bedutils, coverage, genotype, ensemble, multi, population,
                             recalibrate, validate, vcfutils)

@utils.map_wrap
def process_lane(*args):
    return lane.process_lane(*args)

@utils.map_wrap
def trim_lane(*args):
    return lane.trim_lane(*args)

@utils.map_wrap
def process_alignment(*args):
    return lane.process_alignment(*args)

@utils.map_wrap
def postprocess_alignment(*args):
    return lane.postprocess_alignment(*args)

@utils.map_wrap
def prep_align_inputs(*args):
    return alignprep.create_inputs(*args)

@utils.map_wrap
def merge_sample(*args):
    return sample.merge_sample(*args)

@utils.map_wrap
def delayed_bam_merge(*args):
    return sample.delayed_bam_merge(*args)

@utils.map_wrap
def piped_bamprep(*args):
    return bamprep.piped_bamprep(*args)

@utils.map_wrap
def prep_recal(*args):
    return recalibrate.prep_recal(*args)

@utils.map_wrap
def split_variants_by_sample(*args):
    return multi.split_variants_by_sample(*args)

@utils.map_wrap
def postprocess_variants(*args):
    return variation.postprocess_variants(*args)

@utils.map_wrap
def pipeline_summary(*args):
    return qcsummary.pipeline_summary(*args)

@utils.map_wrap
def generate_transcript_counts(*args):
    return rnaseq.generate_transcript_counts(*args)

@utils.map_wrap
def run_cufflinks(*args):
    return rnaseq.run_cufflinks(*args)

@utils.map_wrap
def combine_bam(*args):
    return shared.combine_bam(*args)

@utils.map_wrap
def variantcall_sample(*args):
    return genotype.variantcall_sample(*args)

@utils.map_wrap
def combine_variant_files(*args):
    return vcfutils.combine_variant_files(*args)

@utils.map_wrap
def concat_variant_files(*args):
    return vcfutils.concat_variant_files(*args)

@utils.map_wrap
def merge_variant_files(*args):
    return vcfutils.merge_variant_files(*args)

@utils.map_wrap
def detect_sv(*args):
    return structural.detect_sv(*args)

@utils.map_wrap
def combine_calls(*args):
    return ensemble.combine_calls(*args)

@utils.map_wrap
def prep_gemini_db(*args):
    return population.prep_gemini_db(*args)

@utils.map_wrap
def combine_bed(*args):
    return bedutils.combine(*args)

@utils.map_wrap
def calc_callable_loci(*args):
    return callable.calc_callable_loci(*args)

@utils.map_wrap
def combine_sample_regions(*args):
    return callable.combine_sample_regions(*args)

@utils.map_wrap
def compare_to_rm(*args):
    return validate.compare_to_rm(*args)

@utils.map_wrap
def coverage_summary(*args):
    return coverage.summary(*args)

@utils.map_wrap
def run_disambiguate(*args):
    return disambiguate.run(*args)

@utils.map_wrap
def clean_chipseq_alignment(*args):
    return chipseq.clean_chipseq_alignment(*args)

@utils.map_wrap
def archive_to_cram(*args):
    return archive.to_cram(*args)

########NEW FILE########
__FILENAME__ = prun
"""Generalized running of parallel tasks in multiple environments.
"""
import contextlib
import os

from bcbio import utils
from bcbio.log import logger
from bcbio.provenance import system
from bcbio.distributed import clusterk, ipython, multi, resources

@contextlib.contextmanager
def start(parallel, items, config, dirs=None, name=None, multiplier=1, max_multicore=None):
    """Start a parallel cluster or machines to be used for running remote functions.

    Returns a function used to process, in parallel items with a given function.

    Allows sharing of a single cluster across multiple functions with
    identical resource requirements. Uses local execution for non-distributed
    clusters or completed jobs.

    A checkpoint directory keeps track of finished tasks, avoiding spinning up clusters
    for sections that have been previous processed.

    multiplier - Number of expected jobs per initial input item. Used to avoid underscheduling
      cores when an item is split during processing.
    max_multicore -- The maximum number of cores to use for each process. Can be used
      to process less multicore usage when jobs run faster on more single cores.
    """
    if name:
        checkpoint_dir = utils.safe_makedir(os.path.join(dirs["work"], "checkpoints_parallel"))
        checkpoint_file = os.path.join(checkpoint_dir, "%s.done" % name)
    else:
        checkpoint_file = None
    sysinfo = system.get_info(dirs, parallel)
    items = [x for x in items if x is not None] if items else []
    parallel = resources.calculate(parallel, items, sysinfo, config, multiplier=multiplier,
                                   max_multicore=int(max_multicore or sysinfo.get("cores", 1)))
    try:
        if checkpoint_file and os.path.exists(checkpoint_file):
            logger.info("run local -- checkpoint passed: %s" % name)
            parallel["cores_per_job"] = 1
            parallel["num_jobs"] = 1
            yield multi.runner(parallel, config)
        elif parallel["type"] == "ipython":
            with ipython.create(parallel, dirs, config) as view:
                yield ipython.runner(view, parallel, dirs, config)
        elif parallel["type"] == "clusterk":
            with clusterk.create(parallel) as queue:
                yield clusterk.runner(queue, parallel)
        else:
            yield multi.runner(parallel, config)
    except:
        raise
    else:
        for x in ["cores_per_job", "num_jobs", "mem"]:
            parallel.pop(x, None)
        if checkpoint_file:
            with open(checkpoint_file, "w") as out_handle:
                out_handle.write("done\n")

########NEW FILE########
__FILENAME__ = resources
"""Estimate resources required for processing a set of tasks.

Uses annotations provided in multitasks.py for each function to identify utilized
programs, then extracts resource requirements from the input bcbio_system file.
"""
import copy
import math

from bcbio.pipeline import config_utils
from bcbio.log import logger

def _get_resource_programs(progs, algs):
    """Retrieve programs used in analysis based on algorithm configurations.
    Handles special cases like aligners and variant callers.
    """
    out = set([])
    for p in progs:
        if p == "aligner":
            for alg in algs:
                aligner = alg.get("aligner")
                if aligner:
                    out.add(aligner)
        elif p == "variantcaller":
            for alg in algs:
                vc = alg.get("variantcaller")
                if vc:
                    if isinstance(vc, (list, tuple)):
                        for x in vc:
                            out.add(x)
                    else:
                        out.add(vc)
        elif p == "gatk-vqsr":
            if config_utils.use_vqsr(algs):
                out.add("gatk-vqsr")
        else:
            out.add(p)
    return sorted(list(out))

def _ensure_min_resources(progs, cores, memory, min_memory):
    """Ensure setting match minimum resources required for used programs.
    """
    for p in progs:
        if p in min_memory:
            if not memory or cores * memory < min_memory[p]:
                memory = float(min_memory[p]) / cores
    return cores, memory

def _str_memory_to_gb(memory):
    val = float(memory[:-1])
    units = memory[-1]
    if units.lower() == "m":
        val = val / 1000.0
    else:
        assert units.lower() == "g", "Unexpected memory units: %s" % memory
    return val

def _get_prog_memory(resources):
    """Get expected memory usage, in Gb per core, for a program from resource specification.
    """
    out = None
    for jvm_opt in resources.get("jvm_opts", []):
        if jvm_opt.startswith("-Xmx"):
            out = _str_memory_to_gb(jvm_opt[4:])
    memory = resources.get("memory")
    if memory:
        out = _str_memory_to_gb(memory)
    return out

def _scale_cores_to_memory(cores, mem_per_core, sysinfo, system_memory):
    """Scale multicore usage to avoid excessive memory usage based on system information.
    """
    total_mem = "%.1f" % (cores * mem_per_core + system_memory)
    if "cores" not in sysinfo:
        return cores, total_mem
    cores = min(cores, int(sysinfo["cores"]))
    total_mem = min(float(total_mem), float(sysinfo["memory"]) - system_memory)
    cores = max(1, min(cores, int(math.floor(float(total_mem) / mem_per_core))))
    return cores, total_mem

def _scale_jobs_to_memory(jobs, mem_per_core, sysinfo):
    """When scheduling jobs with single cores, avoid overscheduling due to memory.
    """
    if "cores" not in sysinfo:
        return jobs
    sys_mem_per_core = float(sysinfo["memory"]) / float(sysinfo["cores"])
    if sys_mem_per_core < mem_per_core:
        pct = sys_mem_per_core / float(mem_per_core)
        target_jobs = int(math.floor(jobs * pct))
        return max(target_jobs, 1)
    else:
        return jobs

def calculate(parallel, items, sysinfo, config, multiplier=1,
              max_multicore=None):
    """Determine cores and workers to use for this stage based on used programs.
    multiplier specifies the number of regions items will be split into during
    processing.
    max_multicore specifies an optional limit on the maximum cores. Can use to
    force single core processing during specific tasks.
    sysinfo specifies cores and memory on processing nodes, allowing us to tailor
    jobs for available resources.
    """
    assert len(items) > 0, "Finding job resources but no items to process"
    all_cores = []
    all_memory = []
    # Provide 250Mb of additional memory for the system
    system_memory = 0.25
    algs = [config_utils.get_algorithm_config(x) for x in items]
    progs = _get_resource_programs(parallel.get("progs", []), algs)
    for prog in progs:
        resources = config_utils.get_resources(prog, config)
        cores = resources.get("cores", 1)
        memory = _get_prog_memory(resources)
        all_cores.append(cores)
        if memory:
            all_memory.append(memory)
    # Use modest 1Gb memory usage per core as min baseline if not specified
    if len(all_memory) == 0:
        all_memory.append(1)
    if len(all_cores) == 0:
        all_cores.append(1)
    logger.debug("Resource requests: {progs}; memory: {memory}; cores: {cores}".format(
        progs=", ".join(progs), memory=", ".join("%.1f" % x for x in all_memory),
        cores=", ".join(str(x) for x in all_cores)))

    cores_per_job = max(all_cores)
    if max_multicore:
        cores_per_job = min(cores_per_job, max_multicore)
    if "cores" in sysinfo:
        cores_per_job = min(cores_per_job, int(sysinfo["cores"]))
    memory_per_core = max(all_memory)

    cores_per_job, memory_per_core = _ensure_min_resources(progs, cores_per_job, memory_per_core,
                                                           min_memory=parallel.get("ensure_mem", {}))

    total = parallel["cores"]
    if total > cores_per_job:
        num_jobs = total // cores_per_job
    else:
        num_jobs, cores_per_job = 1, total
    if cores_per_job == 1:
        memory_per_job = "%.1f" % (memory_per_core + system_memory)
        num_jobs = _scale_jobs_to_memory(num_jobs, memory_per_core, sysinfo)
    else:
        cores_per_job, memory_per_job = _scale_cores_to_memory(cores_per_job,
                                                               memory_per_core, sysinfo,
                                                               system_memory)
    # do not overschedule if we don't have extra items to process
    num_jobs = min(num_jobs, len(items) * multiplier)
    logger.debug("Configuring %d jobs to run, using %d cores each with %sg of "
                 "memory reserved for each job" % (num_jobs, cores_per_job,
                                                   str(memory_per_job)))
    parallel = copy.deepcopy(parallel)
    parallel["cores_per_job"] = cores_per_job
    parallel["num_jobs"] = num_jobs
    parallel["mem"] = str(memory_per_job)
    return parallel

########NEW FILE########
__FILENAME__ = runfn
"""Run distributed functions provided a name and json/YAML file with arguments.

Enables command line access and alternative interfaces to run specific
functionality within bcbio-nextgen.
"""
import os

import yaml

from bcbio import log, utils
from bcbio.distributed import multitasks
from bcbio.pipeline import config_utils

def process(args):
    """Run the function in args.name given arguments in args.argfile.
    """
    try:
        fn = getattr(multitasks, args.name)
    except AttributeError:
        raise AttributeError("Did not find exposed function in bcbio.distributed.multitasks named '%s'" % args.name)
    with open(args.argfile) as in_handle:
        fnargs = yaml.safe_load(in_handle)
    fnargs = config_utils.merge_resources(fnargs)
    work_dir = os.path.dirname(args.argfile)
    with utils.chdir(work_dir):
        log.setup_local_logging(parallel={"wrapper": "runfn"})
        out = fn(fnargs)
    out_file = "%s-out%s" % os.path.splitext(args.argfile)
    with open(out_file, "w") as out_handle:
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)

def add_subparser(subparsers):
    parser = subparsers.add_parser("runfn", help=("Run a specific bcbio-nextgen function."
                                                  "Intended for distributed use."))
    parser.add_argument("name", help="Name of the function to run")
    parser.add_argument("argfile", help="JSON file with arguments to the function")

########NEW FILE########
__FILENAME__ = split
"""Split files or tasks for distributed processing across multiple machines.

This tackles parallel work within the context of a program, where we split
based on input records like fastq or across regions like chromosomes in a
BAM file. Following splitting, individual records and run and then combined
back into a summarized output file.

This provides a framework for that process, making it easier to utilize with
splitting specific code.
"""
import copy
import collections

def grouped_parallel_split_combine(args, split_fn, group_fn, parallel_fn,
                                   parallel_name, combine_name,
                                   file_key, combine_arg_keys,
                                   split_outfile_i=-1):
    """Parallel split runner that allows grouping of samples during processing.

    This builds on parallel_split_combine to provide the additional ability to
    group samples and subsequently split them back apart. This allows analysis
    of related samples together. In addition to the arguments documented in
    parallel_split_combine, this needs:

    group_fn: A function that groups samples together given their configuration
      details.
    """
    grouped_args = group_fn(args)
    split_args, combine_map, finished_out, extras = _get_split_tasks(grouped_args, split_fn, file_key,
                                                                     split_outfile_i)
    final_output = parallel_fn(parallel_name, split_args)
    combine_args, final_args = _organize_output(final_output, combine_map,
                                                file_key, combine_arg_keys)
    parallel_fn(combine_name, combine_args)
    return finished_out + final_args + extras

def parallel_split_combine(args, split_fn, parallel_fn,
                           parallel_name, combiner,
                           file_key, combine_arg_keys, split_outfile_i=-1):
    """Split, run split items in parallel then combine to output file.

    split_fn: Split an input file into parts for processing. Returns
      the name of the combined output file along with the individual
      split output names and arguments for the parallel function.
    parallel_fn: Reference to run_parallel function that will run
      single core, multicore, or distributed as needed.
    parallel_name: The name of the function, defined in
      bcbio.distributed.tasks/multitasks/ipythontasks to run in parallel.
    combiner: The name of the function, also from tasks, that combines
      the split output files into a final ready to run file. Can also
      be a callable function if combining is delayed.
    split_outfile_i: the location of the output file in the arguments
      generated by the split function. Defaults to the last item in the list.
    """
    args = [x[0] for x in args]
    split_args, combine_map, finished_out, extras = _get_split_tasks(args, split_fn, file_key,
                                                                     split_outfile_i)
    split_output = parallel_fn(parallel_name, split_args)
    if isinstance(combiner, basestring):
        combine_args, final_args = _organize_output(split_output, combine_map,
                                                    file_key, combine_arg_keys)
        parallel_fn(combiner, combine_args)
    elif callable(combiner):
        final_args = combiner(split_output, combine_map, file_key)
    return finished_out + final_args + extras

def _get_extra_args(extra_args, arg_keys):
    """Retrieve extra arguments to pass along to combine function.

    Special cases like reference files and configuration information
    are passed as single items, the rest as lists mapping to each data
    item combined.
    """
    # XXX back compatible hack -- should have a way to specify these.
    single_keys = set(["sam_ref", "config"])
    out = []
    for i, arg_key in enumerate(arg_keys):
        vals = [xs[i] for xs in extra_args]
        if arg_key in single_keys:
            out.append(vals[-1])
        else:
            out.append(vals)
    return out

def _organize_output(output, combine_map, file_key, combine_arg_keys):
    """Combine output details for parallelization.

    file_key is the key name of the output file used in merging. We extract
    this file from the output data.

    combine_arg_keys are extra items to pass along to the combine function.
    """
    out_map = collections.defaultdict(list)
    extra_args = collections.defaultdict(list)
    final_args = collections.OrderedDict()
    extras = []
    for data in output:
        cur_file = data.get(file_key)
        if not cur_file:
            extras.append([data])
        else:
            cur_out = combine_map[cur_file]
            out_map[cur_out].append(cur_file)
            extra_args[cur_out].append([data[x] for x in combine_arg_keys])
            data[file_key] = cur_out
            if cur_out not in final_args:
                final_args[cur_out] = [data]
            else:
                extras.append([data])
    combine_args = [[v, k] + _get_extra_args(extra_args[k], combine_arg_keys)
                    for (k, v) in out_map.iteritems()]
    return combine_args, final_args.values() + extras

def _get_split_tasks(args, split_fn, file_key, outfile_i=-1):
    """Split up input files and arguments, returning arguments for parallel processing.

    outfile_i specifies the location of the output file in the arguments to
    the processing function. Defaults to the last item in the list.
    """
    split_args = []
    combine_map = {}
    finished_map = collections.OrderedDict()
    extras = []
    for data in args:
        out_final, out_parts = split_fn(data)
        for parts in out_parts:
            split_args.append([copy.deepcopy(data)] + list(parts))
        for part_file in [x[outfile_i] for x in out_parts]:
            combine_map[part_file] = out_final
        if len(out_parts) == 0:
            if out_final is not None:
                if out_final not in finished_map:
                    data[file_key] = out_final
                    finished_map[out_final] = [data]
                else:
                    extras.append([data])
            else:
                extras.append([data])
    return split_args, combine_map, finished_map.values(), extras

########NEW FILE########
__FILENAME__ = transaction
"""Handle file based transactions allowing safe restarts at any point.

To handle interrupts,this defines output files written to temporary
locations during processing and copied to the final location when finished.
This ensures output files will be complete independent of method of
interruption.
"""
import os
import shutil
import tempfile

import contextlib

from bcbio import utils

@contextlib.contextmanager
def file_transaction(*rollback_files):
    """Wrap file generation in a transaction, moving to output if finishes.
    """
    exts = {".vcf": ".idx", ".bam": ".bai", "vcf.gz": ".tbi"}
    safe_names, orig_names = _flatten_plus_safe(rollback_files)
    _remove_files(safe_names)  # remove any half-finished transactions
    try:
        if len(safe_names) == 1:
            yield safe_names[0]
        else:
            yield tuple(safe_names)
    except:  # failure -- delete any temporary files
        _remove_files(safe_names)
        _remove_tmpdirs(safe_names)
        raise
    else:  # worked -- move the temporary files to permanent location
        for safe, orig in zip(safe_names, orig_names):
            if os.path.exists(safe):
                shutil.move(safe, orig)
                for check_ext, check_idx in exts.iteritems():
                    if safe.endswith(check_ext):
                        safe_idx = safe + check_idx
                        if os.path.exists(safe_idx):
                            shutil.move(safe_idx, orig + check_idx)
        _remove_tmpdirs(safe_names)

def _remove_tmpdirs(fnames):
    for x in fnames:
        xdir = os.path.dirname(os.path.abspath(x))
        if xdir and os.path.exists(xdir):
            shutil.rmtree(xdir, ignore_errors=True)

def _remove_files(fnames):
    for x in fnames:
        if x and os.path.exists(x):
            if os.path.isfile(x):
                os.remove(x)
            elif os.path.isdir(x):
                shutil.rmtree(x, ignore_errors=True)

def _flatten_plus_safe(rollback_files):
    """Flatten names of files and create temporary file names.
    """
    tx_files, orig_files = [], []
    for fnames in rollback_files:
        if isinstance(fnames, basestring):
            fnames = [fnames]
        for fname in fnames:
            basedir = utils.safe_makedir(os.path.join(os.path.dirname(fname), "tx"))
            tmpdir = utils.safe_makedir(tempfile.mkdtemp(dir=basedir))
            tx_file = os.path.join(tmpdir, os.path.basename(fname))
            tx_files.append(tx_file)
            orig_files.append(fname)
    return tx_files, orig_files

########NEW FILE########
__FILENAME__ = api
"""Access Galaxy NGLIMS functionality via the standard API.
"""
import urllib
import urllib2
import json
import time

class GalaxyApiAccess:
    """Simple front end for accessing Galaxy's REST API.
    """
    def __init__(self, galaxy_url, api_key):
        self._base_url = galaxy_url
        self._key = api_key
        self._max_tries = 5

    def _make_url(self, rel_url, params=None):
        if not params:
            params = dict()
        params['key'] = self._key
        vals = urllib.urlencode(params)
        return ("%s%s" % (self._base_url, rel_url), vals)

    def _get(self, url, params=None):
        url, params = self._make_url(url, params)
        num_tries = 0
        while 1:
            response = urllib2.urlopen("%s?%s" % (url, params))
            try:
                out = json.loads(response.read())
                break
            except ValueError, msg:
                if num_tries > self._max_tries:
                    raise
                time.sleep(3)
                num_tries += 1
        return out

    def _post(self, url, data, params=None, need_return=True):
        url, params = self._make_url(url, params)
        request = urllib2.Request("%s?%s" % (url, params),
                headers = {'Content-Type' : 'application/json'},
                data = json.dumps(data))
        response = urllib2.urlopen(request)
        try:
            data = json.loads(response.read())
        except ValueError:
            if need_return:
                raise
            else:
                data = {}
        return data

    def run_details(self, run_bc, run_date=None):
        """Next Gen LIMS specific API functionality.
        """
        try:
            details = self._get("/nglims/api_run_details", dict(run=run_bc))
        except ValueError:
            raise ValueError("Could not find information in Galaxy for run: %s" % run_bc)
        if details.has_key("error") and run_date is not None:
            try:
                details = self._get("/nglims/api_run_details", dict(run=run_date))
            except ValueError:
                raise ValueError("Could not find information in Galaxy for run: %s" % run_date)
        return details

    def sequencing_projects(self):
        """Next Gen LIMS: retrieve summary information of sequencing projects.
        """
        return self._get("/nglims/api_projects")

    def sqn_run_summary(self, run_info):
        """Next Gen LIMS: Upload sequencing run summary information.
        """
        return self._post("/nglims/api_upload_sqn_run_summary",
                data=run_info)

    def sqn_report(self, start_date, end_date):
        """Next Gen LIMS: report of items sequenced in a time period.
        """
        return self._get("/nglims/api_sqn_report",
                dict(start=start_date, end=end_date))


########NEW FILE########
__FILENAME__ = nglims
"""Integration with Galaxy nglims.
"""
import collections
import copy
import glob
import gzip
import operator
import os
import subprocess

import joblib
import yaml

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.galaxy.api import GalaxyApiAccess
from bcbio.illumina import flowcell
from bcbio.pipeline.run_info import clean_name
from bcbio.workflow import template

def prep_samples_and_config(run_folder, ldetails, fastq_dir, config):
    """Prepare sample fastq files and provide global sample configuration for the flowcell.

    Handles merging of fastq files split by lane and also by the bcl2fastq
    preparation process.
    """
    fastq_final_dir = utils.safe_makedir(os.path.join(fastq_dir, "merged"))
    cores = utils.get_in(config, ("algorithm", "num_cores"), 1)
    ldetails = joblib.Parallel(cores)(joblib.delayed(_prep_sample_and_config)(x, fastq_dir, fastq_final_dir)
                                      for x in _group_same_samples(ldetails))
    config_file = _write_sample_config(run_folder, [x for x in ldetails if x])
    return config_file, fastq_final_dir

def _prep_sample_and_config(ldetail_group, fastq_dir, fastq_final_dir):
    """Prepare output fastq file and configuration for a single sample.

    Only passes non-empty files through for processing.
    """
    files = []
    print "->", ldetail_group[0]["name"], len(ldetail_group)
    for read in ["R1", "R2"]:
        fastq_inputs = sorted(reduce(operator.add, (_get_fastq_files(x, read, fastq_dir) for x in ldetail_group)))
        if len(fastq_inputs) > 0:
            files.append(_concat_bgzip_fastq(fastq_inputs, fastq_final_dir, read, ldetail_group[0]))
    if len(files) > 0:
        if _non_empty(files[0]):
            out = ldetail_group[0]
            out["files"] = files
            return out

def _non_empty(f):
    with gzip.open(f) as in_handle:
        for line in in_handle:
            return True
    return False

def _write_sample_config(run_folder, ldetails):
    """Generate a bcbio-nextgen YAML configuration file for processing a sample.
    """
    out_file = os.path.join(run_folder, "%s.yaml" % os.path.basename(run_folder))
    with open(out_file, "w") as out_handle:
        fc_name, fc_date = flowcell.parse_dirname(run_folder)
        out = {"details": sorted([_prepare_sample(x, run_folder) for x in ldetails],
                                 key=operator.itemgetter("name", "description")),
               "fc_name": fc_name,
               "fc_date": fc_date}
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

def _prepare_sample(data, run_folder):
    """Extract passed keywords from input LIMS information.
    """
    want = set(["description", "files", "genome_build", "name", "analysis", "upload", "algorithm"])
    out = {}
    for k, v in data.items():
        if k in want:
            out[k] = _relative_paths(v, run_folder)
    if "algorithm" not in out:
        analysis, algorithm = _select_default_algorithm(out.get("analysis"))
        out["algorithm"] = algorithm
        out["analysis"] = analysis
    description = "%s-%s" % (out["name"], clean_name(out["description"]))
    out["name"] = [out["name"], description]
    out["description"] = description
    return out

def _select_default_algorithm(analysis):
    """Provide default algorithm sections from templates or standard
    """
    if not analysis or analysis == "Standard":
        return "Standard", {"aligner": "bwa", "platform": "illumina", "quality_format": "Standard",
                            "recalibrate": False, "realign": False, "mark_duplicates": True,
                            "variantcaller": False}
    elif "variant" in analysis:
        try:
            config, _ = template.name_to_config(analysis)
        except ValueError:
            config, _ = template.name_to_config("freebayes-variant")
        return "variant", config["details"][0]["algorithm"]
    else:
        return analysis, {}

def _relative_paths(xs, base_path):
    """Adjust paths to be relative to the provided base path.
    """
    if isinstance(xs, basestring):
        if xs.startswith(base_path):
            return xs.replace(base_path + "/", "", 1)
        else:
            return xs
    elif isinstance(xs, (list, tuple)):
        return [_relative_paths(x, base_path) for x in xs]
    elif isinstance(xs, dict):
        out = {}
        for k, v in xs.items():
            out[k] = _relative_paths(v, base_path)
        return out
    else:
        return xs

def _get_fastq_files(ldetail, read, fastq_dir):
    """Retrieve fastq files corresponding to the sample and read number.
    """
    return glob.glob(os.path.join(fastq_dir, "Project_%s" % ldetail["project_name"],
                                  "Sample_%s" % ldetail["name"],
                                  "%s_*_%s_*.fastq.gz" % (ldetail["name"], read)))

def _concat_bgzip_fastq(finputs, out_dir, read, ldetail):
    """Concatenate multiple input fastq files, preparing a bgzipped output file.
    """
    out_file = os.path.join(out_dir, "%s_%s.fastq.gz" % (ldetail["name"], read))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            subprocess.check_call("zcat %s | bgzip -c > %s" % (" ".join(finputs), tx_out_file), shell=True)
    return out_file

def _group_same_samples(ldetails):
    """Move samples into groups -- same groups have identical names.
    """
    sample_groups = collections.defaultdict(list)
    for ldetail in ldetails:
        sample_groups[ldetail["name"]].append(ldetail)
    return sorted(sample_groups.values(), key=lambda xs: xs[0]["name"])

def get_runinfo(galaxy_url, galaxy_apikey, run_folder, storedir):
    """Retrieve flattened run information for a processed directory from Galaxy nglims API.
    """
    galaxy_api = GalaxyApiAccess(galaxy_url, galaxy_apikey)
    fc_name, fc_date = flowcell.parse_dirname(run_folder)
    galaxy_info = galaxy_api.run_details(fc_name, fc_date)
    if not galaxy_info["run_name"].startswith(fc_date) and not galaxy_info["run_name"].endswith(fc_name):
        raise ValueError("Galaxy NGLIMS information %s does not match flowcell %s %s" %
                         (galaxy_info["run_name"], fc_date, fc_name))
    ldetails = _flatten_lane_details(galaxy_info)
    out = []
    for item in ldetails:
        # Do uploads for all non-controls
        if item["description"] != "control" or item["project_name"] != "control":
            item["upload"] = {"method": "galaxy", "run_id": galaxy_info["run_id"],
                              "fc_name": fc_name, "fc_date": fc_date,
                              "dir": storedir,
                              "galaxy_url": galaxy_url, "galaxy_api_key": galaxy_apikey}
            for k in ["lab_association", "private_libs", "researcher", "researcher_id", "sample_id",
                      "galaxy_library", "galaxy_role"]:
                item["upload"][k] = item.pop(k, "")
        out.append(item)
    return out

def _flatten_lane_details(runinfo):
    """Provide flattened lane information with multiplexed barcodes separated.
    """
    out = []
    for ldetail in runinfo["details"]:
        # handle controls
        if "project_name" not in ldetail and ldetail["description"] == "control":
            ldetail["project_name"] = "control"
        for i, barcode in enumerate(ldetail.get("multiplex", [{}])):
            cur = copy.deepcopy(ldetail)
            cur["name"] = "%s-%s" % (ldetail["name"], i + 1)
            cur["description"] = barcode.get("name", ldetail["description"])
            cur["bc_index"] = barcode.get("sequence", "")
            cur["project_name"] = clean_name(ldetail["project_name"])
            out.append(cur)
    return out

########NEW FILE########
__FILENAME__ = search
"""Search using HMMER's online REST interface.

http://hmmer.janelia.org/search

From Nick Loman's EntrezAjax:

https://github.com/nickloman/entrezajax
"""
import urllib
import urllib2
import logging

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        logging.debug(headers)
        return headers

def _hmmer(endpoint, args1, args2):
    opener = urllib2.build_opener(SmartRedirectHandler())
    urllib2.install_opener(opener);

    params = urllib.urlencode(args1)
    try:
        req = urllib2.Request(endpoint,
                              data = params,
                              headers={"Accept" : "application/json"})
        v = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        raise Exception("HTTP Error 400: %s" % e.read())

    results_url = v['location']

    enc_res_params = urllib.urlencode(args2)
    modified_res_url = results_url + '?' + enc_res_params

    results_request = urllib2.Request(modified_res_url)
    f = urllib2.urlopen(results_request)
    return f

def phmmer(**kwargs):
    """Search a protein sequence against a HMMER sequence database.

    Arguments:
      seq - The sequence to search -- a Fasta string.
      seqdb -- Sequence database to search against.
      range -- A string range of results to return (ie. 1,10 for the first ten)
      output -- The output format (defaults to JSON).
    """
    logging.debug(kwargs)
    args = {'seq' : kwargs.get('seq'),
            'seqdb' : kwargs.get('seqdb')}
    args2 = {'output' : kwargs.get('output', 'json'),
             'range' : kwargs.get('range')}
    return _hmmer("http://hmmer.janelia.org/search/phmmer", args, args2)

def hmmscan(**kwargs):
    logging.debug(kwargs)
    args = {'seq' : kwargs.get('seq'),
            'hmmdb' : kwargs.get('hmmdb')}
    args2 = {'output' : 'json'}
    range = kwargs.get('range', None)
    if range:
        args2['range'] = range
    return _hmmer("http://hmmer.janelia.org/search/hmmscan", args, args2)

def test():
    seq = """>lcl||YPD4_1219|ftsK|128205128 putative cell division protein
MSQEYTEDKEVTLKKLSNGRRLLEAVLIVVTILAAYLMVALVSFNPSDPSWSQTAWHEPI
HNLGGSIGAWMADTLFSTFGVLAYAIPPIMVIFCWTAFRQRDASEYLDYFALSLRLIGTL
ALILTSCGLAALNIDDLYYFASGGVIGSLFSNAMLPWFNGVGATLTLLCIWVVGLTLFTG
WSWLVIAEKIGAAVLGSLTFITNRSRREERYDDEDSYHDDDHADGRDITGQEKGVVSNKG
VVSNNAVVGAGVAASSALAHGDDDVLFSAPSVTDSIVEHGSVVATGTETTDTKATDTNDE
YDPLLSPLRATDYSVQDATSSPIADVAVEPVLNHDAAAIYGTTPVMTNTATPPLYSFELP
EESLPIQTHAAPTERPEPKLGAWDMSPTPVSHSPFDFSAIQRPVGQLESRQPGSNQSGSH
QIHSAQSSHISVGNTPYMNPGLDAQIDGLSTTSLTNKPVLASGTVAAATAAAAFMPAFTA
TSDSSSQIKQGIGPELPRPNPVRIPTRRELASFGIKLPSQRMAEQELRERDGDETQNPQM
AASSYGTEITSDEDAALQQAILRKAFADQQSERYALSTLAEQSSITERSPAAEMPTTPSQ
VSDLEDEQALQEAELRQAFAAQQQHRYGATGDTDNAVDNIRSVDTSTAFTFSPIADLVDD
SPREPLFTLSPYVDETDVDEPVQLEGKEESLLQDYPEQVPTYQPPVQQAHLGQSAPTQPS
HTQSTYGQSTYGQSTYGQSTPAPVSQPVVTSASAISTSVTPTSIASLNTAPVSAAPVAPS
PQPPAFSQPTAAMDSLIHPFLMRNDQPLQKPTTPLPTLDLLSSPPAEEEPVDMFALEQTA
RLVEARLGDYRVKAEVVGISPGPVITRFELDLAPGVKASRISNLSRDLARSLSAIAVRVV
EVIPGKPYVGLELPNKHRQTVYLREVLDCAKFRENPSPLAIVLGKDIAGQPVVADLAKMP
HLLVAGTTGSGKSVGVNAMILSILYKATPDDVRFIMIDPKMLELSVYEGIPHLLTGVVTD
MKDAANALRWCVGEMERRYKLMSALGVRNLAGYNERVAQAEAMGRPIPDPFWKPSDSMDI
SPPMLVKLPYIVVMVDEFADLMMTVGKKVEELIARLAQKARAAGIHLVLATQRPSVDVIT
GLIKANIPTRIAFTVSSKIDSRTILDQGGAESLLGMGDMLYMAPNSSIPVRVHGAFVRDQ
EVHAVVNDWKARGRPQYIDSILSGGEEGEGGGLGLDSDEELDPLFDQAVNFVLEKRRASI
SGVQRQFRIGYNRAARIIEQMEAQQIVSTPGHNGNREVLAPPPHE"""
    handle = hmmscan(hmmdb = 'pfam', seq = seq)
    import json
    j = json.loads(handle.read())
    print json.dumps(j, sort_keys=True, indent=4)

# test()


########NEW FILE########
__FILENAME__ = demultiplex
"""Demultiplex and fastq conversion from Illumina output directories.

Uses Illumina's bcl2fastq: http://support.illumina.com/downloads/bcl2fastq_conversion_software_184.ilmn
"""
import os
import subprocess
import time

from bcbio import utils

def run_bcl2fastq(run_folder, ss_csv, config):
    """Run bcl2fastq for de-multiplexing and fastq generation.
    run_folder -- directory of Illumina outputs
    ss_csv -- Samplesheet CSV file describing samples.
    """
    bc_dir = os.path.join(run_folder, "Data", "Intensities", "BaseCalls")
    output_dir = os.path.join(run_folder, "fastq")

    if not os.path.exists(output_dir):
        subprocess.check_call(["configureBclToFastq.pl", "--no-eamss",
                               "--input-dir", bc_dir, "--output-dir", output_dir,
                               "--sample-sheet", ss_csv])
    with utils.chdir(output_dir):
        cores = str(utils.get_in(config, ("algorithm", "num_cores"), 1))
        cmd = ["make", "-j", cores]
        if "submit_cmd" in config["process"] and "bcl2fastq_batch" in config["process"]:
            _submit_and_wait(cmd, cores, config, output_dir)
        else:
            subprocess.check_call(cmd)
    return output_dir

def _submit_and_wait(cmd, cores, config, output_dir):
    """Submit command with batch script specified in configuration, wait until finished
    """
    batch_script = "submit_bcl2fastq.sh"
    if not os.path.exists(batch_script + ".finished"):
        if os.path.exists(batch_script + ".failed"):
            os.remove(batch_script + ".failed")
        with open(batch_script, "w") as out_handle:
            out_handle.write(config["process"]["bcl2fastq_batch"].format(
                cores=cores, bcl2fastq_cmd=" ".join(cmd), batch_script=batch_script))
        submit_cmd = utils.get_in(config, ("process", "submit_cmd"))
        subprocess.check_call(submit_cmd.format(batch_script=batch_script), shell=True)
        # wait until finished or failure checkpoint file
        while 1:
            if os.path.exists(batch_script + ".finished"):
                break
            if os.path.exists(batch_script + ".failed"):
                raise ValueError("bcl2fastq batch script failed: %s" %
                                 os.path.join(output_dir, batch_script))
            time.sleep(5)

########NEW FILE########
__FILENAME__ = flowcell
"""Utilities to manage processing flowcells and retrieving Galaxy stored info.
"""
import os
import glob
import urllib
import urllib2
import cookielib
import json

def parse_dirname(fc_dir):
    """Parse the flow cell ID and date from a flow cell directory.
    """
    (_, fc_dir) = os.path.split(fc_dir)
    parts = fc_dir.split("_")
    name = None
    date = None
    for p in parts:
        if p.endswith(("XX", "xx")):
            name = p
        elif len(p) == 6:
            try:
                int(p)
                date = p
            except ValueError:
                pass
    if name is None or date is None:
        raise ValueError("Did not find flowcell name: %s" % fc_dir)
    return name, date

def get_qseq_dir(fc_dir):
    """Retrieve the qseq directory within Solexa flowcell output.
    """
    machine_bc = os.path.join(fc_dir, "Data", "Intensities", "BaseCalls")
    if os.path.exists(machine_bc):
        return machine_bc
    # otherwise assume we are in the qseq directory
    # XXX What other cases can we end up with here?
    else:
        return fc_dir

def get_fastq_dir(fc_dir):
    """Retrieve the fastq directory within Solexa flowcell output.
    """
    full_goat_bc = glob.glob(os.path.join(fc_dir, "Data", "*Firecrest*", "Bustard*"))
    bustard_bc = glob.glob(os.path.join(fc_dir, "Data", "Intensities", "*Bustard*"))
    machine_bc = os.path.join(fc_dir, "Data", "Intensities", "BaseCalls")
    if os.path.exists(machine_bc):
        return os.path.join(machine_bc, "fastq")
    elif len(full_goat_bc) > 0:
        return os.path.join(full_goat_bc[0], "fastq")
    elif len(bustard_bc) > 0:
        return os.path.join(bustard_bc[0], "fastq")
    # otherwise assume we are in the fastq directory
    # XXX What other cases can we end up with here?
    else:
        return fc_dir

class GalaxySqnLimsApi:
    """Manage talking with the Galaxy REST api for sequencing information.
    """
    def __init__(self, base_url, user, passwd):
        self._base_url = base_url
        # build cookies so we keep track of being logged in
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
        login = dict(email=user, password=passwd, login_button='Login')
        req = urllib2.Request("%s/user/login" % self._base_url,
                urllib.urlencode(login))
        response = urllib2.urlopen(req)

    def run_details(self, run):
        """Retrieve sequencing run details as a dictionary.
        """
        run_data = dict(run=run)
        req = urllib2.Request("%s/nglims/api_run_details" % self._base_url,
                urllib.urlencode(run_data))
        response = urllib2.urlopen(req)
        info = json.loads(response.read())
        if info.has_key('error'):
            raise ValueError("Problem retrieving info: %s" % info["error"])
        else:
            return info["details"]

########NEW FILE########
__FILENAME__ = machine
"""Support integration with Illumina sequencer machines.
"""
import glob
import json
import os
import operator
import subprocess
from xml.etree.ElementTree import ElementTree

import logbook
import requests
import yaml

from bcbio import utils
from bcbio.log import setup_local_logging
from bcbio.illumina import demultiplex, samplesheet, transfer
from bcbio.galaxy import nglims

# ## bcbio-nextgen integration

def check_and_postprocess(args):
    """Check for newly dumped sequencer output, post-processing and transferring.
    """
    with open(args.process_config) as in_handle:
        config = yaml.safe_load(in_handle)
    setup_local_logging(config)
    for dname in _find_unprocessed(config):
        lane_details = nglims.get_runinfo(config["galaxy_url"], config["galaxy_apikey"], dname,
                                          utils.get_in(config, ("process", "storedir")))
        fcid_ss = samplesheet.from_flowcell(dname, lane_details)
        _update_reported(config["msg_db"], dname)
        fastq_dir = demultiplex.run_bcl2fastq(dname, fcid_ss, config)
        bcbio_config, ready_fastq_dir = nglims.prep_samples_and_config(dname, lane_details, fastq_dir, config)
        transfer.copy_flowcell(dname, ready_fastq_dir, bcbio_config, config)
        _start_processing(dname, bcbio_config, config)

def _remap_dirname(local, remote):
    """Remap directory names from local to remote.
    """
    def do(x):
        return x.replace(local, remote, 1)
    return do

def _start_processing(dname, sample_file, config):
    """Initiate processing: on a remote server or locally on a cluster.
    """
    to_remote = _remap_dirname(dname, os.path.join(utils.get_in(config, ("process", "dir")),
                                                   os.path.basename(dname)))
    args = {"work_dir": to_remote(os.path.join(dname, "analysis")),
            "run_config": to_remote(sample_file),
            "fc_dir": to_remote(dname)}
    # call a remote server
    if utils.get_in(config, ("process", "server")):
        print "%s/run?args=%s" % (utils.get_in(config, ("process", "server")), json.dumps(args))
        requests.get(url="%s/run" % utils.get_in(config, ("process", "server")),
                     params={"args": json.dumps(args)})
    # submit to a cluster scheduler
    elif "submit_cmd" in config["process"] and "bcbio_batch" in config["process"]:
        with utils.chdir(utils.safe_makedir(args["work_dir"])):
            batch_script = "submit_bcbio.sh"
            with open(batch_script, "w") as out_handle:
                out_handle.write(config["process"]["bcbio_batch"].format(fcdir=args["fc_dir"],
                                                                         run_config=args["run_config"]))
            submit_cmd = utils.get_in(config, ("process", "submit_cmd"))
            subprocess.check_call(submit_cmd.format(batch_script=batch_script), shell=True)
    else:
        raise ValueError("Unexpected processing approach: %s" % config["process"])

def add_subparser(subparsers):
    """Add command line arguments for post-processing sequencer results.
    """
    parser = subparsers.add_parser("sequencer", help="Post process results from a sequencer.")
    parser.add_argument("process_config", help="YAML file specifying sequencer details for post-processing.")
    return parser

# ## Dump directory processing

def _find_unprocessed(config):
    """Find any finished directories that have not been processed.
    """
    reported = _read_reported(config["msg_db"])
    for dname in _get_directories(config):
        if os.path.isdir(dname) and dname not in reported:
            if _is_finished_dumping(dname):
                yield dname

def _get_directories(config):
    for directory in config["dump_directories"]:
        for dname in sorted(glob.glob(os.path.join(directory, "*[Aa]*[Xx][Xx]"))):
            if os.path.isdir(dname):
                yield dname

def _is_finished_dumping(directory):
    """Determine if the sequencing directory has all files.

    The final checkpoint file will differ depending if we are a
    single or paired end run.
    """
    #if _is_finished_dumping_checkpoint(directory):
    #    return True
    # Check final output files; handles both HiSeq and GAII
    run_info = os.path.join(directory, "RunInfo.xml")
    hi_seq_checkpoint = "Basecalling_Netcopy_complete_Read%s.txt" % \
                        _expected_reads(run_info)
    to_check = ["Basecalling_Netcopy_complete_SINGLEREAD.txt",
                "Basecalling_Netcopy_complete_READ2.txt",
                hi_seq_checkpoint]
    return reduce(operator.or_,
                  [os.path.exists(os.path.join(directory, f)) for f in to_check])

def _is_finished_dumping_checkpoint(directory):
    """Recent versions of RTA (1.10 or better), write the complete file.

    This is the most straightforward source but as of 1.10 still does not
    work correctly as the file will be created at the end of Read 1 even
    if there are multiple reads.
    """
    check_file = os.path.join(directory, "Basecalling_Netcopy_complete.txt")
    check_v1, check_v2 = (1, 10)
    if os.path.exists(check_file):
        with open(check_file) as in_handle:
            line = in_handle.readline().strip()
        if line:
            version = line.split()[-1]
            v1, v2 = [float(v) for v in version.split(".")[:2]]
            if ((v1 > check_v1) or (v1 == check_v1 and v2 >= check_v2)):
                return True

def _expected_reads(run_info_file):
    """Parse the number of expected reads from the RunInfo.xml file.
    """
    reads = []
    if os.path.exists(run_info_file):
        tree = ElementTree()
        tree.parse(run_info_file)
        read_elem = tree.find("Run/Reads")
        reads = read_elem.findall("Read")
    return len(reads)

# ## Flat file of processed directories

def _read_reported(msg_db):
    """Retrieve a list of directories previous reported.
    """
    reported = []
    if os.path.exists(msg_db):
        with open(msg_db) as in_handle:
            for line in in_handle:
                reported.append(line.strip())
    return reported

def _update_reported(msg_db, new_dname):
    """Add a new directory to the database of reported messages.
    """
    with open(msg_db, "a") as out_handle:
        out_handle.write("%s\n" % new_dname)

########NEW FILE########
__FILENAME__ = samplesheet
"""Converts Illumina SampleSheet CSV files to the run_info.yaml input file.

This allows running the analysis pipeline without Galaxy, using CSV input
files from Illumina SampleSheet or Genesifter.
"""
import os
import csv
import itertools
import difflib
import glob

import yaml

from bcbio.illumina import flowcell
from bcbio import utils

# ## Create samplesheets

def from_flowcell(run_folder, lane_details, out_dir=None):
    """Convert a flowcell into a samplesheet for demultiplexing.
    """
    fcid = os.path.basename(run_folder)
    if out_dir is None:
        out_dir = run_folder
    out_file = os.path.join(out_dir, "%s.csv" % fcid)
    with open(out_file, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(["FCID", "Lane", "Sample_ID", "SampleRef", "Index",
                         "Description", "Control", "Recipe", "Operator", "SampleProject"])
        for ldetail in lane_details:
            writer.writerow(_lane_detail_to_ss(fcid, ldetail))
    return out_file

def _lane_detail_to_ss(fcid, ldetail):
    """Convert information about a lane into Illumina samplesheet output.
    """
    return [fcid, ldetail["lane"], ldetail["name"], ldetail["genome_build"],
            ldetail["bc_index"], ldetail["description"], "N", "", "",
            ldetail["project_name"]]

# ## Use samplesheets to create YAML files

def _organize_lanes(info_iter, barcode_ids):
    """Organize flat lane information into nested YAML structure.
    """
    all_lanes = []
    for (fcid, lane, sampleref), info in itertools.groupby(info_iter, lambda x: (x[0], x[1], x[1])):
        info = list(info)
        cur_lane = dict(flowcell_id=fcid, lane=lane, genome_build=info[0][3], analysis="Standard")
        
        if not _has_barcode(info):
            cur_lane["description"] = info[0][1]
        else: # barcoded sample
            cur_lane["description"] = "Barcoded lane %s" % lane
            multiplex = []
            for (_, _, sample_id, _, bc_seq) in info:
                bc_type, bc_id = barcode_ids[bc_seq]
                multiplex.append(dict(barcode_type=bc_type,
                                      barcode_id=bc_id,
                                      sequence=bc_seq,
                                      name=sample_id))
            cur_lane["multiplex"] = multiplex
        all_lanes.append(cur_lane)
    return all_lanes

def _has_barcode(sample):
    if sample[0][4]:
        return True

def _generate_barcode_ids(info_iter):
    """Create unique barcode IDs assigned to sequences
    """
    bc_type = "SampleSheet"
    barcodes = list(set([x[-1] for x in info_iter]))
    barcodes.sort()
    barcode_ids = {}
    for i, bc in enumerate(barcodes):
        barcode_ids[bc] = (bc_type, i+1)
    return barcode_ids

def _read_input_csv(in_file):
    """Parse useful details from SampleSheet CSV file.
    """
    with open(in_file, "rU") as in_handle:
        reader = csv.reader(in_handle)
        reader.next() # header
        for line in reader:
            if line: # empty lines
                (fc_id, lane, sample_id, genome, barcode) = line[:5]
                yield fc_id, lane, sample_id, genome, barcode

def _get_flowcell_id(in_file, require_single=True):
    """Retrieve the unique flowcell id represented in the SampleSheet.
    """
    fc_ids = set([x[0] for x in _read_input_csv(in_file)])
    if require_single and len(fc_ids) > 1:
        raise ValueError("There are several FCIDs in the same samplesheet file: %s" % in_file)
    else:
        return fc_ids

def csv2yaml(in_file, out_file=None):
    """Convert a CSV SampleSheet to YAML run_info format.
    """
    if out_file is None:
        out_file = "%s.yaml" % os.path.splitext(in_file)[0]
    barcode_ids = _generate_barcode_ids(_read_input_csv(in_file))
    lanes = _organize_lanes(_read_input_csv(in_file), barcode_ids)
    with open(out_file, "w") as out_handle:
        out_handle.write(yaml.safe_dump(lanes, default_flow_style=False))
    return out_file

def run_has_samplesheet(fc_dir, config, require_single=True):
    """Checks if there's a suitable SampleSheet.csv present for the run
    """
    fc_name, _ = flowcell.parse_dirname(fc_dir)
    sheet_dirs = config.get("samplesheet_directories", [])
    fcid_sheet = {}
    for ss_dir in (s for s in sheet_dirs if os.path.exists(s)):
        with utils.chdir(ss_dir):
            for ss in glob.glob("*.csv"):
                fc_ids = _get_flowcell_id(ss, require_single)
                for fcid in fc_ids:
                    if fcid:
                        fcid_sheet[fcid] = os.path.join(ss_dir, ss)
    # difflib handles human errors while entering data on the SampleSheet.
    # Only one best candidate is returned (if any). 0.85 cutoff allows for
    # maximum of 2 mismatches in fcid

    potential_fcids = difflib.get_close_matches(fc_name, fcid_sheet.keys(), 1, 0.85)
    if len(potential_fcids) > 0 and fcid_sheet.has_key(potential_fcids[0]):
        return fcid_sheet[potential_fcids[0]]
    else:
        return None

########NEW FILE########
__FILENAME__ = transfer
"""Transfer files from sequencer to remote analysis machine.
"""
import glob
import operator
import os
import subprocess

from bcbio import utils
from bcbio.log import logger

def copy_flowcell(dname, fastq_dir, sample_cfile, config):
    """Copy required files for processing using rsync, potentially to a remote server.
    """
    with utils.chdir(dname):
        reports = reduce(operator.add,
                         [glob.glob("*.xml"),
                          glob.glob("Data/Intensities/BaseCalls/*.xml"),
                          glob.glob("Data/Intensities/BaseCalls/*.xsl"),
                          glob.glob("Data/Intensities/BaseCalls/*.htm"),
                          ["Data/Intensities/BaseCalls/Plots", "Data/reports",
                           "Data/Status.htm", "Data/Status_Files", "InterOp"]])
        run_info = reduce(operator.add,
                          [glob.glob("run_info.yaml"),
                           glob.glob("*.csv")])
        fastq = glob.glob(os.path.join(fastq_dir.replace(dname + "/", "", 1),
                                       "*.gz"))
        configs = [sample_cfile.replace(dname + "/", "", 1)]
    include_file = os.path.join(dname, "transfer_files.txt")
    with open(include_file, "w") as out_handle:
        out_handle.write("+ */\n")
        for fname in configs + fastq + run_info + reports:
            out_handle.write("+ %s\n" % fname)
        out_handle.write("- *\n")
    # remote transfer
    if utils.get_in(config, ("process", "host")):
        dest = "%s@%s:%s" % (utils.get_in(config, ("process", "username")),
                             utils.get_in(config, ("process", "host")),
                             utils.get_in(config, ("process", "dir")))
    # local transfer
    else:
        dest = utils.get_in(config, ("process", "dir"))
    cmd = ["rsync", "-akmrtv", "--include-from=%s" % include_file, dname, dest]
    logger.info("Copying files to analysis machine")
    logger.info(" ".join(cmd))
    subprocess.check_call(cmd)

########NEW FILE########
__FILENAME__ = install
"""Handle installation and updates of bcbio-nextgen, third party software and data.

Enables automated installation tool and in-place updates to install additional
data and software.
"""
import argparse
import collections
import contextlib
import datetime
from distutils.version import LooseVersion
import os
import shutil
import string
import subprocess
import sys

import requests
import yaml

from bcbio import broad, utils
from bcbio.pipeline import genome
from bcbio.variation import effects
from bcbio.provenance import programs

REMOTES = {
    "requirements": "https://raw.github.com/chapmanb/bcbio-nextgen/master/requirements.txt",
    "gitrepo": "git://github.com/chapmanb/bcbio-nextgen.git",
    "cloudbiolinux": "https://github.com/chapmanb/cloudbiolinux.git",
    "genome_resources": "https://raw.github.com/chapmanb/bcbio-nextgen/master/config/genomes/%s-resources.yaml",
    "snpeff_dl_url": ("http://downloads.sourceforge.net/project/snpeff/databases/v{snpeff_ver}/"
                      "snpEff_v{snpeff_ver}_{genome}.zip")}

Tool = collections.namedtuple("Tool", ["name", "fname"])

def upgrade_bcbio(args):
    """Perform upgrade of bcbio to latest release, or from GitHub development version.

    Handles bcbio, third party tools and data.
    """
    args = add_install_defaults(args)
    pip_bin = os.path.join(os.path.dirname(sys.executable), "pip")
    if args.upgrade in ["skip"]:
        pass
    elif args.upgrade in ["stable", "system"]:
        _update_conda_packages()
        print("Upgrading bcbio-nextgen to latest stable version")
        sudo_cmd = [] if args.upgrade == "stable" else ["sudo"]
        subprocess.check_call(sudo_cmd + [pip_bin, "install", "-r", REMOTES["requirements"]])
        print("Upgrade of bcbio-nextgen code complete.")
    else:
        _update_conda_packages()
        print("Upgrading bcbio-nextgen to latest development version")
        subprocess.check_call([pip_bin, "install", "git+%s#egg=bcbio-nextgen" % REMOTES["gitrepo"]])
        subprocess.check_call([pip_bin, "install", "--upgrade", "--no-deps",
                               "git+%s#egg=bcbio-nextgen" % REMOTES["gitrepo"]])
        print("Upgrade of bcbio-nextgen development code complete.")

    if args.tooldir:
        with bcbio_tmpdir():
            print("Upgrading third party tools to latest versions")
            upgrade_thirdparty_tools(args, REMOTES)
            print("Third party tools upgrade complete.")
    if args.install_data:
        with bcbio_tmpdir():
            print("Upgrading bcbio-nextgen data files")
            upgrade_bcbio_data(args, REMOTES)
            print("bcbio-nextgen data upgrade complete.")
    if args.isolate and args.tooldir:
        print("Installation directory not added to current PATH")
        print("  Add {t}/bin to PATH and {t}/lib to LD_LIBRARY_PATH".format(t=args.tooldir))
    save_install_defaults(args)
    args.datadir = _get_data_dir()
    _install_container_bcbio_system(args.datadir)
    print("Upgrade completed successfully.")
    return args

def _install_container_bcbio_system(datadir):
    """Install limited bcbio_system.yaml file for setting core and memory usage.

    Adds any non-specific programs to the exposed bcbio_system.yaml file, only
    when upgrade happening inside a docker container.
    """
    base_file = os.path.join(datadir, "config", "bcbio_system.yaml")
    if not os.path.exists(base_file):
        return
    expose_file = os.path.join(datadir, "galaxy", "bcbio_system.yaml")
    expose = set(["memory", "cores", "jvm_opts"])
    with open(base_file) as in_handle:
        config = yaml.load(in_handle)
    if os.path.exists(expose_file):
        with open(expose_file) as in_handle:
            expose_config = yaml.load(in_handle)
    else:
        expose_config = {"resources": {}}
    for pname, vals in config["resources"].iteritems():
        expose_vals = {}
        for k, v in vals.iteritems():
            if k in expose:
                expose_vals[k] = v
        if len(expose_vals) > 0 and pname not in expose_config["resources"]:
            expose_config["resources"][pname] = expose_vals
    with open(expose_file, "w") as out_handle:
        yaml.safe_dump(expose_config, out_handle, default_flow_style=False, allow_unicode=False)
    return expose_file

def _default_deploy_args(args):
    toolplus = {"data": {"bio_nextgen": []}}
    custom_add = collections.defaultdict(list)
    for x in args.toolplus:
        if not x.fname:
            for k, vs in toolplus.get(x.name, {}).iteritems():
                custom_add[k].extend(vs)
    return {"flavor": "ngs_pipeline_minimal",
            "custom_add": dict(custom_add),
            "vm_provider": "novm",
            "hostname": "localhost",
            "fabricrc_overrides": {"edition": "minimal",
                                   "use_sudo": args.sudo,
                                   "keep_isolated": args.isolate,
                                   "distribution": args.distribution or "__auto__",
                                   "dist_name": "__auto__"}}

def _update_conda_packages():
    """If installed in an anaconda directory, upgrade conda packages.
    """
    conda_bin = os.path.join(os.path.dirname(sys.executable), "conda")
    pkgs = ["biopython", "boto", "cython", "ipython", "lxml", "matplotlib",
            "nose", "numpy", "pandas", "patsy", "pycrypto", "pip", "pysam",
            "pyyaml", "pyzmq", "requests", "scipy", "setuptools", "sqlalchemy",
            "statsmodels", "toolz", "tornado"]
    channels = ["-c", "https://conda.binstar.org/collections/chapmanb/bcbio"]
    if os.path.exists(conda_bin):
        subprocess.check_call([conda_bin, "install", "--yes", "numpy"])
        subprocess.check_call([conda_bin, "install", "--yes"] + channels + pkgs)

def _get_data_dir():
    base_dir = os.path.realpath(os.path.dirname(os.path.dirname(sys.executable)))
    if "anaconda" not in os.path.basename(base_dir) and "virtualenv" not in os.path.basename(base_dir):
        raise ValueError("Cannot update data for bcbio-nextgen not installed by installer.\n"
                         "bcbio-nextgen needs to be installed inside an anaconda environment \n"
                         "located in the same directory as `galaxy` `genomes` and `gemini_data` directories.")
    return os.path.dirname(base_dir)

def upgrade_bcbio_data(args, remotes):
    """Upgrade required genome data files in place.
    """
    data_dir = _get_data_dir()
    s = _default_deploy_args(args)
    s["actions"] = ["setup_biodata"]
    tooldir = args.tooldir or get_defaults()["tooldir"]
    if tooldir:
        s["fabricrc_overrides"]["system_install"] = tooldir
    s["fabricrc_overrides"]["data_files"] = data_dir
    s["fabricrc_overrides"]["galaxy_home"] = os.path.join(data_dir, "galaxy")
    cbl = get_cloudbiolinux(remotes)
    s["genomes"] = _get_biodata(cbl["biodata"], args)
    sys.path.insert(0, cbl["dir"])
    cbl_deploy = __import__("cloudbio.deploy", fromlist=["deploy"])
    cbl_deploy.deploy(s)
    _upgrade_genome_resources(s["fabricrc_overrides"]["galaxy_home"],
                              remotes["genome_resources"])
    _upgrade_snpeff_data(s["fabricrc_overrides"]["galaxy_home"], args, remotes)
    if 'data' in set([x.name for x in args.toolplus]):
        gemini = os.path.join(os.path.dirname(sys.executable), "gemini")
        subprocess.check_call([gemini, "update", "--dataonly"])

def _upgrade_genome_resources(galaxy_dir, base_url):
    """Retrieve latest version of genome resource YAML configuration files.
    """
    for dbkey, ref_file in genome.get_builds(galaxy_dir):
        # Check for a remote genome resources file
        remote_url = base_url % dbkey
        r = requests.get(remote_url)
        if r.status_code == requests.codes.ok:
            local_file = os.path.join(os.path.dirname(ref_file), os.path.basename(remote_url))
            if os.path.exists(local_file):
                with open(local_file) as in_handle:
                    local_config = yaml.load(in_handle)
                remote_config = yaml.load(r.text)
                needs_update = remote_config["version"] > local_config.get("version", 0)
                if needs_update:
                    shutil.move(local_file, local_file + ".old%s" % local_config.get("version", 0))
            else:
                needs_update = True
            if needs_update:
                print("Updating %s genome resources configuration" % dbkey)
                with open(local_file, "w") as out_handle:
                    out_handle.write(r.text)

def _upgrade_snpeff_data(galaxy_dir, args, remotes):
    """Install or upgrade snpEff databases, localized to reference directory.
    """
    for dbkey, ref_file in genome.get_builds(galaxy_dir):
        resource_file = os.path.join(os.path.dirname(ref_file), "%s-resources.yaml" % dbkey)
        if os.path.exists(resource_file):
            with open(resource_file) as in_handle:
                resources = yaml.load(in_handle)
            snpeff_db, snpeff_base_dir = effects.get_db({"genome_resources": resources,
                                                         "reference": {"fasta": {"base": ref_file}}})
            if snpeff_db:
                snpeff_db_dir = os.path.join(snpeff_base_dir, snpeff_db)
                if not os.path.exists(snpeff_db_dir):
                    print("Installing snpEff database %s in %s" % (snpeff_db, snpeff_base_dir))
                    tooldir = args.tooldir or get_defaults()["tooldir"]
                    config = {"resources": {"snpeff": {"jvm_opts": ["-Xms500m", "-Xmx1g"],
                                                       "dir": os.path.join(tooldir, "share", "java", "snpeff")}}}
                    raw_version = programs.java_versioner("snpeff", "snpEff",
                                                          stdout_flag="snpEff version SnpEff")(config)
                    snpeff_version = "".join([x for x in raw_version
                                              if x in set(string.digits + ".")]).replace(".", "_")
                    dl_url = remotes["snpeff_dl_url"].format(snpeff_ver=snpeff_version, genome=snpeff_db)
                    dl_file = os.path.basename(dl_url)
                    with utils.chdir(snpeff_base_dir):
                        subprocess.check_call(["wget", "-c", "-O", dl_file, dl_url])
                        subprocess.check_call(["unzip", dl_file])
                        os.remove(dl_file)
                    dl_dir = os.path.join(snpeff_base_dir, "data", snpeff_db)
                    os.rename(dl_dir, snpeff_db_dir)
                    os.rmdir(os.path.join(snpeff_base_dir, "data"))

def _get_biodata(base_file, args):
    with open(base_file) as in_handle:
        config = yaml.load(in_handle)
    config["install_liftover"] = False
    config["genome_indexes"] = args.aligners
    config["genomes"] = [g for g in config["genomes"] if g["dbkey"] in args.genomes]
    return config

def upgrade_thirdparty_tools(args, remotes):
    """Install and update third party tools used in the pipeline.

    Creates a manifest directory with installed programs on the system.
    """
    s = {"fabricrc_overrides": {"system_install": args.tooldir,
                                "local_install": os.path.join(args.tooldir, "local_install"),
                                "distribution": args.distribution,
                                "use_sudo": args.sudo,
                                "edition": "minimal"}}
    s = _default_deploy_args(args)
    s["actions"] = ["install_biolinux"]
    s["fabricrc_overrides"]["system_install"] = args.tooldir
    s["fabricrc_overrides"]["local_install"] = os.path.join(args.tooldir, "local_install")
    cbl = get_cloudbiolinux(remotes)
    sys.path.insert(0, cbl["dir"])
    cbl_deploy = __import__("cloudbio.deploy", fromlist=["deploy"])
    cbl_deploy.deploy(s)
    manifest_dir = os.path.join(_get_data_dir(), "manifest")
    print("Creating manifest of installed packages in %s" % manifest_dir)
    cbl_manifest = __import__("cloudbio.manifest", fromlist=["manifest"])
    if os.path.exists(manifest_dir):
        for fname in os.listdir(manifest_dir):
            if not fname.startswith("toolplus"):
                os.remove(os.path.join(manifest_dir, fname))
    cbl_manifest.create(manifest_dir, args.tooldir)
    print("Installing additional tools")
    _install_toolplus(args, manifest_dir)

def _install_toolplus(args, manifest_dir):
    """Install additional tools we cannot distribute, updating local manifest.
    """
    toolplus_manifest = os.path.join(manifest_dir, "toolplus-packages.yaml")
    system_config = os.path.join(_get_data_dir(), "galaxy", "bcbio_system.yaml")
    toolplus_dir = os.path.join(_get_data_dir(), "toolplus")
    for tool in args.toolplus:
        if tool.name == "data":
            _install_gemini(args.tooldir, _get_data_dir(), args)
        elif tool.name in set(["gatk", "mutect"]):
            _install_gatk_jar(tool.name, tool.fname, toolplus_manifest, system_config, toolplus_dir)
        elif tool.name in set(["protected"]):  # back compatibility
            pass
        else:
            raise ValueError("Unexpected toolplus argument: %s %s" (tool.name, tool.fname))

def _install_gatk_jar(name, fname, manifest, system_config, toolplus_dir):
    """Install a jar for GATK or associated tools like MuTect.
    """
    if not fname.endswith(".jar"):
        raise ValueError("--toolplus argument for %s expects a jar file: %s" % (name, fname))
    if name == "gatk":
        version = broad.get_gatk_version(fname)
    elif name == "mutect":
        version = broad.get_mutect_version(fname)
    else:
        raise ValueError("Unexpected GATK input: %s" % name)
    store_dir = utils.safe_makedir(os.path.join(toolplus_dir, name, version))
    shutil.copyfile(fname, os.path.join(store_dir, os.path.basename(fname)))
    _update_system_file(system_config, name, {"dir": store_dir})
    _update_manifest(manifest, name, version)

def _update_manifest(manifest_file, name, version):
    """Update the toolplus manifest file with updated name and version
    """
    if os.path.exists(manifest_file):
        with open(manifest_file) as in_handle:
            manifest = yaml.load(in_handle)
    else:
        manifest = {}
    manifest[name] = {"name": name, "version": version}
    with open(manifest_file, "w") as out_handle:
        yaml.safe_dump(manifest, out_handle, default_flow_style=False, allow_unicode=False)

def _update_system_file(system_file, name, new_kvs):
    """Update the bcbio_system.yaml file with new resource information.
    """
    bak_file = system_file + ".bak%s" % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    shutil.copyfile(system_file, bak_file)
    with open(system_file) as in_handle:
        config = yaml.load(in_handle)
    new_rs = {}
    for rname, r_kvs in config.get("resources", {}).iteritems():
        if rname == name:
            for k, v in new_kvs.iteritems():
                r_kvs[k] = v
        new_rs[rname] = r_kvs
    config["resources"] = new_rs
    with open(system_file, "w") as out_handle:
        yaml.safe_dump(config, out_handle, default_flow_style=False, allow_unicode=False)

def _install_gemini(tooldir, datadir, args):
    """Install gemini layered on top of bcbio-nextgen, sharing anaconda framework.
    """
    # check if we have an up to date version, upgrading if needed
    gemini = os.path.join(os.path.dirname(sys.executable), "gemini")
    if os.path.exists(gemini):
        vurl = "https://raw.github.com/arq5x/gemini/master/requirements.txt"
        r = requests.get(vurl)
        for line in r.text.split():
            if line.startswith("gemini=="):
                latest_version = line.split("==")[-1]
        cur_version = subprocess.check_output([gemini, "-v"], stderr=subprocess.STDOUT).strip().split()[-1]
        if LooseVersion(latest_version) > LooseVersion(cur_version):
            subprocess.check_call([gemini, "update"])
    # install from scratch inside existing Anaconda python
    else:
        url = "https://raw.github.com/arq5x/gemini/master/gemini/scripts/gemini_install.py"
        script = os.path.basename(url)
        subprocess.check_call(["wget", "-O", script, url, "--no-check-certificate"])
        cmd = [sys.executable, "-E", script, tooldir, datadir, "--notools", "--nodata", "--sharedpy"]
        if not args.sudo:
            cmd.append("--nosudo")
        subprocess.check_call(cmd)
        os.remove(script)

# ## Store a local configuration file with upgrade details

def _get_install_config():
    """Return the YAML configuration file used to store upgrade information.
    """
    try:
        data_dir = _get_data_dir()
    except ValueError:
        return None
    config_dir = utils.safe_makedir(os.path.join(data_dir, "config"))
    return os.path.join(config_dir, "install-params.yaml")

def save_install_defaults(args):
    """Save installation information to make future upgrades easier.
    """
    install_config = _get_install_config()
    if install_config is None:
        return
    if utils.file_exists(install_config):
        with open(install_config) as in_handle:
            cur_config = yaml.load(in_handle)
    else:
        cur_config = {}
    if args.tooldir:
        cur_config["tooldir"] = args.tooldir
    cur_config["sudo"] = args.sudo
    cur_config["isolate"] = args.isolate
    for attr in ["genomes", "aligners"]:
        if not cur_config.get(attr):
            cur_config[attr] = []
        for x in getattr(args, attr):
            if x not in cur_config[attr]:
                cur_config[attr].append(x)
    # toolplus -- save non-filename inputs
    attr = "toolplus"
    if not cur_config.get(attr):
        cur_config[attr] = []
    for x in getattr(args, attr):
        if not x.fname:
            if x.name not in cur_config[attr]:
                cur_config[attr].append(x.name)
    with open(install_config, "w") as out_handle:
        yaml.safe_dump(cur_config, out_handle, default_flow_style=False, allow_unicode=False)

def add_install_defaults(args):
    """Add any saved installation defaults to the upgrade.
    """
    install_config = _get_install_config()
    if install_config is None or not utils.file_exists(install_config):
        return args
    with open(install_config) as in_handle:
        default_args = yaml.load(in_handle)
    if args.tools and args.tooldir is None:
        if "tooldir" in default_args:
            args.tooldir = str(default_args["tooldir"])
        else:
            raise ValueError("Default tool directory not yet saved in config defaults. "
                             "Specify the '--tooldir=/path/to/tools' to upgrade tools. "
                             "After a successful upgrade, the '--tools' parameter will "
                             "work for future upgrades.")
    for attr in ["genomes", "aligners", "toolplus"]:
        for x in default_args.get(attr, []):
            x = Tool(x, None) if attr == "toolplus" else str(x)
            new_val = getattr(args, attr)
            if x not in getattr(args, attr):
                new_val.append(x)
            setattr(args, attr, new_val)
    if "sudo" in default_args and not args.sudo is False:
        args.sudo = default_args["sudo"]
    if "isolate" in default_args and not args.isolate is True:
        args.isolate = default_args["isolate"]
    return args

def get_defaults():
    install_config = _get_install_config()
    if install_config is None or not utils.file_exists(install_config):
        return {}
    with open(install_config) as in_handle:
        return yaml.load(in_handle)

def _check_toolplus(x):
    """Parse options for adding non-standard/commercial tools like GATK and MuTecT.
    """
    std_choices = set(["data"])
    if x in std_choices:
        return Tool(x, None)
    elif "=" in x and len(x.split("=")) == 2:
        name, fname = x.split("=")
        fname = os.path.normpath(os.path.realpath(fname))
        if not os.path.exists(fname):
            raise argparse.ArgumentTypeError("Unexpected --toolplus argument for %s. File does not exist: %s"
                                             % (name, fname))
        return Tool(name, fname)
    else:
        raise argparse.ArgumentTypeError("Unexpected --toolplus argument. Expect toolname=filename.")

def add_subparser(subparsers):
    parser = subparsers.add_parser("upgrade", help="Install or upgrade bcbio-nextgen")
    parser.add_argument("--tooldir",
                        help="Directory to install 3rd party software tools. Leave unspecified for no tools",
                        type=lambda x: (os.path.abspath(os.path.expanduser(x))), default=None)
    parser.add_argument("--tools",
                        help="Boolean argument specifying upgrade of tools. Uses previously saved install directory",
                        action="store_true", default=False)
    parser.add_argument("-u", "--upgrade", help="Code version to upgrade",
                        choices=["stable", "development", "system", "skip"], default="skip")
    parser.add_argument("--toolplus", help="Specify additional tool categories to install",
                        action="append", default=[], type=_check_toolplus)
    parser.add_argument("--genomes", help="Genomes to download",
                        action="append", default=["GRCh37"],
                        choices=["GRCh37", "hg19", "mm10", "mm9", "rn5", "canFam3", "dm3", "Zv9", "phix"])
    parser.add_argument("--aligners", help="Aligner indexes to download",
                        action="append", default=["bwa", "bowtie2"],
                        choices=["bowtie", "bowtie2", "bwa", "novoalign", "star", "ucsc"])
    parser.add_argument("--data", help="Upgrade data dependencies",
                        dest="install_data", action="store_true", default=False)
    parser.add_argument("--nosudo", help="Specify we cannot use sudo for commands",
                        dest="sudo", action="store_false", default=True)
    parser.add_argument("--isolate", help="Created an isolated installation without PATH updates",
                        dest="isolate", action="store_true", default=False)
    parser.add_argument("--distribution", help="Operating system distribution",
                        default="",
                        choices=["ubuntu", "debian", "centos", "scientificlinux", "macosx"])
    return parser

def get_cloudbiolinux(remotes):
    base_dir = os.path.join(os.getcwd(), "cloudbiolinux")
    if not os.path.exists(base_dir):
        subprocess.check_call(["git", "clone", remotes["cloudbiolinux"]])
    return {"biodata": os.path.join(base_dir, "config", "biodata.yaml"),
            "dir": base_dir}

@contextlib.contextmanager
def bcbio_tmpdir():
    orig_dir = os.getcwd()
    work_dir = os.path.join(os.getcwd(), "tmpbcbio-install")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    os.chdir(work_dir)
    yield work_dir
    os.chdir(orig_dir)
    shutil.rmtree(work_dir)

########NEW FILE########
__FILENAME__ = logbook_zmqpush
"""Enable multiple processes to send logs to a central server through ZeroMQ.

Thanks to Zachary Voase: https://github.com/zacharyvoase/logbook-zmqpush
Slightly modified to support Logbook 0.4.1.
"""
import errno
import json
import socket

import zmq
import logbook.queues
from logbook.base import LogRecord

class ZeroMQPushHandler(logbook.queues.ZeroMQHandler):

    """
    A handler that pushes JSON log records over a ZMQ socket.

    Specifically, this handler opens a ``zmq.PUSH`` socket and connects to a
    ``zmq.PULL`` socket at the specified address. You can use
    :class:`ZeroMQPullSubscriber` to receive the log record.

    Example:

        >>> import logbook
        >>> handler = ZeroMQPushHandler('tcp://127.0.0.1:5501')
        >>> with handler.applicationbound():
        ...     logbook.debug("Something happened")

    Switch off hostname injection with `hostname=False`:

        >>> handler = ZeroMQPushHandler('tcp://127.0.0.1:5501', hostname=False)
        >>> with handler.applicationbound():
        ...     logbook.debug("No hostname info")
    """

    def __init__(self, addr=None, level=logbook.NOTSET, filter=None,
                 bubble=False, context=None, hostname=True):
        logbook.Handler.__init__(self, level, filter, bubble)

        self.hostname = hostname
        if context is None:
            context = zmq.Context()
            self._context = context
        else:
            self._context = None
        self.socket = context.socket(zmq.PUSH)
        if addr is not None:
            self.socket.connect(addr)

    def emit(self, record):
        if self.hostname:
            inject_hostname.process(record)
        return super(ZeroMQPushHandler, self).emit(record)

    def close(self):
        if self._context:
            self._context.destroy(linger=0)
        self.socket.close(linger=0)

class ZeroMQPullSubscriber(logbook.queues.ZeroMQSubscriber):

    """
    A subscriber which listens on a PULL socket for log records.

    This subscriber opens a ``zmq.PULL`` socket and binds to the specified
    address. You should probably use this in conjunction with
    :class:`ZeroMQPushHandler`.

    Example:

        >>> subscriber = ZeroMQPullSubscriber('tcp://*:5501')
        >>> log_record = subscriber.recv()
    """

    def __init__(self, addr=None, context=None):
        self._zmq = zmq
        self.context = context or zmq.Context.instance()
        self.socket = self.context.socket(zmq.PULL)
        if addr is not None:
            self.socket.bind(addr)

    def recv(self, timeout=None):
        """Overwrite standard recv for timeout calls to catch interrupt errors.
        """
        if timeout:
            try:
                testsock = self._zmq.select([self.socket], [], [], timeout)[0]
            except zmq.ZMQError as e:
                if e.errno == errno.EINTR:
                    testsock = None
                else:
                    raise
            if not testsock:
                return
            rv = self.socket.recv(self._zmq.NOBLOCK)
            return LogRecord.from_dict(json.loads(rv))
        else:
            return super(ZeroMQPullSubscriber, self).recv(timeout)

@logbook.Processor
def inject_hostname(log_record):
    """A Logbook processor to inject the current hostname into log records."""
    log_record.extra['source'] = socket.gethostname()

def inject(**params):

    """
    A Logbook processor to inject arbitrary information into log records.

    Simply pass in keyword arguments and use as a context manager:

        >>> with inject(identifier=str(uuid.uuid4())).applicationbound():
        ...     logger.debug('Something happened')
    """

    def callback(log_record):
        log_record.extra.update(params)
    return logbook.Processor(callback)

########NEW FILE########
__FILENAME__ = alignprep
"""Prepare read inputs (fastq, gzipped fastq and BAM) for parallel NGS alignment.
"""
import collections
import copy
import os
import shutil
import subprocess

import toolz as tz
try:
    import pybedtools
except ImportError:
    pybedtools = None

from bcbio import bam, utils
from bcbio.bam import cram
from bcbio.log import logger
from bcbio.distributed.multi import run_multicore, zeromq_aware_logging
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, tools
from bcbio.provenance import do

def create_inputs(data):
    """Index input reads and prepare groups of reads to process concurrently.

    Allows parallelization of alignment beyond processors available on a single
    machine. Uses gbzip and grabix to prepare an indexed fastq file.
    """
    # CRAM files must be converted to bgzipped fastq
    if not ("files" in data and _is_cram_input(data["files"])):
        # skip indexing on samples without input files or not doing alignment
        if ("files" not in data or data["files"][0] is None or
              data["config"]["algorithm"].get("align_split_size") is None
              or not data["config"]["algorithm"].get("aligner")):
            return [[data]]
    ready_files = _prep_grabix_indexes(data["files"], data["dirs"], data)
    data["files"] = ready_files
    # bgzip preparation takes care of converting illumina into sanger format
    data["config"]["algorithm"]["quality_format"] = "standard"
    if tz.get_in(["config", "algorithm", "align_split_size"], data):
        splits = _find_read_splits(ready_files[0], data["config"]["algorithm"]["align_split_size"])
    else:
        splits = [None]
    if len(splits) == 1:
        return [[data]]
    else:
        out = []
        for split in splits:
            cur_data = copy.deepcopy(data)
            cur_data["align_split"] = list(split)
            out.append([cur_data])
        return out

def split_namedpipe_cl(in_file, data):
    """Create a commandline suitable for use as a named pipe with reads in a given region.
    """
    grabix = config_utils.get_program("grabix", data["config"])
    start, end = data["align_split"]
    return "<({grabix} grab {in_file} {start} {end})".format(**locals())

def fastq_convert_pipe_cl(in_file, data):
    """Create an anonymous pipe converting Illumina 1.3-1.7 to Sanger.

    Uses seqtk: https://github.com/lh3/seqt
    """
    seqtk = config_utils.get_program("seqtk", data["config"])
    return "<({seqtk} seq -Q64 -V {in_file})".format(**locals())

# ## configuration

def parallel_multiplier(items):
    """Determine if we will be parallelizing items during processing.
    """
    multiplier = 1
    for data in (x[0] for x in items):
        if data["config"]["algorithm"].get("align_split_size"):
            multiplier += 50
    return multiplier

# ## merge

def setup_combine(final_file, data):
    """Setup the data and outputs to allow merging data back together.
    """
    align_dir = os.path.dirname(final_file)
    base, ext = os.path.splitext(os.path.basename(final_file))
    start, end = data["align_split"]
    out_file = os.path.join(utils.safe_makedir(os.path.join(align_dir, "split")),
                            "%s-%s_%s%s" % (base, start, end, ext))
    data["combine"] = {"work_bam": {"out": final_file, "extras": []}}
    return out_file, data

def merge_split_alignments(samples, run_parallel):
    """Manage merging split alignments back into a final working BAM file.
    """
    ready = []
    file_key = "work_bam"
    to_merge = collections.defaultdict(list)
    for data in (xs[0] for xs in samples):
        if data.get("combine"):
            to_merge[data["combine"][file_key]["out"]].append(data)
        else:
            ready.append([data])
    ready_merge = []
    for mgroup in to_merge.itervalues():
        cur_data = mgroup[0]
        del cur_data["align_split"]
        for x in mgroup[1:]:
            cur_data["combine"][file_key]["extras"].append(x[file_key])
        ready_merge.append([cur_data])
    merged = run_parallel("delayed_bam_merge", ready_merge)
    return merged + ready

# ## determine file sections

def _find_read_splits(in_file, split_size):
    """Determine sections of fastq files to process in splits.

    Assumes a 4 line order to input files (name, read, name, quality).
    grabix is 1-based inclusive, so return coordinates in that format.
    """
    gbi_file = in_file + ".gbi"
    with open(gbi_file) as in_handle:
        in_handle.next()  # throw away
        num_lines = int(in_handle.next().strip())
    assert num_lines % 4 == 0, "Expected lines to be multiple of 4"
    split_lines = split_size * 4
    chunks = []
    last = 1
    for chunki in range(num_lines // split_lines + min(1, num_lines % split_lines)):
        new = last + split_lines - 1
        chunks.append((last, min(new, num_lines - 1)))
        last = new
        if chunki > 0:
            last += 1
    return chunks

# ## bgzip and grabix

def _is_bam_input(in_files):
    return in_files[0].endswith(".bam") and (len(in_files) == 1 or in_files[1] is None)

def _is_cram_input(in_files):
    return in_files[0].endswith(".cram") and (len(in_files) == 1 or in_files[1] is None)

def _prep_grabix_indexes(in_files, dirs, data):
    if _is_bam_input(in_files):
        out = _bgzip_from_bam(in_files[0], dirs, data["config"])
    elif _is_cram_input(in_files):
        out = _bgzip_from_cram(in_files[0], dirs, data)
    else:
        out = run_multicore(_bgzip_from_fastq,
                            [[{"in_file": x, "dirs": dirs, "config": data["config"]}] for x in in_files if x],
                            data["config"])
    items = [[{"bgzip_file": x, "config": copy.deepcopy(data["config"])}] for x in out if x]
    run_multicore(_grabix_index, items, data["config"])
    return out

def _bgzip_from_cram(cram_file, dirs, data):
    """Create bgzipped fastq files from an input CRAM file in regions of interest.

    Returns a list with a single file, for single end CRAM files, or two
    files for paired end input.
    """
    region_file = (tz.get_in(["config", "algorithm", "variant_regions"], data)
                   if tz.get_in(["config", "algorithm", "coverage_interval"], data) in ["regional", "exome"]
                   else None)
    if region_file:
        regions = ["%s:%s-%s" % tuple(r) for r in pybedtools.BedTool(region_file)]
    else:
        regions = [None]
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "align_prep"))
    out_s, out_p1, out_p2 = [os.path.join(work_dir, "%s-%s.fq.gz" %
                                          (utils.splitext_plus(os.path.basename(cram_file))[0], fext))
                             for fext in ["s1", "p1", "p2"]]
    if (not utils.file_exists(out_s) and
          (not utils.file_exists(out_p1) or not utils.file_exists(out_p2))):
        cram.index(cram_file)
        fastqs, part_dir = _cram_to_fastq_regions(regions, cram_file, dirs, data)
        if len(fastqs[0]) == 1:
            with file_transaction(out_s) as tx_out_file:
                _merge_and_bgzip([xs[0] for xs in fastqs], tx_out_file, out_s)
        else:
            for i, out_file in enumerate([out_p1, out_p2]):
                if not utils.file_exists(out_file):
                    ext = "/%s" % (i + 1)
                    with file_transaction(out_file) as tx_out_file:
                        _merge_and_bgzip([xs[i] for xs in fastqs], tx_out_file, out_file, ext)
        shutil.rmtree(part_dir)
    if utils.file_exists(out_p1):
        return [out_p1, out_p2]
    else:
        assert utils.file_exists(out_s)
        return [out_s]

def _merge_and_bgzip(orig_files, out_file, base_file, ext=""):
    """Merge a group of gzipped input files into a final bgzipped output.

    Also handles providing unique names for each input file to avoid
    collisions on multi-region output. Handles renaming with awk magic from:
    https://www.biostars.org/p/68477/
    """
    assert out_file.endswith(".gz")
    full_file = out_file.replace(".gz", "")
    run_file = "%s-merge.bash" % utils.splitext_plus(base_file)[0]

    cmds = ["set -e\n"]
    for i, fname in enumerate(orig_files):
        cmd = ("""zcat %s | awk '{print (NR%%4 == 1) ? "@%s_" ++i "%s" : $0}' >> %s\n"""
               % (fname, i, ext, full_file))
        cmds.append(cmd)
    cmds.append("bgzip -f %s\n" % full_file)

    with open(run_file, "w") as out_handle:
        out_handle.write("".join("".join(cmds)))
    do.run([do.find_bash(), run_file], "Rename, merge and bgzip CRAM fastq output")
    assert os.path.exists(out_file) and not _is_gzip_empty(out_file)

def _cram_to_fastq_regions(regions, cram_file, dirs, data):
    """Convert CRAM files to fastq, potentially within sub regions.

    Returns multiple fastq files that can be merged back together.
    """
    base_name = utils.splitext_plus(os.path.basename(cram_file))[0]
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "align_prep",
                                               "%s-parts" % base_name))
    fnames = run_multicore(_cram_to_fastq_region,
                           [(cram_file, work_dir, base_name, region, data) for region in regions],
                           data["config"])
    # check if we have paired or single end data
    if any(not _is_gzip_empty(p1) for p1, p2, s in fnames):
        out = [[p1, p2] for p1, p2, s in fnames]
    else:
        out = [[s] for p1, p2, s in fnames]
    return out, work_dir

@utils.map_wrap
@zeromq_aware_logging
def _cram_to_fastq_region(cram_file, work_dir, base_name, region, data):
    """Convert CRAM to fastq in a specified region.
    """
    ref_file = tz.get_in(["reference", "fasta", "base"], data)
    resources = config_utils.get_resources("bamtofastq", data["config"])
    cores = tz.get_in(["config", "algorithm", "num_cores"], data, 1)
    max_mem = int(resources.get("memory", "1073741824")) * cores  # 1Gb/core default
    rext = "-%s" % region.replace(":", "_").replace("-", "_") if region else "full"
    out_s, out_p1, out_p2 = [os.path.join(work_dir, "%s%s-%s.fq.gz" %
                                          (base_name, rext, fext))
                             for fext in ["s1", "p1", "p2"]]
    if not utils.file_exists(out_p1):
        with file_transaction(out_s, out_p1, out_p2) as (tx_out_s, tx_out_p1, tx_out_p2):
            sortprefix = "%s-sort" % utils.splitext_plus(tx_out_s)[0]
            cmd = ("bamtofastq filename={cram_file} inputformat=cram T={sortprefix} "
                   "gz=1 collate=1 colsbs={max_mem} "
                   "F={tx_out_p1} F2={tx_out_p2} S={tx_out_s} O=/dev/null O2=/dev/null "
                   "reference={ref_file}")
            if region:
                cmd += " ranges='{region}'"
            do.run(cmd.format(**locals()), "CRAM to fastq %s" % region if region else "")
    return [[out_p1, out_p2, out_s]]

def _is_gzip_empty(fname):
    count = subprocess.check_output("zcat %s | head -1 | wc -l" % fname, shell=True,
                                    stderr=open("/dev/null", "w"))
    return int(count) < 1

def _bgzip_from_bam(bam_file, dirs, config, is_retry=False):
    """Create bgzipped fastq files from an input BAM file.
    """
    # tools
    bamtofastq = config_utils.get_program("bamtofastq", config)
    resources = config_utils.get_resources("bamtofastq", config)
    cores = config["algorithm"].get("num_cores", 1)
    max_mem = int(resources.get("memory", "1073741824")) * cores  # 1Gb/core default
    bgzip = tools.get_bgzip_cmd(config, is_retry)
    # files
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "align_prep"))
    out_file_1 = os.path.join(work_dir, "%s-1.fq.gz" % os.path.splitext(os.path.basename(bam_file))[0])
    if bam.is_paired(bam_file):
        out_file_2 = out_file_1.replace("-1.fq.gz", "-2.fq.gz")
    else:
        out_file_2 = None
    needs_retry = False
    if is_retry or not utils.file_exists(out_file_1):
        with file_transaction(out_file_1) as tx_out_file:
            for f in [tx_out_file, out_file_1, out_file_2]:
                if f and os.path.exists(f):
                    os.remove(f)
            fq1_bgzip_cmd = "%s -c /dev/stdin > %s" % (bgzip, tx_out_file)
            sortprefix = "%s-sort" % os.path.splitext(tx_out_file)[0]
            if bam.is_paired(bam_file):
                fq2_bgzip_cmd = "%s -c /dev/stdin > %s" % (bgzip, out_file_2)
                out_str = ("F=>({fq1_bgzip_cmd}) F2=>({fq2_bgzip_cmd}) S=/dev/null O=/dev/null "
                           "O2=/dev/null collate=1 colsbs={max_mem}")
            else:
                out_str = "S=>({fq1_bgzip_cmd})"
            cmd = "{bamtofastq} filename={bam_file} T={sortprefix} " + out_str
            try:
                do.run(cmd.format(**locals()), "BAM to bgzipped fastq",
                       checks=[do.file_reasonable_size(tx_out_file, bam_file)],
                       log_error=False)
            except subprocess.CalledProcessError, msg:
                if not is_retry and "deflate failed" in str(msg):
                    logger.info("bamtofastq deflate IO failure preparing %s. Retrying with single core."
                                % (bam_file))
                    needs_retry = True
                else:
                    logger.exception()
                    raise
    if needs_retry:
        return _bgzip_from_bam(bam_file, dirs, config, is_retry=True)
    else:
        return [x for x in [out_file_1, out_file_2] if x is not None]

@utils.map_wrap
@zeromq_aware_logging
def _grabix_index(data):
    in_file = data["bgzip_file"]
    config = data["config"]
    grabix = config_utils.get_program("grabix", config)
    gbi_file = in_file + ".gbi"
    if not utils.file_exists(gbi_file) or _is_partial_index(gbi_file):
        do.run([grabix, "index", in_file], "Index input with grabix: %s" % os.path.basename(in_file))
    return [gbi_file]

def _is_partial_index(gbi_file):
    """Check for truncated output since grabix doesn't write to a transactional directory.
    """
    with open(gbi_file) as in_handle:
        for i, _ in enumerate(in_handle):
            if i > 2:
                return False
    return True

@utils.map_wrap
@zeromq_aware_logging
def _bgzip_from_fastq(data):
    """Prepare a bgzipped file from a fastq input, potentially gzipped (or bgzipped already).
    """
    in_file = data["in_file"]
    config = data["config"]
    grabix = config_utils.get_program("grabix", config)
    needs_convert = config["algorithm"].get("quality_format", "").lower() == "illumina"
    if in_file.endswith(".gz"):
        needs_bgzip, needs_gunzip = _check_gzipped_input(in_file, grabix, needs_convert)
    else:
        needs_bgzip, needs_gunzip = True, False
    if needs_bgzip or needs_gunzip or needs_convert:
        out_file = _bgzip_file(in_file, data["dirs"], config, needs_bgzip, needs_gunzip,
                               needs_convert)
    else:
        out_file = in_file
    return [out_file]

def _bgzip_file(in_file, dirs, config, needs_bgzip, needs_gunzip, needs_convert):
    """Handle bgzip of input file, potentially gunzipping an existing file.
    """
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "align_prep"))
    out_file = os.path.join(work_dir, os.path.basename(in_file) +
                            (".gz" if not in_file.endswith(".gz") else ""))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            assert needs_bgzip
            bgzip = tools.get_bgzip_cmd(config)
            if needs_convert:
                in_file = fastq_convert_pipe_cl(in_file, {"config": config})
            if needs_gunzip:
                gunzip_cmd = "gunzip -c {in_file} |".format(**locals())
                bgzip_in = "/dev/stdin"
            else:
                gunzip_cmd = ""
                bgzip_in = in_file
            do.run("{gunzip_cmd} {bgzip} -c {bgzip_in} > {tx_out_file}".format(**locals()),
                   "bgzip input file")
    return out_file

def _check_gzipped_input(in_file, grabix, needs_convert):
    """Determine if a gzipped input file is blocked gzip or standard.
    """
    is_bgzip = subprocess.check_output([grabix, "check", in_file])
    if is_bgzip.strip() == "yes" and not needs_convert:
        return False, False
    else:
        return True, True

########NEW FILE########
__FILENAME__ = bowtie
"""Next gen sequence alignments with Bowtie (http://bowtie-bio.sourceforge.net).
"""
import os

from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.provenance import do

galaxy_location_file = "bowtie_indices.loc"

def _bowtie_args_from_config(config):
    """Configurable high level options for bowtie.
    """
    qual_format = config["algorithm"].get("quality_format", None)
    if qual_format is None or qual_format.lower() == "illumina":
        qual_flags = ["--phred64-quals"]
    else:
        qual_flags = []
    multi_mappers = config["algorithm"].get("multiple_mappers", True)
    multi_flags = ["-M", 1] if multi_mappers else ["-m", 1]
    cores = config.get("resources", {}).get("bowtie", {}).get("cores", None)
    num_cores = config["algorithm"].get("num_cores", 1)
    core_flags = ["-p", str(num_cores)] if num_cores > 1 else []
    return core_flags + qual_flags + multi_flags

def align(fastq_file, pair_file, ref_file, names, align_dir, data,
          extra_args=None):
    """Do standard or paired end alignment with bowtie.
    """
    config = data['config']
    out_file = os.path.join(align_dir, "%s.sam" % names["lane"])
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("bowtie", config)]
            cl += _bowtie_args_from_config(config)
            cl += extra_args if extra_args is not None else []
            cl += ["-q",
                   "-v", 2,
                   "-k", 1,
                   "-X", 2000, # default is too selective for most data
                   "--best",
                   "--strata",
                   "--sam",
                   ref_file]
            if pair_file:
                cl += ["-1", fastq_file, "-2", pair_file]
            else:
                cl += [fastq_file]
            cl += [tx_out_file]
            cl = [str(i) for i in cl]
            do.run(cl, "Running Bowtie on %s and %s." % (fastq_file, pair_file), None)
    return out_file

########NEW FILE########
__FILENAME__ = bowtie2
"""Next gen sequence alignments with Bowtie2.

http://bowtie-bio.sourceforge.net/bowtie2/index.shtml
"""
import os
from itertools import ifilter, imap
import pysam
import sys

from bcbio.pipeline import config_utils
from bcbio.utils import file_exists, compose
from bcbio.distributed.transaction import file_transaction
from bcbio.provenance import do
from bcbio import bam



def _bowtie2_args_from_config(config):
    """Configurable high level options for bowtie2.
    """
    qual_format = config["algorithm"].get("quality_format", "")
    if qual_format.lower() == "illumina":
        qual_flags = ["--phred64-quals"]
    else:
        qual_flags = []
    num_cores = config["algorithm"].get("num_cores", 1)
    core_flags = ["-p", str(num_cores)] if num_cores > 1 else []
    return core_flags + qual_flags

def align(fastq_file, pair_file, ref_file, names, align_dir, data,
          extra_args=None):
    """Alignment with bowtie2.
    """
    config = data["config"]
    analysis_config = ANALYSIS.get(data["analysis"])
    assert analysis_config, "Analysis %s is not supported by bowtie2" % (data["analysis"])
    out_file = os.path.join(align_dir, "%s.sam" % names["lane"])
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("bowtie2", config)]
            cl += _bowtie2_args_from_config(config)
            cl += extra_args if extra_args is not None else []
            cl += ["-q",
                   "-x", ref_file]
            cl += analysis_config.get("params", [])
            if pair_file:
                cl += ["-1", fastq_file, "-2", pair_file]
            else:
                cl += ["-U", fastq_file]
            cl += ["-S", tx_out_file]
            cl = [str(i) for i in cl]
            do.run(cl, "Aligning %s and %s with Bowtie2." % (fastq_file, pair_file),
                   None)
    return out_file

# Optional galaxy location file. Falls back on remap_index_fn if not found
galaxy_location_file = "bowtie2_indices.loc"

def remap_index_fn(ref_file):
    """Map sequence references to equivalent bowtie2 indexes.
    """
    return os.path.splitext(ref_file)[0].replace("/seq/", "/bowtie2/")


def filter_multimappers(align_file):
    """
    It does not seem like bowtie2 has a corollary to the -m 1 flag in bowtie,
    there are some options that are close but don't do the same thing. Bowtie2
    sets the XS flag for reads mapping in more than one place, so we can just
    filter on that. This will not work for other aligners.
    """
    type_flag = "b" if bam.is_bam(align_file) else ""
    base, ext = os.path.splitext(align_file)
    align_handle = pysam.Samfile(align_file, "r" + type_flag)
    tmp_out_file = os.path.splitext(align_file)[0] + ".tmp"
    def keep_fn(read):
        return _is_properly_mapped(read) and _is_unique(read)
    keep = ifilter(keep_fn, align_handle)
    with pysam.Samfile(tmp_out_file, "w" + type_flag, template=align_handle) as out_handle:
        for read in keep:
            out_handle.write(read)
    align_handle.close()
    out_handle.close()
    os.rename(tmp_out_file, align_file)
    return align_file

def _is_properly_mapped(read):
    if read.is_paired and not read.is_proper_pair:
        return False
    if read.is_unmapped:
        return False
    return True

def _is_unique(read):
    tags = [x[0] for x in read.tags]
    return "XS" not in tags


ANALYSIS = {"chip-seq": {"params": ["-X", 2000]},
            "RNA-seq": {"params": ["--sensitive", "-X", 2000]}}

########NEW FILE########
__FILENAME__ = bwa
"""Next-gen alignments with BWA (http://bio-bwa.sourceforge.net/)
"""
import os
import subprocess

from bcbio.pipeline import config_utils
from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.ngsalign import alignprep, novoalign, postalign
from bcbio.provenance import do

galaxy_location_file = "bwa_index.loc"

def align_bam(in_bam, ref_file, names, align_dir, data):
    """Perform direct alignment of an input BAM file with BWA using pipes.

    This avoids disk IO by piping between processes:
     - samtools sort of input BAM to queryname
     - bedtools conversion to interleaved FASTQ
     - bwa-mem alignment
     - samtools conversion to BAM
     - samtools sort to coordinate
    """
    config = data["config"]
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    samtools = config_utils.get_program("samtools", config)
    bedtools = config_utils.get_program("bedtools", config)
    bwa = config_utils.get_program("bwa", config)
    resources = config_utils.get_resources("samtools", config)
    num_cores = config["algorithm"].get("num_cores", 1)
    # adjust memory for samtools since used for input and output
    max_mem = config_utils.adjust_memory(resources.get("memory", "1G"),
                                         3, "decrease").upper()
    rg_info = novoalign.get_rg_info(names)
    if not utils.file_exists(out_file):
        with utils.curdir_tmpdir(data) as work_dir:
            with postalign.tobam_cl(data, out_file, bam.is_paired(in_bam)) as (tobam_cl, tx_out_file):
                tx_out_prefix = os.path.splitext(tx_out_file)[0]
                prefix1 = "%s-in1" % tx_out_prefix
                cmd = ("{samtools} sort -n -o -l 0 -@ {num_cores} -m {max_mem} {in_bam} {prefix1} "
                       "| {bedtools} bamtofastq -i /dev/stdin -fq /dev/stdout -fq2 /dev/stdout "
                       "| {bwa} mem -p -M -t {num_cores} -R '{rg_info}' -v 1 {ref_file} - | ")
                cmd = cmd.format(**locals()) + tobam_cl
                do.run(cmd, "bwa mem alignment from BAM: %s" % names["sample"], None,
                       [do.file_nonempty(tx_out_file), do.file_reasonable_size(tx_out_file, in_bam)])
    return out_file

def _can_use_mem(fastq_file, data):
    """bwa-mem handle longer (> 70bp) reads with improved piping.
    Randomly samples 5000 reads from the first two million.
    Default to no piping if more than 75% of the sampled reads are small.
    """
    min_size = 70
    thresh = 0.75
    head_count = 8000000
    tocheck = 5000
    seqtk = config_utils.get_program("seqtk", data["config"])
    gzip_cmd = "zcat {fastq_file}" if fastq_file.endswith(".gz") else "cat {fastq_file}"
    cmd = (gzip_cmd + " | head -n {head_count} | "
           "{seqtk} sample -s42 - {tocheck} | "
           "awk '{{if(NR%4==2) print length($1)}}' | sort | uniq -c")
    count_out = subprocess.check_output(cmd.format(**locals()), shell=True,
                                        executable="/bin/bash", stderr=open("/dev/null", "w"))
    if not count_out.strip():
        raise IOError("Failed to check fastq file sizes with: %s" % cmd.format(**locals()))
    shorter = 0
    for count, size in (l.strip().split() for l in count_out.strip().split("\n")):
        if int(size) < min_size:
            shorter += int(count)
    return (float(shorter) / float(tocheck)) <= thresh

def align_pipe(fastq_file, pair_file, ref_file, names, align_dir, data):
    """Perform piped alignment of fastq input files, generating sorted output BAM.
    """
    pair_file = pair_file if pair_file else ""
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    qual_format = data["config"]["algorithm"].get("quality_format", "").lower()
    if data.get("align_split"):
        final_file = out_file
        out_file, data = alignprep.setup_combine(final_file, data)
        fastq_file = alignprep.split_namedpipe_cl(fastq_file, data)
        if pair_file:
            pair_file = alignprep.split_namedpipe_cl(pair_file, data)
    else:
        final_file = None
        if qual_format == "illumina":
            fastq_file = alignprep.fastq_convert_pipe_cl(fastq_file, data)
            if pair_file:
                pair_file = alignprep.fastq_convert_pipe_cl(pair_file, data)
    rg_info = novoalign.get_rg_info(names)
    if not utils.file_exists(out_file) and (final_file is None or not utils.file_exists(final_file)):
        # If we cannot do piping, use older bwa aln approach
        if not _can_use_mem(fastq_file, data):
            out_file = _align_backtrack(fastq_file, pair_file, ref_file, out_file,
                                        names, rg_info, data)
        else:
            out_file = _align_mem(fastq_file, pair_file, ref_file, out_file,
                                  names, rg_info, data)
    data["work_bam"] = out_file
    return data

def _align_mem(fastq_file, pair_file, ref_file, out_file, names, rg_info, data):
    """Perform bwa-mem alignment on supported read lengths.
    """
    bwa = config_utils.get_program("bwa", data["config"])
    num_cores = data["config"]["algorithm"].get("num_cores", 1)
    with utils.curdir_tmpdir(data) as work_dir:
        with postalign.tobam_cl(data, out_file, pair_file != "") as (tobam_cl, tx_out_file):
            cmd = ("{bwa} mem -M -t {num_cores} -R '{rg_info}' -v 1 {ref_file} "
                   "{fastq_file} {pair_file} | ")
            cmd = cmd.format(**locals()) + tobam_cl
            do.run(cmd, "bwa mem alignment from fastq: %s" % names["sample"], None,
                   [do.file_nonempty(tx_out_file), do.file_reasonable_size(tx_out_file, fastq_file)])
    return out_file

def _align_backtrack(fastq_file, pair_file, ref_file, out_file, names, rg_info, data):
    """Perform a BWA alignment using 'aln' backtrack algorithm.
    """
    assert not data.get("align_split"), "Do not handle split alignments with non-piped bwa"
    bwa = config_utils.get_program("bwa", data["config"])
    config = data["config"]
    sai1_file = "%s_1.sai" % os.path.splitext(out_file)[0]
    sai2_file = "%s_2.sai" % os.path.splitext(out_file)[0] if pair_file else ""
    if not utils.file_exists(sai1_file):
        with file_transaction(sai1_file) as tx_sai1_file:
            _run_bwa_align(fastq_file, ref_file, tx_sai1_file, config)
    if sai2_file and not utils.file_exists(sai2_file):
        with file_transaction(sai2_file) as tx_sai2_file:
            _run_bwa_align(pair_file, ref_file, tx_sai2_file, config)
    with postalign.tobam_cl(data, out_file, pair_file != "") as (tobam_cl, tx_out_file):
        align_type = "sampe" if sai2_file else "samse"
        cmd = ("{bwa} {align_type} -r '{rg_info}' {ref_file} {sai1_file} {sai2_file} "
               "{fastq_file} {pair_file} | ")
        cmd = cmd.format(**locals()) + tobam_cl
        do.run(cmd, "bwa %s" % align_type, data)
    return out_file

def _bwa_args_from_config(config):
    num_cores = config["algorithm"].get("num_cores", 1)
    core_flags = ["-t", str(num_cores)] if num_cores > 1 else []
    qual_format = config["algorithm"].get("quality_format", "").lower()
    qual_flags = ["-I"] if qual_format == "illumina" else []
    return core_flags + qual_flags

def _run_bwa_align(fastq_file, ref_file, out_file, config):
    aln_cl = [config_utils.get_program("bwa", config), "aln",
              "-n 2", "-k 2"]
    aln_cl += _bwa_args_from_config(config)
    aln_cl += [ref_file, fastq_file]
    cmd = "{cl} > {out_file}".format(cl=" ".join(aln_cl), out_file=out_file)
    do.run(cmd, "bwa aln: {f}".format(f=os.path.basename(fastq_file)), None)

########NEW FILE########
__FILENAME__ = mosaik
"""Next gen sequence alignment with Mosaik.

http://bioinformatics.bc.edu/marthlab/Mosaik
"""
import os
import subprocess

from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

galaxy_location_file = "mosaik_index.loc"

def _mosaik_args_from_config(config):
    """Configurable high level options for mosaik.
    """
    multi_mappers = config["algorithm"].get("multiple_mappers", True)
    multi_flags = ["-m", "all"] if multi_mappers else ["-m", "unique"]
    error_flags = ["-mm", "2"]
    num_cores = config["algorithm"].get("num_cores", 1)
    core_flags = ["-p", str(num_cores)] if num_cores > 1 else []
    return core_flags + multi_flags + error_flags

def _convert_fastq(fastq_file, pair_file, rg_name, out_file, config):
    """Convert fastq inputs into internal Mosaik representation.
    """
    out_file = "{0}-fq.mkb".format(os.path.splitext(out_file)[0])
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("mosaik", config,
                                           default="MosaikAligner").replace("Aligner", "Build")]
            cl += ["-q", fastq_file,
                   "-out", tx_out_file,
                   "-st", config["algorithm"].get("platform", "illumina").lower()]
            if pair_file:
                cl += ["-q2", pair_file]
            if rg_name:
                cl += ["-id", rg_name]
            env_set = "export MOSAIK_TMP={0}".format(os.path.dirname(tx_out_file))
            subprocess.check_call(env_set + " && " + " ".join(cl), shell=True)
    return out_file

def _get_mosaik_nn_args(out_file):
    """Retrieve default neural network files from GitHub to pass to Mosaik.
    """
    base_nn_url = "https://raw.github.com/wanpinglee/MOSAIK/master/src/networkFile/"
    out = []
    for arg, fname in [("-annse", "2.1.26.se.100.005.ann"),
                       ("-annpe", "2.1.26.pe.100.0065.ann")]:
        arg_fname = os.path.join(os.path.dirname(out_file), fname)
        if not file_exists(arg_fname):
            subprocess.check_call(["wget", "-O", arg_fname, base_nn_url + fname])
        out += [arg, arg_fname]
    return out

def align(fastq_file, pair_file, ref_file, names, align_dir, data,
          extra_args=None):
    """Alignment with MosaikAligner.
    """
    config = data["config"]
    rg_name = names.get("rg", None) if names else None
    out_file = os.path.join(align_dir, "%s-align.bam" % names["lane"])
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            built_fastq = _convert_fastq(fastq_file, pair_file, rg_name,
                                         out_file, config)
            cl = [config_utils.get_program("mosaik", config, default="MosaikAligner")]
            cl += _mosaik_args_from_config(config)
            cl += extra_args if extra_args is not None else []
            cl += ["-ia", ref_file,
                   "-in", built_fastq,
                   "-out", os.path.splitext(tx_out_file)[0]]
            jump_base = os.path.splitext(ref_file)[0]
            key_file = "{0}_keys.jmp".format(jump_base)
            if file_exists(key_file):
                cl += ["-j", jump_base]
                # XXX hacky way to guess key size which needs to match
                # Can I get hash size directly
                jump_size_gb = os.path.getsize(key_file) / 1073741824.0
                if jump_size_gb < 1.0:
                    cl += ["-hs", "13"]
            cl += _get_mosaik_nn_args(out_file)
            env_set = "export MOSAIK_TMP={0}".format(os.path.dirname(tx_out_file))
            subprocess.check_call(env_set + " && "+
                                  " ".join([str(x) for x in cl]), shell=True)
            os.remove(built_fastq)
    return out_file

def remap_index_fn(ref_file):
    """Map bowtie references to equivalent mosaik indexes.
    """
    return ref_file.replace("/bowtie/", "/mosaik/")

########NEW FILE########
__FILENAME__ = novoalign
"""Next-gen sequencing alignment with Novoalign: http://www.novocraft.com

For BAM input handling this requires:
  novoalign (with license for multicore)
  samtools
"""
import os
import subprocess

from bcbio import bam, utils
from bcbio.ngsalign import alignprep, postalign
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.utils import (memoize_outfile, file_exists)

# ## BAM realignment

def get_rg_info(names):
    return r"@RG\tID:{rg}\tPL:{pl}\tPU:{pu}\tSM:{sample}".format(**names)

def align_bam(in_bam, ref_file, names, align_dir, data):
    """Perform realignment of input BAM file; uses unix pipes for avoid IO.
    """
    config = data["config"]
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    novoalign = config_utils.get_program("novoalign", config)
    samtools = config_utils.get_program("samtools", config)
    resources = config_utils.get_resources("novoalign", config)
    num_cores = config["algorithm"].get("num_cores", 1)
    max_mem = resources.get("memory", "4G").upper()
    extra_novo_args = " ".join(_novoalign_args_from_config(config, False))

    if not file_exists(out_file):
        with utils.curdir_tmpdir(data, base_dir=align_dir) as work_dir:
            with postalign.tobam_cl(data, out_file, bam.is_paired(in_bam)) as (tobam_cl, tx_out_file):
                rg_info = get_rg_info(names)
                tx_out_prefix = os.path.splitext(tx_out_file)[0]
                prefix1 = "%s-in1" % tx_out_prefix
                cmd = ("{samtools} sort -n -o -l 0 -@ {num_cores} -m {max_mem} {in_bam} {prefix1} "
                       "| {novoalign} -o SAM '{rg_info}' -d {ref_file} -f /dev/stdin "
                       "  -F BAMPE -c {num_cores} {extra_novo_args} | ")
                cmd = cmd.format(**locals()) + tobam_cl
                do.run(cmd, "Novoalign: %s" % names["sample"], None,
                       [do.file_nonempty(tx_out_file), do.file_reasonable_size(tx_out_file, in_bam)])
    return out_file

# ## Fastq to BAM alignment

def align_pipe(fastq_file, pair_file, ref_file, names, align_dir, data):
    """Perform piped alignment of fastq input files, generating sorted output BAM.
    """
    pair_file = pair_file if pair_file else ""
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    if data.get("align_split"):
        final_file = out_file
        out_file, data = alignprep.setup_combine(final_file, data)
        fastq_file = alignprep.split_namedpipe_cl(fastq_file, data)
        if pair_file:
            pair_file = alignprep.split_namedpipe_cl(pair_file, data)
    else:
        final_file = None
    samtools = config_utils.get_program("samtools", data["config"])
    novoalign = config_utils.get_program("novoalign", data["config"])
    resources = config_utils.get_resources("novoalign", data["config"])
    num_cores = data["config"]["algorithm"].get("num_cores", 1)
    max_mem = resources.get("memory", "1G")
    extra_novo_args = " ".join(_novoalign_args_from_config(data["config"]))
    rg_info = get_rg_info(names)
    if not utils.file_exists(out_file) and (final_file is None or not utils.file_exists(final_file)):
        with utils.curdir_tmpdir(data) as work_dir:
            with postalign.tobam_cl(data, out_file, pair_file != "") as (tobam_cl, tx_out_file):
                tx_out_prefix = os.path.splitext(tx_out_file)[0]
                cmd = ("{novoalign} -o SAM '{rg_info}' -d {ref_file} -f {fastq_file} {pair_file} "
                       "  -c {num_cores} {extra_novo_args} | ")
                cmd = cmd.format(**locals()) + tobam_cl
                do.run(cmd, "Novoalign: %s" % names["sample"], None,
                       [do.file_nonempty(tx_out_file), do.file_reasonable_size(tx_out_file, fastq_file)])
    data["work_bam"] = out_file
    return data

def _novoalign_args_from_config(config, need_quality=True):
    """Select novoalign options based on configuration parameters.
    """
    if need_quality:
        qual_format = config["algorithm"].get("quality_format", "").lower()
        qual_flags = ["-F", "ILMFQ" if qual_format == "illumina" else "STDFQ"]
    else:
        qual_flags = []
    multi_mappers = config["algorithm"].get("multiple_mappers")
    if multi_mappers is True:
        multi_flag = "Random"
    elif isinstance(multi_mappers, basestring):
        multi_flag = multi_mappers
    else:
        multi_flag = "None"
    multi_flags = ["-r"] + multi_flag.split()
    resources = config_utils.get_resources("novoalign", config)
    # default arguments for improved variant calling based on
    # comparisons to reference materials: turn off soft clipping and recalibrate
    if resources.get("options") is None:
        extra_args = ["-o", "FullNW", "-k"]
    else:
        extra_args = [str(x) for x in resources.get("options", [])]
    return qual_flags + multi_flags + extra_args

# Tweaks to add
# -k -t 200 -K quality calibration metrics
# paired end sizes

# ## Indexing

@memoize_outfile(ext=".ndx")
def refindex(ref_file, kmer_size=None, step_size=None, out_file=None):
    cl = ["novoindex"]
    if kmer_size:
        cl += ["-k", str(kmer_size)]
    if step_size:
        cl += ["-s", str(step_size)]
    cl += [out_file, ref_file]
    subprocess.check_call(cl)

# ## Galaxy integration

# Optional galaxy location file. Falls back on remap_index_fn if not found
galaxy_location_file = "novoalign_indices.loc"

def remap_index_fn(ref_file):
    """Map sequence references to equivalent novoalign indexes.
    """
    checks = [os.path.splitext(ref_file)[0].replace("/seq/", "/novoalign/"),
              os.path.splitext(ref_file)[0] + ".ndx",
              ref_file + ".bs.ndx",
              ref_file + ".ndx"]
    for check in checks:
        if os.path.exists(check):
            return check
    return checks[0]

########NEW FILE########
__FILENAME__ = postalign
"""Perform streaming post-alignment preparation -- de-duplication and sorting.

Centralizes a pipelined approach to generating sorted, de-duplicated BAM output
from sequencer results.

sambamba: https://github.com/lomereiter/sambamba
samblaster: http://arxiv.org/pdf/1403.7486v1.pdf
biobambam bammarkduplicates: http://arxiv.org/abs/1306.0836
"""
import contextlib
import os

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.provenance import do

@contextlib.contextmanager
def tobam_cl(data, out_file, is_paired=False):
    """Prepare command line for producing de-duplicated sorted output.

    - If no deduplication, sort and prepare a BAM file.
    - If paired, then use samblaster and prepare discordant outputs.
    - If unpaired, use biobambam's bammarkduplicates
    """
    do_dedup = _check_dedup(data)
    with utils.curdir_tmpdir(data) as tmpdir:
        with file_transaction(out_file) as tx_out_file:
            if not do_dedup:
                yield (_sam_to_sortbam_cl(data, tmpdir, tx_out_file), tx_out_file)
            elif is_paired:
                sr_file = "%s-sr.bam" % os.path.splitext(out_file)[0]
                disc_file = "%s-disc.bam" % os.path.splitext(out_file)[0]
                with file_transaction(sr_file) as tx_sr_file:
                    with file_transaction(disc_file) as tx_disc_file:
                        yield (samblaster_dedup_sort(data, tmpdir, tx_out_file, tx_sr_file, tx_disc_file),
                               tx_out_file)
            else:
                yield (_biobambam_dedup_sort(data, tmpdir, tx_out_file), tx_out_file)

def _get_cores_memory(data, downscale=2):
    """Retrieve cores and memory, using samtools as baseline.

    For memory, scaling down because we share with alignment and de-duplication.
    """
    resources = config_utils.get_resources("samtools", data["config"])
    num_cores = data["config"]["algorithm"].get("num_cores", 1)
    max_mem = config_utils.adjust_memory(resources.get("memory", "2G"),
                                         downscale, "decrease").upper()
    return num_cores, max_mem

def _sam_to_sortbam_cl(data, tmpdir, tx_out_file):
    """Convert to sorted BAM output with sambamba.
    """
    samtools = config_utils.get_program("samtools", data["config"])
    sambamba = config_utils.get_program("sambamba", data["config"])
    cores, mem = _get_cores_memory(data, downscale=3)
    return ("{samtools} view -b -S -u - | "
            "{sambamba} sort -t {cores} -m {mem} "
            "--tmpdir {tmpdir} -o {tx_out_file} /dev/stdin".format(**locals()))

def samblaster_dedup_sort(data, tmpdir, tx_out_file, tx_sr_file, tx_disc_file):
    """Deduplicate and sort with samblaster, produces split read and discordant pair files.
    """
    sambamba = config_utils.get_program("sambamba", data["config"])
    samblaster = config_utils.get_program("samblaster", data["config"])
    samtools = config_utils.get_program("samtools", data["config"])
    cores, mem = _get_cores_memory(data, downscale=3)
    for dname in ["spl", "disc", "full"]:
        utils.safe_makedir(os.path.join(tmpdir, dname))
    tobam_cmd = ("{samtools} view -S -u /dev/stdin | "
                 "{sambamba} sort -t {cores} -m {mem} --tmpdir {tmpdir}/{dext} "
                 "-o {out_file} /dev/stdin")
    splitter_cmd = tobam_cmd.format(out_file=tx_sr_file, dext="spl", **locals())
    discordant_cmd = tobam_cmd.format(out_file=tx_disc_file, dext="disc", **locals())
    dedup_cmd = tobam_cmd.format(out_file=tx_out_file, dext="full", **locals())
    cmd = ("{samblaster} --splitterFile >({splitter_cmd}) --discordantFile >({discordant_cmd}) "
           "| {dedup_cmd}")
    return cmd.format(**locals())

def _biobambam_dedup_sort(data, tmpdir, tx_out_file):
    """Perform streaming deduplication and sorting with biobambam's bammarkduplicates2.
    """
    samtools = config_utils.get_program("samtools", data["config"])
    sambamba = config_utils.get_program("sambamba", data["config"])
    bammarkduplicates = config_utils.get_program("bammarkduplicates", data["config"])
    base_tmp = os.path.join(tmpdir, os.path.splitext(os.path.basename(tx_out_file))[0])
    cores, mem = _get_cores_memory(data, downscale=3)
    sort2_tmpdir = utils.safe_makedir(os.path.join(tmpdir, "sort2"))
    return ("{samtools} view -b -S -u - |"
            "{samtools} sort -n -o -@ {cores} -m {mem} - {base_tmp}-sort | "
            "{bammarkduplicates} tmpfile={base_tmp}-markdup "
            "markthreads={cores} level=0 | "
            "{sambamba} sort -t {cores} -m {mem} --tmpdir {sort2_tmpdir} "
            "-o {tx_out_file} /dev/stdin").format(**locals())

def _check_dedup(data):
    """Check configuration for de-duplication, handling back compatibility.
    """
    dup_param = utils.get_in(data, ("config", "algorithm", "mark_duplicates"), True)
    if dup_param and isinstance(dup_param, basestring):
        logger.info("Warning: bcbio no longer support explicit setting of mark_duplicate algorithm. "
                    "Using best-practice choice based on input data.")
        dup_param = True
    return dup_param

def dedup_bam(in_bam, data):
    """Perform non-stream based deduplication of BAM input files using biobambam.
    """
    if _check_dedup(data):
        out_file = "%s-dedup%s" % utils.splitext_plus(in_bam)
        if not utils.file_exists(out_file):
            with utils.curdir_tmpdir(data) as tmpdir:
                with file_transaction(out_file) as tx_out_file:
                    bammarkduplicates = config_utils.get_program("bammarkduplicates", data["config"])
                    base_tmp = os.path.join(tmpdir, os.path.splitext(os.path.basename(tx_out_file))[0])
                    cores, mem = _get_cores_memory(data, downscale=3)
                    cmd = ("{bammarkduplicates} tmpfile={base_tmp}-markdup "
                           "markthreads={cores} I={in_bam} O={tx_out_file}")
                    do.run(cmd.format(**locals()), "De-duplication with biobambam")
        return out_file
    else:
        return in_bam

########NEW FILE########
__FILENAME__ = snap
"""Alignment with SNAP: http://snap.cs.berkeley.edu/
"""
import os

from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.ngsalign import novoalign
from bcbio.provenance import do

def align(fastq_file, pair_file, index_dir, names, align_dir, data):
    """Perform piped alignment of fastq input files, generating sorted, deduplicated BAM.

    TODO: Use streaming with new development version of SNAP to feed into
    structural variation preparation de-duplication.
    """
    pair_file = pair_file if pair_file else ""
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    assert not data.get("align_split"), "Split alignments not supported with SNAP"
    snap = config_utils.get_program("snap", data["config"])
    num_cores = data["config"]["algorithm"].get("num_cores", 1)
    resources = config_utils.get_resources("snap", data["config"])
    max_mem = resources.get("memory", "1G")
    rg_info = novoalign.get_rg_info(names)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with utils.curdir_tmpdir(data) as work_dir:
                if fastq_file.endswith(".bam"):
                    cmd_name = "paired" if bam.is_paired(fastq_file) else "single"
                else:
                    cmd_name = "single" if not pair_file else "paired"
                cmd = ("{snap} {cmd_name} {index_dir} {fastq_file} {pair_file} "
                       "-rg '{rg_info}' -t {num_cores} -sa -so -sm {max_mem} -o {tx_out_file}")
                do.run(cmd.format(**locals()), "SNAP alignment: %s" % names["sample"])
    data["work_bam"] = out_file
    return data

def align_bam(bam_file, index_dir, names, align_dir, data):
    return align(bam_file, None, index_dir, names, align_dir, data)

# Optional galaxy location file. Falls back on remap_index_fn if not found
galaxy_location_file = "snap_indices.loc"

def remap_index_fn(ref_file):
    """Map sequence references to snap reference directory, using standard layout.
    """
    snap_dir = os.path.join(os.path.dirname(ref_file), os.pardir, "snap")
    assert os.path.exists(snap_dir) and os.path.isdir(snap_dir), snap_dir
    return snap_dir

########NEW FILE########
__FILENAME__ = star
import os
import tempfile

from bcbio.pipeline import config_utils
from bcbio.utils import safe_makedir, file_exists, get_in, symlink_plus
from bcbio.provenance import do
from bcbio import bam

CLEANUP_FILES = ["Aligned.out.sam", "Log.out", "Log.progress.out"]
ALIGN_TAGS =  ["NH", "HI", "NM", "MD", "AS"]

def align(fastq_file, pair_file, ref_file, names, align_dir, data):
    config = data["config"]
    out_prefix = os.path.join(align_dir, names["lane"])
    out_file = out_prefix + "Aligned.out.sam"
    out_dir = os.path.join(align_dir, "%s_star" % names["lane"])

    final_out = os.path.join(out_dir, "{0}.bam".format(names["sample"]))
    if file_exists(final_out):
        return final_out
    star_path = config_utils.get_program("STAR", config)
    fastq = " ".join([fastq_file, pair_file]) if pair_file else fastq_file
    num_cores = config["algorithm"].get("num_cores", 1)

    safe_makedir(align_dir)
    cmd = ("{star_path} --genomeDir {ref_file} --readFilesIn {fastq} "
           "--runThreadN {num_cores} --outFileNamePrefix {out_prefix} "
           "--outReadsUnmapped Fastx --outFilterMultimapNmax 10 "
           "--outSAMunmapped Within --outSAMattributes %s" % " ".join(ALIGN_TAGS))
    cmd += _read_group_option(names)
    fusion_mode = get_in(data, ("config", "algorithm", "fusion_mode"), False)
    if fusion_mode:
        cmd += " --chimSegmentMin 15 --chimJunctionOverhangMin 15"
    strandedness = get_in(data, ("config", "algorithm", "strandedness"),
                          "unstranded").lower()
    if strandedness == "unstranded":
        cmd += " --outSAMstrandField intronMotif"
    run_message = "Running STAR aligner on %s and %s." % (pair_file, ref_file)
    do.run(cmd.format(**locals()), run_message, None)
    out_file = bam.sam_to_bam(out_file, config)
    if not file_exists(final_out):
        symlink_plus(out_file, final_out)
    return final_out

def _read_group_option(names):
    rg_id = names["rg"]
    rg_sample = names["sample"]
    rg_library = names["pl"]
    rg_platform_unit = names["pu"]

    return (" --outSAMattrRGline ID:{rg_id} PL:{rg_library} "
            "PU:{rg_platform_unit} SM:{rg_sample} ").format(**locals())

def _get_quality_format(config):
    qual_format = config["algorithm"].get("quality_format", None)
    if qual_format.lower() == "illumina":
        return "fastq-illumina"
    elif qual_format.lower() == "solexa":
        return "fastq-solexa"
    else:
        return "fastq-sanger"

def remap_index_fn(ref_file):
    """Map sequence references to equivalent star indexes
    """
    return os.path.join(os.path.dirname(os.path.dirname(ref_file)), "star")

########NEW FILE########
__FILENAME__ = tophat
"""Next-gen alignments with TopHat a spliced read mapper for RNA-seq experiments.

http://tophat.cbcb.umd.edu
"""
import os
import shutil
from contextlib import closing
import glob

import numpy
import pysam

try:
    import sh
except ImportError:
    sh = None

from bcbio.pipeline import config_utils
from bcbio.ngsalign import bowtie, bowtie2
from bcbio.utils import safe_makedir, file_exists, get_in, symlink_plus
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.provenance import do
from bcbio import bam
from bcbio import broad


_out_fnames = ["accepted_hits.sam", "junctions.bed",
               "insertions.bed", "deletions.bed"]


def _set_quality_flag(options, config):
    qual_format = config["algorithm"].get("quality_format", None)
    if qual_format.lower() == "illumina":
        options["solexa1.3-quals"] = True
    elif qual_format.lower() == "solexa":
        options["solexa-quals"] = True
    return options

def _set_transcriptome_option(options, data, ref_file):
    # prefer transcriptome-index vs a GTF file if available
    transcriptome_index = get_in(data, ("genome_resources", "rnaseq",
                                        "transcriptome_index", "tophat"))
    fusion_mode = get_in(data, ("config", "algorithm", "fusion_mode"), False)
    if transcriptome_index and file_exists(transcriptome_index) and not fusion_mode:
        options["transcriptome-index"] = os.path.splitext(transcriptome_index)[0]
        return options

    gtf_file = data["genome_resources"]["rnaseq"].get("transcripts")
    if gtf_file:
        options["GTF"] = gtf_file
        return options

    return options

def _set_cores(options, config):
    num_cores = config["algorithm"].get("num_cores", 0)
    if num_cores > 1 and "num-threads" not in options:
        options["num-threads"] = num_cores
    return options

def _set_rg_options(options, names):
    if not names:
        return options
    options["rg-id"] = names["rg"]
    options["rg-sample"] = names["sample"]
    options["rg-library"] = names["pl"]
    options["rg-platform-unit"] = names["pu"]
    return options

def _set_stranded_flag(options, config):
    strand_flag = {"unstranded": "fr-unstranded",
                   "firststrand": "fr-firststrand",
                   "secondstrand": "fr-secondstrand"}
    stranded = get_in(config, ("algorithm", "strandedness"), "unstranded").lower()
    assert stranded in strand_flag, ("%s is not a valid strandedness value. "
                                     "Valid values are 'firststrand', "
                                     "'secondstrand' and 'unstranded" % (stranded))
    flag = strand_flag[stranded]
    options["library-type"] = flag
    return options

def _set_fusion_mode(options, config):
    fusion_mode = get_in(config, ("algorithm", "fusion_mode"), False)
    if fusion_mode:
        options["fusion-search"] = True
    return options

def tophat_align(fastq_file, pair_file, ref_file, out_base, align_dir, data,
                 names=None):
    """
    run alignment using Tophat v2
    """
    config = data["config"]
    options = get_in(config, ("resources", "tophat", "options"), {})
    options = _set_fusion_mode(options, config)
    options = _set_quality_flag(options, config)
    options = _set_transcriptome_option(options, data, ref_file)
    options = _set_cores(options, config)
    options = _set_rg_options(options, names)
    options = _set_stranded_flag(options, config)

    ref_file, runner = _determine_aligner_and_reference(ref_file, config)

    # fusion search does not work properly with Bowtie2
    if options.get("fusion-search", False):
        ref_file = ref_file.replace("/bowtie2", "/bowtie")

    if _tophat_major_version(config) == 1:
        raise NotImplementedError("Tophat versions < 2.0 are not supported, please "
                                  "download the newest version of Tophat here: "
                                  "http://tophat.cbcb.umd.edu")

    if _ref_version(ref_file) == 1 or options.get("fusion-search", False):
        options["bowtie1"] = True

    out_dir = os.path.join(align_dir, "%s_tophat" % out_base)
    final_out = os.path.join(out_dir, "{0}.bam".format(names["sample"]))
    if file_exists(final_out):
        return final_out

    out_file = os.path.join(out_dir, "accepted_hits.sam")
    unmapped = os.path.join(out_dir, "unmapped.bam")
    files = [ref_file, fastq_file]
    if not file_exists(out_file):
        with file_transaction(out_dir) as tx_out_dir:
            safe_makedir(tx_out_dir)
            if pair_file and not options.get("mate-inner-dist", None):
                d, d_stdev = _estimate_paired_innerdist(fastq_file, pair_file,
                                                        ref_file, out_base,
                                                        tx_out_dir, data)
                options["mate-inner-dist"] = d
                options["mate-std-dev"] = d_stdev
                files.append(pair_file)
            options["output-dir"] = tx_out_dir
            options["no-convert-bam"] = True
            options["no-coverage-search"] = True
            options["no-mixed"] = True
            tophat_runner = sh.Command(config_utils.get_program("tophat",
                                                                config))
            ready_options = {}
            for k, v in options.iteritems():
                ready_options[k.replace("-", "_")] = v
            # tophat requires options before arguments,
            # otherwise it silently ignores them
            tophat_ready = tophat_runner.bake(**ready_options)
            cmd = str(tophat_ready.bake(*files))
            do.run(cmd, "Running Tophat on %s and %s." % (fastq_file, pair_file), None)
        _fix_empty_readnames(out_file)
    if pair_file and _has_alignments(out_file):
        fixed = _fix_mates(out_file, os.path.join(out_dir, "%s-align.sam" % out_base),
                           ref_file, config)
    else:
        fixed = out_file
    fixed = merge_unmapped(fixed, unmapped, config)
    fixed = _fix_unmapped(fixed, config, names)
    fixed = bam.sort(fixed, config)
    picard = broad.runner_from_config(config)
    # set the contig order to match the reference file so GATK works
    fixed = picard.run_fn("picard_reorder", out_file, data["sam_ref"],
                          os.path.splitext(out_file)[0] + ".picard.bam")
    if not file_exists(final_out):
        symlink_plus(fixed, final_out)
    return final_out

def merge_unmapped(mapped_sam, unmapped_bam, config):
    merged_bam = os.path.join(os.path.dirname(mapped_sam), "merged.bam")
    bam_file = bam.sam_to_bam(mapped_sam, config)
    if not file_exists(merged_bam):
        merged_bam = bam.merge([bam_file, unmapped_bam], merged_bam, config)
    return merged_bam

def _has_alignments(sam_file):
    with open(sam_file) as in_handle:
        for line in in_handle:
            if line.startswith("File removed to save disk space"):
                return False
            elif not line.startswith("@"):
                return True
    return False

def _fix_empty_readnames(orig_file):
    """ Fix SAMfile reads with empty read names

    Tophat 2.0.9 sometimes outputs empty read names, making the
    FLAG field be the read name. This throws those reads away.
    """
    with file_transaction(orig_file) as tx_out_file:
        logger.info("Removing reads with empty read names from Tophat output.")
        with open(orig_file) as orig, open(tx_out_file, "w") as out:
            for line in orig:
                if line.split()[0].isdigit():
                    continue
                out.write(line)
    return orig_file


def _fix_mates(orig_file, out_file, ref_file, config):
    """Fix problematic unmapped mate pairs in TopHat output.

    TopHat 2.0.9 appears to have issues with secondary reads:
    https://groups.google.com/forum/#!topic/tuxedo-tools-users/puLfDNbN9bo
    This cleans the input file to only keep properly mapped pairs,
    providing a general fix that will handle correctly mapped secondary
    reads as well.
    """
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            samtools = config_utils.get_program("samtools", config)
            cmd = "{samtools} view -h -t {ref_file}.fai -F 8 {orig_file} > {tx_out_file}"
            do.run(cmd.format(**locals()), "Fix mate pairs in TopHat output", {})
    return out_file

def _fix_unmapped(unmapped_file, config, names):
    """
    the unmapped.bam file from Tophat 2.0.9 is missing some things
    1) the RG tag is missing from the reads
    2) MAPQ is set to 255 instead of 0
    3) for reads where both are unmapped, the mate_is_unmapped flag is not set correctly
    """
    out_file = os.path.splitext(unmapped_file)[0] + "_fixed.bam"
    if file_exists(out_file):
        return out_file
    picard = broad.runner_from_config(config)
    rg_fixed = picard.run_fn("picard_fix_rgs", unmapped_file, names)
    fixed = bam.sort(rg_fixed, config, "queryname")
    with closing(pysam.Samfile(fixed)) as work_sam:
        with file_transaction(out_file) as tx_out_file:
            tx_out = pysam.Samfile(tx_out_file, "wb", template=work_sam)
            for read1 in work_sam:
                if not read1.is_paired:
                    if read1.is_unmapped:
                        read1.mapq = 0
                    tx_out.write(read1)
                    continue
                read2 = work_sam.next()
                if read1.qname != read2.qname:
                    continue
                if read1.is_unmapped and not read2.is_unmapped:
                    read1.mapq = 0
                    read1.tid = read2.tid
                if not read1.is_unmapped and read2.is_unmapped:
                    read2.mapq = 0
                    read2.tid = read1.tid
                if read1.is_unmapped and read2.is_unmapped:
                    read1.mapq = 0
                    read2.mapq = 0
                    read1.mate_is_unmapped = True
                    read2.mate_is_unmapped = True
                tx_out.write(read1)
                tx_out.write(read2)
            tx_out.close()

    return out_file

def align(fastq_file, pair_file, ref_file, names, align_dir, data,):
    out_files = tophat_align(fastq_file, pair_file, ref_file, names["lane"],
                             align_dir, data, names)

    return out_files


def _estimate_paired_innerdist(fastq_file, pair_file, ref_file, out_base,
                               out_dir, data):
    """Use Bowtie to estimate the inner distance of paired reads.
    """
    mean, stdev = _bowtie_for_innerdist("100000", fastq_file, pair_file, ref_file,
                                        out_base, out_dir, data, True)
    if not mean or not stdev:
        mean, stdev = _bowtie_for_innerdist("1", fastq_file, pair_file, ref_file,
                                            out_base, out_dir, data, True)
    # No reads aligning so no data to process, set some default values
    if not mean or not stdev:
        mean, stdev = 200, 50

    return mean, stdev


def _bowtie_for_innerdist(start, fastq_file, pair_file, ref_file, out_base,
                          out_dir, data, remove_workdir=False):
    work_dir = os.path.join(out_dir, "innerdist_estimate")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    safe_makedir(work_dir)
    extra_args = ["-s", str(start), "-u", "250000"]
    ref_file, bowtie_runner = _determine_aligner_and_reference(ref_file, data["config"])
    out_sam = bowtie_runner.align(fastq_file, pair_file, ref_file, {"lane": out_base},
                                  work_dir, data, extra_args)
    dists = []
    with closing(pysam.Samfile(out_sam)) as work_sam:
        for read in work_sam:
            if read.is_proper_pair and read.is_read1:
                dists.append(abs(read.isize) - 2 * read.rlen)
    if dists:
        median = float(numpy.median(dists))
        deviations = []
        for d in dists:
            deviations.append(abs(d - median))
        # this is the median absolute deviation estimator of the
        # standard deviation
        mad = 1.4826 * float(numpy.median(deviations))
        return int(median), int(mad)
    else:
        return None, None

def _calculate_average_read_length(sam_file):
    with closing(pysam.Samfile(sam_file)) as work_sam:
        count = 0
        read_lengths = []
        for read in work_sam:
            count = count + 1
            read_lengths.append(read.rlen)
    avg_read_length = int(float(sum(read_lengths)) / float(count))
    return avg_read_length


def _bowtie_major_version(stdout):
    """
    bowtie --version returns strings like this:
    bowtie version 0.12.7
    32-bit
    Built on Franklin.local
    Tue Sep  7 14:25:02 PDT 2010
    """
    version_line = stdout.split("\n")[0]
    version_string = version_line.strip().split()[2]
    major_version = int(version_string.split(".")[0])
    # bowtie version 1 has a leading character of 0 or 1
    if major_version == 0 or major_version == 1:
        major_version = 1
    return major_version

def _determine_aligner_and_reference(ref_file, config):
    fusion_mode = get_in(config, ("algorithm", "fusion_mode"), False)
    # fusion_mode only works with bowtie1
    if fusion_mode:
        return _get_bowtie_with_reference(config, ref_file, 1)
    else:
        return _get_bowtie_with_reference(config, ref_file, 2)

def _get_bowtie_with_reference(config, ref_file, version):
    if version == 1:
        ref_file = ref_file.replace("/bowtie2/", "/bowtie/")
        return ref_file, bowtie
    else:
        ref_file = ref_file.replace("/bowtie/", "/bowtie2/")
        return ref_file, bowtie2


def _tophat_major_version(config):
    tophat_runner = sh.Command(config_utils.get_program("tophat", config,
                                                        default="tophat"))

    # tophat --version returns strings like this: Tophat v2.0.4
    version_string = str(tophat_runner(version=True)).strip().split()[1]
    major_version = int(version_string.split(".")[0][1:])
    return major_version


def _ref_version(ref_file):
    for ext in [os.path.splitext(x)[1] for x in glob.glob(ref_file + "*")]:
        if ext == ".ebwt":
            return 1
        elif ext == ".bt2":
            return 2
    raise ValueError("Cannot detect which reference version %s is. "
                     "Should end in either .ebwt (bowtie) or .bt2 "
                     "(bowtie2)." % (ref_file))

########NEW FILE########
__FILENAME__ = metrics
# Back compatibility -- use broad subdirectory for new code
from bcbio.broad.metrics import *

########NEW FILE########
__FILENAME__ = utils
# Placeholder for back compatibility.
from bcbio.utils import *

########NEW FILE########
__FILENAME__ = alignment
"""Pipeline code to run alignments and prepare BAM files.

This works as part of the lane/flowcell process step of the pipeline.
"""
from collections import namedtuple
import os

from bcbio import bam, utils
from bcbio.bam import cram
from bcbio.ngsalign import (bowtie, bwa, tophat, bowtie2,
                            novoalign, snap, star)

# Define a next-generation sequencing tool to plugin:
# align_fn -- runs an aligner and generates SAM output
# galaxy_loc_file -- name of a Galaxy location file to retrieve
#  the genome index location
# bam_align_fn -- runs an aligner on a BAM file
# remap_index_fn -- Function that will take the location provided
#  from galaxy_loc_file and find the actual location of the index file.
#  This is useful for indexes that don't have an associated location file
#  but are stored in the same directory structure.
NgsTool = namedtuple("NgsTool", ["align_fn", "bam_align_fn",
                                 "galaxy_loc_file", "remap_index_fn"])


BASE_LOCATION_FILE = "sam_fa_indices.loc"

TOOLS = {
    "bowtie": NgsTool(bowtie.align, None, bowtie.galaxy_location_file, None),
    "bowtie2": NgsTool(bowtie2.align, None,
                       bowtie2.galaxy_location_file, bowtie2.remap_index_fn),
    "bwa": NgsTool(bwa.align_pipe, bwa.align_bam, bwa.galaxy_location_file, None),
    "novoalign": NgsTool(novoalign.align_pipe, novoalign.align_bam,
                         novoalign.galaxy_location_file, novoalign.remap_index_fn),
    "tophat": NgsTool(tophat.align, None,
                      bowtie2.galaxy_location_file, bowtie2.remap_index_fn),
    "samtools": NgsTool(None, None, BASE_LOCATION_FILE, None),
    "snap": NgsTool(snap.align, snap.align_bam, snap.galaxy_location_file, snap.remap_index_fn),
    "star": NgsTool(star.align, None, None, star.remap_index_fn),
    "tophat2": NgsTool(tophat.align, None,
                       bowtie2.galaxy_location_file, bowtie2.remap_index_fn)}

metadata = {"support_bam": [k for k, v in TOOLS.iteritems() if v.bam_align_fn is not None]}

def align_to_sort_bam(fastq1, fastq2, aligner, data):
    """Align to the named genome build, returning a sorted BAM file.
    """
    names = data["rgnames"]
    align_dir_parts = [data["dirs"]["work"], "align", names["sample"]]
    if data.get("disambiguate"):
        align_dir_parts.append(data["disambiguate"]["genome_build"])
    align_dir = utils.safe_makedir(apply(os.path.join, align_dir_parts))
    if fastq1.endswith(".bam"):
        data = _align_from_bam(fastq1, aligner, utils.get_in(data, ("reference", aligner, "base")),
                               utils.get_in(data, ("reference", "fasta", "base")),
                               names, align_dir, data)
    else:
        data = _align_from_fastq(fastq1, fastq2, aligner, utils.get_in(data, ("reference", aligner, "base")),
                                 utils.get_in(data, ("reference", "fasta", "base")),
                                 names, align_dir, data)
    if data["work_bam"] and utils.file_exists(data["work_bam"]):
        bam.index(data["work_bam"], data["config"])
    return data

def _align_from_bam(fastq1, aligner, align_ref, sam_ref, names, align_dir, data):
    assert not data.get("align_split"), "Do not handle split alignments with BAM yet"
    config = data["config"]
    qual_bin_method = config["algorithm"].get("quality_bin")
    if (qual_bin_method == "prealignment" or
         (isinstance(qual_bin_method, list) and "prealignment" in qual_bin_method)):
        out_dir = utils.safe_makedir(os.path.join(align_dir, "qualbin"))
        fastq1 = cram.illumina_qual_bin(fastq1, sam_ref, out_dir, config)
    align_fn = TOOLS[aligner].bam_align_fn
    if align_fn is None:
        raise NotImplementedError("Do not yet support BAM alignment with %s" % aligner)
    out = align_fn(fastq1, align_ref, names, align_dir, data)
    if isinstance(out, dict):
        assert "work_bam" in out
        return out
    else:
        data["work_bam"] = out
        return data

def _align_from_fastq(fastq1, fastq2, aligner, align_ref, sam_ref, names,
                      align_dir, data):
    """Align from fastq inputs, producing sorted BAM output.
    """
    config = data["config"]
    align_fn = TOOLS[aligner].align_fn
    out = align_fn(fastq1, fastq2, align_ref, names, align_dir, data)
    # handle align functions that update the main data dictionary in place
    if isinstance(out, dict):
        assert "work_bam" in out
        return out
    # handle output of raw SAM files that need to be converted to BAM
    else:
        work_bam = bam.sam_to_bam(out, config)
        data["work_bam"] = bam.sort(work_bam, config)
        return data

########NEW FILE########
__FILENAME__ = archive
"""Perform archiving of output files for compressed storage.

Handles conversion to CRAM format.
"""

from bcbio import utils
from bcbio.bam import cram

def to_cram(data):
    """Convert BAM archive files into indexed CRAM.
    """
    ref_file = utils.get_in(data, ("reference", "fasta", "base"))
    cram_file = cram.compress(data["work_bam"], ref_file, data["config"])
    data["work_bam"] = cram_file
    return [[data]]

def compress(samples, run_parallel):
    """Perform compression of output files for long term storage.
    """
    to_cram = []
    finished = []
    for data in [x[0] for x in samples]:
        to_archive = set(utils.get_in(data, ("config", "algorithm", "archive"), []))
        if "cram" in to_archive:
            to_cram.append([data])
        else:
            finished.append([data])
    crammed = run_parallel("archive_to_cram", to_cram)
    return finished + crammed

########NEW FILE########
__FILENAME__ = cleanbam
"""Clean an input BAM file to work with downstream pipelines.

GATK and Picard based pipelines have specific requirements for
chromosome order, run group information and other BAM formatting.
This provides a pipeline to prepare and resort an input.
"""
import os

from bcbio import bam, broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do

def picard_prep(in_bam, names, ref_file, dirs, config):
    """Prepare input BAM using Picard and GATK cleaning tools.

    - ReorderSam to reorder file to reference
    - AddOrReplaceReadGroups to add read group information and coordinate sort
    - PrintReads to filters to remove problem records:
    - filterMBQ to remove reads with mismatching bases and base qualities
    """
    runner = broad.runner_from_config(config)
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "bamclean", names["sample"]))
    runner.run_fn("picard_index_ref", ref_file)
    reorder_bam = os.path.join(work_dir, "%s-reorder.bam" %
                               os.path.splitext(os.path.basename(in_bam))[0])
    reorder_bam = runner.run_fn("picard_reorder", in_bam, ref_file, reorder_bam)
    rg_bam = runner.run_fn("picard_fix_rgs", reorder_bam, names)
    return _filter_bad_reads(rg_bam, ref_file, config)

def _filter_bad_reads(in_bam, ref_file, config):
    """Use GATK filter to remove problem reads which choke GATK and Picard.
    """
    bam.index(in_bam, config)
    out_file = "%s-gatkfilter.bam" % os.path.splitext(in_bam)[0]
    if not utils.file_exists(out_file):
        with utils.curdir_tmpdir({"config": config}) as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                params = ["-T", "PrintReads",
                          "-R", ref_file,
                          "-I", in_bam,
                          "--out", tx_out_file,
                          "--filter_mismatching_base_and_quals"]
                jvm_opts = broad.get_gatk_framework_opts(config, tmp_dir)
                cmd = [config_utils.get_program("gatk-framework", config)] + jvm_opts + params
                do.run(cmd, "Filter problem reads")
    return out_file

########NEW FILE########
__FILENAME__ = config_utils
"""Loads configurations from .yaml files and expands environment variables.
"""
import copy
import glob
import math
import os
import sys
import yaml


class CmdNotFound(Exception):
    pass

# ## Generalized configuration

def update_w_custom(config, lane_info):
    """Update the configuration for this lane if a custom analysis is specified.
    """
    name_remaps = {"variant": ["SNP calling", "variant", "variant2"],
                   "SNP calling": ["SNP calling", "variant", "variant2"],
                   "variant2": ["SNP calling", "variant", "variant2"]}
    config = copy.deepcopy(config)
    base_name = lane_info.get("analysis")
    if "algorithm" not in config:
        config["algorithm"] = {}
    for analysis_type in name_remaps.get(base_name, [base_name]):
        custom = config.get("custom_algorithms", {}).get(analysis_type)
        if custom:
            for key, val in custom.iteritems():
                config["algorithm"][key] = val
    # apply any algorithm details specified with the lane
    for key, val in lane_info.get("algorithm", {}).iteritems():
        config["algorithm"][key] = val
    # apply any resource details specified with the lane
    for prog, pkvs in lane_info.get("resources", {}).iteritems():
        if prog not in config["resources"]:
            config["resources"][prog] = {}
        for key, val in pkvs.iteritems():
            config["resources"][prog][key] = val
    return config

# ## Retrieval functions

def load_system_config(config_file, work_dir=None):
    """Load bcbio_system.yaml configuration file, handling standard defaults.

    Looks for configuration file in default location within
    final base directory from a standard installation. Handles both standard
    installs (galaxy/bcbio_system.yaml) and docker installs (config/bcbio_system.yaml).
    """
    docker_config = _get_docker_config()
    if not os.path.exists(config_file):
        base_dir = get_base_installdir()
        test_config = os.path.join(base_dir, "galaxy", config_file)
        if os.path.exists(test_config):
            config_file = test_config
        else:
            raise ValueError("Could not find input system configuration file %s, "
                             "including inside standard directory %s" %
                             (config_file, os.path.join(base_dir, "galaxy")))
    config = load_config(config_file)
    if docker_config:
        assert work_dir is not None, "Need working directory to merge docker config"
        config_file = os.path.join(work_dir, "%s-merged%s" % os.path.splitext(os.path.basename(config_file)))
        config = _merge_system_configs(config, docker_config, config_file)
    if "algorithm" not in config:
        config["algorithm"] = {}
    config["bcbio_system"] = config_file
    return config, config_file

def get_base_installdir():
    return os.path.normpath(os.path.join(os.path.realpath(sys.executable), os.pardir, os.pardir, os.pardir))

def _merge_system_configs(host_config, container_config, out_file=None):
    """Create a merged system configuration from external and internal specification.
    """
    out = copy.deepcopy(container_config)
    for k, v in host_config.iteritems():
        if k in set(["galaxy_config"]):
            out[k] = v
        elif k == "resources":
            for pname, resources in v.iteritems():
                if not isinstance(resources, dict) and pname not in out[k]:
                    out[k][pname] = resources
                else:
                    for rname, rval in resources.iteritems():
                        if rname in set(["cores", "jvm_opts", "memory"]):
                            if pname not in out[k]:
                                out[k][pname] = {}
                            out[k][pname][rname] = rval
    # Ensure final file is relocatable by mapping back to reference directory
    if "bcbio_system" in out and ("galaxy_config" not in out or not os.path.isabs(out["galaxy_config"])):
        out["galaxy_config"] = os.path.normpath(os.path.join(os.path.dirname(out["bcbio_system"]),
                                                             os.pardir, "galaxy",
                                                             "universe_wsgi.ini"))
    if out_file:
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out

def _get_docker_config():
    base_dir = get_base_installdir()
    docker_configfile = os.path.join(base_dir, "config", "bcbio_system.yaml")
    if os.path.exists(docker_configfile):
        return load_config(docker_configfile)

def merge_resources(args):
    """Merge docker local resources and global resource specification in a set of arguments.

    Finds the `data` object within passed arguments and updates the resources
    from a local docker configuration if present.
    """
    docker_config = _get_docker_config()
    if not docker_config:
        return args
    else:
        def _update_resources(config):
            config["resources"] = _merge_system_configs(config, docker_config)["resources"]
            return config
        return _update_config(args, _update_resources)

def load_config(config_file):
    """Load YAML config file, replacing environmental variables.
    """
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    config = _expand_paths(config)
    # lowercase resource names, the preferred way to specify, for back-compatibility
    newr = {}
    for k, v in config["resources"].iteritems():
        if k.lower() != k:
            newr[k.lower()] = v
    config["resources"].update(newr)
    return config

def _expand_paths(config):
    for field, setting in config.items():
        if isinstance(config[field], dict):
            config[field] = _expand_paths(config[field])
        else:
            config[field] = expand_path(setting)
    return config

def expand_path(path):
    """ Combines os.path.expandvars with replacing ~ with $HOME.
    """
    try:
        return os.path.expandvars(path.replace("~", "$HOME"))
    except AttributeError:
        return path

def get_resources(name, config):
    """Retrieve resources for a program, pulling from multiple config sources.
    """
    return config.get("resources", {}).get(name, {})

def get_program(name, config, ptype="cmd", default=None):
    """Retrieve program information from the configuration.

    This handles back compatible location specification in input
    YAML. The preferred location for program information is in
    `resources` but the older `program` tag is also supported.
    """
    try:
        pconfig = config.get("resources", {})[name]
        # If have leftover old
    except KeyError:
        pconfig = {}
    old_config = config.get("program", {}).get(name, None)
    if old_config:
        for key in ["dir", "cmd"]:
            if not key in pconfig:
                pconfig[key] = old_config
    if ptype == "cmd":
        return _get_program_cmd(name, pconfig, default)
    elif ptype == "dir":
        return _get_program_dir(name, pconfig)
    else:
        raise ValueError("Don't understand program type: %s" % ptype)

def _get_check_program_cmd(fn):

    def wrap(name, config, default):
        program = expand_path(fn(name, config, default))
        is_ok = lambda f: os.path.isfile(f) and os.access(f, os.X_OK)
        if is_ok(program): return program

        for adir in os.environ['PATH'].split(":"):
            if is_ok(os.path.join(adir, program)):
                return os.path.join(adir, program)
        else:
            raise CmdNotFound(" ".join(map(repr, (fn.func_name, name, config, default))))
    return wrap

@_get_check_program_cmd
def _get_program_cmd(name, config, default):
    """Retrieve commandline of a program.
    """
    if config is None:
        return name
    elif isinstance(config, basestring):
        return config
    elif "cmd" in config:
        return config["cmd"]
    elif default is not None:
        return default
    else:
        return name

def _get_program_dir(name, config):
    """Retrieve directory for a program (local installs/java jars).
    """
    if config is None:
        raise ValueError("Could not find directory in config for %s" % name)
    elif isinstance(config, basestring):
        return config
    elif "dir" in config:
        return expand_path(config["dir"])
    else:
        raise ValueError("Could not find directory in config for %s" % name)

def get_jar(base_name, dname):
    """Retrieve a jar in the provided directory
    """
    jars = glob.glob(os.path.join(expand_path(dname), "%s*.jar" % base_name))

    if len(jars) == 1:
        return jars[0]
    elif len(jars) > 1:
        raise ValueError("Found multiple jars for %s in %s. Need single jar: %s" %
                         (base_name, dname, jars))
    else:
        raise ValueError("Could not find java jar %s in %s" %
                         (base_name, dname))

# ## Retrieval and update to configuration from arguments

def _dictdissoc(orig, k):
    """Imitates immutability: create a new dictionary with the key dropped.
    """
    v = orig.pop(k, None)
    new = copy.deepcopy(orig)
    orig[k] = v
    return new

def is_std_config_arg(x):
    return isinstance(x, dict) and "algorithm" in x and "resources" in x and not "files" in x

def is_nested_config_arg(x):
    return isinstance(x, dict) and "config" in x and is_std_config_arg(x["config"])

def get_algorithm_config(xs):
    """Flexibly extract algorithm configuration for a sample from any function arguments.
    """
    for x in xs:
        if is_std_config_arg(x):
            return x["algorithm"]
        elif is_nested_config_arg(x):
            return x["config"]["algorithm"]
        elif isinstance(x, (list, tuple)) and is_nested_config_arg(x[0]):
            return x[0]["config"]["algorithm"]
    raise ValueError("Did not find algorithm configuration in items: {0}"
                     .format(xs))

def add_cores_to_config(args, cores_per_job, parallel=None):
    """Add information about available cores for a job to configuration.
    Ugly hack to update core information in a configuration dictionary.
    """
    def _update_cores(config):
        config["algorithm"]["num_cores"] = int(cores_per_job)
        if parallel:
            config["parallel"] = _dictdissoc(parallel, "view")
        return config
    return _update_config(args, _update_cores)

def _update_config(args, update_fn):
    """Update configuration, nested in argument list, with the provided update function.
    """
    new_i = None
    for i, arg in enumerate(args):
        if (is_std_config_arg(arg) or is_nested_config_arg(arg) or
              (isinstance(arg, (list, tuple)) and is_nested_config_arg(arg[0]))):
            new_i = i
            break
    if new_i is None:
        raise ValueError("Could not find configuration in args: %s" % str(args))

    new_arg = copy.deepcopy(args[new_i])
    if is_nested_config_arg(new_arg):
        new_arg["config"] = update_fn(new_arg["config"])
    elif is_std_config_arg(new_arg):
        new_arg = update_fn(new_arg)
    elif isinstance(arg, (list, tuple)) and is_nested_config_arg(new_arg[0]):
        new_arg_first = new_arg[0]
        new_arg_first["config"] = update_fn(new_arg_first["config"])
        new_arg = [new_arg_first] + new_arg[1:]
    else:
        raise ValueError("Unexpected configuration dictionary: %s" % new_arg)
    args = list(args)[:]
    args[new_i] = new_arg
    return args

def adjust_memory(val, magnitude, direction="increase"):
    """Adjust memory based on number of cores utilized.
    """
    modifier = val[-1:]
    amount = int(val[:-1])
    if direction == "decrease":
        new_amount = amount / magnitude
        # dealing with a specifier like 1G, need to scale to Mb
        if new_amount < 1:
            if modifier.upper().startswith("G"):
                new_amount = (amount * 1024) / magnitude
                modifier = "M" + modifier[1:]
            else:
                raise ValueError("Unexpected decrease in memory: %s by %s" % (val, magnitude))
        amount = new_amount
    elif direction == "increase":
        # for increases with multiple cores, leave small percentage of
        # memory for system to maintain process running resource and
        # avoid OOM killers
        adjuster = 0.91
        amount = int(math.ceil(amount * (adjuster * magnitude)))
    return "{amount}{modifier}".format(amount=amount, modifier=modifier)

def adjust_opts(in_opts, config):
    """Establish JVM opts, adjusting memory for the context if needed.

    This allows using less or more memory for highly parallel or multicore
    supporting processes, respectively.
    """
    memory_adjust = config["algorithm"].get("memory_adjust", {})
    out_opts = []
    for opt in in_opts:
        if opt.startswith(("-Xmx", "-Xms")):
            arg = opt[:4]
            opt = "{arg}{val}".format(arg=arg,
                                      val=adjust_memory(opt[4:],
                                                        memory_adjust.get("magnitude", 1),
                                                        memory_adjust.get("direction")))
        out_opts.append(opt)
    return out_opts

# specific program usage

def use_vqsr(algs):
    """Processing uses GATK's Variant Quality Score Recalibration.
    """
    for alg in algs:
        callers = alg.get("variantcaller", "gatk")
        if isinstance(callers, basestring):
            callers = [callers]
        elif not callers:  # no variant calling, no VQSR
            continue
        vqsr_supported_caller = False
        for c in callers:
            if c in ["gatk", "gatk-haplotype"]:
                vqsr_supported_caller = True
                break
        if alg.get("coverage_interval", "exome").lower() not in ["regional", "exome"] and vqsr_supported_caller:
            return True
    return False

## functions for navigating through the standard galaxy directory of files

def get_transcript_gtf(genome_dir):
    out_file = os.path.join(genome_dir, "rnaseq", "ref-transcripts.gtf")
    return out_file

def get_rRNA_interval(genome_dir):
    return os.path.join(genome_dir, "rnaseq", "rRNA.interval_list")

def get_transcript_refflat(genome_dir):
    return os.path.join(genome_dir, "rnaseq", "ref-transcripts.refFlat")

def get_rRNA_sequence(genome_dir):
    return os.path.join(genome_dir, "rnaseq", "rRNA.fa")

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
"""
This is the main function to call for disambiguating between BAM files 
from two species that have alignments from the same source of fastq files.
It is part of the explant RNA/DNA-Seq workflow where an informatics
approach is used to distinguish between e.g. human and mouse or rat RNA/DNA reads.

For reads that have aligned to both organisms, the functionality is based on
comparing quality scores from either Tophat, STAR or BWA. Read
name is used to collect all alignments for both mates (_1 and _2) and
compared between the alignments from the two species.

For tophat (default, can be changed using option -a), the sum of the flags XO,
NM and NH is evaluated and the lowest sum wins the paired end reads. For equal
scores, the reads are assigned as ambiguous.

The alternative algorithm (STAR, bwa) disambiguates (for aligned reads) by tags
AS (alignment score, higher better), followed by NM (edit distance, lower 
better).

Code by Miika Ahdesmaki July-August 2013, based on original Perl implementation
for Tophat by Zhongwu Lai.

Included in bcbio-nextgen from: https://github.com/mjafin/disambiguate
"""


from __future__ import print_function
import sys, re, pysam
from array import array
from os import path, makedirs
from argparse import ArgumentParser, RawTextHelpFormatter

# "natural comparison" for strings
def nat_cmp(a, b):
    convert = lambda text: int(text) if text.isdigit() else text # lambda function to convert text to int if number present
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] # split string to piecewise strings and string numbers
    #return cmp(alphanum_key(a), alphanum_key(b)) # use internal cmp to compare piecewise strings and numbers
    return (alphanum_key(a) > alphanum_key(b))-(alphanum_key(a) < alphanum_key(b))

# read reads into a list object for as long as the read qname is constant (sorted file). Return the first read with new qname or None
def read_next_reads(fileobject, listobject):
    qnamediff = False
    while not qnamediff:
        try:
            myRead=fileobject.next()
        except StopIteration:
            #print("5")
            return None # return None as the name of the new reads (i.e. no more new reads)
        if nat_cmp(myRead.qname, listobject[0].qname)==0:
            listobject.append(myRead)
        else:
            qnamediff = True
    return myRead # this is the first read with a new qname

# disambiguate between two lists of reads
def disambiguate(humanlist, mouselist, disambalgo):
    if disambalgo == 'tophat':
        dv = 2**13 # a high quality score to replace missing quality scores (no real quality score should be this high)
        sa = array('i',(dv for i in range(0,4))) # score array, with [human_1_QS, human_2_QS, mouse_1_QS, mouse_2_QS]
        for read in humanlist:
            if 0x4&read.flag: # flag 0x4 means unaligned
                continue
            QScore = read.opt('XO') + read.opt('NM') + read.opt('NH')
           # directionality (_1 or _2)
            d12 = 0 if 0x40&read.flag else 1
            if sa[d12]>QScore:
                sa[d12]=QScore # update to lowest (i.e. 'best') quality score
        for read in mouselist:
            if 0x4&read.flag: # flag 0x4 means unaligned
                continue
            QScore = read.opt('XO') + read.opt('NM') + read.opt('NH')
           # directionality (_1 or _2)
            d12 = 2 if 0x40&read.flag else 3
            if sa[d12]>QScore:
                sa[d12]=QScore # update to lowest (i.e. 'best') quality score
        if min(sa[0:2])==min(sa[2:4]) and max(sa[0:2])==max(sa[2:4]): # ambiguous
            return 0
        elif min(sa[0:2]) < min(sa[2:4]) or min(sa[0:2]) == min(sa[2:4]) and max(sa[0:2]) < max(sa[2:4]):
            # assign to human
            return 1
        else:
            # assign to mouse
            return -1
    elif disambalgo.lower() in ('bwa', 'star'):
        dv = -2^13 # default value, low
        bwatags = ['AS', 'NM']# ,'XS'] # in order of importance (compared sequentially, not as a sum as for tophat)
        bwatagsigns = [1, -1]#,1] # for AS and XS higher is better. for NM lower is better, thus multiply by -1
        AS = list()
        for x in range(0, len(bwatagsigns)):
            AS.append(array('i',(dv for i in range(0,4)))) # alignment score array, with [human_1_Score, human_2_Score, mouse_1_Score, mouse_2_Score]
        #
        for read in humanlist:
            if 0x4&read.flag: # flag 0x4 means unaligned
                continue
            # directionality (_1 or _2)
            d12 = 0 if 0x40&read.flag else 1
            for x in range(0, len(bwatagsigns)):
                try:
                    QScore = bwatagsigns[x]*read.opt(bwatags[x])
                except KeyError:
                    if bwatags[x] == 'NM':
                        bwatags[x] = 'nM' # oddity of STAR
                    QScore = bwatagsigns[x]*read.opt(bwatags[x])
                    
                if AS[x][d12]<QScore:
                    AS[x][d12]=QScore # update to highest (i.e. 'best') quality score
        #
        for read in mouselist:
            if 0x4&read.flag: # flag 0x4 means unaligned
                continue
           # directionality (_1 or _2)
            d12 = 2 if 0x40&read.flag else 3
            for x in range(0, len(bwatagsigns)):
                try:
                    QScore = bwatagsigns[x]*read.opt(bwatags[x])
                except KeyError:
                    if bwatags[x] == 'NM':
                        bwatags[x] = 'nM' # oddity of STAR
                    QScore = bwatagsigns[x]*read.opt(bwatags[x])
                
                if AS[x][d12]<QScore:
                    AS[x][d12]=QScore # update to highest (i.e. 'best') quality score
        #
        for x in range(0, len(bwatagsigns)):
            if max(AS[x][0:2]) > max(AS[x][2:4]) or max(AS[x][0:2]) == max(AS[x][2:4]) and min(AS[x][0:2]) > min(AS[x][2:4]):
                # assign to human
                return 1
            elif max(AS[x][0:2]) < max(AS[x][2:4]) or max(AS[x][0:2]) == max(AS[x][2:4]) and min(AS[x][0:2]) < min(AS[x][2:4]):
                # assign to mouse
                return -1
        return 0 # ambiguous
    else:
        print("Not implemented yet")
        sys.exit(2)


#code
def main(args):
    numhum = nummou = numamb = 0
    #starttime = time.clock()
    # parse inputs
    humanfilename = args.A
    mousefilename = args.B
    samplenameprefix = args.prefix
    outputdir = args.output_dir
    intermdir = args.intermediate_dir
    disablesort = args.no_sort
    disambalgo = args.aligner
    supportedalgorithms = set(['tophat', 'bwa', 'star'])

    # check existence of input BAM files
    if not (file_exists(humanfilename) and file_exists(mousefilename)):
        sys.stderr.write("\nERROR in disambiguate.py: Two existing input BAM files "
                         "must be specified as positional arguments\n")
        sys.exit(2)
    if len(samplenameprefix) < 1:
        humanprefix = path.basename(humanfilename.replace(".bam",""))
        mouseprefix = path.basename(mousefilename.replace(".bam",""))
    else:
        if samplenameprefix.endswith(".bam"):
            samplenameprefix = samplenameprefix[0:samplenameprefix.rfind(".bam")] # the above if is not stricly necessary for this to work
        humanprefix = samplenameprefix
        mouseprefix = samplenameprefix
    samplenameprefix = None # clear variable
    if disambalgo.lower() not in supportedalgorithms:
        print(disambalgo+" is not a supported disambiguation scheme at the moment.")
        sys.exit(2)

    if disablesort:
        humanfilenamesorted = humanfilename # assumed to be sorted externally...
        mousefilenamesorted = mousefilename # assumed to be sorted externally...
    else:
        if not path.isdir(intermdir):
            makedirs(intermdir)
        humanfilenamesorted = path.join(intermdir,humanprefix+".speciesA.namesorted.bam")
        mousefilenamesorted = path.join(intermdir,mouseprefix+".speciesB.namesorted.bam")
        if not path.isfile(humanfilenamesorted):
            pysam.sort("-n","-m","2000000000",humanfilename,humanfilenamesorted.replace(".bam",""))
        if not path.isfile(mousefilenamesorted):
            pysam.sort("-n","-m","2000000000",mousefilename,mousefilenamesorted.replace(".bam",""))
   # read in human reads and form a dictionary
    myHumanFile = pysam.Samfile(humanfilenamesorted, "rb" )
    myMouseFile = pysam.Samfile(mousefilenamesorted, "rb" )
    if not path.isdir(outputdir):
        makedirs(outputdir)
    myHumanUniqueFile = pysam.Samfile(path.join(outputdir, humanprefix+".disambiguatedSpeciesA.bam"), "wb", template=myHumanFile)
    myHumanAmbiguousFile = pysam.Samfile(path.join(outputdir, humanprefix+".ambiguousSpeciesA.bam"), "wb", template=myHumanFile)
    myMouseUniqueFile = pysam.Samfile(path.join(outputdir, mouseprefix+".disambiguatedSpeciesB.bam"), "wb", template=myMouseFile)
    myMouseAmbiguousFile = pysam.Samfile(path.join(outputdir, mouseprefix+".ambiguousSpeciesB.bam"), "wb", template=myMouseFile)
    summaryFile = open(path.join(outputdir,humanprefix+'_summary.txt'),'w')

    #initialise
    try:
        nexthumread=myHumanFile.next()
        nextmouread=myMouseFile.next()
    except StopIteration:
        print("No reads in one or either of the input files")
        sys.exit(2)

    EOFmouse = EOFhuman = False
    prevHumID = '-+=RANDOMSTRING=+-'
    prevMouID = '-+=RANDOMSTRING=+-'
    while not EOFmouse&EOFhuman:
        while not (nat_cmp(nexthumread.qname,nextmouread.qname) == 0):
            # check order between current human and mouse qname (find a point where they're identical, i.e. in sync)
            while nat_cmp(nexthumread.qname,nextmouread.qname) > 0 and not EOFmouse: # mouse is "behind" human, output to mouse disambiguous
                myMouseUniqueFile.write(nextmouread)
                if not nextmouread.qname == prevMouID:
                    nummou+=1 # increment mouse counter for unique only
                prevMouID = nextmouread.qname
                try:
                    nextmouread=myMouseFile.next()
                except StopIteration:
                    EOFmouse=True
            while nat_cmp(nexthumread.qname,nextmouread.qname) < 0 and not EOFhuman: # human is "behind" mouse, output to human disambiguous
                myHumanUniqueFile.write(nexthumread)
                if not nexthumread.qname == prevHumID:
                    numhum+=1 # increment human counter for unique only
                prevHumID = nexthumread.qname
                try:
                    nexthumread=myHumanFile.next()
                except StopIteration:
                    EOFhuman=True
            if EOFhuman or EOFmouse:
                break
        # at this point the read qnames are identical and/or we've reached EOF
        humlist = list()
        moulist = list()
        if nat_cmp(nexthumread.qname,nextmouread.qname) == 0:
            humlist.append(nexthumread)
            nexthumread = read_next_reads(myHumanFile, humlist) # read more reads with same qname (the function modifies humlist directly)
            if nexthumread == None:
                EOFhuman = True
            moulist.append(nextmouread)
            nextmouread = read_next_reads(myMouseFile, moulist) # read more reads with same qname (the function modifies moulist directly)
            if nextmouread == None:
                EOFmouse = True

        # perform comparison to check mouse, human or ambiguous
        if len(moulist) > 0 and len(humlist) > 0:
            myAmbiguousness = disambiguate(humlist, moulist, disambalgo)
            if myAmbiguousness < 0: # mouse
                nummou+=1 # increment mouse counter
                for myRead in moulist:
                    myMouseUniqueFile.write(myRead)
            elif myAmbiguousness > 0: # human
                numhum+=1 # increment human counter
                for myRead in humlist:
                    myHumanUniqueFile.write(myRead)
            else: # ambiguous
                numamb+=1 # increment ambiguous counter
                for myRead in moulist:
                    myMouseAmbiguousFile.write(myRead)
                for myRead in humlist:
                    myHumanAmbiguousFile.write(myRead)
        if EOFhuman:
            #flush the rest of the mouse reads
            while not EOFmouse:
                myMouseUniqueFile.write(nextmouread)
                if not nextmouread.qname == prevMouID:
                    nummou+=1 # increment mouse counter for unique only
                prevMouID = nextmouread.qname
                try:
                    nextmouread=myMouseFile.next()
                except StopIteration:
                    #print("3")
                    EOFmouse=True
        if EOFmouse:
            #flush the rest of the human reads
            while not EOFhuman:
                myHumanUniqueFile.write(nexthumread)
                if not nexthumread.qname == prevHumID:
                    numhum+=1 # increment human counter for unique only
                prevHumID = nexthumread.qname
                try:
                    nexthumread=myHumanFile.next()
                except StopIteration:
                    EOFhuman=True

    summaryFile.write("sample\tunique species A pairs\tunique species B pairs\tambiguous pairs\n")
    summaryFile.write(humanprefix+"\t"+str(numhum)+"\t"+str(nummou)+"\t"+str(numamb)+"\n")
    summaryFile.close()
    myHumanFile.close()
    myMouseFile.close()
    myHumanUniqueFile.close()
    myHumanAmbiguousFile.close()
    myMouseUniqueFile.close()
    myMouseAmbiguousFile.close()


def file_exists(fname):
    """Check if a file exists and is non-empty.
    """
    return path.exists(fname) and path.getsize(fname) > 0

if __name__ == "__main__":
   description = """
disambiguate.py disambiguates between two organisms that have alignments
from the same source of fastq files. An example where this might be
useful is as part of an explant RNA/DNA-Seq workflow where an informatics
approach is used to distinguish between human and mouse RNA/DNA reads.

For reads that have aligned to both organisms, the functionality is based on
comparing quality scores from either Tophat of BWA. Read
name is used to collect all alignments for both mates (_1 and _2) and
compared between human and mouse alignments.

For tophat (default, can be changed using option -a), the sum of the tags XO,
NM and NH is evaluated and the lowest sum wins the paired end reads. For equal
scores (both mates, both species), the reads are assigned as ambiguous.

The alternative algorithm (STAR, bwa) disambiguates (for aligned reads) by tags
AS (alignment score, higher better), followed by NM (edit distance, lower 
better).

The output directory will contain four files:\n
...disambiguatedSpeciesA.bam: Reads that could be assigned to species A
...disambiguatedSpeciesB.bam: Reads that could be assigned to species B
...ambiguousSpeciesA.bam: Reads aligned to species A that also aligned \n\tto B but could not be uniquely assigned to either
...ambiguousSpeciesB.bam: Reads aligned to species B that also aligned \n\tto A but could not be uniquely assigned to either
..._summary.txt: A summary of unique read names assigned to species A, B \n\tand ambiguous.

Examples:
disambiguate.py test/human.bam test/mouse.bam
disambiguate.py -s mysample1 test/human.bam test/mouse.bam
   """

   parser = ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
   parser.add_argument('A', help='Input BAM file for species A.')
   parser.add_argument('B', help='Input BAM file for species B.')
   parser.add_argument('-o', '--output-dir', default="disambres",
                       help='Output directory.')
   parser.add_argument('-i', '--intermediate-dir', default="intermfiles",
                       help='Location to store intermediate files')
   parser.add_argument('-d', '--no-sort', action='store_true', default=False,
                       help='Disable BAM file sorting. Use this option if the '
                       'files have already been name sorted.')
   parser.add_argument('-s', '--prefix', default='',
                       help='A prefix (e.g. sample name) to use for the output '
                       'BAM files. If not provided, the input BAM file prefix '
                       'will be used. Do not include .bam in the prefix.')
   parser.add_argument('-a', '--aligner', default='tophat',
                       choices=('tophat', 'bwa', 'star'),
                       help='The aligner used to generate these reads. Some '
                       'aligners set different tags.')
   args = parser.parse_args()
   main(args)

########NEW FILE########
__FILENAME__ = fastq
"""Pipeline utilities to retrieve FASTQ formatted files for processing.
"""
import os
import subprocess

from bcbio import bam, broad
from bcbio.bam import cram
from bcbio.pipeline import alignment
from bcbio.utils import file_exists, safe_makedir
from bcbio.distributed.transaction import file_transaction

def get_fastq_files(item):
    """Retrieve fastq files for the given lane, ready to process.
    """
    assert "files" in item, "Did not find `files` in input; nothing to process"
    ready_files = []
    for fname in item["files"]:
        if fname.endswith(".gz") and _pipeline_needs_fastq(item["config"], item):
            fastq_dir = os.path.join(item["dirs"]["work"], "fastq")
            safe_makedir(fastq_dir)
            out_file = os.path.join(fastq_dir,
                                    os.path.basename(os.path.splitext(fname)[0]))
            if not os.path.exists(out_file):
                with file_transaction(out_file) as tx_out_file:
                    cmd = "gunzip -c {fname} > {tx_out_file}".format(**locals())
                    with open(tx_out_file, "w") as out_handle:
                        subprocess.check_call(cmd, shell=True)
            ready_files.append(out_file)
        elif fname.endswith(".bam"):
            if _pipeline_needs_fastq(item["config"], item):
                ready_files = _convert_bam_to_fastq(fname, item["dirs"]["work"],
                                                    item, item["dirs"], item["config"])
            else:
                ready_files = [fname]
        else:
            assert os.path.exists(fname), fname
            ready_files.append(fname)
    ready_files = [x for x in ready_files if x is not None]
    return ((ready_files[0] if len(ready_files) > 0 else None),
            (ready_files[1] if len(ready_files) > 1 else None))

def _pipeline_needs_fastq(config, item):
    """Determine if the pipeline can proceed with a BAM file, or needs fastq conversion.
    """
    aligner = config["algorithm"].get("aligner")
    support_bam = aligner in alignment.metadata.get("support_bam", [])
    return aligner and not support_bam

def _convert_bam_to_fastq(in_file, work_dir, item, dirs, config):
    """Convert BAM input file into FASTQ files.
    """
    out_dir = safe_makedir(os.path.join(work_dir, "fastq_convert"))

    qual_bin_method = config["algorithm"].get("quality_bin")
    if (qual_bin_method == "prealignment" or
         (isinstance(qual_bin_method, list) and "prealignment" in qual_bin_method)):
        out_bindir = safe_makedir(os.path.join(out_dir, "qualbin"))
        in_file = cram.illumina_qual_bin(in_file, item["sam_ref"], out_bindir, config)

    out_files = [os.path.join(out_dir, "{0}_{1}.fastq".format(
                 os.path.splitext(os.path.basename(in_file))[0], x))
                 for x in ["1", "2"]]
    if bam.is_paired(in_file):
        out1, out2 = out_files
    else:
        out1 = out_files[0]
        out2 = None
    if not file_exists(out1):
        broad_runner = broad.runner_from_config(config)
        broad_runner.run_fn("picard_bam_to_fastq", in_file, out1, out2)
    if os.path.getsize(out2) == 0:
        out2 = None
    return [out1, out2]

########NEW FILE########
__FILENAME__ = genome
"""Read genome build configurations from Galaxy *.loc and bcbio-nextgen resource files.
"""
import ConfigParser
import glob
import os
from xml.etree import ElementTree

import yaml

from bcbio import utils
from bcbio.pipeline import alignment

# ## bcbio-nextgen genome resource files

def get_resources(genome, ref_file):
    """Retrieve genome information from a genome-references.yaml file.
    """
    base_dir = os.path.normpath(os.path.dirname(ref_file))
    resource_file = os.path.join(base_dir, "%s-resources.yaml" % genome)
    if not os.path.exists(resource_file):
        raise IOError("Did not find resource file for %s: %s\n"
                      "To update bcbio_nextgen.py with genome resources for standard builds, run:\n"
                      "bcbio_nextgen.py upgrade -u skip"
                      % (genome, resource_file))
    with open(resource_file) as in_handle:
        resources = yaml.load(in_handle)

    def resource_file_path(x):
        if isinstance(x, basestring) and os.path.exists(os.path.join(base_dir, x)):
            return os.path.normpath(os.path.join(base_dir, x))
        return x

    return utils.dictapply(resources, resource_file_path)

# ## Utilities


def abs_file_paths(xs, base_dir=None, ignore_keys=None):
    """Normalize any file paths found in a subdirectory of configuration input.
    """
    ignore_keys = set([]) if ignore_keys is None else set(ignore_keys)
    if not isinstance(xs, dict):
        return xs
    if base_dir is None:
        base_dir = os.getcwd()
    orig_dir = os.getcwd()
    os.chdir(base_dir)
    out = {}
    for k, v in xs.iteritems():
        if k not in ignore_keys and v and isinstance(v, basestring):
            if v.lower() == "none":
                out[k] = None
            elif os.path.exists(v):
                out[k] = os.path.normpath(os.path.join(base_dir, v))
            else:
                out[k] = v
        else:
            out[k] = v
    os.chdir(orig_dir)
    return out

# ## Galaxy integration -- *.loc files

def _get_galaxy_loc_file(name, galaxy_dt, ref_dir, galaxy_base):
    """Retrieve Galaxy *.loc file for the given reference/aligner name.

    First tries to find an aligner specific *.loc file. If not defined
    or does not exist, then we need to try and remap it from the
    default reference file
    """
    if "file" in galaxy_dt and os.path.exists(os.path.join(galaxy_base, galaxy_dt["file"])):
        loc_file = os.path.join(galaxy_base, galaxy_dt["file"])
        need_remap = False
    elif alignment.TOOLS[name].galaxy_loc_file is None:
        loc_file = os.path.join(ref_dir, alignment.BASE_LOCATION_FILE)
        need_remap = True
    else:
        loc_file = os.path.join(ref_dir, alignment.TOOLS[name].galaxy_loc_file)
        need_remap = False
    if not os.path.exists(loc_file):
        loc_file = os.path.join(ref_dir, alignment.BASE_LOCATION_FILE)
        need_remap = True
    return loc_file, need_remap

def _galaxy_loc_iter(loc_file, galaxy_dt, need_remap=False):
    """Iterator returning genome build and references from Galaxy *.loc file.
    """
    if "column" in galaxy_dt:
        dbkey_i = galaxy_dt["column"].index("dbkey")
        path_i = galaxy_dt["column"].index("path")
    else:
        dbkey_i = None
    with open(loc_file) as in_handle:
        for line in in_handle:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("\t")
                # Detect and report spaces instead of tabs
                if len(parts) == 1:
                    parts = [x.strip() for x in line.strip().split(" ") if x.strip()]
                    if len(parts) > 1:
                        raise IOError("Galaxy location file uses spaces instead of "
                                      "tabs to separate fields: %s" % loc_file)
                if dbkey_i is not None and not need_remap:
                    dbkey = parts[dbkey_i]
                    cur_ref = parts[path_i]
                else:
                    if parts[0] == "index":
                        parts = parts[1:]
                    dbkey = parts[0]
                    cur_ref = parts[-1]
                yield (dbkey, cur_ref)

def _get_ref_from_galaxy_loc(name, genome_build, loc_file, galaxy_dt, need_remap,
                             galaxy_config):
    """Retrieve reference genome file from Galaxy *.loc file.

    Reads from tool_data_table_conf.xml information for the index if it
    exists, otherwise uses heuristics to find line based on most common setups.
    """
    refs = [ref for dbkey, ref in _galaxy_loc_iter(loc_file, galaxy_dt, need_remap)
            if dbkey == genome_build]
    if len(refs) == 0:
        raise IndexError("Genome %s not found in %s" % (genome_build, loc_file))
    # allow multiple references in a file and use the most recently added
    else:
        cur_ref = refs[-1]
    if need_remap:
        remap_fn = alignment.TOOLS[name].remap_index_fn
        cur_ref = os.path.normpath(utils.add_full_path(cur_ref, galaxy_config["tool_data_path"]))
        assert remap_fn is not None, "%s requires remapping function from base location file" % name
        cur_ref = remap_fn(os.path.abspath(cur_ref))
    return cur_ref

def _get_galaxy_tool_info(galaxy_base):
    """Retrieve Galaxy tool-data information from defaults or galaxy config file.
    """
    ini_file = os.path.join(galaxy_base, "universe_wsgi.ini")
    info = {"tool_data_table_config_path": os.path.join(galaxy_base, "tool_data_table_conf.xml"),
            "tool_data_path": os.path.join(galaxy_base, "tool-data")}
    config = ConfigParser.ConfigParser()
    config.read(ini_file)
    if "app:main" in config.sections():
        for option in config.options("app:main"):
            if option in info:
                info[option] = os.path.join(galaxy_base, config.get("app:main", option))
    return info

def _get_galaxy_data_table(name, dt_config_file):
    """Parse data table config file for details on tool *.loc location and columns.
    """
    out = {}
    if os.path.exists(dt_config_file):
        tdtc = ElementTree.parse(dt_config_file)
        for t in tdtc.getiterator("table"):
            if t.attrib.get("name", "") in [name, "%s_indexes" % name]:
                out["column"] = [x.strip() for x in t.find("columns").text.split(",")]
                out["file"] = t.find("file").attrib.get("path", "")
    return out

def get_refs(genome_build, aligner, galaxy_base):
    """Retrieve the reference genome file location from galaxy configuration.
    """
    out = {}
    name_remap = {"samtools": "fasta"}
    if genome_build:
        galaxy_config = _get_galaxy_tool_info(galaxy_base)
        for name in [x for x in (aligner, "samtools") if x]:
            galaxy_dt = _get_galaxy_data_table(name, galaxy_config["tool_data_table_config_path"])
            loc_file, need_remap = _get_galaxy_loc_file(name, galaxy_dt, galaxy_config["tool_data_path"],
                                                        galaxy_base)
            cur_ref = _get_ref_from_galaxy_loc(name, genome_build, loc_file, galaxy_dt, need_remap,
                                               galaxy_config)
            base = os.path.normpath(utils.add_full_path(cur_ref, galaxy_config["tool_data_path"]))
            if os.path.isdir(base):
                indexes = glob.glob(os.path.join(base, "*"))
            else:
                indexes = glob.glob("%s*" % utils.splitext_plus(base)[0])
            if base in indexes:
                indexes.remove(base)
            out[name_remap.get(name, name)] = {"base": base, "indexes": indexes}
    return out

def get_builds(galaxy_base):
    """Retrieve configured genome builds and reference files, using Galaxy configuration files.

    Allows multiple dbkey specifications in the same file, using the most recently added.
    """
    name = "samtools"
    galaxy_config = _get_galaxy_tool_info(galaxy_base)
    galaxy_dt = _get_galaxy_data_table(name, galaxy_config["tool_data_table_config_path"])
    loc_file, need_remap = _get_galaxy_loc_file(name, galaxy_dt, galaxy_config["tool_data_path"],
                                                galaxy_base)
    assert not need_remap, "Should not need to remap reference files"
    fnames = {}
    for dbkey, fname in _galaxy_loc_iter(loc_file, galaxy_dt):
        fnames[dbkey] = fname
    out = []
    for dbkey in sorted(fnames.keys()):
        out.append((dbkey, fnames[dbkey]))
    return out

########NEW FILE########
__FILENAME__ = lane
"""Top level driver functionality for processing a sequencing lane.
"""
import copy
import os

from bcbio import bam, broad, utils
from bcbio.log import logger
from bcbio.bam import callable, fastq
from bcbio.bam.trim import trim_adapters
from bcbio.ngsalign import postalign
from bcbio.pipeline.fastq import get_fastq_files
from bcbio.pipeline.alignment import align_to_sort_bam
from bcbio.pipeline import cleanbam
from bcbio.variation import bedutils, recalibrate

def process_lane(item):
    """Prepare lanes, potentially splitting based on barcodes and reducing the
    number of reads for a test run
    """
    NUM_DOWNSAMPLE = 10000
    logger.debug("Preparing %s" % item["rgnames"]["lane"])
    file1, file2 = get_fastq_files(item)
    if item.get("test_run", False):
        if bam.is_bam(file1):
            file1 = bam.downsample(file1, item, NUM_DOWNSAMPLE)
            file2 = None
        else:
            file1, file2 = fastq.downsample(file1, file2, item,
                                            NUM_DOWNSAMPLE, quick=True)
    item["files"] = [file1, file2]
    return [[item]]

def trim_lane(item):
    """Trim reads with the provided trimming method.
    Support methods: read_through.
    """
    to_trim = [x for x in item["files"] if x is not None]
    dirs = item["dirs"]
    config = item["config"]
    # this block is to maintain legacy configuration files
    trim_reads = config["algorithm"].get("trim_reads", False)
    if not trim_reads:
        logger.info("Skipping trimming of %s." % (", ".join(to_trim)))
        return [[item]]

    if trim_reads == "read_through":
        logger.info("Trimming low quality ends and read through adapter "
                    "sequence from %s." % (", ".join(to_trim)))
        out_files = trim_adapters(to_trim, dirs, config)
    item["files"] = out_files
    return [[item]]

# ## Alignment

def link_bam_file(orig_file, new_dir):
    """Provide symlinks of BAM file and existing indexes.
    """
    new_dir = utils.safe_makedir(new_dir)
    sym_file = os.path.join(new_dir, os.path.basename(orig_file))
    utils.symlink_plus(orig_file, sym_file)
    return sym_file

def _add_supplemental_bams(data):
    """Add supplemental files produced by alignment, useful for structural variant calling.
    """
    file_key = "work_bam"
    if data.get(file_key):
        for supext in ["disc", "sr"]:
            base, ext = os.path.splitext(data[file_key])
            test_file = "%s-%s%s" % (base, supext, ext)
            if os.path.exists(test_file):
                sup_key = file_key + "-plus"
                if not sup_key in data:
                    data[sup_key] = {}
                data[sup_key][supext] = test_file
    return data

def process_alignment(data):
    """Do an alignment of fastq files, preparing a sorted BAM output file.
    """
    if "files" not in data:
        fastq1, fastq2 = None, None
    elif len(data["files"]) == 2:
        fastq1, fastq2 = data["files"]
    else:
        assert len(data["files"]) == 1, data["files"]
        fastq1, fastq2 = data["files"][0], None
    config = data["config"]
    aligner = config["algorithm"].get("aligner", None)
    if fastq1 and os.path.exists(fastq1) and aligner:
        logger.info("Aligning lane %s with %s aligner" % (data["rgnames"]["lane"], aligner))
        data = align_to_sort_bam(fastq1, fastq2, aligner, data)
        data = _add_supplemental_bams(data)
    elif fastq1 and os.path.exists(fastq1) and fastq1.endswith(".bam"):
        sort_method = config["algorithm"].get("bam_sort")
        bamclean = config["algorithm"].get("bam_clean")
        if bamclean is True or bamclean == "picard":
            if sort_method and sort_method != "coordinate":
                raise ValueError("Cannot specify `bam_clean: picard` with `bam_sort` other than coordinate: %s"
                                 % sort_method)
            out_bam = cleanbam.picard_prep(fastq1, data["rgnames"], data["sam_ref"], data["dirs"],
                                           config)
        elif sort_method:
            runner = broad.runner_from_config(config)
            out_file = os.path.join(data["dirs"]["work"], "{}-sort.bam".format(
                os.path.splitext(os.path.basename(fastq1))[0]))
            out_bam = runner.run_fn("picard_sort", fastq1, sort_method, out_file)
        else:
            out_bam = link_bam_file(fastq1, os.path.join(data["dirs"]["work"], "prealign",
                                                         data["rgnames"]["sample"]))
        bam.check_header(out_bam, data["rgnames"], data["sam_ref"], data["config"])
        dedup_bam = postalign.dedup_bam(out_bam, data)
        data["work_bam"] = dedup_bam
    elif fastq1 is None and "vrn_file" in data:
        data["config"]["algorithm"]["variantcaller"] = ""
        data["work_bam"] = None
    else:
        raise ValueError("Could not process input file: %s" % fastq1)
    return [[data]]

def postprocess_alignment(data):
    """Perform post-processing steps required on full BAM files.
    Prepares list of callable genome regions allowing subsequent parallelization.
    Cleans input BED files to avoid issues with overlapping input segments.
    """
    data = bedutils.clean_inputs(data)
    if data["work_bam"]:
        callable_region_bed, nblock_bed, callable_bed = \
            callable.block_regions(data["work_bam"], data["sam_ref"], data["config"])
        data["regions"] = {"nblock": nblock_bed, "callable": callable_bed}
        if (os.path.exists(callable_region_bed) and
                not data["config"]["algorithm"].get("variant_regions")):
            data["config"]["algorithm"]["variant_regions"] = callable_region_bed
            data = bedutils.clean_inputs(data)
        data = _recal_no_markduplicates(data)
    return [data]

def _recal_no_markduplicates(data):
    orig_config = copy.deepcopy(data["config"])
    data["config"]["algorithm"]["mark_duplicates"] = False
    data = recalibrate.prep_recal(data)[0][0]
    data["config"] = orig_config
    return data

########NEW FILE########
__FILENAME__ = main
"""Main entry point for distributed next-gen sequencing pipelines.

Handles running the full pipeline based on instructions
"""
import abc
from collections import defaultdict
import copy
import os
import sys
import argparse
import resource
import tempfile

from bcbio import install, log, structural, utils, upload
from bcbio.distributed import clargs, prun, runfn
from bcbio.illumina import flowcell, machine
from bcbio.log import logger
from bcbio.ngsalign import alignprep
from bcbio.pipeline import (archive, disambiguate, region, run_info, qcsummary,
                            version, rnaseq)
from bcbio.pipeline.config_utils import load_system_config
from bcbio.provenance import programs, profile, system, versioncheck
from bcbio.server import main as server_main
from bcbio.variation import coverage, ensemble, genotype, population, validate
from bcbio.rnaseq.count import (combine_count_files,
                                annotate_combined_count_file)

def run_main(workdir, config_file=None, fc_dir=None, run_info_yaml=None,
             parallel=None, workflow=None):
    """Run variant analysis, handling command line options.
    """
    os.chdir(workdir)
    config, config_file = load_system_config(config_file, workdir)
    if config.get("log_dir", None) is None:
        config["log_dir"] = os.path.join(workdir, "log")
    if parallel["type"] in ["local", "clusterk"]:
        _setup_resources()
        _run_toplevel(config, config_file, workdir, parallel,
                      fc_dir, run_info_yaml)
    elif parallel["type"] == "ipython":
        assert parallel["scheduler"] is not None, "IPython parallel requires a specified scheduler (-s)"
        if parallel["scheduler"] != "sge":
            assert parallel["queue"] is not None, "IPython parallel requires a specified queue (-q)"
        elif not parallel["queue"]:
            parallel["queue"] = ""
        _run_toplevel(config, config_file, workdir, parallel,
                      fc_dir, run_info_yaml)
    else:
        raise ValueError("Unexpected type of parallel run: %s" % parallel["type"])

def _setup_resources():
    """Attempt to increase resource limits up to hard limits.

    This allows us to avoid out of file handle limits where we can
    move beyond the soft limit up to the hard limit.
    """
    target_procs = 10240
    cur_proc, max_proc = resource.getrlimit(resource.RLIMIT_NPROC)
    target_proc = min(max_proc, target_procs) if max_proc > 0 else target_procs
    resource.setrlimit(resource.RLIMIT_NPROC, (max(cur_proc, target_proc), max_proc))
    cur_hdls, max_hdls = resource.getrlimit(resource.RLIMIT_NOFILE)
    target_hdls = min(max_hdls, target_procs) if max_hdls > 0 else target_procs
    resource.setrlimit(resource.RLIMIT_NOFILE, (max(cur_hdls, target_hdls), max_hdls))

def _run_toplevel(config, config_file, work_dir, parallel,
                  fc_dir=None, run_info_yaml=None):
    """
    Run toplevel analysis, processing a set of input files.
    config_file -- Main YAML configuration file with system parameters
    fc_dir -- Directory of fastq files to process
    run_info_yaml -- YAML configuration file specifying inputs to process
    """
    parallel = log.create_base_logger(config, parallel)
    log.setup_local_logging(config, parallel)
    dirs = setup_directories(work_dir, fc_dir, config, config_file)
    config_file = os.path.join(dirs["config"], os.path.basename(config_file))
    samples = run_info.organize(dirs, config, run_info_yaml)
    pipelines = _pair_lanes_with_pipelines(samples)
    final = []
    with utils.curdir_tmpdir({"config": config}) as tmpdir:
        tempfile.tempdir = tmpdir
        for pipeline, pipeline_items in pipelines.items():
            pipeline_items = _add_provenance(pipeline_items, dirs, parallel, config)
            versioncheck.testall(pipeline_items)
            for xs in pipeline.run(config, config_file, parallel, dirs, pipeline_items):
                if len(xs) == 1:
                    upload.from_sample(xs[0])
                    final.append(xs[0])

def setup_directories(work_dir, fc_dir, config, config_file):
    fastq_dir, galaxy_dir, config_dir = _get_full_paths(flowcell.get_fastq_dir(fc_dir)
                                                        if fc_dir else None,
                                                        config, config_file)
    return {"fastq": fastq_dir, "galaxy": galaxy_dir,
            "work": work_dir, "flowcell": fc_dir, "config": config_dir}

def _add_provenance(items, dirs, parallel, config):
    p = programs.write_versions(dirs, config, is_wrapper=parallel.get("wrapper") is not None)
    system.write_info(dirs, parallel, config)
    out = []
    for item in items:
        if item.get("upload") and item["upload"].get("fc_name"):
            entity_id = "%s.%s.%s" % (item["upload"]["fc_date"],
                                      item["upload"]["fc_name"],
                                      item["description"])
        else:
            entity_id = item["description"]
        item["config"]["resources"]["program_versions"] = p
        item["provenance"] = {"programs": p, "entity": entity_id}
        out.append([item])
    return out

# ## Utility functions

def _sanity_check_args(args):
    """Ensure dependent arguments are correctly specified
    """
    if "scheduler" in args and "queue" in args:
        if args.scheduler and not args.queue:
            if args.scheduler != "sge":
                return "IPython parallel scheduler (-s) specified. This also requires a queue (-q)."
        elif args.queue and not args.scheduler:
            return "IPython parallel queue (-q) supplied. This also requires a scheduler (-s)."
        elif args.paralleltype == "ipython" and (not args.queue or not args.scheduler):
            return "IPython parallel requires queue (-q) and scheduler (-s) arguments."

def _sanity_check_kwargs(args):
    """Sanity check after setting up input arguments, handling back compatibility
    """
    if not args.get("workflow") and not args.get("run_info_yaml"):
        return ("Require a sample YAML file describing inputs: "
                "https://bcbio-nextgen.readthedocs.org/en/latest/contents/configuration.html")

def parse_cl_args(in_args):
    """Parse input commandline arguments, handling multiple cases.

    Returns the main config file and set of kwargs.
    """
    sub_cmds = {"upgrade": install.add_subparser,
                "server": server_main.add_subparser,
                "runfn": runfn.add_subparser,
                "version": programs.add_subparser,
                "sequencer": machine.add_subparser}
    parser = argparse.ArgumentParser(
        description="Best-practice pipelines for fully automated high throughput sequencing analysis.")
    sub_cmd = None
    if len(in_args) > 0 and in_args[0] in sub_cmds:
        subparsers = parser.add_subparsers(help="bcbio-nextgen supplemental commands")
        sub_cmds[in_args[0]](subparsers)
        sub_cmd = in_args[0]
    else:
        parser.add_argument("global_config", help="Global YAML configuration file specifying details "
                            "about the system (optional, defaults to installed bcbio_system.yaml)",
                            nargs="?")
        parser.add_argument("fc_dir", help="A directory of Illumina output or fastq files to process (optional)",
                            nargs="?")
        parser.add_argument("run_config", help="YAML file with details about samples to process "
                            "(required, unless using Galaxy LIMS as input)",
                            nargs="*")
        parser.add_argument("-n", "--numcores", help="Total cores to use for processing",
                            type=int, default=1)
        parser.add_argument("-t", "--paralleltype", help="Approach to parallelization",
                            choices=["local", "ipython"], default="local")
        parser.add_argument("-s", "--scheduler", help="Scheduler to use for ipython parallel",
                            choices=["lsf", "sge", "torque", "slurm"])
        parser.add_argument("-q", "--queue", help="Scheduler queue to run jobs on, for ipython parallel")
        parser.add_argument("-r", "--resources",
                            help=("Cluster specific resources specifications. Can be specified multiple times.\n"
                                  "Supports SGE, Torque, LSF and SLURM parameters."),
                            default=[], action="append")
        parser.add_argument("--timeout", help="Number of minutes before cluster startup times out. Defaults to 15",
                            default=15, type=int)
        parser.add_argument("--retries",
                            help=("Number of retries of failed tasks during distributed processing. "
                                  "Default 0 (no retries)"),
                            default=0, type=int)
        parser.add_argument("-p", "--tag", help="Tag name to label jobs on the cluster",
                            default="")
        parser.add_argument("-w", "--workflow", help="Run a workflow with the given commandline arguments")
        parser.add_argument("--workdir", help="Directory to process in. Defaults to current working directory",
                            default=os.getcwd())
        parser.add_argument("-v", "--version", help="Print current version",
                            action="store_true")
    args = parser.parse_args(in_args)
    if hasattr(args, "global_config"):
        error_msg = _sanity_check_args(args)
        if error_msg:
            parser.error(error_msg)
        kwargs = {"parallel": clargs.to_parallel(args),
                  "workflow": args.workflow,
                  "workdir": args.workdir}
        kwargs = _add_inputs_to_kwargs(args, kwargs, parser)
        error_msg = _sanity_check_kwargs(kwargs)
        if error_msg:
            parser.error(error_msg)
    else:
        assert sub_cmd is not None
        kwargs = {"args": args,
                  "config_file": None,
                  sub_cmd: True}
    return kwargs

def _add_inputs_to_kwargs(args, kwargs, parser):
    """Convert input system config, flow cell directory and sample yaml to kwargs.

    Handles back compatibility with previous commandlines while allowing flexible
    specification of input parameters.
    """
    inputs = [x for x in [args.global_config, args.fc_dir] + args.run_config
              if x is not None]
    global_config = "bcbio_system.yaml"  # default configuration if not specified
    if len(inputs) == 1:
        if os.path.isfile(inputs[0]):
            fc_dir = None
            run_info_yaml = inputs[0]
        else:
            fc_dir = inputs[0]
            run_info_yaml = None
    elif len(inputs) == 2:
        if os.path.isfile(inputs[0]):
            global_config = inputs[0]
            if os.path.isfile(inputs[1]):
                fc_dir = None
                run_info_yaml = inputs[1]
            else:
                fc_dir = inputs[1]
                run_info_yaml = None
        else:
            fc_dir, run_info_yaml = inputs
    elif len(inputs) == 3:
        global_config, fc_dir, run_info_yaml = inputs
    elif kwargs.get("workflow", "") == "template":
        kwargs["inputs"] = inputs
        return kwargs
    elif args.version:
        print version.__version__
        sys.exit()
    else:
        print "Incorrect input arguments", inputs
        parser.print_help()
        sys.exit()
    if fc_dir:
        fc_dir = os.path.abspath(fc_dir)
    if run_info_yaml:
        run_info_yaml = os.path.abspath(run_info_yaml)
    if kwargs.get("workflow"):
        kwargs["inputs"] = inputs
    kwargs["config_file"] = global_config
    kwargs["fc_dir"] = fc_dir
    kwargs["run_info_yaml"] = run_info_yaml
    return kwargs

def _get_full_paths(fastq_dir, config, config_file):
    """Retrieve full paths for directories in the case of relative locations.
    """
    if fastq_dir:
        fastq_dir = utils.add_full_path(fastq_dir)
    config_dir = utils.add_full_path(os.path.dirname(config_file))
    galaxy_config_file = utils.add_full_path(config.get("galaxy_config", "universe_wsgi.ini"),
                                             config_dir)
    return fastq_dir, os.path.dirname(galaxy_config_file), config_dir

# ## Generic pipeline framework

def _wres(parallel, progs, fresources=None, ensure_mem=None):
    """Add resource information to the parallel environment on required programs and files.

    Enables spinning up required machines and operating in non-shared filesystem
    environments.

    progs -- Third party tools used in processing
    fresources -- Required file-based resources needed. These will be transferred on non-shared
                  filesystems.
    ensure_mem -- Dictionary of required minimum memory for programs used. Ensures
                  enough memory gets allocated on low-core machines.
    """
    parallel = copy.deepcopy(parallel)
    parallel["progs"] = progs
    if fresources:
        parallel["fresources"] = fresources
    if ensure_mem:
        parallel["ensure_mem"] = ensure_mem
    return parallel

class AbstractPipeline:
    """
    Implement this class to participate in the Pipeline abstraction.
    name: the analysis name in the run_info.yaml file:
        design:
            - analysis: name
    run: the steps run to perform the analyses
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def name(self):
        return

    @abc.abstractmethod
    def run(self, config, config_file, parallel, dirs, lanes):
        return

class Variant2Pipeline(AbstractPipeline):
    """Streamlined variant calling pipeline for large files.
    This is less generalized but faster in standard cases.
    The goal is to replace the base variant calling approach.
    """
    name = "variant2"

    @classmethod
    def run(self, config, config_file, parallel, dirs, samples):
        ## Alignment and preparation requiring the entire input file (multicore cluster)
        with prun.start(_wres(parallel, ["aligner", "samtools", "sambamba"],
                              (["reference", "fasta"], ["reference", "aligner"], ["files"])),
                        samples, config, dirs, "multicore",
                        multiplier=alignprep.parallel_multiplier(samples)) as run_parallel:
            with profile.report("alignment preparation", dirs):
                samples = run_parallel("prep_align_inputs", samples)
                samples = disambiguate.split(samples)
            with profile.report("alignment", dirs):
                samples = run_parallel("process_alignment", samples)
                samples = alignprep.merge_split_alignments(samples, run_parallel)
                samples = disambiguate.resolve(samples, run_parallel)
            with profile.report("callable regions", dirs):
                samples = run_parallel("postprocess_alignment", samples)
                samples = run_parallel("combine_sample_regions", [samples])
                samples = region.clean_sample_data(samples)
            with profile.report("coverage", dirs):
                samples = coverage.summarize_samples(samples, run_parallel)

        ## Variant calling on sub-regions of the input file (full cluster)
        with prun.start(_wres(parallel, ["gatk", "picard", "variantcaller"]),
                        samples, config, dirs, "full",
                        multiplier=region.get_max_counts(samples), max_multicore=1) as run_parallel:
            with profile.report("alignment post-processing", dirs):
                samples = region.parallel_prep_region(samples, run_parallel)
            with profile.report("variant calling", dirs):
                samples = genotype.parallel_variantcall_region(samples, run_parallel)

        ## Finalize variants (per-sample cluster)
        with prun.start(_wres(parallel, ["gatk", "gatk-vqsr", "snpeff", "bcbio_variation"]),
                        samples, config, dirs, "persample") as run_parallel:
            with profile.report("variant post-processing", dirs):
                samples = run_parallel("postprocess_variants", samples)
                samples = run_parallel("split_variants_by_sample", samples)
            with profile.report("validation", dirs):
                samples = run_parallel("compare_to_rm", samples)
                samples = genotype.combine_multiple_callers(samples)
        ## Finalizing BAMs and population databases, handle multicore computation
        with prun.start(_wres(parallel, ["gemini", "samtools", "fastqc", "bamtools", "bcbio_variation",
                                         "bcbio-variation-recall"]),
                        samples, config, dirs, "multicore2") as run_parallel:
            with profile.report("prepped BAM merging", dirs):
                samples = region.delayed_bamprep_merge(samples, run_parallel)
            with profile.report("ensemble calling", dirs):
                samples = ensemble.combine_calls_parallel(samples, run_parallel)
            with profile.report("validation summary", dirs):
                samples = validate.summarize_grading(samples)
            with profile.report("structural variation", dirs):
                samples = structural.run(samples, run_parallel)
            with profile.report("population database", dirs):
                samples = population.prep_db_parallel(samples, run_parallel)
            with profile.report("quality control", dirs):
                samples = qcsummary.generate_parallel(samples, run_parallel)
            with profile.report("archive", dirs):
                samples = archive.compress(samples, run_parallel)
        logger.info("Timing: finished")
        return samples

def _debug_samples(i, samples):
    print "---", i, len(samples)
    for sample in (x[0] for x in samples):
        print "  ", sample["description"], sample.get("region"), \
            utils.get_in(sample, ("config", "algorithm", "variantcaller")), \
            [x.get("variantcaller") for x in sample.get("variants", [])], \
            sample.get("work_bam")

class SNPCallingPipeline(Variant2Pipeline):
    """Back compatible: old name for variant analysis.
    """
    name = "SNP calling"

class VariantPipeline(Variant2Pipeline):
    """Back compatibility; old name
    """
    name = "variant"

class StandardPipeline(AbstractPipeline):
    """Minimal pipeline with alignment and QC.
    """
    name = "Standard"
    @classmethod
    def run(self, config, config_file, parallel, dirs, lane_items):
        ## Alignment and preparation requiring the entire input file (multicore cluster)
        with prun.start(_wres(parallel, ["aligner"]),
                        lane_items, config, dirs, "multicore") as run_parallel:
            with profile.report("alignment", dirs):
                samples = run_parallel("process_alignment", lane_items)
            with profile.report("callable regions", dirs):
                samples = run_parallel("postprocess_alignment", samples)
                samples = run_parallel("combine_sample_regions", [samples])
                samples = region.clean_sample_data(samples)
        ## Quality control
        with prun.start(_wres(parallel, ["fastqc", "bamtools", "samtools"]),
                        samples, config, dirs, "multicore2") as run_parallel:
            with profile.report("quality control", dirs):
                samples = qcsummary.generate_parallel(samples, run_parallel)
        logger.info("Timing: finished")
        return samples

class MinimalPipeline(StandardPipeline):
    name = "Minimal"

class RnaseqPipeline(AbstractPipeline):
    name = "RNA-seq"

    @classmethod
    def run(self, config, config_file, parallel, dirs, samples):
        with prun.start(_wres(parallel, ["picard", "AlienTrimmer"]),
                        samples, config, dirs, "trimming") as run_parallel:
            with profile.report("adapter trimming", dirs):
                samples = run_parallel("process_lane", samples)
                samples = run_parallel("trim_lane", samples)
        with prun.start(_wres(parallel, ["aligner"],
                              ensure_mem={"tophat": 8, "tophat2": 8, "star": 30}),
                        samples, config, dirs, "multicore",
                        multiplier=alignprep.parallel_multiplier(samples)) as run_parallel:
            with profile.report("alignment", dirs):
                samples = disambiguate.split(samples)
                samples = run_parallel("process_alignment", samples)

        with prun.start(_wres(parallel, ["samtools", "cufflinks"]),
                        samples, config, dirs, "rnaseqcount") as run_parallel:
            with profile.report("disambiguation", dirs):
                samples = disambiguate.resolve(samples, run_parallel)
            with profile.report("estimate expression", dirs):
                samples = rnaseq.estimate_expression(samples, run_parallel)

        combined = combine_count_files([x[0].get("count_file") for x in samples])
        gtf_file = utils.get_in(samples[0][0], ('genome_resources', 'rnaseq',
                                                'transcripts'), None)
        annotated = annotate_combined_count_file(combined, gtf_file)
        for x in samples:
            x[0]["combined_counts"] = combined
            if annotated:
                x[0]["annotated_combined_counts"] = annotated

        with prun.start(_wres(parallel, ["picard", "fastqc", "rnaseqc"]),
                        samples, config, dirs, "persample") as run_parallel:
            with profile.report("quality control", dirs):
                samples = qcsummary.generate_parallel(samples, run_parallel)
        logger.info("Timing: finished")
        return samples

class ChipseqPipeline(AbstractPipeline):
    name = "chip-seq"

    @classmethod
    def run(self, config, config_file, parallel, dirs, samples):
        with prun.start(_wres(parallel, ["aligner", "picard"]),
                        samples, config, dirs, "multicore",
                        multiplier=alignprep.parallel_multiplier(samples)) as run_parallel:
            samples = run_parallel("process_lane", samples)
            samples = run_parallel("trim_lane", samples)
            samples = disambiguate.split(samples)
            samples = run_parallel("process_alignment", samples)
        with prun.start(_wres(parallel, ["picard", "fastqc"]),
                        samples, config, dirs, "persample") as run_parallel:
            samples = run_parallel("clean_chipseq_alignment", samples)
            samples = qcsummary.generate_parallel(samples, run_parallel)
        return samples

def _get_pipeline(item):
    from bcbio.log import logger
    SUPPORTED_PIPELINES = {x.name.lower(): x for x in
                           utils.itersubclasses(AbstractPipeline)}
    analysis_type = item.get("analysis", "").lower()
    if analysis_type not in SUPPORTED_PIPELINES:
        logger.error("Cannot determine which type of analysis to run, "
                      "set in the run_info under details.")
        sys.exit(1)
    else:
        return SUPPORTED_PIPELINES[analysis_type]

def _pair_lanes_with_pipelines(lane_items):
    paired = [(x, _get_pipeline(x)) for x in lane_items]
    d = defaultdict(list)
    for x in paired:
        d[x[1]].append(x[0])
    return d

########NEW FILE########
__FILENAME__ = merge
"""Handle multiple samples present on a single flowcell

Merges samples located in multiple lanes on a flowcell. Unique sample names identify
items to combine within a group.
"""
import os
import shutil

from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do, system

def combine_fastq_files(in_files, work_dir, config):
    if len(in_files) == 1:
        return in_files[0]
    else:
        cur1, cur2 = in_files[0]
        out1 = os.path.join(work_dir, os.path.basename(cur1))
        out2 = os.path.join(work_dir, os.path.basename(cur2)) if cur2 else None
        if not os.path.exists(out1):
            with open(out1, "a") as out_handle:
                for (cur1, _) in in_files:
                    with open(cur1) as in_handle:
                        shutil.copyfileobj(in_handle, out_handle)
        if out2 and not os.path.exists(out2):
            with open(out2, "a") as out_handle:
                for (_, cur2) in in_files:
                    with open(cur2) as in_handle:
                        shutil.copyfileobj(in_handle, out_handle)
        for f1, f2 in in_files:
            utils.save_diskspace(f1, "fastq merged to %s" % out1, config)
            if f2:
                utils.save_diskspace(f2, "fastq merged to %s" % out2, config)
        return out1, out2

def merge_bam_files(bam_files, work_dir, config, out_file=None, batch=None):
    """Merge multiple BAM files from a sample into a single BAM for processing.

    Checks system open file limit and merges in batches if necessary to avoid
    file handle limits.
    """
    if len(bam_files) == 1:
        return bam_files[0]
    else:
        if out_file is None:
            out_file = os.path.join(work_dir, os.path.basename(sorted(bam_files)[0]))
        if batch is not None:
            base, ext = os.path.splitext(out_file)
            out_file = "%s-b%s%s" % (base, batch, ext)
        if not utils.file_exists(out_file) or not utils.file_exists(out_file + ".bai"):
            bamtools = config_utils.get_program("bamtools", config)
            samtools = config_utils.get_program("samtools", config)
            resources = config_utils.get_resources("samtools", config)
            num_cores = config["algorithm"].get("num_cores", 1)
            max_mem = config_utils.adjust_memory(resources.get("memory", "1G"),
                                                 2, "decrease").upper()
            batch_size = system.open_file_limit() - 100
            if len(bam_files) > batch_size:
                bam_files = [merge_bam_files(xs, work_dir, config, out_file, i)
                             for i, xs in enumerate(utils.partition_all(batch_size, bam_files))]
            with utils.curdir_tmpdir({"config": config}) as tmpdir:
                with utils.chdir(tmpdir):
                    merge_cl = _bamtools_merge(bam_files)
                    with file_transaction(out_file) as tx_out_file:
                        with file_transaction("%s.list" % os.path.splitext(out_file)[0]) as tx_bam_file_list:
                            tx_out_prefix = os.path.splitext(tx_out_file)[0]
                            with open(tx_bam_file_list, "w") as out_handle:
                                for f in sorted(bam_files):
                                    out_handle.write("%s\n" % f)
                            cmd = (merge_cl + " | "
                                   "{samtools} sort -@ {num_cores} -m {max_mem} - {tx_out_prefix}")
                            do.run(cmd.format(**locals()), "Merge bam files to %s" % os.path.basename(out_file),
                                   None)
            for b in bam_files:
                utils.save_diskspace(b, "BAM merged to %s" % out_file, config)
        bam.index(out_file, config)
        return out_file

def _samtools_merge(bam_files):
    """Concatenate multiple BAM files together with samtools.
    Creates short paths to shorten the commandline.
    """
    if len(bam_files) > system.open_file_limit():
        raise IOError("More files to merge (%s) than available open file descriptors (%s)\n"
                      "See documentation on tips for changing file limits:\n"
                      "https://bcbio-nextgen.readthedocs.org/en/latest/contents/"
                      "parallel.html#tuning-systems-for-scale"
                      % (len(bam_files), system.open_file_limit()))
    return "{samtools} merge - `cat {tx_bam_file_list}`"

def _bamtools_merge(bam_files):
    """Use bamtools to merge multiple BAM files, requires a list from disk.
    """
    if len(bam_files) > system.open_file_limit():
        raise IOError("More files to merge (%s) than available open file descriptors (%s)\n"
                      "See documentation on tips for changing file limits:\n"
                      "https://bcbio-nextgen.readthedocs.org/en/latest/contents/"
                      "parallel.html#tuning-systems-for-scale"
                      % (len(bam_files), system.open_file_limit()))
    return "{bamtools} merge -list {tx_bam_file_list}"

########NEW FILE########
__FILENAME__ = qcsummary
"""Quality control and summary metrics for next-gen alignments and analysis.
"""
import collections
import csv
import os
import shutil
import subprocess

import lxml.html
import yaml
from datetime import datetime

# allow graceful during upgrades
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils, run_info
from bcbio.provenance import do
import bcbio.rnaseq.qc
from bcbio.variation.realign import has_aligned_reads
from bcbio.rnaseq.coverage import plot_gene_coverage

# ## High level functions to generate summary

def generate_parallel(samples, run_parallel):
    """Provide parallel preparation of summary information for alignment and variant calling.
    """
    sum_samples = run_parallel("pipeline_summary", samples)
    summary_file = write_project_summary(sum_samples)
    samples = []
    for data in sum_samples:
        if "summary" not in data[0]:
            data[0]["summary"] = {}
        data[0]["summary"]["project"] = summary_file
        samples.append(data)
    samples = _add_researcher_summary(samples, summary_file)
    return samples

def pipeline_summary(data):
    """Provide summary information on processing sample.
    """
    work_bam = data.get("work_bam")
    if data["sam_ref"] is not None and work_bam and has_aligned_reads(work_bam):
        logger.info("Generating summary files: %s" % str(data["name"]))
        data["summary"] = _run_qc_tools(work_bam, data)
    return [[data]]

def prep_pdf(qc_dir, config):
    """Create PDF from HTML summary outputs in QC directory.

    Requires wkhtmltopdf installed: http://www.msweet.org/projects.php?Z1
    Thanks to: https://www.biostars.org/p/16991/

    Works around issues with CSS conversion on CentOS by adjusting CSS.
    """
    html_file = os.path.join(qc_dir, "fastqc", "fastqc_report.html")
    html_fixed = "%s-fixed%s" % os.path.splitext(html_file)
    try:
        topdf = config_utils.get_program("wkhtmltopdf", config)
    except config_utils.CmdNotFound:
        topdf = None
    if topdf and utils.file_exists(html_file):
        out_file = "%s.pdf" % os.path.splitext(html_file)[0]
        if not utils.file_exists(out_file):
            cmd = ("sed 's/div.summary/div.summary-no/' %s | sed 's/div.main/div.main-no/' > %s"
                   % (html_file, html_fixed))
            do.run(cmd, "Fix fastqc CSS to be compatible with wkhtmltopdf")
            cmd = [topdf, html_fixed, out_file]
            do.run(cmd, "Convert QC HTML to PDF")
        return out_file

def _run_qc_tools(bam_file, data):
    """Run a set of third party quality control tools, returning QC directory and metrics.
    """
    to_run = [("fastqc", _run_fastqc)]
    if data["analysis"].lower() == "rna-seq":
        to_run.append(("rnaseqc", bcbio.rnaseq.qc.sample_summary))
#        to_run.append(("coverage", _run_gene_coverage))
        to_run.append(("complexity", _run_complexity))
    elif data["analysis"].lower() == "chip-seq":
        to_run.append(["bamtools", _run_bamtools_stats])
    else:
        to_run += [("bamtools", _run_bamtools_stats), ("gemini", _run_gemini_stats)]
    qc_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "qc", data["description"]))
    metrics = {}
    for program_name, qc_fn in to_run:
        cur_qc_dir = os.path.join(qc_dir, program_name)
        cur_metrics = qc_fn(bam_file, data, cur_qc_dir)
        metrics.update(cur_metrics)
    metrics["Name"] = data["name"][-1]
    metrics["Quality format"] = utils.get_in(data,
                                             ("config", "algorithm",
                                              "quality_format"),
                                             "standard").lower()
    return {"qc": qc_dir, "metrics": metrics}

# ## Generate project level QC summary for quickly assessing large projects

def write_project_summary(samples):
    """Write project summary information on the provided samples.
    write out dirs, genome resources,

    """
    work_dir = samples[0][0]["dirs"]["work"]
    out_file = os.path.join(work_dir, "project-summary.yaml")
    upload_dir = (os.path.join(work_dir, samples[0][0]["upload"]["dir"])
                  if "dir" in samples[0][0]["upload"] else "")
    test_run = samples[0][0].get("test_run", False)
    date = str(datetime.now())
    prev_samples = _other_pipeline_samples(out_file, samples)
    with open(out_file, "w") as out_handle:
        yaml.safe_dump({"date": date}, out_handle,
                       default_flow_style=False, allow_unicode=False)
        if test_run:
            yaml.safe_dump({"test_run": True}, out_handle, default_flow_style=False,
                           allow_unicode=False)
        yaml.safe_dump({"upload": upload_dir}, out_handle,
                       default_flow_style=False, allow_unicode=False)
        yaml.safe_dump({"bcbio_system": samples[0][0]["config"].get("bcbio_system", "")}, out_handle,
                       default_flow_style=False, allow_unicode=False)
        yaml.safe_dump({"samples": prev_samples + [_save_fields(sample[0]) for sample in samples]}, out_handle,
                       default_flow_style=False, allow_unicode=False)
    return out_file

def _other_pipeline_samples(summary_file, cur_samples):
    """Retrieve samples produced previously by another pipeline in the summary output.
    """
    cur_descriptions = set([s[0]["description"] for s in cur_samples])
    out = []
    if os.path.exists(summary_file):
        with open(summary_file) as in_handle:
            for s in yaml.load(in_handle).get("samples", []):
                if s["description"] not in cur_descriptions:
                    out.append(s)
    return out

def _save_fields(sample):
    to_save = ["dirs", "genome_resources", "genome_build", "sam_ref", "metadata",
               "description"]
    saved = {k: sample[k] for k in to_save if k in sample}
    if "summary" in sample:
        saved["summary"] = {"metrics": sample["summary"]["metrics"]}
        # check if disambiguation was run
        if "disambiguate" in sample:
            if utils.file_exists(sample["disambiguate"]["summary"]):
                disambigStats = _parse_disambiguate(sample["disambiguate"]["summary"])
                saved["summary"]["metrics"]["Disambiguated %s reads" % str(sample["genome_build"])] = disambigStats[0]
                disambigGenome = (sample["config"]["algorithm"]["disambiguate"][0]
                                  if isinstance(sample["config"]["algorithm"]["disambiguate"], (list, tuple))
                                  else sample["config"]["algorithm"]["disambiguate"])
                saved["summary"]["metrics"]["Disambiguated %s reads" % disambigGenome] = disambigStats[1]
                saved["summary"]["metrics"]["Disambiguated ambiguous reads"] = disambigStats[2]
    return saved

def _parse_disambiguate(disambiguatestatsfilename):
    """Parse disambiguation stats from given file.
    """
    disambig_stats = [-1, -1, -1]
    with open(disambiguatestatsfilename, "r") as in_handle:
        header = in_handle.readline().strip().split("\t")
        if header == ['sample', 'unique species A pairs', 'unique species B pairs', 'ambiguous pairs']:
            disambig_stats_tmp = in_handle.readline().strip().split("\t")[1:]
            if len(disambig_stats_tmp) == 3:
                disambig_stats = [int(x) for x in disambig_stats_tmp]
    return disambig_stats

# ## Generate researcher specific summaries

def _add_researcher_summary(samples, summary_yaml):
    """Generate summary files per researcher if organized via a LIMS.
    """
    by_researcher = collections.defaultdict(list)
    for data in (x[0] for x in samples):
        researcher = utils.get_in(data, ("upload", "researcher"))
        if researcher:
            by_researcher[researcher].append(data["description"])
    out_by_researcher = {}
    for researcher, descrs in by_researcher.items():
        out_by_researcher[researcher] = _summary_csv_by_researcher(summary_yaml, researcher,
                                                                   set(descrs), samples[0][0])
    out = []
    for data in (x[0] for x in samples):
        researcher = utils.get_in(data, ("upload", "researcher"))
        if researcher:
            data["summary"]["researcher"] = out_by_researcher[researcher]
        out.append([data])
    return out

def _summary_csv_by_researcher(summary_yaml, researcher, descrs, data):
    """Generate a CSV file with summary information for a researcher on this project.
    """
    out_file = os.path.join(utils.safe_makedir(os.path.join(data["dirs"]["work"], "researcher")),
                            "%s-summary.tsv" % run_info.clean_name(researcher))
    metrics = ["Total reads", "Mapped reads", "Mapped reads pct", "Duplicates", "Duplicates pct"]
    with open(summary_yaml) as in_handle:
        with open(out_file, "w") as out_handle:
            writer = csv.writer(out_handle, dialect="excel-tab")
            writer.writerow(["Name"] + metrics)
            for sample in yaml.safe_load(in_handle)["samples"]:
                if sample["description"] in descrs:
                    row = [sample["description"]] + [utils.get_in(sample, ("summary", "metrics", x), "")
                                                     for x in metrics]
                    writer.writerow(row)
    return out_file

# ## Run and parse read information from FastQC

class FastQCParser:
    def __init__(self, base_dir):
        self._dir = base_dir

    def get_fastqc_summary(self):
        ignore = set(["Total Sequences", "Filtered Sequences",
                      "Filename", "File type", "Encoding"])
        stats = {}
        for stat_line in self._fastqc_data_section("Basic Statistics")[1:]:
            k, v = stat_line.split("\t")[:2]
            if k not in ignore:
                stats[k] = v
        return stats

    def _fastqc_data_section(self, section_name):
        out = []
        in_section = False
        data_file = os.path.join(self._dir, "fastqc_data.txt")
        if os.path.exists(data_file):
            with open(data_file) as in_handle:
                for line in in_handle:
                    if line.startswith(">>%s" % section_name):
                        in_section = True
                    elif in_section:
                        if line.startswith(">>END"):
                            break
                        out.append(line.rstrip("\r\n"))
        return out

def _run_gene_coverage(bam_file, data, out_dir):
    out_file = os.path.join(out_dir, "gene_coverage.pdf")
    ref_file = utils.get_in(data, ("genome_resources", "rnaseq", "transcripts"))
    count_file = data["count_file"]
    if utils.file_exists(out_file):
        return out_file
    with file_transaction(out_file) as tx_out_file:
        plot_gene_coverage(bam_file, ref_file, count_file, tx_out_file)
    return {"gene_coverage": out_file}


def _run_fastqc(bam_file, data, fastqc_out):
    """Run fastqc, generating report in specified directory and parsing metrics.

    Downsamples to 10 million reads to avoid excessive processing times with large
    files, unless we're running a Standard/QC pipeline.
    """
    sentry_file = os.path.join(fastqc_out, "fastqc_report.html")
    if not os.path.exists(sentry_file):
        work_dir = os.path.dirname(fastqc_out)
        utils.safe_makedir(work_dir)
        ds_bam = (bam.downsample(bam_file, data, 1e7)
                  if data.get("analysis", "").lower() not in ["standard"]
                  else None)
        bam_file = ds_bam if ds_bam else bam_file
        num_cores = data["config"]["algorithm"].get("num_cores", 1)
        with utils.curdir_tmpdir(data, work_dir) as tx_tmp_dir:
            with utils.chdir(tx_tmp_dir):
                cl = [config_utils.get_program("fastqc", data["config"]),
                      "-t", str(num_cores), "-o", tx_tmp_dir, "-f", "bam", bam_file]
                do.run(cl, "FastQC: %s" % data["name"][-1])
                fastqc_outdir = os.path.join(tx_tmp_dir,
                                             "%s_fastqc" % os.path.splitext(os.path.basename(bam_file))[0])
                if os.path.exists("%s.zip" % fastqc_outdir):
                    os.remove("%s.zip" % fastqc_outdir)
                if not os.path.exists(sentry_file):
                    if os.path.exists(fastqc_out):
                        shutil.rmtree(fastqc_out)
                    shutil.move(fastqc_outdir, fastqc_out)
        if ds_bam and os.path.exists(ds_bam):
            os.remove(ds_bam)
    parser = FastQCParser(fastqc_out)
    stats = parser.get_fastqc_summary()
    return stats

def _run_complexity(bam_file, data, out_dir):
    try:
        import pandas as pd
        import statsmodels.formula.api as sm
    except ImportError:
        return {"Unique Starts Per Read": "NA"}

    SAMPLE_SIZE = 1000000
    base, _ = os.path.splitext(os.path.basename(bam_file))
    utils.safe_makedir(out_dir)
    out_file = os.path.join(out_dir, base + ".pdf")
    df = bcbio.rnaseq.qc.starts_by_depth(bam_file, data["config"], SAMPLE_SIZE)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tmp_out_file:
            df.plot(x='reads', y='starts', title=bam_file + " complexity")
            fig = plt.gcf()
            fig.savefig(tmp_out_file)

    print "file saved as", out_file
    print "out_dir is", out_dir

    return bcbio.rnaseq.qc.estimate_library_complexity(df)


# ## Qualimap

def _parse_num_pct(k, v):
    num, pct = v.split(" / ")
    return {k: num.replace(",", "").strip(), "%s pct" % k: pct.strip()}

def _parse_qualimap_globals(table):
    """Retrieve metrics of interest from globals table.
    """
    out = {}
    want = {"Mapped reads": _parse_num_pct,
            "Duplication rate": lambda k, v: {k: v}}
    for row in table.xpath("table/tr"):
        col, val = [x.text for x in row.xpath("td")]
        if col in want:
            out.update(want[col](col, val))
    return out

def _parse_qualimap_globals_inregion(table):
    """Retrieve metrics from the global targeted region table.
    """
    out = {}
    for row in table.xpath("table/tr"):
        col, val = [x.text for x in row.xpath("td")]
        if col == "Mapped reads":
            out.update(_parse_num_pct("%s (in regions)" % col, val))
    return out

def _parse_qualimap_coverage(table):
    """Parse summary qualimap coverage metrics.
    """
    out = {}
    for row in table.xpath("table/tr"):
        col, val = [x.text for x in row.xpath("td")]
        if col == "Mean":
            out["Coverage (Mean)"] = val
    return out

def _parse_qualimap_insertsize(table):
    """Parse insert size metrics.
    """
    out = {}
    for row in table.xpath("table/tr"):
        col, val = [x.text for x in row.xpath("td")]
        if col == "Median":
            out["Insert size (Median)"] = val
    return out

def _parse_qualimap_metrics(report_file):
    """Extract useful metrics from the qualimap HTML report file.
    """
    out = {}
    parsers = {"Globals": _parse_qualimap_globals,
               "Globals (inside of regions)": _parse_qualimap_globals_inregion,
               "Coverage": _parse_qualimap_coverage,
               "Coverage (inside of regions)": _parse_qualimap_coverage,
               "Insert size": _parse_qualimap_insertsize,
               "Insert size (inside of regions)": _parse_qualimap_insertsize}
    root = lxml.html.parse(report_file).getroot()
    for table in root.xpath("//div[@class='table-summary']"):
        header = table.xpath("h3")[0].text
        if header in parsers:
            out.update(parsers[header](table))
    return out

def _bed_to_bed6(orig_file, out_dir):
    """Convert bed to required bed6 inputs.
    """
    import pybedtools
    bed6_file = os.path.join(out_dir, "%s-bed6%s" % os.path.splitext(os.path.basename(orig_file)))
    if not utils.file_exists(bed6_file):
        with open(bed6_file, "w") as out_handle:
            for i, region in enumerate(list(x) for x in pybedtools.BedTool(orig_file)):
                fillers = [str(i), "1.0", "+"]
                full = region + fillers[:6 - len(region)]
                out_handle.write("\t".join(full) + "\n")
    return bed6_file

def _run_qualimap(bam_file, data, out_dir):
    """Run qualimap to assess alignment quality metrics.
    """
    report_file = os.path.join(out_dir, "qualimapReport.html")
    if not os.path.exists(report_file):
        utils.safe_makedir(out_dir)
        num_cores = data["config"]["algorithm"].get("num_cores", 1)
        qualimap = config_utils.get_program("qualimap", data["config"])
        resources = config_utils.get_resources("qualimap", data["config"])
        max_mem = config_utils.adjust_memory(resources.get("memory", "1G"),
                                             num_cores)
        cmd = ("unset DISPLAY && {qualimap} bamqc -bam {bam_file} -outdir {out_dir} "
               "-nt {num_cores} --java-mem-size={max_mem}")
        species = data["genome_resources"]["aliases"].get("ensembl", "").upper()
        if species in ["HUMAN", "MOUSE"]:
            cmd += " -gd {species}"
        regions = data["config"]["algorithm"].get("variant_regions")
        if regions:
            bed6_regions = _bed_to_bed6(regions, out_dir)
            cmd += " -gff {bed6_regions}"
        do.run(cmd.format(**locals()), "Qualimap: %s" % data["name"][-1])
    return _parse_qualimap_metrics(report_file)

# ## Lightweight QC approaches

def _parse_bamtools_stats(stats_file):
    out = {}
    want = set(["Total reads", "Mapped reads", "Duplicates", "Median insert size"])
    with open(stats_file) as in_handle:
        for line in in_handle:
            parts = line.split(":")
            if len(parts) == 2:
                metric, stat_str = parts
                metric = metric.split("(")[0].strip()
                if metric in want:
                    stat_parts = stat_str.split()
                    if len(stat_parts) == 2:
                        stat, pct = stat_parts
                        pct = pct.replace("(", "").replace(")", "")
                    else:
                        stat = stat_parts[0]
                        pct = None
                    out[metric] = stat
                    if pct:
                        out["%s pct" % metric] = pct
    return out

def _run_bamtools_stats(bam_file, data, out_dir):
    """Run bamtools stats with reports on mapped reads, duplicates and insert sizes.
    """
    stats_file = os.path.join(out_dir, "bamtools_stats.txt")
    if not utils.file_exists(stats_file):
        utils.safe_makedir(out_dir)
        bamtools = config_utils.get_program("bamtools", data["config"])
        with file_transaction(stats_file) as tx_out_file:
            cmd = "{bamtools} stats -in {bam_file}"
            if bam.is_paired(bam_file):
                cmd += " -insert"
            cmd += " > {tx_out_file}"
            do.run(cmd.format(**locals()), "bamtools stats", data)
    return _parse_bamtools_stats(stats_file)

## Variant statistics from gemini

def _run_gemini_stats(bam_file, data, out_dir):
    """Retrieve high level variant statistics from Gemini.
    """
    out = {}
    gemini_db = data.get("variants", [{}])[0].get("population", {}).get("db")
    if gemini_db:
        gemini_stat_file = "%s-stats.yaml" % os.path.splitext(gemini_db)[0]
        if not utils.file_uptodate(gemini_stat_file, gemini_db):
            gemini = config_utils.get_program("gemini", data["config"])
            tstv = subprocess.check_output([gemini, "stats", "--tstv", gemini_db])
            gt_counts = subprocess.check_output([gemini, "stats", "--gts-by-sample", gemini_db])
            dbsnp_count = subprocess.check_output([gemini, "query", gemini_db, "-q",
                                                   "SELECT count(*) FROM variants WHERE in_dbsnp==1"])
            out["Transition/Transversion"] = tstv.split("\n")[1].split()[-1]
            for line in gt_counts.split("\n"):
                parts = line.rstrip().split()
                if len(parts) > 0 and parts[0] == data["name"][-1]:
                    _, hom_ref, het, hom_var, _, total = parts
                    out["Variations (total)"] = int(total)
                    out["Variations (heterozygous)"] = int(het)
                    out["Variations (homozygous)"] = int(hom_var)
                    break
            out["Variations (in dbSNP)"] = int(dbsnp_count.strip())
            if out.get("Variations (total)") > 0:
                out["Variations (in dbSNP) pct"] = "%.1f%%" % (out["Variations (in dbSNP)"] /
                                                               float(out["Variations (total)"]) * 100.0)
            with open(gemini_stat_file, "w") as out_handle:
                yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
        else:
            with open(gemini_stat_file) as in_handle:
                out = yaml.safe_load(in_handle)
    return out

########NEW FILE########
__FILENAME__ = region
"""Provide analysis of input files by chromosomal regions.

Handle splitting and analysis of files from chromosomal subsets separated by
no-read regions.
"""
import collections
import os

from bcbio import utils
from bcbio.distributed.split import parallel_split_combine

def get_max_counts(samples):
    """Retrieve the maximum region size from a set of callable regions
    """
    bed_files = list(set(utils.get_in(x[0], ("config", "algorithm", "callable_regions"))
                         for x in samples))
    return max(sum(1 for line in open(f)) for f in bed_files if f)

# ## BAM preparation

def to_safestr(region):
    if region[0] in ["nochrom", "noanalysis"]:
        return region[0]
    else:
        return "_".join([str(x) for x in region])

# ## Split and delayed BAM combine

def _split_by_regions(dirname, out_ext, in_key):
    """Split a BAM file data analysis into chromosomal regions.
    """
    import pybedtools
    def _do_work(data):
        regions = [(r.chrom, int(r.start), int(r.stop))
                   for r in pybedtools.BedTool(data["config"]["algorithm"]["callable_regions"])]
        bam_file = data[in_key]
        if bam_file is None:
            return None, []
        part_info = []
        base_out = os.path.splitext(os.path.basename(bam_file))[0]
        nowork = [["nochrom"], ["noanalysis", data["config"]["algorithm"]["non_callable_regions"]]]
        for region in regions + nowork:
            out_dir = os.path.join(data["dirs"]["work"], dirname, data["name"][-1], region[0])
            region_outfile = os.path.join(out_dir, "%s-%s%s" %
                                          (base_out, to_safestr(region), out_ext))
            part_info.append((region, region_outfile))
        out_file = os.path.join(data["dirs"]["work"], dirname, data["name"][-1],
                                "%s%s" % (base_out, out_ext))
        return out_file, part_info
    return _do_work

def _add_combine_info(output, combine_map, file_key):
    """Do not actually combine, but add details for later combining work.

    Each sample will contain information on the out file and additional files
    to merge, enabling other splits and recombines without losing information.
    """
    files_per_output = collections.defaultdict(list)
    for part_file, out_file in combine_map.items():
        files_per_output[out_file].append(part_file)
    out_by_file = collections.defaultdict(list)
    out = []
    for data in output:
        # Do not pass along nochrom, noanalysis regions
        if data["region"][0] not in ["nochrom", "noanalysis"]:
            cur_file = data[file_key]
            # If we didn't process, no need to add combine information
            if cur_file in combine_map:
                out_file = combine_map[cur_file]
                if not "combine" in data:
                    data["combine"] = {}
                data["combine"][file_key] = {"out": out_file,
                                             "extras": files_per_output.get(out_file, [])}
                out_by_file[out_file].append(data)
            elif cur_file:
                out_by_file[cur_file].append(data)
            else:
                out.append([data])
    for samples in out_by_file.values():
        regions = [x["region"] for x in samples]
        region_bams = [x["work_bam"] for x in samples]
        assert len(regions) == len(region_bams)
        if len(set(region_bams)) == 1:
            region_bams = [region_bams[0]]
        data = samples[0]
        data["region_bams"] = region_bams
        data["region"] = regions
        out.append([data])
    return out

def parallel_prep_region(samples, run_parallel):
    """Perform full pre-variant calling BAM prep work on regions.
    """
    file_key = "work_bam"
    split_fn = _split_by_regions("bamprep", "-prep.bam", file_key)
    # identify samples that do not need preparation -- no recalibration or realignment
    extras = []
    torun = []
    for data in [x[0] for x in samples]:
        if data.get("work_bam"):
            data["align_bam"] = data["work_bam"]
        a = data["config"]["algorithm"]
        if (not a.get("recalibrate") and not a.get("realign") and not a.get("variantcaller", "gatk")):
            extras.append([data])
        elif not data.get(file_key):
            extras.append([data])
        else:
            torun.append([data])
    return extras + parallel_split_combine(torun, split_fn, run_parallel,
                                           "piped_bamprep", _add_combine_info, file_key, ["config"])

def delayed_bamprep_merge(samples, run_parallel):
    """Perform a delayed merge on regional prepared BAM files.
    """
    needs_merge = False
    for data in samples:
        if (data[0]["config"]["algorithm"].get("merge_bamprep", True) and
              "combine" in data[0]):
            needs_merge = True
            break
    if needs_merge:
        return run_parallel("delayed_bam_merge", samples)
    else:
        return samples

# ## Utilities

def clean_sample_data(samples):
    """Clean unnecessary information from sample data, reducing size for message passing.
    """
    out = []
    for data in (x[0] for x in samples):
        data["dirs"] = {"work": data["dirs"]["work"], "galaxy": data["dirs"]["galaxy"],
                        "fastq": data["dirs"].get("fastq")}
        data["config"] = {"algorithm": data["config"]["algorithm"],
                          "resources": data["config"]["resources"]}
        for remove_attr in ["config_file", "regions", "algorithm"]:
            data.pop(remove_attr, None)
        out.append([data])
    return out

########NEW FILE########
__FILENAME__ = rnaseq
from bcbio.rnaseq import featureCounts, cufflinks, oncofuse
from bcbio.utils import get_in

def detect_fusion(samples, run_parallel):
    samples = run_parallel("run_oncofuse", samples)
    return samples

def estimate_expression(samples, run_parallel):
    samples = run_parallel("generate_transcript_counts", samples)
    samples = run_parallel("run_cufflinks", samples)
    return samples

def generate_transcript_counts(data):
    """Generate counts per transcript from an alignment"""
    data["count_file"] = featureCounts.count(data)
    if get_in(data, ("config", "algorithm", "fusion_mode"), False):
        oncofuse_file = oncofuse.run(data)
        if oncofuse_file:
            data["oncofuse_file"] = oncofuse.run(data)
    return [[data]]


def run_cufflinks(data):
    """Quantitate transcript expression with Cufflinks"""
    work_bam = data["work_bam"]
    ref_file = data["sam_ref"]
    data["cufflinks_dir"] = cufflinks.run(work_bam, ref_file, data)
    return [[data]]

########NEW FILE########
__FILENAME__ = run_info
"""Retrieve run information describing files to process in a pipeline.

This handles two methods of getting processing information: from a Galaxy
next gen LIMS system or an on-file YAML configuration.
"""
import copy
import itertools
import os
from contextlib import closing

import string
import yaml

from bcbio import utils
from bcbio.log import logger
from bcbio.illumina import flowcell
from bcbio.pipeline import alignment, config_utils, genome
from bcbio.variation import effects, genotype, population
from bcbio.variation.cortex import get_sample_name
from bcbio.bam.fastq import open_fastq

def organize(dirs, config, run_info_yaml):
    """Organize run information from a passed YAML file or the Galaxy API.

    Creates the high level structure used for subsequent processing.
    """
    logger.info("Using input YAML configuration: %s" % run_info_yaml)
    assert run_info_yaml and os.path.exists(run_info_yaml), \
        "Did not find input sample YAML file: %s" % run_info_yaml
    run_details = _run_info_from_yaml(dirs["flowcell"], run_info_yaml, config)
    out = []
    for item in run_details:
        # add algorithm details to configuration, avoid double specification
        item["config"] = config_utils.update_w_custom(config, item)
        item.pop("algorithm", None)
        item["dirs"] = dirs
        if "name" not in item:
            item["name"] = ["", item["description"]]
        elif isinstance(item["name"], basestring):
            description = "%s-%s" % (item["name"], clean_name(item["description"]))
            item["name"] = [item["name"], description]
            item["description"] = description
        item = add_reference_resources(item)
        # Create temporary directories and make absolute
        if utils.get_in(item, ("config", "resources", "tmp", "dir")):
            utils.safe_makedir(utils.get_in(item, ("config", "resources", "tmp", "dir")))
            item["config"]["resources"]["tmp"] = genome.abs_file_paths(
                utils.get_in(item, ("config", "resources", "tmp")))
        out.append(item)
    return out

# ## Genome reference information

def add_reference_resources(data):
    """Add genome reference information to the item to process.
    """
    aligner = data["config"]["algorithm"].get("aligner", None)
    data["reference"] = genome.get_refs(data["genome_build"], aligner, data["dirs"]["galaxy"])
    # back compatible `sam_ref` target
    data["sam_ref"] = utils.get_in(data, ("reference", "fasta", "base"))
    ref_loc = utils.get_in(data, ("config", "resources", "species", "dir"),
                           utils.get_in(data, ("reference", "fasta", "base")))
    data["genome_resources"] = genome.get_resources(data["genome_build"], ref_loc)
    data["reference"]["snpeff"] = effects.get_snpeff_files(data)
    alt_genome = utils.get_in(data, ("config", "algorithm", "validate_genome_build"))
    if alt_genome:
        data["reference"]["alt"] = {alt_genome:
                                    genome.get_refs(alt_genome, None, data["dirs"]["galaxy"])["fasta"]}
    # Re-enable when we have ability to re-define gemini configuration directory
    if False:
        if population.do_db_build([data], check_gemini=False, need_bam=False):
            data["reference"]["gemini"] = population.get_gemini_files(data)
    return data

# ## Sample and BAM read group naming

def _clean_characters(x):
    """Clean problem characters in sample lane or descriptions.
    """
    for problem in [" ", "."]:
        x = x.replace(problem, "_")
    return x

def prep_rg_names(item, config, fc_name, fc_date):
    """Generate read group names from item inputs.
    """
    if fc_name and fc_date:
        lane_name = "%s_%s_%s" % (item["lane"], fc_date, fc_name)
    else:
        lane_name = item["description"]
    return {"rg": item["lane"],
            "sample": item["description"],
            "lane": lane_name,
            "pl": item.get("algorithm", {}).get("platform",
                                                config.get("algorithm", {}).get("platform", "illumina")).lower(),
            "pu": lane_name}

# ## Configuration file validation

def _check_for_duplicates(xs, attr, check_fn=None):
    """Identify and raise errors on duplicate items.
    """
    dups = []
    for key, vals in itertools.groupby(x[attr] for x in xs):
        if len(list(vals)) > 1:
            dups.append(key)
    if len(dups) > 0:
        psamples = []
        for x in xs:
            if x[attr] in dups:
                psamples.append(x)
        # option to skip problem based on custom input function.
        if check_fn and check_fn(psamples):
            return
        descrs = [x["description"] for x in psamples]
        raise ValueError("Duplicate '%s' found in input sample configuration.\n"
                         "Required to be unique for a project: %s\n"
                         "Problem found in these samples: %s" % (attr, dups, descrs))

def _check_for_batch_clashes(xs):
    """Check that batch names do not overlap with sample names.
    """
    names = set([x["description"] for x in xs])
    dups = set([])
    for x in xs:
        batches = utils.get_in(x, ("metadata", "batch"))
        if batches:
            if not isinstance(batches, (list, tuple)):
                batches = [batches]
            for batch in batches:
                if batch in names:
                    dups.add(batch)
    if len(dups) > 0:
        raise ValueError("Batch names must be unique from sample descriptions.\n"
                         "Clashing batch names: %s" % sorted(list(dups)))

def _check_for_misplaced(xs, subkey, other_keys):
    """Ensure configuration keys are not incorrectly nested under other keys.
    """
    problems = []
    for x in xs:
        check_dict = x.get(subkey, {})
        for to_check in other_keys:
            if to_check in check_dict:
                problems.append((x["description"], to_check, subkey))
    if len(problems) > 0:
        raise ValueError("\n".join(["Incorrectly nested keys found in sample YAML. These should be top level:",
                                    " sample         |   key name      |   nested under ",
                                    "----------------+-----------------+----------------"] +
                                   ["% 15s | % 15s | % 15s" % (a, b, c) for (a, b, c) in problems]))

ALGORITHM_KEYS = set(["platform", "aligner", "bam_clean", "bam_sort",
                      "trim_reads", "adapters", "custom_trim",
                      "align_split_size", "quality_bin",
                      "quality_format", "write_summary",
                      "merge_bamprep", "coverage",
                      "coverage_interval", "ploidy",
                      "variantcaller", "variant_regions",
                      "mark_duplicates", "svcaller", "recalibrate",
                      "realign", "phasing", "validate",
                      "validate_regions", "validate_genome_build",
                      "clinical_reporting", "nomap_split_size",
                      "nomap_split_targets", "ensemble", "background",
                      "disambiguate", "strandedness", "fusion_mode", "min_read_length",
                      "coverage_depth_min", "coverage_depth_max", "min_allele_fraction", "remove_lcr",
                      "archive", "tools_off"] +
                     # back compatibility
                      ["coverage_depth"])

def _check_algorithm_keys(item):
    """Check for unexpected keys in the algorithm section.

    Needs to be manually updated when introducing new keys, but avoids silent bugs
    with typos in key names.
    """
    url = "https://bcbio-nextgen.readthedocs.org/en/latest/contents/configuration.html#algorithm-parameters"
    problem_keys = [k for k in item["algorithm"].iterkeys() if k not in ALGORITHM_KEYS]
    if len(problem_keys) > 0:
        raise ValueError("Unexpected configuration keyword in 'algorithm' section: %s\n"
                         "See configuration documentation for supported options:\n%s\n"
                         % (problem_keys, url))


def _detect_fastq_format(in_file, MAX_RECORDS=1000):
    ranges = {"sanger": (33, 73),
              "solexa": (59, 104),
              "illumina_1.3+": (64, 104),
              "illumina_1.5+": (66, 104),
              "illumina_1.8+": (35, 74)}

    gmin, gmax = 99, 0
    possible = set(ranges.keys())

    with closing(open_fastq(in_file)) as in_handle:
        four = itertools.islice(in_handle, 3, None, 4)
        count = 0
        for line in four:
            if len(possible) == 1:
                return possible
            if count > MAX_RECORDS:
                break
            count += 1
            vals = [ord(c) for c in line.rstrip()]
            lmin = min(vals)
            lmax = max(vals)
            for encoding, (emin, emax) in ranges.items():
                if encoding in possible:
                    if lmin < emin or lmax > emax:
                        possible.remove(encoding)

    return possible

def _check_quality_format(items):
    """
    Check if quality_format="standard" and fastq_format is not sanger
    """
    SAMPLE_FORMAT = {"illumina_1.3+": "illumina",
                     "illumina_1.5+": "illumina",
                     "illumina_1.8+": "standard",
                     "solexa": "solexa",
                     "sanger": "standard"}
    fastq_extensions = ["fq.gz", "fastq.gz", ".fastq" ".fq"]

    for item in items:
        specified_format = item["algorithm"].get("quality_format", "").lower()
        fastq_file = next((file for file in item.get('files', []) if
                           any([ext for ext in fastq_extensions if ext in file])), None)

        if fastq_file and specified_format:
            fastq_format = _detect_fastq_format(fastq_file)
            detected_encodings = set([SAMPLE_FORMAT[x] for x in fastq_format])
            if detected_encodings:
                if specified_format not in detected_encodings:
                    raise ValueError("Quality format specified in the YAML "
                                     "file might be a different encoding. "
                                     "'%s' was specified but possible formats "
                                     "detected were %s." % (specified_format,
                                                            ", ".join(detected_encodings)))


def _check_aligner(item):
    """Ensure specified aligner is valid choice.
    """
    allowed = set(alignment.TOOLS.keys() + [None, False])
    if item["algorithm"].get("aligner") not in allowed:
        raise ValueError("Unexpected algorithm 'aligner' parameter: %s\n"
                         "Supported options: %s\n" %
                         (item["algorithm"].get("aligner"), sorted(list(allowed))))

def _check_variantcaller(item):
    """Ensure specified variantcaller is a valid choice.
    """
    allowed = set(genotype.get_variantcallers().keys() + [None, False])
    vcs = item["algorithm"].get("variantcaller", "gatk")
    if not isinstance(vcs, (tuple, list)):
        vcs = [vcs]
    problem = [x for x in vcs if x not in allowed]
    if len(problem) > 0:
        raise ValueError("Unexpected algorithm 'variantcaller' parameter: %s\n"
                         "Supported options: %s\n" % (problem, sorted(list(allowed))))

def _check_sample_config(items, in_file):
    """Identify common problems in input sample configuration files.
    """
    logger.info("Checking sample YAML configuration: %s" % in_file)
    _check_quality_format(items)
    _check_for_duplicates(items, "lane")
    _check_for_duplicates(items, "description")
    _check_for_batch_clashes(items)
    _check_for_misplaced(items, "algorithm",
                         ["resources", "metadata", "analysis",
                          "description", "genome_build", "lane", "files"])

    [_check_algorithm_keys(x) for x in items]
    [_check_aligner(x) for x in items]
    [_check_variantcaller(x) for x in items]


# ## Read bcbio_sample.yaml files

def _file_to_abs(x, dnames):
    """Make a file absolute using the supplied base directory choices.
    """
    if x is None or os.path.isabs(x):
        return x
    elif isinstance(x, basestring) and x.lower() == "none":
        return None
    else:
        for dname in dnames:
            if dname:
                normx = os.path.normpath(os.path.join(dname, x))
                if os.path.exists(normx):
                    return normx
        raise ValueError("Did not find input file %s in %s" % (x, dnames))

def _normalize_files(item, fc_dir):
    """Ensure the files argument is a list of absolute file names.
    Handles BAM, single and paired end fastq.
    """
    files = item.get("files")
    if files:
        if isinstance(files, basestring):
            files = [files]
        fastq_dir = flowcell.get_fastq_dir(fc_dir) if fc_dir else os.getcwd()
        files = [_file_to_abs(x, [os.getcwd(), fc_dir, fastq_dir]) for x in files]
        files = [x for x in files if x]
        _sanity_check_files(item, files)
        item["files"] = files
    return item

def _sanity_check_files(item, files):
    """Ensure input files correspond with supported
    """
    msg = None
    file_types = set([("bam" if x.endswith(".bam") else "fastq") for x in files if x])
    if len(file_types) > 1:
        msg = "Found multiple file types (BAM and fastq)"
    file_type = file_types.pop()
    if file_type == "bam":
        if len(files) != 1:
            msg = "Expect a single BAM file input as input"
    elif file_type == "fastq":
        if len(files) not in [1, 2]:
            msg = "Expect either 1 (single end) or 2 (paired end) fastq inputs"
    if msg:
        raise ValueError("%s for %s: %s" % (msg, item.get("description", ""), files))

def _run_info_from_yaml(fc_dir, run_info_yaml, config):
    """Read run information from a passed YAML file.
    """
    with open(run_info_yaml) as in_handle:
        loaded = yaml.load(in_handle)
    fc_name, fc_date = None, None
    if fc_dir:
        try:
            fc_name, fc_date = flowcell.parse_dirname(fc_dir)
        except ValueError:
            pass
    global_config = {}
    global_vars = {}
    if isinstance(loaded, dict):
        global_config = copy.deepcopy(loaded)
        del global_config["details"]
        if "fc_name" in loaded and "fc_date" in loaded:
            fc_name = loaded["fc_name"].replace(" ", "_")
            fc_date = str(loaded["fc_date"]).replace(" ", "_")
        global_vars = global_config.pop("globals", {})
        loaded = loaded["details"]

    run_details = []
    for i, item in enumerate(loaded):
        item = _normalize_files(item, fc_dir)
        if "lane" not in item:
            item["lane"] = str(i + 1)
        item["lane"] = _clean_characters(str(item["lane"]))
        if "description" not in item:
            if len(item.get("files", [])) == 1 and item["files"][0].endswith(".bam"):
                item["description"] = get_sample_name(item["files"][0])
            else:
                raise ValueError("No `description` sample name provided for input #%s" % (i + 1))
        item["description"] = _clean_characters(str(item["description"]))
        if "upload" not in item:
            upload = global_config.get("upload", {})
            # Handle specifying a local directory directly in upload
            if isinstance(upload, basestring):
                upload = {"dir": upload}
            if fc_name and fc_date:
                upload["fc_name"] = fc_name
                upload["fc_date"] = fc_date
            upload["run_id"] = ""
            item["upload"] = upload
        item["algorithm"] = _replace_global_vars(item["algorithm"], global_vars)
        item["algorithm"] = genome.abs_file_paths(item["algorithm"],
                                                  ignore_keys=["variantcaller", "realign", "recalibrate",
                                                               "phasing", "svcaller"])
        item["algorithm"] = _add_algorithm_defaults(item["algorithm"])
        item["rgnames"] = prep_rg_names(item, config, fc_name, fc_date)
        item["test_run"] = global_config.get("test_run", False)
        run_details.append(item)
    _check_sample_config(run_details, run_info_yaml)
    return run_details

def _add_algorithm_defaults(algorithm):
    """Central location specifying defaults for algorithm inputs.

    Converts allowed multiple inputs into lists if specified as a single item.
    """
    defaults = {"archive": [],
                "min_allele_fraction": 10.0,
                "tools_off": []}
    convert_to_list = set(["archive", "tools_off"])
    for k, v in defaults.items():
        if k not in algorithm:
            algorithm[k] = v
    for k, v in algorithm.items():
        if k in convert_to_list:
            if not isinstance(v, (list, tuple)):
                algorithm[k] = [v]
    return algorithm

def _replace_global_vars(xs, global_vars):
    """Replace globally shared names from input header with value.

    The value of the `algorithm` item may be a pointer to a real
    file specified in the `global` section. If found, replace with
    the full value.
    """
    if isinstance(xs, (list, tuple)):
        return [_replace_global_vars(x) for x in xs]
    elif isinstance(xs, dict):
        final = {}
        for k, v in xs.iteritems():
            if isinstance(v, basestring) and v in global_vars:
                v = global_vars[v]
            final[k] = v
        return final
    else:
        return xs

def clean_name(xs):
    final = []
    safec = "_"
    for x in xs:
        if x not in string.ascii_letters + string.digits:
            if len(final) > 0 and final[-1] != safec:
                final.append(safec)
        else:
            final.append(x)
    if final[-1] == safec:
        final = final[:-1]
    return "".join(final)

########NEW FILE########
__FILENAME__ = sample
"""High level entry point for processing a sample.

Samples may include multiple lanes, or barcoded subsections of lanes,
processed together.
"""
import copy
import os

from bcbio import utils
from bcbio.log import logger
from bcbio.pipeline.merge import (combine_fastq_files, merge_bam_files)
from bcbio.pipeline import config_utils

# ## Merging

def merge_sample(data):
    """Merge fastq and BAM files for multiple samples.
    """
    logger.debug("Combining fastq and BAM files %s" % str(data["name"]))
    config = config_utils.update_w_custom(data["config"], data["info"])
    if config["algorithm"].get("upload_fastq", False):
        fastq1, fastq2 = combine_fastq_files(data["fastq_files"], data["dirs"]["work"],
                                             config)
    else:
        fastq1, fastq2 = None, None

    out_file = os.path.join(data["dirs"]["work"],
                            data["info"]["rgnames"]["sample"] + ".bam")
    sort_bam = merge_bam_files(data["bam_files"], data["dirs"]["work"],
                               config, out_file=out_file)
    return [[{"name": data["name"], "metadata": data["info"].get("metadata", {}),
              "info": data["info"],
              "genome_build": data["genome_build"], "sam_ref": data["sam_ref"],
              "work_bam": sort_bam, "fastq1": fastq1, "fastq2": fastq2,
              "dirs": data["dirs"], "config": config,
              "config_file": data["config_file"]}]]

def delayed_bam_merge(data):
    """Perform a merge on previously prepped files, delayed in processing.

    Handles merging of associated split read and discordant files if present.
    """
    if data.get("combine"):
        assert len(data["combine"].keys()) == 1
        file_key = data["combine"].keys()[0]
        extras = []
        for x in data["combine"][file_key].get("extras", []):
            if isinstance(x, (list, tuple)):
                extras.extend(x)
            else:
                extras.append(x)
        if file_key in data:
            extras.append(data[file_key])
        in_files = sorted(list(set(extras)))
        out_file = data["combine"][file_key]["out"]
        sup_exts = data.get(file_key + "-plus", {}).keys()
        for ext in sup_exts + [""]:
            merged_file = None
            if os.path.exists(utils.append_stem(out_file, "-" + ext)):
                cur_out_file, cur_in_files = out_file, []
            if ext:
                cur_in_files = list(filter(os.path.exists, (utils.append_stem(f, "-" + ext) for f in in_files)))
                cur_out_file = utils.append_stem(out_file, "-" + ext) if len(cur_in_files) > 0 else None
            else:
                cur_in_files, cur_out_file = in_files, out_file
            if cur_out_file:
                config = copy.deepcopy(data["config"])
                config["algorithm"]["save_diskspace"] = False
                if len(cur_in_files) > 0:
                    merged_file = merge_bam_files(cur_in_files, os.path.dirname(cur_out_file), config,
                                                  out_file=cur_out_file)
                else:
                    assert os.path.exists(cur_out_file)
                    merged_file = cur_out_file
            if merged_file:
                if ext:
                    data[file_key + "-plus"][ext] = merged_file
                else:
                    data[file_key] = merged_file
        data.pop("region", None)
        data.pop("combine", None)
    return [[data]]

########NEW FILE########
__FILENAME__ = shared
"""Pipeline functionality shared amongst multiple analysis types.
"""
import os
from contextlib import closing, contextmanager
import functools
import tempfile

try:
    import pybedtools
except ImportError:
    pybedtools = None
import pysam

from bcbio import bam, broad, utils
from bcbio.pipeline import config_utils
from bcbio.utils import file_exists, safe_makedir, save_diskspace
from bcbio.distributed.transaction import file_transaction
from bcbio.provenance import do

# ## Split/Combine helpers

def combine_bam(in_files, out_file, config):
    """Parallel target to combine multiple BAM files.
    """
    runner = broad.runner_from_config(config)
    runner.run_fn("picard_merge", in_files, out_file)
    for in_file in in_files:
        save_diskspace(in_file, "Merged into {0}".format(out_file), config)
    bam.index(out_file, config)
    return out_file

def process_bam_by_chromosome(output_ext, file_key, default_targets=None, dir_ext_fn=None):
    """Provide targets to process a BAM file by individual chromosome regions.

    output_ext: extension to supply to output files
    file_key: the key of the BAM file in the input data map
    default_targets: a list of extra chromosome targets to process, beyond those specified
                     in the BAM file. Useful for retrieval of non-mapped reads.
    dir_ext_fn: A function to retrieve a directory naming extension from input data map.
    """
    if default_targets is None:
        default_targets = []
    def _do_work(data):
        bam_file = data[file_key]
        out_dir = os.path.dirname(bam_file)
        if dir_ext_fn:
            out_dir = os.path.join(out_dir, dir_ext_fn(data))

        out_file = os.path.join(out_dir, "{base}{ext}".format(
                base=os.path.splitext(os.path.basename(bam_file))[0],
                ext=output_ext))
        part_info = []
        if not file_exists(out_file):
            work_dir = safe_makedir(
                "{base}-split".format(base=os.path.splitext(out_file)[0]))
            with closing(pysam.Samfile(bam_file, "rb")) as work_bam:
                for chr_ref in list(work_bam.references) + default_targets:
                    chr_out = os.path.join(work_dir,
                                           "{base}-{ref}{ext}".format(
                                               base=os.path.splitext(os.path.basename(bam_file))[0],
                                               ref=chr_ref, ext=output_ext))
                    part_info.append((chr_ref, chr_out))
        return out_file, part_info
    return _do_work

def write_nochr_reads(in_file, out_file, config):
    """Write a BAM file of reads that are not mapped on a reference chromosome.

    This is useful for maintaining non-mapped reads in parallel processes
    that split processing by chromosome.
    """
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            samtools = config_utils.get_program("samtools", config)
            cmd = "{samtools} view -b -f 4 {in_file} > {tx_out_file}"
            do.run(cmd.format(**locals()), "Select unmapped reads")
    return out_file

def write_noanalysis_reads(in_file, region_file, out_file, config):
    """Write a BAM file of reads in the specified region file that are not analyzed.

    We want to get only reads not in analysis regions but also make use of
    the BAM index to perform well on large files. The tricky part is avoiding
    command line limits. There is a nice discussion on SeqAnswers:
    http://seqanswers.com/forums/showthread.php?t=29538
    sambamba supports intersection via an input BED file so avoids command line
    length issues.
    """
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            bedtools = config_utils.get_program("bedtools", config)
            sambamba = config_utils.get_program("sambamba", config)
            cl = ("{sambamba} view -f bam -L {region_file} {in_file} | "
                  "{bedtools} intersect -abam - -b {region_file} -f 1.0 "
                  "> {tx_out_file}")
            do.run(cl.format(**locals()), "Select unanalyzed reads")
    return out_file

def subset_bam_by_region(in_file, region, out_file_base=None):
    """Subset BAM files based on specified chromosome region.
    """
    if out_file_base is not None:
        base, ext = os.path.splitext(out_file_base)
    else:
        base, ext = os.path.splitext(in_file)
    out_file = "%s-subset%s%s" % (base, region, ext)
    if not file_exists(out_file):
        with closing(pysam.Samfile(in_file, "rb")) as in_bam:
            target_tid = in_bam.gettid(region)
            assert region is not None, \
                   "Did not find reference region %s in %s" % \
                   (region, in_file)
            with file_transaction(out_file) as tx_out_file:
                with closing(pysam.Samfile(tx_out_file, "wb", template=in_bam)) as out_bam:
                    for read in in_bam:
                        if read.tid == target_tid:
                            out_bam.write(read)
    return out_file

def _rewrite_bed_with_chrom(in_file, out_file, chrom):
    with open(in_file) as in_handle:
        with open(out_file, "w") as out_handle:
            for line in in_handle:
                if line.startswith("%s\t" % chrom):
                    out_handle.write(line)


def _subset_bed_by_region(in_file, out_file, region):
    orig_bed = pybedtools.BedTool(in_file)
    region_bed = pybedtools.BedTool("\t".join(str(x) for x in region) + "\n", from_string=True)
    orig_bed.intersect(region_bed).filter(lambda x: len(x) > 5).merge().saveas(out_file)

def get_lcr_bed(items):
    lcr_bed = utils.get_in(items[0], ("genome_resources", "variation", "lcr"))
    do_lcr = any([utils.get_in(data, ("config", "algorithm", "remove_lcr"), False)
                  for data in items])
    if do_lcr and lcr_bed and os.path.exists(lcr_bed):
        return lcr_bed

def remove_lcr_regions(orig_bed, items):
    """If configured and available, update a BED file to remove low complexity regions.
    """
    lcr_bed = get_lcr_bed(items)
    if lcr_bed:
        nolcr_bed = os.path.join("%s-nolcr.bed" % (utils.splitext_plus(orig_bed)[0]))
        with file_transaction(nolcr_bed) as tx_nolcr_bed:
            pybedtools.BedTool(orig_bed).subtract(pybedtools.BedTool(lcr_bed)).saveas(tx_nolcr_bed)
        # If we have a non-empty file, convert to the LCR subtracted for downstream analysis
        if utils.file_exists(nolcr_bed):
            orig_bed = nolcr_bed
    return orig_bed

@contextmanager
def bedtools_tmpdir(data):
    with utils.curdir_tmpdir(data) as tmpdir:
        orig_tmpdir = tempfile.gettempdir()
        pybedtools.set_tempdir(tmpdir)
        yield
        if orig_tmpdir and os.path.exists(orig_tmpdir):
            pybedtools.set_tempdir(orig_tmpdir)
        else:
            tempfile.tempdir = None

def subtract_low_complexity(f):
    """Remove low complexity regions from callable regions if available.
    """
    @functools.wraps(f)
    def wrapper(variant_regions, region, out_file, items=None):
        region_bed = f(variant_regions, region, out_file, items)
        if region_bed and isinstance(region_bed, basestring) and os.path.exists(region_bed) and items:
            region_bed = remove_lcr_regions(region_bed, items)
        return region_bed
    return wrapper

@subtract_low_complexity
def subset_variant_regions(variant_regions, region, out_file, items=None):
    """Return BED file subset by a specified chromosome region.

    variant_regions is a BED file, region is a chromosome name or tuple
    of (name, start, end) for a genomic region.
    """
    if region is None:
        return variant_regions
    elif variant_regions is None:
        return region
    elif not isinstance(region, (list, tuple)) and region.find(":") > 0:
        raise ValueError("Partial chromosome regions not supported")
    else:
        subset_file = "{0}-regions.bed".format(utils.splitext_plus(out_file)[0])
        if not os.path.exists(subset_file):
            with file_transaction(subset_file) as tx_subset_file:
                if isinstance(region, (list, tuple)):
                    _subset_bed_by_region(variant_regions, tx_subset_file, region)
                else:
                    _rewrite_bed_with_chrom(variant_regions, tx_subset_file, region)
        if os.path.getsize(subset_file) == 0:
            return region
        else:
            return subset_file

########NEW FILE########
__FILENAME__ = tools
"""Access tool command lines, handling back compatibility and file type issues.

Abstracts out
"""
import subprocess
from bcbio.pipeline import config_utils

def get_tabix_cmd(config):
    """Retrieve tabix command, handling new bcftools tabix and older tabix.
    """
    try:
        bcftools = config_utils.get_program("bcftools", config)
        # bcftools has terrible error codes and stderr output, swallow those.
        bcftools_tabix = subprocess.check_output("{bcftools} 2>&1; echo $?".format(**locals()),
                                                 shell=True).find("tabix") >= 0
    except config_utils.CmdNotFound:
        bcftools_tabix = False
    if bcftools_tabix:
        return "{0} tabix".format(bcftools)
    else:
        tabix = config_utils.get_program("tabix", config)
        return tabix

def get_bgzip_cmd(config, is_retry=False):
    """Retrieve command to use for bgzip, trying to use parallel pbgzip if available.

    XXX Currently uses non-parallel bgzip until we can debug segfault issues
    with pbgzip.

    Avoids over committing cores to gzipping since run in pipe with other tools.
    Allows for retries which force single core bgzip mode.
    """
    num_cores = max(1, (config.get("algorithm", {}).get("num_cores", 1) // 2) - 1)
    #if not is_retry and num_cores > 1:
    if False:
        try:
            pbgzip = config_utils.get_program("pbgzip", config)
            return "%s -n %s " % (pbgzip, num_cores)
        except config_utils.CmdNotFound:
            pass
    return config_utils.get_program("bgzip", config)

########NEW FILE########
__FILENAME__ = variation
"""Next-gen variant detection and evaluation with GATK and SnpEff.
"""
from bcbio.log import logger
from bcbio.variation.genotype import variant_filtration, get_variantcaller
from bcbio.variation import effects

# ## Genotyping

def postprocess_variants(data):
    """Provide post-processing of variant calls: filtering and effects annotation.
    """
    cur_name = "%s, %s" % (data["name"][-1], get_variantcaller(data))
    logger.info("Finalizing variant calls: %s" % cur_name)
    if data.get("align_bam") and data.get("vrn_file"):
        logger.info("Calculating variation effects for %s" % cur_name)
        ann_vrn_file = effects.snpeff_effects(data)
        if ann_vrn_file:
            data["vrn_file"] = ann_vrn_file
        logger.info("Filtering for %s" % cur_name)
        data["vrn_file"] = variant_filtration(data["vrn_file"], data["sam_ref"],
                                              data["genome_resources"]["variation"],
                                              data)
    return [[data]]

########NEW FILE########
__FILENAME__ = diagnostics
"""Provide logging and diagnostics of running pipelines.

This wraps the BioLite diagnostics database format to provide
tracking of command lines, run times and inspection into run progress.
The goal is to allow traceability and reproducibility of pipelines.

https://bitbucket.org/caseywdunn/biolite
"""

def start_cmd(cmd, descr, entity):
    """Retain details about starting a command, returning a command identifier.
    """
    pass

def end_cmd(cmd_id, succeeded=True):
    """Mark a command as finished with success or failure.
    """
    pass

def track_parallel(items, sub_type):
    """Create entity identifiers to trace the given items in sub-commands.

    Helps handle nesting in parallel program execution:

    run id => sub-section id => parallel ids
    """
    out = []
    for i, args in enumerate(items):
        item_i, item = get_item_from_args(args)
        if item:
            sub_entity = "%s.%s.%s" % (item["provenance"]["entity"], sub_type, i)
            item["provenance"]["entity"] = sub_entity
            args = list(args)
            args[item_i] = item
        out.append(args)
    # TODO: store mapping of entity to sub identifiers
    return out

def _has_provenance(x):
    return isinstance(x, dict) and x.has_key("provenance")

def get_item_from_args(xs):
    """Retrieve processed item from list of input arguments.
    """
    for i, x in enumerate(xs):
        if _has_provenance(x):
            return i, x
    return -1, None

########NEW FILE########
__FILENAME__ = do
"""Centralize running of external commands, providing logging and tracking.
"""
import collections
import contextlib
import os
import subprocess
import time

from bcbio import utils
from bcbio.log import logger, logger_cl, logger_stdout
from bcbio.provenance import diagnostics

def run(cmd, descr, data=None, checks=None, region=None, log_error=True,
        log_stdout=False):
    """Run the provided command, logging details and checking for errors.
    """
    descr = _descr_str(descr, data, region)
    logger.debug(descr)
    # TODO: Extract entity information from data input
    cmd_id = diagnostics.start_cmd(descr, data, cmd)
    try:
        logger_cl.debug(" ".join(cmd) if not isinstance(cmd, basestring) else cmd)
        _do_run(cmd, checks, log_stdout)
    except:
        diagnostics.end_cmd(cmd_id, False)
        if log_error:
            logger.exception()
        raise
    finally:
        diagnostics.end_cmd(cmd_id)

def run_memory_retry(cmd, descr, data=None, check=None, region=None):
    """Run command, retrying when detecting fail due to memory errors.

    This is useful for high throughput Java jobs which fail
    intermittently due to an inability to get system resources.
    """
    max_runs = 5
    num_runs = 0
    while 1:
        try:
            run(cmd, descr, data, check, region=region, log_error=False)
            break
        except subprocess.CalledProcessError, msg:
            if num_runs < max_runs and ("insufficient memory" in str(msg) or
                                        "did not provide enough memory" in str(msg) or
                                        "A fatal error has been detected" in str(msg) or
                                        "java.lang.OutOfMemoryError" in str(msg) or
                                        "Resource temporarily unavailable" in str(msg)):
                logger.info("Retrying job. Memory or resource issue with run: %s"
                            % _descr_str(descr, data, region))
                time.sleep(30)
                num_runs += 1
            else:
                logger.exception()
                raise

def _descr_str(descr, data, region):
    """Add additional useful information from data to description string.
    """
    if data:
        if "name" in data:
            descr = "{0} : {1}".format(descr, data["name"][-1])
        elif "work_bam" in data:
            descr = "{0} : {1}".format(descr, os.path.basename(data["work_bam"]))
    if region:
        descr = "{0} : {1}".format(descr, region)
    return descr

def find_bash():
    for test_bash in [find_cmd("bash"), "/bin/bash", "/usr/bin/bash", "/usr/local/bin/bash"]:
        if test_bash and os.path.exists(test_bash):
            return test_bash
    raise IOError("Could not find bash in any standard location. Needed for unix pipes")

def find_cmd(cmd):
    try:
        return subprocess.check_output(["which", cmd]).strip()
    except subprocess.CalledProcessError:
        return None

def _normalize_cmd_args(cmd):
    """Normalize subprocess arguments to handle list commands, string and pipes.
    Piped commands set pipefail and require use of bash to help with debugging
    intermediate errors.
    """
    if isinstance(cmd, basestring):
        # check for standard or anonymous named pipes
        if cmd.find(" | ") > 0 or cmd.find(">(") or cmd.find("<("):
            return "set -o pipefail; " + cmd, True, find_bash()
        else:
            return cmd, True, None
    else:
        return cmd, False, None

def _do_run(cmd, checks, log_stdout=False):
    """Perform running and check results, raising errors for issues.
    """
    cmd, shell_arg, executable_arg = _normalize_cmd_args(cmd)
    s = subprocess.Popen(cmd, shell=shell_arg, executable=executable_arg,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, close_fds=True)
    debug_stdout = collections.deque(maxlen=100)
    while 1:
        line = s.stdout.readline()
        if line:
            debug_stdout.append(line)
            if log_stdout:
                logger_stdout.debug(line.rstrip())
            else:
                logger.debug(line.rstrip())
        exitcode = s.poll()
        if exitcode is not None:
            for line in s.stdout:
                debug_stdout.append(line)
            if exitcode is not None and exitcode != 0:
                error_msg = " ".join(cmd) if not isinstance(cmd, basestring) else cmd
                error_msg += "\n"
                error_msg += "".join(debug_stdout)
                s.communicate()
                s.stdout.close()
                raise subprocess.CalledProcessError(exitcode, error_msg)
            else:
                break
    s.communicate()
    s.stdout.close()
    # Check for problems not identified by shell return codes
    if checks:
        for check in checks:
            if not check():
                raise IOError("External command failed")

# checks for validating run completed successfully

def file_nonempty(target_file):
    def check():
        ok = utils.file_exists(target_file)
        if not ok:
            logger.info("Did not find non-empty output file {0}".format(target_file))
        return ok
    return check

def file_exists(target_file):
    def check():
        ok = os.path.exists(target_file)
        if not ok:
            logger.info("Did not find output file {0}".format(target_file))
        return ok
    return check

def file_reasonable_size(target_file, input_file):
    def check():
        # named pipes -- we can't calculate size
        if input_file.strip().startswith("<("):
            return True
        if input_file.endswith((".bam", ".gz")):
            scale = 5.0
        else:
            scale = 10.0
        orig_size = os.path.getsize(input_file) / pow(1024.0, 3)
        out_size = os.path.getsize(target_file) / pow(1024.0, 3)
        if out_size < (orig_size / scale):
            logger.info("Output file unexpectedly small. %.1fGb for output versus "
                        "%.1fGb for the input file. This often indicates a truncated "
                        "BAM file or memory errors during the run." % (out_size, orig_size))
            return False
        else:
            return True
    return check

########NEW FILE########
__FILENAME__ = profile
"""Profiling of system resources (CPU, memory, disk, filesystem IO) during pipeline runs.
"""
import contextlib
import os

from bcbio import utils
from bcbio.log import logger

@contextlib.contextmanager
def report(label, dirs):
    """Run reporting metrics to prepare reports of resource usage.
    """
    logger.info("Timing: %s" % label)
    profile_dir = utils.safe_makedir(os.path.join(dirs["work"], "profile"))
    # Prepare and start profiling scripts
    try:
        yield None
    finally:
        # Cleanup and stop profiling
        pass

########NEW FILE########
__FILENAME__ = programs
"""Identify program versions used for analysis, reporting in structured table.

Catalogs the full list of programs used in analysis, enabling reproduction of
results and tracking of provenance in output files.
"""
import os
import contextlib
import subprocess
import sys

import yaml

from bcbio import utils
from bcbio.pipeline import config_utils, version
from bcbio.log import logger

_cl_progs = [{"cmd": "bamtofastq", "name": "biobambam",
              "args": "--version", "stdout_flag": "This is biobambam version"},
             {"cmd": "bamtools", "args": "--version", "stdout_flag": "bamtools"},
             {"cmd": "bcftools", "stdout_flag": "Version:"},
             {"cmd": "bedtools", "args": "--version", "stdout_flag": "bedtools"},
             {"cmd": "bowtie2", "args": "--version", "stdout_flag": "bowtie2-align version"},
             {"cmd": "bwa", "stdout_flag": "Version:"},
             {"cmd": "cufflinks", "stdout_flag": "cufflinks"},
             {"cmd": "cutadapt", "args": "--version"},
             {"cmd": "fastqc", "args": "--version", "stdout_flag": "FastQC"},
             {"cmd": "freebayes", "stdout_flag": "version:"},
             {"cmd": "gemini", "args": "--version", "stdout_flag": "gemini "},
             {"cmd": "novosort", "paren_flag": "novosort"},
             {"cmd": "novoalign", "stdout_flag": "Novoalign"},
             {"cmd": "samtools", "stdout_flag": "Version:"},
             {"cmd": "sambamba", "stdout_flag": "sambamba"},
             {"cmd": "qualimap", "args": "-h", "stdout_flag": "QualiMap"},
             {"cmd": "tophat", "args": "--version", "stdout_flag": "TopHat"},
             {"cmd": "vcflib", "has_cl_version": False},
             {"cmd": "featurecounts", "args": "-v", "stdout_flag": "featureCounts"}]

def _broad_versioner(type):
    def get_version(config):
        from bcbio import broad
        try:
            runner = broad.runner_from_config(config)
        except ValueError:
            return ""
        if type == "gatk":
            return runner.get_gatk_version()
        elif type == "picard":
            return runner.get_picard_version("ViewSam")
        elif type == "mutect":
            try:
                runner = broad.runner_from_config(config, "mutect")
            except ValueError:
                return ""
            return runner.get_mutect_version()
        else:
            raise NotImplementedError(type)
    return get_version

def jar_versioner(program_name, jar_name):
    """Retrieve version information based on jar file.
    """
    def get_version(config):
        try:
            pdir = config_utils.get_program(program_name, config, "dir")
        # not configured
        except ValueError:
            return ""
        jar = os.path.basename(config_utils.get_jar(jar_name, pdir))
        for to_remove in [jar_name, ".jar", "-standalone"]:
            jar = jar.replace(to_remove, "")
        if jar.startswith(("-", ".")):
            jar = jar[1:]
        if jar is "":
            logger.warn("Unable to determine version for program '{}' from jar file {}".format(
                program_name, config_utils.get_jar(jar_name, pdir)))
        return jar
    return get_version

def java_versioner(pname, jar_name, **kwargs):
    def get_version(config):
        try:
            pdir = config_utils.get_program(pname, config, "dir")
        except ValueError:
            return ""
        jar = config_utils.get_jar(jar_name, pdir)
        kwargs["cmd"] = "java"
        kwargs["args"] = "-Xms128m -Xmx256m -jar %s" % jar
        return _get_cl_version(kwargs, config)
    return get_version

_alt_progs = [{"name": "bcbio_variation",
               "version_fn": jar_versioner("bcbio_variation", "bcbio.variation")},
              {"name": "gatk", "version_fn": _broad_versioner("gatk")},
              {"name": "mutect",
               "version_fn": _broad_versioner("mutect")},
              {"name": "picard", "version_fn": _broad_versioner("picard")},
              {"name": "rnaseqc",
               "version_fn": jar_versioner("rnaseqc", "RNA-SeQC")},
              {"name": "snpeff",
               "version_fn": java_versioner("snpeff", "snpEff", stdout_flag="snpEff version SnpEff")},
              {"name": "varscan",
               "version_fn": jar_versioner("varscan", "VarScan")},
              {"name": "oncofuse",
               "version_fn": jar_versioner("Oncofuse", "Oncofuse")},
              {"name": "alientrimmer",
               "version_fn": jar_versioner("AlienTrimmer", "AlienTrimmer")}
]

def _parse_from_stdoutflag(stdout, x):
    for line in stdout:
        if line.find(x) >= 0:
            parts = [p for p in line[line.find(x) + len(x):].split() if p.strip()]
            return parts[0].strip()
    return ""

def _parse_from_parenflag(stdout, x):
    for line in stdout:
        if line.find(x) >= 0:
            return line.split("(")[-1].split(")")[0]
    return ""

def _get_cl_version(p, config):
    """Retrieve version of a single commandline program.
    """
    if not p.get("has_cl_version", True):
        return ""
    try:
        prog = config_utils.get_program(p["cmd"], config)
    except config_utils.CmdNotFound:
        localpy_cmd = os.path.join(os.path.dirname(sys.executable), p["cmd"])
        if os.path.exists(localpy_cmd):
            prog = localpy_cmd
        else:
            return ""
    args = p.get("args", "")

    cmd = "{prog} {args}"
    subp = subprocess.Popen(cmd.format(**locals()), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True)
    with contextlib.closing(subp.stdout) as stdout:
        if p.get("stdout_flag"):
            v = _parse_from_stdoutflag(stdout, p["stdout_flag"])
        elif p.get("paren_flag"):
            v = _parse_from_parenflag(stdout, p["paren_flag"])
        else:
            lines = [l.strip() for l in stdout.read().split("\n") if l.strip()]
            v = lines[-1]
    if v.endswith("."):
        v = v[:-1]
    return v

def _get_brew_versions():
    """Retrieve versions of tools installed via brew.
    """
    from bcbio import install
    tooldir = install.get_defaults().get("tooldir")
    brew_cmd = os.path.join(tooldir, "bin", "brew") if tooldir else "brew"
    try:
        vout = subprocess.check_output([brew_cmd, "which"])
        uses_which = True
    except subprocess.CalledProcessError:
        vout = subprocess.check_output([brew_cmd, "list", "--versions"])
        uses_which = False
    except OSError:  # brew not installed/used
        vout = ""
    out = {}
    for vstr in vout.split("\n"):
        if vstr.strip():
            if uses_which:
                name, v = vstr.rstrip().split(": ")
            else:
                parts = vstr.rstrip().split()
                name = parts[0]
                v = parts[-1]
            out[name] = v
    return out

def _get_versions(config=None):
    """Retrieve details on all programs available on the system.
    """
    out = [{"program": "bcbio-nextgen",
            "version": ("%s-%s" % (version.__version__, version.__git_revision__)
                        if version.__git_revision__ else version.__version__)}]
    manifest_vs = _get_versions_manifest()
    if manifest_vs:
        return out + manifest_vs
    else:
        assert config is not None, "Need configuration to retrieve from non-manifest installs"
        brew_vs = _get_brew_versions()
        import HTSeq
        out.append({"program": "htseq", "version": HTSeq.__version__})
        for p in _cl_progs:
            out.append({"program": p["cmd"],
                        "version": (brew_vs[p["cmd"]] if p["cmd"] in brew_vs else
                                    _get_cl_version(p, config))})
        for p in _alt_progs:
            out.append({"program": p["name"],
                        "version": (brew_vs[p["name"]] if p["name"] in brew_vs else
                                    p["version_fn"](config))})
        return out

def _get_versions_manifest():
    """Retrieve versions from a pre-existing manifest of installed software.
    """
    all_pkgs = ["htseq", "cn.mops", "vt", "platypus-variant", "gatk-framework"] + \
               [p.get("name", p["cmd"]) for p in _cl_progs] + [p["name"] for p in _alt_progs]
    manifest_dir = os.path.join(config_utils.get_base_installdir(), "manifest")
    if os.path.exists(manifest_dir):
        out = []
        for plist in ["toolplus", "brew", "python", "r", "debian", "custom"]:
            pkg_file = os.path.join(manifest_dir, "%s-packages.yaml" % plist)
            if os.path.exists(pkg_file):
                with open(pkg_file) as in_handle:
                    pkg_info = yaml.safe_load(in_handle)
                added = []
                for pkg in all_pkgs:
                    if pkg in pkg_info:
                        added.append(pkg)
                        out.append({"program": pkg, "version": pkg_info[pkg]["version"]})
                for x in added:
                    all_pkgs.remove(x)
        out.sort(key=lambda x: x["program"])
        for pkg in all_pkgs:
            out.append({"program": pkg, "version": ""})
        return out

def _get_program_file(dirs):
    if dirs.get("work"):
        base_dir = utils.safe_makedir(os.path.join(dirs["work"], "provenance"))
        return os.path.join(base_dir, "programs.txt")

def write_versions(dirs, config=None, is_wrapper=False):
    """Write CSV file with versions used in analysis pipeline.
    """
    out_file = _get_program_file(dirs)
    if is_wrapper:
        assert utils.file_exists(out_file), "Failed to create program versions from VM"
    elif out_file is None:
        for p in _get_versions(config):
            print("{program},{version}".format(**p))
    else:
        with open(out_file, "w") as out_handle:
            for p in _get_versions(config):
                out_handle.write("{program},{version}\n".format(**p))
    return out_file

def add_subparser(subparsers):
    """Add command line option for exporting version information.
    """
    parser = subparsers.add_parser("version",
                                   help="Export versions of used software to stdout or a file ")
    parser.add_argument("--workdir", help="Directory export programs to in workdir/provenance/programs.txt",
                        default=None)

def get_version(name, dirs=None, config=None):
    """Retrieve the current version of the given program from cached names.
    """
    if dirs:
        p = _get_program_file(dirs)
    else:
        p = config["resources"]["program_versions"]
    with open(p) as in_handle:
        for line in in_handle:
            prog, version = line.rstrip().split(",")
            if prog == name and version:
                return version
    raise KeyError("Version information not found for %s in %s" % (name, p))

########NEW FILE########
__FILENAME__ = system
"""Identify system information for distributed systems, used to manage resources.

This provides a background on cluster and single multicore systems allowing
jobs to be reasonably distributed in cases of higher memory usage.
"""
import copy
import multiprocessing
import os
import resource
import shlex
import socket
import subprocess

import yaml
from xml.etree import ElementTree as ET

from bcbio import utils
from bcbio.log import logger

def _get_cache_file(dirs, parallel):
    base_dir = utils.safe_makedir(os.path.join(dirs["work"], "provenance"))
    return os.path.join(base_dir, "system-%s-%s.yaml" % (parallel["type"],
                                                         parallel.get("queue", "default")))

def write_info(dirs, parallel, config):
    """Write cluster or local filesystem resources, spinning up cluster if not present.
    """
    if parallel["type"] in ["ipython"] and not parallel.get("run_local"):
        out_file = _get_cache_file(dirs, parallel)
        if not utils.file_exists(out_file):
            sys_config = copy.deepcopy(config)
            minfos = _get_machine_info(parallel, sys_config, dirs, config)
            with open(out_file, "w") as out_handle:
                yaml.safe_dump(minfos, out_handle, default_flow_style=False, allow_unicode=False)

def _get_machine_info(parallel, sys_config, dirs, config):
    """Get machine resource information from the job scheduler via either the command line or the queue.
    """
    if parallel.get("queue") and parallel.get("scheduler"):
        # dictionary as switch statement; can add new scheduler implementation functions as (lowercase) keys
        sched_info_dict = {
                            "slurm": _slurm_info,
                            "torque": _torque_info,
                            "sge": _sge_info
                          }
        if parallel["scheduler"].lower() in sched_info_dict:
            try:
                return sched_info_dict[parallel["scheduler"].lower()](parallel.get("queue", ""))
            except:
                # If something goes wrong, just hit the queue
                logger.exception("Couldn't get machine information from resource query function for queue "
                                 "'{0}' on scheduler \"{1}\"; "
                                 "submitting job to queue".format(parallel.get("queue", ""), parallel["scheduler"]))
        else:
            logger.info("Resource query function not implemented for scheduler \"{0}\"; "
                         "submitting job to queue".format(parallel["scheduler"]))
    from bcbio.distributed import prun
    with prun.start(parallel, [[sys_config]], config, dirs) as run_parallel:
        return run_parallel("machine_info", [[sys_config]])

def _slurm_info(queue):
    """Returns machine information for a slurm job scheduler.
    """
    cl = "sinfo -h -p {} --format '%c %m'".format(queue)
    num_cpus, mem = subprocess.check_output(shlex.split(cl)).split()
    # if the queue contains multiple memory configurations, the minimum value is printed with a trailing '+'
    mem = mem.replace('+', '')
    return [{"cores": int(num_cpus), "memory": float(mem) / 1024.0, "name": "slurm_machine"}]

def _torque_info(queue):
    """Return machine information for a torque job scheduler using pbsnodes.

    To identify which host to use it tries to parse available hosts
    from qstat -Qf `acl_hosts`. If found, it uses these and gets the
    first node from pbsnodes matching to the list. If no attached
    hosts are available, it uses the first host found from pbsnodes.
    """
    nodes = _torque_queue_nodes(queue)
    pbs_out = subprocess.check_output(["pbsnodes"])
    info = {}
    for i, line in enumerate(pbs_out.split("\n")):
        if i == 0 and len(nodes) == 0:
            info["name"] = line.strip()
        elif line.startswith(nodes):
            info["name"] = line.strip()
        elif info.get("name"):
            if line.strip().startswith("np = "):
                info["cores"] = int(line.replace("np = ", "").strip())
            elif line.strip().startswith("status = "):
                mem = [x for x in pbs_out.split(",") if x.startswith("totmem=")][0]
                info["memory"] = float(mem.split("=")[1].rstrip("kb")) / 1048576.0
                return [info]

def _torque_queue_nodes(queue):
    """Retrieve the nodes available for a queue.

    Parses out nodes from `acl_hosts` in qstat -Qf and extracts the
    initial names of nodes used in pbsnodes.
    """
    qstat_out = subprocess.check_output(["qstat", "-Qf", queue])
    hosts = []
    in_hosts = False
    for line in qstat_out.split("\n"):
        if line.strip().startswith("acl_hosts = "):
            hosts.extend(line.replace("acl_hosts = ", "").strip().split(","))
            in_hosts = True
        elif in_hosts:
            if line.find(" = ") > 0:
                break
            else:
                hosts.extend(line.strip().split(","))
    return tuple([h.split(".")[0].strip() for h in hosts if h.strip()])

def _sge_info(queue):
    """Returns machine information for an sge job scheduler.
    """
    qhost_out = subprocess.check_output(["qhost", "-q", "-xml"])
    qstat_queue = ["-q", queue] if queue and "," not in queue else []
    qstat_out = subprocess.check_output(["qstat", "-f", "-xml"] + qstat_queue)
    slot_info = _sge_get_slots(qstat_out)
    mem_info = _sge_get_mem(qhost_out, queue)
    machine_keys = slot_info.keys()
    #num_cpus_vec = [slot_info[x]["slots_total"] for x in machine_keys]
    #mem_vec = [mem_info[x]["mem_total"] for x in machine_keys]
    mem_per_slot = [mem_info[x]["mem_total"] / float(slot_info[x]["slots_total"]) for x in machine_keys]
    min_ratio_index = mem_per_slot.index(min(mem_per_slot))
    mem_info[machine_keys[min_ratio_index]]["mem_total"]
    return [{"cores": slot_info[machine_keys[min_ratio_index]]["slots_total"],
             "memory": mem_info[machine_keys[min_ratio_index]]["mem_total"],
             "name": "sge_machine"}]

def _sge_get_slots(xmlstring):
    """ Get slot information from qstat
    """
    rootxml = ET.fromstring(xmlstring)
    my_machine_dict = {}
    for queue_list in rootxml.iter("Queue-List"):
        # find all hosts supporting queues
        my_hostname = queue_list.find("name").text.rsplit("@")[-1]
        my_slots = queue_list.find("slots_total").text
        my_machine_dict[my_hostname] = {}
        my_machine_dict[my_hostname]["slots_total"] = int(my_slots)
    return my_machine_dict

def _sge_get_mem(xmlstring, queue_name):
    """ Get memory information from qhost
    """
    rootxml = ET.fromstring(xmlstring)
    my_machine_dict = {}
    # on some machines rootxml.tag looks like "{...}qhost" where the "{...}" gets prepended to all attributes
    rootTag = rootxml.tag.rstrip("qhost")
    for host in rootxml.findall(rootTag + 'host'):
        # find all hosts supporting queues
        for queues in host.findall(rootTag + 'queue'):
            # if the user specified queue matches that in the xml:
            if not queue_name or any(q in queues.attrib['name'] for q in queue_name.split(",")):
                my_machine_dict[host.attrib['name']] = {}
                # values from xml for number of processors and mem_total on each machine
                for hostvalues in host.findall(rootTag + 'hostvalue'):
                    if('mem_total' == hostvalues.attrib['name']):
                        if hostvalues.text.lower().endswith('g'):
                            multip = 1
                        elif hostvalues.text.lower().endswith('m'):
                            multip = 1 / float(1024)
                        elif hostvalues.text.lower().endswith('t'):
                            multip = 1024
                        else:
                            raise Exception("Unrecognized suffix in mem_tot from SGE")
                        my_machine_dict[host.attrib['name']]['mem_total'] = \
                                float(hostvalues.text[:-1]) * float(multip)
                break
    return my_machine_dict

def _combine_machine_info(xs):
    if len(xs) == 1:
        return xs[0]
    else:
        raise NotImplementedError("Add logic to pick specification from non-homogeneous clusters.")

def get_info(dirs, parallel):
    """Retrieve cluster or local filesystem resources from pre-retrieved information.
    """
    if parallel["type"] in ["ipython"]:
        cache_file = _get_cache_file(dirs, parallel)
        if utils.file_exists(cache_file):
            with open(cache_file) as in_handle:
                minfo = yaml.load(in_handle)
            return _combine_machine_info(minfo)
        else:
            return {}
    else:
        return _combine_machine_info(machine_info())

def machine_info():
    """Retrieve core and memory information for the current machine.
    """
    import psutil
    BYTES_IN_GIG = 1073741824
    free_bytes = psutil.virtual_memory().available
    return [{"memory": float(free_bytes / BYTES_IN_GIG), "cores": multiprocessing.cpu_count(),
             "name": socket.gethostname()}]

def open_file_limit():
    return resource.getrlimit(resource.RLIMIT_NOFILE)[0]

########NEW FILE########
__FILENAME__ = versioncheck
"""Check specific required program versions required during the pipeline.
"""
from distutils.version import LooseVersion
import subprocess

from bcbio.pipeline import config_utils
from bcbio.log import logger

def samtools(config, items):
    """Ensure samtools has parallel processing required for piped analysis.
    """
    samtools = config_utils.get_program("samtools", config)
    p = subprocess.Popen([samtools, "sort"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = p.communicate()
    p.stdout.close()
    if output.find("-@") == -1:
        return ("Installed version of samtools sort does not have support for multithreading (-@ option) "
                "required to support bwa piped alignment and BAM merging. "
                "Please upgrade to the latest version "
                "from http://samtools.sourceforge.net/")

def _has_pipeline(items):
    """Only perform version checks when we're running an analysis pipeline.
    """
    return any(item.get("analysis", "") != "" for item in items)

def _is_variant(items):
    return any(item.get("analysis", "").lower().startswith("variant") for item in items)

def java(config, items):
    """GATK and derived tools requires Java 1.7 or better.
    """
    want_version = "1.7" if _is_variant(items) else "1.6"
    try:
        java = config_utils.get_program("java", config)
    except config_utils.CmdNotFound:
        return ("java not found on PATH. Java %s or better required." % want_version)
    p = subprocess.Popen([java, "-Xms250m", "-Xmx250m", "-version"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = p.communicate()
    p.stdout.close()
    version = ""
    for line in output.split("\n"):
        if line.startswith("java version"):
            version = line.strip().split()[-1]
            if version.startswith('"'):
                version = version[1:]
            if version.endswith('"'):
                version = version[:-1]
    if not version or LooseVersion(version) < LooseVersion(want_version):
        return ("java version %s or better required for running GATK and other tools. "
                "Found version %s at %s" % (want_version, version, java))

def testall(items):
    logger.info("Testing minimum versions of installed programs")
    items = [x[0] for x in items]
    config = items[0]["config"]
    msgs = []
    if _has_pipeline(items):
        for fn in [samtools, java]:
            out = fn(config, items)
            if out:
                msgs.append(out)
    if msgs:
        raise OSError("Program problems found. You can upgrade dependencies with:\n" +
                      "bcbio_nextgen.py upgrade -u skip --tooldir=/usr/local\n\n" +
                      "\n".join(msgs))

########NEW FILE########
__FILENAME__ = count
"""
count number of reads mapping to features of transcripts

"""
import os
import sys
import itertools

# soft imports
try:
    import HTSeq
    import pandas as pd
    import gffutils
except ImportError:
    HTSeq, pd, gffutils = None, None, None

from bcbio.utils import (file_exists, get_in)
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio import bam


def _get_files(data):
    mapped = bam.mapped(data["work_bam"], data["config"])
    in_file = bam.sort(mapped, data["config"], order="queryname")
    gtf_file = data["genome_resources"]["rnaseq"]["transcripts"]
    work_dir = data["dirs"].get("work", "work")
    out_dir = os.path.join(work_dir, "htseq-count")
    out_file = os.path.join(out_dir, data['rgnames']['sample']) + ".counts"
    stats_file = os.path.join(out_dir, data['rgnames']['sample']) + ".stats"
    return in_file, gtf_file, out_file, stats_file


def is_countfile(in_file):
    with open(in_file) as in_handle:
        firstline = in_handle.next().split("\t")
    if len(firstline) != 2:
        return False
    try:
        int(firstline[1])
    except ValueError:
        return False
    return True


def invert_strand(iv):
    iv2 = iv.copy()
    if iv2.strand == "+":
        iv2.strand = "-"
    elif iv2.strand == "-":
        iv2.strand = "+"
    else:
        raise ValueError("Illegal strand")
    return iv2


class UnknownChrom(Exception):
    pass

def _get_stranded_flag(config):
    strand_flag = {"unstranded": "no",
                   "firststrand": "reverse",
                   "secondstrand": "yes"}
    stranded = _get_strandedness(config)
    assert stranded in strand_flag, ("%s is not a valid strandedness value. "
                                     "Valid values are 'firststrand', 'secondstrand', "
                                     "and 'unstranded")
    return strand_flag[stranded]

def _get_strandedness(config):
    return get_in(config, ("algorithm", "strandedness"), "unstranded").lower()


def htseq_count(data):
    """ adapted from Simon Anders htseq-count.py script
    http://www-huber.embl.de/users/anders/HTSeq/doc/count.html
    """

    sam_filename, gff_filename, out_file, stats_file = _get_files(data)
    stranded = _get_stranded_flag(data["config"])
    overlap_mode = "union"
    feature_type = "exon"
    id_attribute = "gene_id"
    minaqual = 0


    if file_exists(out_file):
        return out_file

    logger.info("Counting reads mapping to exons in %s using %s as the "
                    "annotation and strandedness as %s." % (os.path.basename(sam_filename),
                    os.path.basename(gff_filename), _get_strandedness(data["config"])))

    features = HTSeq.GenomicArrayOfSets("auto", stranded != "no")
    counts = {}

    # Try to open samfile to fail early in case it is not there
    open(sam_filename).close()

    gff = HTSeq.GFF_Reader(gff_filename)
    i = 0
    try:
        for f in gff:
            if f.type == feature_type:
                try:
                    feature_id = f.attr[id_attribute]
                except KeyError:
                    sys.exit("Feature %s does not contain a '%s' attribute" %
                             (f.name, id_attribute))
                if stranded != "no" and f.iv.strand == ".":
                    sys.exit("Feature %s at %s does not have strand "
                             "information but you are running htseq-count "
                             "in stranded mode. Use '--stranded=no'." %
                             (f.name, f.iv))
                features[f.iv] += feature_id
                counts[f.attr[id_attribute]] = 0
            i += 1
            if i % 100000 == 0:
                sys.stderr.write("%d GFF lines processed.\n" % i)
    except:
        sys.stderr.write("Error occured in %s.\n"
                         % gff.get_line_number_string())
        raise

    sys.stderr.write("%d GFF lines processed.\n" % i)

    if len(counts) == 0:
        sys.stderr.write("Warning: No features of type '%s' found.\n"
                         % feature_type)

    try:
        align_reader = htseq_reader(sam_filename)
        first_read = iter(align_reader).next()
        pe_mode = first_read.paired_end
    except:
        sys.stderr.write("Error occured when reading first line of sam "
                         "file.\n")
        raise

    try:
        if pe_mode:
            read_seq_pe_file = align_reader
            read_seq = HTSeq.pair_SAM_alignments(align_reader)
        empty = 0
        ambiguous = 0
        notaligned = 0
        lowqual = 0
        nonunique = 0
        i = 0
        for r in read_seq:
            i += 1
            if not pe_mode:
                if not r.aligned:
                    notaligned += 1
                    continue
                try:
                    if r.optional_field("NH") > 1:
                        nonunique += 1
                        continue
                except KeyError:
                    pass
                if r.aQual < minaqual:
                    lowqual += 1
                    continue
                if stranded != "reverse":
                    iv_seq = (co.ref_iv for co in r.cigar if co.type == "M"
                              and co.size > 0)
                else:
                    iv_seq = (invert_strand(co.ref_iv) for co in r.cigar if
                              co.type == "M" and co.size > 0)
            else:
                if r[0] is not None and r[0].aligned:
                    if stranded != "reverse":
                        iv_seq = (co.ref_iv for co in r[0].cigar if
                                  co.type == "M" and co.size > 0)
                    else:
                        iv_seq = (invert_strand(co.ref_iv) for co in r[0].cigar if
                                  co.type == "M" and co.size > 0)
                else:
                    iv_seq = tuple()
                if r[1] is not None and r[1].aligned:
                    if stranded != "reverse":
                        iv_seq = itertools.chain(iv_seq,
                                                 (invert_strand(co.ref_iv) for co
                                                  in r[1].cigar if co.type == "M"
                                                  and co.size > 0))
                    else:
                        iv_seq = itertools.chain(iv_seq,
                                                 (co.ref_iv for co in r[1].cigar
                                                  if co.type == "M" and co.size
                                                  > 0))
                else:
                    if (r[0] is None) or not (r[0].aligned):
                        notaligned += 1
                        continue
                try:
                    if (r[0] is not None and r[0].optional_field("NH") > 1) or \
                       (r[1] is not None and r[1].optional_field("NH") > 1):
                        nonunique += 1
                        continue
                except KeyError:
                    pass
                if (r[0] and r[0].aQual < minaqual) or (r[1] and
                                                        r[1].aQual < minaqual):
                    lowqual += 1
                    continue

            try:
                if overlap_mode == "union":
                    fs = set()
                    for iv in iv_seq:
                        if iv.chrom not in features.chrom_vectors:
                            raise UnknownChrom
                        for iv2, fs2 in features[iv].steps():
                            fs = fs.union(fs2)
                elif (overlap_mode == "intersection-strict" or
                      overlap_mode == "intersection-nonempty"):
                    fs = None
                    for iv in iv_seq:
                        if iv.chrom not in features.chrom_vectors:
                            raise UnknownChrom
                        for iv2, fs2 in features[iv].steps():
                            if (len(fs2) > 0 or overlap_mode == "intersection-strict"):
                                if fs is None:
                                    fs = fs2.copy()
                                else:
                                    fs = fs.intersection(fs2)
                else:
                    sys.exit("Illegal overlap mode.")
                if fs is None or len(fs) == 0:
                    empty += 1
                elif len(fs) > 1:
                    ambiguous += 1
                else:
                    counts[list(fs)[0]] += 1
            except UnknownChrom:
                if not pe_mode:
                    rr = r
                else:
                    rr = r[0] if r[0] is not None else r[1]
                empty += 1

            if i % 100000 == 0:
                sys.stderr.write("%d sam %s processed.\n" %
                                 ( i, "lines " if not pe_mode else "line pairs"))

    except:
        if not pe_mode:
            sys.stderr.write("Error occured in %s.\n"
                             % read_seq.get_line_number_string())
        else:
            sys.stderr.write("Error occured in %s.\n"
                             % read_seq_pe_file.get_line_number_string() )
        raise

    sys.stderr.write("%d sam %s processed.\n" %
                     (i, "lines " if not pe_mode else "line pairs"))

    with file_transaction(out_file) as tmp_out_file:
        with open(tmp_out_file, "w") as out_handle:
            on_feature = 0
            for fn in sorted(counts.keys()):
                on_feature += counts[fn]
                out_handle.write("%s\t%d\n" % (fn, counts[fn]))

    with file_transaction(stats_file) as tmp_stats_file:
        with open(tmp_stats_file, "w") as out_handle:
            out_handle.write("on_feature\t%d\n" % on_feature)
            out_handle.write("no_feature\t%d\n" % empty)
            out_handle.write("ambiguous\t%d\n" % ambiguous)
            out_handle.write("too_low_aQual\t%d\n" % lowqual)
            out_handle.write("not_aligned\t%d\n" % notaligned)
            out_handle.write("alignment_not_unique\t%d\n" % nonunique)

    return out_file

def combine_count_files(files, out_file=None):
    """
    combine a set of count files into a single combined file
    """
    for f in files:
        assert file_exists(f), "%s does not exist or is empty." % f
        assert is_countfile(f), "%s does not seem to be a count file." % f
    col_names = [os.path.basename(os.path.splitext(x)[0]) for x in files]
    if not out_file:
        out_dir = os.path.join(os.path.dirname(files[0]))
        out_file = os.path.join(out_dir, "combined.counts")

    if file_exists(out_file):
        return out_file

    df = pd.io.parsers.read_table(f, sep="\t", index_col=0, header=None,
                                  names=[col_names[0]])
    for i, f in enumerate(files):
        if i == 0:
            df = pd.io.parsers.read_table(f, sep="\t", index_col=0, header=None,
                                          names=[col_names[0]])
        else:
            df = df.join(pd.io.parsers.read_table(f, sep="\t", index_col=0,
                                                  header=None,
                                                  names=[col_names[i]]))

    df.to_csv(out_file, sep="\t", index_label="id")
    return out_file

def annotate_combined_count_file(count_file, gtf_file, out_file=None):
    dbfn = gtf_file + ".db"
    if not file_exists(dbfn):
        return None

    if not gffutils:
        return None

    db = gffutils.FeatureDB(dbfn, keep_order=True)

    if not out_file:
        out_dir = os.path.dirname(count_file)
        out_file = os.path.join(out_dir, "annotated_combined.counts")

    # if the genes don't have a gene_id or gene_name set, bail out
    try:
        symbol_lookup = {f['gene_id'][0]: f['gene_name'][0] for f in
                         db.features_of_type('exon')}
    except KeyError:
        return None

    df = pd.io.parsers.read_table(count_file, sep="\t", index_col=0, header=0)

    df['symbol'] = df.apply(lambda x: symbol_lookup.get(x.name, ""), axis=1)
    df.to_csv(out_file, sep="\t", index_label="id")
    return out_file


def htseq_reader(align_file):
    """
    returns a read-by-read sequence reader for a BAM or SAM file
    """
    if bam.is_sam(align_file):
        read_seq = HTSeq.SAM_Reader(align_file)
    elif bam.is_bam(align_file):
        read_seq = HTSeq.BAM_Reader(align_file)
    else:
        logger.error("%s is not a SAM or BAM file" % (align_file))
        sys.exit(1)
    return read_seq

########NEW FILE########
__FILENAME__ = coverage
"""
Functions to handle plotting coverage across genes
"""
try:
    from chanjo import bam
except ImportError:
    bam = None
try:
    import gffutils
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError:
    gffutils, pd, plt = None, None, None

import random
import numpy as np
from collections import defaultdict, Counter

from bcbio.utils import file_exists

def _select_random_nonzero_genes(count_file):
    """
    given a count file with rows of gene_ids and columns of counts
    return a random set of genes with non-zero counts
    """
    MIN_READS = 100
    DEFAULT_NUM_SAMPLES = 100
    df = pd.io.parsers.read_csv(count_file, delimiter="\t", header=0, index_col=0)
    means = pd.DataFrame({"mean": df.mean(1)}, index=df.index)
    means = means[means['mean'] > MIN_READS]
    NUM_SAMPLES = min(DEFAULT_NUM_SAMPLES, len(means))
    rows = random.sample(means.index, NUM_SAMPLES)
    return list(means.ix[rows].index)

def _plot_coverage(df, out_file):
    fig = plt.gcf()
    df.plot(x='distance', y='depths', subplots=True)
    fig.savefig(out_file)
    plt.close(fig)
    return out_file

def _normalize_coverage(read_depths):
    """
    given a list of read depths for a gene, scales read depth to
    a 100 bp faux-gene so multiple genes can be averaged
    together to get an overall view of coverage for a set of genes
    """
    gene_length = len(read_depths)
    norm_dist = [100 * float(x) / gene_length for x in range(gene_length)]
    df = pd.DataFrame({"distance": norm_dist, "depths": read_depths})
    return df


def _gene_depth(dbfn, bamfn, gene):
    """
    takes a gffutils db (dbfn), a BAM file (bamfn) and a gene_id (gene)
    and returns a 5' -> 3' list of per-base read depths for the exons of
    the gene
    """
    db = gffutils.FeatureDB(dbfn, keep_order=True)
    read_depths = []
    bam_handle = bam.CoverageAdapter(bamfn)
    for exon in db.children(gene, featuretype="exon", order_by='start'):
        strand = exon.strand
        coord = [exon.start, exon.end]
        read_depths += bam_handle.read(exon.seqid, min(coord), max(coord)).tolist()
    # return a list of depths going in the 5' -> 3' direction
    if strand == "-":
       read_depths = read_depths[::-1]
    return read_depths

def plot_gene_coverage(bam_file, ref_file, count_file, out_file):
    if file_exists(out_file):
        return out_file
    coverage = pd.DataFrame()
    ref_db = ref_file + ".db"
    for gene in _select_random_nonzero_genes(count_file):
        depth = _gene_depth(ref_db, bam_file, gene)
        coverage = coverage.append(_normalize_coverage(depth))

    # group into 100 bins for 0->100% along the transcript
    if coverage.empty:
        return None

    groups = coverage.groupby(np.digitize(coverage.distance, range(100)))
    out_file = _plot_coverage(groups.mean(), out_file)
    return out_file

def estimate_library_content(bam_file, ref_file):
    ref_db = ref_file + ".db"
    library_content = defaultdict(Counter)
    db = gffutils.FeatureDB(ref_db, keep_order=True)
    with bam.open_samfile(bam_file) as bam_handle:
        for read in bam_handle:
            name = read.getrname(read.tid)
            start = read.pos
            end = read.aend
            overlapped = db.region((name, start, end))

########NEW FILE########
__FILENAME__ = cufflinks
"""Assess transcript abundance in RNA-seq experiments using Cufflinks.

http://cufflinks.cbcb.umd.edu/manual.html
"""
import os

from bcbio.utils import get_in, file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do


def run(align_file, ref_file, data):
    config = data["config"]
    cmd = _get_general_options(align_file, config)
    cmd.extend(_get_no_assembly_options(ref_file, data))
    out_dir = _get_output_dir(align_file, data)
    out_file = os.path.join(out_dir, "genes.fpkm_tracking")
    if file_exists(out_file):
        return out_dir
    with file_transaction(out_dir) as tmp_out_dir:
        cmd.extend(["--output-dir", tmp_out_dir])
        cmd.extend([align_file])
        cmd = map(str, cmd)
        do.run(cmd, "Cufflinks on %s." % (align_file))
    return out_dir

def _get_general_options(align_file, config):
    options = []
    cufflinks = config_utils.get_program("cufflinks", config)
    options.extend([cufflinks])
    options.extend(["--num-threads", config["algorithm"].get("num_cores", 1)])
    options.extend(["--quiet"])
    options.extend(["--no-update-check"])
    options.extend(["--max-bundle-frags", 2000000])
    return options

def _get_no_assembly_options(ref_file, data):
    options = []
    options.extend(["--frag-bias-correct", ref_file])
    options.extend(["--multi-read-correct"])
    options.extend(["--upper-quartile-norm"])
    gtf_file = data["genome_resources"]["rnaseq"].get("transcripts", "")
    if gtf_file:
        options.extend(["--GTF", gtf_file])
    mask_file = data["genome_resources"]["rnaseq"].get("transcripts_mask", "")
    if mask_file:
        options.extend(["--mask-file", mask_file])

    return options


def _get_output_dir(align_file, data):
    config = data["config"]
    name = data["rgnames"]["sample"]
    return os.path.join(get_in(data, ("dirs", "work")), "cufflinks", name)

########NEW FILE########
__FILENAME__ = featureCounts
import os

from bcbio.utils import (file_exists, get_in, safe_makedir)
from bcbio.pipeline import config_utils
from bcbio.log import logger
from bcbio.rnaseq.count import htseq_count
from bcbio.bam import is_paired
from bcbio.provenance import do
from bcbio.distributed.transaction import file_transaction

try:
    import pandas as pd
except ImportError:
    pd = None

def count(data):
    """
    count reads mapping to genes using featureCounts
    falls back on htseq_count method if featureCounts is not
    found
    """
    in_bam = data["work_bam"]
    gtf_file = data["genome_resources"]["rnaseq"]["transcripts"]
    work_dir = data["dirs"].get("work", "work")
    out_dir = os.path.join(work_dir, "htseq-count")
    safe_makedir(out_dir)
    count_file = os.path.join(out_dir, data['rgnames']['sample']) + ".counts"
    if file_exists(count_file):
        return count_file

    config = data["config"]

    try:
        featureCounts = config_utils.get_program("featureCounts", config)
    except config_utils.CmdNotFound:
        logger.info("featureCounts not found, falling back to htseq-count "
                    "for feature counting. You can upgrade the tools to "
                    "install featureCount with bcbio_nextgen.py upgrade "
                    "--tools.")
        return htseq_count(data)

    paired_flag = _paired_flag(in_bam)
    strand_flag = _strand_flag(config)

    cmd = ("{featureCounts} -a {gtf_file} -o {tx_count_file} -s {strand_flag} "
           "{paired_flag} {in_bam}")

    message = ("Count reads in {tx_count_file} mapping to {gtf_file} using "
               "featureCounts")
    with file_transaction(count_file) as tx_count_file:
        do.run(cmd.format(**locals()), message.format(**locals()))
    fixed_count_file = _format_count_file(count_file)
    os.rename(fixed_count_file, count_file)

    return count_file

def _format_count_file(count_file):
    """
    this cuts the count file produced from featureCounts down to
    a two column file of gene ids and number of reads mapping to
    each gene
    """
    COUNT_COLUMN = 5
    out_file = os.path.splitext(count_file)[0] + ".fixed.counts"
    if file_exists(out_file):
        return out_file

    df = pd.io.parsers.read_table(count_file, sep="\t", index_col=0, header=1)
    df_sub = df.ix[:, COUNT_COLUMN]
    with file_transaction(out_file) as tx_out_file:
        df_sub.to_csv(tx_out_file, sep="\t", index_label="id", header=False)
    return out_file


def _strand_flag(config):
    """
    0: unstranded 1: stranded 2: reverse stranded
    """
    strand_flag = {"unstranded": "0",
                   "firststrand": "2",
                   "secondstrand": "1"}
    stranded =  get_in(config, ("algorithm", "strandedness"),
                       "unstranded").lower()

    assert stranded in strand_flag, ("%s is not a valid strandedness value. "
                                     "Valid values are 'firststrand', 'secondstrand', "
                                     "and 'unstranded")
    return strand_flag[stranded]

def _paired_flag(bam_file):
    if is_paired(bam_file):
        return "-p -B -C"
    else:
        return ""




########NEW FILE########
__FILENAME__ = oncofuse
"""annonate fusion transcript using external programs.

Supported:
  oncofuse: http://www.unav.es/genetica/oncofuse.html
"""

import os
import csv
import glob

from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do

# ## oncofuse fusion trancript detection
#haven't tested with STAR, instructions referenced from seqanswer, http://seqanswers.com/forums/archive/index.php/t-33095.html

def run(data):
    #cmd line: java -Xmx1G -jar Oncofuse.jar input_file input_type tissue_type output_file
    config = data["config"]
    genome_build = data.get("genome_build", "")
    input_type, input_dir, input_file = _get_input_para(data)
    if genome_build == 'GRCh37': #assume genome_build is hg19 otherwise
        if config["algorithm"].get("aligner") in ['star']:
            input_file = _fix_star_junction_output(input_file)
        if config["algorithm"].get("aligner") in ['tophat', 'tophat2']:
            input_file = _fix_tophat_junction_output(input_file)
    
    #handle cases when fusion file doesn't exist
    if not file_exists(input_file):
        return None
    
    out_file = os.path.join(input_dir, 'oncofuse_out.txt')
    
    if file_exists(out_file):
        return out_file
    
    oncofuse_jar = config_utils.get_jar("Oncofuse",
                                      config_utils.get_program("oncofuse",
                                                               config, "dir"))

    tissue_type = _oncofuse_tissue_arg_from_config(data)
    resources = config_utils.get_resources("oncofuse", config)
    if not file_exists(out_file):
        cl = ["java"]
        cl += resources.get("jvm_opts", ["-Xms750m", "-Xmx5g"])
        cl += ["-jar", oncofuse_jar, input_file, input_type, tissue_type, out_file]
        with open(out_file, "w") as out_handle:
            cmd = " ".join(cl)
            try:
                do.run(cmd, "oncofuse fusion detection", data)
            except:
                return out_file
    return out_file

def is_non_zero_file(fpath):  
    return True if os.path.isfile(fpath) and os.path.getsize(fpath) > 0 else False

def _get_input_para(data):

    TOPHAT_FUSION_OUTFILE = "fusions.out"
    STAR_FUSION_OUTFILE = 'Chimeric.out.junction'
    
    
    config = data["config"]
    aligner = config["algorithm"].get("aligner")
    if aligner == 'tophat2':
        aligner = 'tophat'
    names = data["rgnames"]
    align_dir_parts = os.path.join(data["dirs"]["work"], "align", names["lane"], names["sample"]+"_%s" % aligner)
    if aligner in ['tophat', 'tophat2']:
        align_dir_parts = os.path.join(data["dirs"]["work"], "align", names["lane"], names["sample"]+"_%s" % aligner)
        return 'tophat', align_dir_parts, os.path.join(align_dir_parts, TOPHAT_FUSION_OUTFILE)
    if aligner in ['star']:
        align_dir_parts = os.path.join(data["dirs"]["work"], "align", names["lane"])
        return 'rnastar', align_dir_parts, os.path.join(align_dir_parts,names["lane"]+STAR_FUSION_OUTFILE)
    return None

def _fix_tophat_junction_output(chimeric_out_junction_file):
    #for fusion.out
    out_file = chimeric_out_junction_file + '.hg19'
    with open(out_file, "w") as out_handle:
        with open(chimeric_out_junction_file, "r") as in_handle:
            for line in in_handle:
                parts = line.split("\t")
                left, right = parts[0].split("-")
                parts[0] = "%s-%s" % (_h37tohg19(left), _h37tohg19(right))
                out_handle.write("\t".join(parts))
    return out_file    
    
def _fix_star_junction_output(chimeric_out_junction_file):
    #for Chimeric.out.junction
    out_file = chimeric_out_junction_file + '.hg19'
    with open(out_file, "w") as out_handle:
        with open(chimeric_out_junction_file, "r") as in_handle:
            for line in in_handle:
                parts = line.split("\t")
                parts[0] = _h37tohg19(parts[0])
                parts[3] = _h37tohg19(parts[3])
                out_handle.write("\t".join(parts))
    return out_file

def _h37tohg19(chromosome):
    MAX_CHROMOSOMES = 23
    if chromosome in [str(x) for x in range(1, MAX_CHROMOSOMES)] + ["X", "Y"]:
        new_chrom = "chr%s" % chromosome
    elif chromosome == "MT":
        new_chrom = "chrM"
    else:
        raise NotImplementedError(chromosome)
    return new_chrom


def _oncofuse_tissue_arg_from_config(data):

    """Retrieve oncofuse arguments supplied through input configuration.
    tissue_type is the library argument, which tells Oncofuse to use its
    own pre-built gene expression libraries. There are four pre-built
    libraries, corresponding to the four supported tissue types:
    EPI (epithelial origin),
    HEM (hematological origin),
    MES (mesenchymal origin) and
    AVG (average expression, if tissue source is unknown).
    """
    SUPPORTED_TIISUE_TYPE = ["EPI", "HEM", "MES", "AVG"]
    if data.get("metadata", {}).get("tissue") in SUPPORTED_TIISUE_TYPE:
        return data.get("metadata", {}).get("tissue")
    else:
        return 'AVG'
########NEW FILE########
__FILENAME__ = qc
"""Run Broad's RNA-SeqQC tool and handle reporting of useful summary metrics.
"""

import csv
import os
from random import shuffle
from itertools import ifilter
import shutil
import uuid
import tempfile

# Provide transition period to install via upgrade with conda
try:
    import pandas as pd
    import statsmodels.formula.api as sm
except ImportError:
    pd, sm = None, None

from bcbio import bam
from bcbio import utils
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.utils import safe_makedir, file_exists
from bcbio.distributed.transaction import file_transaction


class RNASeQCRunner(object):
    """
    Runs the Broad's RNA-SeQC tool:
    https://confluence.broadinstitute.org/display/CGATools/RNA-SeQC

    """
    def __init__(self, rnaseqc_path, bwa_path=None, jvm_opts=None):
        self._jvm_opts = " ".join(jvm_opts) if jvm_opts else "-Xms2g -Xmx4g"
        self._bwa_path = bwa_path if bwa_path else "bwa"
        self._rnaseqc_path = rnaseqc_path
        self._base_cmd = ("java -jar {jvm_opts} {rnaseqc_path} -n 1000 -s "
                          "{sample_file} -t {gtf_file} "
                          "-r {ref_file} -o {out_dir} -ttype 2 ")

    def run(self, sample_file, ref_file, rna_file, gtf_file, out_dir,
            single_end=False):
        if single_end:
            self._base_cmd += " -singleEnd"
        cmd = self._base_cmd.format(rnaseqc_path=self._rnaseqc_path,
                                    bwa_path=self._bwa_path,
                                    jvm_opts=self._jvm_opts, **locals())
        do.run(cmd, "RNASeqQC on %s." % sample_file, None)


def rnaseqc_runner_from_config(config):
    """
    get a runner for Broad's RNA-SeQC tool using a bcbio-nextgen config dict to
    configure it
    """
    resources = config_utils.get_resources("rnaseqc", config)
    jvm_opts = resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"])
    bwa_path = config_utils.get_program("bwa", config)
    rnaseqc_dir = config_utils.get_program("rnaseqc", config, "dir")
    rnaseqc_path = config_utils.get_jar("RNA-SeQC", rnaseqc_dir)
    return RNASeQCRunner(rnaseqc_path, bwa_path, jvm_opts)


def sample_summary(bam_file, data, out_dir):
    """Run RNA-SeQC on a single RNAseq sample, writing to specified output directory.
    """
    metrics_file = os.path.join(out_dir, "metrics.tsv")
    if not file_exists(metrics_file):
        with file_transaction(out_dir) as tx_out_dir:
            config = data["config"]
            ref_file = data["sam_ref"]
            genome_dir = os.path.dirname(os.path.dirname(ref_file))
            gtf_file = config_utils.get_transcript_gtf(genome_dir)
            sample_file = os.path.join(safe_makedir(tx_out_dir), "sample_file.txt")
            _write_sample_id_file(data, bam_file, sample_file)
            runner = rnaseqc_runner_from_config(config)
            rna_file = config_utils.get_rRNA_sequence(genome_dir)
            bam.index(bam_file, config)
            single_end = not bam.is_paired(bam_file)
            runner.run(sample_file, ref_file, rna_file, gtf_file, tx_out_dir, single_end)
            # we don't need this large directory for just the report
            shutil.rmtree(os.path.join(tx_out_dir, data["description"]))
    return _parse_rnaseqc_metrics(metrics_file, data["name"][-1])

def _write_sample_id_file(data, bam_file, out_file):
    HEADER = "\t".join(["Sample ID", "Bam File", "Notes"]) + "\n"
    sample_ids = ["\t".join([data["description"], bam_file, data["description"]])]
    with open(out_file, "w") as out_handle:
        out_handle.write(HEADER)
        for sample_id in sample_ids:
            out_handle.write(sample_id + "\n")
    return out_file

# ## Parsing

def _parse_rnaseqc_metrics(metrics_file, sample_name):
    """Parse RNA-SeQC tab delimited metrics file.
    """
    out = {}
    want = set(["Genes Detected", "Transcripts Detected",
                "Mean Per Base Cov.", "Fragment Length Mean",
                "Exonic Rate", "Intergenic Rate", "Intronic Rate",
                "Mapped", "Mapping Rate", "Duplication Rate of Mapped",
                "rRNA", "rRNA rate"])
    with open(metrics_file) as in_handle:
        reader = csv.reader(in_handle, dialect="excel-tab")
        header = reader.next()
        for metrics in reader:
            if metrics[1] == sample_name:
                for name, val in zip(header, metrics):
                    if name in want:
                        out[name] = val
    return out


def starts_by_depth(bam_file, config, sample_size=None):
    """
    Return a set of x, y points where x is the number of reads sequenced and
    y is the number of unique start sites identified
    If sample size < total reads in a file the file will be downsampled.
    """
    binsize = (bam.count(bam_file, config) / 100) + 1
    seen_starts = set()
    counted = 0
    num_reads = []
    starts = []
    buffer = []
    with bam.open_samfile(bam_file) as samfile:
        # unmapped reads should not be counted
        filtered = ifilter(lambda x: not x.is_unmapped, samfile)
        def read_parser(read):
            return ":".join([str(read.tid), str(read.pos)])
        # if no sample size is set, use the whole file
        if not sample_size:
            samples = map(read_parser, filtered)
        else:
            samples = utils.reservoir_sample(filtered, sample_size, read_parser)
        shuffle(samples)
        for read in samples:
            counted += 1
            buffer.append(read)
            if counted % binsize == 0:
                seen_starts.update(buffer)
                buffer = []
                num_reads.append(counted)
                starts.append(len(seen_starts))
        seen_starts.update(buffer)
        num_reads.append(counted)
        starts.append(len(seen_starts))
    return pd.DataFrame({"reads": num_reads, "starts": starts})


def estimate_library_complexity(df, algorithm="RNA-seq"):
    """
    estimate library complexity from the number of reads vs.
    number of unique start sites. returns "NA" if there are
    not enough data points to fit the line
    """
    DEFAULT_CUTOFFS = {"RNA-seq": (0.25, 0.40)}
    cutoffs = DEFAULT_CUTOFFS[algorithm]
    if len(df) < 5:
        return {"unique_starts_per_read": 'nan',
                "complexity": "NA"}
    model = sm.ols(formula="starts ~ reads", data=df)
    fitted = model.fit()
    slope = fitted.params["reads"]
    if slope <= cutoffs[0]:
        complexity = "LOW"
    elif slope <= cutoffs[1]:
        complexity = "MEDIUM"
    else:
        complexity = "HIGH"

    # for now don't return the complexity flag
    return {"Unique Starts Per Read": float(slope)}
    # return {"unique_start_per_read": float(slope),
    #         "complexity": complexity}


########NEW FILE########
__FILENAME__ = background
"""Provide asynchronous background running of subprocesses.

Modified from: https://github.com/vukasin/tornado-subprocess

- Do not store all stdout/stderr, instead print out to avoid filling up buffer

Copyright (c) 2012, Vukasin Toroman <vukasin@toroman.name>
"""

import subprocess
import tornado.ioloop
import time
import fcntl
import functools
import os


class GenericSubprocess (object):
    def __init__ ( self, timeout=-1, **popen_args ):
        self.args = dict()
        self.args["stdout"] = subprocess.PIPE
        self.args["stderr"] = subprocess.PIPE
        self.args["close_fds"] = True
        self.args.update(popen_args)
        self.ioloop = None
        self.expiration = None
        self.pipe = None
        self.timeout = timeout
        self.streams = []
        self.has_timed_out = False

    def start(self):
        """Spawn the task.

        Throws RuntimeError if the task was already started."""
        if not self.pipe is None:
            raise RuntimeError("Cannot start task twice")

        self.ioloop = tornado.ioloop.IOLoop.instance()
        if self.timeout > 0:
            self.expiration = self.ioloop.add_timeout( time.time() + self.timeout, self.on_timeout )
        self.pipe = subprocess.Popen(**self.args)

        self.streams = [ (self.pipe.stdout.fileno(), []),
                         (self.pipe.stderr.fileno(), []) ]
        for fd, d in self.streams:
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)| os.O_NDELAY
            fcntl.fcntl( fd, fcntl.F_SETFL, flags)
            self.ioloop.add_handler( fd,
                                     self.stat,
                                     self.ioloop.READ|self.ioloop.ERROR)

    def on_timeout(self):
        self.has_timed_out = True
        self.cancel()

    def cancel (self ) :
        """Cancel task execution

        Sends SIGKILL to the child process."""
        try:
            self.pipe.kill()
        except:
            pass

    def stat( self, *args ):
        '''Check process completion and consume pending I/O data'''
        self.pipe.poll()
        if not self.pipe.returncode is None:
            '''cleanup handlers and timeouts'''
            if not self.expiration is None:
                self.ioloop.remove_timeout(self.expiration)
            for fd, dest in  self.streams:
                self.ioloop.remove_handler(fd)
            '''schedulle callback (first try to read all pending data)'''
            self.ioloop.add_callback(self.on_finish)
        for fd, dest in  self.streams:
            while True:
                try:
                    data = os.read(fd, 4096)
                    if len(data) == 0:
                        break
                    print data.rstrip()
                except:
                    break
    @property
    def stdout(self):
        return self.get_output(0)

    @property
    def stderr(self):
        return self.get_output(1)

    @property
    def status(self):
        return self.pipe.returncode

    def get_output(self, index ):
        return "".join(self.streams[index][1])

    def on_finish(self):
        raise NotImplemented()


class Subprocess (GenericSubprocess):
    """Create new instance

    Arguments:
        callback: method to be called after completion. This method should take 3 arguments: statuscode(int), stdout(str), stderr(str), has_timed_out(boolean)
        timeout: wall time allocated for the process to complete. After this expires Task.cancel is called. A negative timeout value means no limit is set

    The task is not started until start is called. The process will then be spawned using subprocess.Popen(**popen_args). The stdout and stderr are always set to subprocess.PIPE.
    """

    def __init__ ( self, callback, *args, **kwargs):
        """Create new instance

        Arguments:
            callback: method to be called after completion. This method should take 3 arguments: statuscode(int), stdout(str), stderr(str), has_timed_out(boolean)
            timeout: wall time allocated for the process to complete. After this expires Task.cancel is called. A negative timeout value means no limit is set

        The task is not started until start is called. The process will then be spawned using subprocess.Popen(**popen_args). The stdout and stderr are always set to subprocess.PIPE.
        """
        self.callback = callback
        self.done_callback = False
        GenericSubprocess.__init__(self, *args, **kwargs)

    def on_finish(self):
        if not self.done_callback:
            self.done_callback = True
            '''prevent calling callback twice'''
            self.ioloop.add_callback(functools.partial(self.callback, self.status, self.stdout, self.stderr, self.has_timed_out))

########NEW FILE########
__FILENAME__ = main
"""Top level functionality for running a bcbio-nextgen web server allowing remote jobs.
"""
import tornado.web
import tornado.ioloop

from bcbio.server import run

def start(args):
    """Run server with provided command line arguments.
    """
    application = tornado.web.Application([(r"/run", run.get_handler(args)),
                                           (r"/status", run.StatusHandler)])
    application.runmonitor = RunMonitor()
    application.listen(args.port)
    tornado.ioloop.IOLoop.instance().start()

class RunMonitor:
    """Track current runs and provide status.
    """
    def __init__(self):
        self._running = {}

    def set_status(self, run_id, status):
        self._running[run_id] = status

    def get_status(self, run_id):
        return self._running.get(run_id, "not-running")

def add_subparser(subparsers):
    """Add command line arguments as server subparser.
    """
    parser = subparsers.add_parser("server", help="Run a bcbio-nextgen server allowing remote job execution.")
    parser.add_argument("-c", "--config", help=("Global YAML configuration file specifying system details."
                                                "Defaults to installed bcbio_system.yaml"))
    parser.add_argument("-p", "--port", help="Port to listen on (default 8080)",
                        default=8080, type=int)
    parser.add_argument("-n", "--cores", help="Cores to use when processing locally when not requested (default 1)",
                        default=1, type=int)
    parser.add_argument("-d", "--biodata_dir", help="Directory with biological data",
                        default="/mnt/biodata", type=str)
    return parser

########NEW FILE########
__FILENAME__ = run
"""Provide ability to run bcbio-nextgen workflows.
"""
import collections
import os
import StringIO
import sys
import uuid

import tornado.gen
import tornado.web
import yaml

from bcbio import utils
from bcbio.distributed import clargs
from bcbio.server import background

def run_bcbio_nextgen(**kwargs):
    callback = kwargs.pop("callback", None)
    app = kwargs.pop("app")
    args = [x for x in [kwargs["config_file"], kwargs["fc_dir"], kwargs["run_info_yaml"]] if x]
    run_id = str(uuid.uuid1())
    def set_done(status, stdout, stderr, has_timed_out):
        app.runmonitor.set_status(run_id, "finished" if status == 0 else "failed")
    if utils.get_in(kwargs, ("parallel", "type")) == "local":
        _run_local(kwargs["workdir"], args, utils.get_in(kwargs, ("parallel", "cores")), set_done)
    else:
        # XXX Need to work on ways to prepare batch scripts for bcbio submission
        # when analysis server talks to an HPC cluster
        raise ValueError("Do not yet support automated execution of this parallel config: %s" % parallel)
    app.runmonitor.set_status(run_id, "running")
    if callback:
        callback(run_id)
    else:
        return run_id

def _run_local(workdir, args, cores, callback):
    cmd = [os.path.join(os.path.dirname(sys.executable), "bcbio_nextgen.py")] + args + \
          ["-n", cores]
    with utils.chdir(workdir):
        p = background.Subprocess(callback, timeout=-1, args=[str(x) for x in cmd])
        p.start()

def _rargs_to_parallel_args(rargs, args):
    Args = collections.namedtuple("Args", "numcores scheduler queue resources timeout retries tag")
    return Args(int(rargs.get("numcores", args.cores)), rargs.get("scheduler"),
                rargs.get("queue"), rargs.get("resources", ""),
                int(rargs.get("timeout", 15)), rargs.get("retries"),
                rargs.get("tag"))

def get_handler(args):
    class RunHandler(tornado.web.RequestHandler):
        @tornado.web.asynchronous
        @tornado.gen.coroutine
        def get(self):
            rargs = yaml.safe_load(StringIO.StringIO(str(self.get_argument("args", "{}"))))
            system_config = args.config or "bcbio_system.yaml"
            if "system_config" in rargs:
                system_config = os.path.join(rargs["work_dir"], "web-system_config.yaml")
                with open(system_config, "w") as out_handle:
                    yaml.safe_dump(rargs["system_config"], out_handle, default_flow_style=False, allow_unicode=False)
            if "sample_config" in rargs:
                sample_config = os.path.join(rargs["work_dir"], "web-sample_config.yaml")
                with open(sample_config, "w") as out_handle:
                    yaml.safe_dump(rargs["sample_config"], out_handle, default_flow_style=False, allow_unicode=False)
            else:
                sample_config = rargs.get("run_config")
            kwargs = {"workdir": rargs["work_dir"],
                      "config_file": system_config,
                      "run_info_yaml": sample_config,
                      "fc_dir": rargs.get("fc_dir"),
                      "parallel": clargs.to_parallel(_rargs_to_parallel_args(rargs, args)),
                      "app": self.application}
            run_id = yield tornado.gen.Task(run_bcbio_nextgen, **kwargs)
            self.write(run_id)
            self.finish()
    return RunHandler

class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        run_id = self.get_argument("run_id", None)
        if run_id is None:
            status = "server-up"
        else:
            status = self.application.runmonitor.get_status(run_id)
        self.write(status)
        self.finish()

########NEW FILE########
__FILENAME__ = cn_mops
"""Copy number detection using read counts, with cn.mops.

http://www.bioconductor.org/packages/release/bioc/html/cn.mops.html
"""
from contextlib import closing
import os
import shutil
import subprocess

import pysam
import toolz as tz

from bcbio import bam, install, utils
from bcbio.distributed.multi import run_multicore, zeromq_aware_logging
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils, shared
from bcbio.provenance import do
from bcbio.variation import vcfutils

def run(items, background=None):
    """Detect copy number variations from batched set of samples using cn.mops.
    """
    if not background: background = []
    names = [tz.get_in(["rgnames", "sample"], x) for x in items + background]
    work_bams = [x["align_bam"] for x in items + background]
    if len(items + background) < 2:
        raise ValueError("cn.mops only works on batches with multiple samples")
    data = items[0]
    work_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "structural", names[0],
                                               "cn_mops"))
    parallel = {"type": "local", "cores": data["config"]["algorithm"].get("num_cores", 1),
                "progs": ["delly"]}
    with closing(pysam.Samfile(work_bams[0], "rb")) as pysam_work_bam:
        chroms = [None] if _get_regional_bed_file(items[0]) else pysam_work_bam.references
        out_files = run_multicore(_run_on_chrom, [(chrom, work_bams, names, work_dir, items)
                                                  for chrom in chroms],
                                  data["config"], parallel)
    out_file = _combine_out_files(out_files, work_bams[0], work_dir)
    out = []
    for data in items:
        if "sv" not in data:
            data["sv"] = []
        data["sv"].append({"variantcaller": "cn_mops",
                           "vrn_file": _prep_sample_cnvs(out_file, data)})
        out.append(data)
    return out

def _combine_out_files(chr_files, base_bam, work_dir):
    """Concatenate all CNV calls into a single file.
    """
    out_file = os.path.join(work_dir, "%s-cnv.bed" % (os.path.splitext(os.path.basename(base_bam))[0]))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                for chr_file in chr_files:
                    with open(chr_file) as in_handle:
                        is_empty = in_handle.readline().startswith("track name=empty")
                    if not is_empty:
                        with open(chr_file) as in_handle:
                            shutil.copyfileobj(in_handle, out_handle)
    return out_file

def _prep_sample_cnvs(cnv_file, data):
    """Convert a multiple sample CNV file into a single BED file for a sample.

    Handles matching and fixing names where R converts numerical IDs (1234) into
    strings by adding an X (X1234).
    """
    import pybedtools
    sample_name = tz.get_in(["rgnames", "sample"], data)
    def matches_sample_name(feat):
        return feat.name == sample_name or feat.name == "X%s" % sample_name
    def update_sample_name(feat):
        feat.name = sample_name
        return feat
    sample_file = os.path.join(os.path.dirname(cnv_file), "%s-cnv.bed" % sample_name)
    if not utils.file_exists(sample_file):
        with file_transaction(sample_file) as tx_out_file:
            with shared.bedtools_tmpdir(data):
                pybedtools.BedTool(cnv_file).filter(matches_sample_name).each(update_sample_name).saveas(tx_out_file)
    return sample_file

@utils.map_wrap
@zeromq_aware_logging
def _run_on_chrom(chrom, work_bams, names, work_dir, items):
    """Run cn.mops on work BAMs for a specific chromosome.
    """
    local_sitelib = os.path.join(install.get_defaults().get("tooldir", "/usr/local"),
                                 "lib", "R", "site-library")
    out_file = os.path.join(work_dir, "%s-%s-cnv.bed" % (os.path.splitext(os.path.basename(work_bams[0]))[0],
                                                         chrom if chrom else "all"))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            rcode = "%s-run.R" % os.path.splitext(out_file)[0]
            with open(rcode, "w") as out_handle:
                out_handle.write(_script.format(prep_str=_prep_load_script(work_bams, names, chrom, items),
                                                out_file=tx_out_file,
                                                local_sitelib=local_sitelib))
            rscript = config_utils.get_program("Rscript", items[0]["config"])
            try:
                do.run([rscript, rcode], "cn.mops CNV detection", items[0], log_error=False)
            except subprocess.CalledProcessError, msg:
                # cn.mops errors out if no CNVs found. Just write an empty file.
                if _allowed_cnmops_errorstates(str(msg)):
                    with open(tx_out_file, "w") as out_handle:
                        out_handle.write('track name=empty description="No CNVs found"\n')
                else:
                    logger.exception()
                    raise
    return [out_file]

def _allowed_cnmops_errorstates(msg):
    return (msg.find("No CNV regions in result object. Rerun cn.mops with different parameters") >= 0
            or msg.find("Normalization might not be applicable for this small number of segments") >= 0
            or msg.find("Error in if (is.finite(mv2m)) { : argument is of length zero") >= 0)

def _prep_load_script(work_bams, names, chrom, items):
    if not chrom: chrom = ""
    pairmode = "paired" if bam.is_paired(work_bams[0]) else "unpaired"
    if len(items) == 2 and vcfutils.get_paired_phenotype(items[0]):
        load_script = _paired_load_script
    else:
        load_script = _population_load_script
    return load_script(work_bams, names, chrom, pairmode, items)

def _get_regional_bed_file(data):
    """If we are running a non-genome analysis, pull the regional file for analysis.
    """
    bed_file = data["config"]["algorithm"].get("variant_regions", None)
    is_genome = data["config"]["algorithm"].get("coverage_interval", "exome").lower() in ["genome"]
    if bed_file and utils.file_exists(bed_file) and not is_genome:
        return bed_file

def _population_load_script(work_bams, names, chrom, pairmode, items):
    """Prepare BAMs for assessing CNVs in a population.
    """
    bed_file = _get_regional_bed_file(items[0])
    if bed_file:
        return _population_prep_targeted.format(bam_file_str=",".join(work_bams), names_str=",".join(names),
                                                chrom=chrom, num_cores=0, pairmode=pairmode, bed_file=bed_file)
    else:
        return _population_prep.format(bam_file_str=",".join(work_bams), names_str=",".join(names),
                                       chrom=chrom, num_cores=0, pairmode=pairmode)

def _paired_load_script(work_bams, names, chrom, pairmode, items):
    """Prepare BAMs for assessing CNVs in a paired tumor/normal setup.
    """
    paired = vcfutils.get_paired_bams(work_bams, items)
    bed_file = _get_regional_bed_file(items[0])
    if bed_file:
        return _paired_prep_targeted.format(case_file=paired.tumor_bam, case_name=paired.tumor_name,
                                            ctrl_file=paired.normal_bam, ctrl_name=paired.normal_name,
                                            num_cores=0, chrom=chrom, pairmode=pairmode, bed_file=bed_file)
    else:
        return _paired_prep.format(case_file=paired.tumor_bam, case_name=paired.tumor_name,
                                   ctrl_file=paired.normal_bam, ctrl_name=paired.normal_name,
                                   num_cores=0, chrom=chrom, pairmode=pairmode)

_script = """
.libPaths(c("{local_sitelib}"))
library(cn.mops)
library(rtracklayer)

{prep_str}

calc_cnvs <- cnvs(cnv_out)
strcn_to_cn <- function(x) {{
  as.numeric(substring(x, 3, 20))}}
calc_cnvs$score <- strcn_to_cn(calc_cnvs$CN)
calc_cnvs$name <- calc_cnvs$sampleName
export.bed(calc_cnvs, "{out_file}")
"""

_population_prep = """
bam_files <- strsplit("{bam_file_str}", ",")[[1]]
sample_names <- strsplit("{names_str}", ",")[[1]]
count_drs <- getReadCountsFromBAM(bam_files, sampleNames=sample_names, mode="{pairmode}",
                                  refSeqName="{chrom}", parallel={num_cores})
prep_counts <- cn.mops(count_drs, parallel={num_cores})
cnv_out <- calcIntegerCopyNumbers(prep_counts)
"""

_paired_prep = """
case_count <- getReadCountsFromBAM(c("{case_file}"), sampleNames=c("{case_name}"), mode="{pairmode}",
                                   refSeqName="{chrom}", parallel={num_cores})
ctrl_count <- getReadCountsFromBAM(c("{ctrl_file}"), sampleNames=c("{ctrl_name}"), mode="{pairmode}",
                                   refSeqName="{chrom}", parallel={num_cores},
                                   WL=width(case_count)[[1]])
prep_counts <- referencecn.mops(case_count, ctrl_count, parallel={num_cores})
cnv_out <- calcFractionalCopyNumbers(prep_counts)
"""

_population_prep_targeted = """
bam_files <- strsplit("{bam_file_str}", ",")[[1]]
sample_names <- strsplit("{names_str}", ",")[[1]]
my_gr <- import.bed(c("{bed_file}"), trackLine=FALSE, asRangedData=FALSE)
if ("{chrom}" != "") my_gr = subset(my_gr, seqnames(my_gr) == "{chrom}")
if (length(my_gr) < 1) stop("No CNV regions in result object. Rerun cn.mops with different parameters!")
count_drs <- getSegmentReadCountsFromBAM(bam_files, sampleNames=sample_names, mode="{pairmode}",
                                         GR=my_gr, parallel={num_cores})
prep_counts <- cn.mops(count_drs, parallel={num_cores})
cnv_out <- calcIntegerCopyNumbers(prep_counts)
"""

_paired_prep_targeted = """
my_gr <- import.bed(c("{bed_file}"), trackLine=FALSE, asRangedData=FALSE)
if ("{chrom}" != "") my_gr = subset(my_gr, seqnames(my_gr) == "{chrom}")
if (length(my_gr) < 1) stop("No CNV regions in result object. Rerun cn.mops with different parameters!")
case_count <- getSegmentReadCountsFromBAM(c("{case_file}"), GR=my_gr,
                                          sampleNames=c("{case_name}"),
                                          mode="{pairmode}", parallel={num_cores})
ctrl_count <- getSegmentReadCountsFromBAM(c("{ctrl_file}"), GR=my_gr,
                                          sampleNames=c("{case_name}"),
                                          mode="{pairmode}", parallel={num_cores})
prep_counts <- referencecn.mops(case_count, ctrl_count, parallel={num_cores})
cnv_out <- calcFractionalCopyNumbers(prep_counts)
"""

########NEW FILE########
__FILENAME__ = delly
"""Structural variant calling with Delly

https://github.com/tobiasrausch/delly
"""
from contextlib import closing
import copy
import itertools
import os
import re
import subprocess

try:
    import pybedtools
except ImportError:
    pybedtools = None
import pysam
import toolz as tz

from bcbio import utils
from bcbio.bam import callable
from bcbio.distributed.multi import run_multicore, zeromq_aware_logging
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import shared
from bcbio.provenance import do
from bcbio.variation import vcfutils, vfilter

def _get_sv_exclude_file(items):
    """Retrieve SV file of regions to exclude.
    """
    sv_bed = utils.get_in(items[0], ("genome_resources", "variation", "sv_repeat"))
    if sv_bed and os.path.exists(sv_bed):
        return sv_bed

def _get_variant_regions(items):
    """Retrieve variant regions defined in any of the input items.
    """
    return filter(lambda x: x is not None,
                  [tz.get_in(("config", "algorithm", "variant_regions"), data)
                   for data in items
                   if tz.get_in(["config", "algorithm", "coverage_interval"], data) != "genome"])

def _has_variant_regions(items, base_file, chrom=None):
    """Determine if we should process this chromosome: needs variant regions defined.
    """
    if chrom:
        all_vrs = _get_variant_regions(items)
        if len(all_vrs) > 0:
            test = shared.subset_variant_regions(tz.first(all_vrs), chrom, base_file, items)
            if test == chrom:
                return False
    return True

def prepare_exclude_file(items, base_file, chrom=None):
    """Prepare a BED file for exclusion, incorporating variant regions and chromosome.

    Excludes locally repetitive regions (if `remove_lcr` is set) and
    centromere regions, both of which contribute to long run times and
    false positive structural variant calls.
    """
    out_file = "%s-exclude.bed" % utils.splitext_plus(base_file)[0]
    all_vrs = _get_variant_regions(items)
    ready_region = (shared.subset_variant_regions(tz.first(all_vrs), chrom, base_file, items)
                    if len(all_vrs) > 0 else chrom)
    with shared.bedtools_tmpdir(items[0]):
        # Get a bedtool for the full region if no variant regions
        if ready_region == chrom:
            want_bedtool = callable.get_ref_bedtool(tz.get_in(["reference", "fasta", "base"], items[0]),
                                                    items[0]["config"], chrom)
            lcr_bed = shared.get_lcr_bed(items)
            if lcr_bed:
                want_bedtool = want_bedtool.subtract(pybedtools.BedTool(lcr_bed))
        else:
            want_bedtool = pybedtools.BedTool(ready_region).saveas()
        sv_exclude_bed = _get_sv_exclude_file(items)
        if sv_exclude_bed and len(want_bedtool) > 0:
            want_bedtool = want_bedtool.subtract(sv_exclude_bed).saveas()
        if not utils.file_exists(out_file) and not utils.file_exists(out_file + ".gz"):
            with file_transaction(out_file) as tx_out_file:
                full_bedtool = callable.get_ref_bedtool(tz.get_in(["reference", "fasta", "base"], items[0]),
                                                        items[0]["config"])
                if len(want_bedtool) > 0:
                    full_bedtool.subtract(want_bedtool).saveas(tx_out_file)
                else:
                    full_bedtool.saveas(tx_out_file)
    return out_file

@utils.map_wrap
@zeromq_aware_logging
def _run_delly(bam_files, chrom, sv_type, ref_file, work_dir, items):
    """Run delly, calling structural variations for the specified type.
    """
    out_file = os.path.join(work_dir, "%s-svs%s-%s.vcf"
                            % (os.path.splitext(os.path.basename(bam_files[0]))[0], sv_type, chrom))
    cores = min(utils.get_in(items[0], ("config", "algorithm", "num_cores"), 1),
                len(bam_files))
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            if not _has_variant_regions(items, out_file, chrom):
                vcfutils.write_empty_vcf(out_file)
            else:
                exclude = ["-x", prepare_exclude_file(items, out_file, chrom)]
                cmd = ["delly", "-t", sv_type, "-g", ref_file, "-o", tx_out_file] + exclude + bam_files
                multi_cmd = "export OMP_NUM_THREADS=%s && " % cores
                try:
                    do.run(multi_cmd + " ".join(cmd), "delly structural variant")
                except subprocess.CalledProcessError, msg:
                    # delly returns an error exit code if there are no variants
                    if "No structural variants found" in str(msg):
                        vcfutils.write_empty_vcf(out_file)
                    else:
                        raise
    return [vcfutils.bgzip_and_index(_clean_delly_output(out_file, items), items[0]["config"])]

def _clean_delly_output(in_file, items):
    """Clean delly output, fixing sample names and removing problem GL specifications from output.

    GATK does not like missing GLs like '.,.,.'. This converts them to the recognized '.'
    """
    pat = re.compile(r"\.,\.,\.")
    out_file = "%s-clean.vcf" % utils.splitext_plus(in_file)[0]
    if not utils.file_exists(out_file) and not utils.file_exists(out_file + ".gz"):
        with file_transaction(out_file) as tx_out_file:
            with open(in_file) as in_handle:
                with open(tx_out_file, "w") as out_handle:
                    for line in in_handle:
                        if line.startswith("#"):
                            if line.startswith("#CHROM"):
                                line = _fix_sample_names(line, items)
                        else:
                            line = pat.sub(".", line)
                        out_handle.write(line)
    return out_file

def _fix_sample_names(line, items):
    """Substitute Delly output sample names (filenames) with actual sample names.
    """
    names = [tz.get_in(["rgnames", "sample"], x) for x in items]
    parts = line.split("\t")
    # If we're not empty and actually have genotype information
    if "FORMAT" in parts:
        format_i = parts.index("FORMAT") + 1
        assert len(parts[format_i:]) == len(names), (parts[format_i:], names)
        return "\t".join(parts[:format_i] + names) + "\n"
    else:
        return line

def run(items):
    """Perform detection of structural variations with delly.

    Performs post-call filtering with a custom filter tuned based
    on NA12878 Moleculo and PacBio data, using calls prepared by
    @ryanlayer and @cc2qe

    Filters using the high quality variant pairs (DV) compared with
    high quality reference pairs (DR).
    """
    work_dir = utils.safe_makedir(os.path.join(items[0]["dirs"]["work"], "structural",
                                               items[0]["name"][-1], "delly"))
    work_bams = [data["align_bam"] for data in items]
    ref_file = utils.get_in(items[0], ("reference", "fasta", "base"))
    # Add core request for delly
    config = copy.deepcopy(items[0]["config"])
    delly_config = utils.get_in(config, ("resources", "delly"), {})
    delly_config["cores"] = len(items)
    config["resources"]["delly"] = delly_config
    parallel = {"type": "local", "cores": config["algorithm"].get("num_cores", 1),
                "progs": ["delly"]}
    sv_types = ["DEL", "DUP", "INV"]  # "TRA" has invalid VCF END specifications that GATK doesn't like
    with closing(pysam.Samfile(work_bams[0], "rb")) as pysam_work_bam:
        bytype_vcfs = run_multicore(_run_delly, [(work_bams, chrom, sv_type, ref_file, work_dir, items)
                                                 for (chrom, sv_type)
                                                 in itertools.product(pysam_work_bam.references, sv_types)],
                                    config, parallel)
    out_file = "%s.vcf.gz" % os.path.commonprefix(bytype_vcfs)
    combo_vcf = vcfutils.combine_variant_files(bytype_vcfs, out_file, ref_file, items[0]["config"])
    delly_vcf = vfilter.genotype_filter(combo_vcf, 'DV < 4 || (DV / (DV + DR)) < 0.35', data,
                                        "DVSupport")
    out = []
    for data in items:
        if "sv" not in data:
            data["sv"] = []
        base, ext = utils.splitext_plus(delly_vcf)
        sample = tz.get_in(["rgnames", "sample"], data)
        delly_sample_vcf = "%s-%s%s" % (base, sample, ext)
        data["sv"].append({"variantcaller": "delly",
                           "vrn_file": vcfutils.select_sample(delly_vcf, sample, delly_sample_vcf, data["config"])})
        out.append(data)
    return out

########NEW FILE########
__FILENAME__ = ensemble
"""Combine multiple structural variation callers into single output file.

Takes a simple union approach for reporting the final set of calls, reporting
the evidence from each input.
"""
import fileinput
import os

try:
    import pybedtools
except ImportError:
    pybedtools = None
import toolz as tz
import vcf

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import shared

# ## Conversions to simplified BED files

def _vcf_to_bed(in_file, caller, out_file):
    if in_file and in_file.endswith((".vcf", "vcf.gz")):
        with utils.open_gzipsafe(in_file) as in_handle:
            with open(out_file, "w") as out_handle:
                for rec in vcf.Reader(in_handle, in_file):
                    if not rec.FILTER:
                        if (rec.samples[0].gt_type and
                              not (hasattr(rec.samples[0].data, "FT") and rec.samples[0].data.FT)):
                            out_handle.write("\t".join([rec.CHROM, str(rec.start - 1),
                                                        str(rec.INFO.get("END", rec.start)),
                                                        "%s_%s" % (_get_svtype(rec), caller)])
                                             + "\n")

def _get_svtype(rec):
    try:
        return rec.INFO["SVTYPE"]
    except KeyError:
        return "-".join(str(x).replace("<", "").replace(">", "") for x in rec.ALT)

def _cnvbed_to_bed(in_file, caller, out_file):
    """Convert cn_mops CNV based bed files into flattened BED
    """

    with open(out_file, "w") as out_handle:
        for feat in pybedtools.BedTool(in_file):
            out_handle.write("\t".join([feat.chrom, str(feat.start), str(feat.end),
                                        "cnv%s_%s" % (feat.score, caller)])
                             + "\n")

CALLER_TO_BED = {"lumpy": _vcf_to_bed,
                 "delly": _vcf_to_bed,
                 "cn_mops": _cnvbed_to_bed}

def _create_bed(call, base_file):
    """Create a simplified BED file from caller specific input.
    """
    out_file = "%s-%s.bed" % (utils.splitext_plus(base_file)[0], call["variantcaller"])
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            convert_fn = CALLER_TO_BED.get(call["variantcaller"])
            if convert_fn:
                convert_fn(call["vrn_file"], call["variantcaller"], tx_out_file)

    if utils.file_exists(out_file):
        return out_file

# ## Top level

def summarize(calls, data):
    """Summarize results from multiple callers into a single flattened BED file.
    """
    sample = tz.get_in(["rgnames", "sample"], data)
    work_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "structural",
                                               sample, "ensemble"))
    out_file = os.path.join(work_dir, "%s-ensemble.bed" % sample)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with shared.bedtools_tmpdir(data):
                input_beds = filter(lambda x: x is not None,
                                    [_create_bed(c, out_file) for c in calls])
                if len(input_beds) > 0:
                    all_file = "%s-all.bed" % utils.splitext_plus(tx_out_file)[0]
                    with open(all_file, "w") as out_handle:
                        for line in fileinput.input(input_beds):
                            out_handle.write(line)
                    pybedtools.BedTool(all_file).sort(stream=True).merge(nms=True).saveas(tx_out_file)
    if utils.file_exists(out_file):
        calls.append({"variantcaller": "ensemble",
                      "vrn_file": out_file})
    return calls

########NEW FILE########
__FILENAME__ = hydra
"""Use Hydra to detect structural variation using discordant read pairs.

Hydra: http://code.google.com/p/hydra-sv/

Pipeline: http://code.google.com/p/hydra-sv/wiki/TypicalWorkflow
"""
import os
import copy
import collections
import subprocess
from contextlib import closing

import numpy
import pysam

from bcbio import utils, broad
from bcbio.pipeline.alignment import align_to_sort_bam
from bcbio.pipeline import lane
from bcbio.distributed.transaction import file_transaction

## Prepare alignments to identify discordant pair mappings

def select_unaligned_read_pairs(in_bam, extra, out_dir, config):
    """Retrieve unaligned read pairs from input alignment BAM, as two fastq files.
    """
    runner = broad.runner_from_config(config)
    base, ext = os.path.splitext(os.path.basename(in_bam))
    nomap_bam = os.path.join(out_dir, "{}-{}{}".format(base, extra, ext))
    if not utils.file_exists(nomap_bam):
        with file_transaction(nomap_bam) as tx_out:
            runner.run("FilterSamReads", [("INPUT", in_bam),
                                          ("OUTPUT", tx_out),
                                          ("EXCLUDE_ALIGNED", "true"),
                                          ("WRITE_READS_FILES", "false"),
                                          ("SORT_ORDER", "queryname")])
    has_reads = False
    with closing(pysam.Samfile(nomap_bam, "rb")) as in_pysam:
        for read in in_pysam:
            if read.is_paired:
                has_reads = True
                break
    if has_reads:
        out_fq1, out_fq2 = ["{}-{}.fq".format(os.path.splitext(nomap_bam)[0], i) for i in [1, 2]]
        runner.run_fn("picard_bam_to_fastq", nomap_bam, out_fq1, out_fq2)
        return out_fq1, out_fq2
    else:
        return None, None

def remove_nopairs(in_bam, out_dir, config):
    """Remove any reads without both pairs present in the file.
    """
    runner = broad.runner_from_config(config)
    out_bam = os.path.join(out_dir, apply("{}-safepair{}".format,
                                          os.path.splitext(os.path.basename(in_bam))))
    if not utils.file_exists(out_bam):
        read_counts = collections.defaultdict(int)
        with closing(pysam.Samfile(in_bam, "rb")) as in_pysam:
            for read in in_pysam:
                if read.is_paired:
                    read_counts[read.qname] += 1
        with closing(pysam.Samfile(in_bam, "rb")) as in_pysam:
            with file_transaction(out_bam) as tx_out_bam:
                with closing(pysam.Samfile(tx_out_bam, "wb", template=in_pysam)) as out_pysam:
                    for read in in_pysam:
                        if read_counts[read.qname] == 2:
                            out_pysam.write(read)
    return runner.run_fn("picard_sort", out_bam, "queryname")

def insert_size_stats(dists):
    """Calcualtes mean/median and MAD from distances, avoiding outliers.

    MAD is the Median Absolute Deviation: http://en.wikipedia.org/wiki/Median_absolute_deviation
    """
    med = numpy.median(dists)
    filter_dists = filter(lambda x: x < med + 10 * med, dists)
    median = numpy.median(filter_dists)
    return {"mean": numpy.mean(filter_dists), "std": numpy.std(filter_dists),
            "median": median,
            "mad": numpy.median([abs(x - median) for x in filter_dists])}

def calc_paired_insert_stats(in_bam):
    """Retrieve statistics for paired end read insert distances.
    """
    dists = []
    with closing(pysam.Samfile(in_bam, "rb")) as in_pysam:
        for read in in_pysam:
            if read.is_proper_pair and read.is_read1:
                dists.append(abs(read.isize))
    return insert_size_stats(dists)

def tiered_alignment(in_bam, tier_num, multi_mappers, extra_args,
                     genome_build, pair_stats,
                     work_dir, dirs, config):
    """Perform the alignment of non-mapped reads from previous tier.
    """
    nomap_fq1, nomap_fq2 = select_unaligned_read_pairs(in_bam, "tier{}".format(tier_num),
                                                       work_dir, config)
    if nomap_fq1 is not None:
        base_name = "{}-tier{}out".format(os.path.splitext(os.path.basename(in_bam))[0],
                                          tier_num)
        config = copy.deepcopy(config)
        dirs = copy.deepcopy(dirs)
        config["algorithm"]["bam_sort"] = "queryname"
        config["algorithm"]["multiple_mappers"] = multi_mappers
        config["algorithm"]["extra_align_args"] = ["-i", int(pair_stats["mean"]),
                                               int(pair_stats["std"])] + extra_args
        out_bam, ref_file = align_to_sort_bam(nomap_fq1, nomap_fq2,
                                              lane.rg_names(base_name, base_name, config),
                                              genome_build, "novoalign",
                                              dirs, config,
                                              dir_ext=os.path.join("hydra", os.path.split(nomap_fq1)[0]))
        return out_bam
    else:
        return None

## Run hydra to identify structural variation breakpoints

@utils.memoize_outfile(ext=".bed")
def convert_bam_to_bed(in_bam, out_file):
    """Convert BAM to bed file using BEDTools.
    """
    with file_transaction(out_file) as tx_out_file:
        with open(tx_out_file, "w") as out_handle:
            subprocess.check_call(["bamToBed", "-i", in_bam, "-tag", "NM"],
                                  stdout=out_handle)
    return out_file

@utils.memoize_outfile(ext="-pair.bed")
def pair_discordants(in_bed, pair_stats, out_file):
    with file_transaction(out_file) as tx_out_file:
        with open(tx_out_file, "w") as out_handle:
            subprocess.check_call(["pairDiscordants.py", "-i", in_bed,
                                   "-m", "hydra",
                                   "-z", str(int(pair_stats["median"]) +
                                             10 * int(pair_stats["mad"]))],
                                  stdout=out_handle)
    return out_file

@utils.memoize_outfile(ext="-dedup.bed")
def dedup_discordants(in_bed, out_file):
    with file_transaction(out_file) as tx_out_file:
        with open(tx_out_file, "w") as out_handle:
            subprocess.check_call(["dedupDiscordants.py", "-i", in_bed, "-s", "3"],
                                  stdout=out_handle)
    return out_file

def run_hydra(in_bed, pair_stats):
    base_out = "{}-hydra.breaks".format(os.path.splitext(in_bed)[0])
    final_file = "{}.final".format(base_out)
    if not utils.file_exists(final_file):
        subprocess.check_call(["hydra", "-in", in_bed, "-out", base_out,
                               "-ms", "1", "-li",
                               "-mld", str(int(pair_stats["mad"]) * 10),
                               "-mno", str(int(pair_stats["median"]) +
                                           20 * int(pair_stats["mad"]))])
    return final_file

def hydra_breakpoints(in_bam, pair_stats):
    """Detect structural variation breakpoints with hydra.
    """
    in_bed = convert_bam_to_bed(in_bam)
    if os.path.getsize(in_bed) > 0:
        pair_bed = pair_discordants(in_bed, pair_stats)
        dedup_bed = dedup_discordants(pair_bed)
        return run_hydra(dedup_bed, pair_stats)
    else:
        return None

## Top level organizational code

def detect_sv(align_bam, genome_build, dirs, config):
    """Detect structural variation from discordant aligned pairs.
    """
    work_dir = utils.safe_makedir(os.path.join(dirs["work"], "structural"))
    pair_stats = calc_paired_insert_stats(align_bam)
    fix_bam = remove_nopairs(align_bam, work_dir, config)
    tier2_align = tiered_alignment(fix_bam, "2", True, [],
                                   genome_build, pair_stats,
                                   work_dir, dirs, config)
    if tier2_align:
        tier3_align = tiered_alignment(tier2_align, "3", "Ex 1100", ["-t", "300"],
                                       genome_build, pair_stats,
                                       work_dir, dirs, config)
        if tier3_align:
            hydra_bps = hydra_breakpoints(tier3_align, pair_stats)

########NEW FILE########
__FILENAME__ = lumpy
"""Structural variation detection for split and paired reads using lumpy.

Uses speedseq for lumpy integration and samblaster for read preparation:
https://github.com/cc2qe/speedseq
https://github.com/GregoryFaust/samblaster
https://github.com/arq5x/lumpy-sv
"""
import operator
import os
import sys

import toolz as tz

from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.ngsalign import postalign
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.structural import delly
from bcbio.variation import vcfutils

# ## Read preparation

def _extract_split_and_discordants(in_bam, work_dir, data):
    """Retrieve split-read alignments from input BAM file.
    """
    dedup_file = os.path.join(work_dir, "%s-dedup.bam" % os.path.splitext(os.path.basename(in_bam))[0])
    sr_file = os.path.join(work_dir, "%s-sr.bam" % os.path.splitext(os.path.basename(in_bam))[0])
    disc_file = os.path.join(work_dir, "%s-disc.bam" % os.path.splitext(os.path.basename(in_bam))[0])
    samtools = config_utils.get_program("samtools", data["config"])
    cores = utils.get_in(data, ("config", "algorithm", "num_cores"), 1)
    resources = config_utils.get_resources("sambamba", data["config"])
    mem = config_utils.adjust_memory(resources.get("memory", "2G"),
                                     3, "decrease").upper()
    if not utils.file_exists(sr_file) or not utils.file_exists(disc_file) or utils.file_exists(dedup_file):
        with utils.curdir_tmpdir(data) as tmpdir:
            with file_transaction(sr_file) as tx_sr_file:
                with file_transaction(disc_file) as tx_disc_file:
                    with file_transaction(dedup_file) as tx_dedup_file:
                        samblaster_cl = postalign.samblaster_dedup_sort(data, tmpdir, tx_dedup_file,
                                                                        tx_sr_file, tx_disc_file)
                        out_base = os.path.join(tmpdir, "%s-namesort" % os.path.splitext(in_bam)[0])
                        cmd = ("{samtools} sort -n -o -@ {cores} -m {mem} {in_bam} {out_base} | "
                               "{samtools} view -h - | ")
                        cmd = cmd.format(**locals()) + samblaster_cl
                        do.run(cmd, "samblaster: split and discordant reads", data)
    for fname in [sr_file, disc_file, dedup_file]:
        bam.index(fname, data["config"])
    return dedup_file, sr_file, disc_file

def _find_existing_inputs(in_bam):
    """Check for pre-calculated split reads and discordants done as part of alignment streaming.
    """
    sr_file = "%s-sr.bam" % os.path.splitext(in_bam)[0]
    disc_file = "%s-disc.bam" % os.path.splitext(in_bam)[0]
    if utils.file_exists(sr_file) and utils.file_exists(disc_file):
        return in_bam, sr_file, disc_file
    else:
        return None, None, None

# ## Lumpy main

# Map from numbers used by speedseq to indicate paired and split read evidence
SUPPORT_NUMS = {"1": "PE", "0": "SR"}

def _run_lumpy(full_bams, sr_bams, disc_bams, work_dir, items):
    """Run lumpy-sv, using speedseq pipeline.
    """
    out_file = os.path.join(work_dir, "%s-svs.bedpe"
                            % os.path.splitext(os.path.basename(items[0]["align_bam"]))[0])
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with utils.curdir_tmpdir(items[0]) as tmpdir:
                out_base = utils.splitext_plus(tx_out_file)[0]
                full_bams = ",".join(full_bams)
                sr_bams = ",".join(sr_bams)
                disc_bams = ",".join(disc_bams)
                sv_exclude_bed = delly.prepare_exclude_file(items, out_file)
                exclude = "-x %s" % sv_exclude_bed if sv_exclude_bed else ""
                cmd = ("speedseq lumpy -v -B {full_bams} -S {sr_bams} -D {disc_bams} {exclude} "
                       "-T {tmpdir} -o {out_base}")
                do.run(cmd.format(**locals()), "speedseq lumpy", items[0])
    return out_file

def _get_support(parts):
    """Retrieve supporting information for potentially multiple samples.

    Convert speedseqs numbering scheme back into sample and support information.
    sample_ids are generated like 20 or 21, where the first number is sample number
    and the second is the type of supporting evidence.
    """
    out = {}
    for sample_id, read_count in (x.split(",") for x in parts[11].split(":")[-1].split(";")):
        support_type = SUPPORT_NUMS[sample_id[-1]]
        sample_id = int(sample_id[:-1]) - 1
        out = tz.update_in(out, [sample_id, support_type], lambda x: x + int(read_count), 0)
    return out

def _subset_to_sample(orig_file, index, data):
    """Subset population based calls to those supported within a single sample.
    """
    out_file = utils.append_stem(orig_file, "-" + data["rgnames"]["sample"])
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(orig_file) as in_handle:
                with open(tx_out_file, "w") as out_handle:
                    for parts in (l.rstrip().split("\t") for l in in_handle):
                        support = _get_support(parts)
                        if index in support:
                            out_handle.write("\t".join(parts) + "\n")
    return out_file

def _filter_by_support(orig_file, index):
    """Filter call file based on supporting evidence, adding pass/filter annotations to BEDPE.

    Filters based on the following criteria:
      - Minimum read support for the call.
    Other filters not currently applied due to being too restrictive:
      - Multiple forms of evidence in any sample (split and paired end)
    """
    min_read_count = 4
    out_file = utils.append_stem(orig_file, "-filter")
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(orig_file) as in_handle:
                with open(tx_out_file, "w") as out_handle:
                    for parts in (l.rstrip().split("\t") for l in in_handle):
                        support = _get_support(parts)
                        #evidence = set(reduce(operator.add, [x.keys() for x in support.values()]))
                        read_count = reduce(operator.add, support[index].values())
                        if read_count < min_read_count:
                            lfilter = "ReadCountSupport"
                        #elif len(evidence) < 2:
                        #    lfilter = "ApproachSupport"
                        else:
                            lfilter = "PASS"
                        parts.append(lfilter)
                        out_handle.write("\t".join(parts) + "\n")
    return out_file

def _write_samples_to_ids(base_file, items):
    """Write BED file mapping samples to IDs used in the lumpy bedpe output.
    """
    out_file = "%s-samples.bed" % utils.splitext_plus(base_file)[0]
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                for i, data in enumerate(items):
                    sample = tz.get_in(["rgnames", "sample"], data)
                    for sid, stype in SUPPORT_NUMS.items():
                        sample_id = "%s%s" % (i + 1, sid)
                        out_handle.write("%s\t%s\t%s\n" % (sample, sample_id, stype))
    return out_file

def _bedpe_to_vcf(bedpe_file, sconfig_file, items):
    """Convert BEDPE output into a VCF file.
    """
    tovcf_script = do.find_cmd("bedpeToVcf")
    if tovcf_script:
        out_file = "%s.vcf.gz" % utils.splitext_plus(bedpe_file)[0]
        out_nogzip = out_file.replace(".vcf.gz", ".vcf")
        raw_file = "%s-raw.vcf" % utils.splitext_plus(bedpe_file)[0]
        if not utils.file_exists(out_file):
            if not utils.file_exists(raw_file):
                with file_transaction(raw_file) as tx_raw_file:
                    ref_file = tz.get_in(["reference", "fasta", "base"], items[0])
                    cmd = [sys.executable, tovcf_script, "-c", sconfig_file, "-f", ref_file,
                           "-b", bedpe_file, "-o", tx_raw_file]
                    do.run(cmd, "Convert lumpy bedpe output to VCF")
            prep_file = vcfutils.sort_by_ref(raw_file, items[0])
            if not utils.file_exists(out_nogzip):
                utils.symlink_plus(prep_file, out_nogzip)
        out_file = vcfutils.bgzip_and_index(out_nogzip, items[0]["config"])
        return out_file

def _filter_by_bedpe(vcf_file, bedpe_file, data):
    """Add filters to VCF based on pre-filtered bedpe file.
    """
    out_file = "%s-filter%s" % utils.splitext_plus(vcf_file)
    nogzip_out_file = out_file.replace(".vcf.gz", ".vcf")
    if not utils.file_exists(out_file):
        filters = {}
        with open(bedpe_file) as in_handle:
            for line in in_handle:
                parts = line.split("\t")
                name = parts[6]
                cur_filter = parts[-1].strip()
                if cur_filter != "PASS":
                    filters[name] = cur_filter
        with file_transaction(nogzip_out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                with utils.open_gzipsafe(vcf_file) as in_handle:
                    for line in in_handle:
                        if not line.startswith("#"):
                            parts = line.split("\t")
                            cur_id = parts[2].split("_")[0]
                            cur_filter = filters.get(cur_id, "PASS")
                            if cur_filter != "PASS":
                                parts[6] = cur_filter
                            line = "\t".join(parts)
                        out_handle.write(line)
        if out_file.endswith(".gz"):
            vcfutils.bgzip_and_index(nogzip_out_file, data["config"])
    return out_file

def run(items):
    """Perform detection of structural variations with lumpy, using bwa-mem alignment.
    """
    if not all(utils.get_in(data, ("config", "algorithm", "aligner")) == "bwa" for data in items):
        raise ValueError("Require bwa-mem alignment input for lumpy structural variation detection")
    work_dir = utils.safe_makedir(os.path.join(items[0]["dirs"]["work"], "structural", items[0]["name"][-1],
                                               "lumpy"))
    full_bams, sr_bams, disc_bams = [], [], []
    for data in items:
        dedup_bam, sr_bam, disc_bam = _find_existing_inputs(data["align_bam"])
        if not dedup_bam:
            dedup_bam, sr_bam, disc_bam = _extract_split_and_discordants(data["align_bam"], work_dir, data)
        full_bams.append(dedup_bam)
        sr_bams.append(sr_bam)
        disc_bams.append(disc_bam)
    pebed_file = _run_lumpy(full_bams, sr_bams, disc_bams, work_dir, items)
    out = []
    sample_config_file = _write_samples_to_ids(pebed_file, items)
    lumpy_vcf = _bedpe_to_vcf(pebed_file, sample_config_file, items)
    for i, data in enumerate(items):
        if "sv" not in data:
            data["sv"] = []
        sample = tz.get_in(["rgnames", "sample"], data)
        sample_bedpe = _filter_by_support(_subset_to_sample(pebed_file, i, data), i)
        if lumpy_vcf:
            sample_vcf = utils.append_stem(lumpy_vcf, "-%s" % sample)
            sample_vcf = _filter_by_bedpe(vcfutils.select_sample(lumpy_vcf, sample, sample_vcf, data["config"]),
                                          sample_bedpe, data)
        else:
            sample_vcf = None
        data["sv"].append({"variantcaller": "lumpy",
                           "vrn_file": sample_vcf,
                           "bedpe_file": sample_bedpe,
                           "sample_bed": sample_config_file})
        out.append(data)
    return out

########NEW FILE########
__FILENAME__ = filesystem
"""Extract files from processing run into output directory, organized by sample.
"""
import os
import shutil

from bcbio import utils
from bcbio.log import logger
from bcbio.upload import shared

def copy_finfo(finfo, storage_dir, pass_uptodate=False):
    """Copy a file into the output storage directory.
    """
    if "sample" in finfo:
        out_file = os.path.join(storage_dir, "%s-%s.%s" % (finfo["sample"], finfo["ext"],
                                                           finfo["type"]))
    else:
        out_file = os.path.join(storage_dir, os.path.basename(finfo["path"]))
    out_file = os.path.abspath(out_file)
    if not shared.up_to_date(out_file, finfo):
        logger.info("Storing in local filesystem: %s" % out_file)
        shutil.copy(finfo["path"], out_file)
        return out_file
    if pass_uptodate:
        return out_file

def copy_finfo_directory(finfo, storage_dir):
    """Copy a directory into the final output directory.
    """
    out_dir = os.path.abspath(os.path.join(storage_dir, finfo["ext"]))
    if not shared.up_to_date(out_dir, finfo):
        logger.info("Storing directory in local filesystem: %s" % out_dir)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        shutil.copytree(finfo["path"], out_dir)
        os.utime(out_dir, None)
    return out_dir

def update_file(finfo, sample_info, config):
    """Update the file in local filesystem storage.
    """
    # skip if we have no directory to upload to
    if "dir" not in config:
        return
    if "sample" in finfo:
        storage_dir = utils.safe_makedir(os.path.join(config["dir"], finfo["sample"]))
    elif "run" in finfo:
        storage_dir = utils.safe_makedir(os.path.join(config["dir"], finfo["run"]))
    else:
        raise ValueError("Unexpected input file information: %s" % finfo)
    if finfo.get("type") == "directory":
        return copy_finfo_directory(finfo, storage_dir)
    else:
        return copy_finfo(finfo, storage_dir)

########NEW FILE########
__FILENAME__ = galaxy
"""Move files to local Galaxy upload directory and add to Galaxy Data Libraries.

Required configurable variables in upload:
  dir
"""
import collections
import os
import shutil
import time

import bioblend
import simplejson

from bcbio import utils
from bcbio.log import logger
from bcbio.upload import filesystem
from bcbio.pipeline import qcsummary

# Avoid bioblend import errors, raising at time of use
try:
    from bioblend.galaxy import GalaxyInstance
except ImportError:
    GalaxyInstance = None

def update_file(finfo, sample_info, config):
    """Update file in Galaxy data libraries.
    """
    if GalaxyInstance is None:
        raise ImportError("Could not import bioblend.galaxy")
    if "dir" not in config:
        raise ValueError("Galaxy upload requires `dir` parameter in config specifying the "
                         "shared filesystem path to move files to.")
    if "outputs" in config:
        _galaxy_tool_copy(finfo, config["outputs"])
    else:
        _galaxy_library_upload(finfo, sample_info, config)

def _galaxy_tool_copy(finfo, outputs):
    """Copy information directly to pre-defined outputs from a Galaxy tool.

    XXX Needs generalization
    """
    tool_map = {"align": "bam", "variants": "vcf.gz"}
    for galaxy_key, finfo_type in tool_map.items():
        if galaxy_key in outputs and finfo.get("type") == finfo_type:
            shutil.copy(finfo["path"], outputs[galaxy_key])

def _galaxy_library_upload(finfo, sample_info, config):
    """Upload results to galaxy library.
    """
    folder_name = "%s_%s" % (config["fc_date"], config["fc_name"])
    storage_dir = utils.safe_makedir(os.path.join(config["dir"], folder_name))
    if finfo.get("type") == "directory":
        storage_file = None
        if finfo.get("ext") == "qc":
            pdf_file = qcsummary.prep_pdf(finfo["path"], config)
            if pdf_file:
                finfo["path"] = pdf_file
                finfo["type"] = "pdf"
                storage_file = filesystem.copy_finfo(finfo, storage_dir, pass_uptodate=True)
    else:
        storage_file = filesystem.copy_finfo(finfo, storage_dir, pass_uptodate=True)
    if "galaxy_url" in config and "galaxy_api_key" in config:
        galaxy_url = config["galaxy_url"]
        if not galaxy_url.endswith("/"):
            galaxy_url += "/"
        gi = GalaxyInstance(galaxy_url, config["galaxy_api_key"])
    else:
        raise ValueError("Galaxy upload requires `galaxy_url` and `galaxy_api_key` in config")
    if storage_file and sample_info and not finfo.get("index", False):
        _to_datalibrary_safe(storage_file, gi, folder_name, sample_info, config)

def _to_datalibrary_safe(fname, gi, folder_name, sample_info, config):
    """Upload with retries for intermittent JSON failures.
    """
    num_tries = 0
    max_tries = 5
    while 1:
        try:
            _to_datalibrary(fname, gi, folder_name, sample_info, config)
            break
        except (simplejson.scanner.JSONDecodeError, bioblend.galaxy.client.ConnectionError) as e:
            num_tries += 1
            if num_tries > max_tries:
                raise
            print "Retrying upload, failed with:", str(e)
            time.sleep(5)

def _to_datalibrary(fname, gi, folder_name, sample_info, config):
    """Upload a file to a Galaxy data library in a project specific folder.
    """
    library = _get_library(gi, sample_info, config)
    libitems = gi.libraries.show_library(library.id, contents=True)
    folder = _get_folder(gi, folder_name, library, libitems)
    _file_to_folder(gi, fname, sample_info, libitems, library, folder)

def _file_to_folder(gi, fname, sample_info, libitems, library, folder):
    """Check if file exists on Galaxy, if not upload to specified folder.
    """
    full_name = os.path.join(folder["name"], os.path.basename(fname))

    # Handle VCF: Galaxy reports VCF files without the gzip extension
    file_type = "vcf_bgzip" if full_name.endswith(".vcf.gz") else "auto"
    if full_name.endswith(".vcf.gz"):
        full_name = full_name.replace(".vcf.gz", ".vcf")

    for item in libitems:
        if item["name"] == full_name:
            return item
    logger.info("Uploading to Galaxy library '%s': %s" % (library.name, full_name))
    return gi.libraries.upload_from_galaxy_filesystem(str(library.id), fname, folder_id=str(folder["id"]),
                                                      link_data_only="link_to_files",
                                                      dbkey=sample_info["genome_build"],
                                                      file_type=file_type,
                                                      roles=str(library.roles) if library.roles else None)

def _get_folder(gi, folder_name, library, libitems):
    """Retrieve or create a folder inside the library with the specified name.
    """
    for item in libitems:
        if item["type"] == "folder" and item["name"] == "/%s" % folder_name:
            return item
    return gi.libraries.create_folder(library.id, folder_name)[0]

GalaxyLibrary = collections.namedtuple("GalaxyLibrary", ["id", "name", "roles"])

def _get_library(gi, sample_info, config):
    """Retrieve the appropriate data library for the current user.
    """
    galaxy_lib = sample_info.get("galaxy_library",
                                 config.get("galaxy_library"))
    role = sample_info.get("galaxy_role",
                           config.get("galaxy_role"))
    if galaxy_lib:
        return _get_library_from_name(gi, galaxy_lib, role, sample_info, create=True)
    elif config.get("private_libs") or config.get("lab_association") or config.get("researcher"):
        return _library_from_nglims(gi, sample_info, config)
    else:
        raise ValueError("No Galaxy library specified for sample: %s" %
                         sample_info["description"])

def _get_library_from_name(gi, name, role, sample_info, create=False):
    for lib in gi.libraries.get_libraries():
        if lib["name"].lower() == name.lower() and not lib.get("deleted", False):
            return GalaxyLibrary(lib["id"], lib["name"], role)
    if create and name:
        logger.info("Creating Galaxy library: '%s'" % name)
        lib = gi.libraries.create_library(name)
        librole = str(gi.users.get_current_user()["id"] if not role else role)
        try:
            gi.libraries.set_library_permissions(str(lib["id"]), librole, librole, librole, librole)
        # XXX Returns error on Galaxy side but seems to work -- ugly
        except:
            pass
        return GalaxyLibrary(lib["id"], lib["name"], role)
    else:
        raise ValueError("Could not find Galaxy library matching '%s' for sample %s" %
                         (name, sample_info["description"]))

def _library_from_nglims(gi, sample_info, config):
    """Retrieve upload library from nglims specified user libraries.
    """
    names = [config.get(x, "").strip() for x in ["lab_association", "researcher"]
             if config.get(x)]
    for name in names:
        for ext in ["sequencing", "lab"]:
            check_name = "%s %s" % (name.split()[0], ext)
            try:
                return _get_library_from_name(gi, check_name, None, sample_info)
            except ValueError:
                pass
    check_names = set([x.lower() for x in names])
    for libname, role in config["private_libs"]:
        # Try to find library for lab or rsearcher
        if libname.lower() in check_names:
            return _get_library_from_name(gi, libname, role, sample_info)
    # default to first private library if available
    if len(config.get("private_libs", [])) > 0:
        libname, role = config["private_libs"][0]
        return _get_library_from_name(gi, libname, role, sample_info)
    # otherwise use the lab association or researcher name
    elif len(names) > 0:
        return _get_library_from_name(gi, names[0], None, sample_info, create=True)
    else:
        raise ValueError("Could not find Galaxy library for sample %s" % sample_info["description"])

########NEW FILE########
__FILENAME__ = s3
"""Handle upload and retrieval of files from S3 on Amazon AWS.
"""
import datetime
import email
import os

from bcbio.log import logger

def get_file(local_dir, bucket_name, fname, params):
    """Retrieve file from amazon S3 to a local directory for processing.
    """
    import boto
    out_file = os.path.join(local_dir, os.path.basename(fname))
    conn = boto.connect_s3(params.get("access_key_id"), params.get("secret_access_key"))
    bucket = conn.get_bucket(bucket_name)
    key = bucket.get_key(fname)
    key.get_contents_to_filename(out_file)
    return out_file

def _update_val(key, val):
    if key == "mtime":
        return val.isoformat()
    elif key in ["path", "ext"]:
        return None
    else:
        return val

def update_file(finfo, sample_info, config):
    """Update the file to an Amazon S3 bucket.
    """
    import boto
    conn = boto.connect_s3(config.get("access_key_id"),
                           config.get("secret_access_key"))
    bucket = conn.lookup(config["bucket"])
    if bucket is None:
        bucket = conn.create_bucket(config["bucket"])
    s3dirname = finfo["sample"] if finfo.has_key("sample") else finfo["run"]
    keyname = os.path.join(s3dirname, os.path.basename(finfo["path"]))
    key = bucket.get_key(keyname)
    modified = datetime.datetime.fromtimestamp(email.utils.mktime_tz(
        email.utils.parsedate_tz(key.last_modified))) if key else None
    no_upload = key and modified >= finfo["mtime"]
    if key is None:
        key = boto.s3.key.Key(bucket, keyname)
    if not no_upload:
        logger.info("Uploading to S3: %s %s" % (config["bucket"], keyname))
        for name, val in finfo.iteritems():
            val = _update_val(name, val)
            if val:
                key.set_metadata(name, val)
        key.set_contents_from_filename(finfo["path"],
          reduced_redundancy=config.get("reduced_redundancy", False))

########NEW FILE########
__FILENAME__ = shared
"""Shared functionality for managing upload of final files.
"""
import os
import datetime

from bcbio import utils

def get_file_timestamp(f):
    return datetime.datetime.fromtimestamp(os.path.getmtime(f))

def up_to_date(new, orig):
    if os.path.isdir(orig["path"]):
        return (os.path.exists(new) and
                get_file_timestamp(new) >= orig["mtime"])
    else:
        return (utils.file_exists(new) and
                get_file_timestamp(new) >= orig["mtime"])

########NEW FILE########
__FILENAME__ = utils
"""Helpful utilities for building analysis pipelines.
"""
import gzip
import json
import os
import tempfile
import time
import shutil
import contextlib
import itertools
import functools
import random
import ConfigParser
try:
    from concurrent import futures
except ImportError:
    try:
        import futures
    except ImportError:
        futures = None
import collections
import yaml
import fnmatch
import zlib


@contextlib.contextmanager
def cpmap(cores=1):
    """Configurable parallel map context manager.

    Returns appropriate map compatible function based on configuration:
    - Local single core (the default)
    - Multiple local cores
    """
    if int(cores) == 1:
        yield itertools.imap
    else:
        if futures is None:
            raise ImportError("concurrent.futures not available")
        pool = futures.ProcessPoolExecutor(cores)
        yield pool.map
        pool.shutdown()

def map_wrap(f):
    """Wrap standard function to easily pass into 'map' processing.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return apply(f, *args, **kwargs)
    return wrapper

def transform_to(ext):
    """
    Decorator to create an output filename from an output filename with
    the specified extension. Changes the extension, in_file is transformed
    to a new type.

    Takes functions like this to decorate:
    f(in_file, out_dir=None, out_file=None) or,
    f(in_file=in_file, out_dir=None, out_file=None)

    examples:
    @transform(".bam")
    f("the/input/path/file.sam") ->
        f("the/input/path/file.sam", out_file="the/input/path/file.bam")

    @transform(".bam")
    f("the/input/path/file.sam", out_dir="results") ->
        f("the/input/path/file.sam", out_file="results/file.bam")

    """

    def decor(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            out_file = kwargs.get("out_file", None)
            if not out_file:
                in_path = kwargs.get("in_file", args[0])
                out_dir = kwargs.get("out_dir", os.path.dirname(in_path))
                safe_makedir(out_dir)
                out_name = replace_suffix(os.path.basename(in_path), ext)
                out_file = os.path.join(out_dir, out_name)
            kwargs["out_file"] = out_file
            if not file_exists(out_file):
                out_file = f(*args, **kwargs)
            return out_file
        return wrapper
    return decor


def filter_to(word):
    """
    Decorator to create an output filename from an input filename by
    adding a word onto the stem. in_file is filtered by the function
    and the results are written to out_file. You would want to use
    this over transform_to if you don't know the extension of the file
    going in. This also memoizes the output file.

    Takes functions like this to decorate:
    f(in_file, out_dir=None, out_file=None) or,
    f(in_file=in_file, out_dir=None, out_file=None)

    examples:
    @filter_to(".foo")
    f("the/input/path/file.sam") ->
        f("the/input/path/file.sam", out_file="the/input/path/file.foo.bam")

    @filter_to(".foo")
    f("the/input/path/file.sam", out_dir="results") ->
        f("the/input/path/file.sam", out_file="results/file.foo.bam")

    """

    def decor(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            out_file = kwargs.get("out_file", None)
            if not out_file:
                in_path = kwargs.get("in_file", args[0])
                out_dir = kwargs.get("out_dir", os.path.dirname(in_path))
                safe_makedir(out_dir)
                out_name = append_stem(os.path.basename(in_path), word)
                out_file = os.path.join(out_dir, out_name)
            kwargs["out_file"] = out_file
            if not file_exists(out_file):
                out_file = f(*args, **kwargs)
            return out_file
        return wrapper
    return decor


def memoize_outfile(ext=None, stem=None):
    """
    Memoization decorator.

    See docstring for transform_to and filter_to for details.
    """
    if ext:
        return transform_to(ext)
    if stem:
        return filter_to(stem)


def safe_makedir(dname):
    """Make a directory if it doesn't exist, handling concurrent race conditions.
    """
    if not dname:
        return dname
    num_tries = 0
    max_tries = 5
    while not os.path.exists(dname):
        # we could get an error here if multiple processes are creating
        # the directory at the same time. Grr, concurrency.
        try:
            os.makedirs(dname)
        except OSError:
            if num_tries > max_tries:
                raise
            num_tries += 1
            time.sleep(2)
    return dname

@contextlib.contextmanager
def curdir_tmpdir(data=None, base_dir=None, remove=True):
    """Context manager to create and remove a temporary directory.

    This can also handle a configured temporary directory to use.
    """
    config_tmpdir = get_in(data, ("config", "resources", "tmp", "dir")) if data else None
    if config_tmpdir:
        tmp_dir_base = os.path.join(config_tmpdir, "bcbiotmp")
    elif base_dir is not None:
        tmp_dir_base = os.path.join(base_dir, "bcbiotmp")
    else:
        tmp_dir_base = os.path.join(os.getcwd(), "tmp")
    safe_makedir(tmp_dir_base)
    tmp_dir = tempfile.mkdtemp(dir=tmp_dir_base)
    safe_makedir(tmp_dir)
    try:
        yield tmp_dir
    finally:
        if remove:
            try:
                shutil.rmtree(tmp_dir)
            except:
                pass

@contextlib.contextmanager
def chdir(new_dir):
    """Context manager to temporarily change to a new directory.

    http://lucentbeing.com/blog/context-managers-and-the-with-statement-in-python/
    """
    cur_dir = os.getcwd()
    safe_makedir(new_dir)
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(cur_dir)

@contextlib.contextmanager
def tmpfile(*args, **kwargs):
    """Make a tempfile, safely cleaning up file descriptors on completion.
    """
    (fd, fname) = tempfile.mkstemp(*args, **kwargs)
    try:
        yield fname
    finally:
        os.close(fd)
        if os.path.exists(fname):
            os.remove(fname)

def file_exists(fname):
    """Check if a file exists and is non-empty.
    """
    return fname and os.path.exists(fname) and os.path.getsize(fname) > 0

def file_uptodate(fname, cmp_fname):
    """Check if a file exists, is non-empty and is more recent than cmp_fname.
    """
    return (file_exists(fname) and file_exists(cmp_fname) and
            os.path.getmtime(fname) >= os.path.getmtime(cmp_fname))

def create_dirs(config, names=None):
    if names is None:
        names = config["dir"].keys()
    for dname in names:
        d = config["dir"][dname]
        safe_makedir(d)

def save_diskspace(fname, reason, config):
    """Overwrite a file in place with a short message to save disk.

    This keeps files as a sanity check on processes working, but saves
    disk by replacing them with a short message.
    """
    if config["algorithm"].get("save_diskspace", False):
        with open(fname, "w") as out_handle:
            out_handle.write("File removed to save disk space: %s" % reason)

def read_galaxy_amqp_config(galaxy_config, base_dir):
    """Read connection information on the RabbitMQ server from Galaxy config.
    """
    galaxy_config = add_full_path(galaxy_config, base_dir)
    config = ConfigParser.ConfigParser()
    config.read(galaxy_config)
    amqp_config = {}
    for option in config.options("galaxy_amqp"):
        amqp_config[option] = config.get("galaxy_amqp", option)
    return amqp_config

def add_full_path(dirname, basedir=None):
    if basedir is None:
        basedir = os.getcwd()
    if not dirname.startswith("/"):
        dirname = os.path.join(basedir, dirname)
    return dirname

def splitext_plus(f):
    """Split on file extensions, allowing for zipped extensions.
    """
    base, ext = os.path.splitext(f)
    if ext in [".gz", ".bz2", ".zip"]:
        base, ext2 = os.path.splitext(base)
        ext = ext2 + ext
    return base, ext

def remove_safe(f):
    try:
        os.remove(f)
    except OSError:
        pass

def symlink_plus(orig, new):
    """Create relative symlinks and handle associated biological index files.
    """
    for ext in ["", ".idx", ".gbi", ".tbi", ".bai"]:
        if os.path.exists(orig + ext) and (not os.path.lexists(new + ext) or not os.path.exists(new + ext)):
            with chdir(os.path.dirname(new)):
                remove_safe(new + ext)
                os.symlink(os.path.relpath(orig + ext), os.path.basename(new + ext))
                # Work around symlink issues on some filesystems. Randomly fail to symlink.
                if not os.path.exists(new + ext) or not os.path.lexists(new + ext):
                    remove_safe(new + ext)
                    shutil.copyfile(orig + ext, new + ext)
    orig_noext = splitext_plus(orig)[0]
    new_noext = splitext_plus(new)[0]
    for sub_ext in [".bai"]:
        if os.path.exists(orig_noext + sub_ext) and not os.path.lexists(new_noext + sub_ext):
            with chdir(os.path.dirname(new_noext)):
                os.symlink(os.path.relpath(orig_noext + sub_ext), os.path.basename(new_noext + sub_ext))

def open_gzipsafe(f):
    return gzip.open(f) if f.endswith(".gz") else open(f)

def append_stem(to_transform, word):
    """
    renames a filename or list of filenames with 'word' appended to the stem
    of each one:
    example: append_stem("/path/to/test.sam", "_filtered") ->
    "/path/to/test_filtered.sam"

    """
    if is_sequence(to_transform):
        return [append_stem(f, word) for f in to_transform]
    elif is_string(to_transform):
        (base, ext) = splitext_plus(to_transform)
        return "".join([base, word, ext])
    else:
        raise ValueError("append_stem takes a single filename as a string or "
                         "a list of filenames to transform.")


def replace_suffix(to_transform, suffix):
    """
    replaces the suffix on a filename or list of filenames
    example: replace_suffix("/path/to/test.sam", ".bam") ->
    "/path/to/test.bam"

    """
    if is_sequence(to_transform):
        transformed = []
        for f in to_transform:
            (base, _) = os.path.splitext(f)
            transformed.append(base + suffix)
        return transformed
    elif is_string(to_transform):
        (base, _) = os.path.splitext(to_transform)
        return base + suffix
    else:
        raise ValueError("replace_suffix takes a single filename as a string or "
                         "a list of filenames to transform.")

# ## Functional programming

def partition_all(n, iterable):
    """Partition a list into equally sized pieces, including last smaller parts
    http://stackoverflow.com/questions/5129102/python-equivalent-to-clojures-partition-all
    """
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, n))
        if not chunk:
            break
        yield chunk

def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return itertools.ifilterfalse(pred, t1), itertools.ifilter(pred, t2)

# ## Dealing with configuration files

def merge_config_files(fnames):
    """Merge configuration files, preferring definitions in latter files.
    """
    def _load_yaml(fname):
        with open(fname) as in_handle:
            config = yaml.load(in_handle)
        return config
    out = _load_yaml(fnames[0])
    for fname in fnames[1:]:
        cur = _load_yaml(fname)
        for k, v in cur.iteritems():
            if out.has_key(k) and isinstance(out[k], dict):
                out[k].update(v)
            else:
                out[k] = v
    return out


def get_in(d, t, default=None):
    """
    look up if you can get a tuple of values from a nested dictionary,
    each item in the tuple a deeper layer

    example: get_in({1: {2: 3}}, (1, 2)) -> 3
    example: get_in({1: {2: 3}}, (2, 3)) -> {}
    """
    result = reduce(lambda d, t: d.get(t, {}), t, d)
    if result is False:
        return result
    elif not result:
        return default
    else:
        return result


def flatten(l):
    """
    flatten an irregular list of lists
    example: flatten([[[1, 2, 3], [4, 5]], 6]) -> [1, 2, 3, 4, 5, 6]
    lifted from: http://stackoverflow.com/questions/2158395/

    """
    for el in l:
        if isinstance(el, collections.Iterable) and not isinstance(el,
                                                                   basestring):
            for sub in flatten(el):
                yield sub
        else:
            yield el


def is_sequence(arg):
    """
    check if 'arg' is a sequence

    example: arg([]) -> True
    example: arg("lol") -> False

    """
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))


def is_pair(arg):
    """
    check if 'arg' is a two-item sequence

    """
    return is_sequence(arg) and len(arg) == 2

def is_string(arg):
    return isinstance(arg, basestring)


def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def itersubclasses(cls, _seen=None):
    """
    snagged from:  http://code.activestate.com/recipes/576949/
    itersubclasses(cls)

    Generator over all subclasses of a given class, in depth first order.

    >>> list(itersubclasses(int)) == [bool]
    True
    >>> class A(object): pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>>
    >>> for cls in itersubclasses(A):
    ...     print(cls.__name__)
    B
    D
    E
    C
    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in itersubclasses(object)] #doctest: +ELLIPSIS
    ['type', ...'tuple', ...]
    """

    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None:
        _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError:  # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub

def replace_directory(out_files, dest_dir):
    """
    change the output directory to dest_dir
    can take a string (single file) or a list of files

    """
    if is_sequence(out_files):
        filenames = map(os.path.basename, out_files)
        return [os.path.join(dest_dir, x) for x in filenames]
    elif is_string(out_files):
        return os.path.join(dest_dir, os.path.basename(out_files))
    else:
        raise ValueError("in_files must either be a sequence of filenames "
                         "or a string")

def which(program):
    """ returns the path to an executable or None if it can't be found"""

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def reservoir_sample(stream, num_items, item_parser=lambda x: x):
    """
    samples num_items from the stream keeping each with equal probability
    """
    kept = []
    for index, item in enumerate(stream):
        if index < num_items:
            kept.append(item_parser(item))
        else:
            r = random.randint(0, index)
            if r < num_items:
                kept[r] = item_parser(item)
    return kept


def compose(f, g):
    return lambda x: f(g(x))

def dictapply(d, fn):
    """
    apply a function to all non-dict values in a dictionary
    """
    for k, v in d.items():
        if isinstance(v, dict):
            v = dictapply(v, fn)
        else:
            d[k] = fn(v)
    return d

########NEW FILE########
__FILENAME__ = annotation
"""Annotated variant VCF files with additional information.

- GATK variant annotation with snpEff predicted effects.
"""
import os

from bcbio import broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.variation import vcfutils

def get_gatk_annotations(config):
    broad_runner = broad.runner_from_config(config)
    anns = ["BaseQualityRankSumTest", "FisherStrand",
            "GCContent", "HaplotypeScore", "HomopolymerRun",
            "MappingQualityRankSumTest", "MappingQualityZero",
            "QualByDepth", "ReadPosRankSumTest", "RMSMappingQuality",
            "DepthPerAlleleBySample"]
    if broad_runner.gatk_type() == "restricted":
        anns += ["Coverage"]
    else:
        anns += ["DepthOfCoverage"]
    return anns

def annotate_nongatk_vcf(orig_file, bam_files, dbsnp_file, ref_file, config):
    """Annotate a VCF file with dbSNP and standard GATK called annotations.
    """
    orig_file = vcfutils.bgzip_and_index(orig_file, config)
    out_file = "%s-gatkann%s" % utils.splitext_plus(orig_file)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            # Avoid issues with incorrectly created empty GATK index files.
            # Occurs when GATK cannot lock shared dbSNP database on previous run
            idx_file = orig_file + ".idx"
            if os.path.exists(idx_file) and not utils.file_exists(idx_file):
                os.remove(idx_file)
            annotations = get_gatk_annotations(config)
            params = ["-T", "VariantAnnotator",
                      "-R", ref_file,
                      "--variant", orig_file,
                      "--dbsnp", dbsnp_file,
                      "--out", tx_out_file,
                      "-L", orig_file]
            for bam_file in bam_files:
                params += ["-I", bam_file]
            for x in annotations:
                params += ["-A", x]
            broad_runner = broad.runner_from_config(config)
            broad_runner.run_gatk(params, memory_retry=True)
    vcfutils.bgzip_and_index(out_file, config)
    return out_file

########NEW FILE########
__FILENAME__ = bamprep
"""Provide piped, no disk-IO, BAM preparation for variant calling.
Handles independent analysis of chromosome regions, allowing parallel
runs of this step.
"""
import os

from bcbio import bam, broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, shared
from bcbio.provenance import do
from bcbio.variation import realign

# ## GATK/Picard preparation

def region_to_gatk(region):
    if isinstance(region, (list, tuple)):
        chrom, start, end = region
        return "%s:%s-%s" % (chrom, start + 1, end)
    else:
        return region

def _gatk_extract_reads_cl(data, region, prep_params, tmp_dir):
    """Use GATK to extract reads from full BAM file, recalibrating if configured.
    """
    args = ["-T", "PrintReads",
            "-L", region_to_gatk(region),
            "-R", data["sam_ref"],
            "-I", data["work_bam"]]
    if prep_params.get("max_depth"):
        args += ["--downsample_to_coverage", str(prep_params["max_depth"])]
    if prep_params["recal"] == "gatk":
        if _recal_has_reads(data["prep_recal"]):
            args += ["-BQSR", data["prep_recal"]]
    elif prep_params["recal"]:
        raise NotImplementedError("Recalibration method %s" % prep_params["recal"])
    jvm_opts = broad.get_gatk_framework_opts(data["config"],
                                             memscale={"direction": "decrease", "magnitude": 3})
    return [config_utils.get_program("gatk-framework", data["config"])] + jvm_opts + args

def _recal_has_reads(in_file):
    with open(in_file) as in_handle:
        return not in_handle.readline().startswith("# No aligned reads")

def _piped_input_cl(data, region, tmp_dir, out_base_file, prep_params):
    """Retrieve the commandline for streaming input into preparation step.
    """
    cl = _gatk_extract_reads_cl(data, region, prep_params, tmp_dir)
    sel_file = data["work_bam"]
    bam.index(sel_file, data["config"])
    return sel_file, " ".join(cl)

def _piped_realign_gatk(data, region, cl, out_base_file, tmp_dir, prep_params):
    """Perform realignment with GATK, using input commandline.
    GATK requires writing to disk and indexing before realignment.
    """
    broad_runner = broad.runner_from_config(data["config"])
    pa_bam = "%s-prealign%s" % os.path.splitext(out_base_file)
    if not utils.file_exists(pa_bam):
        with file_transaction(pa_bam) as tx_out_file:
            cmd = "{cl} -o {tx_out_file}".format(**locals())
            do.run(cmd, "GATK pre-alignment {0}".format(region), data)
    bam.index(pa_bam, data["config"])
    dbsnp_vcf = data["genome_resources"]["variation"]["dbsnp"]
    recal_file = realign.gatk_realigner_targets(broad_runner, pa_bam, data["sam_ref"],
                                                dbsnp=dbsnp_vcf, region=region_to_gatk(region))
    recal_cl = realign.gatk_indel_realignment_cl(broad_runner, pa_bam, data["sam_ref"],
                                                 recal_file, tmp_dir, region=region_to_gatk(region))
    return pa_bam, " ".join(recal_cl)

def _cleanup_tempfiles(data, tmp_files):
    for tmp_file in tmp_files:
        if tmp_file and tmp_file != data["work_bam"]:
            for ext in [".bam", ".bam.bai", ".bai"]:
                fname = "%s%s" % (os.path.splitext(tmp_file)[0], ext)
                if os.path.exists(fname):
                    os.remove(fname)

def _piped_bamprep_region_gatk(data, region, prep_params, out_file, tmp_dir):
    """Perform semi-piped BAM preparation using Picard/GATK tools.
    """
    broad_runner = broad.runner_from_config(data["config"])
    cur_bam, cl = _piped_input_cl(data, region, tmp_dir, out_file, prep_params)
    if not prep_params["realign"]:
        prerecal_bam = None
    elif prep_params["realign"] == "gatk":
        prerecal_bam, cl = _piped_realign_gatk(data, region, cl, out_file, tmp_dir,
                                               prep_params)
    else:
        raise NotImplementedError("Realignment method: %s" % prep_params["realign"])
    with file_transaction(out_file) as tx_out_file:
        out_flag = ("-o" if (prep_params["realign"] == "gatk"
                             or not prep_params["realign"])
                    else ">")
        cmd = "{cl} {out_flag} {tx_out_file}".format(**locals())
        do.run(cmd, "GATK: realign {0}".format(region), data)
        _cleanup_tempfiles(data, [cur_bam, prerecal_bam])

# ## Shared functionality

def _get_prep_params(data):
    """Retrieve configuration parameters with defaults for preparing BAM files.
    """
    algorithm = data["config"]["algorithm"]
    recal_param = algorithm.get("recalibrate", True)
    recal_param = "gatk" if recal_param is True else recal_param
    realign_param = algorithm.get("realign", True)
    realign_param = "gatk" if realign_param is True else realign_param
    max_depth = algorithm.get("coverage_depth_max", 10000)
    return {"recal": recal_param, "realign": realign_param,
            "max_depth": max_depth}

def _need_prep(data):
    prep_params = _get_prep_params(data)
    return prep_params["recal"] or prep_params["realign"]

def _piped_bamprep_region(data, region, out_file, tmp_dir):
    """Do work of preparing BAM input file on the selected region.
    """
    if _need_prep(data):
        prep_params = _get_prep_params(data)
        _piped_bamprep_region_gatk(data, region, prep_params, out_file, tmp_dir)
    else:
        raise ValueError("No recalibration or realignment specified")

def piped_bamprep(data, region=None, out_file=None):
    """Perform full BAM preparation using pipes to avoid intermediate disk IO.

    Handles recalibration and realignment of original BAMs.
    """
    data["region"] = region
    if not _need_prep(data):
        return [data]
    else:
        utils.safe_makedir(os.path.dirname(out_file))
        if region[0] == "nochrom":
            prep_bam = shared.write_nochr_reads(data["work_bam"], out_file, data["config"])
        elif region[0] == "noanalysis":
            prep_bam = shared.write_noanalysis_reads(data["work_bam"], region[1], out_file,
                                                     data["config"])
        else:
            if not utils.file_exists(out_file):
                with utils.curdir_tmpdir(data) as tmp_dir:
                    _piped_bamprep_region(data, region, out_file, tmp_dir)
            prep_bam = out_file
        bam.index(prep_bam, data["config"])
        data["work_bam"] = prep_bam
        return [data]

########NEW FILE########
__FILENAME__ = bedutils
"""Utilities for manipulating BED files.
"""
import os
import shutil

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.variation import vcfutils

def clean_file(in_file, data, prefix=""):
    """Prepare a clean input BED file without headers or overlapping segments.

    Overlapping regions (1:1-100, 1:90-100) cause issues with callers like FreeBayes
    that don't collapse BEDs prior to using them.
    """
    bedtools = config_utils.get_program("bedtools", data["config"])
    if in_file:
        bedprep_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "bedprep"))
        out_file = os.path.join(bedprep_dir, "%s%s" % (prefix, os.path.basename(in_file)))
        if not utils.file_exists(out_file):
            with file_transaction(out_file) as tx_out_file:
                cmd = "sort -k1,1 -k2,2n {in_file} | {bedtools} merge -i > {tx_out_file}"
                do.run(cmd.format(**locals()), "Prepare cleaned BED file", data)
        vcfutils.bgzip_and_index(out_file, data["config"], remove_orig=False)
        return out_file

def clean_inputs(data):
    """Clean BED input files to avoid overlapping segments that cause downstream issues.
    """
    data["config"]["algorithm"]["variant_regions"] = clean_file(
        utils.get_in(data, ("config", "algorithm", "variant_regions")), data)
    return data

def combine(in_files, out_file, config):
    """Combine multiple BED files into a single output.
    """
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                for in_file in in_files:
                    with open(in_file) as in_handle:
                        shutil.copyfileobj(in_handle, out_handle)
    return out_file

########NEW FILE########
__FILENAME__ = cortex
"""Perform regional de-novo assembly calling with cortex_var.

Using a pre-mapped set of reads and BED file of regions, performs de-novo
assembly and variant calling against the reference sequence in each region.
This avoids whole genome costs while gaining the advantage of de-novo
prediction.

http://cortexassembler.sourceforge.net/index_cortex_var.html
"""
import os
import glob
import subprocess
import itertools
import shutil
from contextlib import closing

import pysam
from Bio import Seq
from Bio.SeqIO.QualityIO import FastqGeneralIterator

from bcbio import bam
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.utils import file_exists, safe_makedir
from bcbio.variation import vcfutils

def run_cortex(align_bams, items, ref_file, assoc_files, region=None,
               out_file=None):
    """Top level entry to regional de-novo based variant calling with cortex_var.
    """
    raise NotImplementedError("Cortex currently out of date and needs reworking.")
    if len(align_bams) == 1:
        align_bam = align_bams[0]
        config = items[0]["config"]
    else:
        raise NotImplementedError("Need to add multisample calling for cortex_var")
    if out_file is None:
        out_file = "%s-cortex.vcf" % os.path.splitext(align_bam)[0]
    if region is not None:
        work_dir = safe_makedir(os.path.join(os.path.dirname(out_file),
                                             region.replace(".", "_")))
    else:
        work_dir = os.path.dirname(out_file)
    if not file_exists(out_file):
        bam.index(align_bam, config)
        variant_regions = config["algorithm"].get("variant_regions", None)
        if not variant_regions:
            raise ValueError("Only support regional variant calling with cortex_var: set variant_regions")
        target_regions = subset_variant_regions(variant_regions, region, out_file)
        if os.path.isfile(target_regions):
            with open(target_regions) as in_handle:
                regional_vcfs = [_run_cortex_on_region(x.strip().split("\t")[:3], align_bam,
                                                       ref_file, work_dir, out_file, config)
                                 for x in in_handle]

            combine_file = apply("{0}-raw{1}".format, os.path.splitext(out_file))
            _combine_variants(regional_vcfs, combine_file, ref_file, config)
            _select_final_variants(combine_file, out_file, config)
        else:
            vcfutils.write_empty_vcf(out_file)
    return out_file

def _passes_cortex_depth(line, min_depth):
    """Do any genotypes in the cortex_var VCF line passes the minimum depth requirement?
    """
    parts = line.split("\t")
    cov_index = parts[8].split(":").index("COV")
    passes_depth = False
    for gt in parts[9:]:
        cur_cov = gt.split(":")[cov_index]
        cur_depth = sum(int(x) for x in cur_cov.split(","))
        if cur_depth >= min_depth:
            passes_depth = True
    return passes_depth

def _select_final_variants(base_vcf, out_vcf, config):
    """Filter input file, removing items with low depth of support.

    cortex_var calls are tricky to filter by depth. Count information is in
    the COV FORMAT field grouped by alleles, so we need to sum up values and
    compare.
    """
    min_depth = int(config["algorithm"].get("min_depth", 4))
    with file_transaction(out_vcf) as tx_out_file:
        with open(base_vcf) as in_handle:
            with open(tx_out_file, "w") as out_handle:
                for line in in_handle:
                    if line.startswith("#"):
                        passes = True
                    else:
                        passes = _passes_cortex_depth(line, min_depth)
                    if passes:
                        out_handle.write(line)
    return out_vcf

def _combine_variants(in_vcfs, out_file, ref_file, config):
    """Combine variant files, writing the header from the first non-empty input.

    in_vcfs is a list with each item starting with the chromosome regions,
    and ending with the input file.
    We sort by these regions to ensure the output file is in the expected order.
    """
    in_vcfs.sort()
    wrote_header = False
    with open(out_file, "w") as out_handle:
        for in_vcf in (x[-1] for x in in_vcfs):
            with open(in_vcf) as in_handle:
                header = list(itertools.takewhile(lambda x: x.startswith("#"),
                                                  in_handle))
                if not header[0].startswith("##fileformat=VCFv4"):
                    raise ValueError("Unexpected VCF file: %s" % in_vcf)
                for line in in_handle:
                    if not wrote_header:
                        wrote_header = True
                        out_handle.write("".join(header))
                    out_handle.write(line)
        if not wrote_header:
            out_handle.write("".join(header))
    return out_file

def _run_cortex_on_region(region, align_bam, ref_file, work_dir, out_file_base, config):
    """Run cortex on a specified chromosome start/end region.
    """
    kmers = [31, 51, 71]
    min_reads = 1750
    cortex_dir = config_utils.get_program("cortex", config, "dir")
    stampy_dir = config_utils.get_program("stampy", config, "dir")
    vcftools_dir = config_utils.get_program("vcftools", config, "dir")
    if cortex_dir is None or stampy_dir is None:
        raise ValueError("cortex_var requires path to pre-built cortex and stampy")
    region_str = apply("{0}-{1}-{2}".format, region)
    base_dir = safe_makedir(os.path.join(work_dir, region_str))
    try:
        out_vcf_base = os.path.join(base_dir, "{0}-{1}".format(
                    os.path.splitext(os.path.basename(out_file_base))[0], region_str))
        out_file = os.path.join(work_dir, os.path.basename("{0}.vcf".format(out_vcf_base)))
        if not file_exists(out_file):
            fastq = _get_fastq_in_region(region, align_bam, out_vcf_base)
            if _count_fastq_reads(fastq, min_reads) < min_reads:
                vcfutils.write_empty_vcf(out_file)
            else:
                local_ref, genome_size = _get_local_ref(region, ref_file, out_vcf_base)
                indexes = _index_local_ref(local_ref, cortex_dir, stampy_dir, kmers)
                cortex_out = _run_cortex(fastq, indexes, {"kmers": kmers, "genome_size": genome_size,
                                                          "sample": get_sample_name(align_bam)},
                                         out_vcf_base, {"cortex": cortex_dir, "stampy": stampy_dir,
                                                        "vcftools": vcftools_dir},
                                         config)
                if cortex_out:
                    _remap_cortex_out(cortex_out, region, out_file)
                else:
                    vcfutils.write_empty_vcf(out_file)
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
    return [region[0], int(region[1]), int(region[2]), out_file]

def _remap_cortex_out(cortex_out, region, out_file):
    """Remap coordinates in local cortex variant calls to the original global region.
    """
    def _remap_vcf_line(line, contig, start):
        parts = line.split("\t")
        if parts[0] == "" or parts[1] == "":
            return None
        parts[0] = contig
        try:
            parts[1] = str(int(parts[1]) + start)
        except ValueError:
            raise ValueError("Problem in {0} with \n{1}".format(
                    cortex_out, parts))
        return "\t".join(parts)
    def _not_filtered(line):
        parts = line.split("\t")
        return parts[6] == "PASS"
    contig, start, _ = region
    start = int(start)
    with open(cortex_out) as in_handle:
        with open(out_file, "w") as out_handle:
            for line in in_handle:
                if line.startswith("##fileDate"):
                    pass
                elif line.startswith("#"):
                    out_handle.write(line)
                elif _not_filtered(line):
                    update_line = _remap_vcf_line(line, contig, start)
                    if update_line:
                        out_handle.write(update_line)

def _run_cortex(fastq, indexes, params, out_base, dirs, config):
    """Run cortex_var run_calls.pl, producing a VCF variant file.
    """
    print out_base
    fastaq_index = "{0}.fastaq_index".format(out_base)
    se_fastq_index = "{0}.se_fastq".format(out_base)
    pe_fastq_index = "{0}.pe_fastq".format(out_base)
    reffasta_index = "{0}.list_ref_fasta".format(out_base)
    with open(se_fastq_index, "w") as out_handle:
        out_handle.write(fastq + "\n")
    with open(pe_fastq_index, "w") as out_handle:
        out_handle.write("")
    with open(fastaq_index, "w") as out_handle:
        out_handle.write("{0}\t{1}\t{2}\t{2}\n".format(params["sample"], se_fastq_index,
                                                       pe_fastq_index))
    with open(reffasta_index, "w") as out_handle:
        for x in indexes["fasta"]:
            out_handle.write(x + "\n")
    os.environ["PERL5LIB"] = "{0}:{1}:{2}".format(
        os.path.join(dirs["cortex"], "scripts/calling"),
        os.path.join(dirs["cortex"], "scripts/analyse_variants/bioinf-perl/lib"),
        os.environ.get("PERL5LIB", ""))
    kmers = sorted(params["kmers"])
    kmer_info = ["--first_kmer", str(kmers[0])]
    if len(kmers) > 1:
        kmer_info += ["--last_kmer", str(kmers[-1]),
                      "--kmer_step", str(kmers[1] - kmers[0])]
    subprocess.check_call(["perl", os.path.join(dirs["cortex"], "scripts", "calling", "run_calls.pl"),
                           "--fastaq_index", fastaq_index,
                           "--auto_cleaning", "yes", "--bc", "yes", "--pd", "yes",
                           "--outdir", os.path.dirname(out_base), "--outvcf", os.path.basename(out_base),
                           "--ploidy", str(config["algorithm"].get("ploidy", 2)),
                           "--stampy_hash", indexes["stampy"],
                           "--stampy_bin", os.path.join(dirs["stampy"], "stampy.py"),
                           "--refbindir", os.path.dirname(indexes["cortex"][0]),
                           "--list_ref_fasta",  reffasta_index,
                           "--genome_size", str(params["genome_size"]),
                           "--max_read_len", "30000",
                           #"--max_var_len", "4000",
                           "--format", "FASTQ", "--qthresh", "5", "--do_union", "yes",
                           "--mem_height", "17", "--mem_width", "100",
                           "--ref", "CoordinatesAndInCalling", "--workflow", "independent",
                           "--vcftools_dir", dirs["vcftools"],
                           "--logfile", "{0}.logfile,f".format(out_base)]
                          + kmer_info)
    final = glob.glob(os.path.join(os.path.dirname(out_base), "vcfs",
                                   "{0}*FINALcombined_BC*decomp.vcf".format(os.path.basename(out_base))))
    # No calls, need to setup an empty file
    if len(final) != 1:
        print "Did not find output VCF file for {0}".format(out_base)
        return None
    else:
        return final[0]

def _get_cortex_binary(kmer, cortex_dir):
    cortex_bin = None
    for check_bin in sorted(glob.glob(os.path.join(cortex_dir, "bin", "cortex_var_*"))):
        kmer_check = int(os.path.basename(check_bin).split("_")[2])
        if kmer_check >= kmer:
            cortex_bin = check_bin
            break
    assert cortex_bin is not None, \
        "Could not find cortex_var executable in %s for kmer %s" % (cortex_dir, kmer)
    return cortex_bin

def _index_local_ref(fasta_file, cortex_dir, stampy_dir, kmers):
    """Pre-index a generated local reference sequence with cortex_var and stampy.
    """
    base_out = os.path.splitext(fasta_file)[0]
    cindexes = []
    for kmer in kmers:
        out_file = "{0}.k{1}.ctx".format(base_out, kmer)
        if not file_exists(out_file):
            file_list = "{0}.se_list".format(base_out)
            with open(file_list, "w") as out_handle:
                out_handle.write(fasta_file + "\n")
            subprocess.check_call([_get_cortex_binary(kmer, cortex_dir),
                                   "--kmer_size", str(kmer), "--mem_height", "17",
                                   "--se_list", file_list, "--format", "FASTA",
                                   "--max_read_len", "30000",
			           "--sample_id", base_out,
                                   "--dump_binary", out_file])
        cindexes.append(out_file)
    if not file_exists("{0}.stidx".format(base_out)):
        subprocess.check_call([os.path.join(stampy_dir, "stampy.py"), "-G",
                               base_out, fasta_file])
        subprocess.check_call([os.path.join(stampy_dir, "stampy.py"), "-g",
                               base_out, "-H", base_out])
    return {"stampy": base_out,
            "cortex": cindexes,
            "fasta": [fasta_file]}

def _get_local_ref(region, ref_file, out_vcf_base):
    """Retrieve a local FASTA file corresponding to the specified region.
    """
    out_file = "{0}.fa".format(out_vcf_base)
    if not file_exists(out_file):
        with closing(pysam.Fastafile(ref_file)) as in_pysam:
            contig, start, end = region
            seq = in_pysam.fetch(contig, int(start), int(end))
            with open(out_file, "w") as out_handle:
                out_handle.write(">{0}-{1}-{2}\n{3}".format(contig, start, end,
                                                              str(seq)))
    with open(out_file) as in_handle:
        in_handle.readline()
        size = len(in_handle.readline().strip())
    return out_file, size

def _get_fastq_in_region(region, align_bam, out_base):
    """Retrieve fastq files in region as single end.
    Paired end is more complicated since pairs can map off the region, so focus
    on local only assembly since we've previously used paired information for mapping.
    """
    out_file = "{0}.fastq".format(out_base)
    if not file_exists(out_file):
        with closing(pysam.Samfile(align_bam, "rb")) as in_pysam:
            with file_transaction(out_file) as tx_out_file:
                with open(tx_out_file, "w") as out_handle:
                    contig, start, end = region
                    for read in in_pysam.fetch(contig, int(start), int(end)):
                        seq = Seq.Seq(read.seq)
                        qual = list(read.qual)
                        if read.is_reverse:
                            seq = seq.reverse_complement()
                            qual.reverse()
                        out_handle.write("@{name}\n{seq}\n+\n{qual}\n".format(
                                name=read.qname, seq=str(seq), qual="".join(qual)))
    return out_file

## Utility functions

def _count_fastq_reads(in_fastq, min_reads):
    """Count the number of fastq reads in a file, stopping after reaching min_reads.
    """
    with open(in_fastq) as in_handle:
        items = list(itertools.takewhile(lambda i : i <= min_reads,
                                         (i for i, _ in enumerate(FastqGeneralIterator(in_handle)))))
    return len(items)

def get_sample_name(align_bam):
    with closing(pysam.Samfile(align_bam, "rb")) as in_pysam:
        if "RG" in in_pysam.header:
            return in_pysam.header["RG"][0]["SM"]

########NEW FILE########
__FILENAME__ = coverage
"""Examine sequencing coverage, identifying transcripts lacking sufficient coverage for variant calling.

Handles identification of low coverage regions in defined genes of interest or the entire transcript.
"""
import collections
import copy
import os

import yaml

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.provenance import do

def _prep_coverage_file(species, covdir, config):
    """Ensure input coverage file is correct, handling special keywords for whole exome.
    Returns the input coverage file and keyword for special cases.
    """
    cov_file = config["algorithm"]["coverage"]
    cov_kw = None
    if cov_file == "exons":
        cov_kw = cov_file
        cov_file = os.path.join(covdir, "%s-%s.txt" % (species, cov_kw))
    else:
        cov_file = os.path.normpath(os.path.join(os.path.split(covdir)[0], cov_file))
        assert os.path.exists(cov_file), \
            "Did not find input file for coverage: %s" % cov_file
    return cov_file, cov_kw

def _prep_coverage_config(samples, config):
    """Create input YAML configuration and directories for running coverage assessment.
    """
    covdir = utils.safe_makedir(os.path.join(samples[0]["dirs"]["work"], "coverage"))
    name = samples[0]["name"][-1].replace(" ", "_")
    cur_covdir = utils.safe_makedir(os.path.join(covdir, name))
    out_file = os.path.join(cur_covdir, "coverage_summary.csv")
    config_file = os.path.join(cur_covdir, "coverage-in.yaml")
    species = samples[0]["genome_resources"]["aliases"]["ensembl"]
    cov_file, cov_kw = _prep_coverage_file(species, covdir, config)
    out = {"params": {"species": species,
                      "build": samples[0]["genome_build"],
                      "coverage": 13,
                      "transcripts": "canonical",
                      "block": {"min": 100, "distance": 10}},
           "regions": cov_file,
           "ref-file": os.path.abspath(samples[0]["sam_ref"]),
           "experiments": []
           }
    if cov_kw:
        out["params"]["regions"] = cov_kw
    for data in samples:
        out["experiments"].append({"name": data["name"][-1],
                                   "samples": [{"coverage": str(data["work_bam"])}]})
    with open(config_file, "w") as out_handle:
        yaml.safe_dump(out, out_handle, allow_unicode=False, default_flow_style=False)
    return config_file, out_file

def summary(samples, config):
    """Provide summary information on a single sample across regions of interest.
    """
    try:
        bc_jar = config_utils.get_jar("bcbio.coverage", config_utils.get_program("bcbio_coverage", config, "dir"))
    except ValueError:
        logger.warning("No coverage calculations: Did not find bcbio.coverage jar from system config")
        return [[x] for x in samples]
    config_file, out_file = _prep_coverage_config(samples, config)
    tmp_dir = utils.safe_makedir(os.path.join(os.path.dirname(out_file), "tmp"))
    resources = config_utils.get_resources("bcbio_coverage", config)
    config = copy.deepcopy(config)
    config["algorithm"]["memory_adjust"] = {"direction": "increase",
                                            "magnitude": config["algorithm"].get("num_cores", 1)}
    jvm_opts = config_utils.adjust_opts(resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"]), config)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            java_args = ["-Djava.io.tmpdir=%s" % tmp_dir, "-Djava.awt.headless=true"]
            cmd = ["java"] + jvm_opts + java_args + ["-jar", bc_jar, "multicompare", config_file,
                                                     tx_out_file, "-c", str(config["algorithm"].get("num_cores", 1))]
            do.run(cmd, "Summarizing coverage with bcbio.coverage", samples[0])
    out = []
    for x in samples:
        x["coverage"] = {"summary": out_file}
        out.append([x])
    return out

def summarize_samples(samples, run_parallel):
    """Provide summary information for sample coverage across regions of interest.
    """
    to_run = collections.defaultdict(list)
    extras = []
    for data in [x[0] for x in samples]:
        if ("coverage" in data["config"]["algorithm"] and
              data["genome_resources"].get("aliases", {}).get("ensembl")):
            to_run[(data["genome_build"], data["config"]["algorithm"]["coverage"])].append(data)
        else:
            extras.append([data])
    out = []
    if len(to_run) > 0:
        args = []
        for sample_group in to_run.itervalues():
            config = sample_group[0]["config"]
            args.append((sample_group, config))
        out.extend(run_parallel("coverage_summary", args))
    return out + extras

########NEW FILE########
__FILENAME__ = effects
"""Calculate potential effects of variations using external programs.

Supported:
  snpEff: http://sourceforge.net/projects/snpeff/
"""
import os
import csv
import glob

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, tools
from bcbio.provenance import do
from bcbio.variation import vcfutils

# ## snpEff variant effects

def snpeff_effects(data):
    """Annotate input VCF file with effects calculated by snpEff.
    """
    vcf_in = data["vrn_file"]
    if vcfutils.vcf_has_variants(vcf_in):
        vcf_file = _run_snpeff(vcf_in, "vcf", data)
        return vcf_file

def _snpeff_args_from_config(data):
    """Retrieve snpEff arguments supplied through input configuration.
    """
    config = data["config"]
    args = []
    # General supplied arguments
    resources = config_utils.get_resources("snpeff", config)
    if resources.get("options"):
        args += [str(x) for x in resources.get("options", [])]
    # cancer specific calling arguments
    if vcfutils.get_paired_phenotype(data):
        args += ["-cancer"]
    # Provide options tuned to reporting variants in clinical environments
    if config["algorithm"].get("clinical_reporting"):
        args += ["-canon", "-hgvs"]
    return args

def get_db(data):
    """Retrieve a snpEff database name and location relative to reference file.
    """
    snpeff_db = utils.get_in(data, ("genome_resources", "aliases", "snpeff"))
    snpeff_base_dir = None
    if snpeff_db:
        snpeff_base_dir = utils.get_in(data, ("reference", "snpeff", snpeff_db, "base"))
        if not snpeff_base_dir:
            ref_file = utils.get_in(data, ("reference", "fasta", "base"))
            snpeff_base_dir = utils.safe_makedir(os.path.normpath(os.path.join(
                os.path.dirname(os.path.dirname(ref_file)), "snpeff")))
            # back compatible retrieval of genome from installation directory
            if "config" in data and not os.path.exists(os.path.join(snpeff_base_dir, snpeff_db)):
                snpeff_base_dir, snpeff_db = _installed_snpeff_genome(snpeff_db, data["config"])
    return snpeff_db, snpeff_base_dir

def get_snpeff_files(data):
    try:
        snpeff_db, datadir = get_db(data)
    except ValueError:
        snpeff_db = None
    if snpeff_db:
        return {snpeff_db: {"base": datadir,
                            "indexes": glob.glob(os.path.join(datadir, snpeff_db, "*"))}}
    else:
        return {}

def get_cmd(cmd_name, datadir, config):
    """Retrieve snpEff base command line, handling command line and jar based installs.
    """
    resources = config_utils.get_resources("snpeff", config)
    memory = " ".join(resources.get("jvm_opts", ["-Xms750m", "-Xmx5g"]))
    try:
        snpeff = config_utils.get_program("snpeff", config)
        cmd = "{snpeff} {memory} {cmd_name} -dataDir {datadir}"
    except config_utils.CmdNotFound:
        snpeff_jar = config_utils.get_jar("snpEff",
                                          config_utils.get_program("snpeff", config, "dir"))
        config_file = "%s.config" % os.path.splitext(snpeff_jar)[0]
        cmd = "java {memory} -jar {snpeff_jar} {cmd_name} -c {config_file} -dataDir {datadir}"
    return cmd.format(**locals())

def _run_snpeff(snp_in, out_format, data):
    snpeff_db, datadir = get_db(data)
    assert datadir is not None, \
        "Did not find snpEff resources in genome configuration: %s" % data["genome_resources"]
    assert os.path.exists(os.path.join(datadir, snpeff_db)), \
        "Did not find %s snpEff genome data in %s" % (snpeff_db, datadir)
    snpeff_cmd = get_cmd("eff", datadir, data["config"])
    ext = utils.splitext_plus(snp_in)[1] if out_format == "vcf" else ".tsv"
    out_file = "%s-effects%s" % (utils.splitext_plus(snp_in)[0], ext)
    if not utils.file_exists(out_file):
        config_args = " ".join(_snpeff_args_from_config(data))
        if ext.endswith(".gz"):
            bgzip_cmd = "| %s -c" % tools.get_bgzip_cmd(data["config"])
        else:
            bgzip_cmd = ""
        with file_transaction(out_file) as tx_out_file:
            cmd = ("{snpeff_cmd} {config_args} -noLog -1 -i vcf -o {out_format} "
                   "{snpeff_db} {snp_in} {bgzip_cmd} > {tx_out_file}")
            do.run(cmd.format(**locals()), "snpEff effects", data)
    if ext.endswith(".gz"):
        out_file = vcfutils.bgzip_and_index(out_file, data["config"])
    return out_file

# ## back-compatibility

def _find_snpeff_datadir(config_file):
    with open(config_file) as in_handle:
        for line in in_handle:
            if line.startswith("data_dir"):
                data_dir = config_utils.expand_path(line.split("=")[-1].strip())
                if not data_dir.startswith("/"):
                    data_dir = os.path.join(os.path.dirname(config_file), data_dir)
                return data_dir
    raise ValueError("Did not find data directory in snpEff config file: %s" % config_file)

def _installed_snpeff_genome(base_name, config):
    """Find the most recent installed genome for snpEff with the given name.
    """
    snpeff_config_file = os.path.join(config_utils.get_program("snpeff", config, "dir"),
                                      "snpEff.config")
    data_dir = _find_snpeff_datadir(snpeff_config_file)
    dbs = [d for d in sorted(glob.glob(os.path.join(data_dir, "%s*" % base_name)), reverse=True)
           if os.path.isdir(d)]
    if len(dbs) == 0:
        raise ValueError("No database found in %s for %s" % (data_dir, base_name))
    else:
        return data_dir, os.path.split(dbs[0])[-1]

########NEW FILE########
__FILENAME__ = ensemble
"""Ensemble methods that create consensus calls from multiple approaches.

This handles merging calls produced by multiple calling methods or
technologies into a single consolidated callset. Uses the bcbio.variation
toolkit: https://github.com/chapmanb/bcbio.variation and bcbio.variation.recall:
https://github.com/chapmanb/bcbio.variation.recall
"""
import collections
import copy
import glob
import os

import yaml

from bcbio import utils
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.variation import effects, population, validate

def combine_calls(batch_id, samples, data):
    """Combine multiple callsets into a final set of merged calls.
    """
    logger.info("Ensemble consensus calls for {0}: {1}".format(
        batch_id, ",".join(x["variantcaller"] for x in samples[0]["variants"])))
    edata = copy.deepcopy(data)
    base_dir = utils.safe_makedir(os.path.join(edata["dirs"]["work"], "ensemble", batch_id))
    caller_names, vrn_files, bam_files = _organize_variants(samples, batch_id)
    if "caller" in edata["config"]["algorithm"]["ensemble"]:
        callinfo = _run_ensemble_w_caller(batch_id, vrn_files, bam_files, base_dir, edata)
    else:
        config_file = _write_config_file(batch_id, caller_names, base_dir, edata)
        callinfo = _run_ensemble(batch_id, vrn_files, config_file, base_dir,
                                 edata["sam_ref"], edata["config"])
    edata["config"]["algorithm"]["variantcaller"] = "ensemble"
    edata["vrn_file"] = callinfo["vrn_file"]
    edata["ensemble_bed"] = callinfo["bed_file"]
    callinfo["validate"] = validate.compare_to_rm(edata)[0][0].get("validate")
    return [[batch_id, callinfo]]

def combine_calls_parallel(samples, run_parallel):
    """Combine calls using batched Ensemble approach.
    """
    batch_groups, extras = _group_by_batches(samples, _has_ensemble)
    out = []
    if batch_groups:
        processed = run_parallel("combine_calls", ((b, xs, xs[0]) for b, xs in batch_groups.iteritems()))
        for batch_id, callinfo in processed:
            for data in batch_groups[batch_id]:
                data["variants"].insert(0, callinfo)
                out.append([data])
    return out + extras

def _has_ensemble(data):
    return len(data["variants"]) > 1 and "ensemble" in data["config"]["algorithm"]

def _group_by_batches(samples, check_fn):
    """Group calls by batches, processing families together during ensemble calling.
    """
    batch_groups = collections.defaultdict(list)
    extras = []
    for data in [x[0] for x in samples]:
        if check_fn(data):
            batch = data.get("metadata", {}).get("batch")
            if batch:
                batch_groups[batch].append(data)
            else:
                assert data["name"][-1] not in batch_groups
                batch_groups[data["name"][-1]] = [data]
        else:
            extras.append([data])
    return batch_groups, extras

def _organize_variants(samples, batch_id):
    """Retrieve variant calls for all samples, merging batched samples into single VCF.
    """
    bam_files = set([])
    caller_names = [x["variantcaller"] for x in samples[0]["variants"]]
    calls = collections.defaultdict(list)
    for data in samples:
        if "work_bam" in data:
            bam_files.add(data["work_bam"])
        for vrn in data["variants"]:
            calls[vrn["variantcaller"]].append(vrn["vrn_file"])
    data = samples[0]
    vrn_files = []
    for caller in caller_names:
        fnames = calls[caller]
        if len(fnames) == 1:
            vrn_files.append(fnames[0])
        else:
            vrn_files.append(population.get_multisample_vcf(fnames, batch_id, caller, data))
    return caller_names, vrn_files, list(bam_files)

def _bcbio_variation_ensemble(vrn_files, out_file, ref_file, config_file, base_dir, config):
    """Run a variant comparison using the bcbio.variation toolkit, given an input configuration.
    """
    tmp_dir = utils.safe_makedir(os.path.join(base_dir, "tmp"))
    bv_jar = config_utils.get_jar("bcbio.variation",
                                  config_utils.get_program("bcbio_variation", config, "dir"))
    resources = config_utils.get_resources("bcbio_variation", config)
    jvm_opts = resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"])
    java_args = ["-Djava.io.tmpdir=%s" % tmp_dir]
    cmd = ["java"] + jvm_opts + java_args + ["-jar", bv_jar, "variant-ensemble", config_file,
                                             ref_file, out_file] + vrn_files
    with utils.chdir(base_dir):
        do.run(cmd, "Ensemble calling: %s" % os.path.basename(base_dir))

def _run_ensemble(batch_id, vrn_files, config_file, base_dir, ref_file, config):
    """Run an ensemble call using merging and SVM-based approach in bcbio.variation
    """
    out_vcf_file = os.path.join(base_dir, "{0}-ensemble.vcf".format(batch_id))
    out_bed_file = os.path.join(base_dir, "{0}-callregions.bed".format(batch_id))
    work_dir = "%s-work" % os.path.splitext(out_vcf_file)[0]
    if not utils.file_exists(out_vcf_file):
        _bcbio_variation_ensemble(vrn_files, out_vcf_file, ref_file, config_file,
                                  base_dir, config)
        if not utils.file_exists(out_vcf_file):
            base_vcf = glob.glob(os.path.join(work_dir, "prep", "*-cfilter.vcf"))[0]
            utils.symlink_plus(base_vcf, out_vcf_file)
    if not utils.file_exists(out_bed_file):
        multi_beds = glob.glob(os.path.join(work_dir, "prep", "*-multicombine.bed"))
        if len(multi_beds) > 0:
            utils.symlink_plus(multi_beds[0], out_bed_file)
    return {"variantcaller": "ensemble",
            "vrn_file": out_vcf_file,
            "bed_file": out_bed_file if os.path.exists(out_bed_file) else None}

def _write_config_file(batch_id, caller_names, base_dir, data):
    """Write YAML configuration to generate an ensemble set of combined calls.
    """
    config_dir = utils.safe_makedir(os.path.join(base_dir, "config"))
    config_file = os.path.join(config_dir, "{0}-ensemble.yaml".format(batch_id))
    algorithm = data["config"]["algorithm"]
    econfig = {"ensemble": algorithm["ensemble"],
               "names": caller_names,
               "prep-inputs": False}
    intervals = validate.get_analysis_intervals(data)
    if intervals:
        econfig["intervals"] = os.path.abspath(intervals)
    with open(config_file, "w") as out_handle:
        yaml.safe_dump(econfig, out_handle, allow_unicode=False, default_flow_style=False)
    return config_file

def _run_ensemble_w_caller(batch_id, vrn_files, bam_files, base_dir, edata):
    """Run ensemble method using a variant caller to handle re-calling the inputs.

    Uses bcbio.variation.recall method plus an external variantcaller.
    """
    out_vcf_file = os.path.join(base_dir, "{0}-ensemble.vcf".format(batch_id))
    if not utils.file_exists(out_vcf_file):
        caller = edata["config"]["algorithm"]["ensemble"]["caller"]
        cmd = [config_utils.get_program("bcbio-variation-recall", edata["config"]),
               "ensemble", "--cores=%s" % edata["config"]["algorithm"].get("num_cores", 1),
               "--caller=%s" % caller,
               out_vcf_file, edata["sam_ref"]] + vrn_files + bam_files
        do.run(cmd, "Ensemble calling with %s: %s" % (caller, batch_id))
    in_data = copy.deepcopy(edata)
    in_data["vrn_file"] = out_vcf_file
    effects_vcf = effects.snpeff_effects(in_data)
    return {"variantcaller": "ensemble",
            "vrn_file": effects_vcf,
            "bed_file": None}

########NEW FILE########
__FILENAME__ = freebayes
"""Bayesian variant calling with FreeBayes.

http://bioinformatics.bc.edu/marthlab/FreeBayes
"""

from collections import namedtuple
import os
import shutil

try:
    import vcf
except ImportError:
    vcf = None

from bcbio import bam, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.provenance import do
from bcbio.variation import annotation, ploidy
from bcbio.variation.vcfutils import get_paired_bams, is_paired_analysis, bgzip_and_index

def region_to_freebayes(region):
    if isinstance(region, (list, tuple)):
        chrom, start, end = region
        return "%s:%s..%s" % (chrom, start, end)
    else:
        return region

def _freebayes_options_from_config(items, config, out_file, region=None):
    opts = []
    opts += ["--ploidy", str(ploidy.get_ploidy(items, region))]

    variant_regions = utils.get_in(config, ("algorithm", "variant_regions"))
    target = subset_variant_regions(variant_regions, region, out_file, items)
    if target:
        if isinstance(target, basestring) and os.path.isfile(target):
            opts += ["--targets", target]
        else:
            opts += ["--region", region_to_freebayes(target)]
    resources = config_utils.get_resources("freebayes", config)
    if resources.get("options"):
        opts += resources["options"]
    if "--min-alternate-fraction" not in " ".join(opts) and "-F" not in " ".join(opts):
        # add minimum reportable allele frequency, for which FreeBayes defaults to 20
         min_af = float(utils.get_in(config, ("algorithm",
                                              "min_allele_fraction"),20)) / 100.0
         opts += ["--min-alternate-fraction", str(min_af)]
    return opts

def run_freebayes(align_bams, items, ref_file, assoc_files, region=None,
                  out_file=None):
    """Run FreeBayes variant calling, either paired tumor/normal or germline calling.
    """
    if is_paired_analysis(align_bams, items):
        call_file = _run_freebayes_paired(align_bams, items, ref_file,
                                          assoc_files, region, out_file)
    else:
        call_file = _run_freebayes_caller(align_bams, items, ref_file,
                                          assoc_files, region, out_file)

    return call_file

def _run_freebayes_caller(align_bams, items, ref_file, assoc_files,
                          region=None, out_file=None):
    """Detect SNPs and indels with FreeBayes.

    Performs post-filtering to remove very low quality variants which
    can cause issues feeding into GATK. Breaks variants into individual
    allelic primitives for analysis and evaluation.
    """
    config = items[0]["config"]
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % os.path.splitext(align_bams[0])[0]
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            for align_bam in align_bams:
                bam.index(align_bam, config)
            freebayes = config_utils.get_program("freebayes", config)
            vcffilter = config_utils.get_program("vcffilter", config)
            vcfallelicprimitives = config_utils.get_program("vcfallelicprimitives", config)
            vcfstreamsort = config_utils.get_program("vcfstreamsort", config)
            input_bams = " ".join("-b %s" % x for x in align_bams)
            opts = " ".join(_freebayes_options_from_config(items, config, out_file, region))
            # Recommended options from 1000 genomes low-complexity evaluation
            # https://groups.google.com/d/msg/freebayes/GvxIzjcpbas/1G6e3ArxQ4cJ
            opts += " --min-repeat-entropy 1 --experimental-gls"
            compress_cmd = "| bgzip -c" if out_file.endswith("gz") else ""
            cmd = ("{freebayes} -f {ref_file} {input_bams} {opts} | "
                   "{vcffilter} -f 'QUAL > 5' -s | {vcfallelicprimitives} | {vcfstreamsort} "
                   "{compress_cmd} > {tx_out_file}")
            do.run(cmd.format(**locals()), "Genotyping with FreeBayes", {})
    ann_file = annotation.annotate_nongatk_vcf(out_file, align_bams,
                                               assoc_files["dbsnp"],
                                               ref_file, config)
    return ann_file

def _run_freebayes_paired(align_bams, items, ref_file, assoc_files,
                          region=None, out_file=None):
    """Detect SNPs and indels with FreeBayes.

    This is used for paired tumor / normal samples.
    """
    config = items[0]["config"]
    if out_file is None:
        out_file = "%s-paired-variants.vcf.gz" % os.path.splitext(align_bams[0])[0]
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            paired = get_paired_bams(align_bams, items)
            if not paired.normal_bam:
                raise ValueError("Require both tumor and normal BAM files for FreeBayes cancer calling")

            vcfsamplediff = config_utils.get_program("vcfsamplediff", config)
            vcffilter = config_utils.get_program("vcffilter", config)
            freebayes = config_utils.get_program("freebayes", config)
            opts = " ".join(_freebayes_options_from_config(items, config, out_file, region))
            opts += " -f {}".format(ref_file)
            if "--min-alternate-fraction" not in opts and "-F" not in opts:
                # add minimum reportable allele frequency
                # FreeBayes defaults to 20%, but use 10% by default for the
                # tumor case
                min_af = float(utils.get_in(paired.tumor_config, ("algorithm",
                                                                  "min_allele_fraction"),10)) / 100.0
                opts += " --min-alternate-fraction %s" % min_af
            # NOTE: The first sample name in the vcfsamplediff call is
            # the one supposed to be the *germline* one

            # NOTE: -s in vcfsamplediff (strict checking: i.e., require no
            # reads in the germline to call somatic) is not used as it is
            # too stringent
            compress_cmd = "| bgzip -c" if out_file.endswith("gz") else ""
            cl = ("{freebayes} --pooled-discrete --genotype-qualities "
                  "{opts} {paired.tumor_bam} {paired.normal_bam} "
                  "| {vcffilter} -f 'QUAL > 1' -s "
                  "| {vcfsamplediff} VT {paired.normal_name} {paired.tumor_name} - "
                  "{compress_cmd} >  {tx_out_file}")
            bam.index(paired.tumor_bam, config)
            bam.index(paired.normal_bam, config)
            do.run(cl.format(**locals()), "Genotyping paired variants with FreeBayes", {})
    fix_somatic_calls(out_file, config)
    ann_file = annotation.annotate_nongatk_vcf(out_file, align_bams,
                                               assoc_files["dbsnp"], ref_file,
                                               config)
    return ann_file


def _move_vcf(orig_file, new_file):
    """Move a VCF file with associated index.
    """
    for ext in ["", ".idx", ".tbi"]:
        to_move = orig_file + ext
        if os.path.exists(to_move):
            shutil.move(to_move, new_file + ext)

def _clean_freebayes_output(line):
    """Clean FreeBayes output to make post-processing with GATK happy.

    XXX Not applied on recent versions which fix issues to be more compatible
    with bgzip output, but retained in case of need.

    - Remove lines from FreeBayes outputs where REF/ALT are identical:
      2       22816178        .       G       G       0.0339196
      or there are multiple duplicate alleles:
      4       60594753        .       TGAAA   T,T
    - Remove Type=Int specifications which are not valid VCF and GATK chokes
      on.
    """
    if line.startswith("#"):
        line = line.replace("Type=Int,D", "Type=Integer,D")
        return line
    else:
        parts = line.split("\t")
        alleles = [x.strip() for x in parts[4].split(",")] + [parts[3].strip()]
        if len(alleles) == len(set(alleles)):
            return line
    return None

def clean_vcf_output(orig_file, clean_fn, name="clean"):
    """Provide framework to clean a file in-place, with the specified clean
    function.
    """
    base, ext = utils.splitext_plus(orig_file)
    out_file = "{0}-{1}{2}".format(base, name, ext)
    if not utils.file_exists(out_file):
        with open(orig_file) as in_handle:
            with file_transaction(out_file) as tx_out_file:
                with open(tx_out_file, "w") as out_handle:
                    for line in in_handle:
                        update_line = clean_fn(line)
                        if update_line:
                            out_handle.write(update_line)
        _move_vcf(orig_file, "{0}.orig".format(orig_file))
        _move_vcf(out_file, orig_file)
        with open(out_file, "w") as out_handle:
            out_handle.write("Moved to {0}".format(orig_file))


def fix_somatic_calls(in_file, config):
    """Fix somatic variant output, standardize it to the SOMATIC flag.
    """
    if vcf is None:
        raise ImportError("Require PyVCF for manipulating cancer VCFs")

    # HACK: Needed to replicate the structure used by PyVCF
    Info = namedtuple('Info', ['id', 'num', 'type', 'desc'])
    somatic_info = Info(id='SOMATIC', num=0, type='Flag', desc='Somatic event')

    # NOTE: PyVCF will write an uncompressed VCF
    base, ext = utils.splitext_plus(in_file)
    name = "somaticfix"
    out_file = "{0}-{1}{2}".format(base, name, ".vcf")

    if utils.file_exists(in_file):
        reader = vcf.VCFReader(filename=in_file)
        # Add info to the header of the reader
        reader.infos["SOMATIC"] = somatic_info

        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "wb") as handle:
                writer = vcf.VCFWriter(handle, template=reader)
                for record in reader:
                    # Handle FreeBayes
                    if "VT" in record.INFO:
                        if record.INFO["VT"] == "somatic":
                            record.add_info("SOMATIC", True)
                        # Discard old record
                        del record.INFO["VT"]

                    writer.write_record(record)

        # Re-compress the file
        out_file = bgzip_and_index(out_file, config)
        _move_vcf(in_file, "{0}.orig".format(in_file))
        _move_vcf(out_file, in_file)
        with open(out_file, "w") as out_handle:
            out_handle.write("Moved to {0}".format(in_file))

########NEW FILE########
__FILENAME__ = gatk
"""GATK variant calling -- HaplotypeCaller and UnifiedGenotyper.
"""
from distutils.version import LooseVersion

from bcbio import bam, broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.variation.realign import has_aligned_reads
from bcbio.variation import annotation, bamprep, ploidy, vcfutils

def _shared_gatk_call_prep(align_bams, items, ref_file, dbsnp, region, out_file):
    """Shared preparation work for GATK variant calling.
    """
    config = items[0]["config"]
    broad_runner = broad.runner_from_config(config)
    broad_runner.run_fn("picard_index_ref", ref_file)
    for x in align_bams:
        bam.index(x, config)
    # GATK can only downsample to a minimum of 200
    coverage_depth_max = max(200, utils.get_in(config, ("algorithm", "coverage_depth_max"), 10000))
    coverage_depth_min = utils.get_in(config, ("algorithm", "coverage_depth_min"), 4)
    variant_regions = config["algorithm"].get("variant_regions", None)
    confidence = "4.0" if coverage_depth_min < 4 else "30.0"
    region = subset_variant_regions(variant_regions, region, out_file, items)

    params = ["-R", ref_file,
              "--standard_min_confidence_threshold_for_calling", confidence,
              "--standard_min_confidence_threshold_for_emitting", confidence,
              "--downsample_to_coverage", str(coverage_depth_max),
              "--downsampling_type", "BY_SAMPLE",
              ]
    for a in annotation.get_gatk_annotations(config):
        params += ["--annotation", a]
    for x in align_bams:
        params += ["-I", x]
    if dbsnp:
        params += ["--dbsnp", dbsnp]
    if region:
        params += ["-L", bamprep.region_to_gatk(region), "--interval_set_rule", "INTERSECTION"]
    return broad_runner, params

def unified_genotyper(align_bams, items, ref_file, assoc_files,
                       region=None, out_file=None):
    """Perform SNP genotyping on the given alignment file.
    """
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % utils.splitext_plus(align_bams[0])[0]
    if not utils.file_exists(out_file):
        config = items[0]["config"]
        broad_runner, params = \
            _shared_gatk_call_prep(align_bams, items, ref_file, assoc_files["dbsnp"],
                                   region, out_file)
        if (not isinstance(region, (list, tuple)) and
                not all(has_aligned_reads(x, region) for x in align_bams)):
            vcfutils.write_empty_vcf(out_file, config)
        else:
            with file_transaction(out_file) as tx_out_file:
                params += ["-T", "UnifiedGenotyper",
                           "-o", tx_out_file,
                           "-ploidy", (str(ploidy.get_ploidy(items, region))
                                       if broad_runner.gatk_type() == "restricted" else "2"),
                           "--genotype_likelihoods_model", "BOTH"]
                broad_runner.run_gatk(params)
    return out_file

def haplotype_caller(align_bams, items, ref_file, assoc_files,
                       region=None, out_file=None):
    """Call variation with GATK's HaplotypeCaller.

    This requires the full non open-source version of GATK.
    """
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % utils.splitext_plus(align_bams[0])[0]
    if not utils.file_exists(out_file):
        config = items[0]["config"]
        broad_runner, params = \
            _shared_gatk_call_prep(align_bams, items, ref_file, assoc_files["dbsnp"],
                                   region, out_file)
        assert broad_runner.gatk_type() == "restricted", \
            "Require full version of GATK 2.4+ for haplotype calling"
        if not all(has_aligned_reads(x, region) for x in align_bams):
            vcfutils.write_empty_vcf(out_file, config)
        else:
            with file_transaction(out_file) as tx_out_file:
                params += ["-T", "HaplotypeCaller",
                           "-o", tx_out_file,
                           "--annotation", "ClippingRankSumTest",
                           "--annotation", "DepthPerSampleHC"]
                # Enable hardware based optimizations in GATK 3.1+
                if LooseVersion(broad_runner.gatk_major_version()) >= LooseVersion("3.1"):
                    params += ["--pair_hmm_implementation", "VECTOR_LOGLESS_CACHING"]
                broad_runner.new_resources("gatk-haplotype")
                broad_runner.run_gatk(params)
    return out_file

########NEW FILE########
__FILENAME__ = gatkfilter
"""Perform GATK based filtering, perferring variant quality score recalibration.

Performs hard filtering when VQSR fails on smaller sets of variant calls.
"""
from distutils.version import LooseVersion
import os

from bcbio import broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.variation import vcfutils, vfilter

def run(call_file, ref_file, vrn_files, data):
    """Run filtering on the input call file, handling SNPs and indels separately.
    """
    snp_file, indel_file = vcfutils.split_snps_indels(call_file, ref_file, data["config"])
    snp_filter_file = _variant_filtration(snp_file, ref_file, vrn_files, data, "SNP",
                                          vfilter.gatk_snp_hard)
    indel_filter_file = _variant_filtration(indel_file, ref_file, vrn_files, data, "INDEL",
                                            vfilter.gatk_indel_hard)
    orig_files = [snp_filter_file, indel_filter_file]
    out_file = "%scombined.vcf.gz" % os.path.commonprefix(orig_files)
    return vcfutils.combine_variant_files(orig_files, out_file, ref_file, data["config"])

def _apply_vqsr(in_file, ref_file, recal_file, tranch_file,
                sensitivity_cutoff, filter_type, data):
    """Apply VQSR based on the specified tranche, returning a filtered VCF file.
    """
    broad_runner = broad.runner_from_config(data["config"])
    base, ext = utils.splitext_plus(in_file)
    out_file = "{base}-{filter}filter{ext}".format(base=base, ext=ext,
                                                   filter=filter_type)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "ApplyRecalibration",
                      "-R", ref_file,
                      "--input", in_file,
                      "--out", tx_out_file,
                      "--ts_filter_level", sensitivity_cutoff,
                      "--tranches_file", tranch_file,
                      "--recal_file", recal_file,
                      "--mode", filter_type]
            broad_runner.run_gatk(params)
    return out_file

def _get_vqsr_training(filter_type, vrn_files):
    """Return parameters for VQSR training, handling SNPs and Indels.
    """
    params = []
    if filter_type == "SNP":
        for name, train_info in [("train_hapmap", "known=false,training=true,truth=true,prior=15.0"),
                                 ("train_omni", "known=false,training=true,truth=true,prior=12.0"),
                                 ("train_1000g", "known=false,training=true,truth=false,prior=10.0"),
                                 ("dbsnp", "known=true,training=false,truth=false,prior=2.0")]:
            if name in vrn_files:
                assert name in vrn_files, "Missing VQSR SNP training dataset %s" % name
                params.extend(["-resource:%s,VCF,%s" % (name.replace("train_", ""), train_info),
                               vrn_files[name]])
    elif filter_type == "INDEL":
        assert "train_indels" in vrn_files, "Need indel training file specified"
        params.extend(["--maxGaussians", "4"])
        params.extend(
            ["-resource:mills,VCF,known=true,training=true,truth=true,prior=12.0",
             vrn_files["train_indels"]])
    else:
        raise ValueError("Unexpected filter type for VQSR: %s" % filter_type)
    return params

def _get_vqsr_annotations(filter_type):
    """Retrieve appropriate annotations to use for VQSR based on filter type.
    """
    if filter_type == "SNP":
        return ["DP", "QD", "FS", "MQRankSum", "ReadPosRankSum"]
    else:
        assert filter_type == "INDEL"
        return ["DP", "FS", "MQRankSum", "ReadPosRankSum"]

def _run_vqsr(in_file, ref_file, vrn_files, sensitivity_cutoff, filter_type, data):
    """Run variant quality score recalibration.
    """
    cutoffs = ["100.0", "99.99", "99.98", "99.97", "99.96", "99.95", "99.94", "99.93", "99.92", "99.91",
               "99.9", "99.8", "99.7", "99.6", "99.5", "99.0", "98.0", "90.0"]
    if sensitivity_cutoff not in cutoffs:
        cutoffs.append(sensitivity_cutoff)
        cutoffs.sort()
    broad_runner = broad.runner_from_config(data["config"])
    base = utils.splitext_plus(in_file)[0]
    recal_file = "%s.recal" % base
    tranches_file = "%s.tranches" % base
    if not utils.file_exists(recal_file):
        with file_transaction(recal_file, tranches_file) as (tx_recal, tx_tranches):
            params = ["-T", "VariantRecalibrator",
                      "-R", ref_file,
                      "--input", in_file,
                      "--mode", filter_type,
                      "--recal_file", tx_recal,
                      "--tranches_file", tx_tranches]
            for cutoff in cutoffs:
                params += ["-tranche", str(cutoff)]
            params += _get_vqsr_training(filter_type, vrn_files)
            for a in _get_vqsr_annotations(filter_type):
                params += ["-an", a]
            try:
                broad_runner.new_resources("gatk-vqsr")
                broad_runner.run_gatk(params, log_error=False)
            except:  # Can fail to run if not enough values are present to train.
                return None, None
    return recal_file, tranches_file

# ## SNP and indel specific variant filtration

def _already_hard_filtered(in_file, filter_type):
    """Check if we have a pre-existing hard filter file from previous VQSR failure.
    """
    filter_file = "%s-filter%s.vcf.gz" % (utils.splitext_plus(in_file)[0], filter_type)
    return utils.file_exists(filter_file)

def _variant_filtration(in_file, ref_file, vrn_files, data, filter_type,
                        hard_filter_fn):
    """Filter SNP and indel variant calls using GATK best practice recommendations.
    """
    # hard filter if configuration indicates too little data or already finished a hard filtering
    if not config_utils.use_vqsr([data["config"]["algorithm"]]) or _already_hard_filtered(in_file, filter_type):
        return hard_filter_fn(in_file, data)
    else:
        sensitivities = {"INDEL": "98.0", "SNP": "99.97"}
        recal_file, tranches_file = _run_vqsr(in_file, ref_file, vrn_files,
                                              sensitivities[filter_type], filter_type, data)
        if recal_file is None:  # VQSR failed
            logger.info("VQSR failed due to lack of training data. Using hard filtering.")
            return hard_filter_fn(in_file, data)
        else:
            return _apply_vqsr(in_file, ref_file, recal_file, tranches_file,
                               sensitivities[filter_type], filter_type, data)

########NEW FILE########
__FILENAME__ = genotype
"""High level parallel SNP and indel calling using multiple variant callers.
"""
import os
import collections
import copy

from bcbio import utils
from bcbio.distributed.split import grouped_parallel_split_combine
from bcbio.pipeline import region
from bcbio.variation import gatk, gatkfilter, multi, phasing, ploidy, vfilter

# ## Variant filtration -- shared functionality

def variant_filtration(call_file, ref_file, vrn_files, data):
    """Filter variant calls using Variant Quality Score Recalibration.

    Newer GATK with Haplotype calling has combined SNP/indel filtering.
    """
    caller = data["config"]["algorithm"].get("variantcaller")
    call_file = ploidy.filter_vcf_by_sex(call_file, data)
    if caller in ["freebayes"]:
        return vfilter.freebayes(call_file, ref_file, vrn_files, data)
    elif caller in ["gatk", "gatk-haplotype"]:
        return gatkfilter.run(call_file, ref_file, vrn_files, data)
    # no additional filtration for callers that filter as part of call process
    else:
        return call_file

# ## High level functionality to run genotyping in parallel

def get_variantcaller(data):
    if data.get("align_bam"):
        return data["config"]["algorithm"].get("variantcaller", "gatk")

def combine_multiple_callers(samples):
    """Collapse together variant calls from multiple approaches into single data item with `variants`.
    """
    by_bam = collections.OrderedDict()
    for data in (x[0] for x in samples):
        work_bam = utils.get_in(data, ("combine", "work_bam", "out"), data.get("align_bam"))
        variantcaller = get_variantcaller(data)
        key = (data["description"], work_bam)
        try:
            by_bam[key][variantcaller] = data
        except KeyError:
            by_bam[key] = {variantcaller: data}
    out = []
    for grouped_calls in [d.values() for d in by_bam.values()]:
        ready_calls = [{"variantcaller": get_variantcaller(x),
                        "vrn_file": x.get("vrn_file"),
                        "vrn_file_batch": x.get("vrn_file_batch"),
                        "validate": x.get("validate")}
                       for x in grouped_calls]
        final = grouped_calls[0]
        def orig_variantcaller_order(x):
            return final["config"]["algorithm"]["orig_variantcaller"].index(x["variantcaller"])
        if len(ready_calls) > 1 and "orig_variantcaller" in final["config"]["algorithm"]:
            final["variants"] = sorted(ready_calls, key=orig_variantcaller_order)
            final["config"]["algorithm"]["variantcaller"] = final["config"]["algorithm"].pop("orig_variantcaller")
        else:
            final["variants"] = ready_calls
        final.pop("vrn_file_batch", None)
        out.append([final])
    return out

def _split_by_ready_regions(ext, file_key, dir_ext_fn):
    """Organize splits based on regions generated by parallel_prep_region.
    """
    def _do_work(data):
        if "region" in data:
            name = data["group"][0] if "group" in data else data["description"]
            out_dir = os.path.join(data["dirs"]["work"], dir_ext_fn(data))
            out_file = os.path.join(out_dir, "%s%s" % (name, ext))
            assert isinstance(data["region"], (list, tuple))
            out_parts = []
            for i, r in enumerate(data["region"]):
                out_region_dir = os.path.join(out_dir, r[0])
                out_region_file = os.path.join(out_region_dir,
                                               "%s-%s%s" % (name, region.to_safestr(r), ext))
                work_bams = []
                for xs in data["region_bams"]:
                    if len(xs) == 1:
                        work_bams.append(xs[0])
                    else:
                        work_bams.append(xs[i])
                for work_bam in work_bams:
                    assert os.path.exists(work_bam), work_bam
                out_parts.append((r, work_bams, out_region_file))
            return out_file, out_parts
        else:
            return None, []
    return _do_work

def _collapse_by_bam_variantcaller(samples):
    """Collapse regions to a single representative by BAM input and variant caller.
    """
    by_bam = collections.OrderedDict()
    for data in (x[0] for x in samples):
        work_bam = utils.get_in(data, ("combine", "work_bam", "out"), data.get("align_bam"))
        variantcaller = get_variantcaller(data)
        if isinstance(work_bam, list):
            work_bam = tuple(work_bam)
        key = (data["description"], work_bam, variantcaller)
        try:
            by_bam[key].append(data)
        except KeyError:
            by_bam[key] = [data]
    out = []
    for grouped_data in by_bam.values():
        cur = grouped_data[0]
        cur.pop("region", None)
        region_bams = cur.pop("region_bams", None)
        if region_bams and len(region_bams[0]) > 1:
            cur.pop("work_bam", None)
        out.append([cur])
    return out

def parallel_variantcall_region(samples, run_parallel):
    """Perform variant calling and post-analysis on samples by region.
    """
    to_process = []
    extras = []
    for x in samples:
        added = False
        for add in handle_multiple_variantcallers(x):
            added = True
            to_process.append(add)
        if not added:
            extras.append(x)
    split_fn = _split_by_ready_regions(".vcf.gz", "work_bam", get_variantcaller)
    samples = _collapse_by_bam_variantcaller(
        grouped_parallel_split_combine(to_process, split_fn,
                                       multi.group_batches, run_parallel,
                                       "variantcall_sample", "concat_variant_files",
                                       "vrn_file", ["region", "sam_ref", "config"]))
    return extras + samples

def handle_multiple_variantcallers(data):
    """Split samples that potentially require multiple variant calling approaches.
    """
    assert len(data) == 1
    callers = get_variantcaller(data[0])
    if isinstance(callers, basestring):
        return [data]
    elif not callers:
        return []
    else:
        out = []
        for caller in callers:
            base = copy.deepcopy(data[0])
            base["config"]["algorithm"]["orig_variantcaller"] = \
              base["config"]["algorithm"]["variantcaller"]
            base["config"]["algorithm"]["variantcaller"] = caller
            out.append([base])
        return out

def get_variantcallers():
    from bcbio.variation import freebayes, cortex, samtools, varscan, mutect
    return {"gatk": gatk.unified_genotyper,
            "gatk-haplotype": gatk.haplotype_caller,
            "freebayes": freebayes.run_freebayes,
            "cortex": cortex.run_cortex,
            "samtools": samtools.run_samtools,
            "varscan": varscan.run_varscan,
            "mutect": mutect.mutect_caller}

def variantcall_sample(data, region=None, align_bams=None, out_file=None):
    """Parallel entry point for doing genotyping of a region of a sample.
    """
    if out_file is None or not os.path.exists(out_file) or not os.path.lexists(out_file):
        utils.safe_makedir(os.path.dirname(out_file))
        sam_ref = data["sam_ref"]
        config = data["config"]
        caller_fns = get_variantcallers()
        caller_fn = caller_fns[config["algorithm"].get("variantcaller", "gatk")]
        if len(align_bams) == 1:
            items = [data]
        else:
            items = multi.get_orig_items(data)
            assert len(items) == len(align_bams)
        call_file = "%s-raw%s" % utils.splitext_plus(out_file)
        call_file = caller_fn(align_bams, items, sam_ref,
                              data["genome_resources"]["variation"],
                              region, call_file)
        if data["config"]["algorithm"].get("phasing", False) == "gatk":
            call_file = phasing.read_backed_phasing(call_file, align_bams, sam_ref, region, config)
        utils.symlink_plus(call_file, out_file)
    if region:
        data["region"] = region
    data["vrn_file"] = out_file
    return [data]

########NEW FILE########
__FILENAME__ = multi
"""Organize samples for coordinated multi-sample processing.

Handles grouping of related families or batches to go through variant
calling simultaneously.
"""
import collections
import copy
import os

from bcbio import utils
from bcbio.variation import vcfutils

# ## Group batches to process together

def group_by_batch(items):
    """Group a set of sample items by batch (or singleton) name.

    Items in multiple batches cause two batches to be merged together.
    """
    out = collections.defaultdict(list)
    batch_groups = _get_representative_batch(_merge_batches(_find_all_groups(items)))
    for data in items:
        batch = utils.get_in(data, ("metadata", "batch"), data["description"])
        if isinstance(batch, (list, tuple)):
            batch = batch[0]
        batch = batch_groups[batch]
        out[batch].append(data)
    return dict(out)

def _find_all_groups(items):
    """Find all groups
    """
    all_groups = []
    for data in items:
        batches = utils.get_in(data, ("metadata", "batch"), data["description"])
        if not isinstance(batches, (list, tuple)):
            batches = [batches]
        all_groups.append(batches)
    return all_groups

def _merge_batches(all_groups):
    """Merge batches with overlapping groups. Uses merge approach from:

    http://stackoverflow.com/a/4842897/252589
    """
    merged = []
    while len(all_groups) > 0:
        first, rest = all_groups[0], all_groups[1:]
        first = set(first)
        lf = -1
        while len(first) > lf:
            lf = len(first)

            rest2 = []
            for r in rest:
                if len(first.intersection(set(r))) > 0:
                    first |= set(r)
                else:
                    rest2.append(r)
            rest = rest2
        merged.append(first)
        all_groups = rest
    return merged

def _get_representative_batch(merged):
    """Prepare dictionary matching batch items to a representative within a group.
    """
    out = {}
    for mgroup in merged:
        mgroup = sorted(list(mgroup))
        for x in mgroup:
            out[x] = mgroup[0]
    return out

def _list_to_tuple(xs):
    if isinstance(xs, (list, tuple)):
        return tuple([_list_to_tuple(x) for x in xs])
    else:
        return xs

def group_batches(xs):
    """Group samples into batches for simultaneous variant calling.

    Identify all samples to call together: those in the same batch
    and variant caller.
    Pull together all BAM files from this batch and process together,
    Provide details to pull these finalized files back into individual
    expected files.
    """
    singles = []
    batch_groups = collections.defaultdict(list)
    for args in xs:
        assert len(args) == 1
        data = args[0]
        batch = utils.get_in(data, ("metadata", "batch"))
        caller = data["config"]["algorithm"].get("variantcaller", "gatk")
        region = _list_to_tuple(data["region"]) if "region" in data else ()
        if batch is not None:
            batches = batch if isinstance(batch, (list, tuple)) else [batch]
            for b in batches:
                batch_groups[(b, region, caller)].append(copy.deepcopy(data))
        else:
            data["region_bams"] = [data["region_bams"]]
            singles.append(data)
    batches = []
    for batch, items in batch_groups.iteritems():
        batch_data = copy.deepcopy(_pick_lead_item(items))
        batch_data["region_bams"] = [x["region_bams"] for x in items]
        batch_data["group_orig"] = _collapse_subitems(batch_data, items)
        batch_data["group"] = batch
        batches.append(batch_data)
    return singles + batches

# ## Collapse and uncollapse groups to save memory

def _collapse_subitems(base, items):
    """Collapse full data representations relative to a standard base.
    """
    out = []
    for d in items:
        newd = _diff_dict(base, d)
        out.append(newd)
    return out

def _diff_dict(orig, new):
    """Diff a nested dictionary, returning only key/values that differ.
    """
    final = {}
    for k, v in new.items():
        if isinstance(v, dict):
            v = _diff_dict(orig.get(k, {}), v)
            if len(v) > 0:
                final[k] = v
        elif v != orig.get(k):
            final[k] = v
    for k, v in orig.items():
        if k not in new:
            final[k] = None
    return final

def _pick_lead_item(items):
    """Pick single representative sample for batch calling to attach calls to.

    For cancer samples, attach to tumor.
    """
    if vcfutils.is_paired_analysis([x["work_bam"] for x in items], items):
        for data in items:
            if vcfutils.get_paired_phenotype(data) == "tumor":
                return data
        raise ValueError("Did not find tumor sample in paired tumor/normal calling")
    else:
        return items[0]

def get_orig_items(base):
    """Retrieve original items from a diffed set of nested samples.
    """
    assert "group_orig" in base
    out = []
    for data_diff in base["group_orig"]:
        new = copy.deepcopy(base)
        new.pop("group_orig")
        out.append(_patch_dict(data_diff, new))
    return out

def _patch_dict(diff, base):
    """Patch a dictionary, substituting in changed items from the nested diff.
    """
    for k, v in diff.items():
        if isinstance(v, dict):
            base[k] = _patch_dict(v, base.get(k, {}))
        elif not v:
            base.pop(k, None)
        else:
            base[k] = v
    return base

# ## Split batched variants

def split_variants_by_sample(data):
    """Split a multi-sample call file into inputs for individual samples.

    For tumor/normal paired analyses, do not split the final file and attach
    it to the tumor input.
    """
    # not split, do nothing
    if "group_orig" not in data:
        return [[data]]
    # cancer tumor/normal
    elif vcfutils.get_paired_phenotype(data):
        out = []
        for i, sub_data in enumerate(get_orig_items(data)):
            if vcfutils.get_paired_phenotype(sub_data) == "tumor":
                sub_data["vrn_file"] = data["vrn_file"]
            else:
                sub_data.pop("vrn_file", None)
            out.append([sub_data])
        return out
    # population or single sample
    else:
        out = []
        for sub_data in get_orig_items(data):
            sub_vrn_file = data["vrn_file"].replace(str(data["group"][0]) + "-", str(sub_data["name"][-1]) + "-")
            if len(vcfutils.get_samples(data["vrn_file"])) > 1:
                vcfutils.select_sample(data["vrn_file"], str(sub_data["name"][-1]), sub_vrn_file, data["config"])
            elif not os.path.exists(sub_vrn_file):
                utils.symlink_plus(data["vrn_file"], sub_vrn_file)
            sub_data["vrn_file_batch"] = data["vrn_file"]
            sub_data["vrn_file"] = sub_vrn_file
            out.append([sub_data])
        return out

########NEW FILE########
__FILENAME__ = mutect
"""Provide support for MuTect and other paired analysis tools."""

from distutils.version import LooseVersion
import os

from bcbio import bam, broad
from bcbio.utils import file_exists, get_in
from bcbio.distributed.transaction import file_transaction
from bcbio.variation.realign import has_aligned_reads
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.variation import bamprep, vcfutils
from bcbio.log import logger

_PASS_EXCEPTIONS = set(["java.lang.RuntimeException: "
                        "java.lang.IllegalArgumentException: "
                        "Comparison method violates its general contract!",
                        "java.lang.IllegalArgumentException: "
                        "Comparison method violates its general contract!"])

def _check_mutect_version(broad_runner):
    mutect_version = broad_runner.get_mutect_version()
    try:
        assert mutect_version is not None
    except AssertionError:
        logger.warn("WARNING")
        logger.warn("MuTect version could not be determined from jar file. "
                    "Please ensure you are using at least version 1.1.5, "
                    "as versions 1.1.4 and lower have known issues.")
        logger.warn("Proceeding but assuming correct version 1.1.5.")
    else:
        try:
            assert LooseVersion(mutect_version) >= LooseVersion("1.1.5")
        except AssertionError:
            message = ("MuTect 1.1.4 and lower is known to have incompatibilities "
                       "with Java < 7, and this may lead to problems in analyses. "
                       "Please use MuTect 1.1.5 or higher (note that it requires "
                       "Java 7).")
            raise ValueError(message)

def _config_params(base_config, assoc_files, region, out_file):
    """Add parameters based on configuration variables, associated files and genomic regions.
    """
    params = []
    contamination = base_config["algorithm"].get("fraction_contamination", 0)
    params += ["--fraction_contamination", contamination]
    dbsnp = assoc_files["dbsnp"]
    if dbsnp:
        params += ["--dbsnp", dbsnp]
    cosmic = assoc_files.get("cosmic")
    if cosmic:
        params += ["--cosmic", cosmic]
    variant_regions = base_config["algorithm"].get("variant_regions")
    region = subset_variant_regions(variant_regions, region, out_file)
    if region:
        params += ["-L", bamprep.region_to_gatk(region), "--interval_set_rule",
                   "INTERSECTION"]
    return params

def _mutect_call_prep(align_bams, items, ref_file, assoc_files,
                       region=None, out_file=None):
    """Preparation work for MuTect.
    """
    base_config = items[0]["config"]
    broad_runner = broad.runner_from_config(base_config, "mutect")
    _check_mutect_version(broad_runner)

    broad_runner.run_fn("picard_index_ref", ref_file)
    for x in align_bams:
        bam.index(x, base_config)

    paired = vcfutils.get_paired_bams(align_bams, items)
    params = ["-R", ref_file, "-T", "MuTect", "-U", "ALLOW_N_CIGAR_READS"]
    params += ["--downsample_to_coverage", max(200, get_in(paired.tumor_config,
                                                           ("algorithm", "coverage_depth_max"), 10000))]
    params += ["--read_filter", "NotPrimaryAlignment"]
    params += ["-I:tumor", paired.tumor_bam]
    params += ["--tumor_sample_name", paired.tumor_name]
    if paired.normal_bam is not None:
        params += ["-I:normal", paired.normal_bam]
        params += ["--normal_sample_name", paired.normal_name]
    if paired.normal_panel is not None:
        params += ["--normal_panel", paired.normal_panel]
    params += _config_params(base_config, assoc_files, region, out_file)
    return broad_runner, params

def mutect_caller(align_bams, items, ref_file, assoc_files, region=None,
                  out_file=None):
    """Run the MuTect paired analysis algorithm.
    """
    if out_file is None:
        out_file = "%s-paired-variants.vcf.gz" % os.path.splitext(align_bams[0])[0]
    if not file_exists(out_file):
        base_config = items[0]["config"]
        broad_runner = broad.runner_from_config(base_config, "mutect")
        if "appistry" in broad_runner.get_mutect_version():
            out_file_mutect = (out_file.replace(".vcf", "-mutect.vcf")
                               if "vcf" in out_file else out_file + "-mutect.vcf")
        else:
            out_file_mutect = out_file
        broad_runner, params = \
            _mutect_call_prep(align_bams, items, ref_file, assoc_files,
                                   region, out_file_mutect)
        if (not isinstance(region, (list, tuple)) and
              not all(has_aligned_reads(x, region) for x in align_bams)):
                vcfutils.write_empty_vcf(out_file)
                return
        with file_transaction(out_file_mutect) as tx_out_file:
            # Rationale: MuTect writes another table to stdout, which we don't need
            params += ["--vcf", tx_out_file, "-o", os.devnull]
            broad_runner.run_mutect(params)
        if "appistry" in broad_runner.get_mutect_version():
            # SomaticIndelDetector modifications
            out_file_indels = (out_file.replace(".vcf", "-somaticIndels.vcf")
                               if "vcf" in out_file else out_file + "-somaticIndels.vcf")
            params_indels = _SID_call_prep(align_bams, items, ref_file, assoc_files,
                                           region, out_file_indels)
            with file_transaction(out_file_indels) as tx_out_file:
                params_indels += ["-o", tx_out_file]
                broad_runner.run_mutect(params_indels)
            out_file = vcfutils.combine_variant_files(orig_files=[out_file_mutect, out_file_indels],
                                                      out_file=out_file,
                                                      ref_file=items[0]["sam_ref"],
                                                      config=items[0]["config"],
                                                      region=region)
    return out_file

def _SID_call_prep(align_bams, items, ref_file, assoc_files, region=None, out_file=None):
    """Preparation work for SomaticIndelDetector.
    """
    base_config = items[0]["config"]
    for x in align_bams:
        bam.index(x, base_config)

    params = ["-R", ref_file, "-T", "SomaticIndelDetector", "-U", "ALLOW_N_CIGAR_READS"]
    # Limit per base read start count to between 200-10000, i.e. from any base
    # can no more 10000 new reads begin.
    # Further, limit maxNumberOfReads accordingly, otherwise SID discards
    # windows for high coverage panels.
    window_size = 200  # default SID value
    paired = vcfutils.get_paired_bams(align_bams, items)
    max_depth = min(max(200, get_in(paired.tumor_config,
                                    ("algorithm", "coverage_depth_max"), 10000)), 10000)
    params += ["--downsample_to_coverage", max_depth]
    params += ["--maxNumberOfReads", str(int(max_depth) * window_size)]
    params += ["--read_filter", "NotPrimaryAlignment"]
    params += ["-I:tumor", paired.tumor_bam]
    min_af = float(get_in(paired.tumor_config, ("algorithm", "min_allele_fraction"), 10)) / 100.0
    if paired.normal_bam is not None:
        params += ["-I:normal", paired.normal_bam]
        # notice there must be at least 4 reads of coverage in normal
        params += ["--filter_expressions", "T_COV<6||N_COV<4||T_INDEL_F<%s||T_INDEL_CF<0.7" % min_af]
    else:
        params += ["--unpaired"]
        params += ["--filter_expressions", "COV<6||INDEL_F<%s||INDEL_CF<0.7" % min_af]
    if region:
        params += ["-L", bamprep.region_to_gatk(region), "--interval_set_rule",
                   "INTERSECTION"]
    return params

########NEW FILE########
__FILENAME__ = phasing
"""Approaches for calculating haplotype phasing of variants.
"""
import os

from bcbio import broad
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import shared
from bcbio.variation import bamprep

def has_variants(vcf_file):
    with open(vcf_file) as in_handle:
        for line in in_handle:
            if not line.startswith("#"):
                return True
    return False

def read_backed_phasing(vcf_file, bam_files, genome_file, region, config):
    """Phase variants using GATK's read-backed phasing.
    http://www.broadinstitute.org/gatk/gatkdocs/
    org_broadinstitute_sting_gatk_walkers_phasing_ReadBackedPhasing.html
    """
    if has_variants(vcf_file):
        broad_runner = broad.runner_from_config(config)
        out_file = "%s-phased%s" % os.path.splitext(vcf_file)
        if not file_exists(out_file):
            with file_transaction(out_file) as tx_out_file:
                params = ["-T", "ReadBackedPhasing",
                          "-R", genome_file,
                          "--variant", vcf_file,
                          "--out", tx_out_file,
                          "--downsample_to_coverage", "250",
                          "--downsampling_type", "BY_SAMPLE"]
                for bam_file in bam_files:
                    params += ["-I", bam_file]
                variant_regions = config["algorithm"].get("variant_regions", None)
                region = shared.subset_variant_regions(variant_regions, region, out_file)
                if region:
                    params += ["-L", bamprep.region_to_gatk(region),
                               "--interval_set_rule", "INTERSECTION"]
                broad_runner.run_gatk(params)
        return out_file
    else:
        return vcf_file

########NEW FILE########
__FILENAME__ = ploidy
"""Calculate expected ploidy for a genomic regions.

Handles configured ploidy, with custom handling for sex chromosomes and pooled
haploid mitochondrial DNA.
"""
import re

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.variation import vcfutils

def chromosome_special_cases(chrom):
    if chrom in ["MT", "M", "chrM", "chrMT"]:
        return "mitochondrial"
    elif chrom in ["X", "chrX"]:
        return "X"
    elif chrom in ["Y", "chrY"]:
        return "Y"
    else:
        return chrom

def _configured_ploidy_sex(items):
    ploidies = set([data["config"]["algorithm"].get("ploidy", 2) for data in items])
    assert len(ploidies) == 1, "Multiple ploidies set for group calling: %s" % ploidies
    ploidy = ploidies.pop()
    sexes = set([data.get("metadata", {}).get("sex", "").lower() for data in items])
    return ploidy, sexes

def get_ploidy(items, region):
    """Retrieve ploidy of a region, handling special cases.
    """
    chrom = chromosome_special_cases(region[0] if isinstance(region, (list, tuple))
                                     else None)
    ploidy, sexes = _configured_ploidy_sex(items)
    if chrom == "mitochondrial":
        # For now, do haploid calling. Could also do pooled calling
        # but not entirely clear what the best default would be.
        return 1
    elif chrom == "X":
        # Do standard diploid calling if we have any females or unspecified.
        if "female" in sexes:
            return 2
        elif "male" in sexes:
            return 1
        else:
            return 2
    elif chrom == "Y":
        # Always call Y single. If female, filter_vcf_by_sex removes Y regions.
        return 1
    else:
        return ploidy

def _to_haploid(parts):
    """Check if a variant call is homozygous variant, convert to haploid.
    XXX Needs generalization or use of a standard VCF library.
    """
    finfo = dict(zip(parts[-2].split(":"), parts[-1].strip().split(":")))
    pat = re.compile(r"\||/")
    if "GT" in finfo:
        calls = set(pat.split(finfo["GT"]))
        if len(calls) == 1:
            gt_index = parts[-2].split(":").index("GT")
            call_parts = parts[-1].strip().split(":")
            call_parts[gt_index] = calls.pop()
            parts[-1] = ":".join(call_parts) + "\n"
            return "\t".join(parts)

def _fix_line_ploidy(line, sex):
    """Check variant calls to be sure if conforms to expected ploidy for sex/custom chromosomes.
    """
    parts = line.split("\t")
    chrom = chromosome_special_cases(parts[0])
    if chrom == "mitochondrial":
        return _to_haploid(parts)
    elif chrom == "X":
        if sex == "male":
            return _to_haploid(parts)
        else:
            return line
    elif chrom == "Y":
        if sex != "female":
            return _to_haploid(parts)
    else:
        return line

def filter_vcf_by_sex(vcf_file, data):
    """Post-filter a single sample VCF, handling sex chromosomes.

    Handles sex chromosomes and mitochondrial. Does not try to resolve called
    hets into potential homozygotes when converting diploid to haploid.

    Skips filtering on pooled samples, we still need to implement.
    """
    if len(vcfutils.get_samples(vcf_file)) > 1:
        return vcf_file
    _, sexes = _configured_ploidy_sex([data])
    sex = sexes.pop()
    out_file = "%s-ploidyfix%s" % utils.splitext_plus(vcf_file)
    if not utils.file_exists(out_file):
        orig_out_file = out_file
        out_file = orig_out_file.replace(".vcf.gz", ".vcf")
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                with utils.open_gzipsafe(vcf_file) as in_handle:
                    for line in in_handle:
                        if line.startswith("#"):
                            out_handle.write(line)
                        else:
                            line = _fix_line_ploidy(line, sex)
                            if line:
                                out_handle.write(line)
        if orig_out_file.endswith(".gz"):
            out_file = vcfutils.bgzip_and_index(out_file, data["config"])
    return out_file

########NEW FILE########
__FILENAME__ = population
"""Provide infrastructure to allow exploration of variations within populations.

Uses the gemini framework (https://github.com/arq5x/gemini) to build SQLite
database of variations for query and evaluation.
"""
import collections
from distutils.version import LooseVersion
import os
import subprocess

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do, programs
from bcbio.variation import vcfutils

def prep_gemini_db(fnames, call_info, samples):
    """Prepare a gemini database from VCF inputs prepared with snpEff.
    """
    data = samples[0]
    out_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "gemini"))
    name, caller, is_batch = call_info
    gemini_db = os.path.join(out_dir, "%s-%s.db" % (name, caller))
    gemini_vcf = get_multisample_vcf(fnames, name, caller, data)
    use_gemini_quick = (do_db_build(samples, check_gemini=False) and
                        any(vcfutils.vcf_has_variants(f) for f in fnames))
    if not utils.file_exists(gemini_db) and use_gemini_quick:
        use_gemini = do_db_build(samples) and any(vcfutils.vcf_has_variants(f) for f in fnames)
        if use_gemini:
            with file_transaction(gemini_db) as tx_gemini_db:
                gemini = config_utils.get_program("gemini", data["config"])
                if "program_versions" in data["config"].get("resources", {}):
                    gemini_ver = programs.get_version("gemini", config=data["config"])
                else:
                    gemini_ver = None
                # Recent versions of gemini allow loading only passing variants
                load_opts = ""
                if not gemini_ver or LooseVersion(gemini_ver) > LooseVersion("0.6.2.1"):
                    load_opts += " --passonly"
                # For small test files, skip gene table loading which takes a long time
                if gemini_ver and LooseVersion(gemini_ver) > LooseVersion("0.6.4"):
                    if _is_small_vcf(gemini_vcf):
                        load_opts += " --skip-gene-tables"
                    if "/test_automated_output/" in gemini_vcf:
                        load_opts += " --test-mode"
                num_cores = data["config"]["algorithm"].get("num_cores", 1)
                cmd = "{gemini} load {load_opts} -v {gemini_vcf} -t snpEff --cores {num_cores} {tx_gemini_db}"
                cmd = cmd.format(**locals())
                do.run(cmd, "Create gemini database for %s %s" % (name, caller), data)
    return [[(name, caller), {"db": gemini_db if utils.file_exists(gemini_db) else None,
                              "vcf": gemini_vcf if is_batch else None}]]

def _is_small_vcf(vcf_file):
    """Check for small VCFs which we want to analyze quicker.
    """
    count = 0
    small_thresh = 250
    with utils.open_gzipsafe(vcf_file) as in_handle:
        for line in in_handle:
            if not line.startswith("#"):
                count += 1
            if count > small_thresh:
                return False
    return True

def get_multisample_vcf(fnames, name, caller, data):
    """Retrieve a multiple sample VCF file in a standard location.

    Handles inputs with multiple repeated input files from batches.
    """
    unique_fnames = []
    for f in fnames:
        if f not in unique_fnames:
            unique_fnames.append(f)
    out_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "gemini"))
    if len(unique_fnames) > 1:
        gemini_vcf = os.path.join(out_dir, "%s-%s.vcf.gz" % (name, caller))
        vrn_file_batch = None
        for variant in data["variants"]:
            if variant["variantcaller"] == caller and variant.get("vrn_file_batch"):
                vrn_file_batch = variant["vrn_file_batch"]
        if vrn_file_batch:
            utils.symlink_plus(vrn_file_batch, gemini_vcf)
            return gemini_vcf
        else:
            return vcfutils.merge_variant_files(unique_fnames, gemini_vcf, data["sam_ref"],
                                                data["config"])
    else:
        gemini_vcf = os.path.join(out_dir, "%s-%s%s" % (name, caller, utils.splitext_plus(unique_fnames[0])[1]))
        utils.symlink_plus(unique_fnames[0], gemini_vcf)
        return gemini_vcf

def _has_gemini(config):
    try:
        gemini = config_utils.get_program("gemini", config)
    except config_utils.CmdNotFound:
        return False
    try:
        p = subprocess.Popen([gemini, "-h"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        p.stdout.close()
        if p.returncode not in [0, 1]:
            return False
    except OSError:
        return False
    return True

def do_db_build(samples, check_gemini=True, need_bam=True):
    """Confirm we should build a gemini database: need gemini + human samples + not in tool_skip.
    """
    genomes = set()
    for data in samples:
        if not need_bam or data.get("align_bam"):
            genomes.add(data["genome_build"])
        if "gemini" in utils.get_in(data, ("config", "algorithm", "tools_off"), []):
            return False
    if len(genomes) == 1:
        return (samples[0]["genome_resources"].get("aliases", {}).get("human", False)
                and (not check_gemini or _has_gemini(samples[0]["config"])))
    else:
        return False

def get_gemini_files(data):
    """Enumerate available gemini data files in a standard installation.
    """
    try:
        from gemini import annotations, config
    except ImportError:
        return {}
    return {"base": config.read_gemini_config()["annotation_dir"],
            "files": annotations.get_anno_files().values()}

def _group_by_batches(samples, check_fn):
    """Group data items into batches, providing details to retrieve results.
    """
    batch_groups = collections.defaultdict(list)
    singles = []
    out_retrieve = []
    extras = []
    for data in [x[0] for x in samples]:
        if check_fn(data):
            batch = data.get("metadata", {}).get("batch")
            name = str(data["name"][-1])
            if batch:
                out_retrieve.append((str(batch), data))
            else:
                out_retrieve.append((name, data))
            for vrn in data["variants"]:
                if batch:
                    batch_groups[(str(batch), vrn["variantcaller"])].append((vrn["vrn_file"], data))
                else:
                    singles.append((name, vrn["variantcaller"], data, vrn["vrn_file"]))
        else:
            extras.append(data)
    return batch_groups, singles, out_retrieve, extras

def _has_variant_calls(data):
    return data.get("align_bam") and data.get("vrn_file") and vcfutils.vcf_has_variants(data["vrn_file"])

def prep_db_parallel(samples, parallel_fn):
    """Prepares gemini databases in parallel, handling jointly called populations.
    """
    batch_groups, singles, out_retrieve, extras = _group_by_batches(samples, _has_variant_calls)
    to_process = []
    has_batches = False
    for (name, caller), info in batch_groups.iteritems():
        fnames = [x[0] for x in info]
        to_process.append([fnames, (str(name), caller, True), [x[1] for x in info]])
        has_batches = True
    for name, caller, data, fname in singles:
        to_process.append([[fname], (str(name), caller, False), [data]])
    if len(samples) > 0 and not do_db_build([x[0] for x in samples], check_gemini=False) and not has_batches:
        return samples
    output = parallel_fn("prep_gemini_db", to_process)
    out_fetch = {}
    for batch_id, out_file in output:
        out_fetch[tuple(batch_id)] = out_file
    out = []
    for batch_name, data in out_retrieve:
        out_variants = []
        for vrn in data["variants"]:
            vrn["population"] = out_fetch[(batch_name, vrn["variantcaller"])]
            out_variants.append(vrn)
        data["variants"] = out_variants
        out.append([data])
    for x in extras:
        out.append([x])
    return out

########NEW FILE########
__FILENAME__ = realign
"""Perform realignment of BAM files around indels using the GATK toolkit.
"""
import os
import shutil
from contextlib import closing

import pysam

from bcbio import bam, broad
from bcbio.bam import ref
from bcbio.log import logger
from bcbio.utils import curdir_tmpdir, file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline.shared import subset_bam_by_region, subset_variant_regions
from bcbio.provenance import do

# ## GATK realignment

def gatk_realigner_targets(runner, align_bam, ref_file, dbsnp=None,
                           region=None, out_file=None, deep_coverage=False,
                           variant_regions=None):
    """Generate a list of interval regions for realignment around indels.
    """
    if out_file:
        out_file = "%s.intervals" % os.path.splitext(out_file)[0]
    else:
        out_file = "%s-realign.intervals" % os.path.splitext(align_bam)[0]
    # check only for file existence; interval files can be empty after running
    # on small chromosomes, so don't rerun in those cases
    if not os.path.exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            logger.debug("GATK RealignerTargetCreator: %s %s" %
                         (os.path.basename(align_bam), region))
            params = ["-T", "RealignerTargetCreator",
                      "-I", align_bam,
                      "-R", ref_file,
                      "-o", tx_out_file,
                      "-l", "INFO",
                      ]
            region = subset_variant_regions(variant_regions, region, tx_out_file)
            if region:
                params += ["-L", region, "--interval_set_rule", "INTERSECTION"]
            if dbsnp:
                params += ["--known", dbsnp]
            if deep_coverage:
                params += ["--mismatchFraction", "0.30",
                           "--maxIntervalSize", "650"]
            runner.run_gatk(params, memscale={"direction": "decrease", "magnitude": 2})
    return out_file

def gatk_indel_realignment_cl(runner, align_bam, ref_file, intervals,
                              tmp_dir, region=None, deep_coverage=False):
    """Prepare input arguments for GATK indel realignment.
    """
    params = ["-T", "IndelRealigner",
              "-I", align_bam,
              "-R", ref_file,
              "-targetIntervals", intervals,
              ]
    if region:
        params += ["-L", region]
    if deep_coverage:
        params += ["--maxReadsInMemory", "300000",
                   "--maxReadsForRealignment", str(int(5e5)),
                   "--maxReadsForConsensuses", "500",
                   "--maxConsensuses", "100"]
    return runner.cl_gatk(params, tmp_dir)

def gatk_indel_realignment(runner, align_bam, ref_file, intervals,
                           region=None, out_file=None, deep_coverage=False,
                           config=None):
    """Perform realignment of BAM file in specified regions
    """
    if out_file is None:
        out_file = "%s-realign.bam" % os.path.splitext(align_bam)[0]
    if not file_exists(out_file):
        with curdir_tmpdir({"config": config}) as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                logger.info("GATK IndelRealigner: %s %s" %
                            (os.path.basename(align_bam), region))
                cl = gatk_indel_realignment_cl(runner, align_bam, ref_file, intervals,
                                                   tmp_dir, region, deep_coverage)
                cl += ["-o", tx_out_file]
                do.run(cl, "GATK indel realignment", {})
    return out_file

def gatk_realigner(align_bam, ref_file, config, dbsnp=None, region=None,
                   out_file=None, deep_coverage=False):
    """Realign a BAM file around indels using GATK, returning sorted BAM.
    """
    runner = broad.runner_from_config(config)
    bam.index(align_bam, config)
    runner.run_fn("picard_index_ref", ref_file)
    ref.fasta_idx(ref_file)
    if region:
        align_bam = subset_bam_by_region(align_bam, region, out_file)
        bam.index(align_bam, config)
    if has_aligned_reads(align_bam, region):
        variant_regions = config["algorithm"].get("variant_regions", None)
        realign_target_file = gatk_realigner_targets(runner, align_bam,
                                                     ref_file, dbsnp, region,
                                                     out_file, deep_coverage,
                                                     variant_regions)
        realign_bam = gatk_indel_realignment(runner, align_bam, ref_file,
                                             realign_target_file, region,
                                             out_file, deep_coverage, config=config)
        # No longer required in recent GATK (> Feb 2011) -- now done on the fly
        # realign_sort_bam = runner.run_fn("picard_fixmate", realign_bam)
        return realign_bam
    elif out_file:
        shutil.copy(align_bam, out_file)
        return out_file
    else:
        return align_bam

# ## Utilities

def has_aligned_reads(align_bam, region=None):
    """Check if the aligned BAM file has any reads in the region.

    region can be a chromosome string ("chr22"),
    a tuple region (("chr22", 1, 100)) or a file of regions.
    """
    import pybedtools
    if region is not None:
        if isinstance(region, basestring) and os.path.isfile(region):
            regions = [tuple(r) for r in pybedtools.BedTool(region)]
        else:
            regions = [region]
    with closing(pysam.Samfile(align_bam, "rb")) as cur_bam:
        if region is not None:
            for region in regions:
                if isinstance(region, basestring):
                    for item in cur_bam.fetch(region):
                        return True
                else:
                    for item in cur_bam.fetch(region[0], int(region[1]), int(region[2])):
                        return True
        else:
            for item in cur_bam:
                if not item.is_unmapped:
                    return True
    return False

########NEW FILE########
__FILENAME__ = recalibrate
"""Perform quality score recalibration with the GATK toolkit.

Corrects read quality scores post-alignment to provide improved estimates of
error rates based on alignments to the reference genome.

http://www.broadinstitute.org/gsa/wiki/index.php/Base_quality_score_recalibration
"""
import os

from bcbio import bam, broad
from bcbio.log import logger
from bcbio.utils import curdir_tmpdir, file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.variation.realign import has_aligned_reads

# ## GATK recalibration

def prep_recal(data):
    """Perform a GATK recalibration of the sorted aligned BAM, producing recalibrated BAM.
    """
    if data["config"]["algorithm"].get("recalibrate", True) in [True, "gatk"]:
        logger.info("Recalibrating %s with GATK" % str(data["name"]))
        ref_file = data["sam_ref"]
        config = data["config"]
        dbsnp_file = data["genome_resources"]["variation"]["dbsnp"]
        broad_runner = broad.runner_from_config(config)
        platform = config["algorithm"].get("platform", "illumina")
        broad_runner.run_fn("picard_index_ref", ref_file)
        if config["algorithm"].get("mark_duplicates", True):
            (dup_align_bam, _) = broad_runner.run_fn("picard_mark_duplicates", data["work_bam"])
        else:
            dup_align_bam = data["work_bam"]
        bam.index(dup_align_bam, config)
        intervals = config["algorithm"].get("variant_regions", None)
        data["work_bam"] = dup_align_bam
        data["prep_recal"] = _gatk_base_recalibrator(broad_runner, dup_align_bam, ref_file,
                                                     platform, dbsnp_file, intervals, data)
    return [[data]]

# ## Identify recalibration information

def _gatk_base_recalibrator(broad_runner, dup_align_bam, ref_file, platform,
                            dbsnp_file, intervals, data):
    """Step 1 of GATK recalibration process, producing table of covariates.

    Large whole genome BAM files take an excessively long time to recalibrate and
    the extra inputs don't help much beyond a certain point. See the 'Downsampling analysis'
    plots in the GATK documentation:

    http://gatkforums.broadinstitute.org/discussion/44/base-quality-score-recalibrator#latest

    This identifies large files and calculates the fraction to downsample to.

    TODO: Use new GATK 2.6+ AnalyzeCovariates tool to plot recalibration results.
    """
    target_counts = 1e8  # 100 million reads per read group, 20x the plotted max
    out_file = "%s.grp" % os.path.splitext(dup_align_bam)[0]
    if not file_exists(out_file):
        if has_aligned_reads(dup_align_bam, intervals):
            with curdir_tmpdir(data) as tmp_dir:
                with file_transaction(out_file) as tx_out_file:
                    params = ["-T", "BaseRecalibrator",
                              "-o", tx_out_file,
                              "-I", dup_align_bam,
                              "-R", ref_file,
                              ]
                    downsample_pct = bam.get_downsample_pct(broad_runner, dup_align_bam, target_counts)
                    if downsample_pct:
                        params += ["--downsample_to_fraction", str(downsample_pct),
                                   "--downsampling_type", "ALL_READS"]
                    if platform.lower() == "solid":
                        params += ["--solid_nocall_strategy", "PURGE_READ",
                                   "--solid_recal_mode", "SET_Q_ZERO_BASE_N"]
                    # GATK-lite does not have support for
                    # insertion/deletion quality modeling
                    if broad_runner.gatk_type() == "lite":
                        params += ["--disable_indel_quals"]
                    if dbsnp_file:
                        params += ["--knownSites", dbsnp_file]
                    if intervals:
                        params += ["-L", intervals, "--interval_set_rule", "INTERSECTION"]
                    broad_runner.run_gatk(params, tmp_dir)
        else:
            with open(out_file, "w") as out_handle:
                out_handle.write("# No aligned reads")
    return out_file

########NEW FILE########
__FILENAME__ = samtools
"""Variant calling using samtools mpileup and bcftools.

http://samtools.sourceforge.net/mpileup.shtml
"""
import os
from distutils.version import LooseVersion

from bcbio import bam
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.provenance import do, programs
from bcbio.variation import annotation, bamprep, realign, vcfutils


def shared_variantcall(call_fn, name, align_bams, ref_file, items,
                       assoc_files, region=None, out_file=None):
    """Provide base functionality for prepping and indexing for variant calling.
    """
    config = items[0]["config"]
    if out_file is None:
        if vcfutils.is_paired_analysis(align_bams, items):
            out_file = "%s-paired-variants.vcf.gz" % config["metdata"]["batch"]
        else:
            out_file = "%s-variants.vcf.gz" % os.path.splitext(align_bams[0])[0]
    if not file_exists(out_file):
        logger.info("Genotyping with {name}: {region} {fname}".format(
            name=name, region=region, fname=os.path.basename(align_bams[0])))
        for x in align_bams:
            bam.index(x, config)
        variant_regions = config["algorithm"].get("variant_regions", None)
        target_regions = subset_variant_regions(variant_regions, region, out_file)
        if ((variant_regions is not None and isinstance(target_regions, basestring)
              and not os.path.isfile(target_regions))
              or not all(realign.has_aligned_reads(x, region) for x in align_bams)):
            vcfutils.write_empty_vcf(out_file, config)
        else:
            with file_transaction(out_file) as tx_out_file:
                call_fn(align_bams, ref_file, items, target_regions,
                        tx_out_file)
    ann_file = annotation.annotate_nongatk_vcf(out_file, align_bams, assoc_files["dbsnp"],
                                               ref_file, config)
    return ann_file


def run_samtools(align_bams, items, ref_file, assoc_files, region=None,
                 out_file=None):
    """Detect SNPs and indels with samtools mpileup and bcftools.
    """
    return shared_variantcall(_call_variants_samtools, "samtools", align_bams, ref_file,
                              items, assoc_files, region, out_file)

def prep_mpileup(align_bams, ref_file, max_read_depth, config,
                 target_regions=None, want_bcf=True):
    cl = [config_utils.get_program("samtools", config), "mpileup",
          "-f", ref_file, "-d", str(max_read_depth), "-L", str(max_read_depth),
          "-m", "3", "-F", "0.0002"]
    if want_bcf:
        cl += ["-D", "-S", "-u"]
    if target_regions:
        str_regions = bamprep.region_to_gatk(target_regions)
        if os.path.isfile(str_regions):
            cl += ["-l", str_regions]
        else:
            cl += ["-r", str_regions]
    cl += align_bams
    return " ".join(cl)

def _call_variants_samtools(align_bams, ref_file, items, target_regions, out_file):
    """Call variants with samtools in target_regions.

    Works around a GATK VCF compatibility issue in samtools 0.20 by removing extra
    Version information from VCF header lines.
    """
    config = items[0]["config"]

    max_read_depth = "1000"
    mpileup = prep_mpileup(align_bams, ref_file, max_read_depth, config,
                           target_regions=target_regions)
    bcftools = config_utils.get_program("bcftools", config)
    bcftools_version = programs.get_version("bcftools", config=config)
    samtools_version = programs.get_version("samtools", config=config)
    if LooseVersion(bcftools_version) > LooseVersion("0.1.19"):
        if LooseVersion(samtools_version) <= LooseVersion("0.1.19"):
            raise ValueError("samtools calling not supported with 0.1.19 samtools and 0.20 bcftools")
        bcftools_opts = "call -v -c"
    else:
        bcftools_opts = "view -v -c -g"
    compress_cmd = "| bgzip -c" if out_file.endswith("gz") else ""
    vcfutils = config_utils.get_program("vcfutils.pl", config)
    cmd = ("{mpileup} "
           "| {bcftools} {bcftools_opts} - "
           "| {vcfutils} varFilter -D {max_read_depth} "
           "| sed 's/,Version=3>/>/'"
           "{compress_cmd} > {out_file}")
    logger.info(cmd.format(**locals()))
    do.run(cmd.format(**locals()), "Variant calling with samtools", {})

########NEW FILE########
__FILENAME__ = split
"""Utilities for manipulating VCF files.
"""
import os

from bcbio.bam import ref
from bcbio.utils import file_exists, replace_suffix, append_stem
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do
from bcbio.variation import bamprep, vcfutils

def split_vcf(in_file, ref_file, config, out_dir=None):
    """Split a VCF file into separate files by chromosome.
    """
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(in_file), "split")
    out_files = []
    with open(ref.fasta_idx(ref_file, config)) as in_handle:
        for line in in_handle:
            chrom, size = line.split()[:2]
            out_file = os.path.join(out_dir,
                                    os.path.basename(replace_suffix(append_stem(in_file, "-%s" % chrom), ".vcf")))
            subset_vcf(in_file, (chrom, 0, size), out_file, config)
            out_files.append(out_file)
    return out_files

def subset_vcf(in_file, region, out_file, config):
    """Subset VCF in the given region, handling bgzip and indexing of input.
    """
    work_file = vcfutils.bgzip_and_index(in_file, config)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            bcftools = config_utils.get_program("bcftools", config)
            region_str = bamprep.region_to_gatk(region)
            cmd = "{bcftools} view -r {region_str} {work_file} > {tx_out_file}"
            do.run(cmd.format(**locals()), "subset %s: %s" % (os.path.basename(work_file), region_str))
    return out_file

########NEW FILE########
__FILENAME__ = validate
"""Perform validation of final calls against known reference materials.

Automates the process of checking pipeline results against known valid calls
to identify discordant variants. This provides a baseline for ensuring the
validity of pipeline updates and algorithm changes.
"""
import csv
import os

import yaml

from bcbio import utils
from bcbio.bam import callable
from bcbio.pipeline import config_utils, shared
from bcbio.provenance import do
from bcbio.variation import validateplot

# ## Individual sample comparisons

def _has_validate(data):
    return data.get("vrn_file") and "validate" in data["config"]["algorithm"]

def normalize_input_path(x, data):
    """Normalize path for input files, handling relative paths.
    Looks for non-absolute paths in local and fastq directories
    """
    if x is None:
        return None
    elif os.path.isabs(x):
        return os.path.normpath(x)
    else:
        for d in [data["dirs"].get("fastq"), data["dirs"].get("work")]:
            if d:
                cur_x = os.path.normpath(os.path.join(d, x))
                if os.path.exists(cur_x):
                    return cur_x
        raise IOError("Could not find validation file %s" % x)

def compare_to_rm(data):
    """Compare final variant calls against reference materials of known calls.
    """
    if _has_validate(data):
        if isinstance(data["vrn_file"], (list, tuple)):
            vrn_file = [os.path.abspath(x) for x in data["vrn_file"]]
        else:
            vrn_file = os.path.abspath(data["vrn_file"])
        rm_file = normalize_input_path(data["config"]["algorithm"]["validate"], data)
        rm_interval_file = normalize_input_path(data["config"]["algorithm"].get("validate_regions"), data)
        rm_genome = data["config"]["algorithm"].get("validate_genome_build")
        sample = data["name"][-1].replace(" ", "_")
        caller = data["config"]["algorithm"].get("variantcaller")
        if not caller:
            caller = "precalled"
        base_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "validate", sample, caller))
        val_config_file = _create_validate_config_file(vrn_file, rm_file, rm_interval_file,
                                                       rm_genome, base_dir, data)
        work_dir = os.path.join(base_dir, "work")
        out = {"summary": os.path.join(work_dir, "validate-summary.csv"),
               "grading": os.path.join(work_dir, "validate-grading.yaml"),
               "discordant": os.path.join(work_dir, "%s-eval-ref-discordance-annotate.vcf" % sample)}
        if not utils.file_exists(out["discordant"]) or not utils.file_exists(out["grading"]):
            bcbio_variation_comparison(val_config_file, base_dir, data)
        out["concordant"] = filter(os.path.exists,
                                   [os.path.join(work_dir, "%s-%s-concordance.vcf" % (sample, x))
                                    for x in ["eval-ref", "ref-eval"]])[0]
        data["validate"] = out
    return [[data]]

def bcbio_variation_comparison(config_file, base_dir, data):
    """Run a variant comparison using the bcbio.variation toolkit, given an input configuration.
    """
    tmp_dir = utils.safe_makedir(os.path.join(base_dir, "tmp"))
    bv_jar = config_utils.get_jar("bcbio.variation",
                                  config_utils.get_program("bcbio_variation",
                                                           data["config"], "dir"))
    resources = config_utils.get_resources("bcbio_variation", data["config"])
    jvm_opts = resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"])
    java_args = ["-Djava.io.tmpdir=%s" % tmp_dir]
    cmd = ["java"] + jvm_opts + java_args + ["-jar", bv_jar, "variant-compare", config_file]
    do.run(cmd, "Comparing variant calls using bcbio.variation", data)

def _create_validate_config_file(vrn_file, rm_file, rm_interval_file, rm_genome,
                                 base_dir, data):
    config_dir = utils.safe_makedir(os.path.join(base_dir, "config"))
    config_file = os.path.join(config_dir, "validate.yaml")
    with open(config_file, "w") as out_handle:
        out = _create_validate_config(vrn_file, rm_file, rm_interval_file, rm_genome,
                                      base_dir, data)
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return config_file

def _create_validate_config(vrn_file, rm_file, rm_interval_file, rm_genome,
                            base_dir, data):
    """Create a bcbio.variation configuration input for validation.
    """
    if rm_genome:
        rm_genome = utils.get_in(data, ("reference", "alt", rm_genome, "base"))
    if rm_genome and rm_genome != utils.get_in(data, ("reference", "fasta", "base")):
        eval_genome = utils.get_in(data, ("reference", "fasta", "base"))
    else:
        rm_genome = utils.get_in(data, ("reference", "fasta", "base"))
        eval_genome = None
    ref_call = {"file": str(rm_file), "name": "ref", "type": "grading-ref",
                "preclean": True, "prep": True, "remove-refcalls": True}
    a_intervals = get_analysis_intervals(data)
    if a_intervals:
        a_intervals = shared.remove_lcr_regions(a_intervals, [data])
    if rm_interval_file:
        ref_call["intervals"] = rm_interval_file
    eval_call = {"file": vrn_file, "name": "eval", "remove-refcalls": True}
    if eval_genome:
        eval_call["ref"] = eval_genome
        eval_call["preclean"] = True
        eval_call["prep"] = True
    if a_intervals and eval_genome:
        eval_call["intervals"] = os.path.abspath(a_intervals)
    exp = {"sample": data["name"][-1],
           "ref": rm_genome,
           "approach": "grade",
           "calls": [ref_call, eval_call]}
    if a_intervals and not eval_genome:
        exp["intervals"] = os.path.abspath(a_intervals)
    if data.get("align_bam") and not eval_genome:
        exp["align"] = data["align_bam"]
    elif data.get("work_bam") and not eval_genome:
        exp["align"] = data["work_bam"]
    return {"dir": {"base": base_dir, "out": "work", "prep": "work/prep"},
            "experiments": [exp]}

def get_analysis_intervals(data):
    """Retrieve analysis regions for the current variant calling pipeline.
    """
    if data.get("ensemble_bed"):
        return data["ensemble_bed"]
    elif data.get("align_bam"):
        return callable.sample_callable_bed(data["align_bam"],
                                            utils.get_in(data, ("reference", "fasta", "base")), data["config"])
    elif data.get("work_bam"):
        return callable.sample_callable_bed(data["work_bam"],
                                            utils.get_in(data, ("reference", "fasta", "base")), data["config"])
    else:
        for key in ["callable_regions", "variant_regions"]:
            intervals = data["config"]["algorithm"].get(key)
            if intervals:
                return intervals

# ## Summarize comparisons

def _flatten_grading(stats):
    vtypes = ["snp", "indel"]
    cat = "concordant"
    for vtype in vtypes:
        yield vtype, cat, stats[cat][cat].get(vtype, 0)
    for vtype in vtypes:
        for vclass, vitems in sorted(stats["discordant"].get(vtype, {}).iteritems()):
            for vreason, val in sorted(vitems.iteritems()):
                yield vtype, "discordant-%s-%s" % (vclass, vreason), val
            yield vtype, "discordant-%s-total" % vclass, sum(vitems.itervalues())

def _has_grading_info(samples):
    for data in (x[0] for x in samples):
        for variant in data.get("variants", []):
            if "validate" in variant:
                return True
    return False

def summarize_grading(samples):
    """Provide summaries of grading results across all samples.
    """
    if not _has_grading_info(samples):
        return samples
    validate_dir = utils.safe_makedir(os.path.join(samples[0][0]["dirs"]["work"], "validate"))
    out_csv = os.path.join(validate_dir, "grading-summary.csv")
    header = ["sample", "caller", "variant.type", "category", "value"]
    out = []
    with open(out_csv, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(header)
        plot_num = 0
        for data in (x[0] for x in samples):
            plot_data = []
            for variant in data.get("variants", []):
                if variant.get("validate"):
                    variant["validate"]["grading_summary"] = out_csv
                    with open(variant["validate"]["grading"]) as in_handle:
                        grade_stats = yaml.load(in_handle)
                    for sample_stats in grade_stats:
                        sample = sample_stats["sample"]
                        for vtype, cat, val in _flatten_grading(sample_stats):
                            row = [sample, variant.get("variantcaller", ""),
                                   vtype, cat, val]
                            writer.writerow(row)
                            plot_data.append(row)
            plots = (validateplot.create(plot_data, header, plot_num, data["config"],
                                         os.path.splitext(out_csv)[0])
                     if plot_data else None)
            if plots:
                plot_num += 1
                for variant in data.get("variants", []):
                    if variant.get("validate"):
                        variant["validate"]["grading_plots"] = plots
            out.append([data])
    return out

########NEW FILE########
__FILENAME__ = validateplot
"""Plot validation results from variant calling comparisons.

Handles data normalization and plotting, emphasizing comparisons on methodology
differences.
"""
import collections
import os

import numpy as np
try:
    import prettyplotlib as ppl
    import pandas as pd
except ImportError:
    gg, pd, ppl = None, None, None

from bcbio import utils
from bcbio.variation import bamprep

def create_from_csv(in_csv, config=None, outtype="pdf", title=None, size=None):
    df = pd.read_csv(in_csv)
    create(df, None, 0, config or {}, os.path.splitext(in_csv)[0], outtype, title,
           size)

def create(plot_data, header, ploti, sample_config, out_file_base, outtype="pdf",
           title=None, size=None):
    """Create plots of validation results for a sample, labeling prep strategies.
    """
    if pd is None or ppl is None:
        return None
    if header:
        df = pd.DataFrame(plot_data, columns=header)
    else:
        df = plot_data
    df["aligner"] = [get_aligner(x, sample_config) for x in df["sample"]]
    df["bamprep"] = [get_bamprep(x, sample_config) for x in df["sample"]]
    floors = get_group_floors(df, cat_labels)
    df["value.floor"] = [get_floor_value(x, cat, vartype, floors)
                         for (x, cat, vartype) in zip(df["value"], df["category"], df["variant.type"])]
    out = []
    for i, prep in enumerate(df["bamprep"].unique()):
        out.append(plot_prep_methods(df, prep, i + ploti, out_file_base, outtype, title, size))
    return out

cat_labels = {"concordant": "Concordant",
              "discordant-missing-total": "Discordant (missing)",
              "discordant-extra-total": "Discordant (extra)",
              "discordant-shared-total": "Discordant (shared)"}
vtype_labels = {"snp": "SNPs", "indel": "Indels"}
prep_labels = {"gatk": "GATK best-practice BAM preparation (recalibration, realignment)",
               "none": "Minimal BAM preparation (samtools de-duplication only)"}
caller_labels = {"ensemble": "Ensemble", "freebayes": "FreeBayes",
                 "gatk": "GATK Unified\nGenotyper", "gatk-haplotype": "GATK Haplotype\nCaller"}

def plot_prep_methods(df, prep, prepi, out_file_base, outtype, title=None,
                      size=None):
    """Plot comparison between BAM preparation methods.
    """
    samples = df[(df["bamprep"] == prep)]["sample"].unique()
    assert len(samples) >= 1, samples
    out_file = "%s-%s.%s" % (out_file_base, samples[0], outtype)
    df = df[df["category"].isin(cat_labels)]
    _prettyplot(df, prep, prepi, out_file, title, size)
    return out_file

def _prettyplot(df, prep, prepi, out_file, title=None, size=None):
    """Plot using prettyplot wrapper around matplotlib.
    """
    cats = ["concordant", "discordant-missing-total",
            "discordant-extra-total", "discordant-shared-total"]
    vtypes = df["variant.type"].unique()
    fig, axs = ppl.subplots(len(vtypes), len(cats))
    callers = sorted(df["caller"].unique())
    width = 0.8
    for i, vtype in enumerate(vtypes):
        ax_row = axs[i] if len(vtypes) > 1 else axs
        for j, cat in enumerate(cats):
            ax = ax_row[j]
            if i == 0:
                ax.set_title(cat_labels[cat], size=14)
            ax.get_yaxis().set_ticks([])
            if j == 0:
                ax.set_ylabel(vtype_labels[vtype], size=14)
            vals, labels, maxval = _get_chart_info(df, vtype, cat, prep, callers)
            ppl.bar(ax, np.arange(len(callers)), vals,
                    color=ppl.colors.set2[prepi], width=width)
            ax.set_ylim(0, maxval)
            if i == len(vtypes) - 1:
                ax.set_xticks(np.arange(len(callers)) + width / 2.0)
                ax.set_xticklabels([caller_labels.get(x, x).replace("__", "\n") if x else ""
                                    for x in callers], size=8, rotation=45)
            else:
                ax.get_xaxis().set_ticks([])
            _annotate(ax, labels, vals, np.arange(len(callers)), width)
    fig.text(.5, .95, prep_labels[prep] if title is None else title, horizontalalignment='center', size=16)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.87, bottom=0.15, wspace=0.1, hspace=0.1)
    #fig.tight_layout()
    x, y = (10, 5) if size is None else size
    fig.set_size_inches(x, y)
    fig.savefig(out_file)

def _get_chart_info(df, vtype, cat, prep, callers):
    """Retrieve values for a specific variant type, category and prep method.
    """
    maxval_raw = max(list(df["value.floor"]))
    curdf = df[(df["variant.type"] == vtype) & (df["category"] == cat)
               & (df["bamprep"] == prep)]
    vals = []
    labels = []
    for c in callers:
        row = curdf[df["caller"] == c]
        if len(row) > 0:
            vals.append(list(row["value.floor"])[0])
            labels.append(list(row["value"])[0])
        else:
            vals.append(1)
            labels.append("")
    return vals, labels, maxval_raw

def _annotate(ax, annotate, height, left, width):
    """Annotate axis with labels. Adjusted from prettyplotlib to be more configurable.
    """
    annotate_yrange_factor = 0.025
    xticks = np.array(left) + width / 2.0
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin

    # Reset ymax and ymin so there's enough room to see the annotation of
    # the top-most
    if ymax > 0:
        ymax += yrange * 0.1
    if ymin < 0:
        ymin -= yrange * 0.1
    ax.set_ylim(ymin, ymax)
    yrange = ymax - ymin

    offset_ = yrange * annotate_yrange_factor
    if isinstance(annotate, collections.Iterable):
        annotations = map(str, annotate)
    else:
        annotations = ['%.3f' % h if type(h) is np.float_ else str(h)
                       for h in height]
    for x, h, annotation in zip(xticks, height, annotations):
        # Adjust the offset to account for negative bars
        offset = offset_ if h >= 0 else -1 * offset_
        verticalalignment = 'bottom' if h >= 0 else 'top'

        if len(str(annotation)) > 6:
            size = 7
        elif len(str(annotation)) > 5:
            size = 8
        else:
            size = 10
        # Finally, add the text to the axes
        ax.annotate(annotation, (x, h + offset),
                    verticalalignment=verticalalignment,
                    horizontalalignment='center',
                    size=size,
                    color=ppl.colors.almost_black)

def _ggplot(df, out_file):
    """Plot faceted items with ggplot wrapper on top of matplotlib.
    XXX Not yet functional
    """
    import ggplot as gg
    df["variant.type"] = [vtype_labels[x] for x in df["variant.type"]]
    df["category"] = [cat_labels[x] for x in df["category"]]
    df["caller"] = [caller_labels.get(x, None) for x in df["caller"]]
    p = (gg.ggplot(df, gg.aes(x="caller", y="value.floor")) + gg.geom_bar()
         + gg.facet_wrap("variant.type", "category")
         + gg.theme_seaborn())
    gg.ggsave(p, out_file)

def get_floor_value(x, cat, vartype, floors):
    """Modify values so all have the same relative scale for differences.

    Using the chosen base heights, adjusts an individual sub-plot to be consistent
    relative to that height.
    """
    all_base = floors[vartype]
    cur_max = floors[(cat, vartype)]
    if cur_max > all_base:
        diff = cur_max - all_base
        x = max(1, x - diff)
    return x

def get_group_floors(df, cat_labels):
    """Retrieve the floor for a given row of comparisons, creating a normalized set of differences.

    We need to set non-zero floors so large numbers (like concordance) don't drown out small
    numbers (like discordance). This defines the height for a row of comparisons as either
    the minimum height of any sub-plot, or the maximum difference between higher and lower
    (plus 10%).
    """
    group_maxes = collections.defaultdict(list)
    group_diffs = collections.defaultdict(list)
    diff_pad = 0.1  # 10% padding onto difference to avoid large numbers looking like zero
    for name, group in df.groupby(["category", "variant.type"]):
        label, stype = name
        if label in cat_labels:
            diff = max(group["value"]) - min(group["value"])
            group_diffs[stype].append(diff + int(diff_pad * diff))
            group_maxes[stype].append(max(group["value"]))
        group_maxes[name].append(max(group["value"]))
    out = {}
    for k, vs in group_maxes.iteritems():
        if k in group_diffs:
            out[k] = max(max(group_diffs[stype]), min(vs))
        else:
            out[k] = min(vs)
    return out

def get_aligner(x, config):
    return utils.get_in(config, ("algorithm", "aligner"), "")

def get_bamprep(x, config):
    params = bamprep._get_prep_params({"config": {"algorithm": config.get("algorithm", {})}})
    if params["realign"] == "gatk" and params["recal"] == "gatk":
        return "gatk"
    elif not params["realign"] and not params["recal"]:
        return "none"
    else:
        raise ValueError("Unexpected bamprep approach: %s" % params)

########NEW FILE########
__FILENAME__ = varscan
"""Provide variant calling with VarScan from TGI at Wash U.

http://varscan.sourceforge.net/
"""
import contextlib
from distutils.version import LooseVersion
import os
import shutil

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do, programs
from bcbio.utils import file_exists, append_stem
from bcbio.variation import freebayes, samtools, vcfutils
from bcbio.variation.vcfutils import (combine_variant_files, write_empty_vcf,
                                      get_paired_bams, is_paired_analysis)

import pysam


def run_varscan(align_bams, items, ref_file, assoc_files,
                region=None, out_file=None):
    if is_paired_analysis(align_bams, items):
        call_file = samtools.shared_variantcall(_varscan_paired, "varscan",
                                                align_bams, ref_file, items,
                                                assoc_files, region, out_file)
    else:
        call_file = samtools.shared_variantcall(_varscan_work, "varscan",
                                                align_bams, ref_file,
                                                items, assoc_files,
                                                region, out_file)
    return call_file


def _get_varscan_opts(config):
    """Retrieve common options for running VarScan.
    Handles jvm_opts, setting user and country to English to avoid issues
    with different locales producing non-compliant VCF.
    """
    resources = config_utils.get_resources("varscan", config)
    jvm_opts = resources.get("jvm_opts", ["-Xmx750m", "-Xmx2g"])
    jvm_opts += ["-Duser.language=en", "-Duser.country=US"]
    return " ".join(jvm_opts)


def _varscan_paired(align_bams, ref_file, items, target_regions, out_file):

    """Run a paired VarScan analysis, also known as "somatic". """

    max_read_depth = "1000"
    config = items[0]["config"]

    version = programs.jar_versioner("varscan", "VarScan")(config)
    if LooseVersion(version) < LooseVersion("v2.3.6"):
        raise IOError(
            "Please install version 2.3.6 or better of VarScan with support "
            "for multisample calling and indels in VCF format.")
    varscan_jar = config_utils.get_jar(
        "VarScan",
        config_utils.get_program("varscan", config, "dir"))

    remove_zerocoverage = "grep -v -P '\t0\t\t$'"

    # No need for names in VarScan, hence the "_"

    paired = get_paired_bams(align_bams, items)
    if not paired.normal_bam:
        raise ValueError("Require both tumor and normal BAM files for VarScan cancer calling")

    if not file_exists(out_file):
        orig_out_file = out_file
        out_file = orig_out_file.replace(".vcf.gz", ".vcf")
        base, ext = utils.splitext_plus(out_file)
        cleanup_files = []
        for fname, mpext in [(paired.normal_bam, "normal"), (paired.tumor_bam, "tumor")]:
            mpfile = "%s-%s.mpileup" % (base, mpext)
            cleanup_files.append(mpfile)
            with file_transaction(mpfile) as mpfile_tx:
                mpileup = samtools.prep_mpileup([fname], ref_file,
                                                max_read_depth, config,
                                                target_regions=target_regions,
                                                want_bcf=False)
                cmd = "{mpileup} > {mpfile_tx}"
                cmd = cmd.format(**locals())
                do.run(cmd, "samtools mpileup".format(**locals()), None,
                       [do.file_exists(mpfile_tx)])

        # Sometimes mpileup writes an empty file: in this case we
        # just skip the rest of the analysis (VarScan will hang otherwise)

        if any(os.stat(filename).st_size == 0 for filename in cleanup_files):
            write_empty_vcf(orig_out_file, config)
            return

        # First index is normal, second is tumor
        normal_tmp_mpileup = cleanup_files[0]
        tumor_tmp_mpileup = cleanup_files[1]

        jvm_opts = _get_varscan_opts(config)
        varscan_cmd = ("java {jvm_opts} -jar {varscan_jar} somatic"
                       " {normal_tmp_mpileup} {tumor_tmp_mpileup} {base}"
                       " --output-vcf --min-coverage 5 --p-value 0.98 "
                       "--strand-filter 1 ")
        # add minimum AF 
        if "--min-var-freq" not in varscan_cmd:
            min_af = float(utils.get_in(paired.tumor_config, ("algorithm", 
                                                              "min_allele_fraction"),10)) / 100.0
            varscan_cmd += "--min-var-freq {min_af} "
        
        indel_file = base + ".indel.vcf"
        snp_file = base + ".snp.vcf"

        cleanup_files.append(indel_file)
        cleanup_files.append(snp_file)

        to_combine = []

        with file_transaction(indel_file, snp_file) as (tx_indel, tx_snp):
            varscan_cmd = varscan_cmd.format(**locals())
            do.run(varscan_cmd, "Varscan".format(**locals()), None,
                   None)

        # VarScan files need to be corrected to match the VCF specification
        # We do this before combining them otherwise merging may fail
        # if there are invalid records

        if do.file_exists(snp_file):
            to_combine.append(snp_file)
            _fix_varscan_vcf(snp_file, paired.normal_name, paired.tumor_name)

        if do.file_exists(indel_file):
            to_combine.append(indel_file)
            _fix_varscan_vcf(indel_file, paired.normal_name, paired.tumor_name)

        if not to_combine:
            write_empty_vcf(orig_out_file, config)
            return

        out_file = combine_variant_files([snp_file, indel_file],
                                         out_file, ref_file, config,
                                         region=target_regions)

        # Remove cleanup files

        for extra_file in cleanup_files:
            for ext in ["", ".gz", ".gz.tbi"]:
                if os.path.exists(extra_file + ext):
                    os.remove(extra_file + ext)

        if os.path.getsize(out_file) == 0:
            write_empty_vcf(out_file)

        if orig_out_file.endswith(".gz"):
            vcfutils.bgzip_and_index(out_file, config)


def _fix_varscan_vcf(orig_file, normal_name, tumor_name):
    """Fixes issues with the standard VarScan VCF output.

    - Remap sample names back to those defined in the input BAM file.
    - Convert indels into correct VCF representation.
    """
    tmp_file = append_stem(orig_file, "-origsample")

    if not file_exists(tmp_file):
        shutil.move(orig_file, tmp_file)

        with file_transaction(orig_file) as tx_out_file:
            with open(tmp_file) as in_handle:
                with open(tx_out_file, "w") as out_handle:

                    for line in in_handle:
                        line = _fix_varscan_output(line, normal_name,
                                                   tumor_name)
                        if not line:
                            continue
                        out_handle.write(line)


def _fix_varscan_output(line, normal_name, tumor_name):
    """Fix a varscan VCF line

    Fixes the ALT column and also fixes the FREQ field to be a floating point
    value, easier for filtering.

    :param line: a pre-split and stripped varscan line

    This function was contributed by Sean Davis <sdavis2@mail.nih.gov>,
    with minor modifications by Luca Beltrame <luca.beltrame@marionegri.it>.

    """
    line = line.strip()

    if(line.startswith("##")):
        line = line.replace('FREQ,Number=1,Type=String',
                            'FREQ,Number=1,Type=Float')
        return line + "\n"

    line = line.split("\t")

    mapping = {"NORMAL": normal_name, "TUMOR": tumor_name}

    if(line[0].startswith("#CHROM")):

        base_header = line[:9]
        old_samples = line[9:]

        if len(old_samples) == 0:
            return "\t".join(line) + "\n"

        samples = [mapping[sample_name] for sample_name in old_samples]

        assert len(old_samples) == len(samples)
        return "\t".join(base_header + samples) + "\n"

    try:
        REF, ALT = line[3:5]
    except ValueError:
        return "\t".join(line) + "\n"

    Ifreq = line[8].split(":").index("FREQ")
    ndat = line[9].split(":")
    tdat = line[10].split(":")
    somatic_status = line[7].split(";")  # SS=<number>
    # HACK: The position of the SS= changes, so we just search for it
    somatic_status = [item for item in somatic_status
                      if item.startswith("SS=")][0]
    somatic_status = int(somatic_status.split("=")[1])  # Get the number

    ndat[Ifreq] = str(float(ndat[Ifreq].rstrip("%")) / 100)
    tdat[Ifreq] = str(float(tdat[Ifreq].rstrip("%")) / 100)
    line[9] = ":".join(ndat)
    line[10] = ":".join(tdat)

    #FIXME: VarScan also produces invalid REF records (e.g. CAA/A)
    # This is not handled yet.

    if somatic_status == 5:

        # "Unknown" states are broken in current versions of VarScan
        # so we just bail out here for now

        return

    if "+" in ALT or "-" in ALT:
        if "/" not in ALT:
            if ALT[0] == "+":
                R = REF
                A = REF + ALT[1:]
            elif ALT[0] == "-":
                R = REF + ALT[1:]
                A = REF
        else:
            Ins = [p[1:] for p in ALT.split("/") if p[0] == "+"]
            Del = [p[1:] for p in ALT.split("/") if p[0] == "-"]

            if len(Del):
                REF += sorted(Del, key=lambda x: len(x))[-1]

            A = ",".join([REF[::-1].replace(p[::-1], "", 1)[::-1]
                          for p in Del] + [REF + p for p in Ins])
            R = REF

        REF = R
        ALT = A
    else:
        ALT = ALT.replace('/', ',')

    line[3] = REF
    line[4] = ALT
    return "\t".join(line) + "\n"


def _create_sample_list(in_bams, vcf_file):
    """Pull sample names from input BAMs and create input sample list.
    """
    out_file = "%s-sample_list.txt" % os.path.splitext(vcf_file)[0]
    with open(out_file, "w") as out_handle:
        for in_bam in in_bams:
            with contextlib.closing(pysam.Samfile(in_bam, "rb")) as work_bam:
                for rg in work_bam.header.get("RG", []):
                    out_handle.write("%s\n" % rg["SM"])
    return out_file


def _varscan_work(align_bams, ref_file, items, target_regions, out_file):
    """Perform SNP and indel genotyping with VarScan.
    """
    config = items[0]["config"]

    orig_out_file = out_file
    out_file = orig_out_file.replace(".vcf.gz", ".vcf")

    max_read_depth = "1000"
    version = programs.jar_versioner("varscan", "VarScan")(config)
    if version < "v2.3.6":
        raise IOError("Please install version 2.3.6 or better of VarScan"
                      " with support for multisample calling and indels"
                      " in VCF format.")
    varscan_jar = config_utils.get_jar("VarScan",
                                       config_utils.get_program("varscan", config, "dir"))
    jvm_opts = _get_varscan_opts(config)
    sample_list = _create_sample_list(align_bams, out_file)
    mpileup = samtools.prep_mpileup(align_bams, ref_file, max_read_depth, config,
                                    target_regions=target_regions, want_bcf=False)
    # VarScan fails to generate a header on files that start with
    # zerocoverage calls; strip these with grep, we're not going to
    # call on them
    remove_zerocoverage = "grep -v -P '\t0\t\t$'"
    # write a temporary mpileup file so we can check if empty
    mpfile = "%s.mpileup" % os.path.splitext(out_file)[0]
    with file_transaction(mpfile) as mpfile_tx:
        cmd = ("{mpileup} | {remove_zerocoverage} > {mpfile_tx}")
        do.run(cmd.format(**locals()), "mpileup for Varscan")
    if os.path.getsize(mpfile) == 0:
        write_empty_vcf(out_file)
    else:
        cmd = ("cat {mpfile} "
               "| java {jvm_opts} -jar {varscan_jar} mpileup2cns --min-coverage 5 --p-value 0.98 "
               "  --vcf-sample-list {sample_list} --output-vcf --variants "
               "> {out_file}")
        do.run(cmd.format(**locals()), "Varscan", None,
               [do.file_exists(out_file)])
    os.remove(sample_list)
    os.remove(mpfile)
    # VarScan can create completely empty files in regions without
    # variants, so we create a correctly formatted empty file
    if os.path.getsize(out_file) == 0:
        write_empty_vcf(out_file)
    else:
        freebayes.clean_vcf_output(out_file, _clean_varscan_line)

    if orig_out_file.endswith(".gz"):
        vcfutils.bgzip_and_index(out_file, config)

def _clean_varscan_line(line):
    """Avoid lines with non-GATC bases, ambiguous output bases make GATK unhappy.
    """
    if not line.startswith("#"):
        parts = line.split("\t")
        alleles = [x.strip() for x in parts[4].split(",")] + [parts[3].strip()]
        for a in alleles:
            if len(set(a) - set("GATCgatc")) > 0:
                return None
    return line

########NEW FILE########
__FILENAME__ = vcfutils
"""Utilities for manipulating variant files in standard VCF format.
"""

from collections import namedtuple, defaultdict
import copy
import gzip
import itertools
import os
import subprocess

import toolz as tz

from bcbio import broad, utils
from bcbio.bam import ref
from bcbio.distributed.multi import run_multicore, zeromq_aware_logging
from bcbio.distributed.split import parallel_split_combine
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, shared, tools
from bcbio.provenance import do
from bcbio.variation import bamprep

# ## Tumor/normal paired cancer analyses

PairedData = namedtuple("PairedData", ["tumor_bam", "tumor_name",
                                       "normal_bam", "normal_name", "normal_panel",
                                       "tumor_config"])

def is_paired_analysis(align_bams, items):
    """Determine if BAMs are from a tumor/normal paired analysis.
    """
    return get_paired_bams(align_bams, items) is not None

def get_paired_bams(align_bams, items):
    """Split aligned bams into tumor / normal pairs if this is a paired analysis.
    Allows cases with only tumor BAMs to handle callers that can work without
    normal BAMs or with normal VCF panels.
    """
    tumor_bam, normal_bam, normal_name, normal_panel, tumor_config = None, None, None, None, None
    for bamfile, item in itertools.izip(align_bams, items):
        phenotype = get_paired_phenotype(item)
        if phenotype == "normal":
            normal_bam = bamfile
            normal_name = item["name"][1]
        elif phenotype == "tumor":
            tumor_bam = bamfile
            tumor_name = item["name"][1]
            tumor_config = item["config"]
            normal_panel = item["config"]["algorithm"].get("background")
    if tumor_bam:
        return PairedData(tumor_bam, tumor_name, normal_bam,
                          normal_name, normal_panel, tumor_config)

def get_paired_phenotype(data):
    """Retrieve the phenotype for a paired tumor/normal analysis.
    """
    allowed_names = set(["tumor", "normal"])
    p = data.get("metadata", {}).get("phenotype")
    return p if p in allowed_names else None

# ## General utilities

def write_empty_vcf(out_file, config=None):
    needs_bgzip = False
    if out_file.endswith(".vcf.gz"):
        needs_bgzip = True
        out_file = out_file.replace(".vcf.gz", ".vcf")
    with open(out_file, "w") as out_handle:
        out_handle.write("##fileformat=VCFv4.1\n"
                         "## No variants; no reads aligned in region\n"
                         "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
    if needs_bgzip:
        return bgzip_and_index(out_file, config or {})
    else:
        return out_file

def split_snps_indels(orig_file, ref_file, config):
    """Split a variant call file into SNPs and INDELs for processing.
    """
    base, ext = utils.splitext_plus(orig_file)
    snp_file = "{base}-snp{ext}".format(base=base, ext=ext)
    indel_file = "{base}-indel{ext}".format(base=base, ext=ext)
    for out_file, select_arg in [(snp_file, "--types snps"),
                                 (indel_file, "--exclude-types snps")]:
        if not utils.file_exists(out_file):
            with file_transaction(out_file) as tx_out_file:
                bcftools = config_utils.get_program("bcftools", config)
                output_type = "z" if out_file.endswith(".gz") else "v"
                cmd = "{bcftools} view -O {output_type} {orig_file} {select_arg} > {tx_out_file}"
                do.run(cmd.format(**locals()), "Subset to SNPs and indels")
        if out_file.endswith(".gz"):
            bgzip_and_index(out_file, config)
    return snp_file, indel_file

def get_samples(in_file):
    """Retrieve samples present in a VCF file
    """
    with (gzip.open(in_file) if in_file.endswith(".gz") else open(in_file)) as in_handle:
        for line in in_handle:
            if line.startswith("#CHROM"):
                parts = line.strip().split("\t")
                return parts[9:]
    raise ValueError("Did not find sample header in VCF file %s" % in_file)

def _get_exclude_samples(in_file, to_exclude):
    """Identify samples in the exclusion list which are actually in the VCF.
    """
    include, exclude = [], []
    to_exclude = set(to_exclude)
    for s in get_samples(in_file):
        if s in to_exclude:
            exclude.append(s)
        else:
            include.append(s)
    return include, exclude

def exclude_samples(in_file, out_file, to_exclude, ref_file, config):
    """Exclude specific samples from an input VCF file.
    """
    include, exclude = _get_exclude_samples(in_file, to_exclude)
    # can use the input sample, all exclusions already gone
    if len(exclude) == 0:
        out_file = in_file
    elif not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            bcftools = config_utils.get_program("bcftools", config)
            output_type = "z" if out_file.endswith(".gz") else "v"
            include_str = ",".join(include)
            cmd = "{bcftools} view -O {output_type} -s {include_str} {in_file} > {tx_out_file}"
            do.run(cmd.format(**locals()), "Exclude samples: {}".format(to_exclude))
    return out_file

def select_sample(in_file, sample, out_file, config):
    """Select a single sample from the supplied multisample VCF file.
    """
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            if in_file.endswith(".gz"):
                bgzip_and_index(in_file, config)
            bcftools = config_utils.get_program("bcftools", config)
            output_type = "z" if out_file.endswith(".gz") else "v"
            cmd = "{bcftools} view -O {output_type} {in_file} -s {sample} > {tx_out_file}"
            do.run(cmd.format(**locals()), "Select sample: %s" % sample)
    if out_file.endswith(".gz"):
        bgzip_and_index(out_file, config)
    return out_file

def vcf_has_variants(in_file):
    if os.path.exists(in_file):
        with (gzip.open(in_file) if in_file.endswith(".gz") else open(in_file)) as in_handle:
            for line in in_handle:
                if line.strip() and not line.startswith("#"):
                    return True
    return False

# ## Merging of variant files

def merge_variant_files(orig_files, out_file, ref_file, config, region=None):
    """Combine multiple VCF files with different samples into a single output file.

    Uses bcftools merge on bgzipped input files, handling both tricky merge and
    concatenation of files. Does not correctly handle files with the same
    sample (use combine_variant_files instead).
    """
    in_pipeline = False
    if isinstance(orig_files, dict):
        file_key = config["file_key"]
        in_pipeline = True
        orig_files = orig_files[file_key]
    out_file = _do_merge(orig_files, out_file, config, region)
    if in_pipeline:
        return [{file_key: out_file, "region": region, "sam_ref": ref_file, "config": config}]
    else:
        return out_file

def _do_merge(orig_files, out_file, config, region):
    """Do the actual work of merging with bcftools merge.
    """
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            _check_samples_nodups(orig_files)
            prep_files = run_multicore(p_bgzip_and_index, [[x, config] for x in orig_files], config)
            input_vcf_file = "%s-files.txt" % utils.splitext_plus(out_file)[0]
            with open(input_vcf_file, "w") as out_handle:
                for fname in prep_files:
                    out_handle.write(fname + "\n")
            bcftools = config_utils.get_program("bcftools", config)
            output_type = "z" if out_file.endswith(".gz") else "v"
            region_str = "-r {}".format(region) if region else ""
            cmd = "{bcftools} merge -O {output_type} {region_str} `cat {input_vcf_file}` > {tx_out_file}"
            do.run(cmd.format(**locals()), "Merge variants")
    if out_file.endswith(".gz"):
        bgzip_and_index(out_file, config)
    return out_file

def _check_samples_nodups(fnames):
    """Ensure a set of input VCFs do not have duplicate samples.
    """
    counts = defaultdict(int)
    for f in fnames:
        for s in get_samples(f):
            counts[s] += 1
    duplicates = [s for s, c in counts.iteritems() if c > 1]
    if duplicates:
        raise ValueError("Duplicate samples found in inputs %s: %s" % (duplicates, fnames))

def _sort_by_region(fnames, regions, ref_file, config):
    """Sort a set of regionally split files by region for ordered output.
    """
    contig_order = {}
    for i, sq in enumerate(ref.file_contigs(ref_file, config)):
        contig_order[sq.name] = i
    sitems = []
    for region, fname in zip(regions, fnames):
        if isinstance(region, (list, tuple)):
            c, s, e = region
        else:
            c = region
            s, e = 0, 0
        sitems.append(((contig_order[c], s, e), fname))
    sitems.sort()
    return [x[1] for x in sitems]

def concat_variant_files(orig_files, out_file, regions, ref_file, config):
    """Concatenate multiple variant files from regions into a single output file.

    Lightweight approach to merging VCF files split by regions with the same
    sample information, so no complex merging needed. Handles both plain text
    and bgzipped/tabix indexed outputs.
    """
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            sorted_files = _sort_by_region(orig_files, regions, ref_file, config)
            filtered_files = [x for x in sorted_files if vcf_has_variants(x)]
            if len(filtered_files) > 0 and filtered_files[0].endswith(".gz"):
                filtered_files = run_multicore(p_bgzip_and_index, [[x, config] for x in filtered_files], config)
            input_vcf_file = "%s-files.txt" % utils.splitext_plus(out_file)[0]
            with open(input_vcf_file, "w") as out_handle:
                for fname in filtered_files:
                    out_handle.write(fname + "\n")
            if len(filtered_files) > 0:
                compress_str = "| bgzip -c " if out_file.endswith(".gz") else ""
                cmd = "vcfcat `cat {input_vcf_file}` {compress_str} > {tx_out_file}"
                do.run(cmd.format(**locals()), "Concatenate variants")
            else:
                write_empty_vcf(tx_out_file)
    if out_file.endswith(".gz"):
        bgzip_and_index(out_file, config)
    return out_file

def combine_variant_files(orig_files, out_file, ref_file, config,
                          quiet_out=True, region=None):
    """Combine VCF files from the same sample into a single output file.

    Handles cases where we split files into SNPs/Indels for processing then
    need to merge back into a final file.
    """
    in_pipeline = False
    if isinstance(orig_files, dict):
        file_key = config["file_key"]
        in_pipeline = True
        orig_files = orig_files[file_key]
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            ready_files = run_multicore(p_bgzip_and_index, [[x, config] for x in orig_files], config)
            params = ["-T", "CombineVariants",
                      "-R", ref_file,
                      "--out", tx_out_file]
            priority_order = []
            for i, ready_file in enumerate(ready_files):
                name = "v%s" % i
                params.extend(["--variant:{name}".format(name=name), ready_file])
                priority_order.append(name)
            params.extend(["--rod_priority_list", ",".join(priority_order)])
            if quiet_out:
                params.extend(["--suppressCommandLineHeader", "--setKey", "null"])
            variant_regions = config["algorithm"].get("variant_regions", None)
            cur_region = shared.subset_variant_regions(variant_regions, region, out_file)
            if cur_region:
                params += ["-L", bamprep.region_to_gatk(cur_region),
                           "--interval_set_rule", "INTERSECTION"]
            jvm_opts = broad.get_gatk_framework_opts(config)
            cmd = [config_utils.get_program("gatk-framework", config)] + jvm_opts + params
            do.run(cmd, "Combine variant files")
    if out_file.endswith(".gz"):
        bgzip_and_index(out_file, config)
    if in_pipeline:
        return [{file_key: out_file, "region": region, "sam_ref": ref_file, "config": config}]
    else:
        return out_file

def sort_by_ref(vcf_file, data):
    """Sort a VCF file by genome reference and position.
    """
    out_file = "%s-prep%s" % utils.splitext_plus(vcf_file)
    if not utils.file_exists(out_file):
        bv_jar = config_utils.get_jar("bcbio.variation",
                                      config_utils.get_program("bcbio_variation", data["config"], "dir"))
        resources = config_utils.get_resources("bcbio_variation", data["config"])
        jvm_opts = resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"])
        cmd = ["java"] + jvm_opts + ["-jar", bv_jar, "variant-utils", "sort-vcf",
                                     vcf_file, tz.get_in(["reference", "fasta", "base"], data), "--sortpos"]
        do.run(cmd, "Sort VCF by reference")
    return out_file

# ## Parallel VCF file combining

def parallel_combine_variants(orig_files, out_file, ref_file, config, run_parallel):
    """Combine variants in parallel by chromosome, concatenating final outputs.
    """
    file_key = "vcf_files"
    def split_by_region(data):
        base, ext = utils.splitext_plus(os.path.basename(out_file))
        args = []
        for region in [x.name for x in ref.file_contigs(ref_file, config)]:
            region_out = os.path.join(os.path.dirname(out_file), "%s-regions" % base,
                                      "%s-%s%s" % (base, region, ext))
            utils.safe_makedir(os.path.dirname(region_out))
            args.append((region_out, ref_file, config, region))
        return out_file, args
    config = copy.deepcopy(config)
    config["file_key"] = file_key
    prep_files = run_multicore(p_bgzip_and_index, [[x, config] for x in orig_files], config)
    items = [[{file_key: prep_files}]]
    parallel_split_combine(items, split_by_region, run_parallel,
                           "merge_variant_files", "concat_variant_files",
                           file_key, ["region", "sam_ref", "config"], split_outfile_i=0)
    return out_file

# ## VCF preparation

def bgzip_and_index(in_file, config, remove_orig=True):
    """bgzip and tabix index an input file, handling VCF and BED.
    """
    out_file = in_file if in_file.endswith(".gz") else in_file + ".gz"
    if not utils.file_exists(out_file) or not os.path.lexists(out_file):
        assert not in_file == out_file, "Input file is bgzipped but not found: %s" % in_file
        with file_transaction(out_file) as tx_out_file:
            bgzip = tools.get_bgzip_cmd(config)
            cmd = "{bgzip} -c {in_file} > {tx_out_file}"
            try:
                do.run(cmd.format(**locals()), "bgzip %s" % os.path.basename(in_file))
            except subprocess.CalledProcessError:
                # Race conditions: ignore errors where file has been deleted by another
                if os.path.exists(in_file) and not os.path.exists(out_file):
                    raise
        if remove_orig:
            try:
                os.remove(in_file)
            except OSError:  # Handle cases where run in parallel and file has been deleted
                pass
    tabix_index(out_file, config)
    return out_file

@utils.map_wrap
@zeromq_aware_logging
def p_bgzip_and_index(in_file, config):
    """Parallel-aware bgzip and indexing
    """
    return [bgzip_and_index(in_file, config)]

def _guess_preset(f):
    if f.lower().endswith(".vcf.gz"):
        return "vcf"
    elif f.lower().endswith(".bed.gz"):
        return "bed"
    elif f.lower().endswith(".gff.gz"):
        return "gff"
    else:
        raise ValueError("Unexpected tabix input: %s" % f)

def tabix_index(in_file, config, preset=None):
    """Index a file using tabix.
    """
    preset = _guess_preset(in_file) if preset is None else preset
    in_file = os.path.abspath(in_file)
    out_file = in_file + ".tbi"
    if not utils.file_exists(out_file) or not utils.file_uptodate(out_file, in_file):
        try:
            os.remove(out_file)
        except OSError:
            pass
        with file_transaction(out_file) as tx_out_file:
            tabix = tools.get_tabix_cmd(config)
            tx_in_file = os.path.splitext(tx_out_file)[0]
            utils.symlink_plus(in_file, tx_in_file)
            cmd = "{tabix} -f -p {preset} {tx_in_file}"
            do.run(cmd.format(**locals()), "tabix index %s" % os.path.basename(in_file))
    return out_file

########NEW FILE########
__FILENAME__ = vfilter
"""Hard filtering of genomic variants.
"""
from distutils.version import LooseVersion
import math
import os
import shutil

import numpy
import toolz as tz
import vcf
import yaml

from bcbio import broad, utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.provenance import do, programs
from bcbio.variation import vcfutils

# ## General functionality

def hard_w_expression(vcf_file, expression, data, name="+", filterext=""):
    """Perform hard filtering using bcftools expressions like %QUAL < 20 || DP < 4.
    """
    base, ext = utils.splitext_plus(vcf_file)
    out_file = "{base}-filter{filterext}{ext}".format(**locals())
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            if vcfutils.vcf_has_variants(vcf_file):
                bcftools = config_utils.get_program("bcftools", data["config"])
                output_type = "z" if out_file.endswith(".gz") else "v"
                variant_regions = utils.get_in(data, ("config", "algorithm", "variant_regions"))
                intervals = ("-T %s" % vcfutils.bgzip_and_index(variant_regions, data["config"])
                             if variant_regions else "")
                cmd = ("{bcftools} filter -O {output_type} {intervals} --soft-filter '{name}' "
                       "-e '{expression}' -m '+' {vcf_file} > {tx_out_file}")
                do.run(cmd.format(**locals()), "Hard filtering %s with %s" % (vcf_file, expression), data)
            else:
                shutil.copy(vcf_file, out_file)
    if out_file.endswith(".vcf.gz"):
        out_file = vcfutils.bgzip_and_index(out_file, data["config"])
    return out_file

def genotype_filter(vcf_file, expression, data, name, filterext=""):
    """Perform genotype based filtering using GATK with the provided expression.

    Adds FT tags to genotypes, rather than the general FILTER flag.
    """
    base, ext = utils.splitext_plus(vcf_file)
    out_file = "{base}-filter{filterext}{ext}".format(**locals())
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "VariantFiltration",
                      "-R", tz.get_in(["reference", "fasta", "base"], data),
                      "--variant", vcf_file,
                      "--out", tx_out_file,
                      "--genotypeFilterName", name,
                      "--genotypeFilterExpression", "'%s'" % expression]
            jvm_opts = broad.get_gatk_framework_opts(data["config"])
            cmd = [config_utils.get_program("gatk-framework", data["config"])] + jvm_opts + params
            do.run(cmd, "Filter with expression: %s" % expression)
    if out_file.endswith(".vcf.gz"):
        out_file = vcfutils.bgzip_and_index(out_file, data["config"])
    return out_file

# ## Caller specific

def freebayes(in_file, ref_file, vrn_files, data):
    """FreeBayes filters: trying custom filter approach before falling back on hard filtering.
    """
    out_file = _freebayes_hard(in_file, data)
    #out_file = _freebayes_custom(in_file, ref_file, data)
    return out_file

def _freebayes_custom(in_file, ref_file, data):
    """Custom FreeBayes filtering using bcbio.variation, tuned to human NA12878 results.

    Experimental: for testing new methods.
    """
    if vcfutils.get_paired_phenotype(data):
        return None
    config = data["config"]
    bv_ver = programs.get_version("bcbio_variation", config=config)
    if LooseVersion(bv_ver) < LooseVersion("0.1.1"):
        return None
    out_file = "%s-filter%s" % os.path.splitext(in_file)
    if not utils.file_exists(out_file):
        tmp_dir = utils.safe_makedir(os.path.join(os.path.dirname(in_file), "tmp"))
        bv_jar = config_utils.get_jar("bcbio.variation",
                                      config_utils.get_program("bcbio_variation", config, "dir"))
        resources = config_utils.get_resources("bcbio_variation", config)
        jvm_opts = resources.get("jvm_opts", ["-Xms750m", "-Xmx2g"])
        java_args = ["-Djava.io.tmpdir=%s" % tmp_dir]
        cmd = ["java"] + jvm_opts + java_args + ["-jar", bv_jar, "variant-filter", "freebayes",
                                                 in_file, ref_file]
        do.run(cmd, "Custom FreeBayes filtering using bcbio.variation")
    return out_file

def _freebayes_hard(in_file, data):
    """Perform filtering of FreeBayes results, removing low confidence calls.

    Filters using cutoffs on low depth based on Meynert et al's work modeling sensitivity
    of homozygote and heterozygote calling on depth:

    http://www.ncbi.nlm.nih.gov/pubmed/23773188

    and high depth heterozygote SNP filtering based on Heng Li's work
    evaluating variant calling artifacts:

    http://arxiv.org/abs/1404.0929

    Tuned based on NA12878 call comparisons to Genome in a Bottle reference genome.
    """
    stats = _calc_vcf_stats(in_file)
    depth_thresh = int(math.ceil(stats["avg_depth"] + 3 * math.pow(stats["avg_depth"], 0.5)))
    qual_thresh = depth_thresh * 2.0  # Multiplier from default GATK QD hard filter
    filters = ('(AF[0] <= 0.5 && (DP < 4 || (DP < 13 && %QUAL < 10))) || '
               '(AF[0] > 0.5 && (DP < 4 && %QUAL < 50)) || '
               '(%QUAL < {qual_thresh} && DP > {depth_thresh} && AF[0] <= 0.5)'
               .format(**locals()))
    return hard_w_expression(in_file, filters, data, name="FBQualDepth")

def _calc_vcf_stats(in_file):
    """Calculate statistics on VCF for filtering, saving to a file for quick re-runs.
    """
    out_file = "%s-stats.yaml" % utils.splitext_plus(in_file)[0]
    if not utils.file_exists(out_file):
        stats = {"avg_depth": _average_called_depth(in_file)}
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(stats, out_handle, default_flow_style=False, allow_unicode=False)
        return stats
    else:
        with open(out_file) as in_handle:
            stats = yaml.safe_load(in_handle)
        return stats

def _average_called_depth(in_file):
    """Retrieve the average depth of called reads in the provided VCF.
    """
    depths = []
    with utils.open_gzipsafe(in_file) as in_handle:
        reader = vcf.Reader(in_handle, in_file)
        for rec in reader:
            d = rec.INFO.get("DP")
            if d is not None:
                depths.append(d)
    return int(math.ceil(numpy.mean(depths)))

def gatk_snp_hard(in_file, data):
    """Perform hard filtering on GATK SNPs using best-practice recommendations.
    """
    filters = ["QD < 2.0", "MQ < 40.0", "FS > 60.0",
               "MQRankSum < -12.5", "ReadPosRankSum < -8.0"]
    # GATK Haplotype caller (v2.2) appears to have much larger HaplotypeScores
    # resulting in excessive filtering, so avoid this metric
    variantcaller = utils.get_in(data, ("config", "algorithm", "variantcaller"), "gatk")
    if variantcaller not in ["gatk-haplotype"]:
        filters.append("HaplotypeScore > 13.0")
    return hard_w_expression(in_file, " || ".join(filters), data, "GATKHardSNP", "SNP")

def gatk_indel_hard(in_file, data):
    """Perform hard filtering on GATK indels using best-practice recommendations.
    """
    filters = ["QD < 2.0", "ReadPosRankSum < -20.0", "FS > 200.0"]
    return hard_w_expression(in_file, " || ".join(filters), data, "GATKHardIndel", "INDEL")

########NEW FILE########
__FILENAME__ = stormseq
"""Prepare a workflow for running on AWS using STORMSeq as a front end.

http://www.stormseq.org/
"""
import argparse
import json
import os

import yaml

from bcbio import utils
from bcbio.upload import s3
from bcbio.workflow import xprize

def parse_args(args):
    parser = xprize.HelpArgParser(description="Run STORMSeq processing on AWS")
    parser.add_argument("config_file", help="JSON configuration file with form parameters")
    parser.add_argument("base_dir", help="Base directory to process in")
    parser.add_argument("bcbio_config_file", help="bcbio system YAML config")
    args = parser.parse_args(args)
    return args

def _get_s3_files(local_dir, file_info, params):
    """Retrieve s3 files to local directory, handling STORMSeq inputs.
    """
    assert len(file_info) == 1
    files = file_info.values()[0]
    fnames = []
    for k in ["1", "2"]:
        if files[k] not in fnames:
            fnames.append(files[k])
    out = []
    for fname in fnames:
        bucket, key = fname.replace("s3://", "").split("/", 1)
        if params["access_key_id"] == "TEST":
            out.append(os.path.join(local_dir, os.path.basename(key)))
        else:
            out.append(s3.get_file(local_dir, bucket, key, params))
    return out

def setup(args):
    configdir = utils.safe_makedir(os.path.join(args.base_dir, "config"))
    inputdir = utils.safe_makedir(os.path.join(args.base_dir, "inputs"))
    workdir = utils.safe_makedir(os.path.join(args.base_dir, "work"))
    finaldir = utils.safe_makedir(os.path.join(args.base_dir, "ready"))
    out_config_file = os.path.join(configdir, "%s.yaml" %
                                   os.path.splitext(os.path.basename(args.config_file))[0])
    with open(args.config_file) as in_handle:
        ss_config = json.load(in_handle)
        ss_params = ss_config["parameters"]
    out = {"fc_date": xprize.get_fc_date(out_config_file),
           "fc_name": ss_config["sample"],
           "upload": {"dir": finaldir,
                      "method": "s3",
                      "bucket": ss_params["s3_bucket"],
                      "access_key_id": ss_params["access_key_id"],
                      "secret_access_key": ss_params["secret_access_key"]},
            "details": [{
                "files": _get_s3_files(inputdir, ss_config["files"], ss_params),
                "lane": 1,
                "description": ss_params["sample"],
                "analysis": "variant",
                "genome_build": ss_params["genome_version"],
                "algorithm": {
                    "aligner": ss_params["alignment_pipeline"],
                    "variantcaller": ss_params["calling_pipeline"],
                    "quality_format": "Standard",
                    "coverage_interval": "genome" if ss_params["data_type"] == "data_wgs" else "exome",
                    }}]}
    with open(out_config_file, "w") as out_handle:
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)

    return workdir, {"config_file": args.bcbio_config_file,
                     "run_info_yaml": out_config_file}

########NEW FILE########
__FILENAME__ = template
"""Create bcbio_sample.yaml files from standard templates and lists of input files.

Provides an automated way to generate a full set of analysis files from an input
YAML template. Default templates are provided for common approaches which can be tweaked
as needed.
"""
import collections
import contextlib
import copy
import csv
import datetime
import glob
import itertools
import os
import shutil
import urllib2

import yaml

from bcbio import utils
from bcbio.bam import fastq, sample_name
from bcbio.pipeline import run_info
from bcbio.workflow.xprize import HelpArgParser

def parse_args(inputs):
    parser = HelpArgParser(
        description="Create a bcbio_sample.yaml file from a standard template and inputs")
    parser.add_argument("template", help=("Template name or path to template YAML file. "
                                          "Built in choices: freebayes-variant, gatk-variant, tumor-paired, "
                                          "noalign-variant, illumina-rnaseq, illumina-chipseq"))
    parser.add_argument("metadata", help="CSV file with project metadata. Name of file used as project name.")
    parser.add_argument("input_files", nargs="*", help="Input read files, in BAM or fastq format")
    return parser.parse_args(inputs)

# ## Prepare sequence data inputs

def _prep_bam_input(f, i, base):
    if not os.path.exists(f):
        raise ValueError("Could not find input file: %s" % f)
    cur = copy.deepcopy(base)
    cur["files"] = [os.path.abspath(f)]
    cur["description"] = ((sample_name(f) if f.endswith(".bam") else None)
                          or os.path.splitext(os.path.basename(f))[0])
    return cur

def _prep_fastq_input(fs, base):
    for f in fs:
        if not os.path.exists(f):
            raise ValueError("Could not find input file: %s" % f)
    cur = copy.deepcopy(base)
    cur["files"] = [os.path.abspath(f) for f in fs]
    d = os.path.commonprefix([utils.splitext_plus(os.path.basename(f))[0] for f in fs])
    cur["description"] = fastq.rstrip_extra(d)
    return cur

def _prep_items_from_base(base, in_files):
    """Prepare a set of configuration items for input files.
    """
    details = []
    known_exts = {".bam": "bam", ".cram": "bam", ".fq": "fastq",
                  ".fastq": "fastq", ".txt": "fastq",
                  ".fastq.gz": "fastq", ".fq.gz": "fastq",
                  ".txt.gz": "fastq", ".gz": "fastq"}
    in_files = _expand_dirs(in_files, known_exts)
    in_files = _expand_wildcards(in_files)

    for i, (ext, files) in enumerate(itertools.groupby(
            in_files, lambda x: known_exts.get(utils.splitext_plus(x)[-1].lower()))):
        if ext == "bam":
            for f in files:
                details.append(_prep_bam_input(f, i, base))
        elif ext == "fastq":
            files = list(files)
            for fs in fastq.combine_pairs(files):
                details.append(_prep_fastq_input(fs, base))
        else:
            raise ValueError("Unexpected input file types: %s" % str(files))
    return details

def _expand_file(x):
    return os.path.abspath(os.path.normpath(os.path.expanduser(os.path.expandvars(x))))

def _expand_dirs(in_files, known_exts):
    def _is_dir(in_file):
        return os.path.isdir(os.path.expanduser(in_file))
    files, dirs = utils.partition(_is_dir, in_files)
    for dir in dirs:
        for ext in known_exts.keys():
            wildcard = os.path.join(os.path.expanduser(dir), "*" + ext)
            files = itertools.chain(glob.glob(wildcard), files)
    return list(files)

def _expand_wildcards(in_files):
    def _has_wildcard(in_file):
        return "*" in in_file

    files, wildcards = utils.partition(_has_wildcard, in_files)
    for wc in wildcards:
        abs_path = os.path.expanduser(wc)
        files = itertools.chain(glob.glob(abs_path), files)
    return list(files)

# ## Read and write configuration files

def name_to_config(template):
    """Read template file into a dictionary to use as base for all samples.

    Handles well-known template names, pulled from GitHub repository and local
    files.
    """
    if os.path.isfile(template):
        with open(template) as in_handle:
            txt_config = in_handle.read()
        with open(template) as in_handle:
            config = yaml.load(in_handle)
    else:
        base_url = "https://raw.github.com/chapmanb/bcbio-nextgen/master/config/templates/%s.yaml"
        try:
            with contextlib.closing(urllib2.urlopen(base_url % template)) as in_handle:
                txt_config = in_handle.read()
            with contextlib.closing(urllib2.urlopen(base_url % template)) as in_handle:
                config = yaml.load(in_handle)
        except (urllib2.HTTPError, urllib2.URLError):
            raise ValueError("Could not find template '%s' locally or in standard templates on GitHub"
                             % template)
    return config, txt_config

def _write_template_config(template_txt, project_name, out_dir):
    config_dir = utils.safe_makedir(os.path.join(out_dir, "config"))
    out_config_file = os.path.join(config_dir, "%s-template.yaml" % project_name)
    with open(out_config_file, "w") as out_handle:
        out_handle.write(template_txt)
    return out_config_file

def _write_config_file(items, global_vars, template, project_name, out_dir):
    """Write configuration file, adding required top level attributes.
    """
    config_dir = utils.safe_makedir(os.path.join(out_dir, "config"))
    out_config_file = os.path.join(config_dir, "%s.yaml" % project_name)
    out = {"fc_date": datetime.datetime.now().strftime("%Y-%m-%d"),
           "fc_name": project_name,
           "upload": {"dir": "../final"},
           "details": items}
    if global_vars:
        out["globals"] = global_vars
    for k, v in template.iteritems():
        if k not in ["details"]:
            out[k] = v
    if os.path.exists(out_config_file):
        shutil.move(out_config_file,
                    out_config_file + ".bak%s" % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
    with open(out_config_file, "w") as out_handle:
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_config_file

def _safe_name(x):
    for prob in [" ", "."]:
        x = x.replace(prob, "_")
    return x

def _set_global_vars(metadata):
    """Identify files used multiple times in metadata and replace with global variables
    """
    fnames = collections.defaultdict(list)
    for sample in metadata.keys():
        for k, v in metadata[sample].items():
            print k, v
            if os.path.isfile(v):
                v = _expand_file(v)
                metadata[sample][k] = v
                fnames[v].append(k)
    loc_counts = collections.defaultdict(int)
    global_vars = {}
    global_var_sub = {}
    for fname, locs in fnames.items():
        if len(locs) > 1:
            loc_counts[locs[0]] += 1
            name = "%s%s" % (locs[0], loc_counts[locs[0]])
            global_var_sub[fname] = name
            global_vars[name] = fname
    for sample in metadata.keys():
        for k, v in metadata[sample].items():
            if v in global_var_sub:
                metadata[sample][k] = global_var_sub[v]
    return metadata, global_vars

def _parse_metadata(in_file):
    """Reads metadata from a simple CSV structured input file.

    samplename,batch,phenotype
    ERR256785,batch1,normal
    """
    metadata = {}
    with open(in_file) as in_handle:
        reader = csv.reader(in_handle)
        while 1:
            header = reader.next()
            if not header[0].startswith("#"):
                break
        keys = [x.strip() for x in header[1:]]
        for sinfo in (x for x in reader if not x[0].startswith("#")):
            sample = sinfo[0].strip()
            metadata[sample] = dict(zip(keys, (x.strip() for x in sinfo[1:])))
    metadata, global_vars = _set_global_vars(metadata)
    return metadata, global_vars

def _pname_and_metadata(in_file):
    """Retrieve metadata and project name from the input metadata CSV file.

    Uses the input file name for the project name and

    For back compatibility, accepts the project name as an input, providing no metadata.
    """
    if not os.path.isfile(in_file):
        return _safe_name(in_file), {}, {}
    else:
        md, global_vars = _parse_metadata(in_file)
        return (_safe_name(os.path.splitext(os.path.basename(in_file))[0]),
                md, global_vars)

def _handle_special_yaml_cases(v):
    """Handle values that pass integer, boolean or list values.
    """
    if ";" in v:
        v = v.split(";")
    else:
        try:
            v = int(v)
        except ValueError:
            if v.lower() == "true":
                v = True
            elif v.lower() == "false":
                    v = False
    return v

def _add_metadata(item, metadata):
    """Add metadata information from CSV file to current item.

    Retrieves metadata based on 'description' parsed from input CSV file.
    Adds to object and handles special keys:
    - `description`: A new description for the item. Used to relabel items
       based on the pre-determined description from fastq name or BAM read groups.
    - Keys matching supported names in the algorithm section map
      to key/value pairs there instead of metadata.
    """
    item_md = metadata.get(item["description"],
                           metadata.get(os.path.basename(item["files"][0]), {}))
    TOP_LEVEL = set(["description", "genome_build"])
    if len(item_md) > 0:
        if "metadata" not in item:
            item["metadata"] = {}
        for k, v in item_md.iteritems():
            if v:
                v = _handle_special_yaml_cases(v)
                if k in TOP_LEVEL:
                    item[k] = v
                elif k in run_info.ALGORITHM_KEYS:
                    item["algorithm"][k] = v
                else:
                    item["metadata"][k] = v
    elif len(metadata) > 0:
        print "Metadata not found for sample %s, %s" % (item["description"],
                                                        os.path.basename(item["files"][0]))
    return item

def setup(args):
    template, template_txt = name_to_config(args.template)
    base_item = template["details"][0]
    project_name, metadata, global_vars = _pname_and_metadata(args.metadata)
    items = [_add_metadata(item, metadata)
             for item in _prep_items_from_base(base_item, args.input_files)]

    out_dir = os.path.join(os.getcwd(), project_name)
    work_dir = utils.safe_makedir(os.path.join(out_dir, "work"))
    if len(items) == 0:
        out_config_file = _write_template_config(template_txt, project_name, out_dir)
        print "Template configuration file created at: %s" % out_config_file
        print "Edit to finalize custom options, then prepare full sample config with:"
        print "  bcbio_nextgen.py -w template %s %s sample1.bam sample2.fq" % \
            (out_config_file, project_name)
    else:
        out_config_file = _write_config_file(items, global_vars, template, project_name, out_dir)
        print "Configuration file created at: %s" % out_config_file
        print "Edit to finalize and run with:"
        print "  cd %s" % work_dir
        print "  bcbio_nextgen.py ../config/%s" % os.path.basename(out_config_file)

########NEW FILE########
__FILENAME__ = xprize
"""XPrize scoring workflow that converts input BAMs into consolidated Ensemble calls.

Automates the Ensemble approach described here (http://j.mp/VUbz9A) to prepare
a final set of reference haploid variant calls for X Prize scoring.
"""
import argparse
import datetime
import os
import sys

import yaml

from bcbio import utils

class HelpArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def parse_args(args):
    parser = HelpArgParser(
        description="Automate ensemble variant approach for X Prize preparation")
    parser.add_argument("sample", help="Sample name")
    parser.add_argument("bam_file", help="Input BAM file")
    parser.add_argument("bed_file", help="BED file of fosmid regions")
    parser.add_argument("base_dir", help="Base directory to process in")
    parser.add_argument("bcbio_config_file", help="bcbio system YAML config")
    args = parser.parse_args(args)
    return args

def get_fc_date(out_config_file):
    """Retrieve flowcell date, reusing older dates if refreshing a present workflow.
    """
    if os.path.exists(out_config_file):
        with open(out_config_file) as in_handle:
            old_config = yaml.load(in_handle)
            fc_date = old_config["fc_date"]
    else:
        fc_date = datetime.datetime.now().strftime("%y%m%d")
    return fc_date

def setup(args):
    final_dir = utils.safe_makedir(os.path.join(args.base_dir, "ready"))
    configdir = utils.safe_makedir(os.path.join(args.base_dir, args.sample, "config"))
    out_config_file = os.path.join(configdir, "%s.yaml" % args.sample)
    callers = ["gatk", "freebayes", "samtools", "varscan"]
    out = {"fc_date": get_fc_date(out_config_file),
           "fc_name": args.sample,
           "upload": {"dir": final_dir},
           "details": [{
               "files": [args.bam_file],
               "lane": 1,
               "description": args.sample,
               "analysis": "variant",
               "genome_build": "GRCh37",
               "algorithm": {
                   "aligner": False,
                   "recalibrate": False,
                   "realign": False,
                   "ploidy": 1,
                   "variantcaller": callers,
                   "quality_format": "Standard",
                   "variant_regions": args.bed_file,
                   "coverage_interval": "regional",
                   "ensemble": {
                       "format-filters": ["DP < 4"],
                       "classifiers": {
                           "balance": ["AD", "FS", "Entropy"],
                           "calling": ["ReadPosEndDist", "PL", "Entropy", "NBQ"]},
                       "classifier-params": {
                           "type": "svm"},
                       "trusted-pct": 0.65}}}]}
    with open(out_config_file, "w") as out_handle:
        yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)

    workdir = utils.safe_makedir(os.path.join(args.base_dir, args.sample, "work"))
    return workdir, {"config_file": args.bcbio_config_file,
                     "run_info_yaml": out_config_file}

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# bcbio_nextgen documentation build configuration file, created by
# sphinx-quickstart on Tue Jan  1 13:33:31 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'bcbio-nextgen'
copyright = u'2013, bcbio-nextgen contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7.9'
# The full version, including alpha/beta/rc tags.
release = '0.7.9'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    "index": ["sidebar-links.html", "searchbox.html"]}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'bcbio_nextgendoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'bcbio_nextgen.tex', u'bcbio\\_nextgen Documentation',
   u'Brad Chapman', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bcbio_nextgen', u'bcbio_nextgen Documentation',
     [u'Brad Chapman'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'bcbio_nextgen', u'bcbio_nextgen Documentation',
   u'Brad Chapman', 'bcbio_nextgen', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = bcbio_nextgen
#!/usr/bin/env python -E
"""Run an automated analysis pipeline for high throughput sequencing data.

Handles runs in local or distributed mode based on the command line or
configured parameters.

The <config file> is a global YAML configuration file specifying details
about the system. An example configuration file is in 'config/bcbio_sample.yaml'.
This is optional for automated installations.

<fc_dir> is an optional parameter specifying a directory of Illumina output
or fastq files to process. If configured to connect to a Galaxy LIMS system,
this can retrieve run information directly from Galaxy for processing.

<YAML run information> is an optional file specifies details about the
flowcell lanes, instead of retrieving it from Galaxy. An example
configuration file is located in 'config/bcbio_sample.yaml' This allows running
on files in arbitrary locations with no connection to Galaxy required.

Usage:
  bcbio_nextgen.py <config_file> [<fc_dir>] [<run_info_yaml>]
     -t type of parallelization to use:
          - local: Non-distributed, possibly multiple if n > 1 (default)
          - ipython: IPython distributed processing
     -n total number of processes to use
     -s scheduler for ipython parallelization (lsf, sge, slurm)
     -q queue to submit jobs for ipython parallelization
"""
import os
import sys

from bcbio import install, workflow
from bcbio.illumina import machine
from bcbio.distributed import runfn
from bcbio.pipeline.main import run_main, parse_cl_args
from bcbio.server import main as server_main
from bcbio.provenance import programs

def main(**kwargs):
    run_main(**kwargs)

if __name__ == "__main__":
    kwargs = parse_cl_args(sys.argv[1:])
    if "upgrade" in kwargs and kwargs["upgrade"]:
        install.upgrade_bcbio(kwargs["args"])
    elif "server" in kwargs and kwargs["server"]:
        server_main.start(kwargs["args"])
    elif "runfn" in kwargs and kwargs["runfn"]:
        runfn.process(kwargs["args"])
    elif "version" in kwargs and kwargs["version"]:
        programs.write_versions({"work": kwargs["args"].workdir})
    elif "sequencer" in kwargs and kwargs["sequencer"]:
        machine.check_and_postprocess(kwargs["args"])
    else:
        if kwargs.get("workflow"):
            setup_info = workflow.setup(kwargs["workflow"], kwargs.pop("inputs"))
            if setup_info is None:  # no automated run after setup
                sys.exit(0)
            workdir, new_kwargs = setup_info
            os.chdir(workdir)
            kwargs.update(new_kwargs)
        main(**kwargs)

########NEW FILE########
__FILENAME__ = bcbio_nextgen_install
#!/usr/bin/env python
"""Automatically install required tools and data to run bcbio-nextgen pipelines.

This automates the steps required for installation and setup to make it
easier to get started with bcbio-nextgen. The defaults provide data files
for human variant calling.

Requires: git, Python 2.7 or argparse for earlier versions.
"""
import collections
import contextlib
import datetime
import os
import platform
import shutil
import subprocess
import sys
import urllib2

remotes = {"requirements":
           "https://raw.github.com/chapmanb/bcbio-nextgen/master/requirements.txt",
           "gitrepo": "git://github.com/chapmanb/bcbio-nextgen.git",
           "system_config":
           "https://raw.github.com/chapmanb/bcbio-nextgen/master/config/bcbio_system.yaml",
           "anaconda":
           "http://repo.continuum.io/miniconda/Miniconda-3.0.0-%s-x86_64.sh"}

def main(args, sys_argv):
    check_dependencies()
    with bcbio_tmpdir():
        setup_data_dir(args)
        print("Installing isolated base python installation")
        anaconda = install_anaconda_python(args, remotes)
        print("Installing bcbio-nextgen")
        install_conda_pkgs(anaconda)
        bcbio = bootstrap_bcbionextgen(anaconda, args, remotes)
    print("Installing data and third party dependencies")
    system_config = write_system_config(remotes["system_config"], args.datadir,
                                        args.tooldir)
    setup_manifest(args.datadir)
    subprocess.check_call([bcbio["bcbio_nextgen.py"], "upgrade"] + _clean_args(sys_argv, args, bcbio))
    print("Finished: bcbio-nextgen, tools and data installed")
    print(" Genome data installed in:\n  %s" % args.datadir)
    if args.tooldir:
        print(" Tools installed in:\n  %s" % args.tooldir)
    print(" Ready to use system configuration at:\n  %s" % system_config)
    print(" Edit configuration file as needed to match your machine or cluster")

def _clean_args(sys_argv, args, bcbio):
    """Remove data directory from arguments to pass to upgrade function.
    """
    base = [x for x in sys_argv if
            x.startswith("-") or not args.datadir == os.path.abspath(os.path.expanduser(x))]
    # specification of data argument changes in install (default data) to upgrade (default nodata)
    # in bcbio_nextgen 0.7.5 and beyond
    process = subprocess.Popen([bcbio["bcbio_nextgen.py"], "--version"], stdout=subprocess.PIPE)
    version, _ = process.communicate()
    if version.strip() > "0.7.4":
        if "--nodata" in base:
            base.remove("--nodata")
        else:
            base.append("--data")
    return base

def bootstrap_bcbionextgen(anaconda, args, remotes):
    """Install bcbio-nextgen to bootstrap rest of installation process.
    """
    subprocess.check_call([anaconda["pip"], "install", "fabric"])
    subprocess.check_call([anaconda["pip"], "install", "-r", remotes["requirements"]])
    if args.upgrade == "development":
        subprocess.check_call([anaconda["pip"], "install", "--upgrade", "--no-deps",
                               "git+%s#egg=bcbio-nextgen" % remotes["gitrepo"]])
    out = {}
    for script in ["bcbio_nextgen.py"]:
        ve_script = os.path.join(anaconda["dir"], "bin", script)
        if args.tooldir:
            final_script = os.path.join(args.tooldir, "bin", script)
            sudo_cmd = ["sudo"] if args.sudo else []
            subprocess.check_call(sudo_cmd + ["mkdir", "-p", os.path.dirname(final_script)])
            if os.path.lexists(final_script):
                cmd = ["rm", "-f", final_script]
                subprocess.check_call(sudo_cmd + cmd)
            cmd = ["ln", "-s", ve_script, final_script]
            subprocess.check_call(sudo_cmd + cmd)
        out[script] = ve_script
    return out

def install_conda_pkgs(anaconda):
    pkgs = ["biopython", "boto", "cython", "ipython", "lxml", "matplotlib",
            "nose", "numpy", "pandas", "patsy", "pycrypto", "pip", "pysam",
            "pyyaml", "pyzmq", "requests", "scipy", "setuptools", "sqlalchemy",
            "statsmodels", "toolz", "tornado"]
    channels = ["-c", "https://conda.binstar.org/collections/chapmanb/bcbio"]
    subprocess.check_call([anaconda["conda"], "install", "--yes", "numpy"])
    subprocess.check_call([anaconda["conda"], "install", "--yes"] + channels + pkgs)

def _guess_distribution():
    """Simple approach to identify if we are on a MacOSX or Linux system for Anaconda.
    """
    if platform.mac_ver()[0]:
        return "macosx"
    else:
        return "linux"

def install_anaconda_python(args, remotes):
    """Provide isolated installation of Anaconda python for running bcbio-nextgen.
    http://docs.continuum.io/anaconda/index.html
    """
    anaconda_dir = os.path.join(args.datadir, "anaconda")
    bindir = os.path.join(anaconda_dir, "bin")
    conda = os.path.join(bindir, "conda")
    if not os.path.exists(anaconda_dir) or not os.path.exists(conda):
        if os.path.exists(anaconda_dir):
            shutil.rmtree(anaconda_dir)
        dist = args.distribution if args.distribution else _guess_distribution()
        url = remotes["anaconda"] % ("MacOSX" if dist.lower() == "macosx" else "Linux")
        if not os.path.exists(os.path.basename(url)):
            subprocess.check_call(["wget", url])
        subprocess.check_call("bash %s -b -p %s" %
                              (os.path.basename(url), anaconda_dir), shell=True)
    return {"conda": conda,
            "pip": os.path.join(bindir, "pip"),
            "dir": anaconda_dir}

def setup_manifest(datadir):
    """Create barebones manifest to be filled in during update
    """
    manifest_dir = os.path.join(datadir, "manifest")
    if not os.path.exists(manifest_dir):
        os.makedirs(manifest_dir)

def write_system_config(base_url, datadir, tooldir):
    """Write a bcbio_system.yaml configuration file with tool information.
    """
    out_file = os.path.join(datadir, "galaxy", os.path.basename(base_url))
    if not os.path.exists(os.path.dirname(out_file)):
        os.makedirs(os.path.dirname(out_file))
    if os.path.exists(out_file):
        # if no tool directory and exists, do not overwrite
        if tooldir is None:
            return out_file
        else:
            bak_file = out_file + ".bak%s" % (datetime.datetime.now().strftime("%Y%M%d_%H%M"))
            shutil.copy(out_file, bak_file)
    if tooldir:
        java_basedir = os.path.join(tooldir, "share", "java")
    rewrite_ignore = ("log",)
    with contextlib.closing(urllib2.urlopen(base_url)) as in_handle:
        with open(out_file, "w") as out_handle:
            in_resources = False
            in_prog = None
            for line in in_handle:
                if line[0] != " ":
                    in_resources = line.startswith("resources")
                    in_prog = None
                elif (in_resources and line[:2] == "  " and line[2] != " "
                      and not line.strip().startswith(rewrite_ignore)):
                    in_prog = line.split(":")[0].strip()
                # Update java directories to point to install directory, avoid special cases
                elif line.strip().startswith("dir:") and in_prog and in_prog not in ["log", "tmp"]:
                    final_dir = os.path.basename(line.split()[-1])
                    if tooldir:
                        line = "%s: %s\n" % (line.split(":")[0],
                                             os.path.join(java_basedir, final_dir))
                    in_prog = None
                elif line.startswith("galaxy"):
                    line = "# %s" % line
                out_handle.write(line)
    return out_file

def setup_data_dir(args):
    if not os.path.exists(args.datadir):
        cmd = ["mkdir", "-p", args.datadir]
        if args.sudo:
            cmd.insert(0, "sudo")
        subprocess.check_call(cmd)
    if args.sudo:
        subprocess.check_call(["sudo", "chown", "-R", os.environ["USER"], args.datadir])

@contextlib.contextmanager
def bcbio_tmpdir():
    orig_dir = os.getcwd()
    work_dir = os.path.join(os.getcwd(), "tmpbcbio-install")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    os.chdir(work_dir)
    yield work_dir
    os.chdir(orig_dir)
    shutil.rmtree(work_dir)

def check_dependencies():
    """Ensure required tools for installation are present.
    """
    print("Checking required dependencies")
    try:
        subprocess.check_call(["git", "--version"])
    except OSError:
        raise OSError("bcbio-nextgen installer requires Git (http://git-scm.com/)")

def _check_toolplus(x):
    """Parse options for adding non-standard/commercial tools like GATK and MuTecT.
    """
    import argparse
    Tool = collections.namedtuple("Tool", ["name", "fname"])
    std_choices = set(["data"])
    if x in std_choices:
        return Tool(x, None)
    elif "=" in x and len(x.split("=")) == 2:
        name, fname = x.split("=")
        fname = os.path.normpath(os.path.realpath(fname))
        if not os.path.exists(fname):
            raise argparse.ArgumentTypeError("Unexpected --toolplus argument for %s. File does not exist: %s"
                                             % (name, fname))
        return Tool(name, fname)
    else:
        raise argparse.ArgumentTypeError("Unexpected --toolplus argument. Expect toolname=filename.")

if __name__ == "__main__":
    try:
        import argparse
    except ImportError:
        raise ImportError("bcbio-nextgen installer requires `argparse`, included in Python 2.7.\n"
                          "Install for earlier versions with `pip install argparse` or "
                          "`easy_install argparse`.")
    parser = argparse.ArgumentParser(
        description="Automatic installation for bcbio-nextgen pipelines")
    parser.add_argument("datadir", help="Directory to install genome data",
                        type=lambda x: (os.path.abspath(os.path.expanduser(x))))
    parser.add_argument("--tooldir",
                        help="Directory to install 3rd party software tools. Leave unspecified for no tools",
                        type=lambda x: (os.path.abspath(os.path.expanduser(x))), default=None)
    parser.add_argument("--toolplus", help="Specify additional tool categories to install",
                        action="append", default=[], type=_check_toolplus)
    parser.add_argument("--genomes", help="Genomes to download",
                        action="append", default=["GRCh37"],
                        choices=["GRCh37", "hg19", "mm10", "mm9", "rn5", "canFam3", "dm3", "Zv9", "phix"])
    parser.add_argument("--aligners", help="Aligner indexes to download",
                        action="append", default=["bwa"],
                        choices=["bowtie", "bowtie2", "bwa", "novoalign", "star", "ucsc"])
    parser.add_argument("--nodata", help="Do not install data dependencies",
                        dest="install_data", action="store_false", default=True)
    parser.add_argument("--nosudo", help="Specify we cannot use sudo for commands",
                        dest="sudo", action="store_false", default=True)
    parser.add_argument("--isolate", help="Created an isolated installation without PATH updates",
                        dest="isolate", action="store_true", default=False)
    parser.add_argument("-u", "--upgrade", help="Code version to install",
                        choices=["stable", "development"], default="stable")
    parser.add_argument("--distribution", help="Operating system distribution",
                        default="",
                        choices=["ubuntu", "debian", "centos", "scientificlinux", "macosx"])
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        main(parser.parse_args(), sys.argv[1:])

########NEW FILE########
__FILENAME__ = analyze_complexity_by_starts
import argparse
import os
from bcbio.rnaseq import qc
from collections import Counter
import bcbio.bam as bam
import bcbio.utils as utils
from itertools import ifilter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def count_duplicate_starts(bam_file, sample_size=10000000):
    """
    Return a set of x, y points where x is the number of reads sequenced and
    y is the number of unique start sites identified
    If sample size < total reads in a file the file will be downsampled.
    """
    count = Counter()
    with bam.open_samfile(bam_file) as samfile:
        # unmapped reads should not be counted
        filtered = ifilter(lambda x: not x.is_unmapped, samfile)
        def read_parser(read):
            return ":".join([str(read.tid), str(read.pos)])
        samples = utils.reservoir_sample(filtered, sample_size, read_parser)

    count.update(samples)
    return count


if __name__ == "__main__":
    description = ("Create reads sequenced vs unique start sites graph for "
                   "examining the quality of a library. The idea for this "
                   " metric was borrowed from: "
                   "https://github.com/mbusby/ComplexityByStartPosition."
                   "This can also be used to generate counts for use with "
                   "the preseq tool: "
                   "http://smithlab.usc.edu/plone/software/librarycomplexity.")

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("alignment_file", help="Alignment file to process,"
                        "can be SAM or BAM format.")
    parser.add_argument("--complexity", default=False, action='store_true',
                        help="Rough estimate of library complexity")
    parser.add_argument("--histogram", default=False, action='store_true',
                        help="Output a histogram of the unique reads vs. counts.")
    parser.add_argument("--counts", default=False, action='store_true',
                        help="Output a counts of each start site")
    parser.add_argument("--figure", default=None, help="Generate a figure for the complexity")
    parser.add_argument("--sample-size", default=None, type=int,
                        help="Number of reads to sample.")
    args = parser.parse_args()
    df = qc.starts_by_depth(args.alignment_file, args.sample_size)
    if args.figure:
        df.plot(x='reads', y='starts')
        fig = plt.gcf()
        fig.savefig(args.figure)

    if args.histogram:
        base, _ = os.path.splitext(args.alignment_file)
        df.to_csv(base + ".histogram", sep="\t", header=True, index=False)
    if args.complexity:
        print qc.estimate_library_complexity(df)
    if args.counts:
        c = count_duplicate_starts(args.alignment_file)
        for item in c.items():
            print "{0}\t{1}".format(item[0], item[1])

########NEW FILE########
__FILENAME__ = analyze_quality_recal
#!/usr/bin/env python
"""Provide plots summarizing recalibration of quality scores.

Usage:
    analyze_quality_recal.py <recal_bam> <input_fastq1> <input_fastq2>
    --chunk_size=25 --input_format=fastq-illumina
    --dbdir=/tmp/chapmanb

    <recal_bam> is a BAM alignment file containing recalibrarted quality scores
    <input_fastq> are the initial fastq files with quality scores
    --chunk_size -- How many positions to read in at once. Higher scores are
    faster but require more memory.
    --input_format -- Quality score encoding of input fastq files.
    --dbdir -- Where to store database files. This is needed for cluster
    jobs on NFS since sqlite can behave strangely on NFS with lock errors.
    --workdir -- The working directory to write output files to. Defaults to the current
      directory

Requirements:
    sqlite
    biopython
    pysam
    R with ggplot2, plyr and sqldf
    rpy2
    mako
    latex (texlive)
"""
import sys
import os
import csv
import glob
import collections
import subprocess
from optparse import OptionParser
try:
    from pysqlite2 import dbapi2 as sqlite3
except ImportError:
    import sqlite3

from Bio import SeqIO
from Bio import Seq
import pysam
from mako.template import Template
try:
    import rpy2.robjects as robjects
except (ImportError, LookupError):
    robjects = None

def main(recal_bam, fastq1, fastq2=None, chunk_size=None, input_format=None,
        db_dir=None, work_dir=None):
    if not _are_libraries_installed():
        print "R libraries or rpy2 not installed. Not running recalibration plot."
        return
    if work_dir is None:
        work_dir = os.getcwd()
    report_dir = os.path.join(work_dir, "reports")
    image_dir = os.path.join(report_dir, "images")
    if db_dir is None:
        db_dir = work_dir
    if not os.path.exists(image_dir):
        # avoid error with creating directories simultaneously on two threads
        try:
            os.makedirs(image_dir)
        except OSError:
            assert os.path.isdir(image_dir)
    base = os.path.splitext(os.path.basename(recal_bam))[0]
    orig_files = {1: fastq1, 2: fastq2}

    section_info = []
    pairs = ([1] if fastq2 is None else [1, 2])
    for pair in pairs:
        plots = []
        db_file = os.path.join(db_dir, "%s_%s-qualities.sqlite" % (base, pair))
        if not os.path.exists(db_file):
            print "Converting BAM alignment to fastq files"
            recal_fastq1, recal_fastq2 = bam_to_fastq(recal_bam, len(pairs) > 1)
            recal_files = {1: recal_fastq1, 2: recal_fastq2}
            print "Normalizing and sorting fastq files"
            orig = sort_csv(fastq_to_csv(orig_files[pair], input_format,
                work_dir))
            recal = sort_csv(fastq_to_csv(recal_files[pair], "fastq", work_dir))
            print "Summarizing remapped qualities for pair", pair
            summarize_qualities(db_file, orig, recal, chunk_size)
        print "Plotting for pair", pair
        for position_select, pname in _positions_to_examine(db_file):
            title = "Pair %s; Position: %s" % (pair, position_select)
            plot_file = os.path.join(image_dir,
                    "%s_%s_%s-plot.pdf" % (base, pair, pname))
            draw_quality_plot(db_file, plot_file, position_select, title)
            plots.append(plot_file)
        section_info.append(("Pair %s" % pair, plots))

    run_latex_report(base, report_dir, section_info)
    _clean_intermediates(recal_bam, fastq1, fastq2, report_dir)

def _are_libraries_installed():
    if robjects is None:
        print "rpy2 not installed: http://rpy.sourceforge.net/rpy2.html"
        return False
    import rpy2.rinterface
    try:
        robjects.r('''
          library(sqldf)
          library(plyr)
          library(ggplot2)
        ''')
    except rpy2.rinterface.RRuntimeError:
        print "Some R libraries not installed"
        return False
    return True

def draw_quality_plot(db_file, plot_file, position_select, title):
    """Draw a plot of remapped qualities using ggplot2.

    Remapping information is pulled from the sqlite3 database using sqldf
    according to the position select attribute, which is a selection phrase like
    '> 50' or '=28'.

    plyr is used to summarize data by the original and remapped score for all
    selected positions.

    ggplot2 plots a heatmap of remapped counts at each (original, remap)
    coordinate, with a x=y line added for reference.
    """
    robjects.r.assign('db.file', db_file)
    robjects.r.assign('plot.file', plot_file)
    robjects.r.assign('position.select', position_select)
    robjects.r.assign('title', title)
    robjects.r('''
      library(sqldf)
      library(plyr)
      library(ggplot2)
      sql <- paste("select * from data WHERE position", position.select, sep=" ")
      exp.data <- sqldf(sql, dbname=db.file)
      remap.data <- ddply(exp.data, c("orig", "remap"), transform, count=sum(count))
      p <- ggplot(remap.data, aes(orig, remap)) +
           geom_tile(aes(fill = count)) +
           scale_fill_gradient(low = "white", high = "steelblue", trans="log") +
           opts(panel.background = theme_rect(fill = "white"),
                title=title) +
           geom_abline(intercept=0, slope=1)
      ggsave(plot.file, p, width=6, height=6)
    ''')

def _positions_to_examine(db_file):
    """Determine how to sub-divide recalibration analysis based on read length.
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""SELECT MAX(position) FROM data""")
    position = cursor.fetchone()[0]
    if position is not None:
        position = int(position)
    cursor.close()
    split_at = 50
    if position is None:
        return []
    elif position < split_at:
        return [("<= %s" % position, "lt%s" % position)]
    else:
        return [("< %s" % split_at, "lt%s" % split_at),
                (">= %s" % split_at, "gt%s" % split_at)]

def summarize_qualities(db_file, orig_file, cmp_file, chunk_size):
    out_conn = sqlite3.connect(db_file)
    out_cursor = out_conn.cursor()
    out_cursor.execute("""create table data
                (position integer, orig integer,
                 remap integer, count integer)""")
    try:
        cur_pos = 1
        for pos, orig_val, final_val, count in _organize_by_position(orig_file,
                cmp_file, chunk_size):
            out_cursor.execute("INSERT INTO data VALUES (?,?,?,?)",
                    [pos, orig_val, final_val, count])
            if pos != cur_pos:
                cur_pos = pos
                out_conn.commit()
    finally:
        out_conn.commit()
        out_cursor.close()

def _organize_by_position(orig_file, cmp_file, chunk_size):
    """Read two CSV files of qualities, organizing values by position.
    """
    with open(orig_file) as in_handle:
        reader1 = csv.reader(in_handle)
        positions = len(reader1.next()) - 1
    for positions in _chunks(range(positions), chunk_size):
        with open(orig_file) as orig_handle:
            with open(cmp_file) as cmp_handle:
                orig_reader = csv.reader(orig_handle)
                cmp_reader = csv.reader(cmp_handle)
                for item in _counts_at_position(positions,
                        orig_reader, cmp_reader):
                    yield item

def _chunks(l, n):
    """ Yield successive n-sized chunks from l.

    http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def _counts_at_position(positions, orig_reader, cmp_reader):
    """Combine orignal and new qualities at each position, generating counts.
    """
    pos_counts = collections.defaultdict(lambda:
                 collections.defaultdict(lambda:
                 collections.defaultdict(int)))
    for orig_parts in orig_reader:
        cmp_parts = cmp_reader.next()
        for pos in positions:
            try:
                pos_counts[pos][int(orig_parts[pos+1])][int(cmp_parts[pos+1])] += 1
            except IndexError:
                pass
    for pos, count_dict in pos_counts.iteritems():
        for orig_val, cmp_dict in count_dict.iteritems():
            for cmp_val, count in cmp_dict.iteritems():
                yield pos+1, orig_val, cmp_val, count

def sort_csv(in_file):
    """Sort a CSV file by read name, allowing direct comparison.
    """
    out_file = "%s.sort" % in_file
    if not (os.path.exists(out_file) and os.path.getsize(out_file) > 0):
        cl = ["sort", "-k", "1,1", in_file]
        with open(out_file, "w") as out_handle:
            child = subprocess.Popen(cl, stdout=out_handle)
            child.wait()
    return out_file

def fastq_to_csv(in_file, fastq_format, work_dir):
    """Convert a fastq file into a CSV of phred quality scores.
    """
    out_file = "%s.csv" % (os.path.splitext(os.path.basename(in_file))[0])
    out_file = os.path.join(work_dir, out_file)
    if not (os.path.exists(out_file) and os.path.getsize(out_file) > 0):
        with open(in_file) as in_handle:
            with open(out_file, "w") as out_handle:
                writer = csv.writer(out_handle)
                for rec in SeqIO.parse(in_handle, fastq_format):
                    writer.writerow([rec.id] + rec.letter_annotations["phred_quality"])
    return out_file

def bam_to_fastq(bam_file, is_paired):
    """Convert a BAM file to fastq files.
    """
    out_files, out_handles = _get_fastq_handles(bam_file,
            is_paired)
    if len(out_handles) > 0:
        in_bam = pysam.Samfile(bam_file, mode='rb')
        for read in in_bam:
            num = 1 if (not read.is_paired or read.is_read1) else 2
            # reverse the sequence and quality if mapped to opposite strand
            if read.is_reverse:
                seq = str(Seq.reverse_complement(Seq.Seq(read.seq)))
                qual = "".join(reversed(read.qual))
            else:
                seq = read.seq
                qual = read.qual
            out_handles[num].write("@%s\n%s\n+\n%s\n" % (read.qname,
                seq, qual))
    [h.close() for h in out_handles.values()]
    return out_files

def _get_fastq_handles(bam_file, is_paired):
    (base, _) = os.path.splitext(bam_file)
    out_files = []
    out_handles = dict()
    if is_paired:
        for index in [1, 2]:
            cur_file = "%s_%s_fastq.txt" % (base, index)
            out_files.append(cur_file)
            if not (os.path.exists(cur_file) and os.path.getsize(cur_file) > 0):
                out_handles[index] = open(cur_file, "w")
    else:
        cur_file = "%s_fastq.txt" % base
        out_files.append(cur_file)
        out_files.append(None)
        if not(os.path.exists(cur_file) and os.path.getsize(cur_file) > 0):
            out_handles[1] = open(cur_file, "w")
    return out_files, out_handles

def _clean_intermediates(bam_file, fastq1, fastq2, report_dir):
    base = os.path.splitext(bam_file)[0]
    for bam_rem in glob.glob("%s_*fastq*" % base):
        os.remove(bam_rem)
    for fastq in (fastq1, fastq2):
        if fastq:
            for fastq_rem in glob.glob("%s.csv*" %
                    os.path.splitext(os.path.basename(fastq))[0]):
                os.remove(fastq_rem)
    for latex_ext in ["aux", "log"]:
        for latex_rem in glob.glob(os.path.join(report_dir, "%s*.%s" %
                            (os.path.basename(base), latex_ext))):
            os.remove(latex_rem)

def run_latex_report(base, report_dir, section_info):
    """Generate a pdf report with plots using latex.
    """
    out_name = "%s_recal_plots.tex" % base
    out = os.path.join(report_dir, out_name)
    with open(out, "w") as out_handle:
        out_tmpl = Template(out_template)
        out_handle.write(out_tmpl.render(sections=section_info))
    start_dir = os.getcwd()
    try:
        os.chdir(report_dir)
        cl = ["pdflatex", out_name]
        child = subprocess.Popen(cl)
        child.wait()
    finally:
        os.chdir(start_dir)

out_template = r"""
\documentclass{article}
\usepackage{fullpage}
\usepackage[top=0.5in,right=1in,left=1in,bottom=0.5in]{geometry}
\usepackage{graphicx}
\usepackage{placeins}

\begin{document}
% for section, figures in sections:
    \subsubsection*{${section}}
    % for figure in figures:
        \begin{figure}[htbp]
          \centering
          \includegraphics[width=0.57\linewidth]{${figure}}
        \end{figure}
    % endfor
   \FloatBarrier
   \newpage
% endfor
\end{document}
"""

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--chunk_size", dest="chunk_size", default=25)
    parser.add_option("-i", "--input_format", dest="input_format",
            default="fastq-illumina")
    parser.add_option("-d", "--dbdir", dest="dbdir",
            default=None)
    parser.add_option("-w", "--workdir", dest="workdir",
            default=None)
    (options, args) = parser.parse_args()
    kwargs = dict(chunk_size = int(options.chunk_size),
                  input_format = options.input_format,
                  db_dir = options.dbdir, work_dir = options.workdir)
    main(*args, **kwargs)

########NEW FILE########
__FILENAME__ = bam_to_fastq_region
#!/usr/bin/env python
"""Prepare paired end fastq files from a chromosome region in an aligned input BAM file.

Useful for preparing test or other example files with subsets of aligned data.

Usage:
  bam_to_fastq_region.py <YAML config> <BAM input> <chromosome> <start> <end>
"""
import os
import sys
import contextlib

import yaml
import pysam
from Bio import Seq

from bcbio import broad

def main(config_file, in_file, space, start, end):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    runner = broad.runner_from_config(config)
    target_region = (space, int(start), int(end))
    for pair in [1, 2]:
        out_file = "%s_%s-%s.fastq" % (os.path.splitext(os.path.basename(in_file))[0],
                                          pair, target_region[0])
        with open(out_file, "w") as out_handle:
            for name, seq, qual in bam_to_fastq_pair(in_file, target_region, pair):
                out_handle.write("@%s/%s\n%s\n+\n%s\n" % (name, pair, seq, qual))
        sort_fastq(out_file, runner)

def bam_to_fastq_pair(in_file, target_region, pair):
    """Generator to convert BAM files into name, seq, qual in a region.
    """
    space, start, end = target_region
    bam_file = pysam.Samfile(in_file, "rb")
    for read in bam_file:
        if (not read.is_unmapped and not read.mate_is_unmapped
                and bam_file.getrname(read.tid) == space
                and bam_file.getrname(read.mrnm) == space
                and read.pos >= start and read.pos <= end
                and read.mpos >= start and read.mpos <= end
                and not read.is_secondary
                and read.is_paired and getattr(read, "is_read%s" % pair)):
            seq = Seq.Seq(read.seq)
            qual = list(read.qual)
            if read.is_reverse:
                seq = seq.reverse_complement()
                qual.reverse()
            yield read.qname, str(seq), "".join(qual)

@contextlib.contextmanager
def fastq_to_bam(in_file, runner):
    bam_file = "%s.bam" % os.path.splitext(in_file)[0]
    try:
        opts = [("FASTQ", in_file),
                ("OUTPUT", bam_file),
                ("QUALITY_FORMAT", "Standard"),
                ("SAMPLE_NAME", "t")]
        runner.run("FastqToSam", opts)
        yield bam_file
    finally:
        if os.path.exists(bam_file):
            os.remove(bam_file)

@contextlib.contextmanager
def sort_bam(in_file, runner):
    base, ext = os.path.splitext(in_file)
    out_file = "%s-sort%s" % (base, ext)
    try:
        opts = [("INPUT", in_file),
                ("OUTPUT", out_file),
                ("SORT_ORDER", "queryname")]
        runner.run("SortSam", opts)
        yield out_file
    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

def bam_to_fastq(in_file, runner):
    out_file = "%s.fastq" % os.path.splitext(in_file)[0]
    opts = [("INPUT", in_file),
            ("FASTQ", out_file)]
    runner.run("SamToFastq", opts)

def sort_fastq(in_file, runner):
    with fastq_to_bam(in_file, runner) as bam_file:
        with sort_bam(bam_file, runner) as sort_bam_file:
            bam_to_fastq(sort_bam_file, runner)

if __name__ == "__main__":
    main(*sys.argv[1:])


########NEW FILE########
__FILENAME__ = bam_to_wiggle
#!/usr/bin/env python
"""Convert BAM files to BigWig file format in a specified region.

Usage:
    bam_to_wiggle.py <BAM file> [<YAML config>]
    [--outfile=<output file name>
     --chrom=<chrom>
     --start=<start>
     --end=<end>
     --normalize]

chrom start and end are optional, in which case they default to everything.
The normalize flag adjusts counts to reads per million.

The config file is in YAML format and specifies the location of the wigToBigWig
program from UCSC:

program:
  ucsc_bigwig: wigToBigWig

If not specified, these will be assumed to be present in the system path.

The script requires:
    pysam (http://code.google.com/p/pysam/)
    wigToBigWig from UCSC (http://hgdownload.cse.ucsc.edu/admin/exe/)
If a configuration file is used, then PyYAML is also required (http://pyyaml.org/)
"""
import os
import sys
import subprocess
import tempfile
from optparse import OptionParser
from contextlib import contextmanager, closing

import pysam

from bcbio.pipeline.config_utils import load_config, get_program

def main(bam_file, config_file=None, chrom='all', start=0, end=None,
         outfile=None, normalize=False, use_tempfile=False):
    if config_file:
        config = load_config(config_file)
    else:
        config = {"program": {"ucsc_bigwig" : "wigToBigWig"}}
    if outfile is None:
        outfile = "%s.bigwig" % os.path.splitext(bam_file)[0]
    if start > 0:
        start = int(start) - 1
    if end is not None:
        end = int(end)
    regions = [(chrom, start, end)]
    if os.path.abspath(bam_file) == os.path.abspath(outfile):
        sys.stderr.write("Bad arguments, input and output files are the same.\n")
        sys.exit(1)
    if not (os.path.exists(outfile) and os.path.getsize(outfile) > 0):
        if use_tempfile:
            #Use a temp file to avoid any possiblity of not having write permission
            out_handle = tempfile.NamedTemporaryFile(delete=False)
            wig_file = out_handle.name
        else:
            wig_file = "%s.wig" % os.path.splitext(outfile)[0]
            out_handle = open(wig_file, "w")
        with closing(out_handle):
            chr_sizes, wig_valid = write_bam_track(bam_file, regions, config, out_handle,
                                                   normalize)
        try:
            if wig_valid:
                convert_to_bigwig(wig_file, chr_sizes, config, outfile)
        finally:
            os.remove(wig_file)

@contextmanager
def indexed_bam(bam_file, config):
    if not os.path.exists(bam_file + ".bai"):
        pysam.index(bam_file)
    sam_reader = pysam.Samfile(bam_file, "rb")
    yield sam_reader
    sam_reader.close()

def write_bam_track(bam_file, regions, config, out_handle, normalize):
    out_handle.write("track %s\n" % " ".join(["type=wiggle_0",
        "name=%s" % os.path.splitext(os.path.split(bam_file)[-1])[0],
        "visibility=full",
        ]))
    normal_scale = 1e6
    is_valid = False
    with indexed_bam(bam_file, config) as work_bam:
        total = sum(1 for r in work_bam.fetch() if not r.is_unmapped) if normalize else None
        sizes = zip(work_bam.references, work_bam.lengths)
        if len(regions) == 1 and regions[0][0] == "all":
            regions = [(name, 0, length) for name, length in sizes]
        for chrom, start, end in regions:
            if end is None and chrom in work_bam.references:
                end = work_bam.lengths[work_bam.references.index(chrom)]
            assert end is not None, "Could not find %s in header" % chrom
            out_handle.write("variableStep chrom=%s\n" % chrom)
            for col in work_bam.pileup(chrom, start, end):
                if normalize:
                    n = float(col.n) / total * normal_scale
                else:
                    n = col.n
                out_handle.write("%s %.1f\n" % (col.pos+1, n))
                is_valid = True
    return sizes, is_valid

def convert_to_bigwig(wig_file, chr_sizes, config, bw_file=None):
    if not bw_file:
        bw_file = "%s.bigwig" % (os.path.splitext(wig_file)[0])
    size_file = "%s-sizes.txt" % (os.path.splitext(wig_file)[0])
    with open(size_file, "w") as out_handle:
        for chrom, size in chr_sizes:
            out_handle.write("%s\t%s\n" % (chrom, size))
    try:
        cl = [get_program("ucsc_bigwig", config, default="wigToBigWig"), wig_file, size_file, bw_file]
        subprocess.check_call(cl)
    finally:
        os.remove(size_file)
    return bw_file

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-o", "--outfile", dest="outfile")
    parser.add_option("-c", "--chrom", dest="chrom")
    parser.add_option("-s", "--start", dest="start")
    parser.add_option("-e", "--end", dest="end")
    parser.add_option("-n", "--normalize", dest="normalize",
                      action="store_true", default=False)
    parser.add_option("-t", "--tempfile", dest="use_tempfile",
                      action="store_true", default=False)
    (options, args) = parser.parse_args()
    if len(args) not in [1, 2]:
        print "Incorrect arguments"
        print __doc__
        sys.exit()
    kwargs = dict(
        outfile=options.outfile,
        chrom=options.chrom or 'all',
        start=options.start or 0,
        end=options.end,
        normalize=options.normalize,
        use_tempfile=options.use_tempfile)
    main(*args, **kwargs)

########NEW FILE########
__FILENAME__ = broad_redo_analysis
#!/usr/bin/env python
"""Redo post-processing of Broad alignments with updated pipeline.

Usage:
    broad_redo_analysis.py <YAML config file> <flow cell dir>
"""
import os
import sys
import json
import contextlib
import subprocess
import glob
import copy
import csv
from optparse import OptionParser
from multiprocessing import Pool
import xml.etree.ElementTree as ET

import yaml

from bcbio.illumina import flowcell
from bcbio.galaxy.api import GalaxyApiAccess
from bcbio.broad.metrics import PicardMetricsParser
from bcbio import utils
from bcbio.pipeline.config_utils import load_config

def main(config_file, fc_dir):
    work_dir = os.getcwd()
    config = load_config(config_file)
    galaxy_api = GalaxyApiAccess(config['galaxy_url'], config['galaxy_api_key'])
    fc_name, fc_date = flowcell.parse_dirname(fc_dir)
    run_info = galaxy_api.run_details(fc_name)
    fastq_dir = flowcell.get_fastq_dir(fc_dir)
    if config["algorithm"]["num_cores"] > 1:
        pool = Pool(config["algorithm"]["num_cores"])
        try:
            pool.map(_process_wrapper,
                    ((i, fastq_dir, fc_name, fc_date, config, config_file)
                        for i in run_info["details"]))
        except:
            pool.terminate()
            raise
    else:
        map(_process_wrapper,
            ((i, fastq_dir, fc_name, fc_date, config, config_file)
                for i in run_info["details"]))

def process_lane(info, fastq_dir, fc_name, fc_date, config, config_file):
    config = _update_config_w_custom(config, info)
    sample_name = info.get("description", "")
    if config["algorithm"]["include_short_name"]:
        sample_name = "%s: %s" % (info.get("name", ""), sample_name)
    genome_build = "%s%s" % (info["genome_build"],
                             config["algorithm"].get("ref_ext", ""))
    if info.get("analysis", "") == "Broad SNP":
        print "Processing", info["lane"], genome_build, \
                sample_name, info.get("researcher", ""), \
                info.get("analysis", "")
        lane_name = "%s_%s_%s" % (info['lane'], fc_date, fc_name)
        aligner_to_use = config["algorithm"]["aligner"]
        align_ref, sam_ref = get_genome_ref(genome_build,
                aligner_to_use, os.path.dirname(config["galaxy_config"]))
        util_script_dir = os.path.dirname(__file__)
        base_bam = "%s.bam" % lane_name
        resort_bam = resort_karotype_and_rename(base_bam, sam_ref, util_script_dir)
        base_bam = resort_bam
        if config["algorithm"]["recalibrate"]:
            print info['lane'], "Recalibrating with GATK"
            dbsnp_file = get_dbsnp_file(config, sam_ref)
            gatk_bam = recalibrate_quality(base_bam, sam_ref,
                    dbsnp_file, config["program"]["picard"])
            if config["algorithm"]["snpcall"]:
                print info['lane'], "Providing SNP genotyping with GATK"
                run_genotyper(gatk_bam, sam_ref, dbsnp_file, config_file)

def resort_karotype_and_rename(in_bam, ref_file, script_dir):
    assert os.path.exists(in_bam)
    out_file = "%s-ksort%s" % os.path.splitext(in_bam)
    ref_dict = "%s.dict" % os.path.splitext(ref_file)[0]
    assert os.path.exists(ref_dict)
    if not os.path.exists(out_file):
        resort_script = os.path.join(script_dir, "resort_bam_karyotype.py")
        rename_script = os.path.join(script_dir, "rename_samples.py")
        print "Resorting to karyotype", in_bam
        cl = ["python2.6", resort_script, ref_dict, in_bam]
        subprocess.check_call(cl)
        print "Renaming samples", out_file
        cl = ["python2.6", rename_script, out_file]
        subprocess.check_call(cl)
    return out_file

def _process_wrapper(args):
    try:
        return process_lane(*args)
    except KeyboardInterrupt:
        raise Exception

def recalibrate_quality(bam_file, sam_ref, dbsnp_file, picard_dir):
    """Recalibrate alignments with GATK and provide pdf summary.
    """
    cl = ["picard_gatk_recalibrate.py", picard_dir, sam_ref, bam_file]
    if dbsnp_file:
        cl.append(dbsnp_file)
    subprocess.check_call(cl)
    out_file = glob.glob("%s*gatkrecal.bam" % os.path.splitext(bam_file)[0])[0]
    return out_file

def run_genotyper(bam_file, ref_file, dbsnp_file, config_file):
    """Perform SNP genotyping and analysis using GATK.
    """
    cl = ["gatk_genotyper.py", config_file, ref_file, bam_file]
    if dbsnp_file:
        cl.append(dbsnp_file)
    subprocess.check_call(cl)

def get_dbsnp_file(config, sam_ref):
    snp_file = config["algorithm"].get("dbsnp", None)
    if snp_file:
        base_dir = os.path.dirname(os.path.dirname(sam_ref))
        snp_file = os.path.join(base_dir, snp_file)
    return snp_file

def get_fastq_files(directory, lane, fc_name):
    """Retrieve fastq files for the given lane, ready to process.
    """
    files = glob.glob(os.path.join(directory, "%s_*%s*txt*" % (lane, fc_name)))
    files.sort()
    if len(files) > 2 or len(files) == 0:
        raise ValueError("Did not find correct files for %s %s %s %s" %
                (directory, lane, fc_name, files))
    ready_files = []
    for fname in files:
        if fname.endswith(".gz"):
            cl = ["gunzip", fname]
            subprocess.check_call(cl)
            ready_files.append(os.path.splitext(fname)[0])
        else:
            ready_files.append(fname)
    return ready_files[0], (ready_files[1] if len(ready_files) > 1 else None)

def _remap_to_maq(ref_file):
    base_dir = os.path.dirname(os.path.dirname(ref_file))
    name = os.path.basename(ref_file)
    for ext in ["fa", "fasta"]:
        test_file = os.path.join(base_dir, "maq", "%s.%s" % (name, ext))
        if os.path.exists(test_file):
            return test_file
    raise ValueError("Did not find maq file %s" % ref_file)

def get_genome_ref(genome_build, aligner, galaxy_base):
    """Retrieve the reference genome file location from galaxy configuration.
    """
    ref_files = dict(
            bowtie = "bowtie_indices.loc",
            bwa = "bwa_index.loc",
            samtools = "sam_fa_indices.loc",
            maq = "bowtie_indices.loc")
    remap_fns = dict(
            maq = _remap_to_maq
            )
    out_info = []
    for ref_get in [aligner, "samtools"]:
        ref_file = os.path.join(galaxy_base, "tool-data", ref_files[ref_get])
        with open(ref_file) as in_handle:
            for line in in_handle:
                if not line.startswith("#"):
                    parts = line.strip().split()
                    if parts[0] == "index":
                        parts = parts[1:]
                    if parts[0] == genome_build:
                        out_info.append(parts[-1])
                        break
        try:
            out_info[-1] = remap_fns[ref_get](out_info[-1])
        except KeyError:
            pass
        except IndexError:
            raise IndexError("Genome %s not found in %s" % (genome_build,
                ref_file))

    if len(out_info) != 2:
        raise ValueError("Did not find genome reference for %s %s" %
                (genome_build, aligner))
    else:
        return tuple(out_info)

# Utility functions

def _update_config_w_custom(config, lane_info):
    """Update the configuration for this lane if a custom analysis is specified.
    """
    config = copy.deepcopy(config)
    custom = config["custom_algorithms"].get(lane_info.get("analysis", None),
            None)
    if custom:
        for key, val in custom.iteritems():
            config["algorithm"][key] = val
    return config

if __name__ == "__main__":
    parser = OptionParser()
    (options, args) = parser.parse_args()
    kwargs = dict()
    main(*args, **kwargs)

########NEW FILE########
__FILENAME__ = build_compare_vcf
#!/usr/bin/env python
"""Build a test comparison dataset from an existing VCF file.

Produces a slightly modified comparison set to use for testing comparison
software.

Usage:
  build_compare_vcf.py <in_vcf_file>
"""
import os
import sys
import random

import vcf

def main(in_file):
    out_file = apply("{0}-cmp{1}".format, os.path.splitext(in_file))
    with open(in_file) as in_handle:
        with open(out_file, "w") as out_handle:
            rdr = vcf.Reader(in_handle)
            wtr = vcf.Writer(out_handle, rdr)
            for rec in rdr:
                out_rec = adjust_variant(rec)
                if out_rec:
                    wtr.write_record(out_rec)

def adjust_variant(rec):
    do_change = random.random()
    if do_change < 0.2:
        return None
    elif do_change < 0.5:
        return rec
    else:
        rec.samples = [adjust_genotype(g) for g in rec.samples]
        return rec

def adjust_genotype(g):
    alts = ["0", "1"]
    do_change = random.random()
    if do_change < 0.7:
        new_gt = None
    elif do_change < 0.9:
        new_gt = g.gt_phase_char().join(["."] * (len(g.gt_alleles)))
    else:
        new_gt = g.gt_phase_char().join([random.choice(alts) for x in g.gt_alleles])
    if new_gt:
        g.data = g.data._replace(GT=new_gt)
    return g

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = cg_svevents_to_vcf
#!/usr/bin/env python
"""Convert Complete Genomics SvEvents file of structural variants to VCF.

Handles:

  inversion/probable-inversion -> INV
  deletion -> DEL
  tandem-duplication -> DUP
  distal-duplication -> Breakends (BND)

Does not convert: complex

Requirements:

bx-python: https://bitbucket.org/james_taylor/bx-python/wiki/Home

Usage:
  cg_svevents_to_vcf.py <SV Events TSV file> <Genome in UCSC 2bit format>
"""
import sys
import csv
from collections import namedtuple

from bx.seq import twobit

def main(svevents_file, genome_file):
    genome_2bit = twobit.TwoBitFile(open(genome_file))
    for event in svevent_reader(svevents_file):
        for vcf_line in _svevent_to_vcf(event):
            print vcf_line

# ## Convert different types of svEvents into VCF info

VcfLine = namedtuple('VcfLine', ["chrom", "pos", "id", "ref", "alt", "info"])

def _svevent_to_vcf(event):
    if event["Type"] in ["inversion", "probable-inversion"]:
        out = _convert_event_inv(event)
    elif event["Type"] in ["deletion"]:
        out = _convert_event_del(event)
    elif event["Type"] in ["tandem-duplication"]:
        out = _convert_event_dup(event)
    elif event["Type"] in ["distal-duplication"]:
        out = _convert_event_bnd(event)
    elif event["Type"] in ["complex"]:
        out = [] # ignore complex events
    else:
        raise ValueError("Unexpected event type %s" % event["Type"])
    return out

def _convert_event_inv(event):
    print event
    return []

def _convert_event_del(event):
    return []

def _convert_event_dup(event):
    return []

def _convert_event_bnd(event):
    return []

def svevent_reader(in_file):
    """Lazy generator of SV events, returned as dictionary of parts.
    """
    with open(in_file) as in_handle:
        while 1:
            line = in_handle.next()
            if line.startswith(">"):
                break
        header = line[1:].rstrip().split("\t")
        reader = csv.reader(in_handle, dialect="excel-tab")
        for parts in reader:
            out = {}
            for h, p in zip(header, parts):
                out[h] = p
            yield out

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = collect_metrics_to_csv
#!/usr/bin/env python
"""Collect alignment summary metrics from multiple lanes and summarize as CSV.

Usage:
    collect_metrics_to_csv.py <comma separated list of lanes>
"""
import sys
import os
import csv
import glob
import collections
import contextlib

import yaml
import pysam

from bcbio.broad.metrics import PicardMetricsParser, PicardMetrics
from bcbio import utils, broad

WANT_METRICS = [
"AL_TOTAL_READS",
"AL_PF_READS_ALIGNED",
"AL_PF_HQ_ALIGNED_Q20_BASES",
"AL_PCT_READS_ALIGNED_IN_PAIRS",
"DUP_READ_PAIR_DUPLICATES",
"DUP_PERCENT_DUPLICATION",
"DUP_ESTIMATED_LIBRARY_SIZE",
"HS_BAIT_SET",
"HS_GENOME_SIZE",
"HS_LIBRARY_SIZE",
"HS_BAIT_TERRITORY",
"HS_TARGET_TERRITORY",
"HS_PF_UQ_BASES_ALIGNED",
"HS_ON_BAIT_BASES",
"HS_ON_TARGET_BASES",
"HS_PCT_SELECTED_BASES",
"HS_MEAN_TARGET_COVERAGE",
"HS_FOLD_ENRICHMENT",
"HS_ZERO_CVG_TARGETS_PCT",
"HS_FOLD_80_BASE_PENALTY",
"HS_PCT_TARGET_BASES_2X",
"HS_PCT_TARGET_BASES_10X",
"HS_PCT_TARGET_BASES_20X",
"HS_PENALTY_20X",
# ToDo
"SNP_TOTAL_SNPS",
"SNP_PCT_DBSNP",
"Lane IC PCT Mean RD1 Err Rate",
"Lane IC PCT Mean RD2 Err Rate",
]

def main(run_name, work_dir=None, config_file=None, ref_file=None,
         bait_file=None, target_file=None):
    if work_dir is None:
        work_dir = os.getcwd()
    parser = PicardMetricsParser()

    base_bams = _get_base_bams(work_dir, run_name)
    samples = [_get_sample_name(b) for (_, _, b) in base_bams]
    metrics = [lane_stats(l, b, f, run_name, parser, config_file, ref_file,
                          bait_file, target_file)
               for (l, b, f) in base_bams]
    header_counts = _get_header_counts(samples, metrics)
    header = [m for m in WANT_METRICS if header_counts[m] > 0]
    out_file = "%s-summary.csv" % (run_name)
    with open(out_file, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(["sample"] + header)
        for i, sample in enumerate(samples):
            info = [metrics[i].get(m, "") for m in header]
            writer.writerow([sample] + info)

def _get_header_counts(samples, metrics):
    header_counts = collections.defaultdict(int)
    for i, _ in enumerate(samples):
        for metric in WANT_METRICS:
            try:
                metrics[i][metric]
                header_counts[metric] += 1
            except KeyError:
                pass
    return header_counts

def _get_sample_name(in_file):
    bam_file = pysam.Samfile(in_file, "rb")
    name = bam_file.header["RG"][0]["SM"]
    bam_file.close()
    return name

def _get_base_bams(work_dir, run_name):
    bam_files = glob.glob(os.path.join(work_dir, "*_%s*-realign.bam" % run_name))
    # if not in the current base directory, might be in subdirectory as final results
    if len(bam_files) == 0:
        for dname in os.listdir(work_dir):
            bam_files.extend(glob.glob(os.path.join(work_dir, dname,
                                                    "*_%s*-gatkrecal*.bam" % run_name)))
    lane_info = dict()
    for cur_file in bam_files:
        lane_name = os.path.basename(cur_file).split("-")[0]
        lane_parts = lane_name.split("_")
        assert "_".join(lane_parts[1:3]) == run_name
        bc_id = lane_parts[3] if len(lane_parts) == 4 else None
        try:
            bc_id = int(bc_id)
        except ValueError:
            pass
        lane_id = lane_parts[0]
        try:
            lane_id = int(lane_id)
        except ValueError:
            pass
        lane_info[(lane_id, bc_id)] = cur_file
    final = []
    for key in sorted(lane_info.keys()):
        lane, bc = key
        final.append((lane, bc, lane_info[key]))
    return final

def lane_stats(lane, bc_id, bam_fname, run_name, parser,
               config_file, ref_file, bait_file, target_file):
    base_name = "%s_%s" % (lane, run_name)
    if bc_id:
        base_name += "_%s-" % bc_id
    path = os.path.dirname(bam_fname)
    metrics_files = glob.glob(os.path.join(path, "%s*metrics" % base_name))
    if len(metrics_files) == 0:
        assert config_file is not None
        assert ref_file is not None
        metrics_dir = _generate_metrics(bam_fname, config_file, ref_file,
                                        bait_file, target_file)
        metrics_files = glob.glob(os.path.join(metrics_dir, "%s*metrics" % base_name))
    metrics = parser.extract_metrics(metrics_files)
    return metrics

def _generate_metrics(bam_fname, config_file, ref_file,
                      bait_file, target_file):
    """Run Picard commands to generate metrics files when missing.
    """
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    broad_runner = broad.runner_from_config(config)
    bam_fname = os.path.abspath(bam_fname)
    path = os.path.dirname(bam_fname)
    out_dir = os.path.join(path, "metrics")
    utils.safe_makedir(out_dir)
    with utils.chdir(out_dir):
        with utils.curdir_tmpdir() as tmp_dir:
            cur_bam = os.path.basename(bam_fname)
            if not os.path.exists(cur_bam):
                os.symlink(bam_fname, cur_bam)
            gen_metrics = PicardMetrics(broad_runner, tmp_dir)
            gen_metrics.report(cur_bam, ref_file,
                               _bam_is_paired(bam_fname),
                               bait_file, target_file)
    return out_dir

def _bam_is_paired(bam_fname):
    with contextlib.closing(pysam.Samfile(bam_fname, "rb")) as work_bam:
        for read in work_bam:
            if not read.is_unmapped:
                return read.is_paired

if __name__ == "__main__":
    main(*sys.argv[1:])


########NEW FILE########
__FILENAME__ = convert_samplesheet_config
#!/usr/bin/env python
"""Convert Illumina SampleSheet CSV files to the run_info.yaml input file.

This allows running the analysis pipeline without Galaxy, using CSV input
files from Illumina SampleSheet or Genesifter.

Usage:
  convert_samplesheet_config.py <input csv>
"""
import sys

from bcbio.illumina import samplesheet

if __name__ == "__main__":
    samplesheet.csv2yaml(sys.argv[1])

########NEW FILE########
__FILENAME__ = hydra_to_vcf
#!/usr/bin/env python
"""Convert Hydra BEDPE output into VCF 4.1 format.

File format definitions:

http://code.google.com/p/hydra-sv/wiki/FileFormats
http://www.1000genomes.org/wiki/Analysis/Variant%20Call%20Format/
vcf-variant-call-format-version-41

Figure 2 of this review:

Quinlan, AR and IM Hall. 2011. Characterizing complex structural variation
in germline and somatic genomes. Trends in Genetics.
http://download.cell.com/trends/genetics/pdf/PIIS0168952511001685.pdf

Is a great overview of different structural variations and their breakpoint
representation.

Requirements:

bx-python: https://bitbucket.org/james_taylor/bx-python/wiki/Home

Usage:
  hydra_to_vcf.py <hydra output file> <Genome in UCSC 2bit format>
                  [--minsupport Minimum weighted support to include breakends]
"""
import os
import csv
import sys
import unittest
from collections import namedtuple, defaultdict
from operator import attrgetter
from optparse import OptionParser

from bx.seq import twobit
from bx.intervals.cluster import ClusterTree

def main(hydra_file, genome_file, min_support=0):
    options = {"min_support": min_support, "max_single_size": 10000}
    out_file = "{0}.vcf".format(os.path.splitext(hydra_file)[0])
    genome_2bit = twobit.TwoBitFile(open(genome_file))
    with open(out_file, "w") as out_handle:
        hydra_to_vcf_writer(hydra_file, genome_2bit, options, out_handle)

# ## Build VCF breakend representation from Hydra BedPe format

def _vcf_info(start, end, mate_id, info=None):
    """Return breakend information line with mate and imprecise location.
    """
    out = "SVTYPE=BND;MATEID={mate};IMPRECISE;CIPOS=0,{size}".format(
        mate=mate_id, size=end-start)
    if info is not None:
        extra_info = ";".join("{0}={1}".format(k, v) for k, v in info.iteritems())
        out = "{0};{1}".format(out, extra_info)
    return out

def _vcf_alt(base, other_chr, other_pos, isrc, is_first):
    """Create ALT allele line in VCF 4.1 format associating with other paired end.
    """
    if is_first:
        pipe = "[" if isrc else "]"
        out_str = "{base}{pipe}{chr}:{pos}{pipe}"
    else:
        pipe = "]" if isrc else "["
        out_str = "{pipe}{chr}:{pos}{pipe}{base}"
    return out_str.format(pipe=pipe, chr=other_chr, pos=other_pos + 1,
                          base=base)

def _breakend_orientation(strand1, strand2):
    """Convert BEDPE strand representation of breakpoints into VCF.

    | strand1  |  strand2 |     VCF      |
    +----------+----------+--------------+
    |   +      |     -    | t[p[ ]p]t    |
    |   +      |     +    | t]p] t]p]    |
    |   -      |     -    | [p[t [p[t    |
    |   -      |     +    | ]p]t t[p[    |
    """
    EndOrientation = namedtuple("EndOrientation",
                                ["is_first1", "is_rc1", "is_first2", "is_rc2"])
    if strand1 == "+" and strand2 == "-":
        return EndOrientation(True, True, False, True)
    elif strand1 == "+" and strand2 == "+":
        return EndOrientation(True, False, True, False)
    elif strand1 == "-" and strand2 == "-":
        return EndOrientation(False, False, False, False)
    elif strand1 == "-" and strand2 == "+":
        return EndOrientation(False, True, True, True)
    else:
        raise ValueError("Unexpected strand pairing: {0} {1}".format(
            strand1, strand2))

VcfLine = namedtuple('VcfLine', ["chrom", "pos", "id", "ref", "alt", "info"])

def build_vcf_parts(feature, genome_2bit, info=None):
    """Convert BedPe feature information into VCF part representation.

    Each feature will have two VCF lines for each side of the breakpoint.
    """
    base1 = genome_2bit[feature.chrom1].get(
        feature.start1, feature.start1 + 1).upper()
    id1 = "hydra{0}a".format(feature.name)
    base2 = genome_2bit[feature.chrom2].get(
        feature.start2, feature.start2 + 1).upper()
    id2 = "hydra{0}b".format(feature.name)
    orientation = _breakend_orientation(feature.strand1, feature.strand2)
    return (VcfLine(feature.chrom1, feature.start1, id1, base1,
                    _vcf_alt(base1, feature.chrom2, feature.start2,
                             orientation.is_rc1, orientation.is_first1),
                    _vcf_info(feature.start1, feature.end1, id2, info)),
            VcfLine(feature.chrom2, feature.start2, id2, base2,
                    _vcf_alt(base2, feature.chrom1, feature.start1,
                             orientation.is_rc2, orientation.is_first2),
                    _vcf_info(feature.start2, feature.end2, id1, info)))

# ## Represent standard variants types
# Convert breakends into deletions, tandem duplications and inversions

def is_deletion(x, options):
    strand_orientation = ["+", "-"]
    return (x.chrom1 == x.chrom2 and [x.strand1, x.strand2] == strand_orientation
            and (x.start2 - x.start1) < options.get("max_single_size", 0))

def _vcf_single_end_info(x, svtype, is_removal=False):
    if is_removal:
        length = x.start1 - x.start2
    else:
        length = x.start2 - x.start1
    return "SVTYPE={type};IMPRECISE;CIPOS=0,{size1};CIEND=0,{size2};" \
           "END={end};SVLEN={length}".format(size1=x.end1 - x.start1,
                                             size2=x.end2 - x.start2,
                                             end=x.start2,
                                             type=svtype,
                                             length=length)

def build_vcf_deletion(x, genome_2bit):
    """Provide representation of deletion from BedPE breakpoints.
    """
    base1 = genome_2bit[x.chrom1].get(x.start1, x.start1 + 1).upper()
    id1 = "hydra{0}".format(x.name)
    return VcfLine(x.chrom1, x.start1, id1, base1, "<DEL>",
                   _vcf_single_end_info(x, "DEL", True))

def is_tandem_dup(x, options):
    strand_orientation = ["-", "+"]
    return (x.chrom1 == x.chrom2 and [x.strand1, x.strand2] == strand_orientation
            and (x.start2 - x.start1) < options.get("max_single_size", 0))

def build_tandem_deletion(x, genome_2bit):
    """Provide representation of tandem duplication.
    """
    base1 = genome_2bit[x.chrom1].get(x.start1, x.start1 + 1).upper()
    id1 = "hydra{0}".format(x.name)
    return VcfLine(x.chrom1, x.start1, id1, base1, "<DUP:TANDEM>",
                   _vcf_single_end_info(x, "DUP"))

def is_inversion(x1, x2):
    strand1 = ["+", "+"]
    strand2 = ["-", "-"]
    return (x1.chrom1 == x1.chrom2 and x1.chrom1 == x2.chrom1 and
            (([x1.strand1, x1.strand2] == strand1 and
              [x2.strand1, x2.strand2] == strand2) or
             ([x1.strand1, x1.strand2] == strand2 and
              [x2.strand1, x2.strand2] == strand1)))

def build_vcf_inversion(x1, x2, genome_2bit):
    """Provide representation of inversion from BedPE breakpoints.
    """
    id1 = "hydra{0}".format(x1.name)
    start_coords = sorted([x1.start1, x1.end1, x2.start1, x2.end1])
    end_coords = sorted([x1.start2, x1.end2, x2.start2, x2.start2])
    start_pos = (start_coords[1] + start_coords[2]) // 2
    end_pos = (end_coords[1] + end_coords[2]) // 2
    base1 = genome_2bit[x1.chrom1].get(start_pos, start_pos + 1).upper()
    info = "SVTYPE=INV;IMPRECISE;CIPOS={cip1},{cip2};CIEND={cie1},{cie2};" \
           "END={end};SVLEN={length}".format(cip1=start_pos - start_coords[0],
                                             cip2=start_coords[-1] - start_pos,
                                             cie1=end_pos - end_coords[0],
                                             cie2=end_coords[-1] - end_pos,
                                             end=end_pos,
                                             length=end_pos-start_pos)
    return VcfLine(x1.chrom1, start_pos, id1, base1, "<INV>", info)

def is_translocation(x1, x2):
    strand1 = ["+", "-"]
    strand2 = ["-", "+"]
    return (x1.chrom1 != x1.chrom2 and
            ([x1.strand1, x1.strand2] == strand1 and
             [x2.strand1, x2.strand2] == strand2) or
            ([x1.strand1, x1.strand2] == strand2 and
             [x2.strand1, x2.strand2] == strand1))

def get_translocation_info(x1, x2):
    return {"EVENT": "translocation_{0}_{1}".format(x1.name, x2.name)}

# ## Parse Hydra output into BedPe tuple representation

def hydra_parser(in_file, options=None):
    """Parse hydra input file into namedtuple of values.
    """
    if options is None: options = {}
    BedPe = namedtuple('BedPe', ["chrom1", "start1", "end1",
                                 "chrom2", "start2", "end2",
                                 "name", "strand1", "strand2",
                                 "support"])
    with open(in_file) as in_handle:
        reader = csv.reader(in_handle, dialect="excel-tab")
        for line in reader:
            cur = BedPe(line[0], int(line[1]), int(line[2]),
                        line[3], int(line[4]), int(line[5]),
                        line[6], line[8], line[9],
                        float(line[18]))
            if cur.support >= options.get("min_support", 0):
                yield cur

def _cluster_by(end_iter, attr1, attr2, cluster_distance):
    """Cluster breakends by specified attributes.
    """
    ClusterInfo = namedtuple("ClusterInfo", ["chroms", "clusters", "lookup"])
    chr_clusters = {}
    chroms = []
    brends_by_id = {}
    for brend in end_iter:
        if not chr_clusters.has_key(brend.chrom1):
            chroms.append(brend.chrom1)
            chr_clusters[brend.chrom1] = ClusterTree(cluster_distance, 1)
        brends_by_id[int(brend.name)] = brend
        chr_clusters[brend.chrom1].insert(getattr(brend, attr1),
                                          getattr(brend, attr2),
                                          int(brend.name))
    return ClusterInfo(chroms, chr_clusters, brends_by_id)

def _calculate_cluster_distance(end_iter):
    """Compute allowed distance for clustering based on end confidence intervals.
    """
    out = []
    sizes = []
    for x in end_iter:
        out.append(x)
        sizes.append(x.end1 - x.start1)
        sizes.append(x.end2 - x.start2)
    distance = sum(sizes) // len(sizes)
    return distance, out

def group_hydra_breakends(end_iter):
    """Group together hydra breakends with overlapping ends.

    This provides a way to identify inversions, translocations
    and insertions present in hydra break point ends. We cluster together the
    endpoints and return together any items with closely oriented pairs.
    This helps in describing more complex rearrangement events.
    """
    cluster_distance, all_ends = _calculate_cluster_distance(end_iter)
    first_cluster = _cluster_by(all_ends, "start1", "end1", cluster_distance)
    for chrom in first_cluster.chroms:
        for _, _, brends in first_cluster.clusters[chrom].getregions():
            if len(brends) == 1:
                yield [first_cluster.lookup[brends[0]]]
            else:
                second_cluster = _cluster_by([first_cluster.lookup[x] for x in brends],
                                             "start2", "end2", cluster_distance)
                for chrom2 in second_cluster.chroms:
                    for _, _, brends in second_cluster.clusters[chrom].getregions():
                        yield [second_cluster.lookup[x] for x in brends]

# ## Write VCF output

def _write_vcf_header(out_handle):
    """Write VCF header information for Hydra structural variant.
    """
    def w(line):
        out_handle.write("{0}\n".format(line))
    w('##fileformat=VCFv4.1')
    w('##INFO=<ID=IMPRECISE,Number=0,Type=Flag,Description="Imprecise structural variation">')
    w('##INFO=<ID=END,Number=1,Type=Integer,'
      'Description="End position of the variant described in this record">')
    w('##INFO=<ID=CIPOS,Number=2,Type=Integer,'
      'Description="Confidence interval around POS for imprecise variants">')
    w('##INFO=<ID=CIEND,Number=2,Type=Integer,'
      'Description="Confidence interval around END for imprecise variants">')
    w('##INFO=<ID=SVLEN,Number=.,Type=Integer,'
      'Description="Difference in length between REF and ALT alleles">')
    w('##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Type of structural variant">')
    w('##INFO=<ID=MATEID,Number=.,Type=String,Description="ID of mate breakends">')
    w('##INFO=<ID=EVENT,Number=1,Type=String,Description="ID of event associated to breakend">')
    w('##ALT=<ID=DEL,Description="Deletion">')
    w('##ALT=<ID=INV,Description="Inversion">')
    w('##ALT=<ID=DUP,Description="Duplication">')
    w('##ALT=<ID=DUP:TANDEM,Description="Tandem Duplication">')
    w('##source=hydra')
    w("#" + "\t".join(["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]))

def _write_vcf_breakend(brend, out_handle):
    """Write out a single VCF line with breakpoint information.
    """
    out_handle.write("{0}\n".format("\t".join(str(x) for x in
        [brend.chrom, brend.pos + 1, brend.id, brend.ref, brend.alt,
         ".", "PASS", brend.info])))

def _get_vcf_breakends(hydra_file, genome_2bit, options=None):
    """Parse BEDPE input, yielding VCF ready breakends.
    """
    if options is None: options = {}
    for features in group_hydra_breakends(hydra_parser(hydra_file, options)):
        if len(features) == 1 and is_deletion(features[0], options):
            yield build_vcf_deletion(features[0], genome_2bit)
        elif len(features) == 1 and is_tandem_dup(features[0], options):
            yield build_tandem_deletion(features[0], genome_2bit)
        elif len(features) == 2 and is_inversion(*features):
            yield build_vcf_inversion(features[0], features[1], genome_2bit)
        elif len(features) == 2 and is_translocation(*features):
            info = get_translocation_info(features[0], features[1])
            for feature in features:
                for brend in build_vcf_parts(feature, genome_2bit, info):
                    yield brend
        else:
            for feature in features:
                for brend in build_vcf_parts(feature, genome_2bit):
                    yield brend

def hydra_to_vcf_writer(hydra_file, genome_2bit, options, out_handle):
    """Write hydra output as sorted VCF file.

    Requires loading the hydra file into memory to perform sorting
    on output VCF. Could generalize this to no sorting or by-chromosome
    approach if this proves too memory intensive.
    """
    _write_vcf_header(out_handle)
    brends = list(_get_vcf_breakends(hydra_file, genome_2bit, options))
    brends.sort(key=attrgetter("chrom", "pos"))
    for brend in brends:
        _write_vcf_breakend(brend, out_handle)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--minsupport", dest="minsupport", default=0)
    (options, args) = parser.parse_args()
    if len(args) != 2:
        print "Incorrect arguments"
        print __doc__
        sys.exist()
    main(args[0], args[1], int(options.minsupport))

# ## Test code

class HydraConvertTest(unittest.TestCase):
    """Test Hydra output conversion to VCF.
    """
    def setUp(self):
        self.work_dir = os.path.join(os.path.dirname(__file__), os.pardir,
                                     "tests", "data")
        self.in_file = os.path.join(self.work_dir, "structural",
                                    "NA12878-hydra.txt")
        self.genome_file = os.path.join(self.work_dir, "genomes", "hg19",
                                        "ucsc", "hg19.2bit")

    def test_1_input_parser(self):
        """Parse input file as BEDPE.
        """
        breakend = hydra_parser(self.in_file).next()
        assert breakend.chrom1 == "chr22"
        assert breakend.start1 == 9763 
        assert breakend.strand2 == "+"
        assert breakend.name == "1"
        assert breakend.support == 4.0

    def test_2_vcf_parts(self):
        """Convert BEDPE input line into VCF output parts.
        """
        genome_2bit = twobit.TwoBitFile(open(self.genome_file))
        breakends = hydra_parser(self.in_file)
        brend1, brend2 = build_vcf_parts(breakends.next(), genome_2bit)
        assert brend1.alt == "G]chr22:10112]"
        assert brend2.alt == "C]chr22:9764]"
        assert brend2.info == "SVTYPE=BND;MATEID=hydra1a;IMPRECISE;CIPOS=0,102", brend2.info
        brend1, brend2 = build_vcf_parts(breakends.next(), genome_2bit)
        assert brend1.alt == "A[chr22:12112["
        assert brend2.alt == "]chr22:7764]G"
        brend1, brend2 = build_vcf_parts(breakends.next(), genome_2bit)
        assert brend1.alt == "[chr22:11112[A"
        assert brend2.alt == "[chr22:8764[T"
        brend1, brend2 = build_vcf_parts(breakends.next(), genome_2bit)
        assert brend1.alt == "]chr22:13112]G", brend1.alt
        assert brend2.alt == "A[chr22:9764[", brend2.alt

    def test_3_deletions(self):
        """Convert BEDPE breakends that form a deletion.
        """
        genome_2bit = twobit.TwoBitFile(open(self.genome_file))
        parts = _get_vcf_breakends(self.in_file, genome_2bit, {"max_single_size": 5000})
        deletion = parts.next()
        assert deletion.alt == "<DEL>", deletion
        assert "SVLEN=-4348" in deletion.info

########NEW FILE########
__FILENAME__ = monthly_billing_report
#!/usr/bin/env python
"""Retrieve a high level summary report of sequencing done in a month.

Usage:
    sequencing_report.py --month=<month> --year=<year> <YAML post process config>

month and year are both optional, in which case we'll default to this month
in the current year, which is the standard report of interest.

A month runs from the start of the 15th of the previous month to the end of the
14th in the current month, and tracks all projects which had their states set to
complete in this period.
"""
import sys
import csv
import calendar
from datetime import datetime
from optparse import OptionParser

import yaml

from bcbio.galaxy.api import GalaxyApiAccess

def main(config_file, month, year):
    with open(config_file) as in_handle:
        config = yaml.safe_load(in_handle)
    galaxy_api = GalaxyApiAccess(config["galaxy_url"],
        config["galaxy_apikey"])
    smonth, syear = (month - 1, year) if month > 1 else (12, year - 1)
    start_date = datetime(syear, smonth, 15, 0, 0, 0)
    # last day calculation useful if definition of month is
    # from first to last day instead of 15th-15th
    #(_, last_day) = calendar.monthrange(year, month)
    end_date = datetime(year, month, 14, 23, 59, 59)
    out_file = "%s_%s" % (start_date.strftime("%b"),
            end_date.strftime("%b-%Y-sequencing.csv"))
    with open(out_file, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow([
            "Date", "Product", "Payment", "Researcher", "Lab", "Email",
            "Project", "Sample", "Description", "Genome", "Flowcell",
            "Lane", "Received", "Notes"])
        for s in galaxy_api.sqn_report(start_date.isoformat(),
                end_date.isoformat()):
            f_parts = s["sqn_run"]["run_folder"].split("_")
            flowcell = "_".join([f_parts[0], f_parts[-1]])
            writer.writerow([
                s["sqn_run"]["date"],
                s["sqn_type"],
                s["project"]["payment_(fund_number)"],
                s["project"]["researcher"],
                s["project"]["lab_association"],
                s["project"]["email"],
                s["project"]["project_name"],
                s["name"],
                s["description"],
                s["genome_build"],
                flowcell,
                s["sqn_run"]["lane"],
                _received_date(s["events"]),
                s["sqn_run"]["results_notes"]])

def _received_date(events):
    for event in events:
        if event["event"] == "arrived":
            return event["time"]
    return ""

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-m", "--month", dest="month")
    parser.add_option("-y", "--year", dest="year")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        print __doc__
        sys.exit()
    cur_year, cur_month = datetime.now().timetuple()[:2]
    if not options.month:
        options.month = cur_month
    if not options.year:
        options.year = cur_year
    main(args[0], int(options.month), int(options.year))

########NEW FILE########
__FILENAME__ = plink_to_vcf
#!/usr/bin/env python
"""Convert Plink ped/map files into VCF format using plink and Plink/SEQ.

Latest version available as part of bcbio-nextgen:
https://github.com/chapmanb/bcbio-nextgen/blob/master/scripts/plink_to_vcf.py

Requires:

plink: http://pngu.mgh.harvard.edu/~purcell/plink/
PLINK/SEQ: http://atgu.mgh.harvard.edu/plinkseq/
bx-python: https://bitbucket.org/james_taylor/bx-python/wiki/Home

You also need the genome reference file in 2bit format:
http://genome.ucsc.edu/FAQ/FAQformat.html#format7
using faToTwoBit:
http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/

Usage:
  plink_to_vcf.py <ped file> <map file> <UCSC reference file in 2bit format)

"""
import os
import sys
import subprocess

from bx.seq import twobit

def main(ped_file, map_file, ref_file):
    base_dir = os.getcwd()
    pbed_prefix = convert_to_plink_bed(ped_file, map_file, base_dir)
    vcf_file = convert_bed_to_vcf(pbed_prefix, ped_file, base_dir)
    fix_nonref_positions(vcf_file, ref_file)

def convert_to_plink_bed(ped_file, map_file, base_dir):
    # from ubuntu package, 'plink' otherwise
    for plink_cl in ["p-link", "plink"]:
        try:
            subprocess.check_call([plink_cl, "--help"])
            break
        except:
            pass
    plink_prefix = os.path.splitext(os.path.basename(ped_file))[0].replace(".", "_")
    work_dir = os.path.join(base_dir, "vcfconvert")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    out_base = os.path.join(work_dir, plink_prefix)
    if not os.path.exists("{0}.bed".format(out_base)):
        subprocess.check_call([plink_cl, "--noweb",
                               "--ped", ped_file, "--map", map_file,
                               "--make-bed", "--out", out_base])
    return out_base

def convert_bed_to_vcf(pbed_prefix, ped_file, base_dir):
    out_file = os.path.join(base_dir,
                            "{0}-raw.vcf".format(os.path.splitext(os.path.basename(ped_file))[0]))
    if not os.path.exists(out_file):
        subprocess.check_call(["pseq", pbed_prefix, "new-project"])
        subprocess.check_call(["pseq", pbed_prefix, "load-plink",
                               "--file", pbed_prefix, "--id", "vcfconvert"])
        with open(out_file, "w") as out_handle:
            subprocess.check_call(["pseq", pbed_prefix, "write-vcf"],
                                  stdout=out_handle)
    return out_file

def fix_line_problems(parts):
    """Fix problem alleles and reference/variant bases in VCF line.
    """
    varinfo = parts[:9]
    genotypes = []
    # replace haploid calls
    for x in parts[9:]:
        if len(x) == 1:
            x = "./."
        genotypes.append(x)
    if varinfo[3] == "0": varinfo[3] = "N"
    if varinfo[4] == "0": varinfo[4] = "N"
    return varinfo, genotypes

def fix_vcf_line(parts, ref_base):
    """Orient VCF allele calls with respect to reference base.

    Handles cases with ref and variant swaps. strand complements.
    """
    swap = {"1/1": "0/0", "0/1": "0/1", "0/0": "1/1", "./.": "./."}
    complements = {"G": "C", "A": "T", "C": "G", "T": "A", "N": "N"}
    varinfo, genotypes = fix_line_problems(parts)
    ref, var = varinfo[3:5]
    # non-reference regions or non-informative, can't do anything
    if ref_base in [None, "N"] or set(genotypes) == set(["./."]):
        varinfo = None
    # matching reference, all good
    elif ref_base == ref:
        assert ref_base == ref, (ref_base, parts)
    # swapped reference and alternate regions
    elif ref_base == var or ref in ["N", "0"]:
        varinfo[3] = var
        varinfo[4] = ref
        genotypes = [swap[x] for x in genotypes]
    # reference is on alternate strand
    elif ref_base != ref and complements.get(ref) == ref_base:
        varinfo[3] = complements[ref]
        varinfo[4] = ",".join([complements[v] for v in var.split(",")])
    # unspecified alternative base
    elif ref_base != ref and var in ["N", "0"]:
        varinfo[3] = ref_base
        varinfo[4] = ref
        genotypes = [swap[x] for x in genotypes]
    # swapped and on alternate strand
    elif ref_base != ref and complements.get(var) == ref_base:
        varinfo[3] = complements[var]
        varinfo[4] = ",".join([complements[v] for v in ref.split(",")])
        genotypes = [swap[x] for x in genotypes]
    else:
        print "Did not associate ref {0} with line: {1}".format(
            ref_base, varinfo)
    if varinfo is not None:
        return varinfo + genotypes

def fix_nonref_positions(in_file, ref_file):
    """Fix Genotyping VCF positions where the bases are all variants.

    The plink/pseq output does not handle these correctly, and
    has all reference/variant bases reversed.
    """
    ignore_chrs = ["."]
    ref2bit = twobit.TwoBitFile(open(ref_file))
    out_file = in_file.replace("-raw.vcf", ".vcf")

    with open(in_file) as in_handle:
        with open(out_file, "w") as out_handle:
            for line in in_handle:
                if line.startswith("#"):
                    out_handle.write(line)
                else:
                    parts = line.rstrip("\r\n").split("\t")
                    pos = int(parts[1])
                    # handle chr/non-chr naming
                    if parts[0] not in ref2bit.keys():
                        parts[0] = parts[0].replace("chr", "")
                    ref_base = None
                    if parts[0] not in ignore_chrs:
                        try:
                            ref_base = ref2bit[parts[0]].get(pos-1, pos).upper()
                        except Exception, msg:
                            # off the end of the chromosome
                            if str(msg).startswith("end before start"):
                                print msg
                            else:
                                print parts
                                raise
                    parts = fix_vcf_line(parts, ref_base)
                    if parts is not None:
                        out_handle.write("\t".join(parts) + "\n")
        return out_file

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Incorrect arguments"
        print __doc__
        sys.exit(1)
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = rename_samples
#!/usr/bin/env python
"""Rename sample name in a BAM file, eliminating spaces and colon characters.

Usage:
    rename_samples.py [<one or more> <input BAM files>]

Requires:
    pysam -- http://code.google.com/p/pysam/
      % sudo easy_install Cython
      % wget http://pysam.googlecode.com/files/pysam-0.3.tar.gz
      % tar -xzvpf pysam-0.3.tar.gz
      % cd pysam-0.3
      % python setup.py build && sudo python setup.py install
"""
import os
import sys

import pysam

def main(in_files):
    for in_file in in_files:
        out_file = "%s.rename" % in_file
        backup_file = "%s.orig" % in_file
        orig = pysam.Samfile(in_file, "rb")
        new_header = orig.header
        new_header["RG"][0]["SM"] = new_header["RG"][0]["SM"].split(": ")[-1]
        new = pysam.Samfile(out_file, "wb", header=new_header)
        for read in orig:
            new.write(read)
        orig.close()
        new.close()
        os.rename(in_file, backup_file)
        os.rename(out_file, in_file)

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = resort_bam_karyotype
#!/usr/bin/env python
"""Resort a BAM file karyotypically to match GATK's preferred file order.

Broad's GATK and associated resources prefer BAM files sorted as:

    chr1, chr2... chr10, chr11... chrX

instead of the simple alphabetic sort:

    chr1, chr10, chr2 ...

This takes a sorted BAM files with an alternative ordering of chromosomes
and re-sorts it the karyotypic way.

Usage:
    resort_bam_karyotype.py <reference dict> [<one or more> <BAM files>]

<reference dict> is a *.dict file produced by Picard that identifies the order
of chromsomes to sort by:

java -jar CreateSequenceDictionary.jar REFERENCE=your.fasta OUTPUT=your.dict

Requires:
    pysam -- http://code.google.com/p/pysam/
"""
import os
import sys

import pysam

def main(ref_file, *in_bams):
    ref = pysam.Samfile(ref_file, "r")
    sorter = SortByHeader(ref.header)
    for bam in in_bams:
        sort_bam(bam, sorter.header_cmp, sorter.to_include)

def sort_bam(in_bam, sort_fn, to_include=None):
    out_file = "%s-ksort%s" % os.path.splitext(in_bam)
    index_file = "%s.bai" % in_bam
    if not os.path.exists(index_file):
        pysam.index(in_bam)

    orig = pysam.Samfile(in_bam, "rb")
    chroms = [(c["SN"], c) for c in orig.header["SQ"]]
    new_chroms = chroms[:]
    if to_include:
        new_chroms = [(c, x) for (c, x) in new_chroms if c in to_include]
    new_chroms.sort(sort_fn)
    remapper = _id_remapper(chroms, new_chroms)
    new_header = orig.header
    new_header["SQ"] = [h for (_, h) in new_chroms]

    new = pysam.Samfile(out_file, "wb", header=new_header)
    for (chrom, _) in new_chroms:
        for read in orig.fetch(chrom):
            write = True
            read.rname = remapper[read.rname]
            try:
                read.mrnm = remapper[read.mrnm]
            # read pair is on a chromosome we are not using
            except KeyError:
                assert to_include is not None
                write = False
            if write:
                new.write(read)

def _id_remapper(orig, new):
    """Provide a dictionary remapping original read indexes to new indexes.

    When re-ordering the header, the individual read identifiers need to be
    updated as well.
    """
    new_chrom_to_index = {}
    for i_n, (chr_n, _) in enumerate(new):
        new_chrom_to_index[chr_n] = i_n
    remap_indexes = {}
    for i_o, (chr_o, _) in enumerate(orig):
        if chr_o in new_chrom_to_index.keys():
            remap_indexes[i_o] = new_chrom_to_index[chr_o]
    remap_indexes[None] = None
    return remap_indexes

class SortByHeader:
    """Provide chromosome sorting to match an existing header.
    """
    def __init__(self, base_header):
        self._chrom_indexes = {}
        self.to_include = []
        for i, item in enumerate(base_header["SQ"]):
            self._chrom_indexes[item["SN"]] = i
            self.to_include.append(item["SN"])

    def header_cmp(self, one, two):
        return cmp(self._chrom_indexes[one[0]],
                   self._chrom_indexes[two[0]])

def sort_by_karyotype(one, two):
    """Sort function to order reads by karyotype.
    """
    return cmp(_split_to_karyotype(one[0]),
               _split_to_karyotype(two[0]))

def _split_to_karyotype(name):
    parts = name.replace("chr", "").split("_")
    try:
        parts[0] = int(parts[0])
    except ValueError:
        pass
    # anything with an extension (_random) goes at the end
    if len(parts) > 1:
        parts.insert(0, "z")
    return parts

if __name__ == "__main__":
    main(*sys.argv[1:])


########NEW FILE########
__FILENAME__ = sort_gatk_intervals
#!/usr/bin/env python
"""Sort GATK interval lists based on a sequence dictionary.

Usage:
    sort_gatk_intervals.py <interval file> [<sequence dictionary>]

The sequence dictionary is needed if the original interval file does not contain
it. The output file is a Picard style file with a sequence dictionary and
semi-SAM formatted lines.
"""
import sys
import os

def main(interval_file, seqdict_file=None):
    out_file = "%s-sort.interval_list" % (
            os.path.splitext(interval_file)[0].replace(".", "-"))
    with open(out_file, "w") as out_handle:
        with open(interval_file) as in_handle:
            if seqdict_file is None:
                chr_indexes, seqdict = read_dict(in_handle)
            else:
                with open(seqdict_file) as seqdict_handle:
                    chr_indexes, seqdict = read_dict(seqdict_handle)
            out_handle.write(seqdict)
        all_parts = []
        with open(interval_file) as in_handle:
            for parts in read_intervals(in_handle):
                try:
                    all_parts.append(((chr_indexes[parts[0]], int(parts[1]),
                        int(parts[2])), parts))
                except KeyError:
                    print parts[0]
        all_parts.sort()
        for (_, parts) in all_parts:
            out_handle.write("\t".join(parts) + "\n")

def read_intervals(in_handle):
    for i, line in enumerate(l for l in in_handle if not l.startswith("@")):
        parts = line.rstrip("\r\n").split()
        if len(parts) == 1:
            chr_name, loc = parts[0].split(":")
            start, end = loc.split("-")
            yield (chr_name, start, end, "+", "interval_%s" % i)
        elif len(parts) == 6:
            chr_name, start, end, strand, name, _ = parts
            #chr_name, start, end, name, _, strand = parts
            yield (chr_name, start, end, strand, name)
        elif len(parts) == 5:
            yield parts
        else:
            raise NotImplementedError(parts)

def read_dict(in_handle):
    parts = []
    chr_indexes = dict()
    cur_index = 0
    while 1:
        line = in_handle.readline()
        if not line.startswith("@"):
            break
        parts.append(line)
        if line.startswith("@SQ"):
            sn_part = [p for p in line.split("\t") if p.startswith("SN:")][0]
            (_, chr_name) = sn_part.split(":")
            chr_indexes[chr_name] = cur_index
            cur_index += 1
    return chr_indexes, "".join(parts)

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = summarize_gemini_tstv
#!/usr/bin/env python
"""Provide table summarizing Transition/Transversion ratios for variants.
"""
import os
import sys
import glob

import sh
import pandas

def main(work_dir):
    stats = ["tstv", "tstv-coding", "tstv-noncoding", "vars-by-sample"]
    ext = "-gemini.db"
    out = []
    for fname in glob.glob(os.path.join(work_dir, "*{0}".format(ext))):
        cur = {"name": os.path.basename(fname).replace(ext, "")}
        for stat in stats:
            cur[stat] = calculate_gemini_stat(stat, fname)
        out.append(cur)
    df = pandas.DataFrame(out)
    print df

def calculate_gemini_stat(stat, fname):
    out = sh.gemini("stats", "--{0}".format(stat), fname)
    return float(out.split("\n")[1].split("\t")[-1])

if __name__ == "__main__":
    main(os.getcwd())
    

########NEW FILE########
__FILENAME__ = test_automated_analysis
"""This directory is setup with configurations to run the main functional test.

It exercises a full analysis pipeline on a smaller subset of data.
"""
import os
import subprocess
import unittest
import shutil
import contextlib
import collections
import functools

from nose import SkipTest
from nose.plugins.attrib import attr
import yaml

from bcbio.pipeline.config_utils import load_system_config

@contextlib.contextmanager
def make_workdir():
    remove_old_dir = True
    #remove_old_dir = False
    dirname = os.path.join(os.path.dirname(__file__), "test_automated_output")
    if remove_old_dir:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
        os.makedirs(dirname)
    orig_dir = os.getcwd()
    try:
        os.chdir(dirname)
        yield dirname
    finally:
        os.chdir(orig_dir)

def expected_failure(test):
    """Small decorator to mark tests as expected failure.
    Useful for tests that are work-in-progress.
    """
    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except Exception:
            raise SkipTest
        else:
            raise AssertionError('Failure expected')
    return inner

def get_post_process_yaml(data_dir, workdir):
    try:
        from bcbiovm.docker.defaults import get_datadir
        datadir = get_datadir()
        system = os.path.join(datadir, "galaxy", "bcbio_system.yaml") if datadir else None
    except ImportError:
        system = None
    if system is None or not os.path.exists(system):
        try:
            _, system = load_system_config("bcbio_system.yaml")
        except ValueError:
            system = None
    sample = os.path.join(data_dir, "post_process-sample.yaml")
    std = os.path.join(data_dir, "post_process.yaml")
    if os.path.exists(std):
        return std
    elif system and os.path.exists(system):
        # create local config pointing to reduced genomes
        test_system = os.path.join(workdir, os.path.basename(system))
        with open(system) as in_handle:
            config = yaml.load(in_handle)
            config["galaxy_config"] = os.path.join(data_dir, "universe_wsgi.ini")
            with open(test_system, "w") as out_handle:
                yaml.dump(config, out_handle)
        return test_system
    else:
        return sample

class AutomatedAnalysisTest(unittest.TestCase):
    """Setup a full automated analysis and run the pipeline.
    """
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data", "automated")

    def _install_test_files(self, data_dir):
        """Download required sequence and reference files.
        """
        DlInfo = collections.namedtuple("DlInfo", "fname dirname version")
        download_data = [DlInfo("110106_FC70BUKAAXX.tar.gz", None, None),
                         DlInfo("genomes_automated_test.tar.gz", "genomes", 17),
                         DlInfo("110907_ERP000591.tar.gz", None, None),
                         DlInfo("100326_FC6107FAAXX.tar.gz", None, 8),
                         DlInfo("tcga_benchmark.tar.gz", None, 3)]
        for dl in download_data:
            url = "http://chapmanb.s3.amazonaws.com/{fname}".format(fname=dl.fname)
            dirname = os.path.join(data_dir, os.pardir,
                                   dl.fname.replace(".tar.gz", "") if dl.dirname is None
                                   else dl.dirname)
            if os.path.exists(dirname) and dl.version is not None:
                version_file = os.path.join(dirname, "VERSION")
                is_old = True
                if os.path.exists(version_file):
                    with open(version_file) as in_handle:
                        version = int(in_handle.read())
                    is_old = version < dl.version
                if is_old:
                    shutil.rmtree(dirname)
            if not os.path.exists(dirname):
                self._download_to_dir(url, dirname)

    def _download_to_dir(self, url, dirname):
        print dirname
        cl = ["wget", url]
        subprocess.check_call(cl)
        cl = ["tar", "-xzvpf", os.path.basename(url)]
        subprocess.check_call(cl)
        os.rename(os.path.basename(dirname), dirname)
        os.remove(os.path.basename(url))

    @attr(speed=3)
    def IGNOREtest_3_full_pipeline(self):
        """Run full automated analysis pipeline with multiplexing.

        XXX Multiplexing not supporting in latest versions.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "110106_FC70BUKAAXX"),
                  os.path.join(self.data_dir, "run_info.yaml")]
            subprocess.check_call(cl)

    @attr(speed=3)
    def IGNOREtest_4_empty_fastq(self):
        """Handle analysis of empty fastq inputs from failed runs.

        XXX Multiplexing not supporting in latest versions.
        """
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "110221_empty_FC12345AAXX"),
                  os.path.join(self.data_dir, "run_info-empty.yaml")]
            subprocess.check_call(cl)

    @attr(stranded=True)
    @attr(rnaseq=True)
    def test_2_stranded(self):
        """Run an RNA-seq analysis with TopHat and generate gene-level counts.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "test_stranded"),
                  os.path.join(self.data_dir, "run_info-stranded.yaml")]
            subprocess.check_call(cl)

    @attr(rnaseq=True)
    @attr(tophat=True)
    def test_2_rnaseq(self):
        """Run an RNA-seq analysis with TopHat and generate gene-level counts.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "110907_ERP000591"),
                  os.path.join(self.data_dir, "run_info-rnaseq.yaml")]
            subprocess.check_call(cl)

    @attr(fusion=True)
    def test_2_fusion(self):
        """Run an RNA-seq analysis and test fusion genes
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "test_fusion"),
                  os.path.join(self.data_dir, "run_info-fusion.yaml")]
            subprocess.check_call(cl)

    @attr(rnaseq=True)
    @attr(star=True)
    def test_2_star(self):
        """Run an RNA-seq analysis with STAR and generate gene-level counts.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "110907_ERP000591"),
                  os.path.join(self.data_dir, "run_info-star.yaml")]
            subprocess.check_call(cl)

    @attr(explant=True)
    @attr(singleend=True)
    @attr(rnaseq=True)
    def test_explant(self):
        """
        Run an explant RNA-seq analysis with TopHat and generate gene-level counts.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "1_explant"),
                  os.path.join(self.data_dir, "run_info-explant.yaml")]
            subprocess.check_call(cl)

    @attr(chipseq=True)
    def test_chipseq(self):
        """
        Run a chip-seq alignment with Bowtie2
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "test_chipseq"),
                  os.path.join(self.data_dir, "run_info-chipseq.yaml")]
            subprocess.check_call(cl)

    @attr(speed=1)
    @attr(ensemble=True)
    def test_1_variantcall(self):
        """Test variant calling with GATK pipeline.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-variantcall.yaml")]
            subprocess.check_call(cl)

    @attr(speed=1)
    @attr(devel=True)
    def test_5_bam(self):
        """Allow BAM files as input to pipeline.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-bam.yaml")]
            subprocess.check_call(cl)

    @attr(speed=2)
    def test_6_bamclean(self):
        """Clean problem BAM input files that do not require alignment.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-bamclean.yaml")]
            subprocess.check_call(cl)

    @attr(speed=2)
    @attr(cancer=True)
    @attr(cancermulti=True)
    def test_7_cancer(self):
        """Test paired tumor-normal calling using multiple calling approaches: MuTect, VarScan, FreeBayes.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, "run_info-cancer.yaml")]
            subprocess.check_call(cl)

    @attr(cancer=True)
    @attr(cancerpanel=True)
    def test_7_cancer_nonormal(self):
        """Test cancer calling without normal samples or with normal VCF panels.
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py",
                  get_post_process_yaml(self.data_dir, workdir),
                  os.path.join(self.data_dir, "run_info-cancer2.yaml")]
            subprocess.check_call(cl)

    @attr(speed=1)
    @attr(template=True)
    def test_8_template(self):
        """Create a project template from input files and metadata configuration.
        """
        self._install_test_files(self.data_dir)
        fc_dir = os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX")
        with make_workdir() as workdir:
            cl = ["bcbio_nextgen.py", "-w", "template", "freebayes-variant",
                  os.path.join(fc_dir, "100326.csv"),
                  os.path.join(fc_dir, "7_100326_FC6107FAAXX_1_fastq.txt"),
                  os.path.join(fc_dir, "7_100326_FC6107FAAXX_2_fastq.txt"),
                  os.path.join(fc_dir, "8_100326_FC6107FAAXX.bam")]
            subprocess.check_call(cl)

    @attr(docker=True)
    def test_docker(self):
        """Run an analysis with code and tools inside a docker container.

        Requires https://github.com/chapmanb/bcbio-nextgen-vm
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_vm.py", "run",
                  "--systemconfig=%s" % get_post_process_yaml(self.data_dir, workdir),
                  "--fcdir=%s" % os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-bam.yaml")]
            subprocess.check_call(cl)

    @attr(docker_ipython=True)
    def test_docker_ipython(self):
        """Run an analysis with code and tools inside a docker container, driven via IPython.

        Requires https://github.com/chapmanb/bcbio-nextgen-vm
        """
        self._install_test_files(self.data_dir)
        with make_workdir() as workdir:
            cl = ["bcbio_vm.py", "ipython",
                  "--systemconfig=%s" % get_post_process_yaml(self.data_dir, workdir),
                  "--fcdir=%s" % os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-bam.yaml"),
                  "lsf", "localrun"]
            subprocess.check_call(cl)

########NEW FILE########
__FILENAME__ = test_pipeline
"""Test individual components of the analysis pipeline.
"""
import os
import sys
import shutil
import subprocess
import unittest

from nose.plugins.attrib import attr

from bcbio import utils
from bcbio.bam import fastq
from bcbio.distributed import prun
from bcbio.pipeline.config_utils import load_config
from bcbio.provenance import programs
from bcbio.variation import vcfutils

sys.path.append(os.path.dirname(__file__))
from test_automated_analysis import get_post_process_yaml, make_workdir

class RunInfoTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")

    @attr(speed=1)
    @attr(blah=True)
    def test_programs(self):
        """Identify programs and versions used in analysis.
        """
        with make_workdir() as workdir:
            config = load_config(get_post_process_yaml(self.data_dir, workdir))
            print programs._get_versions(config)

class VCFUtilTest(unittest.TestCase):
    """Test various utilities for dealing with VCF files.
    """
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.var_dir = os.path.join(self.data_dir, "variants")
        self.combo_file = os.path.join(self.var_dir, "S1_S2-combined.vcf.gz")

    @attr(speed=1)
    @attr(combo=True)
    def test_1_parallel_vcf_combine(self):
        """Parallel combination of VCF files, split by chromosome.
        """
        files = [os.path.join(self.var_dir, "S1-variants.vcf"), os.path.join(self.var_dir, "S2-variants.vcf")]
        ref_file = os.path.join(self.data_dir, "genomes", "hg19", "seq", "hg19.fa")
        with make_workdir() as workdir:
            config = load_config(get_post_process_yaml(self.data_dir, workdir))
            config["algorithm"] = {}
        region_dir = os.path.join(self.var_dir, "S1_S2-combined-regions")
        if os.path.exists(region_dir):
            shutil.rmtree(region_dir)
        if os.path.exists(self.combo_file):
            os.remove(self.combo_file)
        with prun.start({"type": "local", "cores": 1}, [[config]], config) as run_parallel:
            vcfutils.parallel_combine_variants(files, self.combo_file, ref_file, config, run_parallel)
        for fname in files:
            if os.path.exists(fname + ".gz"):
                subprocess.check_call(["gunzip", fname + ".gz"])
            if os.path.exists(fname + ".gz.tbi"):
                os.remove(fname + ".gz.tbi")

    @attr(speed=1)
    @attr(combo=True)
    def test_2_vcf_exclusion(self):
        """Exclude samples from VCF files.
        """
        ref_file = os.path.join(self.data_dir, "genomes", "hg19", "seq", "hg19.fa")
        with make_workdir() as workdir:
            config = load_config(get_post_process_yaml(self.data_dir, workdir))
            config["algorithm"] = {}
        out_file = utils.append_stem(self.combo_file, "-exclude")
        to_exclude = ["S1"]
        if os.path.exists(out_file):
            os.remove(out_file)
        vcfutils.exclude_samples(self.combo_file, out_file, to_exclude, ref_file, config)

    @attr(speed=1)
    @attr(combo=True)
    def test_3_vcf_split_combine(self):
        """Split a VCF file into SNPs and indels, then combine back together.
        """
        with make_workdir() as workdir:
            config = load_config(get_post_process_yaml(self.data_dir, workdir))
            config["algorithm"] = {}
        ref_file = os.path.join(self.data_dir, "genomes", "hg19", "seq", "hg19.fa")
        fname = os.path.join(self.var_dir, "S1-variants.vcf")
        snp_file, indel_file = vcfutils.split_snps_indels(fname, ref_file, config)
        merge_file = "%s-merge%s.gz" % os.path.splitext(fname)
        vcfutils.combine_variant_files([snp_file, indel_file], merge_file, ref_file,
                                       config)
        for f in [snp_file, indel_file, merge_file]:
            self._remove_vcf(f)

    def _remove_vcf(self, f):
        for ext in ["", ".gz", ".gz.tbi", ".tbi"]:
            if os.path.exists(f + ext):
                os.remove(f + ext)

    @attr(speed=1)
    @attr(combo=True)
    def test_4_vcf_sample_select(self):
        """Select a sample from a VCF file.
        """
        fname = os.path.join(self.var_dir, "S1_S2-combined.vcf.gz")
        out_file = "%s-sampleselect%s" % utils.splitext_plus(fname)
        out_file = vcfutils.select_sample(fname, "S2", out_file, {})
        self._remove_vcf(out_file)

    @attr(speed=1)
    @attr(template=True)
    def test_5_find_fastq_pairs(self):
        """Ensure we can correctly find paired fastq files.
        """
        test_pairs = ["/path/to/input/D1HJVACXX_2_AAGAGATC_1.fastq",
                      "/path/to/input/D1HJVACXX_3_AAGAGATC_1.fastq",
                      "/path/2/input/D1HJVACXX_2_AAGAGATC_2.fastq",
                      "/path/2/input/D1HJVACXX_3_AAGAGATC_2.fastq"]
        out = fastq.combine_pairs(test_pairs)
        assert out[0] == ["/path/to/input/D1HJVACXX_2_AAGAGATC_1.fastq",
                          "/path/2/input/D1HJVACXX_2_AAGAGATC_2.fastq"], out[0]
        assert out[1] == ["/path/to/input/D1HJVACXX_3_AAGAGATC_1.fastq",
                          "/path/2/input/D1HJVACXX_3_AAGAGATC_2.fastq"], out[1]

        test_pairs = ["/path/to/input/Tester_1_fastq.txt",
                      "/path/to/input/Tester_2_fastq.txt"]
        out = fastq.combine_pairs(test_pairs)
        assert out[0] == test_pairs, out[0]

########NEW FILE########
__FILENAME__ = test_SequencingDump
"""Tests associated with detecting sequencing results dumped from a machine.
"""
import os
import unittest

from nose.plugins.attrib import attr
import yaml

try:
    from bcbio.illumina import samplesheet
except ImportError:  # Back compatible, remove after 0.7.9 release
    from bcbio.solexa import samplesheet

class SampleSheetTest(unittest.TestCase):
    """Deal with Illumina SampleSheets and convert to YAML input.
    """
    def setUp(self):
        self.ss_file = os.path.join(os.path.dirname(__file__),
                                    "data", "illumina_samplesheet.csv")

    @attr(speed=1)
    def test_toyaml(self):
        """Convert CSV Illumina SampleSheet to YAML.
        """
        out_file = samplesheet.csv2yaml(self.ss_file)
        assert os.path.exists(out_file)
        with open(out_file) as in_handle:
            info = yaml.load(in_handle)
        assert info[0]['lane'] == '1'
        assert info[0]['multiplex'][0]['barcode_id'] == 5
        os.remove(out_file)

    @attr(speed=1)
    def test_checkforrun(self):
        """Check for the presence of runs in an Illumina SampleSheet.
        """
        fcdir = "fake/101007_80HM7ABXX"
        config = {"samplesheet_directories" : [os.path.dirname(self.ss_file)]}
        ss = samplesheet.run_has_samplesheet(fcdir, config, False)
        assert ss is not None
        fcdir = "fake/101007_NOPEXX"
        ss = samplesheet.run_has_samplesheet(fcdir, config, False)
        assert ss is None

########NEW FILE########
__FILENAME__ = manage_unit_test_data
"""
Manages the unit test data. Run with no arguments it checks to see if
the unit test data is stale and if it is updates it. Can also be used
to upload data to S3.

Note: for some reason the md5 hash for the tarred data directory is always
different, so there is no checking for staleness on upload.

"""

import subprocess
import os
import urllib2
import posixpath
import hashlib
import argparse
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3CreateError


BUCKET = "bcbio_nextgen"
DATA_FILE = "unit_test_data.tar.gz"
DATA_URL = "https://s3.amazonaws.com/" + BUCKET + "/" + DATA_FILE
UNIT_TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def upload_unitdata_to_s3(access_key, secret_key, bucket_name, filename):
    print "Connecting to %s." % (bucket_name)
    conn = S3Connection(access_key, secret_key)
    # make the bucket if it doesn't already exist
    make_bucket(conn, bucket_name)
    bucket = conn.get_bucket(bucket_name)
    print "Uploading %s to %s under key %s." % (filename, bucket_name,
                                                DATA_FILE)
    upload_file_to_bucket(bucket, DATA_FILE, filename)
    # store a md5 sum as a file as well. might be possible to do
    # this with metadata too
    hash_string = md5sum(filename)
    print "Uploading %s as hash of %s under key %s." % (hash_string,
                                                        filename,
                                                        DATA_FILE + ".md5")
    upload_string_to_bucket(bucket, DATA_FILE + ".md5", md5sum(filename))
    print "Done!"


def upload_file_to_bucket(bucket, key_name, filename, public=True):
    k = Key(bucket)
    k.key = key_name
    k.set_contents_from_filename(filename)
    if public:
        k.set_acl('public-read')


def upload_string_to_bucket(bucket, key_name, s, public=True):
    k = Key(bucket)
    k.key = key_name
    k.set_contents_from_string(s)
    if public:
        k.set_acl('public-read')


def make_bucket(conn, bucket_name):
    try:
        bucket = conn.create_bucket(bucket_name)
    # expected if we are not the owner and someone else has made it
    except S3CreateError:
        pass


def tar_data_directory():
    print "Creating archive of unit test data directory."
    unit_test_file = posixpath.basename(DATA_URL)
    if os.path.exists(unit_test_file):
        os.remove(unit_test_file)
    cmd = ["tar", "-czvf", unit_test_file, UNIT_TEST_DATA_DIR]
    subprocess.check_call(cmd)
    return unit_test_file


def md5sum(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.md5(f.read())
    return d.hexdigest()


def needs_update(filename, url):
    return not get_local_hash(filename) == get_remote_hash(url)


def get_local_hash(filename):
    return md5sum(filename)


def get_remote_hash(url):
    response = urllib2.urlopen(url)
    return response.read().strip()


def install_test_files():
    """Download required sequence and reference files.
    """
    local_data_file = posixpath.basename(DATA_URL)
    if os.path.exists(local_data_file):
        if not needs_update(local_data_file, DATA_URL + ".md5"):
            print "Unit test data already up to date."
            exit(1)
        else:
            print "Stale unit test data detected. Grabbing new data."
            os.unlink(local_data_file)

    response = urllib2.urlopen(DATA_URL)
    with open(local_data_file, "wb") as out_handle:
        out_handle.write(response.read())
    subprocess.check_call(["tar", "-zxvf", local_data_file])
    print "Done!"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", help="upload data to S3",
                        action="store_true")
    parser.add_argument("--secret-key", help="secret key for uploading to S3.")
    parser.add_argument("--access-key", help="access key for uploading to S3.")
    args = parser.parse_args()
    if args.upload:
        if not (args.secret_key and args.access_key):
            parser.print_help()
            exit(1)
        else:
            data_file = tar_data_directory()
            upload_unitdata_to_s3(args.access_key, args.secret_key, BUCKET,
                                  data_file)

    else:
        install_test_files()

########NEW FILE########
__FILENAME__ = test_count
import os
import unittest
from bcbio.rnaseq import count
from bcbio.utils import safe_makedir, file_exists
import tempfile
import stat
import shutil


class TestHtseqCount(unittest.TestCase):
    cur_dir = os.path.dirname(__file__)
    organism_dir = os.path.join(cur_dir, "data", "organisms", "mouse")
    data_dir = os.path.join(cur_dir, "data", "count", "test_data")
    correct_dir = os.path.join(cur_dir, "data", "count", "correct")
    out_dir = os.path.join(cur_dir, "htseq-test")

    def setUp(self):
        self.in_bam = os.path.join(self.data_dir, "test.bam")
        self.in_gtf = os.path.join(self.data_dir, "test.gtf")
        self.count_file = os.path.join(self.data_dir, "test.count")
        self.correct_file = os.path.join(self.correct_dir, "correct.count")
        safe_makedir(self.out_dir)


    def test_is_countfile_correct(self):
        test_file = os.path.join(self.data_dir, "test.count")
        self.assertTrue(count.is_countfile(test_file))

    def test_is_countfile_not_correct(self):
        test_file = os.path.join(self.organism_dir, "mouse.gtf")
        self.assertFalse(count.is_countfile(test_file))

    def test_htseq_is_installed_in_path(self):
        self.assertTrue(count._htseq_is_installed({"config": {}}))

    def test_htseq_is_installed_in_resource(self):
        orig_path = os.environ['PATH']
        os.environ['PATH'] = ""
        faux_htseq_count = tempfile.NamedTemporaryFile()
        os.chmod(faux_htseq_count.name, stat.S_IEXEC)
        config = {"config": {"resources": {"htseq-count":
                                           {"cmd": faux_htseq_count.name}}}}
        is_installed = count._htseq_is_installed(config)
        os.environ['PATH'] = orig_path
        self.assertTrue(is_installed)

    def test_htseq_count(self):
        data = {"work_bam": self.in_bam,
                "sam_ref": os.path.join(self.data_dir, "foo"),
                "dirs": {"work": self.out_dir},
                "config": {"algorithm": {"transcripts": self.in_gtf}}}
        out_file = count.htseq_count(data)
        self.assertTrue(file_exists(out_file))

    def tearDown(self):
        shutil.rmtree(self.out_dir)

########NEW FILE########
__FILENAME__ = test_fastq
import unittest
import tempfile
from bcbio.bam.fastq import groom
from bcbio.utils import locate, file_exists
import os
import tempfile


class Fastq(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.join(os.path.dirname(__file__), "data/fastq/")

    def test_groom(self):
        illumina_dir = os.path.join(self.root_dir, "illumina")
        test_data = locate("*.fastq", illumina_dir)
        self.assertTrue(not test_data == [])
        sanger_dir = tempfile.mkdtemp()
        out_files = [groom(x, in_qual="fastq-illumina", out_dir=sanger_dir) for
                     x in test_data]
        self.assertTrue(all(map(file_exists, out_files)))

########NEW FILE########
__FILENAME__ = test_picardrun
import yaml
import unittest
from bcbio.broad.picardrun import bed2interval
from bcbio.utils import replace_suffix
import os
from tempfile import NamedTemporaryFile
import filecmp


class TestBed2interval(unittest.TestCase):

    def setUp(self):
        self.config_file = "data/bed2interval/test_bed2interval.yaml"
        with open(self.config_file) as in_handle:
            self.config = yaml.load(in_handle)
        self.in_file = self.config["input"]
        self.bed = self.config["annotation"]["bed"]
        self.correct_file = self.config["correct"]

    def test_bed2interval(self):
        tmpfile = NamedTemporaryFile()
        out_file = bed2interval(self.in_file, self.bed,
                                out_file=tmpfile.name)
        self.assertTrue(filecmp.cmp(self.correct_file, out_file))

########NEW FILE########
__FILENAME__ = test_trim
from bcbio.bam.trim import trim_read_through
from bcbio.utils import append_stem
import yaml
import unittest
import filecmp
import os
import shutil

CONFIG_FILE = "data/trim_read_through/test_trim_read_through.yaml"
CORRECT_DIR = "data/trim_read_through/correct"


class TestTrimReadThrough(unittest.TestCase):

    def setUp(self):
        with open(CONFIG_FILE) as in_handle:
            self.config = yaml.load(in_handle)
        self.root_work = os.path.dirname(self.config["dir"]["work"])

    def _find_length_filter_correct(self, out_file):
        correct_dir = os.path.join(os.path.dirname(out_file), "correct",
                                   "length_filter")
        correct_file = os.path.join(correct_dir, os.path.basename(out_file))
        return correct_file

    def _trim_single_correct(self, out_file):
        correct_dir = os.path.join(CORRECT_DIR, "trim_single")
        return os.path.join(correct_dir, os.path.basename(out_file))

    def _trim_paired_correct(self, out_file):
        correct_dir = os.path.join(CORRECT_DIR, "trim_paired")
        return os.path.join(correct_dir, os.path.basename(out_file))

    def test_pairedend(self):
        paired = self.config["input_paired"]
        out_files = trim_read_through(paired, self.config["dir"], self.config)
        correct_files = map(self._trim_paired_correct, out_files)
        self.assertTrue(all(map(filecmp.cmp, correct_files, out_files)))
        shutil.rmtree(self.root_work)

    def test_single(self):
        single = self.config["input_single"]
        out_file = trim_read_through(single, self.config["dir"], self.config)
        correct_file = self._trim_single_correct(out_file)
        self.assertTrue(filecmp.cmp(correct_file, out_file))
        shutil.rmtree(self.root_work)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTrimReadThrough)
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = test_utils
import unittest
import tempfile
from bcbio.utils import (transform_to, filter_to, memoize_outfile,
                         replace_suffix, file_exists, append_stem)
from bcbio import utils
import os
import time


class Utils(unittest.TestCase):

    def setUp(self):
        self.out_dir = tempfile.mkdtemp()

    def test_transform_to(self):
        in_file = "test.sam"
        out_file = "test.bam"

        @transform_to(".bam")
        def f(in_file, out_dir=None, out_file=None):
            return out_file

        self.assertTrue(f(in_file) == out_file)
        self.assertTrue(f(in_file, out_dir=self.out_dir) ==
                        os.path.join(self.out_dir, out_file))

    def test_filter_to(self):
        in_file = "test.sam"
        out_file = "test_sorted.sam"

        @filter_to("_sorted")
        def f(in_file, out_dir=None, out_file=None):
            return out_file

        self.assertTrue(f(in_file) == out_file)
        self.assertTrue(f(in_file, out_dir=self.out_dir) ==
                        os.path.join(self.out_dir, out_file))

    def test_memoize_outfile_ext(self):
        temp_file = tempfile.NamedTemporaryFile(dir=self.out_dir,
                                                suffix=".sam")
        ext = ".bam"
        word = __name__

        # test by changing the extension
        @utils.memoize_outfile(ext=ext)
        def f(in_file, word, out_file=None):
            return self._write_word(out_file, word)
        self._run_calls_no_dir(f, temp_file, word)

    def test_memoize_outfile_stem(self):
        temp_file = tempfile.NamedTemporaryFile(dir=self.out_dir,
                                                suffix=".sam")
        stem = "_stem"
        word = __name__

        @utils.memoize_outfile(stem=stem)
        def f(in_file, word, out_file=None):
            return self._write_word(out_file, word)
        self._run_calls_no_dir(f, temp_file, word)

    def test_memoize_outfile_stem_with_dir(self):
        temp_file = tempfile.NamedTemporaryFile(dir=self.out_dir,
                                                suffix=".sam")
        temp_dir = tempfile.mkdtemp()
        stem = "_stem"
        word = __name__

        @utils.memoize_outfile(stem=stem)
        def f(in_file, word, out_dir=None, out_file=None):
            return self._write_word(out_file, word)

        self._run_calls_with_dir(f, temp_file, word, out_dir=temp_dir)

    def test_memoize_outfile_ext_with_dir(self):
        temp_file = tempfile.NamedTemporaryFile(dir=self.out_dir,
                                                suffix=".sam")
        temp_dir = tempfile.mkdtemp()
        ext = ".bam"
        word = __name__

        @utils.memoize_outfile(ext=ext)
        def f(in_file, word, out_dir=None, out_file=None):
            return self._write_word(out_file, word)

        self._run_calls_with_dir(f, temp_file, word, out_dir=temp_dir)

    def test_replace_suffix_of_string(self):
        test_string = "/string/test/foo.txt"
        correct = "/string/test/foo.bar"
        out_string = utils.replace_suffix(test_string, ".bar")
        self.assertEquals(correct, out_string)

    def test_replace_suffix_of_list(self):
        test_list = ["/list/test/foo.txt", "/list/test/foobar.txt"]
        correct = ["/list/test/foo.bar", "/list/test/foobar.bar"]
        out_list = utils.replace_suffix(test_list, ".bar")
        for c, o in zip(correct, out_list):
            self.assertEquals(c, o)

    def test_append_stem_of_string(self):
        test_string = "/string/test/foo.txt"
        correct = "/string/test/foo_bar.txt"
        out_string = utils.append_stem(test_string, "_bar")
        self.assertEquals(correct, out_string)

    def test_append_stem_of_list(self):
        test_list = ["/list/test/foo.txt", "/list/test/foobar.txt"]
        correct = ["/list/test/foo_bar.txt", "/list/test/foobar_bar.txt"]
        out_list = utils.append_stem(test_list, "_bar")
        for c, o in zip(correct, out_list):
            self.assertEquals(c, o)

    def test_replace_directory_of_string(self):
        test_string = "/string/test/foo.txt"
        correct = "/new/dir/foo.txt"
        out_string = utils.replace_directory(test_string, "/new/dir")
        self.assertEquals(correct, out_string)

    def test_replace_directory_of_list(self):
        test_list = ["/list/test/bar.txt", "/list/test/foobar.txt"]
        correct = ["/new/dir/bar.txt", "/new/dir/foobar.txt"]
        out_list = utils.replace_directory(test_list, "/new/dir")
        for c, o in zip(correct, out_list):
            self.assertEquals(c, o)

    def _run_calls_with_dir(self, f, temp_file, word, out_dir=None):
        first_call = f(temp_file.name, word, out_dir=out_dir)
        second_call = f(temp_file.name, word, out_dir=out_dir)
        self.assertTrue(self._read_word(first_call) == word)
        self.assertTrue(self._read_word(second_call) == word)

    def _run_calls_no_dir(self, f, temp_file, word):
        first_call = f(temp_file.name, word)
        second_call = f(temp_file.name, word)
        self.assertTrue(self._read_word(first_call) == word)
        self.assertTrue(self._read_word(second_call) == word)

    def _read_word(self, in_file):
        with open(in_file) as in_handle:
            return in_handle.read()

    def _write_word(self, out_file, word):
        with open(out_file, "w") as out_handle:
            out_handle.write(word)
            out_handle.flush()
        return out_file

########NEW FILE########
