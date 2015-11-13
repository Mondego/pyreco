__FILENAME__ = adaptor_trim
#!/usr/bin/env python
"""Trim adaptor sequences from reads; designed for short read sequencing.

Allows trimming of adaptor sequences from a list of SeqRecords produced
by the Biopython SeqIO library.

This can be imported for use in other scripts, or can be run directly. Running
the script with no arguments will run the tests. Run directly, it will convert a
fastq to a fasta output file, trimming with the passed adaptor:

Usage:

    adaptor_trim.py <in fastq file> <out fastq file> <adaptor seq> <number of errors>

This can filter the trimmed product by minimum and maximum size with --min_size
and --max_size options.
"""
from __future__ import with_statement
import sys
import os
from optparse import OptionParser

from Bio import pairwise2
from Bio.Seq import Seq
from Bio import SeqIO
from Bio.SeqIO.QualityIO import FastqGeneralIterator

def main(in_file, out_file, adaptor_seq, num_errors, min_size=1, max_size=None):
    num_errors = int(num_errors)
    min_size = int(min_size)
    max_size = int(max_size) if max_size else None

    with open(in_file) as in_handle:
        with open(out_file, "w") as out_handle:
            for title, seq, qual in FastqGeneralIterator(in_handle):
                cur_adaptor = (adaptor_seq[:(len(rec) - max_size)] if max_size
                        else adaptor_seq)
                trim = trim_adaptor(seq, cur_adaptor, num_errors)
                cur_max = max_size if max_size else len(seq) - 1
                if len(trim) >= min_size and len(trim) <= cur_max:
                    pos = seq.find(trim)
                    assert pos >= 0
                    trim_qual = qual[pos:pos+len(trim)]
                    out_handle.write("@%s\n%s\n+\n%s\n" % (title, trim,
                        trim_qual))

def _remove_adaptor(seq, region, right_side=True):
    """Remove an adaptor region and all sequence to the right or left.
    """
    # A check for repetitive regions. We handle them below by searching
    # from the left or right depending on the trimming method which should
    # be the expected result.
    #size = len(region)
    #pieces = [str(seq[i:i+size]) for i in range(len(seq) - size)]
    #if pieces.count(region) != 1:
    #    raise ValueError("Non-single match: %s to %s" % (region, seq))
    if right_side:
        try:
            pos = seq.find(region)
        # handle Biopython SeqRecords
        except AttributeError:
            pos = seq.seq.find(region)
        return seq[:pos]
    else:
        try:
            pos = seq.rfind(region)
        # handle Biopython SeqRecords
        except AttributeError:
            pos = seq.seq.rfind(region)
        return seq[pos+len(region):]

def trim_adaptor(seq, adaptor, num_errors, right_side=True):
    """Trim the given adaptor sequence from a starting sequence.

    * seq can be either of:
       - string
       - Biopython SeqRecord
    * adaptor is a string sequence
    * num_errors specifies how many errors are allowed in the match between
    adaptor and the base sequence. Matches with more than this number of errors
    are not allowed.
    """
    gap_char = '-'
    exact_pos = str(seq).find(adaptor)
    if exact_pos >= 0:
        seq_region = str(seq[exact_pos:exact_pos+len(adaptor)])
        adapt_region = adaptor
    else:
        aligns = pairwise2.align.localms(str(seq), str(adaptor),
                5.0, -4.0, -9.0, -0.5, one_alignment_only=True,
                gap_char=gap_char)
        if len(aligns) == 0:
            adapt_region, seq_region = ("", "")
        else:
            seq_a, adaptor_a, score, start, end = aligns[0]
            adapt_region = adaptor_a[start:end]
            #print seq_a, adaptor_a, score, start, end
            seq_region = seq_a[start:end]
    matches = sum((1 if s == adapt_region[i] else 0) for i, s in
            enumerate(seq_region))
    # too many errors -- no trimming
    if (len(adaptor) - matches) > num_errors:
        return seq
    # remove the adaptor sequence and return the result
    else:
        return _remove_adaptor(seq, seq_region.replace(gap_char, ""),
                right_side)

def trim_adaptor_w_qual(seq, qual, adaptor, num_errors, right_side=True):
    """Trim an adaptor with an associated quality string.

    Works like trimmed adaptor, but also trims an associated quality score.
    """
    assert len(seq) == len(qual)
    tseq = trim_adaptor(seq, adaptor, num_errors, right_side=right_side)
    if right_side:
        pos = seq.find(tseq)
    else:
        pos = seq.rfind(tseq)
    tqual = qual[pos:pos+len(tseq)]
    assert len(tseq) == len(tqual)
    return tseq, tqual

# ------- Testing Code
import unittest

from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Alphabet.IUPAC import unambiguous_dna

class AdaptorAlignTrimTest(unittest.TestCase):
    """Test remove adaptor sequences using local alignments.
    """
    def t_1_simple_trim(self):
        """Trim adaptor from non-complex region with errors and deletions.
        """
        adaptor = "GATCGATCGATC"
        tseq = trim_adaptor("GGG" + adaptor + "CCC", adaptor, 2) # exact
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GATCGTTCGATC" + "CCC", adaptor, 2)# 1 error
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GATCGTTCGAAC" + "CCC", adaptor, 2)# 2 errors
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GATCGATCGTC" + "CCC", adaptor, 2) # deletion
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GACGATCGTC" + "CCC", adaptor, 2) # deletion
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GAACGTTGGATC" + "CCC", adaptor, 2)# 3 errors
        assert tseq == "GGGGAACGTTGGATCCCC"
        tseq = trim_adaptor("GGG" + "CATCGGACGTAT" + "CCC", adaptor, 2)# very bad
        assert tseq == "GGGCATCGGACGTATCCC"

    def t_2_alternative_side_trim(self):
        """Trim adaptor from both sides of the sequence.
        """
        adaptor = "GATCGATCGATC"
        tseq = trim_adaptor("GGG" + "GATCGTTCGATC" + "CCC", adaptor, 2)
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GATCGTTCGATC" + "CCC", adaptor, 2, False)
        assert tseq == "CCC"

    def t_3_repetitive_sequence(self):
        """Trim a repetitive adaptor sequence.
        """
        adaptor = "GATCGATC"
        tseq = trim_adaptor("GGG" + "GATCGATCGATC" + "CCC", adaptor, 2)
        assert tseq == "GGG"
        tseq = trim_adaptor("GGG" + "GATCGATCGATC" + "CCC", adaptor, 2, False)
        assert tseq == "CCC"

    def t_4_passing_seqs(self):
        """Handle both Biopython Seq and SeqRecord objects.
        """
        adaptor = "GATCGATCGATC"
        seq = Seq("GGG" + "GATCGTTCGATC" + "CCC", unambiguous_dna)
        tseq = trim_adaptor(seq, adaptor, 2)
        assert isinstance(tseq, Seq)
        assert tseq.alphabet == unambiguous_dna
        tseq = trim_adaptor(seq=seq, adaptor=adaptor, num_errors=2)
        assert isinstance(tseq, Seq)
        assert tseq.alphabet == unambiguous_dna
        trec = trim_adaptor(SeqRecord(seq, "test_id", "test_name", "test_d"),
                adaptor, 2)
        assert isinstance(trec, SeqRecord)
        assert trec.id == "test_id"
        assert str(trec.seq) == "GGG"
        trec = trim_adaptor(SeqRecord(seq, "test_id", "test_name", "test_d"),
                adaptor, 2, False)
        assert isinstance(trec, SeqRecord)
        assert str(trec.seq) == "CCC"

    def t_5_passing_tuple(self):
        """Handle passing a tuple of sequence and quality as input.
        """
        adaptor = "GATCGATCGATC"
        seq = "GGG" + "GATCGTTCGATC" + "CCC"
        qual = "YDV`a`a^[Xa`a`^`_O"
        tseq, tqual = trim_adaptor_w_qual(seq, qual, adaptor, num_errors=2)
        assert tseq == "GGG"
        assert tqual == "YDV"
        tseq, tqual = trim_adaptor_w_qual(seq, qual, adaptor, num_errors=2,
                right_side=False)
        assert tseq == "CCC"
        assert tqual == "`_O"

    def t_6_no_alignment(self):
        """Correctly handle case with no alignment between adaptor and sequence.
        """
        adaptor = "AAAAAAAAAAAAAA"
        to_trim = "TTTTTTTTTTTTTTTTT"
        tseq = trim_adaptor(to_trim, adaptor, 2)
        assert tseq == to_trim

def run_tests(argv):
    test_suite = testing_suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    runner.run(test_suite)

def testing_suite():
    """Generate the suite of tests.
    """
    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 't_'
    tests = [AdaptorAlignTrimTest]
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)
    return test_suite

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-m", "--min_size", dest="min_size", default=1)
    parser.add_option("-x", "--max_size", dest="max_size")
    options, args = parser.parse_args()
    if len(args) == 0:
        sys.exit(run_tests(sys.argv))
    else:
        kwd = dict(min_size = options.min_size,
                   max_size = options.max_size)
        main(*args, **kwd)

########NEW FILE########
__FILENAME__ = Alignments
"""Retrieve regions of alignments and calculate conservation.
"""
import os
import subprocess
import StringIO
import collections

from bx.align import maf
import numpy

from Phast import PhastConsCommandline

class AlignConservationFinder:
    """Provide organism specific statistics on conservation from a alignment.
    """
    def __init__(self, work_dir):
        self._work_dir = work_dir
        self._gap = '-'
        self._base_params = {
            "--target-coverage" : "0.125",
            "--expected-length" : "15",
            }

    def _get_estimate_aligns(self, rec, orgs, chroms, retriever):
        """Retrieve the subset of alignments for use in estimating parameters.
        """
        # 7.8M -> 71m
        # 703M -> 813m
        target_size = 250000 #250kb
        find_size = 1000 # 1kb
        est_aligns = []
        for target_start in range(0, len(rec), target_size):
            aligns = retriever.get_regions(orgs, chroms, target_start, 
                    target_start + find_size, do_slice=False)
            for a in aligns:
                if a not in est_aligns:
                    est_aligns.append(a)
        return est_aligns

    def estimate_phastcons_trees(self, rec, orgs, chroms, retriever, init_model_file):
        """Use a subset of alignments in a sequence to estimate phastCons trees.

        phastCons will estimate conserved and non-conserved tree parameters from
        our full data set. This needs to be done once for each model file, and
        is repeated only when the file is missing.
        """
        base_name = init_model_file.replace("-init.mod", "")
        (base, _) = os.path.splitext(os.path.split(base_name)[-1])
        tree_root = base_name + "-trees"
        cons_tree_file = "%s.cons.mod" % tree_root
        noncons_tree_file = "%s.noncons.mod" % tree_root
        if (not os.path.exists(cons_tree_file) or
                not os.path.exists(noncons_tree_file)):
            aligns = self._get_estimate_aligns(rec, orgs, chroms, retriever)
            estimate_align_file = self._write_maf_file(
                    os.path.join(self._work_dir, "%s-estimate.maf" % base), aligns)
            self._run_phastcons_estimate(estimate_align_file, tree_root,
                    init_model_file)
        return cons_tree_file, noncons_tree_file

    def conservation_stats(self, base_orgs, chroms, align, cons_model,
            noncons_model):
        """Provide conservation statistics for alignments relative to a base.

        base_orgs is a list of synonyms for the organism to be used as a
        base. It is assumed to be present a single time in all alignments.
        """
        base_org, cmp_orgs = self._retrieve_components(base_orgs, chroms, align)
        conserved_file, score_file = self._run_phastcons_conservation(align,
                cons_model, noncons_model)
        c_scores = self._read_conservation_scores(score_file)
        c_regions = self._read_conserved_regions(conserved_file, align)
        assert len(c_scores) == len(base_org.text.replace(self._gap, "")), \
                (len(c_scores), len(base_org.text))
        score_window = 20
        windows = []
        for i in range(max(1, len(c_scores) - score_window)):
            windows.append(numpy.median(c_scores[i:i+score_window]))
        print numpy.median(c_scores), max(windows), c_regions
        for to_remove in [conserved_file, score_file]:
            if os.path.exists(to_remove):
                os.remove(to_remove)
        return numpy.median(c_scores), max(windows), c_regions

    def _read_conserved_regions(self, in_file, align):
        regions = []
        with open(in_file) as in_handle:
            for line in in_handle:
                parts = line.split()
                start = int(parts[1])
                end = int(parts[2])
                slice_c = align.components[0].slice_by_coord(start, end)
                regions.append(slice_c.text.replace(self._gap, '').upper())
        return regions

    def _read_conservation_scores(self, score_file):
        with open(score_file) as in_handle:
            header = in_handle.readline()
            scores = [float(l) for l in in_handle]
        return scores

    def _run_phastcons_estimate(self, align_file, tree_root, init_model_file):
        """Run phastCons, estimating conserved and non-conserved parameters.
        """
        estimate_params = {
            "--msa-format" : "MAF",
            "alignment" : align_file,
            "--estimate-trees" : tree_root,
            "--no-post-probs" : True,
            "models" : init_model_file
            }
        estimate_params.update(self._base_params)
        estimate_cl = PhastConsCommandline(**estimate_params)
        p = subprocess.Popen(str(estimate_cl).split(), stderr=subprocess.PIPE)
        p.wait()
        error_str = p.stderr.read()
        if error_str.find("ERROR") >= 0:
            print error_str
            raise ValueError("Problem running phastCons")

    def _run_phastcons_conservation(self, align, cons_model, non_cons_model):
        """Run phastCons calculating conservation scores
        """
        base_name = os.path.join(self._work_dir, "phastcons-run")
        conserved_file = base_name + "-conserved.bed"
        score_file = base_name + "-scores.bed"
        align_file = self._write_maf_file(base_name + ".maf", [align])
        calcluate_params = {
            "--msa-format" : "MAF",
            "alignment" : align_file,
            "--most-conserved" : conserved_file,
            "models" : "%s,%s" % (cons_model, non_cons_model),
            }
        calcluate_params.update(self._base_params)
       
        calcluate_cl = PhastConsCommandline(**calcluate_params)
        #print calcluate_cl
        error_out = StringIO.StringIO()
        with open(score_file, "w") as score_handle:
            p = subprocess.Popen(str(calcluate_cl).split(), stdout=score_handle,
                    stderr=subprocess.PIPE)
            p.wait()
        error_str = p.stderr.read()
        if error_str.find("ERROR") >= 0:
            print error_str
            raise ValueError("Problem running phastCons")
        for to_remove in [align_file]:
            if os.path.exists(to_remove):
                os.remove(to_remove)
        return conserved_file, score_file

    def _write_maf_file(self, out_file, aligns):
        with open(out_file, "w") as out_handle:
            writer = maf.Writer(out_handle)
            for align in aligns:
                writer.write(align)
        return out_file

    def _retrieve_components(self, base_orgs, chroms, align):
        base_org = None
        cmp_orgs = []
        for c in align.components:
            c_org, c_chrom = c.src.split(".")[:2]
            if c_chrom in chroms:
                if c_org in base_orgs:
                    assert base_org is None
                    base_org = c
                else:
                    cmp_orgs.append(c)
        assert base_org is not None
        return base_org, cmp_orgs

    def _percent_match(self, subs_table):
        """Calculate simple statistics on matches and gaps.
        """
        gap = 0
        match = 0
        mismatch = 0
        for (base_one, base_two), count in subs_table.items():
            if base_one == base_two:
                if base_one != self._gap:
                    match += 1
            elif base_one == self._gap or base_two == self._gap:
                gap += 1
            else:
                mismatch += 1
        total = float(gap + match + mismatch)
        return (float(match) / total, float(gap) / total)

    def _get_substitutions(self, base_org, cmp_org):
        """Retrieve statistics for substitions between the two organisms.
        """
        base_seq = base_org.text.upper()
        cmp_seq = cmp_org.text.upper()
        assert len(base_seq) == len(cmp_seq)
        subs_table = collections.defaultdict(int)
        for i, b_base in enumerate(base_seq):
            c_base = cmp_seq[i]
            subs_table[(b_base, c_base)] += 1
        return dict(subs_table)

class AlignRetriever:
    """Retrieve multiple alignments corresponding to a chromosome segment.

    This uses a bx-python alignment index to retrieve alignment regions
    corresponding to provided coordinates.
    """
    def __init__(self, index):
        self._index = index
        self._gap = '-'

    def get_regions(self, orgs, chroms, start, end, do_slice=True):
        final_aligns = []
        for org in orgs:
            for chrom in chroms:
                region_id = "%s.%s" % (org, chrom)
                aligns = self._index.get(region_id, start, end)
                for align in aligns:
                    region_start, region_end, region_ori = \
                            self._find_region_start(region_id, align)
                    # if our reference strand is reversed, re-orient this
                    # relative to the forward strand
                    if region_ori == "-":
                        align = align.reverse_complement()
                    gap_remap = self._get_gap_remap(region_id, align)
                    # if we are only partially overlapping, we start with our region
                    cur_start = max(start, region_start)
                    rel_start = cur_start - region_start
                    cur_end = min(end, region_end - 1)
                    rel_end = cur_end - region_start
                    if do_slice:
                        align = align.slice(gap_remap[rel_start],
                                gap_remap[rel_end])
                    falign = self._organize_components(orgs, chroms, align)
                    if falign.text_size > 0:
                        final_aligns.append(falign)
        return final_aligns
    
    def _organize_components(self, base_orgs, chroms, align):
        """Separate our base organism and comparisons from the alignment.
        """
        base_org = None
        cmp_orgs = []
        for c in align.components:
            c_org, c_chrom = c.src.split(".")[:2]
            if c_chrom in chroms:
                if c_org in base_orgs:
                    assert base_org is None
                    base_org = c
                else:
                    # remove any all N alignments, which are useless
                    bases = list(set(c.text.replace(self._gap, '').upper()))
                    if not(len(bases) == 1 and bases[0] == 'N'):
                        cmp_orgs.append(c)
        assert base_org is not None
        align.components = [base_org] + cmp_orgs
        align.remove_all_gap_columns()
        return align

    def _get_gap_remap(self, region_id, align):
        for c in align.components:
            if c.src == region_id:
                return self._remap_gaps(0, c.text)

    def _remap_gaps(self, start_index, orig_seq, gap="-"):
        """Generate a dictionary mapping original coordinates to a gapped alignment.
        """
        pos_remap = dict()
        orig_i = start_index
        for align_i, base in enumerate(orig_seq):
            align_i += start_index
            pos_remap[orig_i] = align_i
            if base != "-":
                orig_i += 1
        return pos_remap

    def _find_region_start(self, region_id, align):
        """Find the chromosomal start of the current region in this alignment.

        Assumes 1 region per set of alignments for the organism.
        """
        for c in align.components:
            if c.src == region_id:
                return (c.forward_strand_start, c.forward_strand_end,
                        c.strand)
        raise ValueError("Did not find region in alignment: %s" % region_id)

########NEW FILE########
__FILENAME__ = maf_sort_by_size
#!/usr/bin/env python
"""Sort MAF file by the size of alignments -- largest to smallest.

Usage:
    maf_sort_by_size.py <maf file>
"""
from __future__ import with_statement
import sys
import os

from bx.align import maf
from bx import interval_index_file

def main(in_file):
    base, ext = os.path.splitext(in_file)
    out_file = "%s-sorted%s" % (base, ext)
    index_file = in_file + ".index"
    if not os.path.exists(index_file):
        build_index(in_file, index_file)

    # pull out the sizes and positions of each record
    rec_info = []
    with open(in_file) as in_handle:
        reader = maf.Reader(in_handle)
        while 1:
            pos = reader.file.tell()
            rec = reader.next()
            if rec is None:
                break
            rec_info.append((rec.text_size, pos))
    rec_info.sort(reverse=True)

    # write the records in order, pulling from the index
    index = maf.Indexed(in_file, index_file)
    with open(out_file, "w") as out_handle:
        writer = maf.Writer(out_handle)
        for size, pos in rec_info:
            rec = index.get_at_offset(pos)
            writer.write(rec)

def build_index(in_file, index_file):
    """Build an index of the MAF file for retrieval.
    """
    indexes = interval_index_file.Indexes()
    with open(in_file) as in_handle:
        reader = maf.Reader(in_handle)
        while 1:
            pos = reader.file.tell()
            rec = reader.next()
            if rec is None:
                break
            for c in rec.components:
                indexes.add(c.src, c.forward_strand_start,
                        c.forward_strand_end, pos, max=c.src_size )

    with open(index_file, "w") as index_handle:
        indexes.write(index_handle)

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = Phast
"""Wrappers for PHAST applications: conservation, alignments and phylogeny.

http://compgen.bscb.cornell.edu/phast/
"""
import types

from Bio.Application import _Option, _Argument, _Switch, AbstractCommandline

class PhastConsCommandline(AbstractCommandline):
    def __init__(self, cmd="phastCons", **kwargs):
        self.parameters = [
            _Argument(["alignment"], ["input"],
                    None, True, ""),
            _Argument(["models"], ["input"],
                    None, True, ""),
            _Option(["--target-coverage"], ["input"],
                    None, False, "", False),
            _Option(["--expected-length"], ["input"],
                    None, False, "", False),
            _Option(["--rho"], ["input"],
                    None, False, "", False),
            _Option(["--msa-format"], ["input"],
                    None, False, "", False),
            _Option(["--estimate-trees"], ["input"],
                    None, False, "", False),
            _Switch(["--no-post-probs"], ["input"]),
            _Option(["--most-conserved"], ["input"],
                    None, False, "", False),
            _Option(["--estimate-rho"], ["input"],
                    None, False, "", False),
            ]
        AbstractCommandline.__init__(self, cmd, **kwargs)

########NEW FILE########
__FILENAME__ = CodingRegion
"""Represent coding regions, initially for defining changes due to SNPs.
"""
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Alphabet.IUPAC import unambiguous_dna
from Bio.Data import CodonTable

class NonCodingRegion:
    """Represent a standard region of a chromosome or segment, without coding.
    """
    def __init__(self, full_seq, region_name):
        self._seq = full_seq
        self._name = region_name
        self.is_rc = False

    def __str__(self):
        return "Non-coding region: %s" % self._name

    def get_ref_name(self):
        return self._name

    def is_coding(self):
        return False

    def get_feature_details(self):
        return ("", "", "")

    def snp_surround(self, targets, bp_surround):
        """Retrieve the region surrounding a set of SNP targets.
        """
        target_positions = [t['pos'] for t in targets]
        r_start = max(min(target_positions) - bp_surround, 0)
        r_end = min(max(target_positions) + bp_surround, len(self._seq))
        seq_region = self._seq[r_start:r_end]
        targets = [self._add_surround_info(t, r_start) for t in targets]
        return seq_region, targets

    def _add_surround_info(self, snp, region_start):
        """Add local mapping of a SNP to our surrounding alignment region.
        """
        snp["surround_pos"] = snp["pos"] - region_start
        return snp

class CodingRegion:
    """Represent a coding region, providing remapping of coordinates.
    """
    def __init__(self, full_seq, coding_db):
        """Initialize with a sequence and coding database object.
        """
        self._coding_db = coding_db
        table_name = self._coding_db.get("table", "Standard")
        self._surround = 250 #bp
        self._gap = '-'
        if isinstance(full_seq, SeqRecord):
            full_seq = str(full_seq.seq)
        elif isinstance(full_seq, Seq):
            full_seq = str(full_seq)
        self.is_rc = (coding_db['strand'] == -1)
        self._cds_table = CodonTable.unambiguous_dna_by_name[table_name]
        self._local_seq, self._remap, self._upstream, self._downstream = \
                self._build_local_seq(full_seq, coding_db['location'],
                                      coding_db['strand'])
        if coding_db["coding"]:
            self._codons, self._aa_seq = self._build_aa(self._local_seq,
                    self._cds_table, table_name)
        else:
            self._codons = []
            self._aa_seq = ""
        if len(self._codons) == 0:
            self._non_coding_region = NonCodingRegion(full_seq,
                    coding_db["ref_name"])
            self.is_rc = False

    def __str__(self):
        return "%s %s\n\tCoding region: %s" % (self._coding_db["_id"],
                self._coding_db["name"], self._coding_db["location"])
    
    def get_feature_details(self):
        loc_string = ";".join(["%s-%s" % (s, e) for (s, e) in
                               self._coding_db["location"]])
        return (self._coding_db["_id"], self._coding_db["name"], loc_string)

    def get_ref_name(self):
        return self._coding_db["ref_name"]

    def _build_aa(self, seq, cds_table, table_name):
        """Translate our coding sequencing into codons and amino acids.
        """
        if len(self._local_seq) % 3 != 0:
            return ([], "")
        assert seq[:3] in cds_table.start_codons
        aa_seq = str(Seq(seq, unambiguous_dna).translate(table=table_name))
        if (aa_seq.count('*') != 1 or aa_seq[-1] != '*'):
            return ([], "")
        codons = [seq[i*3:(i+1)*3] for i in range(len(seq) // 3)]
        return codons, aa_seq

    def _build_local_seq(self, seq, loc, strand):
        """Generate a local coding sequence with a map of original coordinates.
        """
        remap = {}
        seq_parts = []
        cur_pos = 0
        loc.sort()
        # if we are reverse complemented, add the parts backwards for
        # correct remapping
        if strand == -1:
            loc.reverse()
        for start, end in loc:
            seq_parts.append(seq[start:end])
            cur_region = range(start, end)
            for i, region in enumerate(cur_region):
                if strand == -1:
                    remap[region] = len(cur_region) - 1 - i + cur_pos
                else:
                    remap[region] = i + cur_pos
            cur_pos += len(cur_region)
        if strand == -1:
            seq_parts.reverse()
        lseq = "".join(seq_parts)
        
        upstream = seq[max(loc[0][0] - self._surround, 0):loc[0][0]]
        downstream = seq[loc[-1][1]:min(loc[-1][1] + self._surround, len(seq))]
        if strand == -1:
            lseq = str(Seq(lseq, unambiguous_dna).reverse_complement())
            upstream = str(Seq(downstream,
                unambiguous_dna).reverse_complement())
            downstream = str(Seq(upstream,
                unambiguous_dna).reverse_complement())
        return lseq, remap, upstream, downstream

    def snp_surround(self, targets, bp_surround):
        """Retrieve the codons surrounding a list of target regions.

        This also includes an extra 5' or 3' "codon" with sequence if
        the start or end abuts the end of the sequence.
        """
        # handle special case where we are labelled as coding but really
        # a frameshift or some other non-parseable coding region
        if not self.is_coding():
            return self._non_coding_region.snp_surround(targets, bp_surround)

        targets = [self._add_local_info(t) for t in targets]
        target_positions = [t['codon_pos'] for t in targets]
        num_surround = bp_surround // 3
        up_extra, down_extra = (None, None)
        r_start = min(target_positions) - num_surround
        if r_start < 0:
            up_extra = self._upstream[r_start*3:]
            r_start = 0
        r_end = max(target_positions) + num_surround
        if r_end > len(self._codons):
            down_extra = self._downstream[:(r_end - len(self._codons))*3]
            r_end = len(self._codons)
        codons = self._codons[r_start:r_end]
        target_indexes = [t - r_start for t in target_positions]
        if up_extra:
            up_fake_codons = [up_extra[i*3:(i+1)*3] for 
                    i in range(len(up_extra) // 3)]
            codons = up_fake_codons + codons
            target_indexes = [i + len(up_fake_codons) for i in target_indexes]
        if down_extra:
            codons.insert(-1, down_extra)
        targets = [self._add_surround_info(t, target_indexes[i]) for i, t in
                enumerate(targets)]
        return "".join(codons), targets

    def is_coding(self):
        return len(self._codons) > 0

    def _add_surround_info(self, target, index_pos):
        """Convert a codon index position in a surround region into a position.
        """
        target["surround_pos"] = (index_pos * 3) + target["in_codon_pos"]
        return target

    def _add_local_info(self, snp_info):
        """Add info to a SNP about its position within this coding region.
        """
        local_pos = self._remap[snp_info['pos']]
        ori_base = snp_info['ref_base']
        new_base = snp_info['snp_base']
        if self.is_rc:
            ori_base = str(Seq(ori_base, unambiguous_dna).reverse_complement())
            new_base = str(Seq(new_base, unambiguous_dna).reverse_complement())
        snp_info['codon_pos'] = local_pos // 3
        snp_info['in_codon_pos'] = local_pos % 3
        orig_codon = self._codons[snp_info['codon_pos']]
        mod_codon = list(orig_codon)
        # substitution or deletion
        if ori_base != self._gap:
            assert self._local_seq[local_pos] == ori_base, (
                    self._local_seq[local_pos], ori_base)
            assert orig_codon[snp_info['in_codon_pos']] == ori_base
            mod_codon[snp_info['in_codon_pos']] = new_base
        # insertion
        else:
            codon_pos = snp_info['in_codon_pos']
            mod_codon = mod_codon[:codon_pos] + [new_base] + \
                    mod_codon[codon_pos:]
        mod_codon = "".join(mod_codon)
        snp_info['orig_codon'] = orig_codon
        snp_info['new_codon'] = mod_codon
        return snp_info

    def get_aa(self, codon):
        return ("*" if codon in self._cds_table.stop_codons else
                self._cds_table.forward_table[codon])


########NEW FILE########
__FILENAME__ = glimmergff_to_proteins
#!/usr/bin/env python
"""Convert GlimmerHMM GFF3 gene predictions into protein sequences.

This works with the GlimmerHMM GFF3 output format:

##gff-version 3
##sequence-region Contig5.15 1 47390
Contig5.15      GlimmerHMM      mRNA    323     325     .       +       .       ID=Contig5.15.path1.gene1;Name=Contig5.15.path1.gene1
Contig5.15      GlimmerHMM      CDS     323     325     .       +       0       ID=Contig5.15.cds1.1;Parent=Contig5.15.path1.gene1;Name=Contig5.15.path1.gene1;Note=final-exon

http://www.cbcb.umd.edu/software/GlimmerHMM/

Usage:
    glimmergff_to_proteins.py <glimmer gff3> <ref fasta>
"""
from __future__ import with_statement
import sys
import os
import operator

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

from BCBio import GFF

def main(glimmer_file, ref_file):
    with open(ref_file) as in_handle:
        ref_recs = SeqIO.to_dict(SeqIO.parse(in_handle, "fasta"))

    base, ext = os.path.splitext(glimmer_file)
    out_file = "%s-proteins.fa" % base
    with open(out_file, "w") as out_handle:
        SeqIO.write(protein_recs(glimmer_file, ref_recs), out_handle, "fasta")

def protein_recs(glimmer_file, ref_recs):
    """Generate protein records from GlimmerHMM gene predictions.
    """
    with open(glimmer_file) as in_handle:
        for rec in glimmer_predictions(in_handle, ref_recs):
            for feature in rec.features:
                seq_exons = []
                for cds in feature.sub_features:
                    seq_exons.append(rec.seq[
                        cds.location.nofuzzy_start:
                        cds.location.nofuzzy_end])
                gene_seq = reduce(operator.add, seq_exons)
                if feature.strand == -1:
                    gene_seq = gene_seq.reverse_complement()
                protein_seq = gene_seq.translate()
                yield SeqRecord(protein_seq, feature.qualifiers["ID"][0], "", "")

def glimmer_predictions(in_handle, ref_recs):
    """Parse Glimmer output, generating SeqRecord and SeqFeatures for predictions
    """
    for rec in GFF.parse(in_handle, target_lines=1000, base_dict=ref_recs):
        yield rec

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print __doc__
        sys.exit()
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = glimmer_to_proteins
#!/usr/bin/env python
"""Convert GlimmerHMM gene predictions into protein sequences.

This works with the GlimmerHMM specific output format:

  12    1  +  Initial       10748      10762       15
  12    2  +  Internal      10940      10971       32
  12    3  +  Internal      11035      11039        5
  12    4  +  Internal      11072      11110       39
  12    5  +  Internal      11146      11221       76
  12    6  +  Terminal      11265      11388      124

http://www.cbcb.umd.edu/software/GlimmerHMM/

Usage:
    glimmer_to_proteins.py <glimmer output> <ref fasta>
"""
from __future__ import with_statement
import sys
import os
import operator

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

def main(glimmer_file, ref_file):
    with open(ref_file) as in_handle:
        ref_rec = SeqIO.read(in_handle, "fasta")

    base, ext = os.path.splitext(glimmer_file)
    out_file = "%s-proteins.fa" % base
    with open(out_file, "w") as out_handle:
        SeqIO.write(protein_recs(glimmer_file, ref_rec), out_handle, "fasta")

def protein_recs(glimmer_file, ref_rec):
    """Generate protein records
    """
    with open(glimmer_file) as in_handle:
        for gene_num, exons, strand in glimmer_predictions(in_handle):
            seq_exons = []
            for start, end in exons:
                seq_exons.append(ref_rec.seq[start:end])
            gene_seq = reduce(operator.add, seq_exons)
            if strand == '-':
                gene_seq = gene_seq.reverse_complement()
            protein_seq = gene_seq.translate()
            yield SeqRecord(protein_seq, gene_num, "", "")

def glimmer_predictions(in_handle):
    """Parse Glimmer output, generating a exons and strand for each prediction.
    """
    # read the header
    while 1:
        line = in_handle.readline()
        if line.startswith("   #    #"):
            break
    in_handle.readline()
    # read gene predictions one at a time
    cur_exons, cur_gene_num, cur_strand = ([], None, None)
    while 1:
        line = in_handle.readline()
        if not line:
            break
        parts = line.strip().split()
        # new exon
        if len(parts) == 0:
            yield cur_gene_num, cur_exons, cur_strand
            cur_exons, cur_gene_num, cur_strand = ([], None, None)
        else:
            this_gene_num = parts[0]
            this_strand = parts[2]
            this_start = int(parts[4]) - 1 # 1 based
            this_end = int(parts[5])
            if cur_gene_num is None:
                cur_gene_num = this_gene_num
                cur_strand = this_strand
            else:
                assert cur_gene_num == this_gene_num
                assert cur_strand == this_strand
            cur_exons.append((this_start, this_end))
    if len(cur_exons) > 0:
        yield cur_gene_num, cur_exons, cur_strand

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print __doc__
        sys.exit()
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = BioSQL-SQLAlchemy_definitions
"""SQLAlchemy definitions for the BioSQL database of biological items.

This provides a non-Seq-based interface to the BioSQL database through python.
This is useful if you have non-seq items to put into BioSQL, and should also
expose things not touched on with the Biopython BioSQL interface. Eventually
this would be a good target for merging.

http://www.biosql.org/wiki/Main_Page

Useful URLs for declarative style:
    https://www.bitbucket.org/stephane/model2/src/tip/transifex/model.py
    http://www.sqlalchemy.org/docs/05/sqlalchemy_ext_declarative.html
"""

def _initialize(Base):
    from sqlalchemy.orm import relation, mapper, dynamic_loader
    from sqlalchemy import MetaData, Table, Column, ForeignKey, Sequence
    from sqlalchemy import String, Unicode, Integer, DateTime, Float
    
    # -- Standard BioSQL tables
    
    class Biodatabase(Base):
        """Entry point to BioSQL databases.
        """
        __tablename__ = 'biodatabase'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        biodatabase_id = Column(Integer, primary_key = True)
        entries = relation("Bioentry", backref = "biodb")

    class Bioentry(Base):
        """The main bioentry object in BioSQL, containing a biological item.
        """
        __tablename__ = 'bioentry'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        bioentry_id = Column(Integer, primary_key = True)
        biodatabase_id = Column(Integer,
                ForeignKey('biodatabase.biodatabase_id'))
        qualifiers = relation("BioentryQualifierValue", backref = "bioentry")
        parent_maps = relation("BioentryRelationship", primaryjoin =
          "Bioentry.bioentry_id == BioentryRelationship.object_bioentry_id",
          lazy="dynamic")
        child_maps = relation("BioentryRelationship", primaryjoin =
          "Bioentry.bioentry_id == BioentryRelationship.subject_bioentry_id",
          order_by = "BioentryRelationship.object_bioentry_id.asc()",
          lazy="dynamic")
        features = relation("SeqFeature", backref="bioentry")
        sequence = relation("Biosequence")

    class Biosequence(Base):
        """Represent a sequence attached to a bioentry.
        """
        __tablename__ = 'biosequence'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        bioentry_id = Column(Integer, ForeignKey('bioentry.bioentry_id'),
                primary_key = True)
    
    class Ontology(Base):
        """Defined a high level dictionary of ontology key terms.
        """
        __tablename__ = 'ontology'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        ontology_id = Column(Integer, primary_key = True)
    
    class Term(Base):
        """Explicitly describe terminology used in key/value pair relationships
        """
        __tablename__ = 'term'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        term_id = Column(Integer, primary_key = True)
        ontology_id = Column(Integer, ForeignKey('ontology.ontology_id'))
        ontology = relation("Ontology", backref = "terms")

    class BioentryQualifierValue(Base):
        """A key/value annotation pair associated with a Bioentry.
        """
        __tablename__ = 'bioentry_qualifier_value'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        bioentry_id = Column(Integer,
                ForeignKey('bioentry.bioentry_id'), primary_key = True)
        term_id = Column(Integer, ForeignKey('term.term_id'), primary_key = True)
        rank = Column(Integer, primary_key = True)
        term = relation("Term", lazy=True)

    class BioentryRelationship(Base):
        """Define a relationship between two bioentry objects.
        """
        __tablename__ = 'bioentry_relationship'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        object_bioentry_id = Column(Integer,
                ForeignKey('bioentry.bioentry_id'), primary_key = True)
        subject_bioentry_id = Column(Integer, 
                ForeignKey('bioentry.bioentry_id'))
        term_id = Column(Integer, ForeignKey('term.term_id'),
                primary_key = True)
        rank = Column(Integer, primary_key = True)
        
        term = relation("Term")
        parent = relation("Bioentry", primaryjoin = 
          "Bioentry.bioentry_id == BioentryRelationship.object_bioentry_id")
        child = relation("Bioentry", primaryjoin =
          "Bioentry.bioentry_id == BioentryRelationship.subject_bioentry_id")

    seqfeature_dbxref_table = Table('seqfeature_dbxref', Base.metadata,
            Column('seqfeature_id', Integer, 
                ForeignKey('seqfeature.seqfeature_id')),
            Column('dbxref_id', Integer, ForeignKey('dbxref.dbxref_id')),
            Column('rank', Integer))
    
    class DBXref(Base):
        """Database cross reference.
        """
        __tablename__ = 'dbxref'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        dbxref_id = Column(Integer, primary_key = True)
    
    class SeqFeature(Base):
        """Provide a feature connected to a bioentry.
        """
        __tablename__ = 'seqfeature'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        seqfeature_id = Column(Integer, primary_key = True)
        bioentry_id = Column(Integer, ForeignKey('bioentry.bioentry_id'))
        type_term_id = Column(Integer, ForeignKey('term.term_id'))
        source_term_id = Column(Integer, ForeignKey('term.term_id'))
        type_term = relation("Term", primaryjoin =
            "SeqFeature.type_term_id == Term.term_id")
        source_term = relation("Term", primaryjoin =
            "SeqFeature.source_term_id == Term.term_id")
        qualifiers = relation("SeqFeatureQualifierValue")
        locations = relation("Location")
        dbxrefs = relation("DBXref", secondary=seqfeature_dbxref_table,
                order_by=seqfeature_dbxref_table.columns.rank)

    class SeqFeatureQualifierValue(Base):
        """A key/value annotation pair associated with a SeqFeature.
        """
        __tablename__ = 'seqfeature_qualifier_value'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        seqfeature_id = Column(Integer,
                ForeignKey('seqfeature.seqfeature_id'), primary_key = True)
        term_id = Column(Integer, ForeignKey('term.term_id'),
                primary_key = True)
        rank = Column(Integer, primary_key = True)
        term = relation("Term", lazy=True)
        
    class Location(Base):
        """Describe a location on a biological sequence.
        """
        __tablename__ = 'location'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        location_id = Column(Integer, primary_key = True)
        seqfeature_id = Column(Integer, ForeignKey('seqfeature.seqfeature_id'))
        dbxref_id = Column(Integer, ForeignKey('dbxref.dbxref_id'))
        qualifiers = relation("LocationQualifierValue")
        dbxref = relation("DBXref")
    
    class LocationQualifierValue(Base):
        """A key/value annotation pair associated with a Location.
        """
        __tablename__ = 'location_qualifier_value'
        __table_args__ = {'mysql_engine':'InnoDB', 'autoload' : True}
        location_id = Column(Integer,
                ForeignKey('location.location_id'), primary_key = True)
        term_id = Column(Integer, ForeignKey('term.term_id'),
                primary_key = True)
        rank = Column(Integer, primary_key = True)
        term = relation("Term", lazy=True)

    # ugly assignment of classes to the top level for use
    globals()['Biodatabase'] = Biodatabase
    globals()['Bioentry'] = Bioentry
    globals()['Biosequence'] = Biosequence
    globals()['BioentryQualifierValue'] = BioentryQualifierValue
    globals()['Ontology'] = Ontology
    globals()['Term'] = Term
    globals()['BioentryRelationship'] = BioentryRelationship
    globals()['SeqFeatureQualifierValue'] = SeqFeatureQualifierValue
    globals()['SeqFeature'] = SeqFeature
    globals()['DBXref'] = DBXref
    globals()['LocationQualifierValue'] = LocationQualifierValue
    globals()['Location'] = Location

########NEW FILE########
__FILENAME__ = genbank_to_ontology
"""Provide a (semi) automated mapping between GenBank and ontologies.

The goal is to provide an ontology namespace and term for each item
of a standard GenBank file.
"""
from __future__ import with_statement
import os
import collections
import csv

from rdflib.Graph import Graph
#from Mgh.SemanticLiterature import sparta
import sparta

def main(ft_file, so_ft_map_file, so_file, dc_file, rdfs_file):
    # -- get all of the keys we need to map from GenBank
    # pulled by hand from the Biopython parser
    header_keys = ['ACCESSION', 'AUTHORS', 'COMMENT', 'CONSRTM', 'DBLINK',
            'DBSOURCE', 'DEFINITION', 'JOURNAL', 'KEYWORDS', 'MEDLINE', 'NID',
            'ORGANISM', 'PID', 'PROJECT', 'PUBMED',
            'REMARK', 'SEGMENT', 'SOURCE', 'TITLE', 'VERSION',
            'VERSION;gi', 'LOCUS;date']
    feature_keys, qual_keys = parse_feature_table(ft_file)

    # -- terms to map them two, along with dictionaries for the existing or
    # hand defined mappings
    dc_terms = parse_dc_terms(dc_file)
    dc_ontology = OntologyGroup("http://purl.org/dc/terms/", dc_terms)
    so_terms = parse_so_terms(so_file)
    so_ontology = OntologyGroup("http://purl.org/obo/owl/SO", so_terms)
    so_ft_map = parse_so_ft_map(so_ft_map_file)
    so_ontology.add_map('feature', 
            'http://www.sequenceontology.org/mappings/FT_SO_map.txt', so_ft_map)
    rdfs_terms = parse_rdfs_terms(rdfs_file)
    rdfs_ontology = OntologyGroup('http://www.w3.org/2000/01/rdf-schema#',
            rdfs_terms)
    me_ft_map = dict(
            rep_origin = 'origin_of_replication',
            unsure = 'sequence_uncertainty',
            conflict = 'sequence_conflict',
            GC_signal = 'GC_rich_promoter_region',
            mat_peptide = 'mature_protein_region',
            C_region = 'C_cluster',
            J_segment = 'J_gene',
            N_region = '',
            S_region = '',
            V_region = 'V_cluster',
            V_segment = 'V_gene'
            )
    me_ft_dc_map = dict(
            old_sequence = 'replaces')
    me_hd_map = {'ACCESSION': 'databank_entry'}
    me_hd_dc_map = {'DEFINITION' : 'description',
                    'VERSION' : 'hasVersion',
                    'VERSION;gi' : 'identifier',
                    'KEYWORDS' : 'subject',
                    'LOCUS;date' : 'created',
                    'PUBMED' : 'relation',
                    'JOURNAL' : 'source',
                    'AUTHORS' : 'contributor',
                    'CONSRTM' : 'creator',
                    'ORGANISM' : '',
                    'SEGMENT' : 'isPartOf',
                    'DBLINK' : 'relation',
                    'DBSOURCE' : 'relation',
                    'MEDLINE' : 'relation',
                    'NID' : 'relation',
                    'PID' : 'relation',
                    'PROJECT' : 'relation'}
    me_ql_map = dict(
            bio_material = 'biomaterial_region',
            bound_moiety = 'bound_by_factor',
            codon_start = 'coding_start',
            direction = 'direction_attribute',
            experiment = 'experimental_result_region',
            macronuclear = 'macronuclear_sequence',
            map = 'fragment_assembly',
            mobile_element = 'integrated_mobile_genetic_element',
            mod_base = 'modified_base_site',
            mol_type = 'sequence_attribute',
            ncRNA_class = 'ncRNA',
            organelle = 'organelle_sequence',
            PCR_primers = 'primer',
            proviral = 'proviral_region',
            pseudo = 'pseudogene',
            rearranged = 'rearranged_at_DNA_level',
            satellite = 'satellite_DNA',
            segment = 'gene_segment',
            rpt_family = 'repeat_family',
            rpt_type = 'repeat_unit',
            rpt_unit_range = 'repeat_region',
            rpt_unit_seq = 'repeat_component',
            tag_peptide = 'cleaved_peptide_region',
            trans_splicing = 'trans_spliced',
            translation = 'polypeptide',
            )
    me_ql_dc_map = dict(
            citation = 'bibliographicCitation',
            gene_synonym = 'alternative',
            identified_by = 'creator',
            label = 'alternative',
            locus_tag = 'alternative',
            old_locus_tag = 'replaces',
            replace = 'isReplacedBy',
            db_xref = 'relation',
            compare = 'relation',
            EC_number = 'relation',
            protein_id = 'relation',
            product = 'alternative',
            standard_name = 'alternative',
            number = 'coverage',
            function = 'description',
            )
    me_ql_rdfs_map = dict(
            note = 'comment',
            )
    ql_make_no_sense_list = ['number']
    so_ontology.add_map('header', 'Brad', me_hd_map)
    so_ontology.add_map('feature', 'Brad', me_ft_map)
    so_ontology.add_map('qualifier', 'Brad', me_ql_map)
    dc_ontology.add_map('header', 'Brad', me_hd_dc_map)
    dc_ontology.add_map('feature', 'Brad', me_ft_dc_map)
    dc_ontology.add_map('qualifier', 'Brad', me_ql_dc_map)
    rdfs_ontology.add_map('qualifier', 'Brad', me_ql_rdfs_map)

    # -- write out the mappings in each of the categories
    with open("genbank_ontology_map.txt", "w") as out_handle:
        out_writer = csv.writer(out_handle, delimiter="\t")
        out_writer.writerow(['gb section', 'identifier', 'ontology',
            'namespace', 'evidence'])
        match_keys_to_ontology('header', header_keys, [so_ontology, dc_ontology,
            rdfs_ontology], out_writer)
        match_keys_to_ontology('feature', feature_keys, [so_ontology,
            dc_ontology, rdfs_ontology], out_writer)
        match_keys_to_ontology('qualifier', qual_keys, [so_ontology,
            dc_ontology, rdfs_ontology], out_writer)

class OntologyGroup:
    def __init__(self, namespace, terms):
        self.ns = namespace
        self.terms = terms
        self._maps = collections.defaultdict(lambda: [])

    def add_map(self, key_type, origin, key_map):
        """Add a mapping of keys to terms within this ontology.
        """
        self._maps[key_type].append((origin, key_map))

    def normalized_terms(self):
        """Retrieve the terms all lower cased and with extra items removed.
        """
        lower_so_terms = {}
        for term in self.terms:
            lower_so_terms[self._normal_term(term)] = term
        return lower_so_terms

    def _normal_term(self, term):
        return term.replace("_", "").lower() 

    def match_key_to_ontology(self, key_type, cur_key):
        normal_terms = self.normalized_terms()
        # try to get it from a dictionary
        for map_origin, check_map in self._maps[key_type]:
            try:
                match_key = check_map[cur_key]
            except KeyError:
                match_key = None
            if (match_key and
                    self._normal_term(match_key) in normal_terms.keys()):
                return match_key, map_origin
        # try to match it by name
        if self._normal_term(cur_key) in normal_terms.keys():
            match_key = normal_terms[self._normal_term(cur_key)]
            return match_key, 'name_match'
        #in_terms = [x for x in normal_terms.keys() if
        #        x.find(self._normal_term(cur_key)) != -1]
        #if len(in_terms) > 0:
        #    print '***', cur_key, in_terms, self.ns
        # could not find a match
        return None, ''

def match_keys_to_ontology(key_type, keys, ontologies, out_writer):
    no_matches = []
    for cur_key in keys:
        found_match = False
        for ontology in ontologies:
            match_key, origin = ontology.match_key_to_ontology(key_type, cur_key)
            if match_key is not None:
                out_writer.writerow([key_type, cur_key, match_key, ontology.ns,
                    origin])
                found_match = True
                break
        if not found_match:
            no_matches.append(cur_key)
    for no_key in no_matches:
        out_writer.writerow([key_type, no_key])

def _parse_terms_from_rdf(in_file, prefix):
    graph = Graph()
    graph.parse(in_file)
    sparta_store = sparta.ThingFactory(graph)
    subjects = []
    for subj in graph.subjects():
        if subj not in subjects:
            subjects.append(subj)
    terms = []
    for subj in subjects:
        rdf_item = sparta_store(subj)
        str_item = str(rdf_item.get_id().replace(prefix + "_", ""))
        if str_item:
            terms.append(str_item)
    terms.sort()
    #print terms
    return terms

def parse_rdfs_terms(rdfs_file):
    return _parse_terms_from_rdf(rdfs_file, "rdfs")

def parse_dc_terms(dc_file):
    """Retrieve a list of Dublin core terms from the RDF file.
    """
    return _parse_terms_from_rdf(dc_file, "dcterms")

def parse_so_terms(so_file):
    """Retrieve all available Sequence Ontology terms from the file.
    """
    so_terms = []
    with open(so_file) as in_handle:
        for line in in_handle:
            if line.find('name:') == 0:
                name = line[5:].strip()
                so_terms.append(name)
    return so_terms

def parse_so_ft_map(so_ft_map_file):
    """Parse out mappings between feature keys and SO.
    """
    so_ft_map = {}
    with open(so_ft_map_file) as in_handle:
        in_handle.readline()
        for line in in_handle:
            parts = line.split()
            if parts[1] not in ['undefined']:
                so_ft_map[parts[0]] = parts[1]
    return so_ft_map

def parse_feature_table(ft_file):
    """Parse all available features and qualifiers from the FT definition.

    This is ugly and parses it straight out of the HTML but this is much easier
    than trying to get it from the specs.
    """
    feature_keys = []
    qual_keys = []
    with open(ft_file) as ft_handle:
        in_feature_region = False
        for line in ft_handle:
            if in_feature_region:
                if line.strip() == "":
                    in_feature_region = False
                else:
                    qual_key, feature_key = line.strip().split()
                    qual_keys.append(qual_key)
                    feature_keys.append(feature_key)
            elif line.find('QUALIFIER FEATURE KEY') == 0:
                in_feature_region = True
    qual_keys = list(set(qual_keys))
    qual_keys = [k.replace('/', '') for k in qual_keys]
    feature_keys = list(set(feature_keys))
    qual_keys.sort()
    feature_keys.sort()
    return feature_keys, qual_keys

if __name__ == "__main__":
    ft_file = os.path.join("feature_table", "FT_index.html")
    so_ft_map_file = os.path.join("feature_table", "FT_SO_map.txt")
    so_file = os.path.join("ontologies", "so.obo")
    dc_file = os.path.join("ontologies", "dcterms.rdf")
    rdfs_file = os.path.join("ontologies", "rdf-schema.rdf")
    main(ft_file, so_ft_map_file, so_file, dc_file, rdfs_file)

########NEW FILE########
__FILENAME__ = sparta
#!/usr/bin/env python

"""
sparta.py - a Simple API for RDF

Sparta is a simple API for RDF that binds RDF nodes to Python 
objects and RDF arcs to attributes of those Python objects. As 
such, it can be considered a "data binding" from RDF to Python.

Requires rdflib <http://www.rdflib.net/> version 2.2.1+.

INCOMPATIBLE CHANGES:
 * Requires rdflib 2.2.1 or greater
 * Thing instantiation now requires an alias_map (but you shouldn't be instantiating it 
   directly anyway...)
ADDITIONS:
 * Adjust to API changes in rdflib (TripleStore->Graph, namespace_manager)
 * addAlias() on the factory accommodates troublesome URIs
TODO: 
 * rdflib context support
 * check API vs. RDF requirements, esp. WRT list (multiple items, sparse, etc.)
 * support other RDF containers?
 * type list members?
 * make type/cardinality lookup more efficient, refactor
 * unit tests
 * complete schema type support (date/time types; wait for PEP 321)
"""

__license__ = """
Copyright (c) 2001-2005 Mark Nottingham <mnot@pobox.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__version__ = "0.81"

import base64, sets
import rdflib   # http://rdflib.net/
from rdflib.Identifier import Identifier as ID
from rdflib.URIRef import URIRef as URI
from rdflib.BNode import BNode
from rdflib.Literal import Literal
from rdflib import RDF, RDFS

RDF_SEQi = "http://www.w3.org/1999/02/22-rdf-syntax-ns#_%s"
MAX_CARD = URI("http://www.w3.org/2002/07/owl#maxCardinality")
CARD = URI("http://www.w3.org/2002/07/owl#cardinality")
RESTRICTION = URI("http://www.w3.org/2002/07/owl#Restriction")
FUNC_PROP = URI("http://www.w3.org/2002/07/owl#FunctionalProperty")
ON_PROP = URI("http://www.w3.org/2002/07/owl#onProperty")
ONE = Literal("1")



class ThingFactory:
    """
    Fed a store, return a factory that can be used to instantiate
    Things into that world.
    """
    def __init__(self, store, schema_store=None, alias_map=None):
        """
        store - rdflib.Graph.Graph instance
        schema_store - rdflib.Graph.Graph instance; defaults to store
        """
        self.store = store
        self.schema_store = schema_store or self.store
        self.alias_map = alias_map or {}

    def __call__(self, ident, **props):
        """
        ident - either:
            a) None  (creates a new BNode)
            b) rdflib.URIRef.URIRef instance
            c) str in the form prefix_localname
        props - dict of properties and values, to be added. If the value is a list, its
                contents will be added to a ResourceSet.

        returns Thing instance
        """
        return Thing(self.store, self.schema_store, self.alias_map, ident, props)

    def addAlias(self, alias, uri):
        """
        Add an alias for an pythonic name to a URI, which overrides the 
        default prefix_localname syntax for properties and object names. Intended to 
        be used for URIs which are unmappable.
        
        E.g., 
          .addAlias("foobar", "http://example.com/my-unmappable-types#blah-type")
        will map the .foobar property to the provided URI.
        """
        self.alias_map[alias] = uri
    
class Thing:
    """ An RDF resource, as uniquely identified by a URI. Properties
        of the resource are avaiable as attributes; for example: 
        .prefix_localname is the property in the namespace mapped 
        to the "prefix" prefix, with the localname "localname".
        
        A "python literal datatype" is a datatype that maps to a Literal type; 
        e.g., int, float, bool.

        A "python data representation" is one of:
            a) a python literal datatype
            b) a self.__class__ instance
            c) a list containing a and/or b
    """
    def __init__(self, store, schema_store, alias_map, ident, props=None):
        """
        store - rdflib.Graph.Graph
        schema_store - rdflib.Graph.Graph
        ident - either:
            a) None  (creates a new BNode)
            b) rdflib.URIRef.URIRef instance
            c) str in the form prefix_localname
        props - dict of properties and values, to be added. If the value is a list, its
                contents will be added to a ResourceSet.
        """
        self._store = store
        self._schema_store = schema_store
        self._alias_map = alias_map
        if ident is None:
            self._id = BNode()
        elif isinstance(ident, ID):
            self._id = ident
        else:
            self._id = self._AttrToURI(ident)
        if props is not None:
            for attr, obj in props.items():
                if type(obj) is type([]):
                    [self.__getattr__(attr).add(o) for o in obj]
                else:
                    self.__setattr__(attr, obj)

    def get_id(self):
        return self._URIToAttr(self._id)
        
    def __getattr__(self, attr):
        """
        attr - either:
            a) str starting with _  (normal attribute access)
            b) str that is a URI
            c) str in the form prefix_localname

        returns a python data representation or a ResourceSet instance
        """
        if attr[0] == '_':
            raise AttributeError
        else:
            if ":" in attr:
                pred = URI(attr)
            else:
                try:
                    pred = self._AttrToURI(attr)
                except ValueError:
                    raise AttributeError
            if self._isUniqueObject(pred):
                try:
                    obj = self._store.triples((self._id, pred, None)).next()[2]
                except StopIteration:
                    raise AttributeError
                return self._rdfToPython(pred, obj)
            else:
                return ResourceSet(self, pred)
                
    def __setattr__(self, attr, obj):
        """
        attr - either:
            a) str starting with _  (normal attribute setting)
            b) str that is a URI
            c) str in the form prefix_localname
        obj - a python data representation or a ResourceSet instance
        """
        if attr[0] == '_':
            self.__dict__[attr] = obj
        else:
            if ":" in attr:
                pred = URI(attr)
            else:
                try:                    
                    pred = self._AttrToURI(attr)
                except ValueError:
                    raise AttributeError
            if self._isUniqueObject(pred):
                self._store.remove((self._id, pred, None))
                self._store.add((self._id, pred, self._pythonToRdf(pred, obj)))
            elif isinstance(obj, (sets.BaseSet, ResourceSet)):
                ResourceSet(self, pred, obj.copy())
            else:
                raise TypeError

    def __delattr__(self, attr):
        """
        attr - either:
            a) str starting with _  (normal attribute deletion)
            b) str that is a URI
            c) str in the form prefix_localname
        """        
        if attr[0] == '_':
            del self.__dict__[attr]
        else:
            if ":" in attr:
                self._store.remove((self._id, URI(attr), None))
            else:
                try:
                    self._store.remove((self._id, self._AttrToURI(attr), None))
                except ValueError:
                    raise AttributeError

    def _rdfToPython(self, pred, obj):
        """
        Given a RDF predicate and object, return the equivalent Python object.
        
        pred - rdflib.URIRef.URIRef instance
        obj - rdflib.Identifier.Identifier instance

        returns a python data representation
        """ 
        obj_types = self._getObjectTypes(pred, obj)
        if isinstance(obj, Literal):  # typed literals
            return self._literalToPython(obj, obj_types)
        elif RDF.List in obj_types:
            return self._listToPython(obj)
        elif RDF.Seq in obj_types:
            l, i = [], 1
            while True:
                counter = URI(RDF_SEQi % i)
                try:
                    item = self._store.triples((obj, counter, None)).next()[2]
                except StopIteration:
                    return l
                l.append(self._rdfToPython(counter, item)) 
                i += 1
        elif isinstance(obj, ID):
            return self.__class__(self._store, self._schema_store, self._alias_map, obj)
        else:
            raise ValueError

    def _pythonToRdf(self, pred, obj):
        """
        Given a Python predicate and object, return the equivalent RDF object.
        
        pred - rdflib.URIRef.URIRef instance
        obj - a python data representation
            
        returns rdflib.Identifier.Identifier instance
        """
        obj_types = self._getObjectTypes(pred, obj)
        if RDF.List in obj_types:
            blank = BNode()
            self._pythonToList(blank, obj)   ### this actually stores things... 
            return blank
        elif RDF.Seq in obj_types:  ### so will this
            blank = BNode()
            i = 1
            for item in obj:
                counter = URI(RDF_SEQi % i)
                self._store.add((blank, counter, self._pythonToRdf(counter, item)))
                i += 1
            return blank
        elif isinstance(obj, self.__class__):
            if obj._store is not self._store:
                obj.copyTo(self._store)  ### and this...
            return obj._id
        else:
            return self._pythonToLiteral(obj, obj_types)

    def _literalToPython(self, obj, obj_types):
        """
        obj - rdflib.Literal.Literal instance
        obj_types - iterator yielding rdflib.URIRef.URIRef instances
        
        returns a python literal datatype
        """
        for obj_type in obj_types:
            try:
                return SchemaToPython[obj_type][0](obj)
            except KeyError:
                pass
        return SchemaToPythonDefault[0](obj)
    
    def _pythonToLiteral(self, obj, obj_types):
        """
        obj - a python literal datatype
        obj_types - iterator yielding rdflib.URIRef.URIRef instances
        
        returns rdflib.Literal.Literal instance
        """
        for obj_type in obj_types:
            try:
                return Literal(SchemaToPython[obj_type][1](obj))
            except KeyError:
                pass
        return Literal(SchemaToPythonDefault[1](obj))
            
    def _listToPython(self, subj):
        """
        Given a RDF list, return the equivalent Python list.
        
        subj - rdflib.Identifier.Identifier instance

        returns list of python data representations
        """
        try:
            first = self._store.triples((subj, RDF.first, None)).next()[2]
        except StopIteration:
            return []
        try:
            rest = self._store.triples((subj, RDF.rest, None)).next()[2]
        except StopIteration:
            return ValueError
        return [self._rdfToPython(RDF.first, first)] + self._listToPython(rest)  ### type first?

    def _pythonToList(self, subj, members):
        """
        Given a Python list, store the eqivalent RDF list.
        
        subj - rdflib.Identifier.Identifier instance
        members - list of python data representations
        """
        first = self._pythonToRdf(RDF.first, members[0])
        self._store.add((subj, RDF.first, first))
        if len(members) > 1:
            blank = BNode()
            self._store.add((subj, RDF.rest, blank))
            self._pythonToList(blank, members[1:])
        else:
            self._store.add((subj, RDF.rest, RDF.nil))
            
    def _AttrToURI(self, attr):
        """
        Given an attribute, return a URIRef.
        
        attr - str in the form prefix_localname
        
        returns rdflib.URIRef.URIRef instance
        """
        if self._alias_map.has_key(attr):
            return URI(self._alias_map[attr])
        else:
            prefix, localname = attr.split("_", 1)
            return URI("".join([self._store.namespace_manager.store.namespace(prefix), localname]))

    def _URIToAttr(self, uri):
        """
        Given a URI, return an attribute.
        
        uri - str that is a URI
        
        returns str in the form prefix_localname. Not the most efficient thing around.
        """
        for alias, alias_uri in self._alias_map.items():
            if unicode(uri) == unicode(alias_uri):
                return alias
        for ns_prefix, ns_uri in self._store.namespace_manager.namespaces():
            if unicode(ns_uri) == unicode(uri[:len(ns_uri)]):
                return "_".join([ns_prefix, uri[len(ns_uri):]])
        raise ValueError

    def _getObjectTypes(self, pred, obj):
        """
        Given a predicate and an object, return a list of the object's types.
        
        pred - rdflib.URIRef.URIRef instance
        obj - rdflib.Identifier.Identifier instance
        
        returns list containing rdflib.Identifier.Identifier instances
        """
        obj_types = [o for (s, p, o) in self._schema_store.triples(
          (pred, RDFS.range, None))]
        if isinstance(obj, URI):
            obj_types += [o for (s, p, o) in self._store.triples((obj, RDF.type, None))]
        return obj_types

    def _isUniqueObject(self, pred):
        """
        Given a predicate, figure out if the object has a cardinality greater than one.
        
        pred - rdflib.URIRef.URIRef instance
        
        returns bool
        """
        # pred rdf:type owl:FunctionalProperty - True
        if (pred, RDF.type, FUNC_PROP) in self._schema_store:
            return True
        # subj rdf:type [ rdfs:subClassOf [ a owl:Restriction; owl:onProperty pred; owl:maxCardinality "1" ]] - True
        # subj rdf:type [ rdfs:subClassOf [ a owl:Restriction; owl:onProperty pred; owl:cardinality "1" ]] - True
        subj_types = [o for (s, p, o) in self._store.triples((self._id, RDF.type, None))]
        for type in subj_types:
            superclasses = [o for (s, p, o) in \
              self._schema_store.triples((type, RDFS.subClassOf, None))]
            for superclass in superclasses:
                if (
                    (superclass, RDF.type, RESTRICTION) in self._schema_store and 
                    (superclass, ON_PROP, pred) in self._schema_store
                   ) and \
                   (
                    (superclass, MAX_CARD, ONE) in self._schema_store or 
                    (superclass, CARD, ONE) in self._schema_store
                   ): return True
        return False

    def __repr__(self):
        return self._id
        
    def __str__(self):
        try:
            return self._URIToAttr(self._id)
        except ValueError:
            return str(self._id)
                
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._id == other._id
        elif isinstance(other, ID):
            return self._id == other
    
    def __ne__(self, other):
        if self is other: return False
        else: return True
        
    def properties(self):
        """
        List unique properties.
        
        returns list containing self.__class__ instances
        """
        props = []
        for (s,p,o) in self._store.triples((self._id, None, None)):
            thing = self.__class__(self._store, self._schema_store,
                                    self._alias_map, p)
            if thing not in props:
                props.append(thing)
        return props

    def copyTo(self, store):
        """
        Recursively copy statements to the given store.
        
        store - rdflib.Store.Store
        """
        for (s, p, o) in self._store.triples((self._id, None, None)):
            store.add((s, p, o))
            if isinstance(o, (URI, BNode)):
                self.__class__(self._store, self._schema_store, self._alias_map, o).copyTo(store)
        
        
class ResourceSet:
    """
    A set interface to the object(s) of a non-unique RDF predicate. Interface is a subset
    (har, har) of sets.Set. .copy() returns a sets.Set instance.
    """
    def __init__(self, subject, predicate, iterable=None):
        """
        subject - rdflib.Identifier.Identifier instance
        predicate -  rdflib.URIRef.URIRef instance
        iterable - 
        """
        self._subject = subject
        self._predicate = predicate
        self._store = subject._store
        if iterable is not None:
            for obj in iterable:
                self.add(obj)
    def __len__(self):
        return len(list(
          self._store.triples((self._subject._id, self._predicate, None))))
    def __contains__(self, obj):
        if isinstance(obj, self._subject.__class__):    
            obj = obj._id
        else: ### doesn't use pythonToRdf because that might store it
            obj_types = self._subject._getObjectTypes(self._predicate, obj) 
            obj = self._subject._pythonToLiteral(obj, obj_types)
        return (self._subject._id, self._predicate, obj) in self._store
    def __iter__(self):
        for (s, p, o) in \
          self._store.triples((self._subject._id, self._predicate, None)):
            yield self._subject._pythonToRdf(self._predicate, o)
    def copy(self):
        return sets.Set(self)
    def add(self, obj):
        self._store.add((self._subject._id, self._predicate, 
          self._subject._pythonToRdf(self._predicate, obj)))
    def remove(self, obj):
        if not obj in self:
            raise KeyError
        self.discard(obj)
    def discard(self, obj):
        if isinstance(obj, self._subject.__class__):
            obj = obj._id
        else: ### doesn't use pythonToRdf because that might store it
            obj_types = self._subject._getObjectTypes(self._predicate, obj)
            obj = self._subject._pythonToLiteral(obj, obj_types)
        self._store.remove((self._subject._id, self._predicate, obj))
    def clear(self):
        self._store.remove((self._subject, self._predicate, None))

        
SchemaToPythonDefault = (unicode, unicode)
SchemaToPython = {  #  (schema->python, python->schema)  Does not validate.
    'http://www.w3.org/2001/XMLSchema#string': (unicode, unicode),
    'http://www.w3.org/2001/XMLSchema#normalizedString': (unicode, unicode),
    'http://www.w3.org/2001/XMLSchema#token': (unicode, unicode),
    'http://www.w3.org/2001/XMLSchema#language': (unicode, unicode),
    'http://www.w3.org/2001/XMLSchema#boolean': (bool, lambda i:unicode(i).lower()),
    'http://www.w3.org/2001/XMLSchema#decimal': (float, unicode), 
    'http://www.w3.org/2001/XMLSchema#integer': (long, unicode), 
    'http://www.w3.org/2001/XMLSchema#nonPositiveInteger': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#long': (long, unicode),
    'http://www.w3.org/2001/XMLSchema#nonNegativeInteger': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#negativeInteger': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#int': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#unsignedLong': (long, unicode),
    'http://www.w3.org/2001/XMLSchema#positiveInteger': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#short': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#unsignedInt': (long, unicode),
    'http://www.w3.org/2001/XMLSchema#byte': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#unsignedShort': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#unsignedByte': (int, unicode),
    'http://www.w3.org/2001/XMLSchema#float': (float, unicode),
    'http://www.w3.org/2001/XMLSchema#double': (float, unicode),  # doesn't do the whole range
#    duration
#    dateTime
#    time
#    date
#    gYearMonth
#    gYear
#    gMonthDay
#    gDay
#    gMonth
#    hexBinary
    'http://www.w3.org/2001/XMLSchema#base64Binary': (base64.decodestring, lambda i:base64.encodestring(i)[:-1]),
    'http://www.w3.org/2001/XMLSchema#anyURI': (str, str),
}


if __name__ == '__main__':
    # use: "python -i sparta.py [URI for RDF file]+"
    from rdflib.TripleStore import TripleStore
    import sys
    mystore = TripleStore()
    for arg in sys.argv[1:]:
        mystore.parse(arg)
    thing = ThingFactory(mystore)

########NEW FILE########
__FILENAME__ = pubmed_related_group
#!/usr/bin/env python
"""Group a list of PubMed IDs based on their relationships in Entrez.

This is a demonstration script tackling the problem of organizing a list
of journal articles into most related groups. The input is a list of pubmed IDs
and the resulting groups are printed, demonstrating the functionality.

It works by trying to group together most closely related items first and
gradually relaxing stringency until all items are placed into related groups.

Usage:
    pubmed_related_group.py <pmids>
"""
from __future__ import with_statement
import sys
import operator

from Bio import Entrez

def main(pmid_file):
    pmids = []
    with open(pmid_file) as in_handle:
        for line in in_handle:
            pmids.append(line.strip())
    entrez_grouper = EntrezRelatedGrouper(3, 10)
    all_groups = entrez_grouper.get_pmid_groups(pmids)
    print all_groups

class EntrezRelatedGrouper:
    """Group journal articles using the Entrez Elink related query.
    """
    def __init__(self, min_group_size, max_group_size):
        self._min_group = min_group_size
        self._max_group = max_group_size

        self._filter_params = [(0.08, 2), (0.10, 2), (0.11, 3),
                (0.125, 3), (0.15, 4), (0.2, 5), (0.9, 10)]

    def get_pmid_groups(self, pmids):
        """Retrieve related groups for the passed article PubMed IDs.

        This works through a set of increasingly less stringent filtering
        parameters, placing all PubMed IDs in groups based on related articles
        from Entrez.
        """
        pmid_related = self._get_elink_related_ids(pmids)
        filter_params = self._filter_params[:]
        final_groups = []
        while len(pmid_related) > 0:
            if len(filter_params) == 0:
                raise ValueError("Ran out of parameters before finding groups")
            cur_thresh, cur_related = filter_params.pop(0)
            while 1:
                filt_related = self._filter_related(pmid_related, cur_thresh,
                        cur_related)
                groups = self._groups_from_related_dict(filt_related)
                new_groups, pmid_related = self._collect_new_groups(
                        pmid_related, groups)
                final_groups.extend(new_groups)
                if len(new_groups) == 0:
                    break
            if len(pmid_related) < self._max_group:
                final_groups.append(pmid_related.keys())
                pmid_related = {}
        return final_groups

    def _collect_new_groups(self, pmid_related, groups):
        """Collect new groups within our parameters, updating the ones to find.
        """
        final_groups = []
        for group_items in groups:
            final_items = [i for i in group_items if pmid_related.has_key(i)]
            if (len(final_items) >= self._min_group and
                    len(final_items) <= self._max_group):
                final_groups.append(final_items)
                for item in final_items:
                    del pmid_related[item]
        final_related_dict = {}
        for pmid, related in pmid_related.items():
            final_related = [r for r in related if pmid_related.has_key(r)]
            final_related_dict[pmid] = final_related
        return final_groups, final_related_dict

    def _get_elink_related_ids(self, pmids):
        """Query Entrez elink for pub med ids related to the passed list.

        Returns a dictionary where the keys are input pubmed ids and the keys
        are related PubMed IDs, sorted by score.
        """
        pmid_related = {}
        for pmid in pmids:
            handle = Entrez.elink(dbform='pubmed', db='pubmed', id=pmid)
            record = Entrez.read(handle)
            cur_ids = []
            for link_dict in record[0]['LinkSetDb'][0]['Link']:
                cur_ids.append((int(link_dict.get('Score', 0)),
                    link_dict['Id']))
            cur_ids.sort()
            cur_ids.reverse()
            local_ids = [x[1] for x in cur_ids if x[1] in pmids]
            if pmid in local_ids:
                local_ids.remove(pmid)
            pmid_related[pmid] = local_ids
        return pmid_related

    def _filter_related(self, inital_dict, overrep_thresh=0.125, related_max=3):
        """Filter a dictionary of related terms to limit over-represented items.

        We may have some items represented many times in a set, which will lead
        to a non-useful huge cluster of related items. These are filtered,
        based on overrep_thresh, and the total items for any item is limited to
        related_max.
        """
        final_dict = {}
        all_vals = reduce(operator.add, inital_dict.values())
        for item_id, item_vals in inital_dict.items():
            final_vals = [val for val in item_vals if 
                float(all_vals.count(val)) / len(inital_dict) <= overrep_thresh]
            final_dict[item_id] = final_vals[:related_max]
        return final_dict

    def _groups_from_related_dict(self, related_dict):
        """Create a list of unique groups from a dictionary of relations.
        """
        cur_groups = []
        all_base = related_dict.keys()
        for base_id, cur_ids in related_dict.items():
            overlap = set(cur_ids) & set(all_base)
            if len(overlap) > 0:
                new_group = set(overlap | set([base_id]))
                is_unique = True
                for exist_i, exist_group in enumerate(cur_groups):
                    if len(new_group & exist_group) > 0:
                        update_group = new_group | exist_group
                        cur_groups[exist_i] = update_group
                        is_unique = False
                        break
                if is_unique:
                    cur_groups.append(new_group)
        return [list(g) for g in cur_groups]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print __doc__
        sys.exit()
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = blast
"""Calculate top cross species hits using BLAST.

Uses best e-value as a threshold to identify best cross-species hits in a number
of organism databases.
"""
import os
import codecs
import subprocess
import contextlib
import tempfile
import xml.parsers.expat
import StringIO

from Bio.Blast.Applications import NcbiblastpCommandline
from Bio.Blast import NCBIXML
from Bio import SeqIO

def get_org_dbs(db_dir, target_org):
    """Retrieve references to fasta and BLAST databases for included organisms.
    """
    fasta_ref = None
    org_names = []
    db_refs = []
    with open(os.path.join(db_dir, "organism_dbs.txt")) as org_handle:
        for line in org_handle:
            org, db = line.rstrip("\r\n").split("\t")
            if db:
                if org == target_org:
                    assert fasta_ref is None
                    fasta_ref = os.path.join(db_dir, "%s.fa" % db)
                org_names.append(org)
                db_refs.append(os.path.join(db_dir, db))
    assert fasta_ref is not None, "Did not find base organism database"
    return fasta_ref, org_names, db_refs

def blast_top_hits(key, rec, db_refs, tmp_dir, blast_cmd=None):
    """BLAST a fasta record against multiple DBs, returning top IDs and scores.
    """
    cur_id = _normalize_id(key)
    id_info = []
    score_info = []
    with _tmpfile(prefix="in", dir=tmp_dir) as ref_in:
        with open(ref_in, "w") as out_handle:
            out_handle.write(rec)
        for xref_db in db_refs:
            with _tmpfile(prefix="out", dir=tmp_dir) as blast_out:
                out_id, out_eval = _compare_by_blast(ref_in, xref_db, blast_out,
                                                     blast_cmd=blast_cmd)
                id_info.append(out_id)
                score_info.append(out_eval)
    return cur_id, id_info, score_info

def blast_hit_list(key, rec, xref_db, thresh, tmp_dir):
    """BLAST a record against a single database, returning hits above e-value threshold.
    """
    with _tmpfile(prefix="in-h", dir=tmp_dir) as ref_in:
        with open(ref_in, "w") as out_handle:
            SeqIO.write([rec], out_handle, "fasta")
        with _tmpfile(prefix="out-h", dir=tmp_dir) as blast_out:
            return _compare_by_blast_hitlist(ref_in, xref_db, blast_out, thresh)

def blast_two_seqs(rec1, rec2, tmp_dir):
    """Blast two sequences returning score and identify information.
    """
    with _tmpfile(prefix="in-21", dir=tmp_dir) as rec1_in:
        with _tmpfile(prefix="in-22", dir=tmp_dir) as rec2_in:
            with open(rec1_in, "w") as out_handle:
                SeqIO.write([rec1], out_handle, "fasta")
            with open(rec2_in, "w") as out_handle:
                SeqIO.write([rec2], out_handle, "fasta")
            with _tmpfile(prefix="out-2", dir=tmp_dir) as blast_out:
                return _compare_by_blast_2seq(rec1_in, rec2_in, blast_out)

def _compare_by_blast_hitlist(query, xref_db, blast_out, thresh):
    cl = NcbiblastpCommandline(query=query, db=xref_db, out=blast_out,
                               outfmt=6, max_target_seqs=10000, evalue=thresh)
    subprocess.check_call(str(cl).split())
    hits = []
    seen = set()
    with open(blast_out) as blast_handle:
        for line in blast_handle:
            parts = line.rstrip("\r\n").split("\t")
            if parts[1] not in seen:
                hits.append((parts[0], parts[1], parts[2], parts[-1]))
                seen.add(parts[1])
    return hits

def _compare_by_blast_2seq(query, subject, blast_out):
    """Compare two sequences by BLAST without output database.
    """
    cl = NcbiblastpCommandline(query=query, subject=subject, out=blast_out,
                               outfmt=6, max_target_seqs=1)
    subprocess.check_call(str(cl).split())
    with open(blast_out) as blast_handle:
        try:
            parts = blast_handle.next().strip().split("\t")
        except StopIteration:
            parts = [""] * 10
        identity = parts[2]
        score = parts[-1]
    return identity, score

def _compare_by_blast(input_ref, xref_db, blast_out, subject_blast=False,
                      blast_cmd=None):
    """Compare all genes in an input file to the output database.
    """
    if blast_cmd is None:
        blast_cmd = "blastp"
    cl = NcbiblastpCommandline(cmd=blast_cmd, query=input_ref, db=xref_db,
                               out=blast_out, outfmt=5, max_target_seqs=1)
    try:
        subprocess.check_call(str(cl).split())
    # handle BLAST errors cleanly; write an empty file and keep moving
    except (OSError, subprocess.CalledProcessError), e:
        if str(e) == "[Errno 2] No such file or directory":
            raise ValueError("Could not find blast executable: %s" % blast_cmd)
        with open(blast_out, "w") as out_handle:
            out_handle.write("\n")
    with codecs.open(blast_out, encoding="utf-8", errors="replace") as blast_handle:
        result = blast_handle.read()
        for problem in [u"\ufffd"]:
            result = result.replace(problem, " ")
        try:
            rec = NCBIXML.read(StringIO.StringIO(result))
        except (xml.parsers.expat.ExpatError, ValueError):
            rec = None
        if rec and len(rec.descriptions) > 0:
            id_info = _normalize_id(rec.descriptions[0].title.split()[1])
            return id_info, rec.descriptions[0].bits
        else:
            return "", 0

def _normalize_id(id_info):
    if id_info.startswith("gi|"):
        parts = [p for p in id_info.split("|") if p]
        id_info = parts[-1]
    return id_info

@contextlib.contextmanager
def _tmpfile(*args, **kwargs):
    """Make a tempfile, safely cleaning up file descriptors on completion.
    """
    (fd, fname) = tempfile.mkstemp(*args, **kwargs)
    try:
        yield fname
    finally:
        os.close(fd)
        if os.path.exists(fname):
            os.remove(fname)

########NEW FILE########
__FILENAME__ = cluster_install_distblast
#!/usr/bin/env python
"""Install distblast software on every node of a Hadoop cluster.

This is an example of how to remotely add non-AMI data or software
to a Hadoop cluster kicked off with whirr.

Usage:
    cluster_install_distblast.py <cluster config file>
"""
import os
import sys
import subprocess

import fabric.api as fabric
import fabric.contrib.files as fabric_files

def main(cluster_config):
    user = "hadoop"
    addresses = _get_whirr_addresses(cluster_config)
    # software for all nodes on the cluster
    for addr in addresses:
        install_distblast(addr, user)
    # data on the head node
    dl_distblast_data(addresses[0], user)

def dl_distblast_data(addr, user):
    """Download distblast data from S3 bucket for analysis.
    """
    data_url = "http://chapmanb.s3.amazonaws.com/distblast.tar.gz"
    with fabric.settings(host_string="%s@%s" % (user, addr)):
        if not fabric_files.exists("distblast"):
            fabric.run("wget %s" % data_url)
            fabric.run("tar -xzvpf %s" % os.path.basename(data_url))

def install_distblast(addr, user):
    print "Installing on", addr
    with fabric.settings(host_string="%s@%s" % (user, addr)):
        work_dir = "install"
        if not fabric_files.exists(work_dir):
            fabric.run("mkdir %s" % work_dir)
        with fabric.cd(work_dir):
            distblast_dir = "bcbb/distblast"
            if not fabric_files.exists(distblast_dir):
                fabric.run("git clone git://github.com/chapmanb/bcbb.git")
                with fabric.cd(distblast_dir):
                    fabric.run("python2.6 setup.py build")
                    fabric.sudo("python2.6 setup.py install")

def _get_whirr_addresses(whirr_config):
    """Retrieve IP addresses of cluster machines from Whirr.
    """
    cl = ["/home/bchapman/install/java/whirr-trunk/bin/whirr", "list-cluster", "--config", whirr_config]
    return _addresses_from_cl(cl)

def _addresses_from_cl(cl):
    proc = subprocess.Popen(cl, stdout=subprocess.PIPE)
    stdout = proc.communicate()[0]
    addresses = []
    for line in stdout.split("\n"):
        parts = line.split()
        if len(parts) > 0:
            addresses.append(parts[2])
    return addresses

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = distblast_pipes
#!/usr/bin/env python
"""Process a fasta file through Hadoop one record at a time using pydoop.
"""
import sys
import os
import json
import logging
logging.basicConfig(level=logging.DEBUG)

from pydoop.pipes import Mapper, Reducer, Factory, runTask
from pydoop.pipes import RecordReader, InputSplit, RecordWriter
from pydoop.hdfs import hdfs
from pydoop.utils import split_hdfs_path

from Bio import SeqIO

from bcbio.phylo import blast

class FastaMapper(Mapper):
    def map(self, context):
        config = context.getJobConf()
        tmp_dir = config.get("job.local.dir")
        xref_dbs = config.get("fasta.blastdb").split(",")
        cur_key, ids, scores = blast.blast_top_hits(context.getInputKey(),
                context.getInputValue(), xref_dbs, tmp_dir)
        cur_val = dict(ids=ids, scores=scores)
        context.emit(cur_key, json.dumps(cur_val))

class FastaReducer(Reducer):
    """Simple reducer that returns a value per input record identifier.
    """
    def reduce(self, context):
        key = context.getInputKey()
        vals = []
        while context.nextValue():
            vals.append(context.getInputValue())
        if len(vals) > 0:
            context.emit(key, vals[0])

class FastaReader(RecordReader):
    """Return one text FASTA record at a time using Biopython SeqIO iterators.
    """
    def __init__(self, context):
        super(FastaReader, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.isplit = InputSplit(context.getInputSplit())
        self.host, self.port, self.fpath = split_hdfs_path(self.isplit.filename)
        self.fs = hdfs(self.host, self.port)
        self.file = self.fs.open_file(self.fpath, os.O_RDONLY)
        self._iterator = (SeqIO.parse(self.file, "fasta") if
                          self.isplit.offset == 0 else None)

    def __del__(self):
        self.file.close()
        self.fs.close()

    def next(self):
        if self._iterator:
            try:
                record = self._iterator.next()
                return (True, record.id, record.format("fasta"))
            except StopIteration:
                pass
        return (False, "", "")

    def getProgress(self):
        return 0

def main(argv):
    runTask(Factory(FastaMapper, FastaReducer, record_reader_class=FastaReader))

if __name__ == "__main__":
    main(sys.argv)

########NEW FILE########
__FILENAME__ = distblast_streaming
#!/usr/bin/env python
"""Process a FASTA file using Hadoop streaming.

Examples with Dumbo and MrJob.
"""
import os
import sys
import json

from bcbio.phylo import blast

def mapper(key, rec):
    tmp_dir = os.environ["job_local_dir"]
    xref_dbs = os.environ["fasta_blastdb"].split(",")
    parts = rec.split("\t")
    if len(parts) == 3: # remove extra initial tab if present
        parts = parts[1:]
    title, seq = rec.split("\t")
    rec_id = title.split()[0]
    cur_key, ids, scores = blast.blast_top_hits(rec_id, seq, xref_dbs, tmp_dir)
    cur_val = dict(ids=ids, scores=scores)
    yield cur_key, cur_val

def reducer(key, vals):
    for v in vals:
        yield key, json.dumps(v)

# -- Alternative MrJob version.
want_mrjob=False

if want_mrjob:
    from mrjob.job import MRJob

    class DistblastJob(MRJob):
        def hadoop_job_runner_kwargs(self):
            config = MRJob.hadoop_job_runner_kwargs(self)
            # config["hadoop_extra_args"].extend(
            #         ["-inputformat", "com.lifetech.hadoop.streaming.FastaInputFormat",
            #          "-libjars", "jars/bioseq-0.0.1.jar"])
            return config

        def mapper(self, key, rec):
            for k, v in mapper(key, rec):
                yield k, v

        def reducer(self, key, vals):
            for k, v in reducer(key, vals):
                yield k, v

if __name__ == '__main__':
    if want_mrjob:
        DistblastJob.run()
    else:
        import dumbo
        dumbo.run(mapper, reducer)

########NEW FILE########
__FILENAME__ = hadoop_run
#!/usr/bin/env python
"""Build up a hadoop job to process an input FASTA file.

This handles copying over all of the input files, scripts and databases.
After running the Hadoop job, the output files are retrieved and reformatted
to be identical to a local run.
"""
import os
import sys
import csv
import glob
import json
import shutil
import optparse
import subprocess

import yaml

from bcbio.phylo import blast

def main(script, org_config_file, config_file, in_dir, out_dir):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    with open(org_config_file) as in_handle:
        org_config = yaml.load(in_handle)
    if os.path.exists(in_dir):
        shutil.rmtree(in_dir)
    os.makedirs(in_dir)
    shutil.copy(org_config["search_file"], in_dir)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    job_name = os.path.splitext(os.path.basename(script))[0]
    print "Creating working directories in HDFS"
    hdfs_script, hdfs_in_dir, hdfs_out_dir = setup_hdfs(job_name, script,
                                                        in_dir, out_dir)
    print "Copying organism database files to HDFS"
    db_files, dbnames, org_names = setup_db(job_name, config['db_dir'],
                                            org_config['target_org'])
    print "Running script on Hadoop"
    if script.endswith("streaming.py"):
        run_hadoop_streaming(job_name, script, hdfs_in_dir, hdfs_out_dir,
                             db_files, dbnames)
    else:
        run_hadoop(job_name, hdfs_script, hdfs_in_dir, hdfs_out_dir,
                   db_files, dbnames)
    print "Processing output files"
    process_output(hdfs_out_dir, out_dir, org_config['target_org'],
                   org_names)

def run_hadoop_streaming(job_name, script, hdfs_in_dir, hdfs_out_dir, db_files, dbnames):
    """Run a hadoop streaming job with dumbo.
    """
    cachefiles = []
    for db_file in db_files:
        cachefiles.extend(("-cachefile", db_file))
    hadoop = os.path.join(os.environ["HADOOP_HOME"], "bin", "hadoop")
    hadoop = os.environ["HADOOP_HOME"]
    cl = ["dumbo", script, "-hadoop", hadoop, "-input", hdfs_in_dir,
          "-output", hdfs_out_dir, "-name", job_name,
          "-inputformat", "com.lifetech.hadoop.streaming.FastaInputFormat",
          "-libjar", os.path.abspath("jar/bioseq-0.0.1.jar"),
          "-outputformat", "text",
          "-cmdenv", "fasta_blastdb=%s" % ','.join(dbnames)] + cachefiles
    subprocess.check_call(cl)

def run_hadoop_streaming_mrjob(job_name, script, in_dir, db_files_str, dbnames):
    jobconf_opts = {
        "mapred.job.name" : job_name,
        "mapred.cache.files" : db_files_str,
        "mapred.create.symlink" : "yes",
        "fasta.blastdb": ",".join(dbnames)
        #"mapred.task.timeout": "60000", # useful for debugging
        }
    hadoop_opts = {
        "-inputformat": "com.lifetech.hadoop.streaming.FastaInputFormat",
        "-libjars" : os.path.abspath("jars/bioseq-0.0.1.jar")
        }
    def _mrjob_opts(opts, type, connect):
        out = []
        for k, v in opts.iteritems():
            if connect == " ":
                val = "'%s %s'" % (k, v)
            else:
                val = "%s%s%s" % (k, connect, v)
            out.append("%s=%s" % (type, val))
        return out
    cl = [sys.executable, script, "-r", "hadoop"] + \
         _mrjob_opts(jobconf_opts, "--jobconf", "=") + \
         _mrjob_opts(hadoop_opts, "--hadoop-arg", " ") + \
         glob.glob(os.path.join(in_dir, "*"))
    subprocess.check_call(cl)

def run_hadoop(job_name, hdfs_script, hdfs_in_dir, hdfs_out_dir,
               db_files, dbnames):
    hadoop_opts = {
      "mapred.job.name" : job_name,
      "hadoop.pipes.executable": hdfs_script,
      "mapred.cache.files" : ",".join(db_files),
      "mapred.create.symlink" : "yes",
      "hadoop.pipes.java.recordreader": "false",
      "hadoop.pipes.java.recordwriter": "true",
      "mapred.map.tasks": "2",
      "mapred.reduce.tasks": "2",
      #"mapred.task.timeout": "60000", # useful for debugging
      "fasta.blastdb": ",".join(dbnames)
      }
    cl = ["hadoop", "pipes"] + _cl_opts(hadoop_opts) + [
          "-program", hdfs_script,
          "-input", hdfs_in_dir, "-output", hdfs_out_dir]
    subprocess.check_call(cl)

def _read_hadoop_out(out_dir, work_dir):
    """Reformat Hadoop output files for tab delimited output.
    """
    cl = ["hadoop", "fs", "-ls", os.path.join(out_dir, "part-*")]
    p = subprocess.Popen(cl, stdout=subprocess.PIPE)
    (out, _) = p.communicate()
    for fname in sorted([l.split()[-1] for l in out.split("\n")
                         if l and not l.startswith("Found")]):
        local_fname = os.path.join(work_dir, os.path.basename(fname))
        cl = ["hadoop", "fs", "-get", fname, local_fname]
        subprocess.check_call(cl)
        with open(local_fname) as in_handle:
            for line in in_handle:
                cur_id, info = line.split("\t")
                data = json.loads(info)
                data["cur_id"] = cur_id
                yield data
        os.remove(local_fname)

def process_output(hdfs_out_dir, local_out_dir, target_org, org_names):
    """Convert JSON output into tab delimited score and ID files.
    """
    if not os.path.exists(local_out_dir):
        os.makedirs(local_out_dir)
    base = target_org.replace(" ", "_")
    id_file = os.path.join(local_out_dir, "%s-ids.tsv" % base)
    score_file = os.path.join(local_out_dir, "%s-scores.tsv" % base)
    with open(id_file, "w") as id_handle:
        with open(score_file, "w") as score_handle:
            id_writer = csv.writer(id_handle, dialect="excel-tab")
            score_writer = csv.writer(score_handle, dialect="excel-tab")
            header = [""] + org_names
            id_writer.writerow(header)
            score_writer.writerow(header)
            for data in _read_hadoop_out(hdfs_out_dir, local_out_dir):
                id_writer.writerow([data["cur_id"]] + data['ids'])
                score_writer.writerow([data["cur_id"]] + data['scores'])

def setup_hdfs(hdfs_work_dir, script, in_dir, out_dir):
    """Add input, output and script directories to hdfs.
    """
    cl = ["hadoop", "fs", "-test", "-d", hdfs_work_dir]
    result = subprocess.call(cl)
    if result == 0:
        cl = ["hadoop", "fs", "-rmr", hdfs_work_dir]
        subprocess.check_call(cl)
    cl = ["hadoop", "fs", "-mkdir", hdfs_work_dir]
    subprocess.check_call(cl)
    out_info = []
    # copy over input and files
    for lfile in [script, in_dir]:
        hdfs_ref = _hdfs_ref(hdfs_work_dir, lfile)
        cl = ["hadoop", "fs", "-put", lfile, hdfs_ref]
        subprocess.check_call(cl)
        out_info.append(hdfs_ref)
    hdfs_out = _hdfs_ref(hdfs_work_dir, out_dir)
    out_info.append(hdfs_out)
    return out_info

def setup_db(work_dir_base, db_dir, target_org):
    """Copy over BLAST database files, prepping them for map availability.
    """
    (_, org_names, db_refs) = blast.get_org_dbs(db_dir, target_org)
    work_dir = os.path.join(work_dir_base, db_dir)
    cl = ["hadoop", "fs", "-mkdir", work_dir]
    subprocess.check_call(cl)
    ref_info = []
    blast_dbs = []
    for db_path in db_refs:
        blast_dbs.append(os.path.basename(db_path))
        for fname in glob.glob(db_path + ".[p|n]*"):
            hdfs_ref = _hdfs_ref(work_dir, fname)
            cl = ["hadoop", "fs", "-put", fname, hdfs_ref]
            subprocess.check_call(cl)
            ref_info.append("%s#%s" % (hdfs_ref, os.path.basename(hdfs_ref)))
    return ref_info, blast_dbs, org_names

def _hdfs_ref(work_dir, local_file):
    basename = os.path.basename(local_file)
    if basename == "":
        basename = os.path.basename(os.path.dirname(local_file))
    return os.path.join(work_dir, basename)

def _cl_opts(opts):
    cl = []
    for key, val in opts.iteritems():
        cl.append("-D")
        cl.append("%s=%s" % (key, val))
    return cl

if __name__ == "__main__":
    parser = optparse.OptionParser()
    opts, args = parser.parse_args()
    main(*args)

########NEW FILE########
__FILENAME__ = blast_all_by_all
#!/usr/bin/env python
"""BLAST all proteins in a genome versus each other individually.

Prepares a matrix of identifies and BLAST scores for an all-versus-all
comparison of individual proteins versus each other.

Usage:
  blast_all_by_all.py <base_config.yaml> <org_config.yaml> <id_file.tsv>
"""
import os
import sys
import csv
import subprocess
import multiprocessing

import yaml
from scipy import sparse, io
from Bio import SeqIO

from bcbio.phylo import blast
from bcbio.picard.utils import chdir

def main(base_config_file, org_config_file, id_file):
    with open(base_config_file) as in_handle:
        config = yaml.load(in_handle)
    with open(org_config_file) as in_handle:
        org_config = yaml.load(in_handle)
    with open(id_file) as in_handle:
        ids = read_id_file(in_handle)
    data_out = "%s-all_search-data.tsv" % org_config["target_org"].replace(" ", "_")
    if not os.path.exists(data_out):
        with open(data_out, "w") as out_handle:
            prepare_data_file(out_handle, ids, org_config, config)
    write_out_matrices(ids, data_out)

def write_out_matrices(ids, data_out):
    base = os.path.splitext(data_out)[0].replace("-data", "")
    mat_file = "%s-scores.mat" % base
    with open(data_out, 'rU') as in_handle:
        score_matrix, ident_matrix = get_matrices(in_handle, ids)
    io.savemat(mat_file, {"human_scores" : score_matrix,
                          "human_identities" : ident_matrix,
                          "human_ids" : ids})
    #id_file = "%s-ids.txt" % base
    #with open(id_file, "w") as out_handle:
    #    for i in ids:
    #        out_handle.write("%s\n" % i)

def get_matrices(in_handle, ids):
    pos_lookup = {}
    for pos, eid in enumerate(ids):
        pos_lookup[eid] = pos
    scores = sparse.lil_matrix((len(ids), len(ids)))
    idents = sparse.lil_matrix((len(ids), len(ids)))
    reader = csv.reader(in_handle, dialect="excel-tab")
    reader.next() # header
    for id1, id2, score, ident in reader:
        pos1 = pos_lookup[id1]
        pos2 = pos_lookup[id2]
        scores[pos1,pos2] = float(score)
        idents[pos1,pos2] = float(ident)
    return scores, idents

def prepare_data_file(out_handle, ids, org_config, config):
    writer = csv.writer(out_handle, dialect="excel-tab")
    seq_recs = SeqIO.index(org_config["search_file"], "fasta")
    search_db = make_search_db(seq_recs, ids, org_config["target_org"], config["work_dir"])
    writer.writerow(["rec1", "rec2", "score", "identity"])
    pool = multiprocessing.Pool(int(config["num_cores"]))
    results = pool.imap(blast_seqs,
                        ((i, seq_recs[i], search_db, config) for i in ids))
    for info in results:
        for id1, id2, identity, score in info:
            writer.writerow([id1, id2, score, identity])

def make_search_db(seq_recs, ids, target_org, tmp_dir):
    search_db = "%s-db.fa" % target_org.replace(" ", "_")
    db_name = os.path.splitext(search_db)[0]
    with chdir(tmp_dir):
        with open(search_db, "w") as out_handle:
            SeqIO.write((seq_recs[i] for i in ids), out_handle, "fasta")
        cl = ["makeblastdb", "-in", search_db,
              "-dbtype", "prot",
              "-out", db_name,
              "-title", target_org]
        subprocess.check_call(cl)
    return os.path.join(tmp_dir, db_name)

def blast_seqs(args):
    """Blast two sequences, returning the score and identity.
    """
    def do_work(rec_id, rec, org_db, config):
        return blast.blast_hit_list(rec_id, rec, org_db, config["evalue_thresh"], config["work_dir"])
    return do_work(*args)

def read_id_file(in_handle):
    in_handle.next() # header
    return [l.split("\t")[0] for l in in_handle]

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = blast_cross_orgs
#!/usr/bin/env python
"""Perform genome wide BLAST comparisons of an organism against other genomes.

Usage:
    blast_cross_orgs.py <organism config> <YAML config>

This requires a set of BLAST databases setup by 'retrieve_org_dbs.py'.

Requires:
    - NCBI's blast+
    - Biopython libraries
"""
import os
import sys
import csv
import itertools
import multiprocessing

import yaml
from Bio import SeqIO

from bcbio.phylo import blast

def main(org_config_file, config_file):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    with open(org_config_file) as in_handle:
        org_config = yaml.load(in_handle)
    if not os.path.exists(config['work_dir']):
        os.makedirs(config['work_dir'])
    (_, org_names, db_refs) = blast.get_org_dbs(config['db_dir'],
            org_config['target_org'])
    id_file, score_file = setup_output_files(org_config['target_org'])
    with open(org_config['search_file']) as in_handle:
        with open(id_file, "w") as id_out_handle:
            with open(score_file, "w") as score_out_handle:
                id_writer = csv.writer(id_out_handle, dialect='excel-tab')
                score_writer = csv.writer(score_out_handle, dialect='excel-tab')
                header = [""] + org_names
                id_writer.writerow(header)
                score_writer.writerow(header)
                _do_work(db_refs, in_handle, id_writer, score_writer, config)

def _do_work(db_refs, in_handle, id_writer, score_writer, config):
    cores = int(config["num_cores"])
    pool = multiprocessing.Pool(cores)
    for rec_group in partition_all(cores * 100, SeqIO.parse(in_handle, "fasta")):
        for out in pool.imap(_process_wrapper,
                             ((rec, db_refs, config['work_dir'], config.get("blast_cmd"))
                              for rec in rec_group)):
            id_writer.writerow([out["cur_id"]] + out["cmp_id"])
            score_writer.writerow([out["cur_id"]] + out["cmp_score"])

def partition_all(n, iterable):
    """Split into lazy chunks of n size.
    http://stackoverflow.com/questions/5129102/python-equivalent-to-clojures-partition-all
    """
    it = iter(iterable)
    while True:
        chunk = list(itertools.islice(it, n))
        if not chunk:
            break
        yield chunk

def _process_wrapper(args):
    try:
        return process_blast(*args)
    except KeyboardInterrupt:
        raise Exception

def process_blast(rec, db_refs, tmp_dir, blast_cmd):
    """Run a BLAST writing results to shared files.
    """
    cur_id, id_info, score_info = blast.blast_top_hits(rec.id, rec.format("fasta"),
            db_refs, tmp_dir, blast_cmd)
    print cur_id
    return {"cmp_id": id_info,
            "cmp_score": score_info,
            "cur_id": cur_id}

def setup_output_files(target_org):
    base = target_org.replace(" ", "_")
    id_file = "%s-ids.tsv" % base
    eval_file = "%s-scores.tsv" % base
    return id_file, eval_file

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = filter_by_transcript
#!/usr/bin/env python
"""Filter an output file, removing alternative transcripts based on names.

Filter ID and score output files from a distributed BLAST, returning
the longest transcript for a gene as an evolutionary transcript sample for
that gene.

Usage:
    filter_by_transcript.py <org config file>
"""
import sys
import os
import csv
import re
import collections
from optparse import OptionParser

import yaml
from Bio import SeqIO

def main(config_file):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    target_files = files_to_filter(config["target_org"])
    names_to_include = get_representative_txs(config['search_file'])
    for f in target_files:
        filter_file(f, names_to_include)

def filter_file(to_filter, names_to_include):
    new_ext = "longtxs"
    base, ext = os.path.splitext(to_filter)
    out_file = "%s-%s%s" % (base, new_ext, ext)
    with open(to_filter, 'rU') as in_handle:
        with open(out_file, "w") as out_handle:
            reader = csv.reader(in_handle, dialect="excel-tab")
            writer = csv.writer(out_handle, dialect="excel-tab")
            writer.writerow(reader.next())
            for parts in reader:
                if parts[0] in names_to_include:
                    writer.writerow(parts)

def get_representative_txs(in_file):
    """Retrieve the largest transcript for each gene, using Ensembl headers.

    This relies on Ensembl header structure in FASTA files. For all genes,
    the largest of potentially many alternative transcripts is chosen as
    the representative sample.
    """
    txs_by_gene = collections.defaultdict(list)
    with open(in_file) as in_handle:
        for rec in SeqIO.parse(in_handle, "fasta"):
            protein_id = rec.id
            header_gene = [p for p in rec.description.split()
                           if p.startswith("gene:")]
            assert len(header_gene) == 1, \
                   "Ensembl gene name not found in header: %s" % rec.description
            (_, gene) = header_gene[0].split(":")
            txs_by_gene[gene].append((len(rec.seq), protein_id))
    final_list = []
    for choices in txs_by_gene.values():
        choices.sort(reverse=True)
        final_list.append(choices[0][1])
    print final_list[:10]
    return set(final_list)

def files_to_filter(base_name):
    base_name = base_name.replace(" ", "_")
    exts = ["ids.tsv", "scores.tsv"]
    fnames_find = ["%s-%s" % (base_name, e) for e in exts]
    fnames = [f for f in fnames_find if os.path.exists(f)]
    if len(fnames) == 0:
        raise ValueError("Did not find files to filter: %s" % fnames_find)
    return fnames

if __name__ == "__main__":
    parser = OptionParser()
    options, args = parser.parse_args()
    if len(args) != 1:
        print __doc__
        sys.exit()
    main(args[0])

########NEW FILE########
__FILENAME__ = homolog_seq_retrieval
#!/usr/bin/env python
"""Retrieve sequences for a group of homologs based on a gene list.

Usage:
    homolog_seq_retrieval.py <base config> <org config> <id result file>
"""
import sys
import csv
import os
import re

import yaml
from Bio import SeqIO

def main(base_file, org_file, result_file):
    with open(base_file) as in_handle:
        base_config = yaml.load(in_handle)
    with open(org_file) as in_handle:
        org_config = yaml.load(in_handle)
    out_dir = os.path.join(os.getcwd(), "%s-seqs" %
            org_config['target_org'].replace(" ", "-"))
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    id_list = read_gene_list(org_config['gene_list'])
    id_list = _build_alt_tx_res(id_list)
    with open(result_file, 'rU') as in_handle:
        reader = csv.reader(in_handle, dialect='excel-tab')
        org_list = reader.next()[1:]
        id_indexes = prepare_indexes(org_config['search_file'],
                base_config['db_dir'], org_list)
        print "Retrieving sequences from list"
        all_matches = dict()
        for cur_id, org_ids in ((l[0], l[1:]) for l in reader):
            match_index = _transcript_matches(cur_id, id_list)
            if match_index > -1:
                print cur_id
                out_file = os.path.join(out_dir, "%s.fa" %
                        cur_id.replace(".", "_"))
                output_seqs([cur_id] + org_ids,
                    [org_config['target_org']] + org_list,
                    id_indexes, out_file)
                all_matches[match_index] = ""
    print "Not found", [id_list[i][0] for i in set(range(len(id_list))) -
            set(all_matches.keys())]

def output_seqs(ids, orgs, indexes, out_file):
    """Output the sequences we are interested in retrieving.
    """
    with open(out_file, "w") as out_handle:
        SeqIO.write(_all_seqs(ids, orgs, indexes), out_handle, "fasta")

def _all_seqs(ids, orgs, indexes):
    """Lazy generator of sequences from our indexes, with IDs properly set.
    """
    for i, cur_id in enumerate(ids):
        if cur_id:
            rec = indexes[i][cur_id]
            rec.id = cur_id
            rec.description = orgs[i]
            yield rec

def _build_alt_tx_res(id_list):
    """Create regular expressions to find alternative transcripts.

    Matches alternative transcripts of base.1 of the form:
        base.1a
        base.1.1
        base.1a.1
    """
    final_list = []
    for cur_id in id_list:
        match_re = re.compile(r"^" + cur_id + r"([a-z]+|\.\d+)(\.\d+)?$")
        final_list.append((cur_id, match_re))
    return final_list

def _transcript_matches(cur_id, id_list):
    """Check if a transcript matches one of the alternatively spliced names.
    """
    for index, (test_id, test_re) in enumerate(id_list):
        if cur_id == test_id or test_re.search(cur_id):
            return index
    return  -1

def prepare_indexes(base_file, db_dir, orgs):
    """Prepare easy to retrieve Biopython indexes from Fasta inputs.
    """
    print "Preparing fasta indexes"
    indexes = []
    for fname in [base_file] + [_get_org_fasta(db_dir, o) for o in orgs]:
        normalizer = IdNormalizer()
        indexes.append(SeqIO.index(fname, "fasta",
            key_function=normalizer.normalize))
        normalizer.finished = True
    return indexes

def _get_org_fasta(db_dir, org):
    """Retrieve the FASTA file for an organism database.
    """
    base_file = os.path.join(db_dir, "organism_dbs.txt")
    with open(base_file) as in_handle:
        for line in in_handle:
            if line.startswith(org):
                parts = line.strip().split()
                return os.path.join(db_dir, "%s.fa" % parts[-1])
    raise ValueError("Did not find fasta file for %s" % org)

def read_gene_list(in_file):
    """Read list of genes of interest.
    """
    genes = []
    with open(in_file) as in_handle:
        reader = csv.reader(in_handle, 'rU')
        reader.next() # header
        for parts in reader:
            tid = parts[-1]
            genes.append(tid.strip())
    return genes

class IdNormalizer:
    def __init__(self):
        self._seen_ids = {}
        self._index = 0
        self.finished = False

    def normalize(self, id_info):
        if id_info.startswith("gi|"):
            parts = [p for p in id_info.split("|") if p]
            id_info = parts[-1]
        if not self.finished:
            try:
                self._seen_ids[id_info]
                self._index += 1
                return self._index
            except KeyError:
                self._seen_ids[id_info] = ""
                return id_info
        return id_info

if __name__ == "__main__":
    apply(main, sys.argv[1:])

########NEW FILE########
__FILENAME__ = retrieve_org_dbs
#!/usr/bin/env python
"""Retrieve full genome databases, preparing them for BLAST analysis.

Usage:
    retrieve_org_dbs.py <YAML config file>

Requires:
    - NCBI's blast+ -- for preparing the organism databases
      ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/
    - Biopython libraries
"""
import os
import sys
import csv
import glob
import ftplib
import subprocess
import contextlib
import urllib2
import socket
import time

import yaml

from Bio import Entrez

def main(config_file):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    Entrez.email = config.get('email', 'test@example.com')
    socket.setdefaulttimeout(config['url_timeout'])
    local_get = LocalRetrieval(config)
    ncbi_get = NcbiEntrezRetrieval(config)
    ensembl_get = EnsemblFtpRetrieval(config)
    organisms = read_org_list(config['org_file'])
    db_dir = config['db_dir']
    ensembl_db_dir = os.path.join(db_dir, "ensembl")
    for check_dir in [db_dir, ensembl_db_dir]:
        if not os.path.exists(check_dir):
            os.makedirs(check_dir)
    org_files = []
    for org in organisms:
        check_glob = os.path.join(config["db_dir"], "custom", "%s*" % org)
        print "Preparing organism:", org
        check_custom = [x for x in glob.glob(check_glob)
                        if not x.endswith((".phr", ".pin", ".psq"))]
        if org in config.get('problem_orgs', []):
            db_file = ''
        elif len(check_custom) == 1:
            db_file = local_get.retrieve_db(org, check_custom[0], db_dir)
        else:
            print("Did not find single pre-downloaded FASTA file in '%s'\n"
                  "Instead Found %s\n"
                  "Attempting to download from Ensembl or NCBI" % (check_glob, check_custom))
            db_file = ensembl_get.retrieve_db(org, ensembl_db_dir)
            if db_file:
                print "Ensembl"
                db_file = os.path.join(os.path.basename(ensembl_db_dir), db_file)
            else:
                print "NCBI"
                db_file = ncbi_get.retrieve_db(org, db_dir)
        org_files.append((org, db_file))
    with open(os.path.join(db_dir, "organism_dbs.txt"), "w") as out_handle:
        for org, fname in org_files:
            out_handle.write("%s\t%s\n" % (org, fname))

def read_org_list(in_file):
    with open(in_file, 'rU') as in_handle:
        reader = csv.reader(in_handle)
        orgs = [r[-1] for r in reader]
    return orgs

class _BaseRetrieval:
    def _make_blast_db(self, db_dir, final_file, db_name, organism):
        with _chdir(db_dir):
            if not os.path.exists("%s.pin" % db_name):
                cmd = self._config.get("blastdb_cmd", "makeblastdb")
                cl = [cmd, "-in", os.path.basename(final_file),
                      "-dbtype", "prot",
                      "-out", db_name,
                      "-title", organism]
                subprocess.check_call(cl)

class LocalRetrieval(_BaseRetrieval):
    """Prepare a database file from a local FASTA ref.
    """
    def __init__(self, config):
        self._config = config

    def retrieve_db(self, org, fname, db_dir):
        self._make_blast_db(os.path.dirname(fname), os.path.basename(fname),
                            os.path.splitext(os.path.basename(fname))[0], org)
        return os.path.splitext(fname.replace("%s/" % db_dir, ""))[0]

class NcbiEntrezRetrieval(_BaseRetrieval):
    """Pull down fasta protein genome sequences using NCBI Entrez.
    """
    def __init__(self, config):
        self._max_tries = 5
        self._config = config

    def retrieve_db(self, organism, db_dir):
        genome_ids = self._query_for_ids(organism)
        out_file = os.path.join(db_dir, "%s-entrez.fa" %
                organism.replace(" ", "_"))
        db_name = os.path.splitext(os.path.basename(out_file))[0]
        if not os.path.exists(out_file):
            num_tries = 1
            while 1:
                try:
                    self._download_and_error_out(out_file, genome_ids)
                    break
                except urllib2.URLError:
                    print "Timeout error"
                    time.sleep(5)
                    if num_tries > self._max_tries:
                        raise
                    else:
                        num_tries += 1
        self._make_blast_db(db_dir, os.path.basename(out_file), db_name,
                organism)
        return db_name

    def _download_and_error_out(self, out_file, genome_ids):
        """Do the full genome downloading, raising timeout errors to be handled.
        """
        with open(out_file, "w") as out_handle:
            for genome_id in genome_ids:
                print "Downloading", genome_id
                self._download_to_file(genome_id, out_handle)

    def _download_to_file(self, genome_id, out_handle):
        entrez_url = "http://www.ncbi.nlm.nih.gov/sites/entrez?Db=genome&" \
                     "Cmd=File&dopt=Protein+FASTA&list_uids=%s" % genome_id
        download_handle = urllib2.urlopen(entrez_url)
        # read off garbage at the beginning of the file related to the genome
        while 1:
            line = download_handle.readline()
            if line.startswith(">"):
                out_handle.write(line)
                break
            if not line:
                break
            print line
        for line in download_handle:
            out_handle.write(line)
        download_handle.close()
        # be sure output has trailing newlines. Who knows what could be there.
        out_handle.write("\n")

    def _query_for_ids(self, organism):
        handle = Entrez.esearch(db="genome", term="%s[Organism]" % organism)
        record = Entrez.read(handle)
        return record['IdList']

class EnsemblFtpRetrieval(_BaseRetrieval):
    """Handle obtaining a reference genome from Ensembl
    """
    def __init__(self, config):
        self._main_ftp = "ftp://ftp.ensembl.org/pub/current_fasta/"
        self._genome_ftp = "ftp://ftp.ensemblgenomes.org/pub/%s/current/fasta/"
        self._genome_dbs = ["bacteria", "protists", "metazoa", "fungi",
                "plants"]
        self._initialized = False
        self._config = config

    def _initialize(self):
        if not self._initialized:
            urls = [self._genome_ftp % d for d in self._genome_dbs] + \
                   [self._main_ftp]
            self._org_to_urls = dict()
            for url in urls:
                orgs = self._files_at_url(url)
                for org in orgs:
                    self._org_to_urls[org] = url
            self._initialized = True

    def _files_at_url(self, url):
        """Add organisms available at the provided FTP url.
        """
        parts = url.replace("ftp://", "").split("/")
        ftp = ftplib.FTP(parts[0])
        ftp.login()
        orgs = ftp.nlst("/".join(parts[1:]))
        return [o.split("/")[-1] for o in orgs]

    def retrieve_db(self, organism, db_dir):
        self._initialize()
        ftp_url = self._get_ftp_url(organism)
        if ftp_url is None:
            return ""
        file_name = ftp_url.split("/")[-1]
        final_file = os.path.join(db_dir, file_name.replace(".gz", ""))
        db_name = os.path.splitext(os.path.basename(final_file))[0]
        if not os.path.exists(final_file):
            with _chdir(db_dir):
                cl = ["wget", ftp_url]
                subprocess.check_call(cl)
                cl = ["gunzip", file_name]
                subprocess.check_call(cl)
        self._make_blast_db(db_dir, final_file, db_name, organism)
        return db_name

    def _get_ftp_url(self, organism):
        """Retrieve the protein database link for a given organism.
        """
        ftp_url = None
        org_parts = organism.split()
        for check_org in [organism.replace(" ", "_").lower(),
                "_".join([org_parts[0][0], org_parts[1]]).lower()]:
            try:
                ftp_url = self._org_to_urls[check_org]
                break
            except KeyError:
                pass
        if ftp_url:
            ftp_url = ftp_url + check_org + "/pep/"
            files = self._files_at_url(ftp_url)
            for f in files:
                if f.endswith("pep.all.fa.gz"):
                    ftp_url = ftp_url + f
                    break
        return ftp_url

@contextlib.contextmanager
def _chdir(new_dir):
    orig_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(orig_dir)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(*sys.argv[1:])
    else:
        print "Incorrect arguments"
        print __doc__
        sys.exit()

########NEW FILE########
__FILENAME__ = convert_library_dbkey
#!/usr/bin/env python
"""Convert all datasets in a Galaxy library to a specific organism.

This coverts the dbkey for datasets in a library to a new organism, and is
useful for bulk updates of pre-loaded libraries.

Usage:
    covert_library_dbkey.py <config ini file> <library name> <organism dbkey>
"""
import sys
import os
import tempfile
import ConfigParser

def main(ini_file, library_name, dbkey):
    sys.path.append(os.path.join(os.getcwd(), "lib"))
    app = get_galaxy_app(ini_file)

    #for library in app.model.Library.query():
    #    print library.name, library.deleted

    library = app.model.Library.query().filter_by(name=library_name,
            deleted=False).first()
    app.model.session.begin()
    for dataset in library.root_folder.datasets:
        print 'Assigning', dataset.library_dataset_dataset_association.name, \
                'to', dbkey
        #print dataset.library_dataset_dataset_association.dbkey
        dataset.library_dataset_dataset_association.dbkey = dbkey
    app.model.session.commit()

def get_galaxy_app(ini_file):
    import galaxy.app

    conf_parser = ConfigParser.ConfigParser({'here':os.getcwd()})
    conf_parser.read(ini_file)
    configuration = {}
    for key, value in conf_parser.items("app:main"):
        configuration[key] = value
    # If we don't load the tools, the app will startup much faster
    empty_xml = tempfile.NamedTemporaryFile()
    empty_xml.write( "<root/>" )
    empty_xml.flush()
    configuration['tool_config_file'] = empty_xml.name
    configuration['enable_job_running'] = False
    configuration['database_create_tables'] = False
    app = galaxy.app.UniverseApplication( global_conf = ini_file, **configuration )
    return app

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print __doc__
        sys.exit()
    main(*sys.argv[1:4])

########NEW FILE########
__FILENAME__ = galaxy_fabfile
"""Fabric deployment file to set up Galaxy plus associated data files.

Fabric (http://docs.fabfile.org) is used to manage the automation of
a remote server.

Usage:
    fab -f galaxy_fabfile.py servername deploy_galaxy
"""
import os
from contextlib import contextmanager

from fabric.api import *
from fabric.contrib.files import *

# -- Host specific setup for various groups of servers.

env.user = 'ubuntu'
env.install_ucsc = True
env.remove_old_genomes = False
env.use_sudo = False

def mothra():
    """Setup environment for mothra.
    """
    env.user = 'chapman'
    env.hosts = ['mothra']
    env.path = '/source/galaxy/web'
    env.galaxy_files = '/source/galaxy'
    env.install_dir = '/source'
    env.shell = "/bin/zsh -l -i -c"

def galaga():
    """Setup environment for galaga.
    """
    env.user = 'chapman'
    env.hosts = ['galaga']
    env.path = '/source/galaxy/web'
    env.galaxy_files = '/source/galaxy'
    env.install_dir = '/source'
    env.shell = "/bin/zsh -l -i -c"

def rcclu():
    """Setup environment for rcclu cluster. Pass in hosts on commandline.
    """
    env.user = "chapmanb"
    env.galaxy_files = "/solexa2/borowsky/tools/galaxy"
    env.install_dir = "/solexa2/borowsky/tools"
    env.shell = "/bin/bash -l -i -c"
    env.path = None

def localhost():
    """Setup environment for local authentication.
    """
    env.user = 'chapmanb'
    env.hosts = ['localhost']
    env.shell = '/usr/local/bin/bash -l -c'
    env.path = '/home/chapmanb/tmp/galaxy-central'

def amazon_ec2():
    """Setup for a ubuntu amazon ec2 share.

    Need to pass in host and private key file on commandline:
        -H hostname -i private_key_file
    """
    env.user = 'ubuntu'
    env.path = '/vol/galaxy/web'
    env.install_dir = '/usr/local'
    env.galaxy_files = '/vol/galaxy'
    env.shell = "/bin/bash -l -c"
    env.use_sudo = True

# -- Configuration for genomes to download and prepare

class _DownloadHelper:
    def _exists(self, fname, seq_dir):
        """Check if a file exists in either download or final destination.
        """
        return exists(fname) or exists(os.path.join(seq_dir, fname))

class UCSCGenome(_DownloadHelper):
    def __init__(self, genome_name):
        self._name = genome_name
        self._url = "ftp://hgdownload.cse.ucsc.edu/goldenPath/%s/bigZips" % \
                genome_name

    def download(self, seq_dir):
        for zipped_file in ["chromFa.tar.gz", "%s.fa.gz" % self._name,
                            "chromFa.zip"]:
            if not self._exists(zipped_file, seq_dir):
                with settings(warn_only=True):
                    result = run("wget %s/%s" % (self._url, zipped_file))
                if not result.failed:
                    break
            else:
                break
        genome_file = "%s.fa" % self._name
        if not self._exists(genome_file, seq_dir):
            if zipped_file.endswith(".tar.gz"):
                run("tar -xzpf %s" % zipped_file)
            elif zipped_file.endswith(".zip"):
                run("unzip %s" % zipped_file)
            elif zipped_file.endswith(".gz"):
                run("gunzip -c %s > out.fa" % zipped_file)
            else:
                raise ValueError("Do not know how to handle: %s" % zipped_file)
            tmp_file = genome_file.replace(".fa", ".txt")
            with settings(warn_only=True):
                result = run("ls *.fa")
            # some UCSC downloads have the files in multiple directories
            # mv them to the parent directory and delete the child directories
            #ignore_random = " -a \! -name '*_random.fa' -a \! -name 'chrUn*'" \
            #        "-a \! -name '*hap*.fa'"
            ignore_random = ""
            if result.failed:
                run("find . -name '*.fa'%s -exec mv {} . \;" % ignore_random)
                run("find . -type d -a \! -name '\.' | xargs rm -rf")
            result = run("find . -name '*.fa'%s" % ignore_random)
            result = result.split("\n")
            result.sort()
            run("cat %s > %s" % (" ".join(result), tmp_file))
            run("rm -f *.fa")
            run("mv %s %s" % (tmp_file, genome_file))
        return genome_file, [zipped_file]

class NCBIRest(_DownloadHelper):
    """Retrieve files using the TogoWS REST server pointed at NCBI.
    """
    def __init__(self, name, refs):
        self._name = name
        self._refs = refs
        self._base_url = "http://togows.dbcls.jp/entry/ncbi-nucleotide/%s.fasta"

    def download(self, seq_dir):
        genome_file = "%s.fa" % self._name
        if not self._exists(genome_file, seq_dir):
            for ref in self._refs:
                run("wget %s" % (self._base_url % ref))
                run("ls -l")
                run("sed -i.bak -r -e '/1/ s/^>.*$/>%s/g' %s.fasta" % (ref,
                    ref))
                # sed in Fabric does not cd properly?
                #sed('%s.fasta' % ref, '^>.*$', '>%s' % ref, '1')
            tmp_file = genome_file.replace(".fa", ".txt")
            run("cat *.fasta > %s" % tmp_file)
            run("rm -f *.fasta")
            run("rm -f *.bak")
            run("mv %s %s" % (tmp_file, genome_file))
        return genome_file, []

class EnsemblGenome(_DownloadHelper):
    """Retrieve genome FASTA files from Ensembl.

    ftp://ftp.ensemblgenomes.org/pub/plants/release-3/fasta/arabidopsis_thaliana/dna/Arabidopsis_thaliana.TAIR9.55.dna.toplevel.fa.gz
    ftp://ftp.ensembl.org/pub/release-56/fasta/caenorhabditis_elegans/dna/Caenorhabditis_elegans.WS200.56.dna.toplevel.fa.gz
    """
    def __init__(self, ensembl_section, release_number, release2, organism,
            name, convert_to_ucsc=False):
        if ensembl_section == "standard":
            url = "ftp://ftp.ensembl.org/pub/"
        else:
            url = "ftp://ftp.ensemblgenomes.org/pub/%s/" % ensembl_section
        url += "release-%s/fasta/%s/dna/" % (release_number, organism.lower())
        self._url = url
        self._get_file = "%s.%s.%s.dna.toplevel.fa.gz" % (organism, name,
                release2)
        self._name = name
        self._convert_to_ucsc = convert_to_ucsc

    def download(self, seq_dir):
        genome_file = "%s.fa" % self._name
        if not self._exists(self._get_file, seq_dir):
            run("wget %s%s" % (self._url, self._get_file))
        if not self._exists(genome_file, seq_dir):
            run("gunzip -c %s > %s" % (self._get_file, genome_file))
        if self._convert_to_ucsc:
            #run("sed s/ / /g %s" % genome_file)
            raise NotImplementedError("Replace with chr")
        return genome_file, [self._get_file]

genomes = [
           ("phiX174", "phix", NCBIRest("phix", ["NC_001422.1"])),
           ("Scerevisiae", "sacCer2", UCSCGenome("sacCer2")),
           ("Mmusculus", "mm9", UCSCGenome("mm9")),
           ("Mmusculus", "mm8", UCSCGenome("mm8")),
           ("Hsapiens", "hg18", UCSCGenome("hg18")),
           ("Hsapiens", "hg19", UCSCGenome("hg19")),
           ("Rnorvegicus", "rn4", UCSCGenome("rn4")),
           ("Xtropicalis", "xenTro2", UCSCGenome("xenTro2")),
           ("Athaliana", "araTha_tair9", EnsemblGenome("plants", "3", "55",
               "Arabidopsis_thaliana", "TAIR9")),
           ("Dmelanogaster", "dm3", UCSCGenome("dm3")),
           #("Dmelanogaster", "BDGP5.13", EnsemblGenome("metazoa", "4", "55",
           #    "Drosophila_melanogaster", "BDGP5.13", convert_to_ucsc=True),
           ("Celegans", "WS200", EnsemblGenome("standard", "56", "56",
               "Caenorhabditis_elegans", "WS200")),
           ("Mtuberculosis_H37Rv", "mycoTube_H37RV", NCBIRest("mycoTube_H37RV",
               ["NC_000962"])),
           ("Msmegmatis", "92", NCBIRest("92", ["NC_008596.1"])),
           ("Paeruginosa_UCBPP-PA14", "386", NCBIRest("386", ["CP000438.1"])),
           ("Ecoli", "eschColi_K12", NCBIRest("eschColi_K12", ["U00096.2"])),
           ("Amellifera_Honeybee", "apiMel3", UCSCGenome("apiMel3")),
           ("Cfamiliaris_Dog", "canFam2", UCSCGenome("canFam2")),
           ("Drerio_Zebrafish", "danRer6", UCSCGenome("danRer6")),
           ("Ecaballus_Horse", "equCab2", UCSCGenome("equCab2")),
           ("Fcatus_Cat", "felCat3", UCSCGenome("felCat3")),
           ("Ggallus_Chicken", "galGal3", UCSCGenome("galGal3")),
           ("Tguttata_Zebra_finch", "taeGut1", UCSCGenome("taeGut1")),
          ]

lift_over_genomes = ['hg18', 'hg19', 'mm9', 'xenTro2', 'rn4']

# -- Fabric instructions

def deploy_galaxy():
    """Deploy a Galaxy server along with associated data files.
    """
    _required_libraries()
    _support_programs()
    #latest_code()
    _setup_ngs_tools()
    _setup_liftover()

# == Decorators and context managers

def _if_not_installed(pname):
    def argcatcher(func):
        def decorator(*args, **kwargs):
            with settings(
                    hide('warnings', 'running', 'stdout', 'stderr'),
                    warn_only=True):
                result = run(pname)
            if result.return_code == 127:
                return func(*args, **kwargs)
        return decorator
    return argcatcher

def _if_installed(pname):
    """Run if the given program name is installed.
    """
    def argcatcher(func):
        def decorator(*args, **kwargs):
            with settings(
                    hide('warnings', 'running', 'stdout', 'stderr'),
                    warn_only=True):
                result = run(pname)
            if result.return_code not in [127]:
                return func(*args, **kwargs)
        return decorator
    return argcatcher

@contextmanager
def _make_tmp_dir():
    work_dir = os.path.join(env.galaxy_files, "tmp")
    if not exists(work_dir):
        run("mkdir %s" % work_dir)
    yield work_dir
    if exists(work_dir):
        run("rm -rf %s" % work_dir)

# == NGS

def _setup_ngs_tools():
    """Install next generation tools. Follows Galaxy docs at:

    http://bitbucket.org/galaxy/galaxy-central/wiki/NGSLocalSetup
    """
    _install_ngs_tools()
    _setup_ngs_genomes()

def _install_ngs_tools():
    """Install external next generation sequencing tools.
    """
    _install_bowtie()
    _install_bwa()
    _install_samtools()
    _install_fastx_toolkit()
    _install_maq()
    #_install_bfast()
    if env.install_ucsc:
        _install_ucsc_tools()

@_if_not_installed("faToTwoBit")
def _install_ucsc_tools():
    """Install useful executables from UCSC.
    """
    tools = ["liftOver", "faToTwoBit"]
    url = "http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/"
    install_dir = os.path.join(env.install_dir, "bin")
    for tool in tools:
        with cd(install_dir):
            if not exists(tool):
                install_cmd = sudo if env.use_sudo else run
                install_cmd("wget %s%s" % (url, tool))
                install_cmd("chmod a+rwx %s" % tool)

def _install_ucsc_tools_src():
    """Install Jim Kent's executables from source.
    """
    url = "http://hgdownload.cse.ucsc.edu/admin/jksrc.zip"
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s" % url)

@_if_not_installed("bowtie")
def _install_bowtie():
    """Install the bowtie short read aligner.
    """
    version = "0.12.5"
    mirror_info = "?use_mirror=cdnetworks-us-1"
    url = "http://downloads.sourceforge.net/project/bowtie-bio/bowtie/%s/" \
          "bowtie-%s-src.zip" % (version, version)
    install_dir = os.path.join(env.install_dir, "bin")
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s%s" % (url, mirror_info))
            run("unzip %s" % os.path.split(url)[-1])
            install_cmd = sudo if env.use_sudo else run
            with cd("bowtie-%s" % version):
                run("make")
                for fname in run("find -perm -100 -name 'bowtie*'").split("\n"):
                    install_cmd("mv -f %s %s" % (fname, install_dir))

@_if_not_installed("bwa")
def _install_bwa():
    version = "0.5.7"
    mirror_info = "?use_mirror=cdnetworks-us-1"
    url = "http://downloads.sourceforge.net/project/bio-bwa/bwa-%s.tar.bz2" % (
            version)
    install_dir = os.path.join(env.install_dir, "bin")
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s%s" % (url, mirror_info))
            run("tar -xjvpf %s" % (os.path.split(url)[-1]))
            install_cmd = sudo if env.use_sudo else run
            with cd("bwa-%s" % version):
                run("make")
                install_cmd("mv bwa %s" % install_dir)
                install_cmd("mv solid2fastq.pl %s" % install_dir)
                install_cmd("mv qualfa2fq.pl %s" % install_dir)

@_if_not_installed("samtools")
def _install_samtools():
    version = "0.1.7"
    vext = "a"
    mirror_info = "?use_mirror=cdnetworks-us-1"
    url = "http://downloads.sourceforge.net/project/samtools/samtools/%s/" \
            "samtools-%s%s.tar.bz2" % (version, version, vext)
    install_dir = os.path.join(env.install_dir, "bin")
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s%s" % (url, mirror_info))
            run("tar -xjvpf %s" % (os.path.split(url)[-1]))
            with cd("samtools-%s%s" % (version, vext)):
                run("sed -i.bak -r -e 's/-lcurses/-lncurses/g' Makefile")
                #sed("Makefile", "-lcurses", "-lncurses")
                run("make")
                install_cmd = sudo if env.use_sudo else run
                for install in ["samtools", "misc/maq2sam-long"]:
                    install_cmd("mv -f %s %s" % (install, install_dir))

@_if_not_installed("fastq_quality_boxplot_graph.sh")
def _install_fastx_toolkit():
    version = "0.0.13"
    gtext_version = "0.6"
    url_base = "http://hannonlab.cshl.edu/fastx_toolkit/"
    fastx_url = "%sfastx_toolkit-%s.tar.bz2" % (url_base, version)
    gtext_url = "%slibgtextutils-%s.tar.bz2" % (url_base, gtext_version)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s" % gtext_url)
            run("tar -xjvpf %s" % (os.path.split(gtext_url)[-1]))
            install_cmd = sudo if env.use_sudo else run
            with cd("libgtextutils-%s" % gtext_version):
                run("./configure --prefix=%s" % (env.install_dir))
                run("make")
                install_cmd("make install")
            run("wget %s" % fastx_url)
            run("tar -xjvpf %s" % os.path.split(fastx_url)[-1])
            with cd("fastx_toolkit-%s" % version):
                run("./configure --prefix=%s" % (env.install_dir))
                run("make")
                install_cmd("make install")

@_if_not_installed("maq")
def _install_maq():
    version = "0.7.1"
    mirror_info = "?use_mirror=cdnetworks-us-1"
    url = "http://downloads.sourceforge.net/project/maq/maq/%s/maq-%s.tar.bz2" \
            % (version, version)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s%s" % (url, mirror_info))
            run("tar -xjvpf %s" % (os.path.split(url)[-1]))
            install_cmd = sudo if env.use_sudo else run
            with cd("maq-%s" % version):
                run("./configure --prefix=%s" % (env.install_dir))
                run("make")
                install_cmd("make install")

@_if_not_installed("bfast")
def _install_bfast():
    version = "0.6.4"
    vext = "d"
    url = "http://downloads.sourceforge.net/project/bfast/bfast/%s/bfast-%s%s.tar.gz"\
            % (version, version, vext)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            run("wget %s" % (url))
            run("tar -xzvpf %s" % (os.path.split(url)[-1]))
            install_cmd = sudo if env.use_sudo else run
            with cd("bfast-%s%s" % (version, vext)):
                run("./configure --prefix=%s" % (env.install_dir))
                run("make")
                install_cmd("make install")

def _setup_ngs_genomes():
    """Download and create index files for next generation genomes.
    """
    genome_dir = os.path.join(env.galaxy_files, "genomes")
    if not exists(genome_dir):
        run('mkdir %s' % genome_dir)
    for organism, genome, manager in genomes:
        cur_dir = os.path.join(genome_dir, organism, genome)
        if not exists(cur_dir):
            run('mkdir -p %s' % cur_dir)
        with cd(cur_dir):
            if env.remove_old_genomes:
                _clean_genome_directory()
            seq_dir = 'seq'
            ref_file, base_zips = manager.download(seq_dir)
            ref_file = _move_seq_files(ref_file, base_zips, seq_dir)
            bwa_index = _index_bwa(ref_file)
            bowtie_index = _index_bowtie(ref_file)
            maq_index = _index_maq(ref_file)
            twobit_index = _index_twobit(ref_file)
            #bfast_index = _index_bfast(ref_file)
            if False:
                arachne_index = _index_arachne(ref_file)
                _index_eland(ref_file)
            with cd(seq_dir):
                sam_index = _index_sam(ref_file)
        for ref_index_file, cur_index, prefix in [
                ("sam_fa_indices.loc", sam_index, "index"),
                ("bowtie_indices.loc", bowtie_index, ""),
                ("bwa_index.loc", bwa_index, ""),
                ("alignseq.loc", twobit_index, "seq"),
                ("twobit.loc", twobit_index, ""),
                ]:
            if cur_index:
                str_parts = [genome, os.path.join(cur_dir, cur_index)]
                if prefix:
                    str_parts.insert(0, prefix)
                _update_loc_file(ref_index_file, str_parts)

def _clean_genome_directory():
    """Remove any existing sequence information in the current directory.
    """
    remove = ["arachne", "bowtie", "bwa", "maq", "seq", "ucsc"]
    for dirname in remove:
        if exists(dirname):
            run("rm -rf %s" % dirname)

def _move_seq_files(ref_file, base_zips, seq_dir):
    if not exists(seq_dir):
        run('mkdir %s' % seq_dir)
    for move_file in [ref_file] + base_zips:
        if exists(move_file):
            run("mv %s %s" % (move_file, seq_dir))
    path, fname = os.path.split(ref_file)
    moved_ref = os.path.join(path, seq_dir, fname)
    assert exists(moved_ref), moved_ref
    return moved_ref

def _update_loc_file(ref_file, line_parts):
    """Add a reference to the given genome to the base index file.
    """
    if env.path is not None:
        tools_dir = os.path.join(env.path, "tool-data")
        add_str = "\t".join(line_parts)
        with cd(tools_dir):
            if not exists(ref_file):
                run("cp %s.sample %s" % (ref_file, ref_file))
            if not contains(add_str, ref_file):
                append(add_str, ref_file)

@_if_installed("faToTwoBit")
def _index_twobit(ref_file):
    """Index reference files using 2bit for random access.
    """
    dir_name = "ucsc"
    ref_base = os.path.splitext(os.path.split(ref_file)[-1])[0]
    out_file = "%s.2bit" % ref_base
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
    with cd(dir_name):
        if not exists(out_file):
            run("faToTwoBit %s %s" % (os.path.join(os.pardir, ref_file),
                out_file))
    return os.path.join(dir_name, out_file)

def _index_bowtie(ref_file):
    dir_name = "bowtie"
    ref_base = os.path.splitext(os.path.split(ref_file)[-1])[0]
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        with cd(dir_name):
            run("bowtie-build -f %s %s" % (
                os.path.join(os.pardir, ref_file),
                ref_base))
    return os.path.join(dir_name, ref_base)

def _index_bwa(ref_file):
    dir_name = "bwa"
    local_ref = os.path.split(ref_file)[-1]
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        with cd(dir_name):
            run("ln -s %s" % os.path.join(os.pardir, ref_file))
            with settings(warn_only=True):
                result = run("bwa index -a bwtsw %s" % local_ref)
            # work around a bug in bwa indexing for small files
            if result.failed:
                run("bwa index %s" % local_ref)
            run("rm -f %s" % local_ref)
    return os.path.join(dir_name, local_ref)

def _index_maq(ref_file):
    dir_name = "maq"
    local_ref = os.path.split(ref_file)[-1]
    binary_out = "%s.bfa" % os.path.splitext(local_ref)[0]
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        with cd(dir_name):
            run("ln -s %s" % os.path.join(os.pardir, ref_file))
            run("maq fasta2bfa %s %s" % (local_ref,
                binary_out))
    return os.path.join(dir_name, binary_out)

def _index_sam(ref_file):
    (_, local_file) = os.path.split(ref_file)
    if not exists("%s.fai" % local_file):
        run("samtools faidx %s" % local_file)
    return ref_file

def _index_bfast(ref_file):
    """Indexes bfast in color and nucleotide space for longer reads.

    This preps for 40+bp sized reads, which is bfast's strength.
    """
    dir_name = "bfast"
    window_size = 14
    bfast_nt_masks = [
   "1111111111111111111111",
   "1111101110111010100101011011111",
   "1011110101101001011000011010001111111",
   "10111001101001100100111101010001011111",
   "11111011011101111011111111",
   "111111100101001000101111101110111",
   "11110101110010100010101101010111111",
   "111101101011011001100000101101001011101",
   "1111011010001000110101100101100110100111",
   "1111010010110110101110010110111011",
    ]
    bfast_color_masks = [
    "1111111111111111111111",
    "111110100111110011111111111",
    "10111111011001100011111000111111",
    "1111111100101111000001100011111011",
    "111111110001111110011111111",
    "11111011010011000011000110011111111",
    "1111111111110011101111111",
    "111011000011111111001111011111",
    "1110110001011010011100101111101111",
    "111111001000110001011100110001100011111",
    ]
    local_ref = os.path.split(ref_file)[-1]
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        with cd(dir_name):
            run("ln -s %s" % os.path.join(os.pardir, ref_file))
            # nucleotide space
            run("bfast fasta2brg -f %s -A 0" % local_ref)
            for i, mask in enumerate(bfast_nt_masks):
                run("bfast index -d 1 -n 4 -f %s -A 0 -m %s -w %s -i %s" %
                        (local_ref, mask, window_size, i + 1))
            # colorspace
            run("bfast fasta2brg -f %s -A 1" % local_ref)
            for i, mask in enumerate(bfast_color_masks):
                run("bfast index -d 1 -n 4 -f %s -A 1 -m %s -w %s -i %s" %
                        (local_ref, mask, window_size, i + 1))

@_if_installed("MakeLookupTable")
def _index_arachne(ref_file):
    """Index for Broad's Arachne aligner.
    """
    dir_name = "arachne"
    ref_base = os.path.splitext(os.path.split(ref_file)[-1])[0]
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        with cd(dir_name):
            run("ln -s %s" % os.path.join(os.pardir, ref_file))
            ref_file = os.path.split(ref_file)[-1]
            run("MakeLookupTable SOURCE=%s OUT_HEAD=%s" % (ref_file,
                ref_base))
            run("fastaHeaderSizes FASTA=%s HEADER_SIZES=%s.headerSizes" %
                    (ref_file, ref_file))
            #run("rm -f %s" % ref_file)
    return os.path.join(dir_name, ref_base)

@_if_installed("squashGenome")
def _index_eland(ref_file):
    """Index for Solexa's Eland aligner.

    This is nasty since Eland will choke on large files like the mm9 and h18
    genomes. It also has a restriction on only having 24 larger reference 
    files per directory. This indexes files with lots of shorter sequences (like
    xenopus) as one file, and splits up other files, removing random and other
    associated chromosomes to avoid going over the 24 file limit.
    """
    dir_name = "eland"
    if not exists(dir_name):
        run("mkdir %s" % dir_name)
        num_refs = run("grep '^>' %s | wc -l" % ref_file)
        # For a lot of reference sequences, Eland needs them in 1 file
        if int(num_refs) > 239:
            run("squashGenome %s %s" % (dir_name, ref_file))
        # For large reference sequences, squash fails and need them split up
        else:
            tmp_dir = "tmp_seqparts"
            run("mkdir %s" % tmp_dir)
            run("seqretsplit -sequence %s -osdirectory2 %s -outseq ." % 
                    (ref_file, tmp_dir))
            with cd(tmp_dir):
                result = run("ls *.fasta")
                result = result.split("\n")
            seq_files = [os.path.join(tmp_dir, f) for f in result]
            run("squashGenome %s %s" % (dir_name, " ".join(seq_files)))
            run("rm -rf %s" % tmp_dir)
            # Eland can only handle up to 24 reference files in a directory
            # If we have more, remove any with *random* in the name to get
            # below. This sucks, but seemingly no way around it because
            # Eland will choke on large reference files
            if int(num_refs) > 24:
                with cd(dir_name):
                    for remove_re in ["*random*", "*_hap*", "chrun_*"]:
                        with settings(warn_only=True):
                            run("rm -f %s" % remove_re)
                    new_count = run("ls | wc -l")
                    # Human is still too big, need to remove chromosome M
                    if int(new_count) // 2 > 24:
                        with settings(warn_only=True):
                            run("rm -f chrm*")

# == Liftover files

def _setup_liftover():
    """Download chain files for running liftOver.

    Does not install liftOver binaries automatically.
    """
    lo_dir = os.path.join(env.galaxy_files, "liftOver")
    if not exists(lo_dir):
        run("mkdir %s" % lo_dir)
    lo_base_url = "ftp://hgdownload.cse.ucsc.edu/goldenPath/%s/liftOver/%s"
    lo_base_file = "%sTo%s.over.chain.gz"
    for g1 in lift_over_genomes:
        for g2 in [g for g in lift_over_genomes if g != g1]:
            g2u = g2[0].upper() + g2[1:]
            cur_file = lo_base_file % (g1, g2u)
            non_zip = os.path.splitext(cur_file)[0]
            worked = False
            with cd(lo_dir):
                if not exists(non_zip):
                    with settings(warn_only=True):
                        result = run("wget %s" % (lo_base_url % (g1, cur_file)))
                    # Lift over back and forths don't always exist
                    # Only move forward if we found the file
                    if not result.failed:
                        worked = True
                        run("gunzip %s" % cur_file)
            if worked:
                ref_parts = [g1, g2, os.path.join(lo_dir, non_zip)]
                _update_loc_file("liftOver.loc", ref_parts)

def _required_libraries():
    """Install galaxy libraries not included in the eggs.
    """
    # -- HDF5
    # wget 'http://www.hdfgroup.org/ftp/HDF5/current/src/hdf5-1.8.4-patch1.tar.bz2'
    # tar -xjvpf hdf5-1.8.4-patch1.tar.bz2
    # ./configure --prefix=/source
    # make && make install
    #
    # -- PyTables http://www.pytables.org/moin
    # wget 'http://www.pytables.org/download/preliminary/pytables-2.2b3/tables-2.2b3.tar.gz'
    # tar -xzvpf tables-2.2b3.tar.gz
    # cd tables-2.2b3
    # python2.6 setup.py build --hdf5=/source
    # python2.6 setup.py install --hdf5=/source
    pass

def _support_programs():
    """Install programs used by galaxy.
    """
    pass
    # gnuplot
    # gcc44-fortran
    # R
    # rpy
    # easy_install gnuplot-py
    # emboss

def latest_code():
    """Pull the latest Galaxy code from bitbucket and update.
    """
    is_new = False
    if env.path is not None:
        if not exists(env.path):
            is_new = True
            with cd(os.path.split(env.path)[0]):
                run('hg clone https://chapmanb@bitbucket.org/chapmanb/galaxy-central/')
        with cd(env.path):
            run('hg pull')
            run('hg update')
            if is_new:
                run('sh setup.sh')
            else:
                run('sh manage_db.sh upgrade')

########NEW FILE########
__FILENAME__ = GFFOutput
"""Output Biopython SeqRecords and SeqFeatures to GFF3 format.

The target format is GFF3, the current GFF standard:
    http://www.sequenceontology.org/gff3.shtml
"""
import urllib

from Bio import SeqIO

class _IdHandler:
    """Generate IDs for GFF3 Parent/Child relationships where they don't exist.
    """
    def __init__(self):
        self._prefix = "biopygen"
        self._counter = 1
        self._seen_ids = []

    def _generate_id(self, quals):
        """Generate a unique ID not present in our existing IDs.
        """
        gen_id = self._get_standard_id(quals)
        if gen_id is None:
            while 1:
                gen_id = "%s%s" % (self._prefix, self._counter)
                if gen_id not in self._seen_ids:
                    break
                self._counter += 1
        return gen_id

    def _get_standard_id(self, quals):
        """Retrieve standardized IDs from other sources like NCBI GenBank.

        This tries to find IDs from known key/values when stored differently
        than GFF3 specifications.
        """
        possible_keys = ["transcript_id", "protein_id"]
        for test_key in possible_keys:
            if quals.has_key(test_key):
                cur_id = quals[test_key]
                if isinstance(cur_id, tuple) or isinstance(cur_id, list):
                    return cur_id[0]
                else:
                    return cur_id
        return None

    def update_quals(self, quals, has_children):
        """Update a set of qualifiers, adding an ID if necessary.
        """
        cur_id = quals.get("ID", None)
        # if we have an ID, record it
        if cur_id:
            if not isinstance(cur_id, list) and not isinstance(cur_id, tuple):
                cur_id = [cur_id]
            for add_id in cur_id:
                self._seen_ids.append(add_id)
        # if we need one and don't have it, create a new one
        elif has_children:
            new_id = self._generate_id(quals)
            self._seen_ids.append(new_id)
            quals["ID"] = [new_id]
        return quals

class GFF3Writer:
    """Write GFF3 files starting with standard Biopython objects.
    """
    def __init__(self):
        pass

    def write(self, recs, out_handle, include_fasta=False):
        """Write the provided records to the given handle in GFF3 format.
        """
        id_handler = _IdHandler()
        self._write_header(out_handle)
        fasta_recs = []
        try:
            recs = iter(recs)
        except TypeError:
            recs = [recs]
        for rec in recs:
            self._write_rec(rec, out_handle)
            self._write_annotations(rec.annotations, rec.id, len(rec.seq), out_handle)
            for sf in rec.features:
                sf = self._clean_feature(sf)
                id_handler = self._write_feature(sf, rec.id, out_handle,
                        id_handler)
            if include_fasta and len(rec.seq) > 0:
                fasta_recs.append(rec)
        if len(fasta_recs) > 0:
            self._write_fasta(fasta_recs, out_handle)

    def _clean_feature(self, feature):
        quals = {}
        for key, val in feature.qualifiers.items():
            if not isinstance(val, (list, tuple)):
                val = [val]
            val = [str(x) for x in val]
            quals[key] = val
        feature.qualifiers = quals
        clean_sub = [self._clean_feature(f) for f in feature.sub_features]
        feature.sub_features = clean_sub
        return feature

    def _write_rec(self, rec, out_handle):
        # if we have a SeqRecord, write out optional directive
        if len(rec.seq) > 0:
            out_handle.write("##sequence-region %s 1 %s\n" % (rec.id, len(rec.seq)))

    def _get_phase(self, feature):
        if feature.qualifiers.has_key("phase"):
            phase = feature.qualifiers["phase"][0]
        elif feature.type == "CDS":
            phase = int(feature.qualifiers.get("codon_start", [1])[0]) - 1
        else:
            phase = "."
        return str(phase)

    def _write_feature(self, feature, rec_id, out_handle, id_handler,
            parent_id=None):
        """Write a feature with location information.
        """
        if feature.strand == 1:
            strand = '+'
        elif feature.strand == -1:
            strand = '-'
        else:
            strand = '.'
        # remove any standard features from the qualifiers
        quals = feature.qualifiers.copy()
        for std_qual in ["source", "score", "phase"]:
            if quals.has_key(std_qual) and len(quals[std_qual]) == 1:
                del quals[std_qual]
        # add a link to a parent identifier if it exists
        if parent_id:
            if not quals.has_key("Parent"):
                quals["Parent"] = []
            quals["Parent"].append(parent_id)
        quals = id_handler.update_quals(quals, len(feature.sub_features) > 0)
        if feature.type:
            ftype = feature.type
        else:
            ftype = "sequence_feature"
        parts = [str(rec_id),
                 feature.qualifiers.get("source", ["feature"])[0],
                 ftype,
                 str(feature.location.nofuzzy_start + 1), # 1-based indexing
                 str(feature.location.nofuzzy_end),
                 feature.qualifiers.get("score", ["."])[0],
                 strand,
                 self._get_phase(feature),
                 self._format_keyvals(quals)]
        out_handle.write("\t".join(parts) + "\n")
        for sub_feature in feature.sub_features:
            id_handler = self._write_feature(sub_feature, rec_id, out_handle,
                    id_handler, quals["ID"][0])
        return id_handler

    def _format_keyvals(self, keyvals):
        format_kvs = []
        for key in sorted(keyvals.iterkeys()):
            values = keyvals[key]
            key = key.strip()
            format_vals = []
            if not isinstance(values, list) or isinstance(values, tuple):
                values = [values]
            for val in values:
                val = urllib.quote(str(val).strip(), safe=":/ ")
                if ((key and val) and val not in format_vals):
                    format_vals.append(val)
            format_kvs.append("%s=%s" % (key, ",".join(format_vals)))
        return ";".join(format_kvs)

    def _write_annotations(self, anns, rec_id, size, out_handle):
        """Add annotations which refer to an entire sequence.
        """
        format_anns = self._format_keyvals(anns)
        if format_anns:
            parts = [rec_id, "annotation", "remark", "1", str(size if size > 1 else 1),
                     ".", ".", ".", format_anns]
            out_handle.write("\t".join(parts) + "\n")

    def _write_header(self, out_handle):
        """Write out standard header directives.
        """
        out_handle.write("##gff-version 3\n")

    def _write_fasta(self, recs, out_handle):
        """Write sequence records using the ##FASTA directive.
        """
        out_handle.write("##FASTA\n")
        SeqIO.write(recs, out_handle, "fasta")

def write(recs, out_handle, include_fasta=False):
    """High level interface to write GFF3 files from SeqRecords and SeqFeatures.

    If include_fasta is True, the GFF3 file will include sequence information
    using the ##FASTA directive.
    """
    writer = GFF3Writer()
    return writer.write(recs, out_handle, include_fasta)

########NEW FILE########
__FILENAME__ = GFFParser
"""Parse GFF files into features attached to Biopython SeqRecord objects.

This deals with GFF3 formatted files, a tab delimited format for storing
sequence features and annotations:

http://www.sequenceontology.org/gff3.shtml

It will also deal with older GFF versions (GTF/GFF2):

http://www.sanger.ac.uk/Software/formats/GFF/GFF_Spec.shtml
http://mblab.wustl.edu/GTF22.html

The implementation utilizes map/reduce parsing of GFF using Disco. Disco
(http://discoproject.org) is a Map-Reduce framework for Python utilizing
Erlang for parallelization. The code works on a single processor without
Disco using the same architecture.
"""
import os
import copy
import re
import collections
import urllib
import itertools

# Make defaultdict compatible with versions of python older than 2.4
try:
    collections.defaultdict
except AttributeError:
    import _utils
    collections.defaultdict = _utils.defaultdict

from Bio.Seq import UnknownSeq
from Bio.SeqRecord import SeqRecord
from Bio import SeqFeature
from Bio import SeqIO

def _gff_line_map(line, params):
    """Map part of Map-Reduce; parses a line of GFF into a dictionary.

    Given an input line from a GFF file, this:
    - decides if the file passes our filtering limits
    - if so:
        - breaks it into component elements
        - determines the type of attribute (flat, parent, child or annotation)
        - generates a dictionary of GFF info which can be serialized as JSON
    """
    def _merge_keyvals(parts):
        """Merge key-values escaped by quotes that are improperly split at semicolons.
        """
        out = []
        for i, p in enumerate(parts):
            if i > 0 and len(p) == 1 and p[0].endswith('"') and not p[0].startswith('"'):
                if out[-1][-1].startswith('"'):
                    prev_p = out.pop(-1)
                    to_merge = prev_p[-1]
                    prev_p[-1] = "%s; %s" % (to_merge, p[0])
                    out.append(prev_p)
            else:
                out.append(p)
        return out

    gff3_kw_pat = re.compile("\w+=")
    def _split_keyvals(keyval_str):
        """Split key-value pairs in a GFF2, GTF and GFF3 compatible way.

        GFF3 has key value pairs like:
          count=9;gene=amx-2;sequence=SAGE:aacggagccg
        GFF2 and GTF have:           
          Sequence "Y74C9A" ; Note "Clone Y74C9A; Genbank AC024206"
          name "fgenesh1_pg.C_chr_1000003"; transcriptId 869
        """
        quals = collections.defaultdict(list)
        if keyval_str is None:
            return quals
        # ensembl GTF has a stray semi-colon at the end
        if keyval_str[-1] == ';':
            keyval_str = keyval_str[:-1]
        # GFF2/GTF has a semi-colon with at least one space after it.
        # It can have spaces on both sides; wormbase does this.
        # GFF3 works with no spaces.
        # Split at the first one we can recognize as working
        parts = keyval_str.split(" ; ")
        if len(parts) == 1:
            parts = [x.strip() for x in keyval_str.split(";")]
        # check if we have GFF3 style key-vals (with =)
        is_gff2 = True
        if gff3_kw_pat.match(parts[0]):
            is_gff2 = False
            key_vals = _merge_keyvals([p.split('=') for p in parts])
        # otherwise, we are separated by a space with a key as the first item
        else:
            pieces = []
            for p in parts:
                # fix misplaced semi-colons in keys in some GFF2 files
                if p and p[0] == ';':
                    p = p[1:]
                pieces.append(p.strip().split(" "))
            key_vals = [(p[0], " ".join(p[1:])) for p in pieces]
        for item in key_vals:
            # standard in-spec items are key=value
            if len(item) == 2:
                key, val = item
            # out-of-spec files can have just key values. We set an empty value
            # which will be changed to true later to standardize.
            else:
                assert len(item) == 1, item
                key = item[0]
                val = ''
            # remove quotes in GFF2 files
            quoted = False
            if (len(val) > 0 and val[0] == '"' and val[-1] == '"'):
                quoted = True
                val = val[1:-1]
            if val:
                if quoted:
                    quals[key].append(val)
                else:
                    quals[key].extend([v for v in val.split(',') if v])
            # if we don't have a value, make this a key=True/False style
            # attribute
            else:
                quals[key].append('true')
        for key, vals in quals.items():
            quals[key] = [urllib.unquote(v) for v in vals]
        return quals, is_gff2

    def _nest_gff2_features(gff_parts):
        """Provide nesting of GFF2 transcript parts with transcript IDs.

        exons and coding sequences are mapped to a parent with a transcript_id
        in GFF2. This is implemented differently at different genome centers
        and this function attempts to resolve that and map things to the GFF3
        way of doing them.
        """
        # map protein or transcript ids to a parent
        for transcript_id in ["transcript_id", "transcriptId", "proteinId"]:
            try:
                gff_parts["quals"]["Parent"] = \
                        gff_parts["quals"][transcript_id]
                break
            except KeyError:
                pass
        # case for WormBase GFF -- everything labelled as Transcript or CDS
        for flat_name in ["Transcript", "CDS"]:
            if gff_parts["quals"].has_key(flat_name):
                # parent types
                if gff_parts["type"] in [flat_name]:
                    if not gff_parts["id"]:
                        gff_parts["id"] = gff_parts["quals"][flat_name][0]
                        gff_parts["quals"]["ID"] = [gff_parts["id"]]
                # children types
                elif gff_parts["type"] in ["intron", "exon", "three_prime_UTR",
                        "coding_exon", "five_prime_UTR", "CDS", "stop_codon",
                        "start_codon"]:
                    gff_parts["quals"]["Parent"] = gff_parts["quals"][flat_name]
                break

        return gff_parts

    strand_map = {'+' : 1, '-' : -1, '?' : None, None: None}
    line = line.strip()
    if line[:2] == "##":
        return [('directive', line[2:])]
    elif line and line[0] != "#":
        parts = line.split('\t')
        should_do = True
        if params.limit_info:
            for limit_name, limit_values in params.limit_info.items():
                cur_id = tuple([parts[i] for i in 
                    params.filter_info[limit_name]])
                if cur_id not in limit_values:
                    should_do = False
                    break
        if should_do:
            assert len(parts) >= 8, line
            # not python2.4 compatible but easier to understand
            #gff_parts = [(None if p == '.' else p) for p in parts]
            gff_parts = []
            for p in parts:
                if p == ".":
                    gff_parts.append(None)
                else:
                    gff_parts.append(p)
            gff_info = dict()
            # collect all of the base qualifiers for this item
            if len(parts) > 8:
                quals, is_gff2 = _split_keyvals(gff_parts[8])
            else:
                quals, is_gff2 = collections.defaultdict(list), False
            gff_info["is_gff2"] = is_gff2
            if gff_parts[1]:
                quals["source"].append(gff_parts[1])
            if gff_parts[5]:
                quals["score"].append(gff_parts[5])
            if gff_parts[7]:
                quals["phase"].append(gff_parts[7])
            gff_info['quals'] = dict(quals)
            gff_info['rec_id'] = gff_parts[0]
            # if we are describing a location, then we are a feature
            if gff_parts[3] and gff_parts[4]:
                gff_info['location'] = [int(gff_parts[3]) - 1,
                        int(gff_parts[4])]
                gff_info['type'] = gff_parts[2]
                gff_info['id'] = quals.get('ID', [''])[0]
                gff_info['strand'] = strand_map.get(gff_parts[6], None)
                if is_gff2:
                    gff_info = _nest_gff2_features(gff_info)
                # features that have parents need to link so we can pick up
                # the relationship
                if gff_info['quals'].has_key('Parent'):
                    # check for self referential parent/child relationships
                    # remove the ID, which is not useful
                    for p in gff_info['quals']['Parent']:
                        if p == gff_info['id']:
                            gff_info['id'] = ''
                            del gff_info['quals']['ID']
                            break
                    final_key = 'child'
                elif gff_info['id']:
                    final_key = 'parent'
                # Handle flat features
                else:
                    final_key = 'feature'
            # otherwise, associate these annotations with the full record
            else:
                final_key = 'annotation'
            if params.jsonify:
                return [(final_key, simplejson.dumps(gff_info))]
            else:
                return [(final_key, gff_info)]
    return []

def _gff_line_reduce(map_results, out, params):
    """Reduce part of Map-Reduce; combines results of parsed features.
    """
    final_items = dict()
    for gff_type, final_val in map_results:
        if params.jsonify and gff_type not in ['directive']:
            final_val = simplejson.loads(final_val)
        try:
            final_items[gff_type].append(final_val)
        except KeyError:
            final_items[gff_type] = [final_val]
    for key, vals in final_items.items():
        if params.jsonify:
            vals = simplejson.dumps(vals)
        out.add(key, vals)

class _MultiIDRemapper:
    """Provide an ID remapping for cases where a parent has a non-unique ID.

    Real life GFF3 cases have non-unique ID attributes, which we fix here
    by using the unique sequence region to assign children to the right
    parent.
    """
    def __init__(self, base_id, all_parents):
        self._base_id = base_id
        self._parents = all_parents

    def remap_id(self, feature_dict):
        rstart, rend = feature_dict['location']
        for index, parent in enumerate(self._parents):
            pstart, pend = parent['location']
            if rstart >= pstart and rend <= pend:
                if index > 0:
                    return ("%s_%s" % (self._base_id, index + 1))
                else:
                    return self._base_id
        raise ValueError("Did not find remapped ID location: %s, %s, %s" % (
                self._base_id, [p['location'] for p in self._parents],
                feature_dict['location']))

class _AbstractMapReduceGFF:
    """Base class providing general GFF parsing for local and remote classes.

    This class should be subclassed to provide a concrete class to parse
    GFF under specific conditions. These classes need to implement
    the _gff_process function, which returns a dictionary of SeqRecord
    information.
    """
    def __init__(self, create_missing=True):
        """Initialize GFF parser 

        create_missing - If True, create blank records for GFF ids not in
        the base_dict. If False, an error will be raised.
        """
        self._create_missing = create_missing
        self._map_fn = _gff_line_map
        self._reduce_fn = _gff_line_reduce
        self._examiner = GFFExaminer()

    def _gff_process(self, gff_files, limit_info, target_lines=None):
        raise NotImplementedError("Derived class must define")

    def parse(self, gff_files, base_dict=None, limit_info=None):
        """Parse a GFF file, returning an iterator of SeqRecords.

        limit_info - A dictionary specifying the regions of the GFF file
        which should be extracted. This allows only relevant portions of a file
        to be parsed.
        
        base_dict - A base dictionary of SeqRecord objects which may be
        pre-populated with sequences and other features. The new features from
        the GFF file will be added to this dictionary.
        """
        for rec in self.parse_in_parts(gff_files, base_dict, limit_info):
            yield rec

    def parse_in_parts(self, gff_files, base_dict=None, limit_info=None,
            target_lines=None):
        """Parse a region of a GFF file specified, returning info as generated.

        target_lines -- The number of lines in the file which should be used
        for each partial parse. This should be determined based on available
        memory.
        """
        for results in self.parse_simple(gff_files, limit_info, target_lines):
            if base_dict is None:
                cur_dict = dict()
            else:
                cur_dict = copy.deepcopy(base_dict)
            cur_dict = self._results_to_features(cur_dict, results)
            all_ids = cur_dict.keys()
            all_ids.sort()
            for cur_id in all_ids:
                yield cur_dict[cur_id]

    def parse_simple(self, gff_files, limit_info=None, target_lines=1):
        """Simple parse which does not build or nest features.

        This returns a simple dictionary representation of each line in the
        GFF file.
        """
        # gracefully handle a single file passed
        if not isinstance(gff_files, (list, tuple)):
            gff_files = [gff_files]
        limit_info = self._normalize_limit_info(limit_info)
        for results in self._gff_process(gff_files, limit_info, target_lines):
            yield results

    def _normalize_limit_info(self, limit_info):
        """Turn all limit information into tuples for identical comparisons.
        """
        final_limit_info = {}
        if limit_info:
            for key, values in limit_info.items():
                final_limit_info[key] = []
                for v in values:
                    if isinstance(v, str):
                        final_limit_info[key].append((v,))
                    else:
                        final_limit_info[key].append(tuple(v))
        return final_limit_info

    def _results_to_features(self, base, results):
        """Add parsed dictionaries of results to Biopython SeqFeatures.
        """
        base = self._add_annotations(base, results.get('annotation', []))
        for feature in results.get('feature', []):
            (_, base) = self._add_toplevel_feature(base, feature)
        base = self._add_parent_child_features(base, results.get('parent', []),
                results.get('child', []))
        base = self._add_seqs(base, results.get('fasta', []))
        base = self._add_directives(base, results.get('directive', []))
        return base

    def _add_directives(self, base, directives):
        """Handle any directives or meta-data in the GFF file.

        Relevant items are added as annotation meta-data to each record.
        """
        dir_keyvals = collections.defaultdict(list)
        for directive in directives:
            parts = directive.split()
            if len(parts) > 1:
                key = parts[0]
                if len(parts) == 2:
                    val = parts[1]
                else:
                    val = tuple(parts[1:])
                # specific directives that need special handling
                if key == "sequence-region": # convert to Python 0-based coordinates
                    val = (val[0], int(val[1]) - 1, int(val[2]))
                dir_keyvals[key].append(val)
        for key, vals in dir_keyvals.items():
            for rec in base.values():
                self._add_ann_to_rec(rec, key, vals)
        return base

    def _add_seqs(self, base, recs):
        """Add sequence information contained in the GFF3 to records.
        """
        for rec in recs:
            if base.has_key(rec.id):
                base[rec.id].seq = rec.seq
            else:
                base[rec.id] = rec
        return base
    
    def _add_parent_child_features(self, base, parents, children):
        """Add nested features with parent child relationships.
        """
        multi_remap = self._identify_dup_ids(parents)
        # add children features
        children_prep = collections.defaultdict(list)
        for child_dict in children:
            child_feature = self._get_feature(child_dict)
            for pindex, pid in enumerate(child_feature.qualifiers['Parent']):
                if multi_remap.has_key(pid):
                    pid = multi_remap[pid].remap_id(child_dict)
                    child_feature.qualifiers['Parent'][pindex] = pid
                children_prep[pid].append((child_dict['rec_id'],
                    child_feature))
        children = dict(children_prep)
        # add children to parents that exist
        for cur_parent_dict in parents:
            cur_id = cur_parent_dict['id']
            if multi_remap.has_key(cur_id):
                cur_parent_dict['id'] = multi_remap[cur_id].remap_id(
                        cur_parent_dict)
            cur_parent, base = self._add_toplevel_feature(base, cur_parent_dict)
            cur_parent, children = self._add_children_to_parent(cur_parent,
                    children)
        # create parents for children without them (GFF2 or split/bad files)
        while len(children) > 0:
            parent_id, cur_children = itertools.islice(children.items(),
                    1).next()
            # one child, do not nest it
            if len(cur_children) == 1:
                rec_id, child = cur_children[0]
                loc = (child.location.nofuzzy_start, child.location.nofuzzy_end)
                rec, base = self._get_rec(base,
                        dict(rec_id=rec_id, location=loc))
                rec.features.append(child)
                del children[parent_id]
            else:
                cur_parent, base = self._add_missing_parent(base, parent_id,
                        cur_children)
                cur_parent, children = self._add_children_to_parent(cur_parent,
                        children)
        return base

    def _identify_dup_ids(self, parents):
        """Identify duplicated ID attributes in potential nested parents.

        According to the GFF3 spec ID attributes are supposed to be unique
        for a file, but this is not always true in practice. This looks
        for duplicates, and provides unique IDs sorted by locations.
        """
        multi_ids = collections.defaultdict(list)
        for parent in parents:
            multi_ids[parent['id']].append(parent)
        multi_ids = [(mid, ps) for (mid, ps) in multi_ids.items()
                     if len(parents) > 1]
        multi_remap = dict()
        for mid, parents in multi_ids:
            multi_remap[mid] = _MultiIDRemapper(mid, parents)
        return multi_remap

    def _add_children_to_parent(self, cur_parent, children):
        """Recursively add children to parent features.
        """
        if children.has_key(cur_parent.id):
            cur_children = children[cur_parent.id]
            ready_children = []
            for _, cur_child in cur_children:
                cur_child, _ = self._add_children_to_parent(cur_child, children)
                ready_children.append(cur_child)
            # Support Biopython features for 1.62+ CompoundLocations and pre-1.62
            if not hasattr(SeqFeature, "CompoundLocation"):
                cur_parent.location_operator = "join"
            for cur_child in ready_children:
                cur_parent.sub_features.append(cur_child)
            del children[cur_parent.id]
        return cur_parent, children

    def _add_annotations(self, base, anns):
        """Add annotation data from the GFF file to records.
        """
        # add these as a list of annotations, checking not to overwrite
        # current values
        for ann in anns:
            rec, base = self._get_rec(base, ann)
            for key, vals in ann['quals'].items():
                self._add_ann_to_rec(rec, key, vals)
        return base

    def _add_ann_to_rec(self, rec, key, vals):
        """Add a key/value annotation to the given SeqRecord.
        """
        if rec.annotations.has_key(key):
            try:
                rec.annotations[key].extend(vals)
            except AttributeError:
                rec.annotations[key] = [rec.annotations[key]] + vals
        else:
            rec.annotations[key] = vals

    def _get_rec(self, base, info_dict):
        """Retrieve a record to add features to.
        """
        max_loc = info_dict.get('location', (0, 1))[1]
        try:
            cur_rec = base[info_dict['rec_id']]
            # update generated unknown sequences with the expected maximum length
            if isinstance(cur_rec.seq, UnknownSeq):
                cur_rec.seq._length = max([max_loc, cur_rec.seq._length])
            return cur_rec, base
        except KeyError:
            if self._create_missing:
                new_rec = SeqRecord(UnknownSeq(max_loc), info_dict['rec_id'])
                base[info_dict['rec_id']] = new_rec
                return new_rec, base
            else:
                raise

    def _add_missing_parent(self, base, parent_id, cur_children):
        """Add a new feature that is missing from the GFF file.
        """
        base_rec_id = list(set(c[0] for c in cur_children))
        assert len(base_rec_id) == 1
        feature_dict = dict(id=parent_id, strand=None,
                type="inferred_parent", quals=dict(ID=[parent_id]),
                rec_id=base_rec_id[0])
        coords = [(c.location.nofuzzy_start, c.location.nofuzzy_end) 
                for r, c in cur_children]
        feature_dict["location"] = (min([c[0] for c in coords]),
                max([c[1] for c in coords]))
        return self._add_toplevel_feature(base, feature_dict)

    def _add_toplevel_feature(self, base, feature_dict):
        """Add a toplevel non-nested feature to the appropriate record.
        """
        new_feature = self._get_feature(feature_dict)
        rec, base = self._get_rec(base, feature_dict)
        rec.features.append(new_feature)
        return new_feature, base

    def _get_feature(self, feature_dict):
        """Retrieve a Biopython feature from our dictionary representation.
        """
        location = SeqFeature.FeatureLocation(*feature_dict['location'])
        new_feature = SeqFeature.SeqFeature(location, feature_dict['type'],
                id=feature_dict['id'], strand=feature_dict['strand'])
        new_feature.qualifiers = feature_dict['quals']
        return new_feature

    def _parse_fasta(self, in_handle):
        """Parse FASTA sequence information contained in the GFF3 file.
        """
        return list(SeqIO.parse(in_handle, "fasta"))

class _GFFParserLocalOut:
    """Provide a collector for local GFF MapReduce file parsing.
    """
    def __init__(self, smart_breaks=False):
        self._items = dict()
        self._smart_breaks = smart_breaks
        self._missing_keys = collections.defaultdict(int)
        self._last_parent = None
        self.can_break = True
        self.num_lines = 0

    def add(self, key, vals):
        if self._smart_breaks:
            # if we are not GFF2 we expect parents and break
            # based on not having missing ones
            if key == 'directive':
                if vals[0] == '#':
                    self.can_break = True
                self._last_parent = None
            elif not vals[0].get("is_gff2", False):
                self._update_missing_parents(key, vals)
                self.can_break = (len(self._missing_keys) == 0)
            # break when we are done with stretches of child features
            elif key != 'child':
                self.can_break = True
                self._last_parent = None
            # break when we have lots of child features in a row
            # and change between parents
            else:
                cur_parent = vals[0]["quals"]["Parent"][0]
                if (self._last_parent):
                    self.can_break = (cur_parent != self._last_parent)
                self._last_parent = cur_parent
        self.num_lines += 1
        try:
            self._items[key].extend(vals)
        except KeyError:
            self._items[key] = vals

    def _update_missing_parents(self, key, vals):
        # smart way of deciding if we can break this.
        # if this is too much, can go back to not breaking in the
        # middle of children
        if key in ["child"]:
            for val in vals:
                for p_id in val["quals"]["Parent"]:
                    self._missing_keys[p_id] += 1
        for val in vals:
            try:
                del self._missing_keys[val["quals"]["ID"][0]]
            except KeyError:
                pass

    def has_items(self):
        return len(self._items) > 0

    def get_results(self):
        self._last_parent = None
        return self._items

class GFFParser(_AbstractMapReduceGFF):
    """Local GFF parser providing standardized parsing of GFF3 and GFF2 files.
    """
    def __init__(self, line_adjust_fn=None, create_missing=True):
        _AbstractMapReduceGFF.__init__(self, create_missing=create_missing)
        self._line_adjust_fn = line_adjust_fn
    
    def _gff_process(self, gff_files, limit_info, target_lines):
        """Process GFF addition without any parallelization.

        In addition to limit filtering, this accepts a target_lines attribute
        which provides a number of lines to parse before returning results.
        This allows partial parsing of a file to prevent memory issues.
        """
        line_gen = self._file_line_generator(gff_files)
        for out in self._lines_to_out_info(line_gen, limit_info, target_lines):
            yield out

    def _file_line_generator(self, gff_files):
        """Generate single lines from a set of GFF files.
        """
        for gff_file in gff_files:
            if hasattr(gff_file, "read"):
                need_close = False
                in_handle = gff_file
            else:
                need_close = True
                in_handle = open(gff_file)
            while 1:
                line = in_handle.readline()
                if not line:
                    break
                yield line
            if need_close:
                in_handle.close()

    def _lines_to_out_info(self, line_iter, limit_info=None,
            target_lines=None):
        """Generate SeqRecord and SeqFeatures from GFF file lines.
        """
        params = self._examiner._get_local_params(limit_info)
        out_info = _GFFParserLocalOut((target_lines is not None and
                target_lines > 1))
        found_seqs = False
        for line in line_iter:
            results = self._map_fn(line, params)
            if self._line_adjust_fn and results:
                if results[0][0] not in ['directive']:
                    results = [(results[0][0],
                        self._line_adjust_fn(results[0][1]))]
            self._reduce_fn(results, out_info, params)
            if (target_lines and out_info.num_lines >= target_lines and
                    out_info.can_break):
                yield out_info.get_results()
                out_info = _GFFParserLocalOut((target_lines is not None and
                        target_lines > 1))
            if (results and results[0][0] == 'directive' and 
                    results[0][1] == 'FASTA'):
                found_seqs = True
                break

        class FakeHandle:
            def __init__(self, line_iter):
                self._iter = line_iter
            def read(self):
                return "".join(l for l in self._iter)
            def readline(self):
                try:
                    return self._iter.next()
                except StopIteration:
                    return ""

        if found_seqs:
            fasta_recs = self._parse_fasta(FakeHandle(line_iter))
            out_info.add('fasta', fasta_recs)
        if out_info.has_items():
            yield out_info.get_results()

class DiscoGFFParser(_AbstractMapReduceGFF):
    """GFF Parser with parallelization through Disco (http://discoproject.org.
    """
    def __init__(self, disco_host, create_missing=True):
        """Initialize parser.
        
        disco_host - Web reference to a Disco host which will be used for
        parallelizing the GFF reading job.
        """
        _AbstractMapReduceGFF.__init__(self, create_missing=create_missing)
        self._disco_host = disco_host

    def _gff_process(self, gff_files, limit_info, target_lines=None):
        """Process GFF addition, using Disco to parallelize the process.
        """
        assert target_lines is None, "Cannot split parallelized jobs"
        # make these imports local; only need them when using disco
        import simplejson
        import disco
        # absolute path names unless they are special disco files 
        full_files = []
        for f in gff_files:
            if f.split(":")[0] != "disco":
                full_files.append(os.path.abspath(f))
            else:
                full_files.append(f)
        results = disco.job(self._disco_host, name="gff_reader",
                input=full_files,
                params=disco.Params(limit_info=limit_info, jsonify=True,
                    filter_info=self._examiner._filter_info),
                required_modules=["simplejson", "collections", "re"],
                map=self._map_fn, reduce=self._reduce_fn)
        processed = dict()
        for out_key, out_val in disco.result_iterator(results):
            processed[out_key] = simplejson.loads(out_val)
        yield processed

def parse(gff_files, base_dict=None, limit_info=None, target_lines=None):
    """High level interface to parse GFF files into SeqRecords and SeqFeatures.
    """
    parser = GFFParser()
    for rec in parser.parse_in_parts(gff_files, base_dict, limit_info,
            target_lines):
        yield rec

def parse_simple(gff_files, limit_info=None):
    """Parse GFF files as line by line dictionary of parts.
    """
    parser = GFFParser()
    for rec in parser.parse_simple(gff_files, limit_info=limit_info):
        if "child" in rec:
            assert "parent" not in rec
            yield rec["child"][0]
        elif "parent" in rec:
            yield rec["parent"][0]
        # ignore directive lines
        else:
            assert "directive" in rec

def _file_or_handle(fn):
    """Decorator to handle either an input handle or a file.
    """
    def _file_or_handle_inside(*args, **kwargs):
        in_file = args[1]
        if hasattr(in_file, "read"):
            need_close = False
            in_handle = in_file
        else:
            need_close = True
            in_handle = open(in_file)
        args = (args[0], in_handle) + args[2:]
        out = fn(*args, **kwargs)
        if need_close:
            in_handle.close()
        return out
    return _file_or_handle_inside

class GFFExaminer:
    """Provide high level details about a GFF file to refine parsing.

    GFF is a spec and is provided by many different centers. Real life files
    will present the same information in slightly different ways. Becoming
    familiar with the file you are dealing with is the best way to extract the
    information you need. This class provides high level summary details to
    help in learning.
    """
    def __init__(self):
        self._filter_info = dict(gff_id = [0], gff_source_type = [1, 2],
                gff_source = [1], gff_type = [2])
    
    def _get_local_params(self, limit_info=None):
        class _LocalParams:
            def __init__(self):
                self.jsonify = False
        params = _LocalParams()
        params.limit_info = limit_info
        params.filter_info = self._filter_info
        return params
    
    @_file_or_handle
    def available_limits(self, gff_handle):
        """Return dictionary information on possible limits for this file.

        This returns a nested dictionary with the following structure:
        
        keys -- names of items to filter by
        values -- dictionary with:
            keys -- filter choice
            value -- counts of that filter in this file

        Not a parallelized map-reduce implementation.
        """
        cur_limits = dict()
        for filter_key in self._filter_info.keys():
            cur_limits[filter_key] = collections.defaultdict(int)
        for line in gff_handle:
            # when we hit FASTA sequences, we are done with annotations
            if line.startswith("##FASTA"):
                break
            # ignore empty and comment lines
            if line.strip() and line.strip()[0] != "#":
                parts = [p.strip() for p in line.split('\t')]
                assert len(parts) >= 8, line
                parts = parts[:9]
                for filter_key, cur_indexes in self._filter_info.items():
                    cur_id = tuple([parts[i] for i in cur_indexes])
                    cur_limits[filter_key][cur_id] += 1
        # get rid of the default dicts
        final_dict = dict()
        for key, value_dict in cur_limits.items():
            if len(key) == 1:
                key = key[0]
            final_dict[key] = dict(value_dict)
        gff_handle.close()
        return final_dict

    @_file_or_handle
    def parent_child_map(self, gff_handle):
        """Provide a mapping of parent to child relationships in the file.

        Returns a dictionary of parent child relationships:

        keys -- tuple of (source, type) for each parent
        values -- tuple of (source, type) as children of that parent
        
        Not a parallelized map-reduce implementation.
        """
        # collect all of the parent and child types mapped to IDs
        parent_sts = dict()
        child_sts = collections.defaultdict(list)
        for line in gff_handle:
            # when we hit FASTA sequences, we are done with annotations
            if line.startswith("##FASTA"):
                break
            if line.strip() and not line.startswith("#"):
                line_type, line_info = _gff_line_map(line,
                        self._get_local_params())[0]
                if (line_type == 'parent' or (line_type == 'child' and
                        line_info['id'])):
                    parent_sts[line_info['id']] = (
                            line_info['quals'].get('source', [""])[0], line_info['type'])
                if line_type == 'child':
                    for parent_id in line_info['quals']['Parent']:
                        child_sts[parent_id].append((
                            line_info['quals'].get('source', [""])[0], line_info['type']))
        #print parent_sts, child_sts
        # generate a dictionary of the unique final type relationships
        pc_map = collections.defaultdict(list)
        for parent_id, parent_type in parent_sts.items():
            for child_type in child_sts[parent_id]:
                pc_map[parent_type].append(child_type)
        pc_final_map = dict()
        for ptype, ctypes in pc_map.items():
            unique_ctypes = list(set(ctypes))
            unique_ctypes.sort()
            pc_final_map[ptype] = unique_ctypes
        return pc_final_map

########NEW FILE########
__FILENAME__ = _utils
class defaultdict(dict):
    """Back compatible defaultdict: http://code.activestate.com/recipes/523034/
    """
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not hasattr(default_factory, '__call__')):
            raise TypeError('first argument must be callable')
        dict.__init__(self, *a, **kw)
        self.default_factory = default_factory
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value
    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()
    def copy(self):
        return self.__copy__()
    def __copy__(self):
        return type(self)(self.default_factory, self)
    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))
    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default_factory,
                                        dict.__repr__(self))


########NEW FILE########
__FILENAME__ = access_gff_index
"""Access an GFF file using bx-python's interval indexing.

Requires:
    bx-python: http://bitbucket.org/james_taylor/bx-python/wiki/Home
    gff library: http://github.com/chapmanb/bcbb/tree/master/gff

Index time:
  44 Mb file
  11 seconds
  Index is 7.5Mb
"""
from __future__ import with_statement
import os
import sys

from bx import interval_index_file

from BCBio import GFF

def main(gff_file):
    gff_index = gff_file + ".index"
    if not os.path.exists(gff_index):
        print "Indexing GFF file"
        index(gff_file)
    index = GFFIndexedAccess(gff_file, keep_open=True)
    print index.seqids
    print
    for feature in index.get_features_in_region("Chr2", 17500, 20000):
        print feature
    for feature in index.get_features_in_region("Chr5", 500000, 502500):
        print feature

    exam = GFF.GFFExaminer()
    #print exam.available_limits(gff_file)
    #print exam.parent_child_map(gff_file)

    found = 0
    limit_info = dict(
            gff_type = ["protein", "gene", "mRNA", "exon", "CDS", "five_prime_UTR",
                "three_prime_UTR"]
            )
    for feature in index.get_features_in_region("Chr1", 0, 50000, 
            limit_info):
        found += 1
    print found

class GFFIndexedAccess(interval_index_file.AbstractIndexedAccess):
    """Provide indexed access to a GFF file.
    """
    def __init__(self, *args, **kwargs):
        interval_index_file.AbstractIndexedAccess.__init__(self, *args,
                **kwargs)
        self._parser = GFF.GFFParser()

    @property
    def seqids(self):
        return self.indexes.indexes.keys()

    def get_features_in_region(self, seqid, start, end, limit_info=None):
        """Retrieve features located on a given region in start/end coordinates.
        """
        limit_info = self._parser._normalize_limit_info(limit_info)
        line_gen = self.get_as_iterator(seqid, int(start), int(end))
        recs = None
        for results in self._parser._lines_to_out_info(line_gen, limit_info):
            assert not recs, "Unexpected multiple results"
            recs = self._parser._results_to_features(dict(), results)
        if recs is None:
            return []
        else:
            assert len(recs) == 1
            rec = recs[seqid]
            return rec.features

    def read_at_current_offset(self, handle, **kwargs):
        line = handle.readline()
        return line

def index(gff_file, index_file=None):
    index = interval_index_file.Indexes()
    with open(gff_file) as in_handle:
        while 1:
            pos = in_handle.tell()
            line = in_handle.readline()
            if not line:
                break
            if not line.startswith("#"):
                parts = line.split("\t")
                (seqid, gtype, source, start, end) = parts[:5]
                index.add(seqid, int(start), int(end), pos)
    if index_file is None:
        index_file = gff_file + ".index"
    with open(index_file, "w") as index_handle:
        index.write(index_handle)
    return index_file

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = genbank_to_gff
#!/usr/bin/env python
"""Convert a GenBank file into GFF format.

Usage:
    genbank_to_gff.py <genbank_file>
"""
import sys
import os

from Bio import SeqIO
from Bio import Seq

from BCBio import GFF

def main(gb_file):
    out_file = "%s.gff" % os.path.splitext(gb_file)[0]
    with open(out_file, "w") as out_handle:
        GFF.write(SeqIO.parse(gb_file, "genbank"), out_handle)

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = gff2_to_gff3
#!/usr/bin/env python
"""Convert a GFF2 file to an updated GFF3 format file.

Usage:
    gff2_to_gff3.py <in_gff2_file>

The output file has the same name with the extension gff3.
"""
import sys
import os

from BCBio.GFF import GFFParser, GFF3Writer

def main(in_file):
    base, ext = os.path.splitext(in_file)
    out_file = "%s.gff3" % (base)
    in_handle = open(in_file)
    out_handle = open(out_file, "w")
    reader = GFFParser()
    writer = GFF3Writer()
    writer.write(reader.parse_in_parts(in_handle, target_lines=25000),
            out_handle)
    in_handle.close()
    out_handle.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print __doc__
        sys.exit()
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = gff_to_biosql
#!/usr/bin/env python
"""Load a fasta file of sequences and associated GFF file into BioSQL.

You will need to adjust the database parameters and have a BioSQL database set
up. See:

http://biopython.org/wiki/BioSQL

Depending on the size of the sequences being loaded, you may also get errors on
loading very large chromosome sequences. Updating these options can help:

    set global max_allowed_packet=1000000000;
    set global net_buffer_length=1000000;

Usage:
    gff_to_biosql.py <fasta file> <gff file>
"""
from __future__ import with_statement
import sys

from BioSQL import BioSeqDatabase
from Bio import SeqIO

from BCBio.GFF import GFFParser

def main(seq_file, gff_file):
    # -- To be customized
    # You need to update these parameters to point to your local database
    # XXX demo example could be swapped to use SQLite when that is integrated
    user = "chapmanb"
    passwd = "cdev"
    host = "localhost"
    db_name = "wb199_gff"
    biodb_name = "wb199_gff_cds_pcr"
    # These need to be updated to reflect what you would like to parse
    # out of the GFF file. Set limit_info=None to parse everything, but
    # be sure the file is small or you may deal with memory issues.
    rnai_types = [('Orfeome', 'PCR_product'),
                ('GenePair_STS', 'PCR_product'),
                ('Promoterome', 'PCR_product')]
    gene_types = [('Non_coding_transcript', 'gene'),
                  ('Coding_transcript', 'gene'),
                  ('Coding_transcript', 'mRNA'),
                  ('Coding_transcript', 'CDS')]
    limit_info = dict(gff_source_type = rnai_types + gene_types)
    # --
    print "Parsing FASTA sequence file..."
    with open(seq_file) as seq_handle:
        seq_dict = SeqIO.to_dict(SeqIO.parse(seq_handle, "fasta"))

    print "Parsing GFF data file..."
    parser = GFFParser()
    recs = parser.parse(gff_file, seq_dict, limit_info=limit_info)

    print "Writing to BioSQL database..."
    server = BioSeqDatabase.open_database(driver="MySQLdb", user=user,
            passwd=passwd, host=host, db=db_name)
    try:
        if biodb_name not in server.keys():
            server.new_database(biodb_name)
        else:
            server.remove_database(biodb_name)
            server.adaptor.commit()
            server.new_database(biodb_name)
        db = server[biodb_name]
        db.load(recs)
        server.adaptor.commit()
    except:
        server.adaptor.rollback()
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print __doc__
        sys.exit()
    main(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = gff_to_genbank
#!/usr/bin/env python
"""Convert a GFF and associated FASTA file into GenBank format.

Usage:
    gff_to_genbank.py <GFF annotation file> <FASTA sequence file>
"""
import sys
import os

from Bio import SeqIO
from Bio.Alphabet import generic_dna
from Bio import Seq

from BCBio import GFF

def main(gff_file, fasta_file):
    out_file = "%s.gb" % os.path.splitext(gff_file)[0]
    fasta_input = SeqIO.to_dict(SeqIO.parse(fasta_file, "fasta", generic_dna))
    gff_iter = GFF.parse(gff_file, fasta_input)
    SeqIO.write(_check_gff(_fix_ncbi_id(gff_iter)), out_file, "genbank")

def _fix_ncbi_id(fasta_iter):
    """GenBank identifiers can only be 16 characters; try to shorten NCBI.
    """
    for rec in fasta_iter:
        if len(rec.name) > 16 and rec.name.find("|") > 0:
            new_id = [x for x in rec.name.split("|") if x][-1]
            print "Warning: shortening NCBI name %s to %s" % (rec.id, new_id)
            rec.id = new_id
            rec.name = new_id
        yield rec

def _check_gff(gff_iterator):
    """Check GFF files before feeding to SeqIO to be sure they have sequences.
    """
    for rec in gff_iterator:
        if isinstance(rec.seq, Seq.UnknownSeq):
            print "Warning: FASTA sequence not found for '%s' in GFF file" % (
                    rec.id)
            rec.seq.alphabet = generic_dna
        yield _flatten_features(rec)

def _flatten_features(rec):
    """Make sub_features in an input rec flat for output.

    GenBank does not handle nested features, so we want to make
    everything top level.
    """
    out = []
    for f in rec.features:
        cur = [f]
        while len(cur) > 0:
            nextf = []
            for curf in cur:
                out.append(curf)
                if len(curf.sub_features) > 0:
                    nextf.extend(curf.sub_features)
            cur = nextf
    rec.features = out
    return rec

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = test_GFFSeqIOFeatureAdder
"""Test decoration of existing SeqRecords with GFF through a SeqIO interface.
"""
import sys
import os
import unittest
import pprint
import StringIO

from Bio import SeqIO
from BCBio import GFF
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from BCBio.GFF import (GFFExaminer, GFFParser, DiscoGFFParser)

class MapReduceGFFTest(unittest.TestCase):
    """Tests GFF parsing using a map-reduce framework for parallelization.
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._test_gff_file = os.path.join(self._test_dir,
                "c_elegans_WS199_shortened_gff.txt")
        self._disco_host = "http://localhost:7000"
    
    def t_local_map_reduce(self):
        """General map reduce framework without parallelization.
        """
        cds_limit_info = dict(
                gff_type = ["gene", "mRNA", "CDS"],
                gff_id = ['I']
                )
        rec_dict = SeqIO.to_dict(GFF.parse(self._test_gff_file,
            limit_info=cds_limit_info))
        test_rec = rec_dict['I']
        assert len(test_rec.features) == 32

    def t_disco_map_reduce(self):
        """Map reduce framework parallelized using disco.
        """
        # this needs to be more generalized but fails okay with no disco
        try:
            import disco
            import simplejson
        except ImportError:
            print "Skipping -- disco and json not found"
            return
        cds_limit_info = dict(
                gff_source_type = [('Non_coding_transcript', 'gene'),
                             ('Coding_transcript', 'gene'),
                             ('Coding_transcript', 'mRNA'),
                             ('Coding_transcript', 'CDS')],
                gff_id = ['I']
                )
        parser = DiscoGFFParser(disco_host=self._disco_host)
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file,
            limit_info=cds_limit_info))
        final_rec = rec_dict['I']
        # second gene feature is multi-parent
        assert len(final_rec.features) == 2 # two gene feature

class GFF3Test(unittest.TestCase):
    """Real live GFF3 tests from WormBase and NCBI.

    Uses GFF3 data from:

    ftp://ftp.wormbase.org/pub/wormbase/genomes/c_elegans/
    genome_feature_tables/GFF3/
    ftp://ftp.wormbase.org/pub/wormbase/genomes/c_elegans/sequences/dna/

    and from NCBI.
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._test_seq_file = os.path.join(self._test_dir,
                "c_elegans_WS199_dna_shortened.fa")
        self._test_gff_file = os.path.join(self._test_dir,
                "c_elegans_WS199_shortened_gff.txt")
        self._test_gff_ann_file = os.path.join(self._test_dir,
                "c_elegans_WS199_ann_gff.txt")
        self._full_dir = "/usr/home/chapmanb/mgh/ruvkun_rnai/wormbase/" + \
                "data_files_WS198"
        self._test_ncbi = os.path.join(self._test_dir,
                "ncbi_gff3.txt")

    def not_t_full_celegans(self):
        """Test the full C elegans chromosome and GFF files.

        This is used to test GFF on large files and is not run as a standard
        test. You will need to download the files and adjust the paths
        to run this.
        """
        # read the sequence information
        seq_file = os.path.join(self._full_dir, "c_elegans.WS199.dna.fa")
        gff_file = os.path.join(self._full_dir, "c_elegans.WS199.gff3")
        seq_handle = open(seq_file)
        seq_dict = SeqIO.to_dict(SeqIO.parse(seq_handle, "fasta"))
        seq_handle.close()
        #with open(gff_file) as gff_handle:
        #    possible_limits = feature_adder.available_limits(gff_handle)
        #    pprint.pprint(possible_limits)
        rnai_types = [('Orfeome', 'PCR_product'),
                    ('GenePair_STS', 'PCR_product'),
                    ('Promoterome', 'PCR_product')]
        gene_types = [('Non_coding_transcript', 'gene'),
                      ('Coding_transcript', 'gene'),
                      ('Coding_transcript', 'mRNA'),
                      ('Coding_transcript', 'CDS')]
        limit_info = dict(gff_source_type = rnai_types + gene_types)
        for rec in GFF.parse(gff_file, seq_dict, limit_info=limit_info):
            pass

    def _get_seq_dict(self):
        """Internal reusable function to get the sequence dictionary.
        """
        seq_handle = open(self._test_seq_file)
        seq_dict = SeqIO.to_dict(SeqIO.parse(seq_handle, "fasta"))
        seq_handle.close()
        return seq_dict
    
    def t_possible_limits(self):
        """Calculate possible queries to limit a GFF file.
        """
        gff_examiner = GFFExaminer()
        possible_limits = gff_examiner.available_limits(self._test_gff_file)
        print
        pprint.pprint(possible_limits)

    def t_parent_child(self):
        """Summarize parent-child relationships in a GFF file.
        """
        gff_examiner = GFFExaminer()
        pc_map = gff_examiner.parent_child_map(self._test_gff_file)
        print
        pprint.pprint(pc_map)

    def t_flat_features(self):
        """Check addition of flat non-nested features to multiple records.
        """
        seq_dict = self._get_seq_dict()
        pcr_limit_info = dict(
            gff_source_type = [('Orfeome', 'PCR_product'),
                         ('GenePair_STS', 'PCR_product'),
                         ('Promoterome', 'PCR_product')]
            )
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file, seq_dict,
            limit_info=pcr_limit_info))
        assert len(rec_dict['I'].features) == 4
        assert len(rec_dict['X'].features) == 5

    def t_nested_features(self):
        """Check three-deep nesting of features with gene, mRNA and CDS.
        """
        seq_dict = self._get_seq_dict()
        cds_limit_info = dict(
                gff_source_type = [('Coding_transcript', 'gene'),
                             ('Coding_transcript', 'mRNA'),
                             ('Coding_transcript', 'CDS')],
                gff_id = ['I']
                )
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file, seq_dict,
            limit_info=cds_limit_info))
        final_rec = rec_dict['I']
        # first gene feature is plain
        assert len(final_rec.features) == 2 # two gene feature
        assert len(final_rec.features[0].sub_features) == 1 # one transcript
        # 15 final CDS regions
        assert len(final_rec.features[0].sub_features[0].sub_features) == 15

    def t_nested_multiparent_features(self):
        """Verify correct nesting of features with multiple parents.
        """
        seq_dict = self._get_seq_dict()
        cds_limit_info = dict(
                gff_source_type = [('Coding_transcript', 'gene'),
                             ('Coding_transcript', 'mRNA'),
                             ('Coding_transcript', 'CDS')],
                gff_id = ['I']
                )
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file, seq_dict,
            limit_info=cds_limit_info))
        final_rec = rec_dict['I']
        # second gene feature is multi-parent
        assert len(final_rec.features) == 2 # two gene feature
        cur_subs = final_rec.features[1].sub_features
        assert len(cur_subs) == 3 # three transcripts
        # the first and second transcript have the same CDSs
        assert len(cur_subs[0].sub_features) == 6
        assert len(cur_subs[1].sub_features) == 6
        assert cur_subs[0].sub_features[0] is cur_subs[1].sub_features[0]

    def t_no_dict_error(self):
        """Ensure an error is raised when no dictionary to map to is present.
        """
        parser = GFFParser(create_missing=False)
        try:
            for rec in parser.parse(self._test_gff_file):
                pass
            # no error -- problem
            raise AssertionError('Did not complain with missing dictionary')
        except KeyError:
            pass

    def t_unknown_seq(self):
        """Prepare unknown base sequences with the correct length.
        """
        rec_dict = SeqIO.to_dict(GFF.parse(self._test_gff_file))
        assert len(rec_dict["I"].seq) == 12766937
        assert len(rec_dict["X"].seq) == 17718531

    def t_gff_annotations(self):
        """Check GFF annotations placed on an entire sequence.
        """
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_ann_file))
        final_rec = rec_dict['I']
        assert len(final_rec.annotations.keys()) == 2
        assert final_rec.annotations['source'] == ['Expr_profile']
        assert final_rec.annotations['expr_profile'] == ['B0019.1']
    
    def t_gff3_iterator(self):
        """Iterated parsing in GFF3 files with nested features.
        """
        parser = GFFParser()
        recs = [r for r in parser.parse_in_parts(self._test_gff_file,
            target_lines=70)]
        # should be one big set because we don't have a good place to split
        assert len(recs) == 6
        assert len(recs[0].features) == 59
    
    def t_gff3_iterator_limit(self):
        """Iterated interface using a limit query on GFF3 files.
        """
        cds_limit_info = dict(
                gff_source_type = [('Coding_transcript', 'gene'),
                             ('Coding_transcript', 'mRNA'),
                             ('Coding_transcript', 'CDS')],
                gff_id = ['I']
                )
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file,
            limit_info=cds_limit_info))
        assert len(rec_dict) == 1
        tfeature = rec_dict["I"].features[0].sub_features[0]
        for sub_test in tfeature.sub_features:
            assert sub_test.type == "CDS", sub_test

    def t_gff3_noval_attrib(self):
        """Parse GFF3 file from NCBI with a key/value pair with no value.
        """
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_ncbi))
        assert len(rec_dict) == 1
        t_feature = rec_dict.values()[0].features[0]
        assert t_feature.qualifiers["pseudo"] == ["true"]

    def t_gff3_multiple_ids(self):
        """Deal with GFF3 with non-unique ID attributes, using NCBI example.
        """
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_ncbi))
        assert len(rec_dict) == 1
        t_features = rec_dict.values()[0].features[1:]
        # 4 feature sets, same ID, different positions, different attributes
        assert len(t_features) == 4
        for f in t_features:
            assert len(f.sub_features) == 3

    def t_simple_parsing(self):
        """Parse GFF into a simple line by line dictionary without nesting.
        """
        parser = GFFParser()
        num_lines = 0
        for line_info in parser.parse_simple(self._test_gff_file):
            num_lines += 1
        assert num_lines == 177, num_lines
        line_info = line_info['child'][0]
        assert line_info['quals']['confirmed_est'] == \
                ['yk1055g06.5', 'OSTF085G5_1']
        assert line_info['location'] == [4582718, 4583189]

    def t_simple_parsing_nesting(self):
        """Simple parsing for lines with nesting, using the simplified API.
        """
        test_gff = os.path.join(self._test_dir, "transcripts.gff3")
        num_lines = 0
        for line_info in GFF.parse_simple(test_gff):
            num_lines += 1
        assert num_lines == 16, num_lines

    def t_extra_comma(self):
        """Correctly handle GFF3 files with extra trailing commas.
        """
        tfile = os.path.join(self._test_dir, "mouse_extra_comma.gff3")
        in_handle = open(tfile)
        for rec in GFF.parse(in_handle):
            pass
        in_handle.close()
        tested = False
        for sub_top in rec.features[0].sub_features:
            for sub in sub_top.sub_features:
                if sub.qualifiers.get("Name", "") == ["CDS:NC_000083.5:LOC100040603"]:
                    tested = True
                    assert len(sub.qualifiers["Parent"]) == 1
        assert tested, "Did not find sub-feature to test"

    def t_novalue_key(self):
        """Handle GFF3 files with keys and no values.
        """
        tfile = os.path.join(self._test_dir, "glimmer_nokeyval.gff3")
        rec = GFF.parse(tfile).next()
        f1, f2 = rec.features
        assert f1.qualifiers['ID'] == ['GL0000006']
        assert len(f1.sub_features) == 2
        assert f1.sub_features[0].qualifiers["Lack 3'-end"] == ["true"]
        assert not f1.sub_features[0].qualifiers.has_key("ID")
        assert f2.qualifiers["Complete"] == ["true"]

class SolidGFFTester(unittest.TestCase):
    """Test reading output from SOLiD analysis, as GFF3.

    See more details on SOLiD GFF here:

    http://solidsoftwaretools.com/gf/project/matogff/
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._test_gff_file = os.path.join(self._test_dir,
                "F3-unique-3.v2.gff")

    def t_basic_solid_parse(self):
        """Basic parsing of SOLiD GFF results files.
        """
        parser = GFFParser()
        rec_dict = SeqIO.to_dict(parser.parse(self._test_gff_file))
        test_feature = rec_dict['3_341_424_F3'].features[0]
        assert test_feature.location.nofuzzy_start == 102716
        assert test_feature.location.nofuzzy_end == 102736
        assert len(test_feature.qualifiers) == 7
        assert test_feature.qualifiers['score'] == ['10.6']
        assert test_feature.qualifiers['source'] == ['solid']
        assert test_feature.strand == -1
        assert test_feature.type == 'read'
        assert test_feature.qualifiers['g'] == ['T2203031313223113212']
        assert len(test_feature.qualifiers['q']) == 20
    
    def t_solid_iterator(self):
        """Iterated parsing in a flat file without nested features.
        """
        parser = GFFParser()
        feature_sizes = []
        for rec in parser.parse_in_parts(self._test_gff_file,
                target_lines=5):
            feature_sizes.append(len(rec.features))
        assert len(feature_sizes) == 112
        assert max(feature_sizes) == 1

    def t_line_adjust(self):
        """Adjust lines during parsing to fix potential GFF problems.
        """
        def adjust_fn(results):
            rec_index = results['quals']['i'][0]
            read_name = results['rec_id']
            results['quals']['read_name'] = [read_name]
            results['rec_id'] = rec_index
            return results
        parser = GFFParser(line_adjust_fn=adjust_fn)
        recs = [r for r in parser.parse(self._test_gff_file)]
        assert len(recs) == 1
        work_rec = recs[0]
        assert work_rec.id == '1'
        assert len(work_rec.features) == 112
        assert work_rec.features[0].qualifiers['read_name'] == \
                ['3_336_815_F3']

class GFF2Tester(unittest.TestCase):
    """Parse GFF2 and GTF files, building features.
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._ensembl_file = os.path.join(self._test_dir, "ensembl_gtf.txt")
        self._wormbase_file = os.path.join(self._test_dir, "wormbase_gff2.txt")
        self._jgi_file = os.path.join(self._test_dir, "jgi_gff2.txt")
        self._wb_alt_file = os.path.join(self._test_dir,
                "wormbase_gff2_alt.txt")

    def t_basic_attributes(self):
        """Parse out basic attributes of GFF2 from Ensembl GTF.
        """
        limit_info = dict(
                gff_source_type = [('snoRNA', 'exon')]
                )
        rec_dict = SeqIO.to_dict(GFF.parse(self._ensembl_file,
            limit_info=limit_info))
        work_rec = rec_dict['I']
        assert len(work_rec.features) == 1
        test_feature = work_rec.features[0]
        qual_keys = test_feature.qualifiers.keys()
        qual_keys.sort()
        assert qual_keys == ['Parent', 'exon_number', 'gene_id', 'gene_name',
                'source', 'transcript_id', 'transcript_name']
        assert test_feature.qualifiers['source'] == ['snoRNA']
        assert test_feature.qualifiers['transcript_name'] == ['NR_001477.2']
        assert test_feature.qualifiers['exon_number'] == ['1']

    def t_tricky_semicolons(self):
        """Parsing of tricky semi-colon positions in WormBase GFF2.
        """
        limit_info = dict(
                gff_source_type = [('Genomic_canonical', 'region')]
                )
        rec_dict = SeqIO.to_dict(GFF.parse(self._wormbase_file,
            limit_info=limit_info))
        work_rec = rec_dict['I']
        assert len(work_rec.features) == 1
        test_feature = work_rec.features[0]
        assert test_feature.qualifiers['Note'] == \
          ['Clone cTel33B; Genbank AC199162', 'Clone cTel33B; Genbank AC199162'], test_feature.qualifiers["Note"]

    def t_unescaped_semicolons(self):
        """Parse inputs with unescaped semi-colons.
        This is a band-aid to not fail rather than correct parsing, since
        the combined feature will not be maintained.
        """
        f = os.path.join(self._test_dir, "unescaped-semicolon.gff3")
        rec_dict = SeqIO.to_dict(GFF.parse(f))
        f = rec_dict['chr1'].features[0]
        assert f.qualifiers["Description"][0].startswith('osFTL6')
        assert f.qualifiers["Description"][0].endswith('protein, expressed')

    def t_jgi_gff(self):
        """Parsing of JGI formatted GFF2, nested using transcriptId and proteinID
        """
        rec_dict = SeqIO.to_dict(GFF.parse(self._jgi_file))
        tfeature = rec_dict['chr_1'].features[0]
        assert tfeature.location.nofuzzy_start == 37060
        assert tfeature.location.nofuzzy_end == 38216
        assert tfeature.type == 'inferred_parent'
        assert len(tfeature.sub_features) == 6
        sfeature = tfeature.sub_features[1]
        assert sfeature.qualifiers['proteinId'] == ['873']
        assert sfeature.qualifiers['phase'] == ['0']

    def t_ensembl_nested_features(self):
        """Test nesting of features with GFF2 files using transcript_id.
        """
        rec_dict = SeqIO.to_dict(GFF.parse(self._ensembl_file))
        assert len(rec_dict["I"].features) == 2
        t_feature = rec_dict["I"].features[0]
        assert len(t_feature.sub_features) == 32

    def t_wormbase_nested_features(self):
        """Test nesting of features with GFF2 files using Transcript only.
        """
        rec_dict = SeqIO.to_dict(GFF.parse(self._wormbase_file))
        assert len(rec_dict) == 3
        parent_features = [f for f in rec_dict["I"].features if f.type ==
                "Transcript"]
        assert len(parent_features) == 1
        inferred_features = [f for f in rec_dict["I"].features if f.type ==
                "inferred_parent"]
        assert len(inferred_features) == 0
        tfeature = parent_features[0]
        assert tfeature.qualifiers["WormPep"][0] == "WP:CE40797"
        assert len(tfeature.sub_features) == 46

    def t_wb_cds_nested_features(self):
        """Nesting of GFF2 features with a flat CDS key value pair.
        """
        rec_dict = SeqIO.to_dict(GFF.parse(self._wb_alt_file))
        assert len(rec_dict) == 2
        features = rec_dict.values()[1].features
        assert len(features) == 1
        tfeature = features[0]
        assert tfeature.id == "cr01.sctg102.wum.2.1"
        assert len(tfeature.sub_features) == 7

    def t_gff2_iteration(self):
        """Test iterated features with GFF2 files, breaking without parents.
        """
        recs = []
        for rec in GFF.parse(self._wormbase_file, target_lines=15):
            recs.append(rec)
        assert len(recs) == 4
        assert recs[0].features[0].type == 'region'
        assert recs[0].features[1].type == 'SAGE_tag'
        assert len(recs[0].features[2].sub_features) == 29

class DirectivesTest(unittest.TestCase):
    """Tests for parsing directives and other meta-data.
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._gff_file = os.path.join(self._test_dir, "hybrid1.gff3")

    def t_basic_directives(self):
        """Parse out top level meta-data supplied in a GFF3 file.
        """
        recs = SeqIO.to_dict(GFF.parse(self._gff_file))
        anns = recs['chr17'].annotations
        assert anns['gff-version'] == ['3']
        assert anns['attribute-ontology'] == ['baz']
        assert anns['feature-ontology'] == ['bar']
        assert anns['source-ontology'] == ['boo']
        assert anns['sequence-region'] == [('foo', 0, 100), ('chr17',
            62467933, 62469545)]

    def t_fasta_directive(self):
        """Parse FASTA sequence information contained in a GFF3 file.
        """
        recs = SeqIO.to_dict(GFF.parse(self._gff_file))
        assert len(recs) == 1
        test_rec = recs['chr17']
        assert str(test_rec.seq) == "GATTACAGATTACA"
    
    def t_examiner_with_fasta(self):
        """Perform high level examination of files with FASTA directives.
        """
        examiner = GFFExaminer()
        pc_map = examiner.parent_child_map(self._gff_file)
        assert pc_map[('UCSC', 'mRNA')] == [('UCSC', 'CDS')]
        limits = examiner.available_limits(self._gff_file)
        assert limits['gff_id'].keys()[0][0] == 'chr17'
        assert sorted(limits['gff_source_type'].keys()) == \
                [('UCSC', 'CDS'), ('UCSC', 'mRNA')]

class OutputTest(unittest.TestCase):
    """Tests to write SeqFeatures to GFF3 output format.
    """
    def setUp(self):
        self._test_dir = os.path.join(os.path.dirname(__file__), "GFF")
        self._test_seq_file = os.path.join(self._test_dir,
                "c_elegans_WS199_dna_shortened.fa")
        self._test_gff_file = os.path.join(self._test_dir,
                "c_elegans_WS199_shortened_gff.txt")
        self._test_gff_ann_file = os.path.join(self._test_dir,
                "c_elegans_WS199_ann_gff.txt")
        self._wormbase_file = os.path.join(self._test_dir, "wormbase_gff2.txt")

    def t_gff3_to_gff3(self):
        """Read in and write out GFF3 without any loss of information.
        """
        recs = SeqIO.to_dict(GFF.parse(self._test_gff_file))
        out_handle = StringIO.StringIO()
        GFF.write(recs.values(), out_handle)
        wrote_handle = StringIO.StringIO(out_handle.getvalue())
        recs_two = SeqIO.to_dict(GFF.parse(wrote_handle))

        orig_rec = recs.values()[0]
        re_rec = recs.values()[0]
        assert len(orig_rec.features) == len(re_rec.features)
        for i, orig_f in enumerate(orig_rec.features):
            assert str(orig_f) == str(re_rec.features[i])

    def t_gff2_to_gff3(self):
        """Read in GFF2 and write out as GFF3.
        """
        recs = SeqIO.to_dict(GFF.parse(self._wormbase_file))
        out_handle = StringIO.StringIO()
        GFF.write(recs.values(), out_handle)
        wrote_handle = StringIO.StringIO(out_handle.getvalue())
        # check some tricky lines in the GFF2 file
        checks = 0
        for line in wrote_handle:
            if line.find("Interpolated_map_position") >= 0:
                checks += 1
                assert line.find("RFLP=No") > 0
            if line.find("Gene=WBGene00000138") > 0:
                checks += 1
                assert line.find("ID=B0019.1") > 0
            if line.find("translated_nucleotide_match\t12762127") > 0:
                checks += 1
                assert line.find("Note=MSP:FADFSPLDVSDVNFATDDLAK") > 0
        assert checks == 3, "Missing check line"

    def t_write_from_recs(self):
        """Write out GFF3 from SeqRecord inputs.
        """
        seq = Seq("GATCGATCGATCGATCGATC")
        rec = SeqRecord(seq, "ID1")
        qualifiers = {"source": "prediction", "score": 10.0, "other": ["Some", "annotations"],
                      "ID": "gene1"}
        sub_qualifiers = {"source": "prediction"}
        top_feature = SeqFeature(FeatureLocation(0, 20), type="gene", strand=1,
                                                          qualifiers=qualifiers)
        top_feature.sub_features = [SeqFeature(FeatureLocation(0, 5), type="exon", strand=1,
                                               qualifiers=sub_qualifiers),
                                    SeqFeature(FeatureLocation(15, 20), type="exon", strand=1,
                                               qualifiers=sub_qualifiers)]
        rec.features = [top_feature]
        out_handle = StringIO.StringIO()
        GFF.write([rec], out_handle)
        wrote_info = out_handle.getvalue().split("\n")
        assert wrote_info[0] == "##gff-version 3"
        assert wrote_info[1] == "##sequence-region ID1 1 20"
        print wrote_info[2].split("\t")
        assert wrote_info[2].split("\t") == ['ID1', 'prediction', 'gene', '1',
                                             '20', '10.0', '+', '.',
                                             'ID=gene1;other=Some,annotations']
        assert wrote_info[3].split("\t") == ['ID1', 'prediction', 'exon', '1', '5',
                                             '.', '+', '.', 'Parent=gene1']

    def t_write_fasta(self):
        """Include FASTA records in GFF output.
        """
        seq = Seq("GATCGATCGATCGATCGATC")
        rec = SeqRecord(seq, "ID1")
        qualifiers = {"source": "prediction", "score": 10.0, "other": ["Some", "annotations"],
                      "ID": "gene1"}
        rec.features = [SeqFeature(FeatureLocation(0, 20), type="gene", strand=1,
                                   qualifiers=qualifiers)]
        out_handle = StringIO.StringIO()
        GFF.write([rec], out_handle, include_fasta=True)
        wrote_info = out_handle.getvalue().split("\n")
        fasta_parts = wrote_info[3:]
        assert fasta_parts[0] == "##FASTA"
        assert fasta_parts[1] == ">ID1 <unknown description>"
        assert fasta_parts[2] == str(seq)

    def t_write_seqrecord(self):
        """Write single SeqRecords.
        """
        seq = Seq("GATCGATCGATCGATCGATC")
        rec = SeqRecord(seq, "ID1")
        qualifiers = {"source": "prediction", "score": 10.0, "other": ["Some", "annotations"],
                      "ID": "gene1"}
        rec.features = [SeqFeature(FeatureLocation(0, 20), type="gene", strand=1,
                                   qualifiers=qualifiers)]
        out_handle = StringIO.StringIO()
        GFF.write([rec], out_handle, include_fasta=True)
        wrote_info = out_handle.getvalue().split("\n")
        gff_line = wrote_info[2]
        assert gff_line.split("\t")[0] == "ID1"

def run_tests(argv):
    test_suite = testing_suite()
    runner = unittest.TextTestRunner(sys.stdout, verbosity = 2)
    runner.run(test_suite)

def testing_suite():
    """Generate the suite of tests.
    """
    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 't_'
    tests = [GFF3Test, MapReduceGFFTest, SolidGFFTester, GFF2Tester,
             DirectivesTest, OutputTest]
    #tests = [GFF3Test]
    for test in tests:
        cur_suite = test_loader.loadTestsFromTestCase(test)
        test_suite.addTest(cur_suite)
    return test_suite

if __name__ == "__main__":
    sys.exit(run_tests(sys.argv))

########NEW FILE########
__FILENAME__ = couchdb_get_freqs
#!/usr/bin/env python
"""Get frequencies from a CouchDB remote database.

Total time  : 14:22.19s
Memory      : 8154
Percent CPU : 63.8%
"""
import sys
import random
import couchdb.client

def main():
    db_name = "reads_090504/read_to_freq"
    server = couchdb.client.Server("http://mothra:5984/")
    db = server[db_name]

    max_records = 2810717
    num_trials = 500000
    for index in range(num_trials):
        read_id = str(random.randint(0, max_records))
        doc = db[read_id]
        freq = int(doc["frequency"])
        if index % 10000 == 0:
            print index, read_id, freq

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = freq_to_couchdb
#!/usr/bin/env python
"""Write a file of read frequencies to a CouchDB database.

Did not finish on first pass with naive code:

    Total time  : 22:15:19.10s
    Memory      : 4896
    Percent CPU : 2.6%

    -rw-rw-r-- 1 chapman users 5.7G 2009-05-07 07:52 read_to_freq.couch

    1842694 documents loaded

Re-done with improvements from Chris and Paul for bulk loading:

    Total time  : 5:31.01s
    Memory      : 7490
    Percent CPU : 10.4%

    -rw-rw-r-- 1 chapman users 236M 2009-05-11 08:01 read_to_freq.couch
"""
import sys
import couchdb.client

def main(in_file):
    db_name = "reads_090504/read_to_freq"
    server = couchdb.client.Server("http://mothra:5984/")
    # tune this somewhere between 500-5000 depending on your doc size
    bulk_size = 5000
    bulk_docs = []
    if db_name in server:
        db = server[db_name]
    else:
        db = server.create(db_name)

    with open(in_file) as in_handle:
        for read_index, freq in enumerate(in_handle):
            bulk_docs.append(dict(_id=str(read_index), frequency=int(freq)))
            if len(bulk_docs) >= bulk_size:
                db.update(bulk_docs)
                bulk_docs = []
        db.update(bulk_docs)

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = freq_to_mongodb
#!/usr/bin/env python
"""Write a file of read frequencies to a MongoDB database.

./mongod --dbpath /store3/alt_home/chapman/dbs/mongodb --quiet

Original stats:
Total time  : 5:13.66s
Memory      : 4954
Percent CPU : 99.9%

    -rwxrwxr-x 1 chapman users    0 2009-05-05 17:58 mongod.lock
    -rw------- 1 chapman users  64M 2009-05-05 17:58 reads_090504.0
    -rw------- 1 chapman users 128M 2009-05-05 17:59 reads_090504.1
    -rw------- 1 chapman users 256M 2009-05-05 17:59 reads_090504.2
    -rw------- 1 chapman users 512M 2009-05-05 18:01 reads_090504.3
    -rw------- 1 chapman users 1.0G 2009-05-05 18:03 reads_090504.4
    -rw------- 1 chapman users  16M 2009-05-05 17:58 reads_090504.ns

With _id change:

Total time  : 2:58.90s
Memory      : 4988
Percent CPU : 99.9%

-rw------- 1 chapman users  64M 2009-05-08 10:19 reads_090504.0
-rw------- 1 chapman users 128M 2009-05-08 10:20 reads_090504.1
-rw------- 1 chapman users 256M 2009-05-08 10:20 reads_090504.2
-rw------- 1 chapman users 512M 2009-05-08 10:21 reads_090504.3
-rw------- 1 chapman users  16M 2009-05-08 10:19 reads_090504.ns
"""
import sys
from pymongo.connection import Connection
from pymongo import ASCENDING

def main(in_file):
    conn = Connection("mothra")
    db = conn["reads_090504"]
    col = db["read_to_freq"]

    with open(in_file) as in_handle:
        for read_index, freq in enumerate(in_handle):
            col.insert(dict(_id=read_index, freq=int(freq)))
    #col.create_index("_id", ASCENDING)

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = freq_to_tyrant
"""Write file of read frequencies to a Tokyo Tyrant server.

ttserver test.tcb#opts=ld#bnum=1000000#lcnum=10000

Total time  : 11:58.90s
Memory      : 2536
Percent CPU : 39.2%

-rw-r--r-- 1 chapman users 24M 2009-05-07 09:01 test.tcb
"""
import sys
import pytyrant
import json

def main(in_file):
    db = pytyrant.PyTyrant.open("mothra", 1978)

    with open(in_file) as in_handle:
        for read_index, freq in enumerate(in_handle):
            db[str(read_index)] = json.dumps(dict(frequency=freq))

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = mongodb_get_freqs
#!/usr/bin/env python
"""Get frequencies from a MongoDB remote database.

Total time  : 3:57.29s
Memory      : 7848
Percent CPU : 34.6%
"""
import sys
import random
from pymongo.connection import Connection

def main():
    conn = Connection("mothra")
    db = conn["reads_090504"]
    print db.validate_collection("read_to_freq")
    col = db["read_to_freq"]
    print col.index_information()
    print col.options()

    max_records = 2810718
    num_trials = 500000
    for index in range(num_trials):
        read_id = random.randint(0, max_records)
        doc = col.find_one(dict(_id=read_id))
        if doc is None:
            print index, read_id
        freq = int(doc["freq"])
        if index % 10000 == 0:
            print index, freq, doc

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = tyrant_get_freqs
#!/usr/bin/env python
"""Get frequencies from a Tokyo Tyrant remote database.

Total time  : 3:20.37s
Memory      : 6706
Percent CPU : 35.4%
"""
import sys
import random
import pytyrant
import json

def main():
    db = pytyrant.PyTyrant.open("mothra", 1978)

    max_records = 2810718
    num_trials = 500000
    for index in range(num_trials):
        read_id = str(random.randint(0, max_records))
        freq = int(json.loads(db[read_id])['frequency'])
        if index % 10000 == 0:
            print index, freq, read_id

if __name__ == "__main__":
    main()

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
__FILENAME__ = fastq
from bcbio.log import logger
from bcbio import utils
from Bio import SeqIO


@utils.memoize_outfile(stem="groom")
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

    count = SeqIO.convert(in_file, in_qual, out_file, "fastq-sanger")
    logger.info("Converted %d reads in %s to %s." % (count, in_file, out_file))
    return out_file

########NEW FILE########
__FILENAME__ = trim
"""Provide trimming of input reads from Fastq or BAM files.
"""
import os
import contextlib

from bcbio.utils import file_exists, save_diskspace, safe_makedir

from Bio.SeqIO.QualityIO import FastqGeneralIterator

def _trim_quality(seq, qual, to_trim, min_length):
    """Trim bases of the given quality from 3' read ends.
    """
    removed = 0
    while qual.endswith(to_trim):
        removed += 1
        qual = qual[:-1]
    if len(qual) >= min_length:
        return seq[:len(seq) - removed], qual
    else:
        return None, None

@contextlib.contextmanager
def _work_handles(in_files, dirs, ext):
    """Create working handles for input files and close on completion.
    """
    out_dir = safe_makedir(os.path.join(dirs["work"], "trim"))
    out_handles = {}
    in_handles = {}
    name_map = {}
    for in_file in in_files:
        out_file = os.path.join(out_dir, "{base}{ext}".format(
            base=os.path.splitext(os.path.basename(in_file))[0], ext=ext))
        name_map[in_file] = out_file
        if not file_exists(out_file):
            in_handles[in_file] = open(in_file)
            out_handles[in_file] = open(out_file, "w")
    try:
        yield in_handles, out_handles, name_map
    finally:
        for h in in_handles.values():
            h.close()
        for h in out_handles.values():
            h.close()

def _trim_by_read(in_handles, to_trim, min_length):
    """Lazy generator for trimmed reads for all input files.
    """
    iterators = [(f, FastqGeneralIterator(h)) for f, h in in_handles.iteritems()]
    f1, x1 = iterators[0]
    for name, seq, qual in x1:
        out = {}
        tseq, tqual = _trim_quality(seq, qual, to_trim, min_length)
        if tseq:
            out[f1] = (name, tseq, tqual)
        for f2, x2 in iterators[1:]:
            name, seq, qual = x2.next()
            tseq, tqual = _trim_quality(seq, qual, to_trim, min_length)
            if tseq:
                out[f2] = (name, tseq, tqual)
        if len(out) == len(iterators):
            yield out

def _save_diskspace(in_file, out_file, config):
    """Potentially remove input file to save space if configured and in work directory.
    """
    if (os.path.commonprefix([in_file, out_file]).rstrip("/") ==
        os.path.split(os.path.dirname(out_file))[0]):
        save_diskspace(in_file, "Trimmed to {}".format(out_file), config)

def brun_trim_fastq(fastq_files, dirs, config):
    """Trim FASTQ files, removing low quality B-runs.

    This removes stretches of low quality sequence from read ends. Illumina
    quality assessment generates these stretches. Removing them can help reduce
    false positive rates for variant calling.

    http://genomebiology.com/2011/12/11/R112

    Does simple trimming of problem ends and removes read pairs where
    any of the trimmed read sizes falls below the allowable size.
    """
    qual_format = config["algorithm"].get("quality_format", "").lower()
    min_length = int(config["algorithm"].get("min_read_length", 20))
    to_trim = "B" if qual_format == "illumina" else "#"
    with _work_handles(fastq_files, dirs, "-qtrim.txt") as (in_handles, out_handles, out_fnames):
        if len(out_handles) == len(fastq_files):
            for next_reads in _trim_by_read(in_handles, to_trim, min_length):
                for fname, (name, seq, qual) in next_reads.iteritems():
                    out_handles[fname].write("@%s\n%s\n+\n%s\n" % (name, seq, qual))
        out_files = [out_fnames[x] for x in fastq_files]
        for inf, outf in zip(fastq_files, out_files):
            _save_diskspace(inf, outf, config)
        return out_files

########NEW FILE########
__FILENAME__ = metrics
"""Handle running, parsing and manipulating metrics available through Picard.
"""
import os
import glob
import json
import contextlib
import pprint

from bcbio.utils import tmpfile, file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.broad.picardrun import picard_rnaseq_metrics

import pysam


class PicardMetricsParser(object):
    """Read metrics files produced by Picard analyses.

    Metrics info:
    http://www.broadinstitute.org/~prodinfo/picard_metric_definitions.html
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
        with open(dup_metrics) as in_handle:
            dup_vals = self._parse_dup_metrics(in_handle)
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
        dup_total = int(dup_vals["READ_PAIRS_EXAMINED"])
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
            if align_total != dup_total:
                out.append(("Alignment combinations",
                            _add_commas(str(dup_total)), ""))
            out.append(self._count_percent("Pair duplicates",
                                           dup_vals["READ_PAIR_DUPLICATES"],
                                           dup_total))
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
        want_stats = ["READ_PAIRS_EXAMINED", "READ_PAIR_DUPLICATES",
                "PERCENT_DUPLICATION", "ESTIMATED_LIBRARY_SIZE"]
        header = self._read_off_header(in_handle)
        info = in_handle.readline().rstrip("\n").split("\t")
        vals = self._read_vals_of_interest(want_stats, header, info)
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

    def report(self, align_bam, ref_file, is_paired, bait_file, target_file):
        """Produce report metrics using Picard with sorted aligned BAM file.
        """
        dup_bam, dup_metrics = self._get_current_dup_metrics(align_bam)
        align_metrics = self._collect_align_metrics(dup_bam, ref_file)
        # Prefer the GC metrics in FastQC instead of Picard
        # gc_graph, gc_metrics = self._gc_bias(dup_bam, ref_file)
        gc_graph = None
        insert_graph, insert_metrics, hybrid_metrics = (None, None, None)
        if is_paired:
            insert_graph, insert_metrics = self._insert_sizes(dup_bam)
        if bait_file and target_file:
            hybrid_metrics = self._hybrid_select_metrics(dup_bam,
                                                         bait_file, target_file)

        vrn_vals = self._variant_eval_metrics(dup_bam)
        summary_info = self._parser.get_summary_metrics(align_metrics,
                dup_metrics, insert_metrics, hybrid_metrics,
                vrn_vals)
        pprint.pprint(summary_info)
        graphs = []
        if gc_graph and os.path.exists(gc_graph):
            graphs.append((gc_graph, "Distribution of GC content across reads"))
        if insert_graph and os.path.exists(insert_graph):
            graphs.append((insert_graph, "Distribution of paired end insert sizes"))
        return summary_info, graphs

    def _get_current_dup_metrics(self, align_bam):
        """Retrieve existing duplication metrics file, or generate if not present.
        """
        dup_fname_pos = align_bam.find("-dup")
        if dup_fname_pos > 0:
            base_name = align_bam[:dup_fname_pos]
            metrics = glob.glob("{0}*.dup_metrics".format(base_name))
            assert len(metrics) > 0, "Appear to have deduplication but did not find metrics file"
            return align_bam, metrics[0]
        else:
            return self._picard.run_fn("picard_mark_duplicates", align_bam)

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
                        self._picard.run("CalculateHsMetrics", opts)
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
        with tmpfile(dir=os.getcwd(), prefix="picardbed") as tmp_bed:
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

    def report(self, align_bam, ref_file, gtf_file, is_paired=False,
               rrna_file="null"):
        """Produce report metrics for a RNASeq experiment using Picard
        with a sorted aligned BAM file.

        """

        # collect duplication metrics
        dup_bam, dup_metrics = self._get_current_dup_metrics(align_bam)
        align_metrics = self._collect_align_metrics(align_bam, ref_file)
        insert_graph, insert_metrics = (None, None)
        if is_paired:
            insert_graph, insert_metrics = self._insert_sizes(align_bam)

        rnaseq_metrics = self._rnaseq_metrics(align_bam, gtf_file, rrna_file)

        summary_info = self._parser.get_summary_metrics(align_metrics,
                                                dup_metrics,
                                                insert_metrics=insert_metrics,
                                                rnaseq_metrics=rnaseq_metrics)
        pprint.pprint(summary_info)
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
    if not file_exists(index_file):
        with file_transaction(index_file) as tx_index_file:
            opts = [("INPUT", in_bam),
                    ("OUTPUT", tx_index_file)]
            picard.run("BuildBamIndex", opts)
    return index_file

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

def picard_fastq_to_bam(picard, fastq_one, fastq_two, out_dir,
                        platform, sample_name="", rg_name="", pu_name="",
                        qual_format=None):
    """Convert fastq file(s) to BAM, adding sample, run group and platform information.
    """
    qual_formats = {"illumina": "Illumina"}
    if qual_format is None:
        try:
            qual_format = qual_formats[platform.lower()]
        except KeyError:
            raise ValueError("Need to specify quality format for %s" % platform)
    out_bam = os.path.join(out_dir, "%s-fastq.bam" %
                           os.path.splitext(os.path.basename(fastq_one))[0])
    if not file_exists(out_bam):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_bam) as tx_out_bam:
                opts = [("FASTQ", fastq_one),
                        ("QUALITY_FORMAT", qual_format),
                        ("READ_GROUP_NAME", rg_name),
                        ("SAMPLE_NAME", sample_name),
                        ("PLATFORM_UNIT", pu_name),
                        ("PLATFORM", platform),
                        ("TMP_DIR", tmp_dir),
                        ("OUTPUT", tx_out_bam)]
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
                        ("OUTPUT", tx_out_bam)]
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
                picard.run("MarkDuplicates", opts)
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
            else:
                contig, _, length, _, aligned, _, unaligned = parts
                out.append(AlignInfo(contig, int(length), int(aligned), int(unaligned)))
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
        reordered = "\t".join([splitline[0], splitline[1], splitline[2],
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
__FILENAME__ = ipython
"""Distributed execution using an IPython cluster.

Uses IPython parallel to setup a cluster and manage execution:

http://ipython.org/ipython-doc/stable/parallel/index.html

Borrowed from Rory Kirchner's Bipy cluster implementation:

https://github.com/roryk/bipy/blob/master/bipy/cluster/__init__.py
"""
import os
import copy
import glob
import pipes
import time
import uuid
import subprocess
import contextlib

from bcbio import utils
from bcbio.log import setup_logging, logger
from bcbio.pipeline import config_utils

from IPython.parallel import Client
from IPython.parallel.apps import launcher
from IPython.utils import traitlets

# ## Custom launchers

timeout_params = ["--timeout=30", "--IPEngineApp.wait_for_url_file=120"]

class BcbioLSFEngineSetLauncher(launcher.LSFEngineSetLauncher):
    """Custom launcher handling heterogeneous clusters on LSF.
    """
    cores = traitlets.Integer(1, config=True)
    default_template = traitlets.Unicode("""#!/bin/sh
#BSUB -q {queue}
#BSUB -J bcbio-ipengine[1-{n}]
#BSUB -oo bcbio-ipengine.bsub.%%J
#BSUB -n {cores}
#BSUB -R "span[hosts=1]"
%s %s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
    """ % (' '.join(map(pipes.quote, launcher.ipengine_cmd_argv)),
           ' '.join(timeout_params)))

    def start(self, n):
        self.context["cores"] = self.cores
        return super(BcbioLSFEngineSetLauncher, self).start(n)

class BcbioLSFControllerLauncher(launcher.LSFControllerLauncher):
    default_template = traitlets.Unicode("""#!/bin/sh
#BSUB -J bcbio-ipcontroller
#BSUB -oo bcbio-ipcontroller.bsub.%%J
%s --ip=* --log-to-file --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
    """%(' '.join(map(pipes.quote, launcher.ipcontroller_cmd_argv))))
    def start(self):
        return super(BcbioLSFControllerLauncher, self).start()

class BcbioSGEEngineSetLauncher(launcher.SGEEngineSetLauncher):
    """Custom launcher handling heterogeneous clusters on SGE.
    """
    cores = traitlets.Integer(1, config=True)
    default_template = traitlets.Unicode("""#$ -V
#$ -cwd
#$ -b y
#$ -j y
#$ -S /bin/sh
#$ -q {queue}
#$ -N bcbio-ipengine
#$ -t 1-{n}
#$ -pe threaded {cores}
%s %s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""% (' '.join(map(pipes.quote, launcher.ipengine_cmd_argv)),
      ' '.join(timeout_params)))

    def start(self, n):
        self.context["cores"] = self.cores
        return super(BcbioSGEEngineSetLauncher, self).start(n)

class BcbioSGEControllerLauncher(launcher.SGEControllerLauncher):
    default_template = traitlets.Unicode(u"""#$ -V
#$ -S /bin/sh
#$ -N ipcontroller
%s --ip=* --log-to-file --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""%(' '.join(map(pipes.quote, launcher.ipcontroller_cmd_argv))))
    def start(self):
        return super(BcbioSGEControllerLauncher, self).start()

# ## Control clusters

def _start(parallel, profile, cluster_id):
    """Starts cluster from commandline.
    """
    scheduler = parallel["scheduler"].upper()
    ns = "bcbio.distributed.ipython"
    engine_class = "Bcbio%sEngineSetLauncher" % scheduler
    controller_class = "Bcbio%sControllerLauncher" % scheduler
    subprocess.check_call(
        launcher.ipcluster_cmd_argv +
        ["start",
         "--daemonize=True",
         "--IPClusterEngines.early_shutdown=180",
         "--delay=30",
         "--log-level=%s" % "WARN",
         "--profile=%s" % profile,
         #"--cluster-id=%s" % cluster_id,
         "--n=%s" % parallel["num_jobs"],
         "--%s.cores=%s" % (engine_class, parallel["cores_per_job"]),
         "--IPClusterStart.controller_launcher_class=%s.%s" % (ns, controller_class),
         "--IPClusterStart.engine_launcher_class=%s.%s" % (ns, engine_class),
         "--%sLauncher.queue=%s" % (scheduler, parallel["queue"]),
         ])

def _stop(profile, cluster_id):
    subprocess.check_call(launcher.ipcluster_cmd_argv +
                          ["stop", "--profile=%s" % profile,
                           #"--cluster-id=%s" % cluster_id
                          ])

def _is_up(profile, cluster_id, n):
    try:
        #client = Client(profile=profile, cluster_id=cluster_id)
        client = Client(profile=profile)
        up = len(client.ids)
    except IOError, msg:
        return False
    else:
        return up >= n

@contextlib.contextmanager
def cluster_view(parallel, config):
    """Provide a view on an ipython cluster for processing.

    parallel is a dictionary with:
      - scheduler: The type of cluster to start (lsf, sge).
      - num_jobs: Number of jobs to start.
      - cores_per_job: The number of cores to use for each job.
    """
    delay = 5
    max_delay = 300
    max_tries = 10
    profile = "bcbio_nextgen"
    cluster_id = str(uuid.uuid1())
    num_tries = 0
    while 1:
        try:
            _start(parallel, profile, cluster_id)
            break
        except subprocess.CalledProcessError:
            if num_tries > max_tries:
                raise
            num_tries += 1
            time.sleep(delay)
    try:
        slept = 0
        while not _is_up(profile, cluster_id, parallel["num_jobs"]):
            time.sleep(delay)
            slept += delay
            if slept > max_delay:
                raise IOError("Cluster startup timed out.")
        #client = Client(profile=profile, cluster_id=cluster_id)
        client = Client(profile=profile)
        # push config to all engines and force them to set up logging
        client[:]['config'] = config
        client[:].execute('from bcbio.log import setup_logging')
        client[:].execute('setup_logging(config)')
        client[:].execute('from bcbio.log import logger')
        yield client.load_balanced_view()
    finally:
        _stop(profile, cluster_id)

def dictadd(orig, k, v):
    """Imitates immutability by adding a key/value to a new dictionary.
    Works around not being able to deepcopy view objects; can remove this
    once we create views on demand.
    """
    view = orig.pop("view", None)
    new = copy.deepcopy(orig)
    new[k] = v
    if view:
        orig["view"] = view
        new["view"] = view
    return new

def _find_cores_per_job(fn, parallel, item_count, config):
    """Determine cores and workers to use for this stage based on function metadata.
    """
    all_cores = [1]
    for prog in (fn.metadata.get("resources", []) if hasattr(fn, "metadata") else []):
        resources = config_utils.get_resources(prog, config)
        cores = resources.get("cores")
        if cores:
            all_cores.append(cores)
    cores_per_job = max(all_cores)
    total = parallel["cores"]
    if total > cores_per_job:
        return min(total // cores_per_job, item_count), cores_per_job
    else:
        return 1, total

cur_num = 0
def _get_checkpoint_file(cdir, fn_name):
    """Retrieve checkpoint file for this step, with step number and function name.
    """
    global cur_num
    fname = os.path.join(cdir, "%s-%s.done" % (cur_num, fn_name))
    cur_num += 1
    return fname

def runner(parallel, fn_name, items, work_dir, config):
    """Run a task on an ipython parallel cluster, allowing alternative queue types.

    This will spawn clusters for parallel and custom queue types like multicore
    and high I/O tasks on demand.

    A checkpoint directory keeps track of finished tasks, avoiding spinning up clusters
    for sections that have been previous processed.
    """
    setup_logging(config)
    out = []
    checkpoint_dir = utils.safe_makedir(os.path.join(work_dir, "checkpoints_ipython"))
    checkpoint_file = _get_checkpoint_file(checkpoint_dir, fn_name)
    fn = getattr(__import__("{base}.ipythontasks".format(base=parallel["module"]),
                            fromlist=["ipythontasks"]),
                 fn_name)
    items = [x for x in items if x is not None]
    num_jobs, cores_per_job = _find_cores_per_job(fn, parallel, len(items), config)
    parallel = dictadd(parallel, "cores_per_job", cores_per_job)
    parallel = dictadd(parallel, "num_jobs", num_jobs)
    # already finished, run locally on current machine to collect details
    if os.path.exists(checkpoint_file):
        logger.info("ipython: %s -- local; checkpoint passed" % fn_name)
        for args in items:
            if args:
                data = fn(args)
                if data:
                    out.extend(data)
    # Run on a standard parallel queue
    else:
        logger.info("ipython: %s" % fn_name)
        if len(items) > 0:
            with cluster_view(parallel, config) as view:
                for data in view.map_sync(fn, items):
                    if data:
                        out.extend(data)
    with open(checkpoint_file, "w") as out_handle:
        out_handle.write("done\n")
    return out

########NEW FILE########
__FILENAME__ = ipythontasks
"""Ipython parallel ready entry points for parallel execution
"""
import contextlib

from IPython.parallel import require

from bcbio.pipeline import sample, lane, shared, variation
from bcbio.variation import realign, genotype, ensemble, recalibrate, multi
from bcbio.log import setup_logging, logger

@contextlib.contextmanager
def _setup_logging(args):
    if len(args) > 0:
        for check_i in [0, -1]:
            config = args[0][check_i]
            if isinstance(config, dict) and config.has_key("config"):
                config = config["config"]
                break
            elif isinstance(config, dict) and config.has_key("algorithm"):
                break
            else:
                config = None
        setup_logging(config)
    try:
        yield None
    except:
        logger.exception("Unexpected error")
        raise

@require(lane)
def process_lane(*args):
    with _setup_logging(args):
        return apply(lane.process_lane, *args)

@require(lane)
def process_alignment(*args):
    with _setup_logging(args):
        return apply(lane.process_alignment, *args)
process_alignment.metadata = {"resources": ["novoalign"]}

@require(sample)
def merge_sample(*args):
    with _setup_logging(args):
        return apply(sample.merge_sample, *args)

@require(sample)
def recalibrate_sample(*args):
    with _setup_logging(args):
        return apply(sample.recalibrate_sample, *args)

@require(recalibrate)
def prep_recal(*args):
    with _setup_logging(args):
        return apply(recalibrate.prep_recal, *args)
prep_recal.metadata = {"resources": ["gatk"]}

@require(recalibrate)
def write_recal_bam(*args):
    with _setup_logging(args):
        return apply(recalibrate.write_recal_bam, *args)

@require(realign)
def realign_sample(*args):
    with _setup_logging(args):
        return apply(realign.realign_sample, *args)

@require(multi)
def split_variants_by_sample(*args):
    with _setup_logging(args):
        return apply(multi.split_variants_by_sample, *args)

@require(sample)
def postprocess_variants(*args):
    with _setup_logging(args):
        return apply(sample.postprocess_variants, *args)

@require(sample)
def process_sample(*args):
    with _setup_logging(args):
        return apply(sample.process_sample, *args)

@require(sample)
def generate_bigwig(*args):
    with _setup_logging(args):
        return apply(sample.generate_bigwig, *args)

@require(shared)
def combine_bam(*args):
    with _setup_logging(args):
        return apply(shared.combine_bam, *args)

@require(genotype)
def variantcall_sample(*args):
    with _setup_logging(args):
        return apply(genotype.variantcall_sample, *args)

@require(genotype)
def combine_variant_files(*args):
    with _setup_logging(args):
        return apply(genotype.combine_variant_files, *args)

@require(variation)
def detect_sv(*args):
    with _setup_logging(args):
        return apply(variation.detect_sv, *args)

@require(ensemble)
def combine_calls(*args):
    with _setup_logging(args):
        return apply(ensemble.combine_calls, *args)

########NEW FILE########
__FILENAME__ = lsf
"""Commandline interaction with LSF schedulers.
"""
import re
import subprocess

_jobid_pat = re.compile("Job <(?P<jobid>\d+)> is")

def submit_job(scheduler_args, command):
    """Submit a job to the scheduler, returning the supplied job ID.
    """
    cl = ["bsub"] + scheduler_args + command
    status = subprocess.check_output(cl)
    match = _jobid_pat.search(status)
    return match.groups("jobid")[0]

def stop_job(jobid):
    cl = ["bkill", jobid]
    subprocess.check_call(cl)

def are_running(jobids):
    """Check if all of the submitted job IDs are running.
    """
    run_info = subprocess.check_output(["bjobs"])
    running = []
    for parts in (l.split() for l in run_info.split("\n") if l.strip()):
        if len(parts) >= 3:
            pid, _, status = parts[:3]
            if status.lower() in ["run"]:
                running.append(pid)
    want_running = set(running).intersection(set(jobids))
    return len(want_running) == len(jobids)

########NEW FILE########
__FILENAME__ = manage
"""Manage processes on a cluster

Automate:
 - starting working nodes to process the data
 - kicking off an analysis
 - cleaning up nodes on finishing

Currently works on LSF and SGE managed clusters; it's readily generalizable to
other architectures as well.
"""
import time
import math

def run_and_monitor(config, config_file, args, parallel):
    """Run a distributed analysis in s cluster environment, monitoring outputs.
    """
    args = [x for x in args if x is not None]
    cp = config["distributed"]["cluster_platform"]
    cluster = __import__("bcbio.distributed.{0}".format(cp), fromlist=[cp])
    jobids = []
    try:
        print "Starting manager"
        manager_id = start_analysis_manager(cluster, args, config)
        time.sleep(60)
        print "Starting cluster workers"
        jobids.extend(start_workers(cluster, config, config_file, parallel))
        jobids.append(manager_id)
        while not(cluster.are_running(jobids)):
            time.sleep(5)
        print "Running analysis"
        monitor_analysis(cluster, manager_id)
    finally:
        print "Cleaning up cluster workers"
        stop_workers(cluster, jobids)

def start_workers(cluster, config, config_file, parallel):
    """Initiate worker nodes on cluster, returning jobs IDs for management.
    """
    # we can manually specify workers or dynamically get as many as needed
    num_workers = config["distributed"].get("num_workers", None)
    if num_workers in [None, "all"]:
        cores_per_host = config["distributed"].get("cores_per_host", 1)
        if cores_per_host == 0:
            raise ValueError("Set num_workers or cores_per_host in YAML config")
        assert parallel["cores"] is not None, \
               "Supply workers needed if not configured in YAML"
        num_workers = int(math.ceil(float(parallel["cores"]) / cores_per_host))
    program_cl = [config["analysis"]["worker_program"], config_file]
    if parallel.get("task_module", None):
        program_cl.append("--tasks={0}".format(parallel["task_module"]))
    if parallel.get("queues", None):
        program_cl.append("--queues={0}".format(parallel["queues"]))
    args = config["distributed"]["platform_args"].split()
    return [cluster.submit_job(args, program_cl) for _ in range(num_workers)]

def start_analysis_manager(cluster, args, config):
    """Start analysis manager node on cluster.
    """
    cluster_args = config["distributed"]["platform_args"].split()
    program_cl = ["bcbio_nextgen.py"] + args + ["-t", "messaging-main"]
    job_id = cluster.submit_job(cluster_args, program_cl)
    # wait for job to start
    # Avoid this for systems where everything queues as batches
    #while not(cluster.are_running([job_id])):
    #    time.sleep(5)
    return job_id

def monitor_analysis(cluster, job_id):
    """Wait for manager cluster job to finish
    """
    while cluster.are_running([job_id]):
        time.sleep(5)

def stop_workers(cluster, jobids):
    for jobid in jobids:
        try:
            cluster.stop_job(jobid)
        except:
            pass

########NEW FILE########
__FILENAME__ = messaging
"""Run distributed tasks using the Celery distributed task queue.

http://celeryproject.org/
"""

import os
import sys
import time
import contextlib
import multiprocessing
import psutil

from mako.template import Template

from bcbio import utils
from bcbio.distributed import ipython

def parallel_runner(parallel, dirs, config, config_file):
    """Process a supplied function: single, multi-processor or distributed.
    """
    def run_parallel(fn_name, items, metadata=None):
        if parallel["type"].startswith("messaging"):
            task_module = "{base}.tasks".format(base=parallel["module"])
            runner_fn = runner(task_module, dirs, config, config_file)
            return runner_fn(fn_name, items)
        elif parallel["type"] == "ipython":
            return ipython.runner(parallel, fn_name, items, dirs["work"], config)
        else:
            out = []
            fn = getattr(__import__("{base}.multitasks".format(base=parallel["module"]),
                                    fromlist=["multitasks"]),
                         fn_name)
            cores = cores_including_resources(int(parallel["cores"]), metadata, config)
            with utils.cpmap(cores) as cpmap:
                for data in cpmap(fn, filter(lambda x: x is not None, items)):
                    if data:
                        out.extend(data)
            return out
    return run_parallel

def runner(task_module, dirs, config, config_file, wait=True):
    """Run a set of tasks using Celery, waiting for results or asynchronously.

    Initialize with the configuration and directory information,
    used to prepare a Celery configuration file and imports. It
    returns a function which acts like standard map; provide the function
    name instead of the function itself when calling.

    After name lookup, Celery runs the function in parallel; Celery servers
    can be remote or local but must have access to a shared filesystem. The
    function polls if wait is True, returning when all results are available.
    """
    with create_celeryconfig(task_module, dirs, config, config_file):
        sys.path.append(dirs["work"])
        __import__(task_module)
        tasks = sys.modules[task_module]
        from celery.task.sets import TaskSet
        def _run(fn_name, xs):
            fn = getattr(tasks, fn_name)
            job = TaskSet(tasks=[apply(fn.subtask, (x,)) for x in xs])
            result = job.apply_async()
            out = []
            if wait:
                with _close_taskset(result):
                    while not result.ready():
                        time.sleep(5)
                        if result.failed():
                            raise ValueError("Failed distributed task; cleaning up")
                    for x in result.join():
                        if x:
                            out.extend(x)
            return out
        return _run

@contextlib.contextmanager
def _close_taskset(ts):
    """Revoke existing jobs if a taskset fails; raise original error.
    """
    try:
        yield None
    except:
        try:
            raise
        finally:
            try:
                ts.revoke()
            except:
                pass

# ## Handle memory bound processes on multi-core machines

def cores_including_resources(cores, metadata, config):
    """Retrieve number of cores to use, considering program resources.
    """
    if metadata is None: metadata = {}
    required_memory = -1
    for program in metadata.get("programs", []):
        presources = config.get("resources", {}).get(program, {})
        memory = presources.get("memory", None)
        if memory:
            if memory.endswith("g"):
                memory = int(memory[:-1])
            else:
                raise NotImplementedError("Unpexpected units on memory: %s", memory)
            if memory > required_memory:
                required_memory = memory
    if required_memory > 0:
        cur_memory = _machine_memory()
        cores = min(cores,
                    int(round(float(cur_memory) / float(required_memory))))
    if cores < 1:
        cores = 1
    return cores


def _machine_memory():
    BYTES_IN_GIG = 1073741824
    free_bytes = psutil.virtual_memory().available
    return free_bytes / BYTES_IN_GIG

# ## Utility functions

_celeryconfig_tmpl = """
CELERY_IMPORTS = ("${task_import}", )

BROKER_URL = "amqp://${userid}:${password}@${host}:${port}/${rabbitmq_vhost}"
CELERY_RESULT_BACKEND= "amqp"
CELERY_TASK_SERIALIZER = "json"
CELERYD_CONCURRENCY = ${cores}
CELERY_ACKS_LATE = False
CELERYD_PREFETCH_MULTIPLIER = 1
BCBIO_CONFIG_FILE = "${config_file}"
"""

@contextlib.contextmanager
def create_celeryconfig(task_module, dirs, config, config_file):
    amqp_config = utils.read_galaxy_amqp_config(config["galaxy_config"], dirs["config"])
    if not amqp_config.has_key("host") or not amqp_config.has_key("userid"):
        raise ValueError("universe_wsgi.ini does not have RabbitMQ messaging details set")
    out_file = os.path.join(dirs["work"], "celeryconfig.py")
    amqp_config["rabbitmq_vhost"] = config["distributed"]["rabbitmq_vhost"]
    cores = config["distributed"].get("cores_per_host", 0)
    if cores < 1:
        cores = multiprocessing.cpu_count()
    amqp_config["cores"] = cores
    amqp_config["task_import"] = task_module
    amqp_config["config_file"] = config_file
    with open(out_file, "w") as out_handle:
        out_handle.write(Template(_celeryconfig_tmpl).render(**amqp_config))
    try:
        yield out_file
    finally:
        pyc_file = "%s.pyc" % os.path.splitext(out_file)[0]
        for fname in [pyc_file, out_file]:
            if os.path.exists(fname):
                os.remove(fname)

########NEW FILE########
__FILENAME__ = multitasks
"""Multiprocessing ready entry points for sample analysis.
"""
from bcbio import utils
from bcbio.pipeline import sample, lane, shared, variation
from bcbio.variation import realign, genotype, ensemble, recalibrate, multi

@utils.map_wrap
def process_lane(*args):
    return lane.process_lane(*args)

@utils.map_wrap
def process_alignment(*args):
    return lane.process_alignment(*args)

@utils.map_wrap
def merge_sample(*args):
    return sample.merge_sample(*args)

@utils.map_wrap
def prep_recal(*args):
    return recalibrate.prep_recal(*args)

@utils.map_wrap
def write_recal_bam(*args):
    return recalibrate.write_recal_bam(*args)

@utils.map_wrap
def realign_sample(*args):
    return realign.realign_sample(*args)

@utils.map_wrap
def split_variants_by_sample(*args):
    return multi.split_variants_by_sample(*args)

@utils.map_wrap
def postprocess_variants(*args):
    return sample.postprocess_variants(*args)

@utils.map_wrap
def process_sample(*args):
    return sample.process_sample(*args)

@utils.map_wrap
def generate_bigwig(*args):
    return sample.generate_bigwig(*args)

@utils.map_wrap
def combine_bam(*args):
    return shared.combine_bam(*args)

@utils.map_wrap
def variantcall_sample(*args):
    return genotype.variantcall_sample(*args)

@utils.map_wrap
def combine_variant_files(*args):
    return genotype.combine_variant_files(*args)

@utils.map_wrap
def detect_sv(*args):
    return variation.detect_sv(*args)

@utils.map_wrap
def combine_calls(*args):
    return ensemble.combine_calls(*args)

########NEW FILE########
__FILENAME__ = sge
"""Commandline interaction with SGE cluster schedulers.
"""
import re
import time
import subprocess

_jobid_pat = re.compile('Your job (?P<jobid>\d+) \("')

def submit_job(scheduler_args, command):
    """Submit a job to the scheduler, returning the supplied job ID.
    """
    cl = ["qsub", "-cwd", "-b", "y", "-j", "y"] + scheduler_args + command
    status = subprocess.check_output(cl)
    match = _jobid_pat.search(status)
    return match.groups("jobid")[0]

def stop_job(jobid):
    cl = ["qdel", jobid]
    subprocess.check_call(cl)

def are_running(jobids):
    """Check if submitted job IDs are running.
    """
    # handle SGE errors, retrying to get the current status
    max_retries = 10
    tried = 0
    while 1:
        try:
            run_info = subprocess.check_output(["qstat"])
            break
        except:
            tried += 1
            if tried > max_retries:
                raise
            time.sleep(5)
    running = []
    for parts in (l.split() for l in run_info.split("\n") if l.strip()):
        if len(parts) >= 5:
            pid, _, _, _, status = parts[:5]
            if status.lower() in ["r"]:
                running.append(pid)
    want_running = set(running).intersection(set(jobids))
    return len(want_running) == len(jobids)

def available_nodes(scheduler_args):
    """Retrieve a count of available nodes in the configured queue.
    """
    cl = ["qstat", "-f"]
    info = subprocess.check_output(cl)
    total = 0
    for i, line in enumerate(info.split("\n")):
        if i > 1 and not line.startswith("----") and line.startswith(tuple(scheduler_args)):
            _, _, counts = line.split()[:3]
            _, _, avail = counts.split("/")
            total += int(avail)
    return total if total > 0 else None

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
import os
import copy
import collections

def grouped_parallel_split_combine(args, split_fn, group_fn, parallel_fn,
                                   parallel_name, ungroup_name, combine_name,
                                   file_key, combine_arg_keys):
    """Parallel split runner that allows grouping of samples during processing.

    This builds on parallel_split_combine to provide the additional ability to
    group samples and subsequently split them back apart. This allows analysis
    of related samples together. In addition to the arguments documented in
    parallel_split_combine, this takes:

    group_fn: A function that groups samples together given their configuration
      details.
    ungroup_name: Name of a parallelizable function, defined in distributed.tasks,
      that will pull apart results from grouped analysis into individual sample
      results to combine via `combine_name`
    """
    split_args, combine_map, finished_out = _get_split_tasks(args, split_fn, file_key)
    grouped_args, grouped_info = group_fn(split_args)
    split_output = parallel_fn(parallel_name, grouped_args)
    ready_output, grouped_output = _check_group_status(split_output, grouped_info)
    ungrouped_output = parallel_fn(ungroup_name, grouped_output)
    final_output = ready_output + ungrouped_output
    combine_args, final_args = _organize_output(final_output, combine_map,
                                                file_key, combine_arg_keys)
    parallel_fn(combine_name, combine_args)
    return finished_out + final_args

def _check_group_status(xs, grouped_info):
    """Identify grouped items that need ungrouping to continue.
    """
    ready = []
    grouped = []
    for x in xs:
        if x.has_key("group"):
            x["group_orig"] = grouped_info[x["group"]]
            grouped.append([x])
        else:
            ready.append(x)
    return ready, grouped

def parallel_split_combine(args, split_fn, parallel_fn,
                           parallel_name, combine_name,
                           file_key, combine_arg_keys):
    """Split, run split items in parallel then combine to output file.

    split_fn: Split an input file into parts for processing. Returns
      the name of the combined output file along with the individual
      split output names and arguments for the parallel function.
    parallel_fn: Reference to run_parallel function that will run
      single core, multicore, or distributed as needed.
    parallel_name: The name of the function, defined in
      bcbio.distributed.tasks/multitasks/ipythontasks to run in parallel.
    combine_name: The name of the function, also from tasks, that combines
      the split output files into a final ready to run file.
    """
    split_args, combine_map, finished_out = _get_split_tasks(args, split_fn, file_key)
    split_output = parallel_fn(parallel_name, split_args)
    combine_args, final_args = _organize_output(split_output, combine_map,
                                                file_key, combine_arg_keys)
    parallel_fn(combine_name, combine_args)
    return finished_out + final_args

def _organize_output(output, combine_map, file_key, combine_arg_keys):
    """Combine output details for parallelization.

    file_key is the key name of the output file used in merging. We extract
    this file from the output data.
    """
    out_map = collections.defaultdict(list)
    extra_args = {}
    final_args = []
    already_added = []
    for data in output:
        cur_file = data[file_key]
        cur_out = combine_map[cur_file]
        out_map[cur_out].append(cur_file)
        extra_args[cur_out] = [data[x] for x in combine_arg_keys]
        data[file_key] = cur_out
        if cur_out not in already_added:
            already_added.append(cur_out)
            final_args.append([data])
    combine_args = [[v, k] + extra_args[k] for (k, v) in out_map.iteritems()]
    return combine_args, final_args

def _get_split_tasks(args, split_fn, file_key):
    """Split up input files and arguments, returning arguments for parallel processing.
    """
    split_args = []
    combine_map = {}
    finished_out = []
    for data in args:
        out_final, out_parts = split_fn(*data)
        for parts in out_parts:
            split_args.append(copy.deepcopy(data) + list(parts))
        for part_file in [x[-1] for x in out_parts]:
            combine_map[part_file] = out_final
        if len(out_parts) == 0:
            data[0][file_key] = out_final
            finished_out.append(data)
    return split_args, combine_map, finished_out

########NEW FILE########
__FILENAME__ = tasks
"""Task definitions for the Celery message queue (http://celeryproject.org/).
"""
import time

from celery.task import task

from bcbio.pipeline import sample, lane, toplevel, storage, shared, variation
from bcbio.variation import realign, genotype, ensemble, recalibrate, multi

# Global configuration for tasks in the main celeryconfig module
import celeryconfig

@task(ignore_results=True, queue="toplevel")
def analyze_and_upload(*args):
    """Run full analysis and upload results to Galaxy instance.

    Workers need to run on the machine with Galaxy installed for upload,
    but the actual processing can be distributed to multiple nodes.
    """
    config_file = celeryconfig.BCBIO_CONFIG_FILE
    remote_info = args[0]
    toplevel.analyze_and_upload(remote_info, config_file)

@task(ignore_results=True, queue="storage")
def long_term_storage(*args):
    config_file = celeryconfig.BCBIO_CONFIG_FILE
    remote_info = args[0]
    storage.long_term_storage(remote_info, config_file)

@task
def process_lane(*args):
    return lane.process_lane(*args)

@task
def process_alignment(*args):
    return lane.process_alignment(*args)

@task
def merge_sample(*args):
    return sample.merge_sample(*args)

@task
def prep_recal(*args):
    return recalibrate.prep_recal(*args)

@task
def write_recal_bam(*args):
    return recalibrate.write_recal_bam(*args)

@task
def realign_sample(*args):
    return realign.realign_sample(*args)

@task
def process_sample(*args):
    return sample.process_sample(*args)

@task
def split_variants_by_sample(*args):
    return multi.split_variants_by_sample(*args)

@task
def postprocess_variants(*args):
    return sample.postprocess_variants(*args)

@task
def generate_bigwig(*args):
    return sample.generate_bigwig(*args)

@task
def combine_bam(*args):
    return shared.combine_bam(*args)

@task
def variantcall_sample(*args):
    return genotype.variantcall_sample(*args)

@task
def combine_variant_files(*args):
    return genotype.combine_variant_files(*args)

@task
def detect_sv(*args):
    return variation.detect_sv(*args)

@task
def combine_calls(*args):
    return ensemble.combine_calls(*args)

@task
def test(x):
    print x
    time.sleep(5)
    return x

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
    exts = {".vcf": ".idx", ".bam": ".bai"}
    safe_names, orig_names = _flatten_plus_safe(rollback_files)
    _remove_files(safe_names) # remove any half-finished transactions
    try:
        if len(safe_names) == 1:
            yield safe_names[0]
        else:
            yield tuple(safe_names)
    except: # failure -- delete any temporary files
        _remove_files(safe_names)
        _remove_tmpdirs(safe_names)
        raise
    else: # worked -- move the temporary files to permanent location
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
"""Access Galaxy via the standard API.
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

    def get_libraries(self):
        return self._get("/api/libraries")

    def show_library(self, library_id):
        return self._get("/api/libraries/%s" % library_id)

    def create_library(self, name, descr="", synopsis=""):
        return self._post("/api/libraries", data = dict(name=name,
            description=descr, synopsis=synopsis))

    def library_contents(self, library_id):
        return self._get("/api/libraries/%s/contents" % library_id)

    def create_folder(self, library_id, parent_folder_id, name, descr=""):
        return self._post("/api/libraries/%s/contents" % library_id,
                data=dict(create_type="folder", folder_id=parent_folder_id,
                          name=name, description=descr))

    def show_folder(self, library_id, folder_id):
        return self._get("/api/libraries/%s/contents/%s" % (library_id,
            folder_id))

    def upload_directory(self, library_id, folder_id, directory, dbkey,
            access_role='', file_type='auto', link_data_only='link_to_files'):
        """Upload a directory of files with a specific type to Galaxy.
        """
        return self._post("/api/libraries/%s/contents" % library_id,
                data=dict(create_type='file', upload_option='upload_directory',
                    folder_id=folder_id, server_dir=directory,
                    dbkey=dbkey, roles=str(access_role),
                    file_type=file_type, link_data_only=str(link_data_only)),
                need_return=False)

    def upload_from_filesystem(self, library_id, folder_id, fname, dbkey,
            access_role='', file_type='auto', link_data_only='link_to_files'):
        """Upload to Galaxy using 'Upload files from filesystem paths'
        """
        return self._post("/api/libraries/%s/contents" % library_id,
                data=dict(create_type='file', upload_option='upload_paths',
                    folder_id=folder_id, filesystem_paths=fname,
                    dbkey=dbkey, roles=str(access_role),
                    file_type=file_type, link_data_only=str(link_data_only)),
                need_return=False)

    def get_datalibrary_id(self, name):
        """Retrieve a data library with the given name or create new.
        """
        ret_info = None
        for lib_info in self.get_libraries():
            if lib_info["name"].strip() == name.strip():
                ret_info = lib_info
                break
        # need to add a new library
        if ret_info is None:
            ret_info = self.create_library(name)[0]
        return ret_info["id"]

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
__FILENAME__ = bowtie
"""Next gen sequence alignments with Bowtie (http://bowtie-bio.sourceforge.net).
"""
import os
import subprocess

from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

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
    core_flags = ["-p", str(cores)] if cores else []
    return core_flags + qual_flags + multi_flags

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          extra_args=None, rg_name=None):
    """Do standard or paired end alignment with bowtie.
    """
    out_file = os.path.join(align_dir, "%s.sam" % out_base)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("bowtie", config)]
            cl += _bowtie_args_from_config(config)
            cl += extra_args if extra_args is not None else []
            cl += ["-q",
                   "-v", config["algorithm"]["max_errors"],
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
            subprocess.check_call(cl)
    return out_file


########NEW FILE########
__FILENAME__ = bowtie2
"""Next gen sequence alignments with Bowtie2.

http://bowtie-bio.sourceforge.net/bowtie2/index.shtml
"""
import os
import subprocess

from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.ngsalign import bowtie

def _bowtie2_args_from_config(config):
    """Configurable high level options for bowtie2.
    """
    qual_format = config["algorithm"].get("quality_format", "")
    if qual_format.lower() == "illumina":
        qual_flags = ["--phred64-quals"]
    else:
        qual_flags = []
    cores = config.get("resources", {}).get("bowtie", {}).get("cores", None)
    core_flags = ["-p", str(cores)] if cores else []
    return core_flags + qual_flags

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          extra_args=None, rg_name=None):
    """Alignment with bowtie2.
    """
    out_file = os.path.join(align_dir, "%s.sam" % out_base)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("bowtie2", config)]
            cl += _bowtie2_args_from_config(config)
            cl += extra_args if extra_args is not None else []
            cl += ["-q",
                   "--sensitive",
                   "-X", 2000, # default is too selective for most data
                   "-x", ref_file]
            if pair_file:
                cl += ["-1", fastq_file, "-2", pair_file]
            else:
                cl += ["-U", fastq_file]
            cl += ["-S", tx_out_file]
            cl = [str(i) for i in cl]
            subprocess.check_call(cl)
    return out_file

def remap_index_fn(ref_file):
    """Map sequence references to equivalent bowtie2 indexes.
    """
    return os.path.splitext(ref_file)[0].replace("/seq/", "/bowtie2/")

########NEW FILE########
__FILENAME__ = bwa
"""Next-gen alignments with BWA (http://bio-bwa.sourceforge.net/)
"""
import os
import subprocess

from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

galaxy_location_file = "bwa_index.loc"

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          rg_name=None):
    """Perform a BWA alignment, generating a SAM file.
    """
    sai1_file = os.path.join(align_dir, "%s_1.sai" % out_base)
    sai2_file = (os.path.join(align_dir, "%s_2.sai" % out_base)
                 if pair_file else None)
    sam_file = os.path.join(align_dir, "%s.sam" % out_base)
    if not file_exists(sam_file):
        if not file_exists(sai1_file):
            with file_transaction(sai1_file) as tx_sai1_file:
                _run_bwa_align(fastq_file, ref_file, tx_sai1_file, config)
        if sai2_file and not file_exists(sai2_file):
            with file_transaction(sai2_file) as tx_sai2_file:
                _run_bwa_align(pair_file, ref_file, tx_sai2_file, config)
        align_type = "sampe" if sai2_file else "samse"
        sam_cl = [config_utils.get_program("bwa", config), align_type, ref_file, sai1_file]
        if sai2_file:
            sam_cl.append(sai2_file)
        sam_cl.append(fastq_file)
        if sai2_file:
            sam_cl.append(pair_file)
        with file_transaction(sam_file) as tx_sam_file:
            with open(tx_sam_file, "w") as out_handle:
                logger.info(" ".join(sam_cl))
                subprocess.check_call(sam_cl, stdout=out_handle)
    return sam_file

def _bwa_args_from_config(config):
    cores = config.get("resources", {}).get("bwa", {}).get("cores", None)
    core_flags = ["-t", str(cores)] if cores else []
    qual_format = config["algorithm"].get("quality_format", "").lower()
    qual_flags = ["-I"] if qual_format == "illumina" else []
    return core_flags + qual_flags

def _run_bwa_align(fastq_file, ref_file, out_file, config):
    aln_cl = [config_utils.get_program("bwa", config), "aln",
              "-n %s" % config["algorithm"]["max_errors"],
              "-k %s" % config["algorithm"]["max_errors"]]
    aln_cl += _bwa_args_from_config(config)
    aln_cl += [ref_file, fastq_file]
    with open(out_file, "w") as out_handle:
        logger.info(" ".join(aln_cl))
        subprocess.check_call(aln_cl, stdout=out_handle)


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
    error_flags = ["-mm", config["algorithm"]["max_errors"]]
    cores = config.get("resources", {}).get("mosaik", {}).get("cores", None)
    core_flags = ["-p", str(cores)] if cores else []
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

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          extra_args=None, rg_name=None):
    """Alignment with MosaikAligner.
    """
    out_file = os.path.join(align_dir, "%s-align.bam" % out_base)
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
  novosort (also with license for multicore)
  samtools
"""
import os
import subprocess
import sys
import sh

from bcbio.pipeline import config_utils
from bcbio.log import logger
from bcbio.utils import (memoize_outfile, file_exists, transform_to, curdir_tmpdir)
from bcbio.distributed.transaction import file_transaction

# ## BAM realignment

def align_bam(in_bam, ref_file, names, align_dir, config):
    """Perform realignment of input BAM file, handling sorting of input/output with novosort.

    Uses unix pipes for avoid IO writing between steps:
      - novosort of input BAM to coordinates
      - alignment with novoalign
      - conversion to BAM with samtools
      - coordinate sorting with novosort
    """
    out_file = os.path.join(align_dir, "{0}-sort.bam".format(names["lane"]))
    if not file_exists(out_file):
        with curdir_tmpdir(base_dir=align_dir) as work_dir:
            with file_transaction(out_file) as tx_out_file:
                resources = config_utils.get_resources("novoalign", config)
                num_cores = resources["cores"]
                max_mem = resources.get("memory", "4G")
                read_sort = sh.novosort.bake(in_bam, c=num_cores, m=max_mem,
                                             compression=0, n=True, t=work_dir,
                                             _piped=True)
                rg_info = r"SAM '@RG\tID:{rg}\tPL:{pl}\tPU:{pu}\tSM:{sample}'".format(**names)
                align = sh.novoalign.bake(o=rg_info, d=ref_file, f="/dev/stdin", F="BAMPE",
                                          c=num_cores, _piped=True)
                to_bam = sh.samtools.view.bake(b=True, S=True, u=True,
                                               _piped=True).bake("-")
                coord_sort = sh.novosort.bake("/dev/stdin", c=num_cores, m=max_mem,
                                              o=tx_out_file, t=work_dir)
                subprocess.check_call("%s | %s | %s | %s" % (read_sort, align, to_bam, coord_sort),
                                      shell=True)
    return out_file

# ## Fastq to BAM alignment

def _novoalign_args_from_config(config):
    """Select novoalign options based on configuration parameters.
    """
    qual_format = config["algorithm"].get("quality_format", "").lower()
    qual_flags = ["-F", "ILMFQ" if qual_format == "illumina" else "STDFQ"]
    multi_mappers = config["algorithm"].get("multiple_mappers", True)
    if multi_mappers is True:
        multi_flag = "Random"
    elif isinstance(multi_mappers, basestring):
        multi_flag = multi_mappers
    else:
        multi_flag = "None"
    multi_flags = ["-r"] + multi_flag.split()
    extra_args = config["algorithm"].get("extra_align_args", [])
    return qual_flags + multi_flags + extra_args

# Tweaks to add
# -k -t 200 -K quality calibration metrics
# paired end sizes

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          extra_args=None, rg_name=None):
    """Align with novoalign.
    """
    out_file = os.path.join(align_dir, "{0}.sam".format(out_base))
    if not file_exists(out_file):
        cl = [config_utils.get_program("novoalign", config)]
        cl += _novoalign_args_from_config(config)
        cl += extra_args if extra_args is not None else []
        cl += ["-o", "SAM"]
        if rg_name:
            cl.append(r"@RG\tID:{0}".format(rg_name))
        cl += ["-d", ref_file, "-f", fastq_file]
        if pair_file:
            cl.append(pair_file)
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                logger.info(" ".join([str(x) for x in cl]))
                subprocess.check_call([str(x) for x in cl], stdout=out_handle)
    return out_file

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


def remap_index_fn(ref_file):
    """Map sequence references to equivalent novoalign indexes.
    """
    return os.path.splitext(ref_file)[0].replace("/seq/", "/novoalign/")

########NEW FILE########
__FILENAME__ = split
"""Split input FASTQ files into pieces to allow parallel cluster processing.

This is useful for speeding up alignments on a cluster at the price of
temporary increased disk usage.
"""
import os
import glob
import itertools
import operator
import time

import pysam
from Bio import Seq
from Bio.SeqIO.QualityIO import FastqGeneralIterator

from bcbio.bam.trim import _save_diskspace
from bcbio import utils, broad
from bcbio.pipeline import config_utils

def _find_current_split(in_fastq, out_dir):
    """Check for existing split files to avoid re-splitting.
    """
    base = os.path.join(out_dir,
                        os.path.splitext(os.path.basename(in_fastq))[0])
    def get_splitnum(fname):
        """Number from filename like: NA12878-E2-XPR855_2_69.fastq
        """
        base = os.path.splitext(os.path.basename(fname))[0]
        _, num = base.rsplit("_", 1)
        return int(num)
    return sorted(glob.glob("{0}*".format(base)), key=get_splitnum)

def _split_by_size(in_fastq, split_size, out_dir):
    """Split FASTQ files by a specified number of records.
    """
    existing = _find_current_split(in_fastq, out_dir)
    if len(existing) > 0:
        return existing
    def new_handle(num):
        base, ext = os.path.splitext(os.path.basename(in_fastq))
        fname = os.path.join(out_dir, "{base}_{num}{ext}".format(
            base=base, num=num, ext=ext))
        return fname, open(fname, "w")
    cur_index = 0
    cur_count = 0
    out_fname, out_handle = new_handle(cur_index)
    out_files = [out_fname]
    with open(in_fastq) as in_handle:
        for name, seq, qual in FastqGeneralIterator(in_handle):
            if cur_count < split_size:
                cur_count += 1
            else:
                cur_count = 0
                cur_index += 1
                out_handle.close()
                out_fname, out_handle = new_handle(cur_index)
                out_files.append(out_fname)
            out_handle.write("@%s\n%s\n+\n%s\n" % (name, seq, qual))
    out_handle.close()
    return out_files

def split_fastq_files(fastq1, fastq2, split_size, out_dir, config):
    """Split paired end FASTQ files into pieces for parallel analysis.
    """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    split_fastq1 = _split_by_size(fastq1, split_size, out_dir)
    _save_diskspace(fastq1, split_fastq1[0], config)
    if fastq2:
        split_fastq2 = _split_by_size(fastq2, split_size, out_dir)
        _save_diskspace(fastq2, split_fastq2[0], config)
    else:
        split_fastq2 = [None] * len(split_fastq1)
    return zip(split_fastq1, split_fastq2, [None] + [x+1 for x in range(len(split_fastq1) - 1)])

def _get_seq_qual(read):
    if read.is_reverse:
        seq = str(Seq.Seq(read.seq).reverse_complement())
        tmp = list(read.qual)
        tmp.reverse()
        qual = "".join(tmp)
    else:
        seq = read.seq
        qual = read.qual
    return seq, qual

def _find_current_bam_split(bam_file, out_dir):
    """Check for existing split files from BAM inputs, to avoid re-splitting.
    """
    base = os.path.join(out_dir,
                        os.path.splitext(os.path.basename(bam_file))[0])
    def get_pair_and_splitnum(fname):
        base = os.path.splitext(os.path.basename(fname))[0]
        _, pair, num = base.rsplit("_", 2)
        return int(num), int(pair)
    xs = []
    for fname in glob.glob("{0}_*".format(base)):
        num, pair = get_pair_and_splitnum(fname)
        xs.append((num, pair, fname))
    out = []
    for num, g in itertools.groupby(sorted(xs), operator.itemgetter(0)):
        f1, f2 = [x[-1] for x in sorted(g)]
        split = num if num > 0 else None
        out.append((f1, f2, split))
    return out

def split_bam_file(bam_file, split_size, out_dir, config):
    """Split a BAM file into paired end fastq splits based on split size.

    XXX Need to generalize for non-paired end inputs.
    """
    existing = _find_current_bam_split(bam_file, out_dir)
    if len(existing) > 0:
        return existing
    pipe = True

    utils.safe_makedir(out_dir)
    broad_runner = broad.runner_from_config(config)
    out_files = []
    def new_handle(num):
        out = []
        for pair in [1, 2]:
            fname = os.path.join(out_dir, "{base}_{pair}_{num}.fastq".format(
                base=os.path.splitext(os.path.basename(bam_file))[0], pair=pair, num=num))
            out += [fname, open(fname, "w")]
        return out
    with utils.curdir_tmpdir(base_dir=config_utils.get_resources("tmp", config).get("dir")) as tmp_dir:
        if pipe:
            sort_file = os.path.join(tmp_dir, "%s-sort.bam" %
                                     os.path.splitext(os.path.basename(bam_file))[0])
            os.mkfifo(sort_file)
            broad_runner.run_fn("picard_sort", bam_file, "queryname", sort_file,
                                compression_level=0, pipe=True)
        else:
            sort_file = os.path.join(out_dir, "%s-sort.bam" %
                                     os.path.splitext(os.path.basename(bam_file))[0])
            broad_runner.run_fn("picard_sort", bam_file, "queryname", sort_file)

        samfile = pysam.Samfile(sort_file, "rb")
        i = 0
        num = 0
        f1, out_handle1, f2, out_handle2 = new_handle(num)
        out_files.append([f1, f2, None])
        for x1, x2 in utils.partition_all(2, samfile):
            x1_seq, x1_qual = _get_seq_qual(x1)
            out_handle1.write("@%s/1\n%s\n+\n%s\n" % (i, x1_seq, x1_qual))
            x2_seq, x2_qual = _get_seq_qual(x2)
            out_handle2.write("@%s/2\n%s\n+\n%s\n" % (i, x2_seq, x2_qual))
            i += 1
            if i % split_size == 0:
                num += 1
                out_handle1.close()
                out_handle2.close()
                f1, out_handle1, f2, out_handle2 = new_handle(num)
                out_files.append([f1, f2, num])
        out_handle1.close()
        out_handle2.close()
        samfile.close()
        if pipe:
            os.unlink(sort_file)
        else:
            utils.save_diskspace(sort_file, "Split to {}".format(out_files[0][0]), config)
    return out_files

def split_read_files(fastq1, fastq2, split_size, out_dir, config):
    """Split input reads for parallel processing, dispatching on input type.
    """
    if fastq1.endswith(".bam") and fastq2 is None:
        return split_bam_file(fastq1, split_size, out_dir, config)
    else:
        return split_fastq_files(fastq1, fastq2, split_size, out_dir, config)

########NEW FILE########
__FILENAME__ = tophat
"""Next-gen alignments with TopHat a spliced read mapper for RNA-seq experiments.

http://tophat.cbcb.umd.edu
"""
import sh
import os
import shutil
import subprocess
from contextlib import closing
import glob
import pysam
import numpy
from bcbio.pipeline import config_utils
from bcbio.ngsalign import bowtie, bowtie2
from bcbio.utils import safe_makedir, file_exists, get_in, flatten
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger


_out_fnames = ["accepted_hits.sam", "junctions.bed",
               "insertions.bed", "deletions.bed"]


def _set_quality_flag(options, config):
    qual_format = config["algorithm"].get("quality_format", None)
    if qual_format is None or qual_format.lower() == "illumina":
        options["solexa1.3-quals"] = True
    elif qual_format == "solexa":
        options["solexa-quals"] = True
    return options


def _set_gtf(options, config):
    gtf_file = config.get("gtf", None)
    if gtf_file is not None:
        options["GTF"] = gtf_file
    return options


def _set_cores(options, config):
    cores = config.get("resources", {}).get("tophat", {}).get("cores", None)
    if cores and "num-threads" not in options:
        options["num-threads"] = cores
    return options


def tophat_align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
                 rg_name=None):
    """
    run alignment using Tophat v2
    """
    options = get_in(config, ("resources", "tophat", "options"), {})
    options = _set_quality_flag(options, config)
    options = _set_gtf(options, config)
    options = _set_cores(options, config)

    # select the correct bowtie option to use; tophat2 is ignoring this option
    if _tophat_major_version(config) == 2 and _ref_version(ref_file) == 1:
        options["bowtie1"] = True

    out_dir = os.path.join(align_dir, "%s_tophat" % out_base)
    out_file = os.path.join(out_dir, _out_fnames[0])
    if file_exists(out_file):
        return out_file
    files = [ref_file, fastq_file]
    if not file_exists(out_file):
        with file_transaction(out_dir) as tx_out_dir:
            safe_makedir(tx_out_dir)
            if pair_file:
                d, d_stdev = _estimate_paired_innerdist(fastq_file, pair_file,
                                                        ref_file, out_base,
                                                        tx_out_dir, config)
                options["mate-inner-dist"] = d
                options["mate-std-dev"] = d_stdev
                files.append(pair_file)
            options["output-dir"] = tx_out_dir
            options["no-convert-bam"] = True
            tophat_runner = sh.Command(config_utils.get_program("tophat",
                                                                config))
            ready_options = {}
            for k, v in options.iteritems():
                ready_options[k.replace("-", "_")] = v
            # tophat requires options before arguments,
            # otherwise it silently ignores them
            tophat_ready = tophat_runner.bake(**ready_options)
            tophat_ready(*files)
    out_file_final = os.path.join(out_dir, "%s.sam" % out_base)
    os.symlink(os.path.basename(out_file), out_file_final)
    return out_file_final

def align(fastq_file, pair_file, ref_file, out_base, align_dir, config,
          rg_name=None):

    out_dir = os.path.join(align_dir, "%s_tophat" % out_base)
    out_file = os.path.join(out_dir, _out_fnames[0])

    if file_exists(out_file):
        return out_file

    if not _bowtie_ref_match(ref_file, config):
        logger.error("Bowtie version %d was detected but the reference "
                     "file %s is built for version %d. Download version "
                     "%d or build it with bowtie-build."
                     % (_bowtie_major_version(config), ref_file,
                        _ref_version(ref_file),
                        _bowtie_major_version(config)))
        exit(1)

    out_files = tophat_align(fastq_file, pair_file, ref_file, out_base,
                             align_dir, config, rg_name=None)

    return out_files


def _estimate_paired_innerdist(fastq_file, pair_file, ref_file, out_base,
                               out_dir, config):
    """Use Bowtie to estimate the inner distance of paired reads.
    """
    # skip initial reads for large file, but not for smaller
    dists = _bowtie_for_innerdist("1000000", fastq_file, pair_file, ref_file,
                                  out_base, out_dir, config)
    if len(dists) == 0:
        dists = _bowtie_for_innerdist("1", fastq_file, pair_file, ref_file,
                                      out_base, out_dir, config, True)
    return int(round(numpy.mean(dists))), int(round(numpy.std(dists)))


def _bowtie_for_innerdist(start, fastq_file, pair_file, ref_file, out_base,
                          out_dir, config, remove_workdir=False):
    work_dir = os.path.join(out_dir, "innerdist_estimate")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    safe_makedir(work_dir)
    extra_args = ["-s", str(start), "-u", "250000"]
    bowtie_runner = _select_bowtie_version(config)
    out_sam = bowtie_runner.align(fastq_file, pair_file, ref_file, out_base,
                                  work_dir, config, extra_args)
    dists = []
    with closing(pysam.Samfile(out_sam)) as work_sam:
        for read in work_sam:
            if read.is_proper_pair and read.is_read1:
                dists.append(abs(read.isize) - 2 * read.rlen)
    return dists


def _bowtie_major_version(config):
    bowtie_runner = sh.Command(config_utils.get_program("bowtie", config,
                                                        default="bowtie2"))
    """
    bowtie --version returns strings like this:
    bowtie version 0.12.7
    32-bit
    Built on Franklin.local
    Tue Sep  7 14:25:02 PDT 2010
    """
    version_line = str(bowtie_runner(version=True)).split("\n")[0]
    version_string = version_line.strip().split()[2]
    major_version = int(version_string.split(".")[0])
    # bowtie version 1 has a leading character of 0
    if major_version == 0:
        major_version += 1
    return major_version


def _tophat_major_version(config):
    tophat_runner = sh.Command(config_utils.get_program("tophat", config,
                                                        default="tophat"))

    # tophat --version returns strings like this: Tophat v2.0.4
    version_string = str(tophat_runner(version=True)).strip().split()[1]
    major_version = int(version_string.split(".")[0][1:])
    return major_version


def _bowtie_ref_match(ref_file, config):
    return _ref_version(ref_file) == _bowtie_major_version(config)


def _select_bowtie_version(config):
    if _bowtie_major_version(config) == 1:
        return bowtie
    else:
        return bowtie2


def _ref_version(ref_file):
    _, ext = os.path.splitext(glob.glob(ref_file + "*")[0])
    if ext == ".ebwt":
        return 1
    elif ext == ".bt2":
        return 2
    else:
        logger.error("Cannot detect which reference version %s is. "
                     "Should end in either .ebwt (bowtie) or .bt2 "
                     "(bowtie2)." % (ref_file))
        exit(1)

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
import os
import re
from collections import namedtuple

from Bio.SeqIO.QualityIO import FastqGeneralIterator

from bcbio import utils, broad
from bcbio.ngsalign import bowtie, bwa, tophat, bowtie2, mosaik, novoalign
from bcbio.distributed.transaction import file_transaction

# Define a next-generation sequencing tool to plugin:
# align_fn -- runs an aligner and generates SAM output
# galaxy_loc_file -- name of a Galaxy location file to retrieve
#  the genome index location
# remap_index_fn -- Function that will take the location provided
#  from galaxy_loc_file and find the actual location of the index file.
#  This is useful for indexes that don't have an associated location file
#  but are stored in the same directory structure.
NgsTool = namedtuple("NgsTool", ["align_fn", "bam_align_fn", "galaxy_loc_file",
                                 "remap_index_fn"])

base_location_file = "sam_fa_indices.loc"
_tools = {
    "bowtie": NgsTool(bowtie.align, None, bowtie.galaxy_location_file, None),
    "bowtie2": NgsTool(bowtie2.align, None, base_location_file, bowtie2.remap_index_fn),
    "bwa": NgsTool(bwa.align, None, bwa.galaxy_location_file, None),
    "mosaik": NgsTool(mosaik.align, None, mosaik.galaxy_location_file, None),
    "novoalign": NgsTool(novoalign.align, novoalign.align_bam, base_location_file, novoalign.remap_index_fn),
    "tophat": NgsTool(tophat.align, None, base_location_file, bowtie2.remap_index_fn),
    "samtools": NgsTool(None, None, base_location_file, None),
    }

metadata = {"support_bam": [k for k, v in _tools.iteritems() if v.bam_align_fn is not None]}

def align_to_sort_bam(fastq1, fastq2, genome_build, aligner,
                      lane_name, sample_name, dirs, config, dir_ext=""):
    """Align to the named genome build, returning a sorted BAM file.
    """
    names = {"rg": lane_name.split("_")[0],
             "sample": sample_name,
             "lane": lane_name,
             "pl": config["algorithm"]["platform"].lower(),
             "pu": (lane_name.rsplit("_", 1)[0]
                    if re.search(r"_s\d+$", lane_name) is not None
                    else lane_name)}
    align_dir = utils.safe_makedir(os.path.join(dirs["work"], "align", sample_name, dir_ext))
    align_ref, sam_ref = get_genome_ref(genome_build, aligner, dirs["galaxy"])
    if fastq1.endswith(".bam"):
        return _align_from_bam(fastq1, aligner, align_ref, names, align_dir, config)
    else:
        return _align_from_fastq(fastq1, fastq2, aligner, align_ref, sam_ref, names,
                                 align_dir, config)

def _align_from_bam(fastq1, aligner, align_ref, names, align_dir, config):
    align_fn = _tools[aligner].bam_align_fn
    return align_fn(fastq1, align_ref, names, align_dir, config)

def _align_from_fastq(fastq1, fastq2, aligner, align_ref, sam_ref, names,
                      align_dir, config):
    """Align from fastq inputs, producing sorted BAM output.
    """
    align_fn = _tools[aligner].align_fn
    sam_file = align_fn(fastq1, fastq2, align_ref, names["lane"], align_dir, config,
                        rg_name=names["rg"])
    if fastq2 is None and aligner in ["bwa", "bowtie2"]:
        fastq1 = _remove_read_number(fastq1, sam_file)
    sort_method = config["algorithm"].get("bam_sort", "coordinate")
    if sort_method == "queryname":
        return sam_to_querysort_bam(sam_file, config)
    else:
        # remove split information if present for platform unit
        return sam_to_sort_bam(sam_file, sam_ref, fastq1, fastq2, names["sample"],
                               names["rg"], names["pu"], config)

def _remove_read_number(in_file, sam_file):
    """Work around problem with MergeBamAlignment with BWA and single end reads.

    Need to remove read number ends from Fastq to match BWA stripping of numbers.

    http://sourceforge.net/mailarchive/forum.php?thread_name=87bosvbbqz.fsf%
    40fastmail.fm&forum_name=samtools-help
    http://sourceforge.net/mailarchive/forum.php?thread_name=4EB03C42.2060405%
    40broadinstitute.org&forum_name=samtools-help
    """
    out_file = os.path.join(os.path.dirname(sam_file),
                            "%s-safe%s" % os.path.splitext(os.path.basename(in_file)))
    if not os.path.exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            with open(in_file) as in_handle:
                with open(tx_out_file, "w") as out_handle:
                    for i, (name, seq, qual) in enumerate(FastqGeneralIterator(in_handle)):
                        if i == 0 and not name.endswith("/1"):
                            out_file = in_file
                            break
                        else:
                            name = name.rsplit("/", 1)[0]
                            out_handle.write("@%s\n%s\n+\n%s\n" % (name, seq, qual))
    return out_file

def sam_to_querysort_bam(sam_file, config):
    """Convert SAM file directly to a query sorted BAM without merging of FASTQ reads.

    This allows merging of multiple mappers which do not work with MergeBamAlignment.
    """
    runner = broad.runner_from_config(config)
    out_file = "{}.bam".format(os.path.splitext(sam_file)[0])
    return runner.run_fn("picard_sort", sam_file, "queryname", out_file)

def sam_to_sort_bam(sam_file, ref_file, fastq1, fastq2, sample_name,
                    rg_name, lane_name, config):
    """Convert SAM file to merged and sorted BAM file.
    """
    picard = broad.runner_from_config(config)
    platform = config["algorithm"]["platform"]
    qual_format = config["algorithm"].get("quality_format", None)
    base_dir = os.path.dirname(sam_file)

    picard.run_fn("picard_index_ref", ref_file)
    out_fastq_bam = picard.run_fn("picard_fastq_to_bam", fastq1, fastq2,
                                  base_dir, platform, sample_name, rg_name, lane_name,
                                  qual_format)
    out_bam = picard.run_fn("picard_sam_to_bam", sam_file, out_fastq_bam, ref_file,
                            fastq2 is not None)
    sort_bam = picard.run_fn("picard_sort", out_bam)

    utils.save_diskspace(sam_file, "SAM converted to BAM", config)
    utils.save_diskspace(out_fastq_bam, "Combined into output BAM %s" % out_bam, config)
    utils.save_diskspace(out_bam, "Sorted to %s" % sort_bam, config)
    # merge FASTQ files, only if barcoded samples in the work directory
    if (os.path.commonprefix([fastq1, sort_bam]) ==
             os.path.split(os.path.dirname(sort_bam))[0]
          and not config["algorithm"].get("upload_fastq", True)):
        utils.save_diskspace(fastq1, "Merged into output BAM %s" % out_bam, config)
        if fastq2:
            utils.save_diskspace(fastq2, "Merged into output BAM %s" % out_bam, config)
    return sort_bam

def get_genome_ref(genome_build, aligner, galaxy_base):
    """Retrieve the reference genome file location from galaxy configuration.
    """
    if not genome_build:
        return (None, None)
    ref_dir = os.path.join(galaxy_base, "tool-data")
    out_info = []
    for ref_get in [aligner, "samtools"]:
        if not ref_get:
            out_info.append(None)
            continue
        ref_file = os.path.join(ref_dir, _tools[ref_get].galaxy_loc_file)
        cur_ref = None
        with open(ref_file) as in_handle:
            for line in in_handle:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split()
                    if parts[0] == "index":
                        parts = parts[1:]
                    if parts[0] == genome_build:
                        cur_ref = parts[-1]
                        break
        if cur_ref is None:
            raise IndexError("Genome %s not found in %s" % (genome_build,
                ref_file))
        remap_fn = _tools[ref_get].remap_index_fn
        if remap_fn:
            cur_ref = remap_fn(cur_ref)
        out_info.append(utils.add_full_path(cur_ref, ref_dir))

    if len(out_info) != 2:
        raise ValueError("Did not find genome reference for %s %s" %
                (genome_build, aligner))
    else:
        return tuple(out_info)

########NEW FILE########
__FILENAME__ = config_utils
"""Loads configurations from .yaml files and expands environment variables.
"""
import os
import glob
import yaml

def load_config(config_file):
    """Load YAML config file, replacing environmental variables.
    """
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)

    for field, setting in config.items():
        if isinstance(config[field], dict):
            for sub_field, sub_setting in config[field].items():
                config[field][sub_field] = expand_path(sub_setting)
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
    resources = config.get("resources", {}).get(name, {})
    if "jvm_opts" not in resources:
        java_memory = config["algorithm"].get("java_memory", None)
        if java_memory:
            resources["jvm_opts"] = ["-Xms%s" % java_memory, "-Xmx%s" % java_memory]
    return resources

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
            if not pconfig.has_key(key):
                pconfig[key] = old_config
    if ptype == "cmd":
        return _get_program_cmd(name, pconfig, default)
    elif ptype == "dir":
        return _get_program_dir(name, pconfig)
    else:
        raise ValueError("Don't understand program type: %s" % ptype)

def _get_program_cmd(name, config, default):
    """Retrieve commandline of a program.
    """
    if config is None:
        return name
    elif isinstance(config, basestring):
        return config
    elif config.has_key("cmd"):
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
    elif config.has_key("dir"):
        return config["dir"]
    else:
        raise ValueError("Could not find directory in config for %s" % name)

def get_jar(base_name, dname):
    """Retrieve a jar in the provided directory
    """
    jars = glob.glob(os.path.join(dname, "%s*.jar" % base_name))
    if len(jars) == 1:
        return jars[0]
    else:
        raise ValueError("Could not find java jar %s in %s: %s" % (
            base_name, dname, jars))

########NEW FILE########
__FILENAME__ = demultiplex
"""Pipeline support for barcode analysis and de-mulitplexing.
"""
import os
import copy
import subprocess

from Bio import SeqIO
from Bio.SeqIO.QualityIO import FastqGeneralIterator

from bcbio import utils
from bcbio.pipeline.fastq import get_fastq_files
from bcbio.distributed.transaction import file_transaction

def split_by_barcode(fastq1, fastq2, multiplex, base_name, dirs, config):
    """Split a fastq file into multiplex pieces using barcode details.
    """
    unmatched_str = "unmatched"
    if len(multiplex) == 1 and multiplex[0]["barcode_id"] is None:
        return {None: (fastq1, fastq2)}
    bc_dir = os.path.join(dirs["work"], "%s_barcode" % base_name)
    nomatch_file = "%s_%s_1_fastq.txt" % (base_name, unmatched_str)
    metrics_file = "%s_bc.metrics" % base_name
    out_files = []
    for info in multiplex:
        fq_fname = lambda x: os.path.join(bc_dir, "%s_%s_%s_fastq.txt" %
                             (base_name, info["barcode_id"], x))
        bc_file1 = fq_fname("1")
        bc_file2 = fq_fname("2") if fastq2 else None
        out_files.append((info["barcode_id"], bc_file1, bc_file2))
    if not utils.file_exists(bc_dir):
        with file_transaction(bc_dir) as tx_bc_dir:
            with utils.chdir(tx_bc_dir):
                tag_file, need_trim = _make_tag_file(multiplex, unmatched_str, config)
                cl = ["barcode_sort_trim.py", tag_file,
                      "%s_--b--_--r--_fastq.txt" % base_name,
                      fastq1]
                if fastq2:
                    cl.append(fastq2)
                cl.append("--mismatch=%s" % config["algorithm"]["bc_mismatch"])
                cl.append("--metrics=%s" % metrics_file)
                if int(config["algorithm"]["bc_read"]) > 1:
                    cl.append("--read=%s" % config["algorithm"]["bc_read"])
                if int(config["algorithm"]["bc_position"]) == 5:
                    cl.append("--five")
                if config["algorithm"].get("bc_allow_indels", True) is False:
                    cl.append("--noindel")
                if "bc_offset" in config["algorithm"]:
                    cl.append("--bc_offset=%s" % config["algorithm"]["bc_offset"])
                subprocess.check_call(cl)
    else:
        with utils.curdir_tmpdir() as tmp_dir:
            with utils.chdir(tmp_dir):
                _, need_trim = _make_tag_file(multiplex, unmatched_str, config)
    out = {}
    for b, f1, f2 in out_files:
        if os.path.exists(f1):
            if need_trim.has_key(b):
                f1, f2 = _basic_trim(f1, f2, need_trim[b], config)
            out[b] = (f1, f2)
    return out

def _basic_trim(f1, f2, trim_seq, config):
    """Chop off barcodes on sequences based on expected sequence size.
    """
    work_file, is_first = ((f2, False) if int(config["algorithm"]["bc_read"]) == 2
                           else (f1, True))
    assert work_file is not None and os.path.exists(work_file)
    trim_file = "%s_trim_fastq.txt" % work_file.split("_fastq.txt")[0]
    if not os.path.exists(trim_file):
        if int(config["algorithm"]["bc_position"] == 5):
            def trimmer(x):
                return x[len(trim_seq):]
        else:
            def trimmer(x):
                return x[:-len(trim_seq)]
        with open(trim_file, "w") as out_handle:
            with open(work_file) as in_handle:
                for name, seq, qual in FastqGeneralIterator(in_handle):
                    out_handle.write("@%s\n%s\n+\n%s\n" % (name, trimmer(seq),
                                                           trimmer(qual)))
    return (trim_file, f2) if is_first else (f1, trim_file)

def _make_tag_file(barcodes, unmatched_str, config):
    need_trim = {}
    tag_file = "%s-barcodes.cfg" % barcodes[0].get("barcode_type", "barcode")
    barcodes = _adjust_illumina_tags(barcodes,config)
    with open(tag_file, "w") as out_handle:
        for bc in barcodes:
            if bc["barcode_id"] != unmatched_str:
                out_handle.write("%s %s\n" % (bc["barcode_id"], bc["sequence"]))
            else:
                need_trim[bc["barcode_id"]] = bc["sequence"]
    return tag_file, need_trim

def _adjust_illumina_tags(barcodes, config):
    """Handle additional trailing A in Illumina barcodes.

    Illumina barcodes are listed as 6bp sequences but have an additional
    A base when coming off on the sequencer. This checks for this case and
    adjusts the sequences appropriately if needed. When the configuration 
    option to disregard the additional A in barcode matching is set, the
    added base is an ambigous N to avoid an additional mismatch.
    If the configuration uses bc_offset to adjust the comparison location,
    we do not add trailing base and rely on the configuration setting.
    """
    illumina_size = 7
    all_illumina = True
    need_a = False
    for bc in barcodes:
        if (bc.get("barcode_type", "illumina").lower().find("illumina") == -1 or
            int(config["algorithm"].get("bc_offset", 0)) == 1):
            all_illumina = False
            break
        if (not bc["sequence"].upper().endswith("A") or
            len(bc["sequence"]) < illumina_size):
            need_a = True
    if all_illumina and need_a:
        # If we skip the trailing A in barcode matching, set as ambiguous base
        extra_base = "N" if config["algorithm"].get("bc_illumina_no_trailing", False) else "A"
        new = []
        for bc in barcodes:
            new_bc = copy.deepcopy(bc)
            new_bc["sequence"] = "{seq}{extra_base}".format(seq=new_bc["sequence"],
                                                            extra_base=extra_base)
            new.append(new_bc)
        barcodes = new
    return barcodes

def add_multiplex_across_lanes(run_items, fastq_dir, fc_name):
    """Add multiplex information to control and non-multiplexed lanes.

    Illumina runs include barcode reads for non-multiplex lanes, and the
    control, when run on a multiplexed flow cell. This checks for this
    situation and adds details to trim off the extra bases.
    """
    if fastq_dir:
        fastq_dir = utils.add_full_path(fastq_dir)
    # determine if we have multiplexes and collect expected size
    fastq_sizes = []
    tag_sizes = []
    has_barcodes = False
    for xs in run_items:
        if len(xs) > 1:
            has_barcodes = True
            tag_sizes.extend([len(x["sequence"]) for x in xs])
            fastq_sizes.append(_get_fastq_size(xs[0], fastq_dir, fc_name))
    if not has_barcodes: # nothing to worry about
        return run_items
    fastq_sizes = list(set(fastq_sizes))

    # discard 0 sizes to handle the case where lane(s) are empty or failed
    try:
        fastq_sizes.remove(0)
    except ValueError: pass

    tag_sizes = list(set(tag_sizes))
    final_items = []
    for xs in run_items:
        if len(xs) == 1 and xs[0]["barcode_id"] is None:
            assert len(fastq_sizes) == 1, \
                   "Multi and non-multiplex reads with multiple sizes"
            expected_size = fastq_sizes[0]
            assert len(tag_sizes) == 1, \
                   "Expect identical tag size for a flowcell"
            tag_size = tag_sizes[0]
            this_size = _get_fastq_size(xs[0], fastq_dir, fc_name)
            if this_size == expected_size:
                x = xs[0]
                x["barcode_id"] = "trim"
                x["sequence"] = "N" * tag_size
                xs = [x]
            else:
                assert this_size == expected_size - tag_size, \
                       "Unexpected non-multiplex sequence"
        final_items.append(xs)
    return final_items

def _get_fastq_size(item, fastq_dir, fc_name):
    """Retrieve the size of reads from the first flowcell sequence.
    """
    (fastq1, _) = get_fastq_files(fastq_dir, None, item, fc_name)
    with open(fastq1) as in_handle:
        try:
            rec = SeqIO.parse(in_handle, "fastq").next()
            size = len(rec.seq)
        except StopIteration:
            size = 0
    return size


########NEW FILE########
__FILENAME__ = fastq
"""Pipeline utilities to retrieve FASTQ formatted files for processing.
"""
import os
import glob
import subprocess
import contextlib
import collections

import pysam

from bcbio import broad
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import alignment
from bcbio.utils import file_exists, safe_makedir

def get_fastq_files(directory, work_dir, item, fc_name, bc_name=None,
                    config=None):
    """Retrieve fastq files for the given lane, ready to process.
    """
    if item.has_key("files") and bc_name is None:
        names = item["files"]
        if isinstance(names, basestring):
            names = [names]
        files = [x if os.path.isabs(x) else os.path.join(directory, x) for x in names]
    else:
        assert fc_name is not None
        lane = item["lane"]
        if bc_name:
            glob_str = "%s_*%s_%s_*_fastq.txt" % (lane, fc_name, bc_name)
        else:
            glob_str = "%s_*%s*_fastq.txt" % (lane, fc_name)
        files = glob.glob(os.path.join(directory, glob_str))
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
        elif fname.endswith(".bam"):
            if _pipeline_needs_fastq(config, item):
                ready_files = convert_bam_to_fastq(fname, work_dir, config)
            else:
                ready_files = [fname]
        else:
            assert os.path.exists(fname), fname
            ready_files.append(fname)
    ready_files = [x for x in ready_files if x is not None]
    return ready_files[0], (ready_files[1] if len(ready_files) > 1 else None)

def _pipeline_needs_fastq(config, item):
    """Determine if the pipeline can proceed with a BAM file, or needs fastq conversion.
    """
    aligner = config["algorithm"].get("aligner")
    has_multiplex = item.get("multiplex") is not None
    do_split = config["algorithm"].get("align_split_size") is not None
    support_bam = aligner in alignment.metadata.get("support_bam", [])
    return (has_multiplex or
            (aligner and not do_split and not support_bam))

def convert_bam_to_fastq(in_file, work_dir, config):
    """Convert BAM input file into FASTQ files.
    """
    out_dir = safe_makedir(os.path.join(work_dir, "fastq_convert"))
    out_files = [os.path.join(out_dir, "{0}_{1}.fastq".format(
                 os.path.splitext(os.path.basename(in_file))[0], x))
                 for x in ["1", "2"]]
    if _is_paired(in_file):
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

def _is_paired(bam_file):
    # XXX need development version of pysam for this to work on
    # fastq files without headers (ie. FastqToSam)
    # Instead return true by default and then check after output
    return True
    with contextlib.closing(pysam.Samfile(bam_file, "rb")) as work_bam:
        for read in bam_file:
            return read.is_paired

########NEW FILE########
__FILENAME__ = lane
"""Top level driver functionality for processing a sequencing lane.
"""
import os
import copy

from bcbio.log import logger
from bcbio import utils
from bcbio.pipeline.fastq import get_fastq_files
from bcbio.pipeline.demultiplex import split_by_barcode
from bcbio.pipeline.alignment import align_to_sort_bam
from bcbio.ngsalign.split import split_read_files
from bcbio.bam.trim import brun_trim_fastq

def _prep_fastq_files(item, bc_files, dirs, config):
    """Potentially prepare input FASTQ files for processing.
    """
    fastq1, fastq2 = bc_files[item["barcode_id"]]
    split_size = config.get("distributed", {}).get("align_split_size",
                                                   config["algorithm"].get("align_split_size", None))
    if split_size:
        split_dir = utils.safe_makedir(os.path.join(dirs["work"], "align_splitprep", item["description"]))
        return split_read_files(fastq1, fastq2, split_size, split_dir, config)
    else:
        return [[fastq1, fastq2, None]]

def process_lane(lane_items, fc_name, fc_date, dirs, config):
    """Prepare lanes, potentially splitting based on barcodes.
    """
    lane_name = "%s_%s_%s" % (lane_items[0]['lane'], fc_date, fc_name)
    logger.info("Demulitplexing %s" % lane_name)
    full_fastq1, full_fastq2 = get_fastq_files(dirs["fastq"], dirs["work"],
                                               lane_items[0], fc_name,
                                               config=_update_config_w_custom(config, lane_items[0]))
    bc_files = split_by_barcode(full_fastq1, full_fastq2, lane_items,
                                lane_name, dirs, config)
    out = []
    for item in lane_items:
        config = _update_config_w_custom(config, item)
        # Can specify all barcodes but might not have actual sequences
        # Would be nice to have a good way to check this is okay here.
        if bc_files.has_key(item["barcode_id"]):
            for fastq1, fastq2, lane_ext in _prep_fastq_files(item, bc_files, dirs, config):
                cur_lane_name = lane_name
                cur_lane_desc = item["description"]
                if item.get("name", "") and config["algorithm"].get("include_short_name", True):
                    cur_lane_desc = "%s : %s" % (item["name"], cur_lane_desc)
                if item["barcode_id"] is not None:
                    cur_lane_name += "_%s" % (item["barcode_id"])
                if lane_ext is not None:
                    cur_lane_name += "_s{0}".format(lane_ext)
                if config["algorithm"].get("trim_reads", False):
                    trim_info = brun_trim_fastq([x for x in [fastq1, fastq2] if x is not None],
                                                dirs, config)
                    fastq1 = trim_info[0]
                    if fastq2 is not None:
                        fastq2 = trim_info[1]
                out.append((fastq1, fastq2, item, cur_lane_name, cur_lane_desc,
                            dirs, config))
    return out


def process_alignment(fastq1, fastq2, info, lane_name, lane_desc,
                      dirs, config):
    """Do an alignment of fastq files, preparing a sorted BAM output file.
    """
    aligner = config["algorithm"].get("aligner", None)
    out_bam = ""
    if os.path.exists(fastq1) and aligner:
        logger.info("Aligning lane %s with %s aligner" % (lane_name, aligner))
        out_bam = align_to_sort_bam(fastq1, fastq2, info["genome_build"], aligner,
                                    lane_name, lane_desc, dirs, config)
    elif os.path.exists(fastq1) and fastq1.endswith(".bam"):
        out_bam = fastq1
    return [{"fastq": [fastq1, fastq2], "out_bam": out_bam, "info": info,
             "config": config}]

def _update_config_w_custom(config, lane_info):
    """Update the configuration for this lane if a custom analysis is specified.
    """
    name_remaps = {"variant": ["SNP calling", "variant"],
                   "SNP calling": ["SNP calling", "variant"]}
    config = copy.deepcopy(config)
    base_name = lane_info.get("analysis")
    for analysis_type in name_remaps.get(base_name, [base_name]):
        custom = config["custom_algorithms"].get(analysis_type, None)
        if custom:
            for key, val in custom.iteritems():
                config["algorithm"][key] = val
    # apply any algorithm details specified with the lane
    for key, val in lane_info.get("algorithm", {}).iteritems():
        config["algorithm"][key] = val
    return config

########NEW FILE########
__FILENAME__ = main
"""Main entry point for distributed next-gen sequencing pipelines.

Handles running the full pipeline based on instructions
"""
import os
import sys
import math
import argparse

from bcbio.solexa.flowcell import get_fastq_dir
from bcbio import utils
from bcbio.log import setup_logging
from bcbio.distributed.messaging import parallel_runner
from bcbio.pipeline.run_info import get_run_info
from bcbio.pipeline.demultiplex import add_multiplex_across_lanes
from bcbio.pipeline.merge import organize_samples
from bcbio.pipeline.qcsummary import write_metrics, write_project_summary
from bcbio.variation.realign import parallel_realign_sample
from bcbio.variation.genotype import parallel_variantcall, combine_multiple_callers
from bcbio.variation import ensemble, recalibrate

def run_main(config, config_file, work_dir, parallel,
             fc_dir=None, run_info_yaml=None):
    """Run toplevel analysis, processing a set of input files.

    config_file -- Main YAML configuration file with system parameters
    fc_dir -- Directory of fastq files to process
    run_info_yaml -- YAML configuration file specifying inputs to process
    """
    setup_logging(config)
    fc_name, fc_date, run_info = get_run_info(fc_dir, config, run_info_yaml)
    fastq_dir, galaxy_dir, config_dir = _get_full_paths(get_fastq_dir(fc_dir) if fc_dir else None,
                                                        config, config_file)
    config_file = os.path.join(config_dir, os.path.basename(config_file))
    dirs = {"fastq": fastq_dir, "galaxy": galaxy_dir,
            "work": work_dir, "flowcell": fc_dir, "config": config_dir}
    config = _set_resources(parallel, config)
    run_parallel = parallel_runner(parallel, dirs, config, config_file)

    # process each flowcell lane
    run_items = add_multiplex_across_lanes(run_info["details"], dirs["fastq"], fc_name)
    lanes = ((info, fc_name, fc_date, dirs, config) for info in run_items)
    lane_items = run_parallel("process_lane", lanes)
    align_items = run_parallel("process_alignment", lane_items)
    # process samples, potentially multiplexed across multiple lanes
    samples = organize_samples(align_items, dirs, config_file)
    samples = run_parallel("merge_sample", samples)
    samples = run_parallel("prep_recal", samples)
    samples = recalibrate.parallel_write_recal_bam(samples, run_parallel)
    samples = parallel_realign_sample(samples, run_parallel)
    samples = parallel_variantcall(samples, run_parallel)
    samples = run_parallel("postprocess_variants", samples)
    samples = combine_multiple_callers(samples)
    samples = run_parallel("detect_sv", samples)
    samples = run_parallel("combine_calls", samples)
    run_parallel("process_sample", samples)
    run_parallel("generate_bigwig", samples, {"programs": ["ucsc_bigwig"]})
    write_project_summary(samples)
    write_metrics(run_info, fc_name, fc_date, dirs)

def _set_resources(parallel, config):
    """Set resource availability for programs, downsizing to local runs.
    """
    for program in ["gatk", "novoalign"]:
        if not config["resources"].has_key(program):
            config["resources"][program] = {}
        if parallel["type"] == "local":
            import multiprocessing
            cores = min(parallel["cores"], multiprocessing.cpu_count())
            config["resources"][program]["cores"] = cores
    return config

# ## Utility functions

def parse_cl_args(in_args):
    """Parse input commandline arguments, handling multiple cases.

    Returns the main config file and set of kwargs.
    """
    parser = argparse.ArgumentParser(
        description="Best-practice pipelines for fully automated high throughput sequencing analysis")
    parser.add_argument("inputs", nargs="*")
    parser.add_argument("-n", "--numcores", type=int, default=0)
    parser.add_argument("-t", "--paralleltype")
    parser.add_argument("-s", "--scheduler")
    parser.add_argument("-q", "--queue")
    parser.add_argument("-u", "--upgrade", help="Perform an upgrade of bcbio_nextgen in place.",
                        choices = ["stable", "development", "system"])

    args = parser.parse_args(in_args)
    config_file = args.inputs[0] if len(args.inputs) > 0 else None
    kwargs = {"numcores": args.numcores if args.numcores > 0 else None,
              "paralleltype": args.paralleltype,
              "scheduler": args.scheduler,
              "queue": args.queue,
              "upgrade": args.upgrade}
    if len(args.inputs) == 3:
        kwargs["fc_dir"] = args.inputs[1]
        kwargs["run_info_yaml"] = args.inputs[2]
    elif len(args.inputs) == 2:
        extra = args.inputs[1]
        if os.path.isfile(extra):
            kwargs["run_info_yaml"] = extra
        else:
            kwargs["fc_dir"] = extra
    elif args.upgrade is None:
        parser.print_help()
        sys.exit()
    return config_file, kwargs

def _get_full_paths(fastq_dir, config, config_file):
    """Retrieve full paths for directories in the case of relative locations.
    """
    if fastq_dir:
        fastq_dir = utils.add_full_path(fastq_dir)
    config_dir = utils.add_full_path(os.path.dirname(config_file))
    galaxy_config_file = utils.add_full_path(config.get("galaxy_config", "universe_wsgi.ini"),
                                             config_dir)
    return fastq_dir, os.path.dirname(galaxy_config_file), config_dir

########NEW FILE########
__FILENAME__ = merge
"""Handle multiple samples present on a single flowcell

Merges samples located in multiple lanes on a flowcell. Unique sample names identify
items to combine within a group.
"""
import os
import shutil
import collections

from bcbio import utils, broad

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

def organize_samples(items, dirs, config_file):
    """Organize BAM output files by sample name.
    """
    def _sort_by_lane_barcode(x):
        """Index a sample by lane and barcode.
        """
        return (x["info"]["lane"], x["info"]["barcode_id"])
    items_by_name = collections.defaultdict(list)
    for item in items:
        name = (item["info"].get("name", ""), item["info"]["description"])
        items_by_name[name].append(item)
    out = []
    for name, item_group in items_by_name.iteritems():
        fastq_files = [x["fastq"] for x in item_group]
        bam_files = [x["out_bam"] for x in item_group]
        item_group.sort(key=_sort_by_lane_barcode)

        out.append({"name": name, "info": item_group[0]["info"],
                    "fastq_files": fastq_files, "bam_files": bam_files,
                    "dirs": dirs, "config": item_group[0]["config"],
                    "config_file": config_file})
    out.sort(key=_sort_by_lane_barcode)
    out = [[x] for x in out]
    return out

def merge_bam_files(bam_files, work_dir, config, batch=0):
    """Merge multiple BAM files from a sample into a single BAM for processing.

    Avoids too many open file issues by merging large numbers of files in batches.
    """
    max_merge = 500
    bam_files.sort()
    i = 1
    while len(bam_files) > max_merge:
        bam_files = [merge_bam_files(xs, work_dir, config, batch + i)
                     for xs in utils.partition_all(max_merge, bam_files)]
        i += 1
    if batch > 0:
        out_dir = utils.safe_makedir(os.path.join(work_dir, "batchmerge%s" % batch))
    else:
        out_dir = work_dir
    out_file = os.path.join(out_dir, os.path.basename(sorted(bam_files)[0]))
    picard = broad.runner_from_config(config)
    if len(bam_files) == 1:
        if not os.path.exists(out_file):
            os.symlink(bam_files[0], out_file)
    else:
        picard.run_fn("picard_merge", bam_files, out_file)
        for b in bam_files:
            utils.save_diskspace(b, "BAM merged to %s" % out_file, config)
    return out_file

########NEW FILE########
__FILENAME__ = qcsummary
"""Quality control and summary metrics for next-gen alignments and analysis.
"""
import os
import csv
import copy
import glob
import subprocess
import xml.etree.ElementTree as ET

import yaml
from mako.template import Template

from bcbio.broad import runner_from_config
from bcbio.broad.metrics import PicardMetrics, PicardMetricsParser
from bcbio import utils
from bcbio.pipeline import config_utils

# ## High level functions to generate summary PDF

def generate_align_summary(bam_file, is_paired, sam_ref, sample_name,
                           config, dirs):
    """Run alignment summarizing script to produce a pdf with align details.
    """
    with utils.chdir(dirs["work"]):
        with utils.curdir_tmpdir() as tmp_dir:
            graphs, summary, overrep = \
                    _graphs_and_summary(bam_file, sam_ref, is_paired,
                                        tmp_dir, config)
        return _generate_pdf(graphs, summary, overrep, bam_file, sample_name,
                             dirs, config)

def _safe_latex(to_fix):
    """Escape characters that make LaTeX unhappy.
    """
    chars = ["%", "_", "&", "#"]
    for char in chars:
        to_fix = to_fix.replace(char, "\\%s" % char)
    return to_fix

def _generate_pdf(graphs, summary, overrep, bam_file, sample_name,
                  dirs, config):
    base = os.path.splitext(os.path.basename(bam_file))[0]
    sample_name = base if sample_name is None else " : ".join(sample_name)
    tmpl = Template(_section_template)
    sample_name = "%s (%s)" % (_safe_latex(sample_name),
                               _safe_latex(base))
    recal_plots = sorted(glob.glob(os.path.join(dirs["work"], "reports", "images",
                                                "%s*-plot.pdf" % base)))
    section = tmpl.render(name=sample_name, summary=None,
                          summary_table=summary,
                          figures=[(f, c, i) for (f, c, i) in graphs if f],
                          overrep=overrep,
                          recal_figures=recal_plots)
    out_file = os.path.join(dirs["work"], "%s-summary.tex" % base)
    out_tmpl = Template(_base_template)
    with open(out_file, "w") as out_handle:
        out_handle.write(out_tmpl.render(parts=[section]))
    if config["algorithm"].get("write_summary", True):
        cl = [config_utils.get_program("pdflatex", config), out_file]
        subprocess.check_call(cl)
    return "%s.pdf" % os.path.splitext(out_file)[0]

def _graphs_and_summary(bam_file, sam_ref, is_paired, tmp_dir, config):
    """Prepare picard/FastQC graphs and summary details.
    """
    bait = config["algorithm"].get("hybrid_bait", None)
    target = config["algorithm"].get("hybrid_target", None)
    broad_runner = runner_from_config(config)
    metrics = PicardMetrics(broad_runner, tmp_dir)
    summary_table, metrics_graphs = \
                   metrics.report(bam_file, sam_ref, is_paired, bait, target)
    metrics_graphs = [(p, c, 0.75) for p, c in metrics_graphs]
    fastqc_graphs, fastqc_stats, fastqc_overrep = \
                   fastqc_report(bam_file, config)
    all_graphs = fastqc_graphs + metrics_graphs
    summary_table = _update_summary_table(summary_table, sam_ref, fastqc_stats)
    return all_graphs, summary_table, fastqc_overrep

def _update_summary_table(summary_table, ref_file, fastqc_stats):
    stats_want = []
    summary_table[0] = (summary_table[0][0], summary_table[0][1],
            "%sbp %s" % (fastqc_stats.get("Sequence length", "0"), summary_table[0][-1]))
    for stat in stats_want:
        summary_table.insert(0, (stat, fastqc_stats.get(stat, ""), ""))
    ref_org = os.path.splitext(os.path.split(ref_file)[-1])[0]
    summary_table.insert(0, ("Reference organism",
        ref_org.replace("_", " "), ""))
    return summary_table

# ## Generate project level QC summary for quickly assessing large projects

def write_project_summary(samples):
    """Write project summary information on the provided samples.
    """
    def _nocommas(x):
        return x.replace(",", "")
    def _percent(x):
        return x.replace("(", "").replace(")", "").replace("\\", "")
    out_file = os.path.join(samples[0][0]["dirs"]["work"], "project-summary.csv")
    sample_info = _get_sample_summaries(samples)
    header = ["Total", "Aligned", "Pair duplicates", "Insert size",
              "On target bases", "Mean target coverage", "10x coverage targets",
              "Zero coverage targets", "Total variations", "In dbSNP",
              "Transition/Transversion (all)", "Transition/Transversion (dbSNP)",
              "Transition/Transversion (novel)"]
    select = [(0, _nocommas), (1, _percent), (1, _percent), (0, None),
              (1, _percent), (0, None), (0, _percent),
              (0, _percent), (0, None), (0, _percent),
              (0, None), (0, None), (0, None)]
    rows = [["Sample"] + header]
    for name, info in sample_info:
        cur = [name]
        for col, (i, prep_fn) in zip(header, select):
            val = info.get(col, ["", ""])[i]
            if prep_fn and val:
                val = prep_fn(val)
            cur.append(val)
        rows.append(cur)
    with open(out_file, "w") as out_handle:
        writer = csv.writer(out_handle)
        for row in rows:
            writer.writerow(row)

def _get_sample_summaries(samples):
    """Retrieve high level summary information for each sample.
    """
    out = []
    with utils.curdir_tmpdir() as tmp_dir:
        for sample in (x[0] for x in samples):
            is_paired = sample.get("fastq2", None) not in ["", None]
            _, summary, _ = _graphs_and_summary(sample["work_bam"], sample["sam_ref"],
                                            is_paired, tmp_dir, sample["config"])
            sample_info = {}
            for xs in summary:
                n = xs[0]
                if n is not None:
                    sample_info[n] = xs[1:]
            sample_name = ";".join([x for x in sample["name"] if x])
            out.append((sample_name, sample_info))
    return out

# ## Run and parse read information from FastQC

def fastqc_report(bam_file, config):
    """Calculate statistics about a read using FastQC.
    """
    out_dir = _run_fastqc(bam_file, config)
    parser = FastQCParser(out_dir)
    graphs = parser.get_fastqc_graphs()
    stats, overrep = parser.get_fastqc_summary()
    return graphs, stats, overrep

class FastQCParser:
    def __init__(self, base_dir):
        self._dir = base_dir
        self._max_seq_size = 45
        self._max_overrep = 20

    def get_fastqc_graphs(self):
        graphs = (("per_base_quality.png", "", 1.0),
                  ("per_base_sequence_content.png", "", 0.85),
                  ("per_sequence_gc_content.png", "", 0.85),
                  ("kmer_profiles.png", "", 0.85),)
        final_graphs = []
        for f, caption, size in graphs:
            full_f = os.path.join(self._dir, "Images", f)
            if os.path.exists(full_f):
                final_graphs.append((full_f, caption, size))
        return final_graphs

    def get_fastqc_summary(self):
        stats = {}
        for stat_line in self._fastqc_data_section("Basic Statistics")[1:]:
            k, v = [_safe_latex(x) for x in stat_line.split("\t")[:2]]
            stats[k] = v
        over_rep = []
        for line in self._fastqc_data_section("Overrepresented sequences")[1:]:
            parts = [_safe_latex(x) for x in line.split("\t")]
            over_rep.append(parts)
            over_rep[-1][0] = self._splitseq(over_rep[-1][0])
        return stats, over_rep[:self._max_overrep]

    def _splitseq(self, seq):
        pieces = []
        cur_piece = []
        for s in seq:
            if len(cur_piece) >= self._max_seq_size:
                pieces.append("".join(cur_piece))
                cur_piece = []
            cur_piece.append(s)
        pieces.append("".join(cur_piece))
        return " ".join(pieces)

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


def _run_fastqc(bam_file, config):
    out_base = "fastqc"
    utils.safe_makedir(out_base)
    fastqc_out = os.path.join(out_base, "%s_fastqc" %
                              os.path.splitext(os.path.basename(bam_file))[0])
    if not os.path.exists(fastqc_out):
        cl = [config_utils.get_program("fastqc", config),
              "-o", out_base, "-f", "bam", bam_file]
        subprocess.check_call(cl)
    if os.path.exists("%s.zip" % fastqc_out):
        os.remove("%s.zip" % fastqc_out)
    return fastqc_out


# ## High level summary in YAML format for loading into Galaxy.

def write_metrics(run_info, fc_name, fc_date, dirs):
    """Write an output YAML file containing high level sequencing metrics.
    """
    lane_stats, sample_stats, tab_metrics = summary_metrics(run_info,
            dirs["work"], fc_name, fc_date, dirs["fastq"])
    out_file = os.path.join(dirs["work"], "run_summary.yaml")
    with open(out_file, "w") as out_handle:
        metrics = dict(lanes=lane_stats, samples=sample_stats)
        yaml.dump(metrics, out_handle, default_flow_style=False)
    if dirs["flowcell"]:
        tab_out_file = os.path.join(dirs["flowcell"], "run_summary.tsv")
        try:
            with open(tab_out_file, "w") as out_handle:
                writer = csv.writer(out_handle, dialect="excel-tab")
                for info in tab_metrics:
                    writer.writerow(info)
        # If on NFS mounted directory can fail due to filesystem or permissions
        # errors. That's okay, we'll just not write the file.
        except IOError:
            pass
    return out_file

def summary_metrics(run_info, analysis_dir, fc_name, fc_date, fastq_dir):
    """Reformat run and analysis statistics into a YAML-ready format.
    """
    tab_out = []
    lane_info = []
    sample_info = []
    for lane_xs in run_info["details"]:
        run = lane_xs[0]
        tab_out.append([run["lane"], run.get("researcher", ""),
            run.get("name", ""), run.get("description")])
        base_info = dict(
                researcher = run.get("researcher_id", ""),
                sample = run.get("sample_id", ""),
                lane = run["lane"],
                request = run_info["run_id"])
        cur_lane_info = copy.deepcopy(base_info)
        cur_lane_info["metrics"] = _bustard_stats(run["lane"], fastq_dir,
                                                  fc_date, analysis_dir)
        lane_info.append(cur_lane_info)
        for lane_x in lane_xs:
            cur_name = "%s_%s_%s" % (run["lane"], fc_date, fc_name)
            if lane_x["barcode_id"]:
                cur_name = "%s_%s-" % (cur_name, lane_x["barcode_id"])
            stats = _metrics_from_stats(_lane_stats(cur_name, analysis_dir))
            if stats:
                cur_run_info = copy.deepcopy(base_info)
                cur_run_info["metrics"] = stats
                cur_run_info["barcode_id"] = str(lane_x["barcode_id"])
                cur_run_info["barcode_type"] = str(lane_x.get("barcode_type", ""))
                sample_info.append(cur_run_info)
    return lane_info, sample_info, tab_out

def _metrics_from_stats(stats):
    """Remap Broad metrics names to our local names.
    """
    if stats:
        s_to_m = dict(
                AL_MEAN_READ_LENGTH = 'Read length',
                AL_TOTAL_READS = 'Reads',
                AL_PF_READS_ALIGNED = 'Aligned',
                DUP_READ_PAIR_DUPLICATES = 'Pair duplicates'
                )
        metrics = dict()
        for stat_name, metric_name in s_to_m.iteritems():
            metrics[metric_name] = stats.get(stat_name, 0)
        return metrics

def _bustard_stats(lane_num, fastq_dir, fc_date, analysis_dir):
    """Extract statistics about the flow cell from Bustard outputs.
    """
    stats = dict()
    if fastq_dir:
        sum_file = os.path.join(fastq_dir, os.pardir, "BustardSummary.xml")
        #sum_file = os.path.join(fc_dir, "Data", "Intensities", "BaseCalls",
        #        "BustardSummary.xml")
        if os.path.exists(sum_file):
            with open(sum_file) as in_handle:
                results = ET.parse(in_handle).getroot().find("TileResultsByLane")
                for lane in results:
                    if lane.find("laneNumber").text == str(lane_num):
                        stats = _collect_cluster_stats(lane)
    read_stats = _calc_fastq_stats(analysis_dir, lane_num, fc_date)
    stats.update(read_stats)
    return stats

def _calc_fastq_stats(analysis_dir, lane_num, fc_date):
    """Grab read length from fastq; could provide distribution if non-equal.
    """
    stats = dict()
    fastqc_dirs = glob.glob(os.path.join(analysis_dir, "fastqc",
                                         "%s_%s*" % (lane_num, fc_date)))
    if len(fastqc_dirs) > 0:
        parser = FastQCParser(sorted(fastqc_dirs)[-1])
        fastqc_stats, _ = parser.get_fastqc_summary()
        stats["Read length"] = fastqc_stats["Sequence length"]
    return stats

def _collect_cluster_stats(lane):
    """Retrieve total counts on cluster statistics.
    """
    stats = {"Clusters" : 0, "Clusters passed": 0}
    for tile in lane.find("Read").findall("Tile"):
        stats["Clusters"] += int(tile.find("clusterCountRaw").text)
        stats["Clusters passed"] += int(tile.find("clusterCountPF").text)
    return stats

def _lane_stats(cur_name, work_dir):
    """Parse metrics information from files in the working directory.
    """
    parser = PicardMetricsParser()
    metrics_files = glob.glob(os.path.join(work_dir, "%s*metrics" % cur_name))
    metrics = parser.extract_metrics(metrics_files)
    return metrics

# ## LaTeX templates for output PDF

_section_template = r"""
\subsection*{${name}}

% if summary_table:
    \begin{table}[h]
    \centering
    \begin{tabular}{|l|rr|}
    \hline
    % for label, val, extra in summary_table:
        %if label is not None:
            ${label} & ${val} & ${extra} \\%
        %else:
            \hline
        %endif
    %endfor
    \hline
    \end{tabular}
    \caption{Summary of lane results}
    \end{table}
% endif

% if summary:
    \begin{verbatim}
    ${summary}
    \end{verbatim}
% endif

% for i, (figure, caption, size) in enumerate(figures):
    \begin{figure}[htbp]
      \centering
      \includegraphics[width=${size}\linewidth] {${figure}}
      \caption{${caption}}
    \end{figure}
% endfor

% if len(overrep) > 0:
    \begin{table}[htbp]
    \centering
    \begin{tabular}{|p{8cm}rrp{4cm}|}
    \hline
    Sequence & Count & Percent & Match \\%
    \hline
    % for seq, count, percent, match in overrep:
        \texttt{${seq}} & ${count} & ${"%.2f" % float(percent)} & ${match} \\%
    % endfor
    \hline
    \end{tabular}
    \caption{Overrepresented read sequences}
    \end{table}
% endif

\FloatBarrier
% if len(recal_figures) > 0:
    \subsubsection*{Quality score recalibration}
    % for figure in recal_figures:
        \begin{figure}[htbp]
          \centering
          \includegraphics[width=0.48\linewidth]{${figure}}
        \end{figure}
    % endfor
% endif
\FloatBarrier
"""

_base_template = r"""
\documentclass{article}
\usepackage{fullpage}
\usepackage{graphicx}
\usepackage{placeins}

\begin{document}
% for part in parts:
    ${part}
% endfor
\end{document}
"""

########NEW FILE########
__FILENAME__ = run_info
"""Retrieve run information describing files to process in a pipeline.

This handles two methods of getting processing information: from a Galaxy
next gen LIMS system or an on-file YAML configuration.
"""
import os
import time
import copy
import string
import datetime
import collections

import yaml

from bcbio.log import logger
from bcbio.galaxy.api import GalaxyApiAccess
from bcbio.solexa.flowcell import get_flowcell_info

def get_run_info(fc_dir, config, run_info_yaml):
    """Retrieve run information from a passed YAML file or the Galaxy API.
    """
    if run_info_yaml and os.path.exists(run_info_yaml):
        logger.info("Found YAML samplesheet, using %s instead of Galaxy API" % run_info_yaml)
        fc_name, fc_date, run_info = _run_info_from_yaml(fc_dir, run_info_yaml)
    else:
        logger.info("Fetching run details from Galaxy instance")
        fc_name, fc_date = get_flowcell_info(fc_dir)
        galaxy_api = GalaxyApiAccess(config['galaxy_url'], config['galaxy_api_key'])
        run_info = galaxy_api.run_details(fc_name, fc_date)
    return fc_name, fc_date, _organize_runs_by_lane(run_info)

def _organize_runs_by_lane(run_info):
    """Organize run information collapsing multiplexed items by lane.

    Lane is the unique identifier in a run and used to combine multiple
    run items on a fastq lane, separable by barcodes.
    """
    items = _normalize_barcodes(run_info["details"])
    items_by_lane = collections.defaultdict(list)
    for x in items:
        items_by_lane[x["lane"]].append(x)
    out = []
    for grouped_items in [items_by_lane[x] for x in sorted(items_by_lane.keys())]:
        bcs = [x["barcode_id"] for x in grouped_items]
        assert len(bcs) == len(set(bcs)), "Duplicate barcodes {0} in lane {1}".format(
            bcs, grouped_items[0]["lane"])
        assert len(bcs) == 1 or None not in bcs, "Barcode and non-barcode in lane {0}".format(
            grouped_items[0]["lane"])
        out.append(grouped_items)
    run_info["details"] = out
    return run_info

def _normalize_barcodes(items):
    """Normalize barcode specification methods into individual items.
    """
    split_items = []
    for item in items:
        if item.has_key("multiplex"):
            for multi in item["multiplex"]:
                base = copy.deepcopy(item)
                base["description"] += ": {0}".format(multi["name"])
                del multi["name"]
                del base["multiplex"]
                base.update(multi)
                split_items.append(base)
        elif item.has_key("barcode"):
            item.update(item["barcode"])
            del item["barcode"]
            split_items.append(item)
        else:
            item["barcode_id"] = None
            split_items.append(item)
    return split_items

def _run_info_from_yaml(fc_dir, run_info_yaml):
    """Read run information from a passed YAML file.
    """
    with open(run_info_yaml) as in_handle:
        loaded = yaml.load(in_handle)
    fc_name = None
    if fc_dir:
        try:
            fc_name, fc_date = get_flowcell_info(fc_dir)
        except ValueError:
            pass
    global_config = {}
    if isinstance(loaded, dict):
        if loaded.has_key("fc_name") and loaded.has_key("fc_date"):
            fc_name = loaded["fc_name"].replace(" ", "_")
            fc_date = str(loaded["fc_date"]).replace(" ", "_")
            global_config = copy.deepcopy(loaded)
            del global_config["details"]
        loaded = loaded["details"]
    if fc_name is None:
        fc_name, fc_date = _unique_flowcell_info()
    run_details = []
    for i, item in enumerate(loaded):
        if not item.has_key("lane"):
            if item.has_key("description"):
                item["lane"] = item["description"]
            elif item.has_key("files"):
                item["lane"] = _generate_lane(item["files"], i)
            else:
                raise ValueError("Unable to generate lane info for input %s" % item)
        if not item.has_key("description"):
            item["description"] = str(item["lane"])
        item["description_filenames"] = global_config.get("description_filenames", False)
        run_details.append(item)
    run_info = dict(details=run_details, run_id="")
    return fc_name, fc_date, run_info

def _clean_extra_whitespace(s):
    while s.endswith(("_", "-", " ", ".")):
        s = s[:-1]
    return s

def _generate_lane(fnames, index):
    """Generate a lane identifier from filenames.
    """
    to_remove = ["s_", "sequence"]
    work_names = []
    if isinstance(fnames, basestring):
        fnames = [fnames]
    for fname in fnames:
        n = os.path.splitext(os.path.basename(fname))[0]
        for r in to_remove:
            n = n.replace(r, "")
        work_names.append(n)
    if len(work_names) == 1:
        return _clean_extra_whitespace(work_names[0])
    else:
        prefix = _clean_extra_whitespace(os.path.commonprefix(work_names))
        return prefix if prefix else str(index+1)

def _unique_flowcell_info():
    """Generate data and unique identifier for non-barcoded flowcell.

    String encoding from:
    http://stackoverflow.com/questions/561486/
    how-to-convert-an-integer-to-the-shortest-url-safe-string-in-python
    """
    alphabet = string.ascii_uppercase + string.digits
    fc_date = datetime.datetime.now().strftime("%y%m%d")
    n = int(time.time())
    s = []
    while True:
        n, r = divmod(n, len(alphabet))
        s.append(alphabet[r])
        if n == 0: break
    return ''.join(reversed(s)), fc_date

########NEW FILE########
__FILENAME__ = sample
"""High level entry point for processing a sample.

Samples may include multiple lanes, or barcoded subsections of lanes,
processed together.
"""
import os
import subprocess


from bcbio.utils import file_exists, save_diskspace
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline.lane import _update_config_w_custom
from bcbio.log import logger
from bcbio.pipeline.merge import (combine_fastq_files, merge_bam_files)
from bcbio.pipeline.qcsummary import generate_align_summary
from bcbio.pipeline.variation import (finalize_genotyper, variation_effects)
from bcbio.rnaseq.cufflinks import assemble_transcripts
from bcbio.pipeline.shared import ref_genome_info

def merge_sample(data):
    """Merge fastq and BAM files for multiple samples.
    """
    logger.info("Combining fastq and BAM files %s" % str(data["name"]))
    config = _update_config_w_custom(data["config"], data["info"])
    genome_build, sam_ref = ref_genome_info(data["info"], config, data["dirs"])
    if config["algorithm"].get("upload_fastq", False):
        fastq1, fastq2 = combine_fastq_files(data["fastq_files"], data["dirs"]["work"],
                                             config)
    else:
        fastq1, fastq2 = None, None
    sort_bam = merge_bam_files(data["bam_files"], data["dirs"]["work"], config)
    return [[{"name": data["name"], "metadata": data["info"].get("metadata", {}),
              "genome_build": genome_build, "sam_ref": sam_ref,
              "work_bam": sort_bam, "fastq1": fastq1, "fastq2": fastq2,
              "dirs": data["dirs"], "config": config,
              "config_file": data["config_file"]}]]

# ## General processing

def postprocess_variants(data):
    """Provide post-processing of variant calls.
    """
    if data["config"]["algorithm"]["snpcall"]:
        logger.info("Finalizing variant calls: %s" % str(data["name"]))
        data["vrn_file"] = finalize_genotyper(data["vrn_file"], data["work_bam"],
                                              data["sam_ref"], data["config"])
        logger.info("Calculating variation effects for %s" % str(data["name"]))
        ann_vrn_file = variation_effects(data["vrn_file"], data["sam_ref"],
                                         data["genome_build"], data["config"])
        if ann_vrn_file:
            data["vrn_file"] = ann_vrn_file
    return [[data]]

def process_sample(data):
    """Finalize processing for a sample, potentially multiplexed.
    """
    if data["config"]["algorithm"].get("transcript_assemble", False):
        data["tx_file"] = assemble_transcripts(data["work_bam"], data["sam_ref"],
                                               data["config"])
    if data["sam_ref"] is not None:
        logger.info("Generating summary files: %s" % str(data["name"]))
        generate_align_summary(data["work_bam"], data["fastq2"] is not None,
                               data["sam_ref"], data["name"],
                               data["config"], data["dirs"])
    return [[data]]

def generate_bigwig(data):
    """Provide a BigWig coverage file of the sorted alignments.
    """
    logger.info("Preparing BigWig file %s" % str(data["name"]))
    bam_file = data["work_bam"]
    wig_file = "%s.bigwig" % os.path.splitext(bam_file)[0]
    if not file_exists(wig_file):
        with file_transaction(wig_file) as tx_file:
            cl = ["bam_to_wiggle.py", bam_file,
                  data["config_file"], "--outfile=%s" % tx_file]
            subprocess.check_call(cl)
    return [[data]]

########NEW FILE########
__FILENAME__ = shared
"""Pipeline functionality shared amongst multiple analysis types.
"""
import os
import collections
from contextlib import closing

import pysam

from bcbio import broad
from bcbio.pipeline.alignment import get_genome_ref
from bcbio.utils import file_exists, safe_makedir, save_diskspace
from bcbio.distributed.transaction import file_transaction

# ## Split/Combine helpers

def combine_bam(in_files, out_file, config):
    """Parallel target to combine multiple BAM files.
    """
    runner = broad.runner_from_config(config)
    runner.run_fn("picard_merge", in_files, out_file)
    for in_file in in_files:
        save_diskspace(in_file, "Merged into {0}".format(out_file), config)
    runner.run_fn("picard_index", out_file)
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

def write_nochr_reads(in_file, out_file):
    """Write a BAM file of reads that are not on a reference chromosome.

    This is useful for maintaining non-mapped reads in parallel processes
    that split processing by chromosome.
    """
    if not file_exists(out_file):
        with closing(pysam.Samfile(in_file, "rb")) as in_bam:
            with file_transaction(out_file) as tx_out_file:
                with closing(pysam.Samfile(tx_out_file, "wb", template=in_bam)) as out_bam:
                    for read in in_bam:
                        if read.tid < 0:
                            out_bam.write(read)
    return out_file

def subset_bam_by_region(in_file, region, out_file_base = None):
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

def subset_variant_regions(variant_regions, region, out_file):
    """Return BED file subset by a specified chromosome region.

    variant_regions is a BED file, region is a chromosome name.
    """
    if region is None:
        return variant_regions
    elif variant_regions is None:
        return region
    elif region.find(":") > 0:
        raise ValueError("Partial chromosome regions not supported")
    else:
        # create an ordered subset file for processing
        subset_file = "{0}-regions.bed".format(os.path.splitext(out_file)[0])
        items = []
        with open(variant_regions) as in_handle:
            for line in in_handle:
                if line.startswith(region) and line.split("\t")[0] == region:
                    start = int(line.split("\t")[1])
                    items.append((start, line))
        if len(items) > 0:
            if not os.path.exists(subset_file):
                with open(subset_file, "w") as out_handle:
                    items.sort()
                    for _, line in items:
                        out_handle.write(line)
            return subset_file
        else:
            return region

# ## Retrieving file information from configuration variables

def configured_ref_file(name, config, sam_ref):
    """Full path to a reference file specified in the configuration.

    Resolves non-absolute paths relative to the base genome reference directory.
    """
    ref_file = config["algorithm"].get(name, None)
    if ref_file:
        if not os.path.isabs(ref_file):
            base_dir = os.path.dirname(os.path.dirname(sam_ref))
            ref_file = os.path.join(base_dir, ref_file)
    return ref_file

def configured_vrn_files(config, sam_ref):
    """Full path to all configured files for variation assessment.
    """
    names = ["dbsnp", "train_hapmap", "train_1000g_omni", "train_indels"]
    VrnFiles = collections.namedtuple("VrnFiles", names)
    return apply(VrnFiles, [configured_ref_file(n, config, sam_ref) for n in names])

def ref_genome_info(info, config, dirs):
    """Retrieve reference genome information from configuration variables.
    """
    genome_build = info.get("genome_build", None)
    (_, sam_ref) = get_genome_ref(genome_build, config["algorithm"]["aligner"],
                                  dirs["galaxy"])
    return genome_build, sam_ref

########NEW FILE########
__FILENAME__ = storage
"""Transfer raw files from finished NGS runs for backup and storage.
"""
import os

import yaml

from bcbio.log import logger

def long_term_storage(remote_info, config_file):
    """Securely copy files from remote directory to the storage server.

    This requires ssh public keys to be setup so that no password entry
    is necessary, Fabric is used to manage setting up copies on the remote
    storage server.
    """
    import fabric.api as fabric
    import fabric.contrib.files as fabric_files
 
    logger.info("Copying run data over to remote storage: %s" % config["store_host"])
    logger.debug("The contents from AMQP for this dataset are:\n %s" % remote_info)
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    base_dir = config["store_dir"]
    fabric.env.host_string = "%s@%s" % (config["store_user"], config["store_host"])
    fc_dir = os.path.join(base_dir, os.path.basename(remote_info['directory']))
    if not fabric_files.exists(fc_dir):
        fabric.run("mkdir %s" % fc_dir)
    for fcopy in remote_info['to_copy']:
        target_loc = os.path.join(fc_dir, fcopy)
        if not fabric_files.exists(target_loc):
            target_dir = os.path.dirname(target_loc)
            if not fabric_files.exists(target_dir):
                fabric.run("mkdir -p %s" % target_dir)
            cl = ["scp", "-r", "%s@%s:%s/%s" % (
                  remote_info["user"], remote_info["hostname"], remote_info["directory"],
                  fcopy), target_loc]
            fabric.run(" ".join(cl))

########NEW FILE########
__FILENAME__ = toplevel
"""Top level management of analysis processing.

Handles copying remote files from sequencer, starting processing scripts,
and upload of results back to Galaxy.
"""
import os
import re
import subprocess

import yaml
# Fabric only needed on running side, not on setup and initial import
try:
    import fabric.api as fabric
    import fabric.contrib.files as fabric_files
except (ImportError, SystemExit):
    fabric, fabric_files = (None, None)

from bcbio.log import logger
from bcbio import utils

def analyze_and_upload(remote_info, config_file):
    """Main entry point for analysis and upload to Galaxy.
    """
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    fc_dir = _copy_from_sequencer(remote_info, config)
    analysis_dir = _run_analysis(fc_dir, remote_info, config, config_file)
    _upload_to_galaxy(fc_dir, analysis_dir, remote_info,
                      config, config_file)

# ## Copying over files from sequencer, if necessary

def _copy_from_sequencer(remote_info, config):
    """Get local directory of flowcell info, or copy from sequencer.
    """
    if remote_info.has_key("fc_dir"):
        fc_dir = remote_info["fc_dir"]
        assert os.path.exists(fc_dir)
    else:
        logger.debug("Remote host information: %s" % remote_info)
        c_host_str = _config_hosts(config)
        with fabric.settings(host_string=c_host_str):
            fc_dir = _remote_copy(remote_info, config)
    return fc_dir

def _config_hosts(config):
    """Retrieve configured machines to perform analysis and copy on.
    """
    copy_user = config["analysis"].get("copy_user", None)
    copy_host = config["analysis"].get("copy_host", None)
    if not copy_user or not copy_host:
        copy_user = os.environ["USER"]
        copy_host = re.sub(r'\..*', '', os.uname()[1])
    copy_host_str = "%s@%s" % (copy_user, copy_host)
    return copy_host_str

def _remote_copy(remote_info, config):
    """Securely copy files from remote directory to the processing server.

    This requires ssh public keys to be setup so that no password entry
    is necessary.
    """
    fc_dir = os.path.join(config["analysis"]["store_dir"],
                          os.path.basename(remote_info['directory']))
    logger.info("Copying analysis files to %s" % fc_dir)
    if not fabric_files.exists(fc_dir):
        fabric.run("mkdir %s" % fc_dir)
    for fcopy in remote_info['to_copy']:
        target_loc = os.path.join(fc_dir, fcopy)
        if not fabric_files.exists(target_loc):
            target_dir = os.path.dirname(target_loc)
            if not fabric_files.exists(target_dir):
                fabric.run("mkdir -p %s" % target_dir)
            cl = ["scp", "-r", "%s@%s:%s/%s" %
                  (remote_info["user"], remote_info["hostname"],
                   remote_info["directory"], fcopy),
                  target_loc]
            fabric.run(" ".join(cl))
    logger.info("Analysis files copied")
    return fc_dir

def _run_analysis(fc_dir, remote_info, config, config_file):
    """Run local or distributed analysis, wait to finish.
    """
    run_yaml = _get_run_yaml(remote_info, fc_dir, config)
    analysis_dir = os.path.join(config["analysis"].get("base_dir", os.getcwd()),
                                os.path.basename(remote_info["directory"]))
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    with utils.chdir(analysis_dir):
        prog = "bcbio_nextgen.py"
        cl = [prog, config_file, fc_dir]
        if run_yaml:
            cl.append(run_yaml)
        subprocess.check_call(cl)
    return analysis_dir

def _get_run_yaml(remote_info, fc_dir, config):
    """Retrieve YAML specifying run from configured or default location.
    """
    if remote_info.get("run_yaml", None):
        run_yaml = remote_info["run_yaml"]
    else:
        run_yaml = os.path.join(config["analysis"]["store_dir"],
                                os.path.basename(fc_dir), "run_info.yaml")
    if not os.path.exists(run_yaml):
        run_yaml = None
    return run_yaml

def _upload_to_galaxy(fc_dir, analysis_dir, remote_info, config, config_file):
    """Upload results from analysis directory to Galaxy data libraries.
    """
    run_yaml = _get_run_yaml(remote_info, fc_dir, config)
    with utils.chdir(analysis_dir):
        cl = [config["analysis"]["upload_program"], config_file, fc_dir,
              analysis_dir]
        if run_yaml:
            cl.append(run_yaml)
        subprocess.check_call(cl)

########NEW FILE########
__FILENAME__ = variation
"""Next-gen variant detection and evaluation with GATK and SnpEff.
"""
import os
import json
import subprocess

from bcbio.variation.genotype import variant_filtration, gatk_evaluate_variants
from bcbio.variation.effects import snpeff_effects
from bcbio.variation.annotation import annotate_effects
from bcbio.variation import freebayes, phasing
from bcbio.pipeline.shared import (configured_vrn_files, configured_ref_file)
from bcbio.structural import hydra

# ## Genotyping

def finalize_genotyper(call_file, bam_file, ref_file, config):
    """Perform SNP genotyping and analysis.
    """
    vrn_files = configured_vrn_files(config, ref_file)
    variantcaller = config["algorithm"].get("variantcaller", "gatk")
    if variantcaller in ["freebayes", "cortex", "samtools", "gatk-haplotype", "varscan"]:
        call_file = freebayes.postcall_annotate(call_file, bam_file, ref_file, vrn_files, config)
    filter_snp = variant_filtration(call_file, ref_file, vrn_files, config)
    phase_snp = phasing.read_backed_phasing(filter_snp, bam_file, ref_file, config)
    _eval_genotyper(phase_snp, ref_file, vrn_files.dbsnp, config)
    return phase_snp

def _eval_genotyper(vrn_file, ref_file, dbsnp_file, config):
    """Evaluate variant genotyping, producing a JSON metrics file with values.
    """
    metrics_file = "%s.eval_metrics" % vrn_file
    target = config["algorithm"].get("hybrid_target", None)
    if not os.path.exists(metrics_file):
        stats = gatk_evaluate_variants(vrn_file, ref_file, config, dbsnp_file, target)
        with open(metrics_file, "w") as out_handle:
            json.dump(stats, out_handle)
    return metrics_file

# ## Calculate variation effects

def variation_effects(vrn_file, genome_file, genome_build, config):
    """Calculate effects of variations, associating them with transcripts.

    Runs snpEff, returning the resulting effects file. No longer runs the GATK
    annotator, since it requires an old version of snpEff.
    """
    return snpeff_effects(vrn_file, genome_build, config)

# ## Structural variation

def detect_sv(data):
    """Detect structural variation for input sample.
    """
    sv_todo = data["config"]["algorithm"].get("sv_detection", None)
    if sv_todo is not None and data.get("fastq2"):
        if sv_todo == "hydra":
            sv_calls = hydra.detect_sv(data["work_bam"], data["genome_build"],
                                       data["dirs"], data["config"])
        else:
            raise ValueError("Unexpected structural variation method:{}".format(sv_todo))
    return [[data]]

########NEW FILE########
__FILENAME__ = cufflinks
"""Assess transcript abundance in RNA-seq experiments using Cufflinks.

http://cufflinks.cbcb.umd.edu/manual.html
"""
import os
import subprocess

from bcbio.pipeline import config_utils
from bcbio.pipeline.variation import configured_ref_file

def assemble_transcripts(align_file, ref_file, config):
    """Create transcript assemblies using Cufflinks.
    """
    work_dir, fname = os.path.split(align_file)
    cores = config.get("resources", {}).get("cufflinks", {}).get("cores", None)

    core_flags = ["-p", str(cores)] if cores else []
    out_dir = os.path.join(work_dir,
                           "{base}-cufflinks".format(base=os.path.splitext(fname)[0]))
    cl = [config_utils.get_program("cufflinks", config),
          align_file,
          "-o", out_dir,
          "-b", ref_file,
          "-u"]
    cl += core_flags
    tx_file = configured_ref_file("transcripts", config, ref_file)
    tx_mask_file = configured_ref_file("transcripts_mask", config, ref_file)
    if tx_file:
        cl += ["-g", tx_file]
    if tx_mask_file:
        cl += ["-M", tx_mask_file]
    out_tx_file = os.path.join(out_dir, "transcripts.gtf")
    if not os.path.exists(out_tx_file):
        subprocess.check_call(cl)
    assert os.path.exists(out_tx_file)
    return out_tx_file

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

def get_flowcell_info(fc_dir):
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
__FILENAME__ = samplesheet
"""Converts Illumina SampleSheet CSV files to the run_info.yaml input file.

This allows running the analysis pipeline without Galaxy, using CSV input
files from Illumina SampleSheet or Genesifter.
"""
import os
import sys
import csv
import itertools
import difflib
import glob

import yaml

from bcbio.solexa.flowcell import (get_flowcell_info)
from bcbio import utils

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
        out_handle.write(yaml.dump(lanes, default_flow_style=False))
    return out_file

def run_has_samplesheet(fc_dir, config, require_single=True):
    """Checks if there's a suitable SampleSheet.csv present for the run
    """
    fc_name, _ = get_flowcell_info(fc_dir)
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
__FILENAME__ = hydra
"""Use Hydra to detect structural variation using discordant read pairs.

Hydra: http://code.google.com/p/hydra-sv/

Pipeline: http://code.google.com/p/hydra-sv/wiki/TypicalWorkflow
"""
import os
import copy
import collections
import subprocess
from contextlib import nested, closing

import pysam
import numpy
from Bio.Seq import Seq

from bcbio import utils, broad
from bcbio.pipeline.alignment import align_to_sort_bam
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

def calc_paired_insert_stats(in_bam):
    """Retrieve statistics for paired end read insert distances.

    MAD is the Median Absolute Deviation: http://en.wikipedia.org/wiki/Median_absolute_deviation
    """
    dists = []
    with closing(pysam.Samfile(in_bam, "rb")) as in_pysam:
        for read in in_pysam:
            if read.is_proper_pair and read.is_read1:
                dists.append(abs(read.isize))
    # remove outliers
    med = numpy.median(dists)
    filter_dists = filter(lambda x: x < med + 10 * med, dists)
    median = numpy.median(filter_dists)
    return {"mean": numpy.mean(filter_dists), "std": numpy.std(filter_dists),
            "median": median,
            "mad": numpy.median([abs(x - median) for x in filter_dists])}

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
        return align_to_sort_bam(nomap_fq1, nomap_fq2, genome_build, "novoalign",
                                 base_name, base_name,
                                 dirs, config, dir_ext=os.path.join("hydra", os.path.split(nomap_fq1)[0]))
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
__FILENAME__ = utils
"""Helpful utilities for building analysis pipelines.
"""
import os
import tempfile
import time
import shutil
import contextlib
import itertools
import functools
import ConfigParser
try:
    import multiprocessing
    from multiprocessing.pool import IMapIterator
except ImportError:
    multiprocessing = None
import collections
import yaml
import fnmatch


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
        if multiprocessing is None:
            raise ImportError("multiprocessing not available")
        # Fix to allow keyboard interrupts in multiprocessing: https://gist.github.com/626518
        def wrapper(func):
            def wrap(self, timeout=None):
                return func(self, timeout=timeout if timeout is not None else 1e100)
            return wrap
        IMapIterator.next = wrapper(IMapIterator.next)
        # recycle threads on Python 2.7; remain compatible with Python 2.6
        try:
            pool = multiprocessing.Pool(int(cores), maxtasksperchild=1)
        except TypeError:
            pool = multiprocessing.Pool(int(cores))
        yield pool.imap_unordered
        pool.terminate()


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
                if out_dir is None:
                    out_dir = os.path.dirname(in_path)
                if out_dir:
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
    @filter_to("foo")
    f("the/input/path/file.sam") ->
        f("the/input/path/file.sam", out_file="the/input/path/file_foo.bam")

    @filter_to("foo")
    f("the/input/path/file.sam", out_dir="results") ->
        f("the/input/path/file.sam", out_file="results/file_foo.bam")

    """

    def decor(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            out_file = kwargs.get("out_file", None)
            if not out_file:
                in_path = kwargs.get("in_file", args[0])
                out_dir = kwargs.get("out_dir", os.path.dirname(in_path))
                if out_dir is None:
                    out_dir = os.path.dirname(in_path)
                if out_dir:
                    safe_makedir(out_dir)
                out_name = append_stem(os.path.basename(in_path), word, "_")
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
def curdir_tmpdir(remove=True, base_dir=None):
    """Context manager to create and remove a temporary directory.

    This can also handle a configured temporary directory to use.
    """
    if base_dir is not None:
        tmp_dir_base = os.path.join(base_dir, "bcbiotmp")
    else:
        tmp_dir_base = os.path.join(os.getcwd(), "tmp")
    safe_makedir(tmp_dir_base)
    tmp_dir = tempfile.mkdtemp(dir=tmp_dir_base)
    safe_makedir(tmp_dir)
    try :
        yield tmp_dir
    finally :
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
    try :
        yield
    finally :
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
    return os.path.exists(fname) and os.path.getsize(fname) > 0

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


def append_stem(filename, word, delim="_"):
    """
    returns a filename with 'word' appended to the stem
    example: append_stem("/path/to/test.sam", "filtered") ->
    "/path/to/test_filtered.sam"

    """
    (base, ext) = os.path.splitext(filename)
    return "".join([base, delim, word, ext])


def replace_suffix(filename, suffix):
    """
    replace the suffix of filename with suffix
    example: replace_suffix("/path/to/test.sam", ".bam") ->
    "/path/to/test.bam"

    """
    (base, _) = os.path.splitext(filename)
    return base + suffix

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
    if not result:
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


def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)

########NEW FILE########
__FILENAME__ = annotation
"""Annotated variant VCF files with additional information.

- GATK variant annotation with snpEff predicted effects.
"""
import os

from bcbio import broad
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

# ## snpEff annotation

def annotate_effects(orig_file, snpeff_file, genome_file, config):
    """Annotate predicted variant effects using snpEff.
    """
    broad_runner = broad.runner_from_config(config)
    out_file = "%s-annotated%s" % os.path.splitext(orig_file)
    # Avoid generalization since 2.0.3 is not working
    #snpeff_file = _general_snpeff_version(snpeff_file)
    variant_regions = config["algorithm"].get("variant_regions", None)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "VariantAnnotator",
                      "-R", genome_file,
                      "-A", "SnpEff",
                      "--variant", orig_file,
                      "--snpEffFile", snpeff_file,
                      "--out", tx_out_file]
            broad_runner.run_gatk(params)
            if variant_regions:
                params += ["-L", variant_regions, "--interval_set_rule", "INTERSECTION"]
    return out_file

def _fix_snpeff_version_line(line, supported_versions):
    """Change snpEff versions to supported minor releases.

    ##SnpEffVersion="2.0.3 (build 2011-10-08), by Pablo Cingolani"
    """
    start, rest = line.split('"', 1)
    version, end = rest.split(" ", 1)
    version_base = version.rsplit(".", 1)[0]
    for sv in supported_versions:
        sv_base = sv.rsplit(".", 1)[0]
        if sv_base == version_base:
            version = sv
            break
    return '%s"%s %s' % (start, version, end)

def _general_snpeff_version(snpeff_file):
    """GATK wants exact snpEff versions; allow related minor releases.
    """
    gatk_versions = ["2.0.2"]
    safe_snpeff = "%s-safev%s" % os.path.splitext(snpeff_file)
    if not file_exists(safe_snpeff):
        with file_transaction(safe_snpeff) as tx_safe:
            with open(snpeff_file) as in_handle:
                with open(safe_snpeff, "w") as out_handle:
                    for line in in_handle:
                        if line.startswith("##SnpEffVersion"):
                            line = _fix_snpeff_version_line(line, gatk_versions)
                        out_handle.write(line)
    return safe_snpeff

def annotate_nongatk_vcf(orig_file, bam_file, dbsnp_file, ref_file, config):
    """Annotate a VCF file with dbSNP and standard GATK called annotations.
    """
    broad_runner = broad.runner_from_config(config)
    out_file = "%s-gatkann%s" % os.path.splitext(orig_file)
    annotations = ["BaseQualityRankSumTest", "DepthOfCoverage", "FisherStrand",
                   "GCContent", "HaplotypeScore", "HomopolymerRun",
                   "MappingQualityRankSumTest", "MappingQualityZero",
                   "QualByDepth", "ReadPosRankSumTest", "RMSMappingQuality",
                   "DepthPerAlleleBySample"]
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "VariantAnnotator",
                      "-R", ref_file,
                      "-I", bam_file,
                      "--variant", orig_file,
                      "--dbsnp", dbsnp_file,
                      "--out", tx_out_file,
                      "-L", orig_file]
            for x in annotations:
                params += ["-A", x]
            broad_runner.run_gatk(params)
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

from bcbio import broad
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.utils import file_exists, safe_makedir, partition_all
from bcbio.variation.genotype import combine_variant_files, write_empty_vcf

def run_cortex(align_bams, ref_file, config, dbsnp=None, region=None,
               out_file=None):
    """Top level entry to regional de-novo based variant calling with cortex_var.
    """
    if len(align_bams) == 1:
        align_bam = align_bams[0]
    else:
        raise NotImplementedError("Need to add multisample calling for cortex_var")
    broad_runner = broad.runner_from_config(config)
    if out_file is None:
        out_file = "%s-cortex.vcf" % os.path.splitext(align_bam)[0]
    if region is not None:
        work_dir = safe_makedir(os.path.join(os.path.dirname(out_file),
                                             region.replace(".", "_")))
    else:
        work_dir = os.path.dirname(out_file)
    if not file_exists(out_file):
        broad_runner.run_fn("picard_index", align_bam)
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
            write_empty_vcf(out_file)
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
                    raise ValueError("Unexpected VCF file: %s" % x)
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
                write_empty_vcf(out_file)
            else:
                local_ref, genome_size = _get_local_ref(region, ref_file, out_vcf_base)
                indexes = _index_local_ref(local_ref, cortex_dir, stampy_dir, kmers)
                cortex_out = _run_cortex(fastq, indexes, {"kmers": kmers, "genome_size": genome_size,
                                                          "sample": _get_sample_name(align_bam)},
                                         out_vcf_base, {"cortex": cortex_dir, "stampy": stampy_dir,
                                                        "vcftools": vcftools_dir},
                                         config)
                if cortex_out:
                    _remap_cortex_out(cortex_out, region, out_file)
                else:
                    write_empty_vcf(out_file)
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
                with open(out_file, "w") as out_handle:
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

def _get_sample_name(align_bam):
    with closing(pysam.Samfile(align_bam, "rb")) as in_pysam:
        return in_pysam.header["RG"][0]["SM"]

########NEW FILE########
__FILENAME__ = effects
"""Calculate potential effects of variations using external programs.

Supported:
  snpEff: http://sourceforge.net/projects/snpeff/
"""
import os
import csv
import glob
import subprocess
import collections

from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils

# ## snpEff variant effects

# remap Galaxy genome names to the ones used by snpEff. Not nice code.
SnpEffGenome = collections.namedtuple("SnpEffGenome", ["base", "default_version"])
SNPEFF_GENOME_REMAP = {
        "GRCh37": SnpEffGenome("GRCh37.", "68"),
        "hg19" : SnpEffGenome("hg19", ""),
        "mm9" : SnpEffGenome("NCBIM37.", "68"),
        "araTha_tair9": SnpEffGenome("athalianaTair9", ""),
        "araTha_tair10": SnpEffGenome("athalianaTair10", ""),
        }

def _find_snpeff_datadir(config_file):
    with open(config_file) as in_handle:
        for line in in_handle:
            if line.startswith("data_dir"):
                data_dir = config_utils.expand_path(line.split("=")[-1].strip())
                if not data_dir.startswith("/"):
                    data_dir = os.path.join(os.path.dirname(config_file, data_dir))
                return data_dir
    raise ValueError("Did not find data directory in snpEff config file: %s" % config_file)

def _installed_snpeff_genome(config_file, base_name):
    """Find the most recent installed genome for snpEff with the given name.
    """
    data_dir = _find_snpeff_datadir(config_file)
    dbs = sorted(glob.glob(os.path.join(data_dir, "%s*" % base_name)), reverse=True)
    if len(dbs) == 0:
        raise ValueError("No database found in %s for %s" % (data_dir, base_name))
    else:
        return os.path.split(dbs[0])[-1]

def _get_snpeff_genome(gname, config):
    """Generalize retrieval of the snpEff genome to use for an input name.

    This tries to find the snpEff configuration file and identify the
    installed genome corresponding to the input genome name.
    """
    try:
        ginfo = SNPEFF_GENOME_REMAP[gname]
    except KeyError:
        ginfo = SNPEFF_GENOME_REMAP[gname.split("-")[0]]
    snpeff_config_file = os.path.join(config_utils.get_program("snpEff", config, "dir"),
                                      "snpEff.config")
    if os.path.exists(snpeff_config_file):
        return _installed_snpeff_genome(snpeff_config_file, ginfo.base)
    else:
        return "%s%s" % (ginfo.base, ginfo.default_version)

def snpeff_effects(vcf_in, genome, config):
    """Annotate input VCF file with effects calculated by snpEff.
    """
    interval_file = config["algorithm"].get("hybrid_target", None)
    if _vcf_has_items(vcf_in):
        se_interval = (_convert_to_snpeff_interval(interval_file, vcf_in)
                       if interval_file else None)
        try:
            vcf_file = _run_snpeff(vcf_in, _get_snpeff_genome(genome, config),
                                   se_interval, "vcf", config)
        finally:
            for fname in [se_interval]:
                if fname and os.path.exists(fname):
                    os.remove(fname)
        return vcf_file

def _run_snpeff(snp_in, genome, se_interval, out_format, config):
    snpeff_jar = config_utils.get_jar("snpEff",
                                      config_utils.get_program("snpEff", config, "dir"))
    config_file = "%s.config" % os.path.splitext(snpeff_jar)[0]
    resources = config_utils.get_resources("snpEff", config)
    ext = "vcf" if out_format == "vcf" else "tsv"
    out_file = "%s-effects.%s" % (os.path.splitext(snp_in)[0], ext)
    if not file_exists(out_file):
        cl = ["java"]
        cl += resources.get("jvm_opts", [])
        cl += ["-jar", snpeff_jar, "eff", "-c", config_file,
               "-1", "-i", "vcf", "-o", out_format, genome, snp_in]
        if se_interval:
            cl.extend(["-filterInterval", se_interval])
        print " ".join(cl)
        with file_transaction(out_file) as tx_out_file:
            with open(tx_out_file, "w") as out_handle:
                subprocess.check_call(cl, stdout=out_handle)
    return out_file

def _vcf_has_items(in_file):
    if os.path.exists(in_file):
        with open(in_file) as in_handle:
            for line in in_handle:
                if line.strip() and not line.startswith("#"):
                    return True
    return False

def _convert_to_snpeff_interval(in_file, base_file):
    """Handle wide variety of BED-like inputs, converting to BED-3.
    """
    out_file = "%s-snpeff-intervals.bed" % os.path.splitext(base_file)[0]
    if not os.path.exists(out_file):
        with open(out_file, "w") as out_handle:
            writer = csv.writer(out_handle, dialect="excel-tab")
            with open(in_file) as in_handle:
                for line in (l for l in in_handle if not l.startswith(("@", "#"))):
                    parts = line.split()
                    writer.writerow(parts[:3])
    return out_file

########NEW FILE########
__FILENAME__ = ensemble
"""Ensemble methods that create consensus calls from multiple approaches.

This handles merging calls produced by multiple calling methods or
technologies into a single consolidated callset. Uses the bcbio.variation
toolkit: https://github.com/chapmanb/bcbio.variation
"""
import os
import glob
import copy
import subprocess

import yaml

from bcbio import utils
from bcbio.log import logger
from bcbio.pipeline import config_utils

def combine_calls(data):
    """Combine multiple callsets into a final set of merged calls.
    """
    if len(data["variants"]) > 1 and data["config"]["algorithm"].has_key("ensemble"):
        logger.info("Ensemble consensus calls for {0}: {1}".format(
            ",".join(x["variantcaller"] for x in data["variants"]), data["work_bam"]))
        sample = data["name"][-1].replace(" ", "_")
        base_dir = utils.safe_makedir(os.path.join(data["dirs"]["work"], "ensemble"))
        config_file = _write_config_file(data, sample, base_dir, "ensemble")
        callinfo = _run_bcbio_variation(config_file, base_dir, sample, data)
        data = copy.deepcopy(data)
        data["variants"].insert(0, callinfo)
        _write_config_file(data, sample, base_dir, "compare")
    return [[data]]

def _run_bcbio_variation(config_file, base_dir, sample, data):
    tmp_dir = utils.safe_makedir(os.path.join(base_dir, "tmp"))
    out_vcf_file = os.path.join(base_dir, "{0}-ensemble.vcf".format(sample))
    out_bed_file = os.path.join(base_dir, "{0}-callregions.bed".format(sample))
    if not utils.file_exists(out_vcf_file):
        bv_jar = config_utils.get_jar("bcbio.variation",
                                      config_utils.get_program("bcbio_variation",
                                                               data["config"], "dir"))
        java_args = ["-Djava.io.tmpdir=%s" % tmp_dir]
        subprocess.check_call(["java"] + java_args + ["-jar", bv_jar, "variant-compare", config_file])
        base_vcf = glob.glob(os.path.join(base_dir, sample, "work", "prep",
                                          "*-cfilter.vcf"))[0]
        base_bed = glob.glob(os.path.join(base_dir, sample, "work", "prep",
                                          "*-multicombine.bed"))[0]
        os.symlink(base_vcf, out_vcf_file)
        os.symlink(base_bed, out_bed_file)

    return {"variantcaller": "ensemble",
            "vrn_file": out_vcf_file,
            "bed_file": out_bed_file}

def _write_config_file(data, sample, base_dir, config_name):
    """Write YAML configuration to generate an ensemble set of combined calls.
    """
    sample_dir = os.path.join(base_dir, sample)
    config_dir = utils.safe_makedir(os.path.join(sample_dir, "config"))
    config_file = os.path.join(config_dir, "{0}.yaml".format(config_name))
    prep_fns = {"ensemble": _prep_config_ensemble, "compare": _prep_config_compare}

    econfig = prep_fns[config_name](sample, data["variants"],
                                    data["work_bam"], data["sam_ref"], sample_dir,
                                    data["config"]["algorithm"].get("variant_regions", None),
                                    data["config"]["algorithm"])
    with open(config_file, "w") as out_handle:
        yaml.dump(econfig, out_handle, allow_unicode=False, default_flow_style=False)
    return config_file

def _prep_config_compare(sample, variants, align_bam, ref_file, base_dir,
                         intervals, algorithm):
    """Write YAML bcbio.variation configuration input for results comparison.

    Preps a config file making it easy to compare finalized combined calls
    to individual inputs.
    """
    return _prep_config_shared(sample, variants, align_bam, ref_file, base_dir,
                               intervals, algorithm, "compare", False)

def _prep_config_ensemble(sample, variants, align_bam, ref_file, base_dir,
                          intervals, algorithm):
    """Prepare a YAML configuration file describing the sample inputs.
    """
    return _prep_config_shared(sample, variants, align_bam, ref_file, base_dir,
                               intervals, algorithm, "work", True)

def _prep_config_shared(sample, variants, align_bam, ref_file, base_dir,
                          intervals, algorithm, work_dir, do_combo):
    combo_name = "combo"
    exp = {"sample": sample, "ref": ref_file, "align": align_bam, "calls": []}
    if do_combo:
        cparams = algorithm["ensemble"].get("classifier-params", {})
        exp["finalize"] = \
          [{"method": "multiple",
            "target": combo_name},
            {"method": "recal-filter",
             "target": [combo_name, variants[0]["variantcaller"]],
             "params": {"support": combo_name,
                        "classifiers": algorithm["ensemble"]["classifiers"],
                        "classifier-type": cparams.get("type", "svm"),
                        "normalize": cparams.get("normalize", "default"),
                        "log-attrs": cparams.get("log-attrs", []),
                        "xspecific": True,
                        "trusted":
                        {"total": algorithm["ensemble"].get("trusted-pct", 0.65)}}}]
    if intervals:
        exp["intervals"] = os.path.abspath(intervals)
    for i, v in enumerate(variants):
        cur = {"name": v["variantcaller"], "file": v["vrn_file"],
               "remove-refcalls": True}
        if algorithm.get("ploidy", 2) == 1:
            cur["make-haploid"] = True
        # add a recall variant for the first sample which will combine all calls
        if i == 0 and do_combo:
            recall = copy.deepcopy(cur)
            recall["name"] = combo_name
            recall["recall"] = True
            recall["annotate"] = True
            if algorithm["ensemble"].get("format-filters"):
                recall["format-filters"] = algorithm["ensemble"]["format-filters"]
            exp["calls"].append(recall)
        exp["calls"].append(cur)
    return {"dir": {"base": base_dir, "out": work_dir, "prep": os.path.join(work_dir, "prep")},
            "experiments": [exp]}

########NEW FILE########
__FILENAME__ = freebayes
"""Bayesian variant calling with FreeBayes.

http://bioinformatics.bc.edu/marthlab/FreeBayes
"""
import os
import shutil
import subprocess

from bcbio import broad
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.variation import annotation, genotype
from bcbio.log import logger
from bcbio.pipeline import config_utils
from bcbio.pipeline.shared import subset_variant_regions

def _freebayes_options_from_config(aconfig, out_file, region=None):
    opts = []
    ploidy = aconfig.get("ploidy", 2)
    opts += ["--ploidy", str(ploidy)]
    if ploidy == 2:
        opts += ["--min-alternate-fraction", "0.2"]

    variant_regions = aconfig.get("variant_regions", None)
    target = subset_variant_regions(variant_regions, region, out_file)
    if target:
        opts += ["--region" if target == region else "--targets", target]
    background = aconfig.get("call_background", None)
    if background and os.path.exists(background):
        opts += ["--variant-input", background]
    return opts

def run_freebayes(align_bams, ref_file, config, dbsnp=None, region=None,
                  out_file=None):
    """Detect small polymorphisms with FreeBayes.
    """
    if len(align_bams) == 1:
        align_bam = align_bams[0]
    else:
        raise NotImplementedError("Need to add multisample calling for freebayes")
    broad_runner = broad.runner_from_config(config)
    broad_runner.run_fn("picard_index", align_bam)
    if out_file is None:
        out_file = "%s-variants.vcf" % os.path.splitext(align_bam)[0]
    if not file_exists(out_file):
        logger.info("Genotyping with FreeBayes: {region} {fname}".format(
            region=region, fname=os.path.basename(align_bam)))
        with file_transaction(out_file) as tx_out_file:
            cl = [config_utils.get_program("freebayes", config),
                  "-b", align_bam, "-v", tx_out_file, "-f", ref_file,
                  "--left-align-indels", "--use-mapping-quality",
                  "--min-alternate-count", "2"]
            cl += _freebayes_options_from_config(config["algorithm"], out_file, region)
            subprocess.check_call(cl)
        _remove_freebayes_refalt_dups(out_file)
        _post_filter_freebayes(out_file, ref_file, broad_runner)
    return out_file

def _move_vcf(orig_file, new_file):
    """Move a VCF file with associated index.
    """
    for ext in ["", ".idx"]:
        to_move = orig_file + ext
        if os.path.exists(to_move):
            shutil.move(to_move, new_file + ext)

def _post_filter_freebayes(orig_file, ref_file, broad_runner):
    """Perform basic sanity filtering of FreeBayes results, removing low confidence calls.
    """
    in_file = apply("{0}-raw{1}".format, os.path.splitext(orig_file))
    _move_vcf(orig_file, in_file)
    filters = ["QUAL < 20.0", "DP < 5"]
    filter_file = genotype.variant_filtration_with_exp(broad_runner,
                                                       in_file, ref_file, "", filters)
    _move_vcf(filter_file, orig_file)

def _remove_freebayes_refalt_dups(in_file):
    """Remove lines from FreeBayes outputs where REF/ALT are identical.
    2       22816178        .       G       G       0.0339196
    """
    out_file = apply("{0}-nodups{1}".format, os.path.splitext(in_file))
    if not file_exists(out_file):
        with open(in_file) as in_handle:
            with open(out_file, "w") as out_handle:
                for line in in_handle:
                    if line.startswith("#"):
                        out_handle.write(line)
                    else:
                        parts = line.split("\t")
                        if parts[3] != parts[4]:
                            out_handle.write(line)
        _move_vcf(in_file, "{0}.orig".format(in_file))
        _move_vcf(out_file, in_file)
        with open(out_file, "w") as out_handle:
            out_handle.write("Moved to {0}".format(in_file))

def postcall_annotate(in_file, bam_file, ref_file, vrn_files, config):
    """Perform post-call annotation of FreeBayes calls in preparation for filtering.
    """
    #out_file = _check_file_gatk_merge(in_file)
    out_file = annotation.annotate_nongatk_vcf(in_file, bam_file, vrn_files.dbsnp,
                                               ref_file, config)
    return out_file

def _check_file_gatk_merge(vcf_file):
    """Remove problem lines generated by GATK merging from FreeBayes calls.

    Works around this issue until next GATK release:
    http://getsatisfaction.com/gsa/topics/
    variantcontext_creates_empty_allele_from_vcf_input_with_multiple_alleles
    """
    def _not_empty_allele(line):
        parts = line.split("\t")
        alt = parts[4]
        return not alt[0] == ","
    orig_file = "{0}.orig".format(vcf_file)
    if not file_exists(orig_file):
        shutil.move(vcf_file, orig_file)
        with open(orig_file) as in_handle:
            with open(vcf_file, "w") as out_handle:
                for line in in_handle:
                    if line.startswith("#") or _not_empty_allele(line):
                        out_handle.write(line)
    return vcf_file

########NEW FILE########
__FILENAME__ = genotype
"""Provide SNP, indel calling and variation analysis using GATK genotyping tools.

Genotyping:

http://www.broadinstitute.org/gsa/wiki/index.php/Best_Practice_Variant_Detection_with_the_GATK_v3
http://www.broadinstitute.org/gsa/wiki/index.php/Unified_genotyper

Variant Evaluation:

http://www.broadinstitute.org/gsa/wiki/index.php/VariantEval
"""
import os
import copy
import itertools
import collections

from bcbio import broad
from bcbio.log import logger
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.distributed.split import (parallel_split_combine,
                                     grouped_parallel_split_combine)
from bcbio.pipeline.shared import (process_bam_by_chromosome, configured_ref_file,
                                   subset_variant_regions)
from bcbio.variation.realign import has_aligned_reads
from bcbio.variation import multi

# ## GATK Genotype calling

def _shared_gatk_call_prep(align_bams, ref_file, config, dbsnp, region, out_file):
    """Shared preparation work for GATK variant calling.
    """
    broad_runner = broad.runner_from_config(config)
    broad_runner.run_fn("picard_index_ref", ref_file)
    for x in align_bams:
        broad_runner.run_fn("picard_index", x)
    coverage_depth = config["algorithm"].get("coverage_depth", "high").lower()
    variant_regions = config["algorithm"].get("variant_regions", None)
    confidence = "4.0" if coverage_depth in ["low"] else "30.0"
    if out_file is None:
        out_file = "%s-variants.vcf" % os.path.splitext(align_bams[0])[0]
    region = subset_variant_regions(variant_regions, region, out_file)

    params = ["-R", ref_file,
              "--annotation", "QualByDepth",
              "--annotation", "HaplotypeScore",
              "--annotation", "MappingQualityRankSumTest",
              "--annotation", "ReadPosRankSumTest",
              "--annotation", "FisherStrand",
              "--annotation", "RMSMappingQuality",
              "--annotation", "DepthOfCoverage",
              "--standard_min_confidence_threshold_for_calling", confidence,
              "--standard_min_confidence_threshold_for_emitting", confidence,
              ]
    for x in align_bams:
        params += ["-I", x]
    if dbsnp:
        params += ["--dbsnp", dbsnp]
    if region:
        params += ["-L", region, "--interval_set_rule", "INTERSECTION"]
    return broad_runner, params, out_file

def unified_genotyper(align_bams, ref_file, config, dbsnp=None,
                       region=None, out_file=None):
    """Perform SNP genotyping on the given alignment file.
    """
    broad_runner, params, out_file = \
        _shared_gatk_call_prep(align_bams, ref_file, config, dbsnp,
                               region, out_file)
    if not file_exists(out_file):
        if not all(has_aligned_reads(x, region) for x in align_bams):
            write_empty_vcf(out_file)
        else:
            with file_transaction(out_file) as tx_out_file:
                params += ["-T", "UnifiedGenotyper",
                           "-o", tx_out_file,
                           "--genotype_likelihoods_model", "BOTH"]
                broad_runner.run_gatk(params)
    return out_file

def haplotype_caller(align_bam, ref_file, config, dbsnp=None,
                       region=None, out_file=None):
    """Call variation with GATK's HaplotypeCaller.

    This requires the full non open-source version of GATK.
    """
    broad_runner, params, out_file = \
        _shared_gatk_call_prep(align_bams, ref_file, config, dbsnp,
                               region, out_file)
    assert broad_runner.has_gatk_full(), \
        "Require full version of GATK 2.0 for haplotype based calling"
    if not file_exists(out_file):
        if not all(has_aligned_reads(x, region) for x in align_bams):
            write_empty_vcf(out_file)
        else:
            with file_transaction(out_file) as tx_out_file:
                params += ["-T", "HaplotypeCaller",
                           "-o", tx_out_file]
                broad_runner.run_gatk(params)
    return out_file

def write_empty_vcf(out_file):
    with open(out_file, "w") as out_handle:
        out_handle.write("##fileformat=VCFv4.1\n"
                         "## No variants; no reads aligned in region\n"
                         "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")

# ## Utility functions for dealing with VCF files

def split_snps_indels(broad_runner, orig_file, ref_file):
    """Split a variant call file into SNPs and INDELs for processing.
    """
    base, ext = os.path.splitext(orig_file)
    snp_file = "{base}-snp{ext}".format(base=base, ext=ext)
    indel_file = "{base}-indel{ext}".format(base=base, ext=ext)
    params = ["-T", "SelectVariants",
              "-R", ref_file,
              "--variant", orig_file]
    for out_file, select_type in [(snp_file, ["SNP"]),
                                  (indel_file, ["INDEL", "MIXED", "MNP",
                                                "SYMBOLIC", "NO_VARIATION"])]:
        if not file_exists(out_file):
            with file_transaction(out_file) as tx_out_file:
                cur_params = params + ["--out", tx_out_file]
                for x in select_type:
                    cur_params += ["--selectTypeToInclude", x]
                broad_runner.run_gatk(cur_params)
    return snp_file, indel_file

def combine_variant_files(orig_files, out_file, ref_file, config,
                          quiet_out=True):
    """Combine multiple VCF files into a single output file.
    """
    broad_runner = broad.runner_from_config(config)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "CombineVariants",
                      "-R", ref_file,
                      "--out", tx_out_file]
            priority_order = []
            for orig_file in orig_files:
                name = os.path.splitext(os.path.basename(orig_file))[0]
                params.extend(["--variant:{name}".format(name=name), orig_file])
                priority_order.append(name)
            params.extend(["--rod_priority_list", ",".join(priority_order)])
            if quiet_out:
                params.extend(["--suppressCommandLineHeader", "--setKey", "null"])
            broad_runner.run_gatk(params)
    return out_file

# ## Variant filtration -- shared functionality

def variant_filtration(call_file, ref_file, vrn_files, config):
    """Filter variant calls using Variant Quality Score Recalibration.

    Newer GATK with Haplotype calling has combined SNP/indel filtering.
    """
    broad_runner = broad.runner_from_config(config)
    caller = config["algorithm"].get("variantcaller")
    cov_interval = config["algorithm"].get("coverage_interval", "exome").lower()
    if caller in ["gatk-haplotype"] and cov_interval not in ["regional"]:
        return _variant_filtration_both(broad_runner, call_file, ref_file, vrn_files,
                                        config)
    # no additional filtration for callers that filter as part of call process
    elif caller in ["samtools", "varscan"]:
        return call_file
    else:
        snp_file, indel_file = split_snps_indels(broad_runner, call_file, ref_file)
        snp_filter_file = _variant_filtration_snp(broad_runner, snp_file, ref_file,
                                                  vrn_files, config)
        indel_filter_file = _variant_filtration_indel(broad_runner, indel_file,
                                                      ref_file, vrn_files, config)
        orig_files = [snp_filter_file, indel_filter_file]
        out_file = "{base}combined.vcf".format(base=os.path.commonprefix(orig_files))
        return combine_variant_files(orig_files, out_file, ref_file, config)

def _apply_variant_recal(broad_runner, snp_file, ref_file, recal_file,
                         tranch_file, filter_type):
    """Apply recalibration details, returning filtered VCF file.
    """
    base, ext = os.path.splitext(snp_file)
    out_file = "{base}-{filter}filter{ext}".format(base=base, ext=ext,
                                                   filter=filter_type)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "ApplyRecalibration",
                      "-R", ref_file,
                      "--input", snp_file,
                      "--out", tx_out_file,
                      "--tranches_file", tranch_file,
                      "--recal_file", recal_file,
                      "--mode", filter_type]
            broad_runner.run_gatk(params)
    return out_file

def _shared_variant_filtration(filter_type, cov_interval, snp_file,
                               ref_file, vrn_files):
    """Share functionality for filtering variants.
    """
    recal_file = "{base}.recal".format(base = os.path.splitext(snp_file)[0])
    tranches_file = "{base}.tranches".format(base = os.path.splitext(snp_file)[0])
    params = ["-T", "VariantRecalibrator",
              "-R", ref_file,
              "--input", snp_file,
              "--mode", filter_type,
              "-an", "QD",
              "-an", "FS",
              "-an", "HaplotypeScore",
              "-an", "ReadPosRankSum"]
    if filter_type in ["SNP", "BOTH"]:
        params.extend(
            ["-resource:hapmap,VCF,known=false,training=true,truth=true,prior=15.0",
             vrn_files.train_hapmap,
             "-resource:omni,VCF,known=false,training=true,truth=false,prior=12.0",
             vrn_files.train_1000g_omni,
             "-resource:dbsnp,VCF,known=true,training=false,truth=false,prior=8.0",
             vrn_files.dbsnp,
              "-an", "MQRankSum",
              "-an", "MQ"])
    if filter_type in ["INDEL", "BOTH"]:
        assert vrn_files.train_indels, \
               "Need indel training file specified"
        params.extend(
            ["-resource:mills,VCF,known=true,training=true,truth=true,prior=12.0",
             vrn_files.train_indels,])
    if cov_interval == "exome":
        params.extend(["--maxGaussians", "4", "--percentBadVariants", "0.05"])
    else:
        params.extend(["-an", "DP"])
    return params, recal_file, tranches_file

def variant_filtration_with_exp(broad_runner, snp_file, ref_file, filter_type,
                                expressions):
    """Perform hard filtering with GATK using JEXL expressions.

    Variant quality score recalibration will not work on some regions; it
    requires enough positions to train the model. This provides a general wrapper
    around GATK to do cutoff based filtering.
    """
    base, ext = os.path.splitext(snp_file)
    out_file = "{base}-filter{ftype}{ext}".format(base=base, ext=ext,
                                                  ftype=filter_type)
    if not file_exists(out_file):
        logger.info("Hard filtering %s with %s" % (snp_file, expressions))
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "VariantFiltration",
                      "-R", ref_file,
                      "--out", tx_out_file,
                      "--variant", snp_file]
            for exp in expressions:
                params.extend(["--filterName", "GATKStandard{e}".format(e=exp.split()[0]),
                               "--filterExpression", exp])
            broad_runner.run_gatk(params)
    return out_file

# ## SNP specific variant filtration

def _variant_filtration_snp(broad_runner, snp_file, ref_file, vrn_files,
                            config):
    """Filter SNP variant calls using GATK best practice recommendations.
    """
    filter_type = "SNP"
    cov_interval = config["algorithm"].get("coverage_interval", "exome").lower()
    variantcaller = config["algorithm"].get("variantcaller", "gatk")
    params, recal_file, tranches_file = _shared_variant_filtration(
        filter_type, cov_interval, snp_file, ref_file, vrn_files)
    assert vrn_files.train_hapmap and vrn_files.train_1000g_omni, \
           "Need HapMap and 1000 genomes training files"
    filters = ["QD < 2.0", "MQ < 40.0", "FS > 60.0",
               "MQRankSum < -12.5", "ReadPosRankSum < -8.0"]
    # GATK Haplotype caller (v2.2) appears to have much larger HaplotypeScores
    # resulting in excessive filtering, so avoid this metric
    if variantcaller not in ["gatk-haplotype"]:
        filters.append("HaplotypeScore > 13.0")
    if cov_interval == "regional" or variantcaller == "freebayes":
        return variant_filtration_with_exp(broad_runner, snp_file, ref_file, filter_type,
                                           filters)
    else:
        # also check if we've failed recal and needed to do strict filtering
        filter_file = "{base}-filterSNP.vcf".format(base = os.path.splitext(snp_file)[0])
        if file_exists(filter_file):
            config["algorithm"]["coverage_interval"] = "regional"
            return _variant_filtration_snp(broad_runner, snp_file, ref_file, vrn_files,
                                           config)
        if not file_exists(recal_file):
            with file_transaction(recal_file, tranches_file) as (tx_recal, tx_tranches):
                params.extend(["--recal_file", tx_recal,
                               "--tranches_file", tx_tranches])
                try:
                    broad_runner.run_gatk(params)
                # Can fail to run if not enough values are present to train. Rerun with regional
                # filtration approach instead
                except:
                    config["algorithm"]["coverage_interval"] = "regional"
                    return _variant_filtration_snp(broad_runner, snp_file, ref_file, vrn_files,
                                                   config)
        return _apply_variant_recal(broad_runner, snp_file, ref_file, recal_file,
                                    tranches_file, filter_type)

# ## Indel specific variant filtration

def _variant_filtration_indel(broad_runner, snp_file, ref_file, vrn_files,
                              config):
    """Filter indel variant calls using GATK best practice recommendations.
    """
    filter_type = "INDEL"
    cov_interval = config["algorithm"].get("coverage_interval", "exome").lower()
    params, recal_file, tranches_file = _shared_variant_filtration(
        filter_type, cov_interval, snp_file, ref_file, vrn_files)
    if cov_interval in ["exome", "regional"]:
        return variant_filtration_with_exp(broad_runner, snp_file, ref_file, filter_type,
                                           ["QD < 2.0", "ReadPosRankSum < -20.0", "FS > 200.0"])
    else:
        if not file_exists(recal_file):
            with file_transaction(recal_file, tranches_file) as (tx_recal, tx_tranches):
                params.extend(["--recal_file", tx_recal,
                               "--tranches_file", tx_tranches])
                broad_runner.run_gatk(params)
        return _apply_variant_recal(broad_runner, snp_file, ref_file, recal_file,
                                    tranches_file, filter_type)

# ## Variant filtration for combined indels and SNPs

def _variant_filtration_both(broad_runner, snp_file, ref_file, vrn_files,
                              config):
    """Filter SNP and indel variant calls using GATK best practice recommendations.
    """
    filter_type = "BOTH"
    cov_interval = config["algorithm"].get("coverage_interval", "exome").lower()
    params, recal_file, tranches_file = _shared_variant_filtration(
        filter_type, cov_interval, snp_file, ref_file, vrn_files)
    if not file_exists(recal_file):
        with file_transaction(recal_file, tranches_file) as (tx_recal, tx_tranches):
            params.extend(["--recal_file", tx_recal,
                           "--tranches_file", tx_tranches])
            broad_runner.run_gatk(params)
    return _apply_variant_recal(broad_runner, snp_file, ref_file, recal_file,
                                tranches_file, filter_type)

# ## Variant evaluation

def gatk_evaluate_variants(vcf_file, ref_file, config, dbsnp=None, intervals=None):
    """Evaluate variants, return SNP counts and Transition/Transversion ratios.
    """
    runner = broad.runner_from_config(config)
    eval_file = variant_eval(vcf_file, ref_file, dbsnp, intervals, runner)
    stats = _extract_eval_stats(eval_file)
    return _format_stats(stats['called'])

def _format_stats(stats):
    """Convert statistics into high level summary of major variables.
    """
    total = sum(itertools.chain.from_iterable(s.itervalues() for s in stats.itervalues()))
    if total > 0:
        dbsnp = sum(stats['known'].itervalues()) / float(total) * 100.0
    else:
        dbsnp = -1.0
    tv_dbsnp = stats['known']['tv']
    ti_dbsnp = stats['known']['ti']
    tv_novel = stats['novel']['tv']
    ti_novel = stats['novel']['ti']
    if tv_novel > 0 and tv_dbsnp > 0:
        titv_all = float(ti_novel + ti_dbsnp) / float(tv_novel + tv_dbsnp)
        titv_dbsnp = float(ti_dbsnp) / float(tv_dbsnp)
        titv_novel = float(ti_novel) / float(tv_novel)
    else:
        titv_all, titv_dbsnp, titv_novel = (-1.0, -1.0, -1.0)
    return dict(total=total, dbsnp_pct = dbsnp, titv_all=titv_all,
                titv_dbsnp=titv_dbsnp, titv_novel=titv_novel)

def _extract_eval_stats(eval_file):
    """Parse statistics of interest from GATK output file.
    """
    stats = dict()
    for snp_type in ['called', 'filtered']:
        stats[snp_type]  = dict()
        for dbsnp_type in ['known', 'novel']:
            stats[snp_type][dbsnp_type] = dict(ti=0, tv=0)
    for line in _eval_analysis_type(eval_file, "Ti/Tv Variant Evaluator"):
        if line[1:3] == ['dbsnp', 'eval']:
            snp_type = line[3]
            dbsnp_type = line[5]
            try:
                cur = stats[snp_type][dbsnp_type]
            except KeyError:
                cur = None
            if cur:
                stats[snp_type][dbsnp_type]["ti"] = int(line[6])
                stats[snp_type][dbsnp_type]["tv"] = int(line[7])
    return stats

def _eval_analysis_type(in_file, analysis_name):
    """Retrieve data lines associated with a particular analysis.
    """
    supported_versions = ["v0.2", "v1.0", "v1.1"]
    with open(in_file) as in_handle:
        # read until we reach the analysis
        for line in in_handle:
            if line.startswith(("##:GATKReport", "#:GATKReport")):
                version = line.split()[0].split(".", 1)[-1].split(":")[0]
                assert version in supported_versions, \
                       "Unexpected GATKReport version: {0}".format(version)
                if line.find(analysis_name) > 0:
                    break
        # read off header lines
        for _ in range(1):
            in_handle.next()
        # read the table until a blank line
        for line in in_handle:
            if not line.strip():
                break
            parts = line.rstrip("\n\r").split()
            yield parts

def variant_eval(vcf_in, ref_file, dbsnp, target_intervals, picard):
    """Evaluate variants in comparison with dbSNP reference.
    """
    out_file = "%s.eval" % os.path.splitext(vcf_in)[0]
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "VariantEval",
                      "-R", ref_file,
                      "--eval", vcf_in,
                      "--dbsnp", dbsnp,
                      "-ST", "Filter",
                      "-o", tx_out_file,
                      "-l", "INFO",
                      "--doNotUseAllStandardModules",
                      "--evalModule", "CompOverlap",
                      "--evalModule", "CountVariants",
                      "--evalModule", "GenotypeConcordance",
                      "--evalModule", "TiTvVariantEvaluator",
                      "--evalModule", "ValidationReport",
                      "--stratificationModule", "Filter"]
            if target_intervals:
                # BED file target intervals are explicit with GATK 1.3
                # http://getsatisfaction.com/gsa/topics/
                # gatk_v1_3_and_bed_interval_file_must_be_parsed_through_tribble
                if _is_bed_file(target_intervals):
                    flag = "-L:bed"
                else:
                    flag = "-L"
                params.extend([flag, target_intervals])
            picard.run_gatk(params)
    return out_file

def _is_bed_file(fname):
    """Simple check if a file is in BED format.
    """
    if fname.lower().endswith(".bed"):
        return True
    with open(fname) as in_handle:
        for line in in_handle:
            if not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) > 3:
                    try:
                        int(parts[1])
                        int(parts[2])
                        return True
                    except ValueError:
                        pass
                break
    return False

# ## High level functionality to run genotyping in parallel

def _get_variantcaller(data):
    return data["config"]["algorithm"].get("variantcaller", "gatk")

def combine_multiple_callers(data):
    """Collapse together variant calls from multiple approaches into variants
    """
    by_bam = collections.defaultdict(list)
    for x in data:
        by_bam[x[0]["work_bam"]].append(x[0])
    out = []
    for grouped_calls in by_bam.itervalues():
        ready_calls = [{"variantcaller": _get_variantcaller(x),
                        "vrn_file": x.get("vrn_file")}
                       for x in grouped_calls]
        final = grouped_calls[0]
        def orig_variantcaller_order(x):
            return final["config"]["algorithm"]["orig_variantcaller"].index(x["variantcaller"])
        if len(ready_calls) > 1:
            final["variants"] = sorted(ready_calls, key=orig_variantcaller_order)
        else:
            final["variants"] = ready_calls
        out.append([final])
    return out

def _handle_multiple_variantcallers(data):
    """Split samples that potentially require multiple variant calling approaches.
    """
    assert len(data) == 1
    callers = _get_variantcaller(data[0])
    if isinstance(callers, basestring):
        return [data]
    else:
        out = []
        for caller in callers:
            base = copy.deepcopy(data[0])
            base["config"]["algorithm"]["orig_variantcaller"] = \
              base["config"]["algorithm"]["variantcaller"]
            base["config"]["algorithm"]["variantcaller"] = caller
            out.append([base])
        return out

def parallel_variantcall(sample_info, parallel_fn):
    """Provide sample genotyping, running in parallel over individual chromosomes.
    """
    to_process = []
    finished = []
    for x in sample_info:
        if x[0]["config"]["algorithm"]["snpcall"]:
            to_process.extend(_handle_multiple_variantcallers(x))
        else:
            finished.append(x)
    if len(to_process) > 0:
        split_fn = process_bam_by_chromosome("-variants.vcf", "work_bam",
                                             dir_ext_fn = _get_variantcaller)
        processed = grouped_parallel_split_combine(
            to_process, split_fn, multi.group_batches, parallel_fn,
            "variantcall_sample", "split_variants_by_sample", "combine_variant_files",
            "vrn_file", ["sam_ref", "config"])
        finished.extend(processed)
    return finished

def variantcall_sample(data, region=None, out_file=None):
    """Parallel entry point for doing genotyping of a region of a sample.
    """
    from bcbio.variation import freebayes, cortex, samtools, varscan
    caller_fns = {"gatk": unified_genotyper,
                  "gatk-haplotype": haplotype_caller,
                  "freebayes": freebayes.run_freebayes,
                  "cortex": cortex.run_cortex,
                  "samtools": samtools.run_samtools,
                  "varscan": varscan.run_varscan}
    if data["config"]["algorithm"]["snpcall"]:
        sam_ref = data["sam_ref"]
        config = data["config"]
        caller_fn = caller_fns[config["algorithm"].get("variantcaller", "gatk")]
        if isinstance(data["work_bam"], basestring):
            align_bams = [data["work_bam"]]
        else:
            align_bams = data["work_bam"]
        data["vrn_file"] = caller_fn(align_bams, sam_ref, config,
                                     configured_ref_file("dbsnp", config, sam_ref),
                                     region, out_file)
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

from bcbio import broad, utils
from bcbio.distributed.transaction import file_transaction

def group_batches(xs):
    """Group samples into batches for simultaneous variant calling.

    Identify all samples to call together: those in the same batch,
    variant caller and genomic region.
    Pull together all BAM files from this batch and process together,
    Provide details to pull these finalized files back into individual
    expected files.
    """
    singles = []
    batch_groups = collections.defaultdict(list)
    for data, region, out_fname in xs:
        batch = data.get("metadata", {}).get("batch")
        caller = data["config"]["algorithm"]["variantcaller"]
        if batch is not None:
            batch_groups[(batch, region, caller)].append((data, out_fname))
        else:
            singles.append((data, region, out_fname))
    batches = []
    remap_batches = {}
    for (batch, region, _), xs in batch_groups.iteritems():
        cur_data, cur_fname = xs[0]
        batch_fname = utils.append_stem(cur_fname, batch, "-")
        batch_data = copy.deepcopy(cur_data)
        batch_data["work_bam"] = [x[0]["work_bam"] for x in xs]
        batch_data["group"] = batch_fname
        batches.append((batch_data, region, batch_fname))
        remap_batches[batch_fname] = xs
    return singles + batches, remap_batches

def split_variants_by_sample(data):
    """Split a multi-sample call file into inputs for individual samples.
    """
    config = data["config"]
    vrn_file = data["vrn_file"]
    out = []
    for sub_data, sub_vrn_file in data["group_orig"]:
        if is_multisample(vrn_file):
            select_sample_from_vcf(vrn_file, sub_data["name"][-1], sub_vrn_file,
                                   data["sam_ref"], config)
        else:
            os.symlink(vrn_file, sub_vrn_file)
        sub_data["vrn_file"] = sub_vrn_file
        out.append(sub_data)
    return out

def select_sample_from_vcf(in_file, sample, out_file, ref_file, config):
    """Select a single sample from the supplied multisample VCF file.
    """
    brunner = broad.runner_from_config(config)
    if not utils.file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "SelectVariants",
                      "-R", ref_file,
                      "--sample_name", sample,
                      "--variant", in_file,
                      "--out", tx_out_file]
            brunner.run_gatk(params)
    return out_file

def is_multisample(fname):
    """Check VCF header to determine if we have a multi-sample file.
    """
    with open(fname) as in_handle:
        for line in in_handle:
            if line.startswith("#CHROM"):
                return len(line.split("\t")) > 10

########NEW FILE########
__FILENAME__ = phasing
"""Approaches for calculating haplotype phasing of variants.

Currently supports GATK's Read-Backed phasing:

http://www.broadinstitute.org/gsa/wiki/index.php/Read-backed_phasing_algorithm
"""
import os

from bcbio import broad
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction

def read_backed_phasing(vcf_file, bam_file, genome_file, config):
    """Annotate predicted variant effects using snpEff.
    """
    broad_runner = broad.runner_from_config(config)
    out_file = "%s-phased%s" % os.path.splitext(vcf_file)
    variant_regions = config["algorithm"].get("variant_regions", None)
    if not file_exists(out_file):
        with file_transaction(out_file) as tx_out_file:
            params = ["-T", "ReadBackedPhasing",
                      "-R", genome_file,
                      "-I", bam_file,
                      "--variant", vcf_file,
                      "--out", tx_out_file]
            if variant_regions:
                params += ["-L", variant_regions, "--interval_set_rule", "INTERSECTION"]
            broad_runner.run_gatk(params)
    return out_file

########NEW FILE########
__FILENAME__ = realign
"""Perform realignment of BAM files around indels using the GATK toolkit.
"""
import os
import shutil
from contextlib import closing

import pysam

from bcbio import broad
from bcbio.log import logger
from bcbio.utils import curdir_tmpdir, file_exists, save_diskspace
from bcbio.distributed.transaction import file_transaction
from bcbio.distributed.split import parallel_split_combine
from bcbio.pipeline.shared import (process_bam_by_chromosome, configured_ref_file,
                                   write_nochr_reads, subset_bam_by_region,
                                   subset_variant_regions)

# ## Realignment runners with GATK specific arguments

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
            logger.info("GATK RealignerTargetCreator: %s %s" %
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
            runner.run_gatk(params)
    return out_file

def gatk_indel_realignment(runner, align_bam, ref_file, intervals,
                           region=None, out_file=None, deep_coverage=False):
    """Perform realignment of BAM file in specified regions
    """
    if out_file is None:
        out_file = "%s-realign.bam" % os.path.splitext(align_bam)[0]
    if not file_exists(out_file):
        with curdir_tmpdir() as tmp_dir:
            with file_transaction(out_file) as tx_out_file:
                logger.info("GATK IndelRealigner: %s %s" %
                            (os.path.basename(align_bam), region))
                params = ["-T", "IndelRealigner",
                          "-I", align_bam,
                          "-R", ref_file,
                          "-targetIntervals", intervals,
                          "-o", tx_out_file,
                          "-l", "INFO",
                          ]
                if region:
                    params += ["-L", region]
                if deep_coverage:
                    params += ["--maxReadsInMemory", "300000",
                               "--maxReadsForRealignment", str(int(5e5)),
                               "--maxReadsForConsensuses", "500",
                               "--maxConsensuses", "100"]
                try:
                    runner.run_gatk(params, tmp_dir)
                except:
                    logger.exception("Running GATK IndelRealigner failed: {} {}".format(
                        os.path.basename(align_bam), region))
                    raise
    return out_file

def gatk_realigner(align_bam, ref_file, config, dbsnp=None, region=None,
                   out_file=None, deep_coverage=False):
    """Realign a BAM file around indels using GATK, returning sorted BAM.
    """
    runner = broad.runner_from_config(config)
    runner.run_fn("picard_index", align_bam)
    runner.run_fn("picard_index_ref", ref_file)
    if not os.path.exists("%s.fai" % ref_file):
        pysam.faidx(ref_file)
    if region:
        align_bam = subset_bam_by_region(align_bam, region, out_file)
        runner.run_fn("picard_index", align_bam)
    if has_aligned_reads(align_bam, region):
        variant_regions = config["algorithm"].get("variant_regions", None)
        realign_target_file = gatk_realigner_targets(runner, align_bam,
                                                     ref_file, dbsnp, region,
                                                     out_file, deep_coverage,
                                                     variant_regions)
        realign_bam = gatk_indel_realignment(runner, align_bam, ref_file,
                                             realign_target_file, region,
                                             out_file, deep_coverage)
        # No longer required in recent GATK (> Feb 2011) -- now done on the fly
        # realign_sort_bam = runner.run_fn("picard_fixmate", realign_bam)
        return realign_bam
    elif out_file:
        shutil.copy(align_bam, out_file)
        return out_file
    else:
        return align_bam

def has_aligned_reads(align_bam, region=None):
    """Check if the aligned BAM file has any reads in the region.
    """
    has_items = False
    with closing(pysam.Samfile(align_bam, "rb")) as cur_bam:
        if region is not None:
            for item in cur_bam.fetch(region):
                has_items = True
                break
        else:
            for item in cur_bam:
                if not item.is_unmapped:
                    has_items = True
                    break
    return has_items

# ## High level functionality to run realignments in parallel

def parallel_realign_sample(sample_info, parallel_fn):
    """Realign samples, running in parallel over individual chromosomes.
    """
    to_process = []
    finished = []
    for x in sample_info:
        if (x[0]["config"]["algorithm"]["snpcall"] and
            x[0]["config"]["algorithm"].get("realign", True)):
            to_process.append(x)
        else:
            finished.append(x)
    if len(to_process) > 0:
        file_key = "work_bam"
        split_fn = process_bam_by_chromosome("-realign.bam", file_key,
                                           default_targets=["nochr"])
        processed = parallel_split_combine(to_process, split_fn, parallel_fn,
                                           "realign_sample", "combine_bam",
                                           file_key, ["config"])
        finished.extend(processed)
    return finished

def realign_sample(data, region=None, out_file=None):
    """Realign sample BAM file at indels.
    """
    logger.info("Realigning %s with GATK: %s %s" % (data["name"],
                                                    os.path.basename(data["work_bam"]),
                                                    region))
    if (data["config"]["algorithm"]["snpcall"] and
        data["config"]["algorithm"].get("realign", True)):
        sam_ref = data["sam_ref"]
        config = data["config"]
        if region == "nochr":
            realign_bam = write_nochr_reads(data["work_bam"], out_file)
        else:
            realign_bam = gatk_realigner(data["work_bam"], sam_ref, config,
                                         configured_ref_file("dbsnp", config, sam_ref),
                                         region, out_file)
        if region is None:
            save_diskspace(data["work_bam"], "Realigned to %s" % realign_bam,
                           config)
        data["work_bam"] = realign_bam
    return [data]

########NEW FILE########
__FILENAME__ = recalibrate
"""Perform quality score recalibration with the GATK toolkit.

Corrects read quality scores post-alignment to provide improved estimates of
error rates based on alignments to the reference genome.

http://www.broadinstitute.org/gsa/wiki/index.php/Base_quality_score_recalibration
"""
import os
import shutil
from contextlib import closing

import pysam

from bcbio import broad
from bcbio.log import logger
from bcbio.utils import curdir_tmpdir, file_exists
from bcbio.distributed.split import parallel_split_combine
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline.shared import (configured_ref_file, process_bam_by_chromosome,
                                   subset_bam_by_region, write_nochr_reads)
from bcbio.variation.realign import has_aligned_reads

def prep_recal(data):
    """Perform a GATK recalibration of the sorted aligned BAM, producing recalibrated BAM.
    """
    if data["config"]["algorithm"].get("recalibrate", True):
        logger.info("Recalibrating %s with GATK" % str(data["name"]))
        ref_file = data["sam_ref"]
        config = data["config"]
        dbsnp_file = configured_ref_file("dbsnp", config, ref_file)
        broad_runner = broad.runner_from_config(config)
        platform = config["algorithm"]["platform"]
        broad_runner.run_fn("picard_index_ref", ref_file)
        if config["algorithm"].get("mark_duplicates", True):
            (dup_align_bam, _) = broad_runner.run_fn("picard_mark_duplicates", data["work_bam"],
                                                     remove_dups=True)
        else:
            dup_align_bam = data["work_bam"]
        broad_runner.run_fn("picard_index", dup_align_bam)
        intervals = config["algorithm"].get("variant_regions", None)
        data["work_bam"] = dup_align_bam
        data["prep_recal"] = _gatk_base_recalibrator(broad_runner, dup_align_bam, ref_file,
                                                     platform, dbsnp_file, intervals)
    return [[data]]

# ## Identify recalibration information

def _get_downsample_pct(runner, in_bam):
    """Calculate a downsampling percent to use for large BAM files.

    Large whole genome BAM files take an excessively long time to recalibrate and
    the extra inputs don't help much beyond a certain point. See the 'Downsampling analysis'
    plots in the GATK documentation:

    http://gatkforums.broadinstitute.org/discussion/44/base-quality-score-recalibrator#latest

    This identifies large files and calculates the fraction to downsample to.
    """
    target_counts = 1e8 # 100 million reads per read group, 20x the plotted max
    total = sum(x.aligned for x in runner.run_fn("picard_idxstats", in_bam))
    with closing(pysam.Samfile(in_bam, "rb")) as work_bam:
        n_rgs = max(1, len(work_bam.header["RG"]))
    rg_target = n_rgs * target_counts
    if total > rg_target:
        return float(rg_target) / float(total)

def _gatk_base_recalibrator(broad_runner, dup_align_bam, ref_file, platform,
        dbsnp_file, intervals):
    """Step 1 of GATK recalibration process, producing table of covariates.
    """
    out_file = "%s.grp" % os.path.splitext(dup_align_bam)[0]
    plot_file = "%s-plots.pdf" % os.path.splitext(dup_align_bam)[0]
    if not file_exists(out_file):
        if has_aligned_reads(dup_align_bam):
            with curdir_tmpdir() as tmp_dir:
                with file_transaction(out_file) as tx_out_file:
                    params = ["-T", "BaseRecalibrator",
                              "-o", tx_out_file,
                              "--plot_pdf_file", plot_file,
                              "-I", dup_align_bam,
                              "-R", ref_file,
                              ]
                    downsample_pct = _get_downsample_pct(broad_runner, dup_align_bam)
                    if downsample_pct:
                        params += ["--downsample_to_fraction", str(downsample_pct),
                                   "--downsampling_type", "ALL_READS"]
                    # GATK-lite does not have support for
                    # insertion/deletion quality modeling
                    if not broad_runner.has_gatk_full():
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

# ## Create recalibrated BAM

def parallel_write_recal_bam(xs, parallel_fn):
    """Rewrite a recalibrated BAM file in parallel, working off each chromosome.
    """
    to_process = []
    finished = []
    for x in xs:
        if x[0]["config"]["algorithm"].get("recalibrate", True):
            to_process.append(x)
        else:
            finished.append(x)
    if len(to_process) > 0:
        file_key = "work_bam"
        split_fn = process_bam_by_chromosome("-gatkrecal.bam", file_key,
                                           default_targets=["nochr"])
        processed = parallel_split_combine(to_process, split_fn, parallel_fn,
                                           "write_recal_bam", "combine_bam",
                                           file_key, ["config"])
        finished.extend(processed)
        # Save diskspace from original to recalibrated
        #save_diskspace(data["work_bam"], "Recalibrated to %s" % recal_bam,
        #               data["config"])
    return finished

def write_recal_bam(data, region=None, out_file=None):
    """Step 2 of GATK recalibration -- use covariates to re-write output file.
    """
    config = data["config"]
    if out_file is None:
        out_file = "%s-gatkrecal.bam" % os.path.splitext(data["work_bam"])[0]
    logger.info("Writing recalibrated BAM for %s to %s" % (data["name"], out_file))
    if region == "nochr":
        out_bam = write_nochr_reads(data["work_bam"], out_file)
    else:
        out_bam = _run_recal_bam(data["work_bam"], data["prep_recal"],
                                 region, data["sam_ref"], out_file, config)
    data["work_bam"] = out_bam
    return [data]

def _run_recal_bam(dup_align_bam, recal_file, region, ref_file, out_file, config):
    """Run BAM recalibration with the given input
    """
    if not file_exists(out_file):
        if _recal_available(recal_file):
            broad_runner = broad.runner_from_config(config)
            intervals = config["algorithm"].get("variant_regions", None)
            with curdir_tmpdir() as tmp_dir:
                with file_transaction(out_file) as tx_out_file:
                    params = ["-T", "PrintReads",
                              "-BQSR", recal_file,
                              "-R", ref_file,
                              "-I", dup_align_bam,
                              "--out", tx_out_file,
                              ]
                    if region:
                        params += ["-L", region]
                    if intervals:
                        params += ["-L", intervals]
                    if params and intervals:
                        params += ["--interval_set_rule", "INTERSECTION"]
                    broad_runner.run_gatk(params, tmp_dir)
        elif region:
            subset_bam_by_region(dup_align_bam, region, out_file)
        else:
            shutil.copy(dup_align_bam, out_file)
    return out_file

def _recal_available(recal_file):
    """Determine if it's possible to do a recalibration; do we have data?
    """
    if os.path.exists(recal_file):
        with open(recal_file) as in_handle:
            while 1:
                line = in_handle.next()
                if not line.startswith("#"):
                    break
            test_line = in_handle.next()
            if test_line and not test_line.startswith("EOF"):
                return True
    return False

########NEW FILE########
__FILENAME__ = samtools
"""Variant calling using samtools mpileup and bcftools.

http://samtools.sourceforge.net/mpileup.shtml
"""
import os

import sh

from bcbio import broad
from bcbio.utils import file_exists
from bcbio.distributed.transaction import file_transaction
from bcbio.log import logger
from bcbio.pipeline.shared import subset_variant_regions
from bcbio.variation.genotype import write_empty_vcf
from bcbio.variation.realign import has_aligned_reads

def shared_variantcall(call_fn, name, align_bams, ref_file, config,
                       dbsnp=None, region=None, out_file=None):
    """Provide base functionality for prepping and indexing for variant calling.
    """
    broad_runner = broad.runner_from_config(config)
    for x in align_bams:
        broad_runner.run_fn("picard_index", x)
    if out_file is None:
        out_file = "%s-variants.vcf" % os.path.splitext(align_bams[0])[0]
    if not file_exists(out_file):
        logger.info("Genotyping with {name}: {region} {fname}".format(name=name,
            region=region, fname=os.path.basename(align_bams[0])))
        variant_regions = config["algorithm"].get("variant_regions", None)
        target_regions = subset_variant_regions(variant_regions, region, out_file)
        if ((variant_regions is not None and not os.path.isfile(target_regions))
              or not all(has_aligned_reads(x, region) for x in align_bams)):
            write_empty_vcf(out_file)
        else:
            with file_transaction(out_file) as tx_out_file:
                call_fn(align_bams, ref_file, config, target_regions,
                        tx_out_file)
    return out_file


def run_samtools(align_bams, ref_file, config, dbsnp=None, region=None,
                 out_file=None):
    """Detect SNPs and indels with samtools mpileup and bcftools.
    """
    return shared_variantcall(_call_variants_samtools, "samtools", align_bams, ref_file,
                              config, dbsnp, region, out_file)

def prep_mpileup(align_bams, ref_file, max_read_depth, target_regions=None, want_bcf=True):
    mpileup = sh.samtools.mpileup.bake(*align_bams,
                                       f=ref_file, d=max_read_depth, L=max_read_depth,
                                       m=3, F=0.0002)
    if want_bcf:
        mpileup = mpileup.bake(D=True, S=True, u=True)
    if target_regions:
        mpileup = mpileup.bake(l=target_regions)
    return mpileup

def _call_variants_samtools(align_bams, ref_file, config, target_regions, out_file):
    """Call variants with samtools in target_regions.
    """
    max_read_depth = 1000
    with open(out_file, "w") as out_handle:
        mpileup = prep_mpileup(align_bams, ref_file, max_read_depth, target_regions)
        bcftools = sh.bcftools.view.bake("-", v=True, c=True, g=True)
        varfilter = sh.Command("vcfutils.pl").varFilter.bake(D=max_read_depth, _out=out_handle)
        varfilter(bcftools(mpileup()))

########NEW FILE########
__FILENAME__ = split
"""Utilities to manipulate VCF files.
"""
import os

from bcbio.utils import file_exists, replace_suffix, append_stem
from bcbio.distributed.transaction import file_transaction

import sh

def split_vcf(in_file, config, out_dir=None):
    """
    split a VCF file into separate files by chromosome
    requires tabix to be installed

    """
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(in_file), "split")

    fasta_file = config["ref"]["fasta"]
    fasta_index = fasta_file + ".fai"
    samtools_path = config["program"].get("samtools", "samtools")
    tabix_path = config["program"].get("tabix", "tabix")

    if not file_exists(fasta_index):
        samtools = sh.Command(samtools_path)
        samtools.faidx(fasta_file)

    # if in_file is not compressed, compress it
    (_, ext) = os.path.splitext(in_file)
    if ext is not ".gz":
        gzip_file = in_file + ".gz"
        if not file_exists(gzip_file):
            sh.bgzip("-c", in_file, _out=gzip_file)
        in_file = gzip_file

    # create tabix index
    tabix_index(in_file)

    # find the chromosome names from the fasta index file
    chroms = str(sh.cut("-f1", fasta_index)).split()

    # make outfile from chromosome name
    def chr_out(chrom):
        out_file = replace_suffix(append_stem(in_file, chrom), ".vcf")
        return os.path.join(out_dir, os.path.basename(out_file))

    # run tabix to break up the vcf file
    def run_tabix(chrom):
        tabix = sh.Command(tabix_path)
        out_file = chr_out(chrom)
        if file_exists(out_file):
            return out_file
        with file_transaction(out_file) as tmp_out_file:
            tabix("-h", in_file, chrom, _out=tmp_out_file)
        return out_file

    out_files = map(run_tabix, chroms)
    return out_files


def tabix_index(in_file, preset="vcf", config=None):
    """
    index a file using tabix

    """
    if config:
        tabix_path = config["program"].get("tabix", "tabix")
    else:
        tabix_path = sh.which("tabix")
    tabix = sh.Command(tabix_path)
    out_file = in_file + ".tbi"
    if file_exists(out_file):
        return out_file
    tabix("-p", preset, in_file)

    return out_file

########NEW FILE########
__FILENAME__ = varscan
"""Provide variant calling with VarScan from TGI at Wash U.

http://varscan.sourceforge.net/
"""
import os
import shutil
import contextlib

from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils
from bcbio.variation import samtools

import sh
import pysam

def run_varscan(align_bams, ref_file, config,
                dbsnp=None, region=None, out_file=None):
    call_file = samtools.shared_variantcall(_varscan_work, "varscan", align_bams,
                                            ref_file, config, dbsnp, region, out_file)
    _fix_varscan_vcf(call_file, align_bams)
    return call_file

def _fix_varscan_vcf(orig_file, in_bams):
    """Fixes issues with the standard VarScan VCF output.

    - Remap sample names back to those defined in the input BAM file.
    - Convert indels into correct VCF representation.
    """
    tmp_file = utils.append_stem(orig_file, "origsample", "-")
    if not utils.file_exists(tmp_file):
        shutil.move(orig_file, tmp_file)
        with file_transaction(orig_file) as tx_out_file:
            with open(tmp_file) as in_handle:
                with open(orig_file, "w") as out_handle:
                    for line in in_handle:
                        parts = line.split("\t")
                        if line.startswith("#CHROM"):
                            line = _fix_sample_line(line, in_bams)
                        elif not line.startswith("#") and parts[4].startswith(("+", "-")):
                            line = _fix_indel_line(parts)
                        out_handle.write(line)

def _fix_indel_line(parts):
    """Convert VarScan indel representations into standard VCF.
    """
    ref = parts[3]
    alt = parts[4]
    mod_alt = alt[0]
    seq_alt = alt[1:]
    if mod_alt == "+":
        new_ref = ref
        new_alt = ref + seq_alt
    elif mod_alt == "-":
        new_ref = ref + seq_alt
        new_alt = ref
    parts[3] = new_ref
    parts[4] = new_alt
    return "\t".join(parts)

def _fix_sample_line(line, in_bams):
    """Pull sample names from input BAMs and replace VCF file header.
    """
    samples = []
    for in_bam in in_bams:
        with contextlib.closing(pysam.Samfile(in_bam, "rb")) as work_bam:
            for rg in work_bam.header.get("RG", []):
                samples.append(rg["SM"])
    parts = line.split("\t")
    standard = parts[:9]
    old_samples = parts[9:]
    if len(old_samples) == 0:
        return line
    else:
        assert len(old_samples) == len(samples), (old_samples, samples)
        return "\t".join(standard + samples) + "\n"

def _varscan_work(align_bams, ref_file, config, target_regions, out_file):
    """Perform SNP and indel genotyping with VarScan.
    """
    max_read_depth = 1000
    varscan_jar = config_utils.get_jar("VarScan",
                                       config_utils.get_program("varscan", config, "dir"))
    with open(out_file, "w") as out_handle:
        mpileup = samtools.prep_mpileup(align_bams, ref_file, max_read_depth, target_regions,
                                        want_bcf=False)
        varscan = sh.Command("java").bake("-jar", varscan_jar, "mpileup2cns",
                                          "--min-coverage", "5",
                                          "--p-value", "0.98",
                                          "--output-vcf", "--variants", _out=out_handle)
        varscan(mpileup())

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
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'bcbio-nextgen'
copyright = u'2013, Brad Chapman'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5'

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
#html_sidebars = {}

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
__FILENAME__ = barcode_sort_trim
#!/usr/bin/env python
"""Identify fastq reads with barcodes, trimming and sorting for downstream work.

Given a fastq file or pair of fastq files containing barcodes, this identifies
the barcode in each read and writes it into a unique file. Mismatches are
allowed and barcode position within the reads can be specified.

Usage:
    barcode_sort_trim.py <barcode file> <out format> <in file> [<pair file>]
        --mismatch=n (number of allowed mismatches, default 1)
        --bc_offset=n (an offset into the read where the barcode starts (5' barcode)
                       or ends (3' barcode))
        --read=n Integer read number containing the barcode (default to 1)
        --five (barcode is on the 5' end of the sequence, default to 3')
        --noindel (disallow insertion/deletions on barcode matches)
        --quiet (do not print out summary information on tags)
        --tag_title (append matched barcode to sequence header)

<barcode file> is a text file of:
    <name> <sequence>
for all barcodes present in the fastq multiplex.

<out format> specifies how the output files should be written:
    1_100721_FC626DUAAX_--b--_--r--_fastq.txt
  It should contain two values for substitution:
    --b-- Location of the barcode identifier
    --r-- Location of the read number (1 or 2)
  This can be used to specify any output location:
    /your/output/dir/out_--b--_--r--.txt

Requires:
    Python -- versions 2.6 or 2.7
    Biopython -- http://biopython.org
"""
from __future__ import with_statement
import sys
import os
import itertools
import unittest
import collections
import csv
from optparse import OptionParser

from Bio import pairwise2
from Bio.SeqIO.QualityIO import FastqGeneralIterator

def main(barcode_file, out_format, in1, in2, in3, mismatch, bc_offset,
         bc_read_i, three_end, allow_indels,
         metrics_file, verbose, tag_title):
    barcodes = read_barcodes(barcode_file)
    stats = collections.defaultdict(int)
    out_writer = output_to_fastq(out_format)
    for (name1, seq1, qual1), (name2, seq2, qual2), (name3, seq3, qual3) in itertools.izip(
            read_fastq(in1), read_fastq(in2), read_fastq(in3)):
        end_gen = end_generator(seq1, seq2, seq3, bc_read_i, three_end, bc_offset)
        bc_name, bc_seq, match_seq = best_match(end_gen, barcodes, mismatch,
                                                allow_indels)
        seq1, qual1, seq2, qual2, seq3, qual3 = remove_barcode(
                seq1, qual1, seq2, qual2, seq3, qual3,
                match_seq, bc_read_i, three_end, bc_offset)
        if tag_title:
            name1 += " %s" % match_seq
            name2 += " %s" % match_seq
            name3 += " %s" % match_seq
        out_writer(bc_name, name1, seq1, qual1, name2, seq2, qual2,
                   name3, seq3, qual3)
        stats[bc_name] += 1

    sort_bcs = []
    for bc in stats.keys():
        try:
            sort_bc = float(bc)
        except ValueError:
            sort_bc = str(bc)
        sort_bcs.append((sort_bc, bc))
    sort_bcs.sort()
    sort_bcs = [s[1] for s in sort_bcs]
    if verbose:
        print "% -10s %s" % ("barcode", "count")
        for bc in sort_bcs:
            print "% -10s %s" % (bc, stats[bc])
        print "% -10s %s" % ("total", sum(stats.values()))
    if metrics_file:
        with open(metrics_file, "w") as out_handle:
            writer = csv.writer(out_handle, dialect="excel-tab")
            for bc in sort_bcs:
                writer.writerow([bc, stats[bc]])

def best_match(end_gen, barcodes, mismatch, allow_indels=True):
    """Identify barcode best matching to the test sequence, with mismatch.

    Returns the barcode id, barcode sequence and match sequence.
    unmatched is returned for items which can't be matched to a barcode within
    the provided parameters.
    """
    if len(barcodes) == 1 and barcodes.values() == ["trim"]:
        size = len(barcodes.keys()[0])
        test_seq = end_gen(size)
        return barcodes.values()[0], test_seq, test_seq

    # easiest, fastest case -- exact match
    sizes = list(set(len(b) for b in barcodes.keys()))
    for s in sizes:
        test_seq = end_gen(s)
        try:
            bc_id = barcodes[test_seq]
            return bc_id, test_seq, test_seq
        except KeyError:
            pass

    # check for best approximate match within mismatch values
    match_info = []
    if mismatch > 0 or _barcode_has_ambiguous(barcodes):
        for bc_seq, bc_id in barcodes.iteritems():
            test_seq = end_gen(len(bc_seq))
            if _barcode_very_ambiguous(barcodes):
                gapopen_penalty = -18.0
            else:
                gapopen_penalty = -9.0
            aligns = pairwise2.align.globalms(bc_seq, test_seq,
                    5.0, -4.0, gapopen_penalty, -0.5, one_alignment_only=True)
            (abc_seq, atest_seq) = aligns[0][:2] if len(aligns) == 1 else ("", "")
            matches = sum(1 for i, base in enumerate(abc_seq)
                          if (base == atest_seq[i] or base == "N"))
            gaps = abc_seq.count("-")
            cur_mismatch = len(test_seq) - matches + gaps
            if cur_mismatch <= mismatch and (allow_indels or gaps == 0):
                match_info.append((cur_mismatch, bc_id, abc_seq, atest_seq))
    if len(match_info) > 0:
        match_info.sort()
        name, bc_seq, test_seq = match_info[0][1:]
        return name, bc_seq.replace("-", ""), test_seq.replace("-", "")
    else:
        return "unmatched", "", ""

def _barcode_very_ambiguous(barcodes):
    max_size = max(len(x) for x in barcodes.keys())
    max_ns = max(x.count("N") for x in barcodes.keys())
    return float(max_ns) / float(max_size) > 0.5

def _barcode_has_ambiguous(barcodes):
    for seq in barcodes.keys():
        if "N" in seq:
            return True
    return False

def end_generator(seq1, seq2=None, seq3=None, bc_read_i=1, three_end=True, bc_offset=0):
    """Function which pulls a barcode of a provided size from paired seqs.

    This respects the provided details about location of the barcode, returning
    items of the specified size to check against the read.
    """
    seq_choice = {1: seq1, 2: seq2, 3: seq3}
    seq = seq_choice[bc_read_i]
    assert seq is not None

    def _get_end(size):
        assert size > 0
        if three_end:
            return seq[-size-bc_offset:len(seq)-bc_offset]
        else:
            return seq[bc_offset:size+bc_offset]
    return _get_end

def _remove_from_end(seq, qual, match_seq, three_end, bc_offset):
    if match_seq:
        if three_end:
            assert seq[-len(match_seq)-bc_offset:len(seq)-bc_offset] == match_seq
            seq = seq[:-len(match_seq)-bc_offset]
            qual = qual[:-len(match_seq)-bc_offset]
        else:
            assert seq[bc_offset:len(match_seq)+bc_offset] == match_seq
            seq = seq[len(match_seq)+bc_offset:]
            qual = qual[len(match_seq)+bc_offset:]
    return seq, qual

def remove_barcode(seq1, qual1, seq2, qual2, seq3, qual3,
                   match_seq, bc_read_i, three_end, bc_offset=0):
    """Trim found barcode from the appropriate sequence end.
    """
    if bc_read_i == 1:
        seq1, qual1 = _remove_from_end(seq1, qual1, match_seq, three_end, bc_offset)
    elif bc_read_i == 2:
        assert seq2 and qual2
        seq2, qual2 = _remove_from_end(seq2, qual2, match_seq, three_end, bc_offset)
    else:
        assert bc_read_i == 3
        assert seq3 and qual3
        seq3, qual3 = _remove_from_end(seq3, qual3, match_seq, three_end, bc_offset)
    return seq1, qual1, seq2, qual2, seq3, qual3

def _write_to_handles(name, seq, qual, fname, out_handles):
    try:
        out_handle = out_handles[fname]
    except KeyError:
        out_handle = open(fname, "w")
        out_handles[fname] = out_handle
    out_handle.write("@%s\n%s\n+\n%s\n" % (name, seq, qual))

def output_to_fastq(output_base):
    """Write a set of paired end reads as fastq, managing output handles.
    """
    work_dir = os.path.dirname(output_base)
    if not os.path.exists(work_dir) and work_dir:
        try:
            os.makedirs(work_dir)
        except OSError:
            assert os.path.isdir(work_dir)
    out_handles = dict()

    def write_reads(barcode, name1, seq1, qual1, name2, seq2, qual2,
                    name3, seq3, qual3):
        read1name = output_base.replace("--r--", "1").replace("--b--", barcode)
        _write_to_handles(name1, seq1, qual1, read1name, out_handles)
        if seq2:
            read2name = output_base.replace("--r--", "2").replace("--b--", barcode)
            _write_to_handles(name2, seq2, qual2, read2name, out_handles)
        if seq3:
            read3name = output_base.replace("--r--", "3").replace("--b--", barcode)
            _write_to_handles(name3, seq3, qual3, read3name, out_handles)
    return write_reads


def read_barcodes(fname):
    barcodes = {}
    with open(fname) as in_handle:
        for line in (l for l in in_handle if not l.startswith("#")):
            name, seq = line.rstrip("\r\n").split()
            barcodes[seq] = name
    return barcodes


def read_fastq(fname):
    """Provide read info from fastq file, potentially not existing.
    """
    if fname:
        with open(fname) as in_handle:
            for info in FastqGeneralIterator(in_handle):
                yield info
    else:
        for info in itertools.repeat(("", None, None)):
            yield info


# --- Testing code: run with 'nosetests -v -s barcode_sort_trim.py'

class BarcodeTest(unittest.TestCase):
    """Test identification and removal of barcodes with local alignments.
    """
    def setUp(self):
        self.barcodes = {"CGATGT": "2", "CAGATC": "7", "TTAGGCATC": "8"}

    def test_1_end_generator(self):
        """Ensure the proper end is returned for sequences.
        """
        seq1, seq2 = ("AAATTT", "GGGCCC")
        end_gen = end_generator(seq1, seq2, None, 1, True)
        assert end_gen(3) == "TTT"
        end_gen = end_generator(seq1, seq2, None, 1, False)
        assert end_gen(3) == "AAA"
        assert end_gen(4) == "AAAT"
        end_gen = end_generator(seq1, seq2, None, 2, True)
        assert end_gen(3) == "CCC"
        end_gen = end_generator(seq1, seq2, None, 2, False)
        assert end_gen(3) == "GGG"
        # Test end generation with an offset
        end_gen = end_generator(seq1, seq2, None, 1, True,1)
        assert end_gen(3) == "ATT"
        end_gen = end_generator(seq1, seq2, None, 1, False,1)
        assert end_gen(3) == "AAT"
        assert end_gen(4) == "AATT"
        end_gen = end_generator(seq1, seq2, None, 2, True,1)
        assert end_gen(3) == "GCC"
        end_gen = end_generator(seq1, seq2, None, 2, False,1)

    def test_2_identical_match(self):
        """Ensure we can identify identical barcode matches.
        """
        bc_id, seq, _ = best_match(end_generator("CGATGT"), self.barcodes, 0)
        assert bc_id == "2"
        assert seq == "CGATGT"

    def test_3_allowed_mismatch(self):
        """Identify barcodes with the allowed number of mismatches.
        """
        # 1 and 2 mismatches
        (bc_id, _, _) = best_match(end_generator("CGTTGT"), self.barcodes, 1)
        assert bc_id == "2"
        # with indels permitted, accepts 2 mismatches, even if "1" is specified
        (bc_id, _, _) = best_match(end_generator("CGAAGT"), self.barcodes, 1)
        assert bc_id == "2"
        (bc_id, _, _) = best_match(end_generator("GCATGT"), self.barcodes, 2)
        assert bc_id == "2"
        # single gap insertion
        (bc_id, _, _) = best_match(end_generator("GATTGT"), self.barcodes, 1)
        # single gap deletion
        (bc_id, _, _) = best_match(end_generator("GCGAGT"), self.barcodes, 1)
        assert bc_id == "unmatched"
        (bc_id, _, _) = best_match(end_generator("GCGAGT"), self.barcodes, 2)
        assert bc_id == "2"
        (bc_id, _, _) = best_match(end_generator("GCGAGT"), self.barcodes, 2, False)
        assert bc_id == "unmatched"
        # too many errors
        (bc_id, _, _) = best_match(end_generator("GCATGT"), self.barcodes, 1)
        assert bc_id == "unmatched"
        (bc_id, _, _) = best_match(end_generator("GCTTGT"), self.barcodes, 2)
        assert bc_id == "unmatched"

    def test_4_custom_barcodes(self):
        """ Detect longer non-standard custom barcodes, trimming
        """
        # Use the custom long barcode
        custom_barcode = dict((bc_seq, bc_id) for bc_id, bc_seq in self.barcodes.iteritems())
        # Simulate an arbitrary read, attach barcode and remove it from the 3' end
        seq = "GATTACA" * 5 + custom_barcode["8"]
        (bc_id, bc_seq, match_seq) = best_match(end_generator(seq), self.barcodes, 1)
        (removed, _, _, _, _, _) = remove_barcode(seq, "B" * 9, seq, "g" * 9, None, None,
                                                  match_seq, True, True)
        # Was the barcode properly identified and removed with 1 mismatch allowed ?
        assert bc_id == "8"
        assert bc_seq == match_seq
        assert removed == "GATTACA" * 5

    def test_5_illumina_barcodes(self):
        """ Test that Illumina reads with a trailing A are demultiplexed correctly
        """
        # Use the first barcode
        for bc_seq, bc_id in self.barcodes.items():
            if bc_id == "2":
                break
            
        # Simulate an arbitrary read, attach barcode and add a trailing A
        seq = "GATTACA" * 5 + bc_seq + "A"
        (bc_id, bc_seq, match_seq) = best_match(end_generator(seq,None,None,1,True,1), self.barcodes, 1)
        (removed, _, _, _, _, _) = remove_barcode(seq, "B" * 9, seq, "g" * 9, None, None,
                                                  match_seq, True, True, 1)
        # Was the barcode properly identified and removed with 1 mismatch allowed ?
        assert bc_id == "2"
        assert bc_seq == match_seq
        assert removed == "GATTACA" * 5

    def test_6_ambiguous_barcodes(self):
        """Allow mismatch N characters in specified barcodes.
        """
        bcs = {"CGATGN": "2", "CAGATC": "7"}
        (bc_id, _, _) = best_match(end_generator("CGATGT"), bcs, 0, False)
        assert bc_id == "2", bc_id
        (bc_id, _, _) = best_match(end_generator("CGATGN"), bcs, 0, False)
        assert bc_id == "2", bc_id
        (bc_id, _, _) = best_match(end_generator("CGATNT"), bcs, 0, False)
        assert bc_id == "unmatched", bc_id
        (bc_id, _, _) = best_match(end_generator("CGATNT"), bcs, 1, False)
        assert bc_id == "2", bc_id

    def test_7_very_ambiguous_barcodes(self):
        """Matching with highly ambiguous barcodes used for sorting."""
        bcs = {"ANNNNNN": "A", "CNNNNNN": "C", "GNNNNNN": "G", "TNNNNNN": "T"}
        (bc_id, _, _) = best_match(end_generator("CGGGAGA", bc_offset=0), bcs, 2, True)
        assert bc_id == "C", bc_id
        (bc_id, _, _) = best_match(end_generator("GCGGGAG", bc_offset=0), bcs, 0, False)
        assert bc_id == "G", bc_id

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--second", dest="deprecated_first_read",
                      action="store_false", default=True)
    parser.add_option("-r", "--read", dest="bc_read_i", action="store",
                      default=1)
    parser.add_option("-f", "--five", dest="three_end",
                      action="store_false", default=True)
    parser.add_option("-i", "--noindel", dest="indels",
                      action="store_false", default=True)
    parser.add_option("-q", "--quiet", dest="verbose",
                      action="store_false", default=True)
    parser.add_option("-m", "--mismatch", dest="mismatch", default=1)
    parser.add_option("-b", "--bc_offset", dest="bc_offset", default=0)
    parser.add_option("-o", "--metrics", dest="metrics_file", default=None)
    parser.add_option("-t", "--tag_title", dest="tag_title",
                      action="store_true", default=False)
    options, args = parser.parse_args()
    in2, in3 = (None, None)
    if len(args) == 3:
        barcode_file, out_format, in1 = args
    elif len(args) == 4:
        barcode_file, out_format, in1, in2 = args
    elif len(args) == 5:
        barcode_file, out_format, in1, in2, in3 = args
    else:
        print __doc__
        sys.exit()
    # handle deprecated less general options
    if options.deprecated_first_read is False:
        options.bc_read_i = 2
    main(barcode_file, out_format, in1, in2, in3, int(options.mismatch), int(options.bc_offset),
         int(options.bc_read_i), options.three_end, options.indels,
         options.metrics_file, options.verbose, options.tag_title)

########NEW FILE########
__FILENAME__ = bcbio_nextgen
#!/usr/bin/env python
"""Run an automated analysis pipeline on nextgen sequencing information.

Handles runs in local or distributed mode based on the command line or
configured parameters.

The <config file> is a global YAML configuration file specifying details
about the system. An example configuration file is in 'config/post_process.yaml'.

<fc_dir> is an optional parameter specifying a directory of Illumina output
or fastq files to process. If configured to connect to a Galaxy LIMS system,
this can retrieve run information directly from Galaxy for processing.

<YAML run information> is on optional file specifies details about the
flowcell lanes, instead of retrieving it from Galaxy. An example
configuration file is located in 'config/run_info.yaml' This allows running
on files in arbitrary locations with no connection to Galaxy required.

Usage:
  bcbio_nextgen.py <config_file> [<fc_dir>] [<run_info_yaml>]
     -t type of parallelization to use:
          - local: Non-distributed, possibly multiple if n > 1 (default)
          - ipython: IPython distributed processing
          - messaging: RabbitMQ distributed messaging queue
     -n total number of processes to use
     -s scheduler for ipython parallelization (lsf, sge)
     -q queue to submit jobs for ipython parallelization
"""
import os
import sys
import subprocess

from bcbio.pipeline.run_info import get_run_info
from bcbio.distributed import manage as messaging
from bcbio.pipeline.config_utils import load_config
from bcbio.pipeline.main import run_main, parse_cl_args

def main(config_file, fc_dir=None, run_info_yaml=None, numcores=None,
         paralleltype=None, queue=None, scheduler=None, upgrade=None):
    work_dir = os.getcwd()
    config = load_config(config_file)
    if config.get("log_dir", None) is None:
        config["log_dir"] = os.path.join(work_dir, "log")
    paralleltype, numcores = _get_cores_and_type(config, fc_dir, run_info_yaml,
                                                 numcores, paralleltype)
    parallel = {"type": paralleltype, "cores": numcores,
                "scheduler": scheduler, "queue": queue,
                "module": "bcbio.distributed"}
    if parallel["type"] in ["local", "messaging-main"]:
        if numcores is None:
            config["algorithm"]["num_cores"] = numcores
        run_main(config, config_file, work_dir, parallel,
                 fc_dir, run_info_yaml)
    elif parallel["type"] == "messaging":
        parallel["task_module"] = "bcbio.distributed.tasks"
        args = [config_file, fc_dir]
        if run_info_yaml:
            args.append(run_info_yaml)
        messaging.run_and_monitor(config, config_file, args, parallel)
    elif parallel["type"] == "ipython":
        assert parallel["queue"] is not None, "Ipython parallel requires a specified queue (-q)"
        run_main(config, config_file, work_dir, parallel,
                 fc_dir, run_info_yaml)
    else:
        raise ValueError("Unexpected type of parallel run: %s" % parallel["type"])

def _get_cores_and_type(config, fc_dir, run_info_yaml,
                        numcores=None, paralleltype=None):
    """Return core and parallelization approach from combo of config and commandline.

    Prefers passed commandline parameters over pre-configured, defaulting
    to a local run on a single core.

    The preferred approach is to pass in values explicitly on the commandline
    and this helps maintain back compatibility.
    """
    config_cores = config["algorithm"].get("num_cores", None)
    if config_cores:
        try:
            config_cores = int(config_cores)
            if numcores is None:
                numcores = config_cores
        except ValueError:
            if paralleltype is None:
                paralleltype = config_cores
    if paralleltype is None:
        paralleltype = "local"

    if numcores is None:
        if config["distributed"].get("num_workers", "") == "all":
            cp = config["distributed"]["cluster_platform"]
            cluster = __import__("bcbio.distributed.{0}".format(cp), fromlist=[cp])
            numcores = cluster.available_nodes(config["distributed"]["platform_args"]) - 1
        if numcores is None:
            if paralleltype == "local":
                numcores = 1
            else:
                numcores = _needed_workers(get_run_info(fc_dir, config, run_info_yaml)[-1])
    return paralleltype, int(numcores)

def _needed_workers(run_info):
    """Determine workers needed to run multiplex flowcells in parallel.
    """
    names = []
    for xs in run_info["details"]:
        for x in xs:
            names.append(x.get("name", (x["lane"], x["barcode_id"])))
    return len(set(names))

def _upgrade_bcbio(method):
    """Perform upgrade of bcbio to latest release, or from GitHub development version.
    """
    url = "https://raw.github.com/chapmanb/bcbb/master/nextgen/requirements.txt"
    pip_bin = os.path.join(os.path.dirname(sys.executable), "pip")
    if method in ["stable", "system"]:
        sudo_cmd = [] if method == "stable" else ["sudo"]
        subprocess.check_call(sudo_cmd + [pip_bin, "install", "--upgrade", "distribute"])
        subprocess.check_call(sudo_cmd + [pip_bin, "install", "-r", url])
    else:
        raise NotImplementedError("Development upgrade")

if __name__ == "__main__":
    config_file, kwargs = parse_cl_args(sys.argv[1:])
    if kwargs["upgrade"] and config_file is None:
        _upgrade_bcbio(kwargs["upgrade"])
    else:
        main(config_file, **kwargs)

########NEW FILE########
__FILENAME__ = bcbio_nextgen_install
#!/usr/bin/env python
"""Automatically install required tools and data to run bcbio-nextgen pipelines.

This automates the steps required for installation and setup to make it
easier to get started with bcbio-nextgen. The defaults provide data files
for human variant calling.

Requires: PyYAML, fabric
"""
import argparse
import contextlib
import datetime
import os
import urllib2
import shutil
import subprocess
import sys

import yaml

bcbio_remotes = {"system_config":
                 "https://raw.github.com/chapmanb/bcbb/master/nextgen/config/bcbio_system.yaml",
                 "requirements":
                 "https://raw.github.com/chapmanb/bcbb/master/nextgen/requirements.txt"}

def main(args):
    work_dir = os.path.join(os.getcwd(), "tmpbcbio-install")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    os.chdir(work_dir)
    cbl = get_cloudbiolinux()
    fabricrc = write_fabricrc(cbl["fabricrc"], args.tooldir, args.datadir,
                              args.distribution, args.sudo)
    biodata = write_biodata(cbl["biodata"], args.genomes, args.aligners)
    if args.install_tools:
        print "Installing tools..."
        install_tools(cbl["tool_fabfile"], fabricrc)
    print "Installing data..."
    install_data(cbl["data_fabfile"], fabricrc, biodata)
    print "Installing bcbio-nextgen..."
    install_bcbio_nextgen(bcbio_remotes["requirements"], args.datadir, args.tooldir,
                          args.sudo)
    system_config = write_system_config(bcbio_remotes["system_config"], args.datadir,
                                        args.tooldir)
    print "Finished: bcbio-nextgen, tools and data installed"
    print " Ready to use system configuration at:\n  %s" % system_config
    print " Tools installed in:\n  %s" % args.tooldir
    print " Genome data installed in:\n  %s" % args.datadir
    shutil.rmtree(work_dir)

def install_bcbio_nextgen(requirements, datadir, tooldir, use_sudo):
    """Install a virtualenv containing bcbio_nextgen depdencies.
    """
    virtualenv_dir = os.path.join(datadir, "bcbio-nextgen-virtualenv")
    if not os.path.exists(virtualenv_dir):
        subprocess.check_call(["virtualenv", "--no-site-packages", "--distribute", virtualenv_dir])
    sudo_cmd = ["sudo"] if use_sudo else []
    subprocess.check_call(sudo_cmd + ["pip", "install", "--upgrade", "distribute"])
    subprocess.check_call([os.path.join(virtualenv_dir, "bin", "pip"), "install",
                           "-r", requirements])
    for script in ["bcbio_nextgen.py", "bam_to_wiggle.py"]:
        final_script = os.path.join(tooldir, "bin", script)
        ve_script = os.path.join(virtualenv_dir, "bin", script)
        if not os.path.exists(final_script):
            cmd = ["ln", "-s", ve_script, final_script]
            subprocess.check_call(sudo_cmd + cmd)

def install_tools(fabfile, fabricrc):
    subprocess.check_call(["fab", "-f", fabfile, "-H", "localhost",
                           "-c", fabricrc,
                           "install_biolinux:flavor=ngs_pipeline"])

def install_data(fabfile, fabricrc, biodata):
    subprocess.check_call(["fab", "-f", fabfile, "-H", "localhost",
                           "-c", fabricrc, "install_data_s3:%s" % biodata])

def write_system_config(base_url, datadir, tooldir):
    java_basedir = os.path.join(tooldir, "share", "java")
    out_file = os.path.join(datadir, "galaxy", os.path.basename(base_url))
    if os.path.exists(out_file):
        bak_file = out_file + ".bak%s" % (datetime.datetime.now().strftime("%Y%M%d_%H%M"))
    to_rewrite = ("gatk", "picard", "snpEff", "bcbio_variation")
    with contextlib.closing(urllib2.urlopen(base_url)) as in_handle:
        with open(out_file, "w") as out_handle:
            in_prog = None
            for line in in_handle:
                if line.strip().startswith(to_rewrite):
                    in_prog = line.split(":")[0].strip()
                elif line.strip().startswith("dir:") and in_prog:
                    line = "%s: %s\n" % (line.split(":")[0],
                                         os.path.join(java_basedir, in_prog.lower()))
                    in_prog = None
                elif line.startswith("galaxy"):
                    line = "# %s" % line
                out_handle.write(line)
    return out_file

def write_biodata(base_file, genomes, aligners):
    out_file = os.path.join(os.getcwd(), os.path.basename(base_file))
    with open(base_file) as in_handle:
        config = yaml.load(in_handle)
    config["install_liftover"] = False
    config["genome_indexes"] = aligners
    config["genomes"] = [g for g in config["genomes"] if g["dbkey"] in genomes]
    with open(out_file, "w") as out_handle:
        yaml.dump(config, out_handle, allow_unicode=False, default_flow_style=False)
    return out_file

def write_fabricrc(base_file, tooldir, datadir, distribution, use_sudo):
    out_file = os.path.join(os.getcwd(), os.path.basename(base_file))
    with open(base_file) as in_handle:
        with open(out_file, "w") as out_handle:
            for line in in_handle:
                if line.startswith("system_install"):
                    line = "system_install = %s\n" % tooldir
                elif line.startswith("local_install"):
                    line = "local_install = %s/install\n" % tooldir
                elif line.startswith("data_files"):
                    line = "data_files = %s\n" % datadir
                elif line.startswith("distribution"):
                    line = "distribution = %s\n" % distribution
                elif line.startswith("use_sudo"):
                    line = "use_sudo = %s\n" % use_sudo
                elif line.startswith("edition"):
                    line = "edition = minimal\n"
                elif line.startswith("#galaxy_home"):
                    line = "galaxy_home = %s\n" % os.path.join(datadir, "galaxy")
                out_handle.write(line)
    return out_file

def get_cloudbiolinux():
    base_dir = os.path.join(os.getcwd(), "cloudbiolinux")
    if not os.path.exists(base_dir):
        subprocess.check_call(["git", "clone",
                               "git://github.com/chapmanb/cloudbiolinux.git"])
    return {"fabricrc": os.path.join(base_dir, "config", "fabricrc.txt"),
            "biodata": os.path.join(base_dir, "config", "biodata.yaml"),
            "tool_fabfile": os.path.join(base_dir, "fabfile.py"),
            "data_fabfile": os.path.join(base_dir, "data_fabfile.py")}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automatic installation for bcbio-nextgen pipelines")
    parser.add_argument("tooldir", help="Directory to install 3rd party software tools")
    parser.add_argument("datadir", help="Directory to install genome data")
    parser.add_argument("--distribution", help="Operating system distribution",
                        default="ubuntu")
    parser.add_argument("--genomes", help="Genomes to download",
                        action="append", default=["hg19", "GRCh37"])
    parser.add_argument("--aligners", help="Aligner indexes to download",
                        action="append", default=["bwa", "bowtie2", "novoalign", "ucsc"])
    parser.add_argument("--nosudo", help="Specify we cannot use sudo for commands",
                        dest="sudo", action="store_false", default=True)
    parser.add_argument("--notools", help="Do not install tool dependencies",
                        dest="install_tools", action="store_false", default=True)
    if len(sys.argv) == 1:
        parser.print_help()
    else:
        main(parser.parse_args())

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
__FILENAME__ = illumina_finished_msg
#!/usr/bin/env python
"""Script to check for finalized illumina runs and report to messaging server.

Run this script with an hourly cron job; it looks for newly finished output
directories for processing.

Usage:
    illumina_finished_msg.py <YAML local config>
                             [<post-processing config file>]

Supplying a post-processing configuration file skips the messaging step and
we moves directly into analysis processing on the current machine. Use
this if there is no RabbitMQ messaging server and your dump machine is directly
connected to the analysis machine. You will also want to set postprocess_dir in
the YAML local config to the directory to write fastq and analysis files.

The Galaxy config needs to have information on the messaging server and queues.

The local config should have the following information:

    dump_directories: directories to check for machine output
    msg_db: flat file of reported output directories
"""
import os
import operator
import socket
import glob
import getpass
import subprocess
from optparse import OptionParser
from xml.etree.ElementTree import ElementTree

import yaml
import logbook

from bcbio.solexa import samplesheet
from bcbio.log import create_log_handler, logger2
from bcbio import utils
from bcbio.distributed import messaging
from bcbio.solexa.flowcell import (get_flowcell_info, get_fastq_dir, get_qseq_dir)
from bcbio.pipeline.config_utils import load_config

def main(local_config, post_config_file=None,
         process_msg=True, store_msg=True, qseq=True, fastq=True):
    config = load_config(local_config)
    log_handler = create_log_handler(config)

    with log_handler.applicationbound():
        search_for_new(config, local_config, post_config_file,
                       process_msg, store_msg, qseq, fastq)

def search_for_new(config, config_file, post_config_file,
                   process_msg, store_msg, qseq, fastq):
    """Search for any new unreported directories.
    """
    reported = _read_reported(config["msg_db"])
    for dname in _get_directories(config):
        if os.path.isdir(dname) and dname not in reported:
            if _is_finished_dumping(dname):
                # Injects run_name on logging calls.
                # Convenient for run_name on "Subject" for email notifications
                with logbook.Processor(lambda record: record.extra.__setitem__('run', os.path.basename(dname))):
                    logger2.info("The instrument has finished dumping on directory %s" % dname)
                    _update_reported(config["msg_db"], dname)
                    _process_samplesheets(dname, config)
                    if qseq:
                        logger2.info("Generating qseq files for %s" % dname)
                        _generate_qseq(get_qseq_dir(dname), config)
                    fastq_dir = None
                    if fastq:
                        logger2.info("Generating fastq files for %s" % dname)
                        fastq_dir = _generate_fastq(dname, config)
                    _post_process_run(dname, config, config_file,
                                      fastq_dir, post_config_file,
                                      process_msg, store_msg)

def _post_process_run(dname, config, config_file, fastq_dir, post_config_file,
                      process_msg, store_msg):
    """With a finished directory, send out message or process directly.
    """
    run_module = "bcbio.distributed.tasks"
    # without a configuration file, send out message for processing
    if post_config_file is None:
        store_files, process_files = _files_to_copy(dname)
        if process_msg:
            finished_message("analyze_and_upload", run_module, dname,
                             process_files, config, config_file)
        if store_msg:
            raise NotImplementedError("Storage server needs update.")
            finished_message("long_term_storage", run_module, dname,
                             store_files, config, config_file)
    # otherwise process locally
    else:
        analyze_locally(dname, post_config_file, fastq_dir)

def analyze_locally(dname, post_config_file, fastq_dir):
    """Run analysis directly on the local machine.
    """
    assert fastq_dir is not None
    post_config = load_config(post_config_file)
    analysis_dir = os.path.join(fastq_dir, os.pardir, "analysis")
    utils.safe_makedir(analysis_dir)
    with utils.chdir(analysis_dir):
        prog = "bcbio_nextgen.py"
        cl = [prog, post_config_file, dname]
        run_yaml = os.path.join(dname, "run_info.yaml")
        if os.path.exists(run_yaml):
            cl.append(run_yaml)
        subprocess.check_call(cl)

def _process_samplesheets(dname, config):
    """Process Illumina samplesheets into YAML files for post-processing.
    """
    ss_file = samplesheet.run_has_samplesheet(dname, config)
    if ss_file:
        out_file = os.path.join(dname, "run_info.yaml")
        logger2.info("CSV Samplesheet %s found, converting to %s" %
                 (ss_file, out_file))
        samplesheet.csv2yaml(ss_file, out_file)

def _generate_fastq(fc_dir, config):
    """Generate fastq files for the current flowcell.
    """
    fc_name, fc_date = get_flowcell_info(fc_dir)
    short_fc_name = "%s_%s" % (fc_date, fc_name)
    fastq_dir = get_fastq_dir(fc_dir)
    basecall_dir = os.path.split(fastq_dir)[0]
    postprocess_dir = config.get("postprocess_dir", "")
    if postprocess_dir:
        fastq_dir = os.path.join(postprocess_dir, os.path.basename(fc_dir),
                                 "fastq")
    if not fastq_dir == fc_dir and not os.path.exists(fastq_dir):
        with utils.chdir(basecall_dir):
            lanes = sorted(list(set([f.split("_")[1] for f in
                glob.glob("*qseq.txt")])))
            cl = ["solexa_qseq_to_fastq.py", short_fc_name,
                  ",".join(lanes)]
            if postprocess_dir:
                cl += ["-o", fastq_dir]
            logger2.debug("Converting qseq to fastq on all lanes.")
            subprocess.check_call(cl)
    return fastq_dir

def _generate_qseq(bc_dir, config):
    """Generate qseq files from illumina bcl files if not present.

    More recent Illumina updates do not produce qseq files. Illumina's
    offline base caller (OLB) generates these starting with bcl,
    intensity and filter files.
    """
    if not os.path.exists(os.path.join(bc_dir, "finished.txt")):
        bcl2qseq_log = os.path.join(config["log_dir"], "setupBclToQseq.log")
        cmd = os.path.join(config["program"]["olb"], "bin", "setupBclToQseq.py")
        cl = [cmd, "-L", bcl2qseq_log, "-o", bc_dir, "--in-place", "--overwrite",
              "--ignore-missing-stats"]
        # in OLB version 1.9, the -i flag changed to intensities instead of input
        version_cl = [cmd, "-v"]
        p = subprocess.Popen(version_cl, stdout=subprocess.PIPE)
        (out, _) = p.communicate()
        olb_version = float(out.strip().split()[-1].rsplit(".", 1)[0])
        if olb_version > 1.8:
            cl += ["-P", ".clocs"]
            cl += ["-b", bc_dir]
        else:
            cl += ["-i", bc_dir, "-p", os.path.split(bc_dir)[0]]
        subprocess.check_call(cl)
        with utils.chdir(bc_dir):
            try:
                processors = config["algorithm"]["num_cores"]
            except KeyError:
                processors = 8
            cl = config["program"].get("olb_make", "make").split() + ["-j", str(processors)]
            subprocess.check_call(cl)

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

def _files_to_copy(directory):
    """Retrieve files that should be remotely copied.
    """
    with utils.chdir(directory):
        image_redo_files = reduce(operator.add,
                                  [glob.glob("*.params"),
                                   glob.glob("Images/L*/C*"),
                                   ["RunInfo.xml", "runParameters.xml"]])
        qseqs = reduce(operator.add,
                     [glob.glob("Data/Intensities/*.xml"),
                      glob.glob("Data/Intensities/BaseCalls/*qseq.txt"),
                      ])
        reports = reduce(operator.add,
                     [glob.glob("*.xml"),
                      glob.glob("Data/Intensities/BaseCalls/*.xml"),
                      glob.glob("Data/Intensities/BaseCalls/*.xsl"),
                      glob.glob("Data/Intensities/BaseCalls/*.htm"),
                      ["Data/Intensities/BaseCalls/Plots", "Data/reports",
                       "Data/Status.htm", "Data/Status_Files", "InterOp"]])
        run_info = reduce(operator.add,
                        [glob.glob("run_info.yaml"),
                         glob.glob("*.csv"),
                        ])
        logs = reduce(operator.add, [["Logs", "Recipe", "Diag", "Data/RTALogs", "Data/Log.txt"]])
        fastq = ["Data/Intensities/BaseCalls/fastq"]
    return (sorted(image_redo_files + logs + reports + run_info + qseqs),
            sorted(reports + fastq + run_info))

def _read_reported(msg_db):
    """Retrieve a list of directories previous reported.
    """
    reported = []
    if os.path.exists(msg_db):
        with open(msg_db) as in_handle:
            for line in in_handle:
                reported.append(line.strip())
    return reported

def _get_directories(config):
    for directory in config["dump_directories"]:
        for dname in sorted(glob.glob(os.path.join(directory, "*[Aa]*[Xx][Xx]"))):
            if os.path.isdir(dname):
                yield dname

def _update_reported(msg_db, new_dname):
    """Add a new directory to the database of reported messages.
    """
    with open(msg_db, "a") as out_handle:
        out_handle.write("%s\n" % new_dname)

def finished_message(fn_name, run_module, directory, files_to_copy,
                     config, config_file):
    """Wait for messages with the give tag, passing on to the supplied handler.
    """
    logger2.debug("Calling remote function: %s" % fn_name)
    user = getpass.getuser()
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    data = dict(
            machine_type='illumina',
            hostname=hostname,
            user=user,
            directory=directory,
            to_copy=files_to_copy
            )
    dirs = {"work": os.getcwd(),
            "config": os.path.dirname(config_file)}
    runner = messaging.runner(run_module, dirs, config, config_file, wait=False)
    runner(fn_name, [[data]])

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-p", "--noprocess", dest="process_msg",
            action="store_false", default=True)
    parser.add_option("-s", "--nostore", dest="store_msg",
            action="store_false", default=True)
    parser.add_option("-f", "--nofastq", dest="fastq",
            action="store_false", default=True)
    parser.add_option("-q", "--noqseq", dest="qseq",
            action="store_false", default=True)

    (options, args) = parser.parse_args()
    kwargs = dict(process_msg=options.process_msg, store_msg=options.store_msg,
                  fastq=options.fastq, qseq=options.qseq)
    main(*args, **kwargs)

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
from bcbio.pipeline.config_utils import load_config

def main(config_file, month, year):
    config = load_config(config_file)
    galaxy_api = GalaxyApiAccess(config["galaxy_url"],
        config["galaxy_api_key"])
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
__FILENAME__ = nextgen_analysis_server
#!/usr/bin/env python
"""Start a nextgen analysis server that handles processing from a distributed task queue.

This reads configuration details and then starts a Celery (http://celeryproject.org>
server that will handle requests that are passed via an external message queue. This
allows distributed processing of analysis sections with less assumptions about the
system architecture.

Usage:
  nextgen_analysis_server.py <post_process.yaml>
   [--queues=list,of,queues: can specify specific queues to listen for jobs
                             on. No argument runs the default queue, which
                             handles processing alignments. 'toplevel' handles
                             managing the full work process.]
   [--tasks=task.module.import: Specify the module of tasks to make available.
                                Defaults to bcbio.distributed.tasks if not specified.]
   [--basedir=<dirname>: Base directory to work in. Defaults to current directory.]
"""
import os
import sys
import subprocess
import optparse

import yaml
from celery import signals

from bcbio import utils
from bcbio.distributed.messaging import create_celeryconfig
from bcbio.pipeline.config_utils import load_config
from bcbio.log import logger, setup_logging

def main(config_file, queues=None, task_module=None, base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()
    if task_module is None:
        task_module = "bcbio.distributed.tasks"
    config = load_config(config_file)
    if config.get("log_dir", None) is None:
        config["log_dir"] = os.path.join(base_dir, "log")
    signals.setup_logging.connect(celery_logger(config))
    setup_logging(config)
    logger.info("Starting distributed worker process: {0}".format(queues if queues else ""))
    with utils.chdir(base_dir):
        with utils.curdir_tmpdir() as work_dir:
            dirs = {"work": work_dir, "config": os.path.dirname(config_file)}
            with create_celeryconfig(task_module, dirs, config,
                                     os.path.abspath(config_file)):
                run_celeryd(work_dir, queues)

def celery_logger(config):
    def _worker(**kwds):
        setup_logging(config)
    return _worker

def run_celeryd(work_dir, queues):
    with utils.chdir(work_dir):
        cl = ["celeryd"]
        if queues:
            cl += ["-Q", queues]
        subprocess.check_call(cl)

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-q", "--queues", dest="queues", action="store",
                      default=None)
    parser.add_option("-t", "--tasks", dest="task_module", action="store",
                      default=None)
    parser.add_option("-d", "--basedir", dest="basedir", action="store",
                      default=None)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        print "Incorrect arguments"
        print __doc__
        sys.exit()
    main(args[0], options.queues, options.task_module, options.basedir)

########NEW FILE########
__FILENAME__ = plink_to_vcf
#!/usr/bin/env python
"""Convert Plink ped/map files into VCF format using plink and Plink/SEQ.

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
    plink_prefix = os.path.splitext(os.path.basename(ped_file))[0]
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
                            "{0}.vcf".format(os.path.splitext(os.path.basename(ped_file))[0]))
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
    elif ref_base != ref and complements[ref] == ref_base:
        varinfo[3] = complements[ref]
        varinfo[4] = complements[var]
    # unspecified alternative base
    elif ref_base != ref and var in ["N", "0"]:
        varinfo[3] = ref_base
        varinfo[4] = ref
        genotypes = [swap[x] for x in genotypes]
    # swapped and on alternate strand
    elif ref_base != ref and complements[var] == ref_base:
        varinfo[3] = complements[var]
        varinfo[4] = complements[ref]
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
    out_file = apply("{0}-fix{1}".format, os.path.splitext(in_file))

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
__FILENAME__ = solexa_qseq_to_fastq
#!/usr/bin/env python
"""Convert output solexa qseq files into fastq format, handling multiplexing.

Works with qseq output from Illumina's on-machine base caller in:
Data/Intensities/BaseCalls/
or from the offline base caller in:
Data/*_Firecrest*/Bustard*

Usage:
    solexa_qseq_to_fastq.py <run name> <list of lane numbers>

The lane numbers should be separated by commas, so to build fastq files for all
lanes, you should pass:

    1,2,3,4,5,6,7,8

Output files will be in the fastq directory as <lane>_<run_name>_fastq.txt

Illumina barcoded samples contain barcodes in a separate qseq lane, which are
identified by being much shorter than the primary read. Barcodes are added to
the 3' end of the first sequence to remain consistent with other homebrew
barcoding methods.

Optional arguments:
    --failed (-f): Write out reads failing the Illumina quality checks instead.
    --outdir (-o): Write out fastq files to different output directory; defaults
                   to a directory named fastq in the current directory.
"""
from __future__ import with_statement
import os
import sys
import glob
from optparse import OptionParser

def main(run_name, lane_nums, do_fail=False, outdir=None):
    if outdir is None:
        outdir = os.path.join(os.getcwd(), "fastq")
    if not os.path.exists(outdir):
        try:
            os.makedirs(outdir)
        except OSError:
            assert os.path.isdir(outdir)
    if do_fail:
        fail_dir = os.path.join(outdir, "failed")
        if not os.path.exists(fail_dir):
            try:
                os.makedirs(fail_dir)
            except OSError:
                assert os.path.isdir(fail_dir)
    else:
        fail_dir = None
    for lane_num in lane_nums:
        lane_prefix = "s_%s" % lane_num
        out_prefix = "%s_%s" % (lane_num, run_name)
        write_lane(lane_prefix, out_prefix, outdir, fail_dir)

def write_lane(lane_prefix, out_prefix, outdir, fail_dir):
    qseq_files = glob.glob("%s_*qseq.txt" % lane_prefix)
    one_files, two_files, bc_files = _split_paired(qseq_files)
    is_paired = len(two_files) > 0
    out_files = (_get_outfiles(out_prefix, outdir, is_paired)
                 if not fail_dir else None)
    fail_files = (_get_outfiles(out_prefix, fail_dir, is_paired)
                  if fail_dir else None)
    for (num, files) in [("1", one_files), ("2", two_files)]:
        for i, fname in enumerate(files):
            bc_file = _get_associated_barcode(num, i, fname, bc_files)
            convert_qseq_to_fastq(fname, num, bc_file, out_files, fail_files)

def _get_associated_barcode(read_num, file_num, fname, bc_files):
    """Get barcodes for the first read if present.
    """
    if read_num == "1" and len(bc_files) > 0:
        bc_file = bc_files[file_num]
        bc_parts = bc_file.split("_")
        read_parts = fname.split("_")
        assert (bc_parts[1] == read_parts[1] and
                bc_parts[3] == read_parts[3]), (bc_parts, read_parts)
        return bc_file
    return None

def convert_qseq_to_fastq(fname, num, bc_file, out_files, fail_files=None):
    """Convert a qseq file into the appropriate fastq output.
    """
    bc_iterator = _qseq_iterator(bc_file, fail_files is None) if bc_file else None
    for basename, seq, qual, passed in _qseq_iterator(fname, fail_files is None):
        # if we have barcodes, add them to the 3' end of the sequence
        if bc_iterator:
            (_, bc_seq, bc_qual, _) = bc_iterator.next()
            seq = "%s%s" % (seq, bc_seq)
            qual = "%s%s" % (qual, bc_qual)
        name = "%s/%s" % (basename, num)
        out = "@%s\n%s\n+\n%s\n" % (name, seq, qual)
        if passed:
            out_files[num].write(out)
        elif fail_files:
            fail_files[num].write(out)

def _qseq_iterator(fname, pass_wanted):
    """Return the name, sequence, quality, and pass info of qseq reads.

    Names look like:

    HWI-EAS264:4:1:1111:3114#0/1
    """
    with open(fname) as qseq_handle:
        for line in qseq_handle:
            parts = line.strip().split("\t")
            passed = int(parts[-1]) == 1
            if passed is pass_wanted:
                name = ":".join([parts[0]] +  parts[2:6]) + "#" + parts[6]
                seq = parts[8].replace(".", "N")
                qual = parts[9]
                assert len(seq) == len(qual)
                yield name, seq, qual, passed

def _get_outfiles(out_prefix, outdir, has_paired_files):
    out_files = {}
    if has_paired_files:
        for num in ("1", "2"):
            out_files[num] = os.path.join(outdir, "%s_%s_fastq.txt" % (
                out_prefix, num))
    else:
        out_files["1"] = os.path.join(outdir, "%s_fastq.txt" % out_prefix)
    for index, fname in out_files.items():
        out_files[index] = open(fname, "w")
    return out_files

def _split_paired(files):
    """Identify first read, second read and barcode sequences in qseqs.

    Barcoded sequences are identified by being much shorter than reads
    in the first lane.
    """
    files.sort()
    one = []
    two = []
    bcs = []
    ref_size = None
    for f in files:
        parts = f.split("_")
        if parts[2] == "1":
            one.append(f)
            if ref_size is None:
                ref_size = _get_qseq_seq_size(f) // 2
        elif parts[2] == "2":
            cur_size = _get_qseq_seq_size(f)
            assert ref_size is not None
            if cur_size < ref_size:
                bcs.append(f)
            else:
                two.append(f)
        elif parts[2] == "3":
            two.append(f)
        else:
            raise ValueError("Unexpected part: %s" % f)
    one.sort()
    two.sort()
    bcs.sort()
    if len(two) > 0: assert len(two) == len(one)
    if len(bcs) > 0: assert len(bcs) == len(one)
    return one, two, bcs

def _get_qseq_seq_size(fname):
    with open(fname) as in_handle:
        parts = in_handle.readline().split("\t")
        return len(parts[8])

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--failed", dest="do_fail", action="store_true",
                      default=False)
    parser.add_option("-o", "--outdir", dest="outdir", action="store",
                      default=None)
    (options, args) = parser.parse_args()
    if len(args) < 2:
        print __doc__
        sys.exit()
    main(args[0], args[1].split(","), options.do_fail, options.outdir)

########NEW FILE########
__FILENAME__ = upload_to_galaxy
#!/usr/bin/env python
"""Upload a set of next-gen sequencing data files to a data library in Galaxy.

Usage:
    upload_to_galaxy.py <config file> <flowcell directory> <analysis output dir>
                        [<YAML run information>]

The optional <YAML run information> file specifies details about the
flowcell lanes, instead of retrieving it from Galaxy. An example
configuration file is located in 'config/run_info.yaml'

The configuration file is in YAML format with the following key/value pairs:

galaxy_url: Base URL of Galaxy for uploading.
galaxy_api_key: Developer's API key.
galaxy_config: Path to Galaxy's universe_wsgi.ini file. This is required so
we know where to organize directories for upload based on library_import_dir.
"""
import sys
import os
import glob
import shutil
import ConfigParser
import time

import yaml

from bcbio.solexa.flowcell import get_fastq_dir
from bcbio.pipeline.run_info import get_run_info
from bcbio.galaxy.api import GalaxyApiAccess
from bcbio import utils
from bcbio.pipeline.config_utils import load_config

def main(config_file, fc_dir, analysis_dir, run_info_yaml=None):
    config = load_config(config_file)
    galaxy_api = (GalaxyApiAccess(config['galaxy_url'], config['galaxy_api_key'])
                  if config.has_key("galaxy_api_key") else None)
    fc_name, fc_date, run_info = get_run_info(fc_dir, config, run_info_yaml)

    base_folder_name = "%s_%s" % (fc_date, fc_name)
    run_details = lims_run_details(run_info, base_folder_name)
    for (library_name, access_role, dbkey, lane, bc_id, name, desc,
            local_name, fname_out) in run_details:
        library_id = (get_galaxy_library(library_name, galaxy_api)
                      if library_name else None)
        upload_files = list(select_upload_files(local_name, bc_id, fc_dir,
                                                analysis_dir, config, fname_out))
        if len(upload_files) > 0:
            print lane, bc_id, name, desc, library_name
            print "Creating storage directory"
            if library_id:
                folder, cur_galaxy_files = get_galaxy_folder(library_id,
                               base_folder_name, name, desc, galaxy_api)
            else:
                cur_galaxy_files = []
            store_dir = move_to_storage(lane, bc_id, base_folder_name, upload_files,
                                        cur_galaxy_files, config, config_file,
                                        fname_out)
            if store_dir and library_id:
                print "Uploading directory of files to Galaxy"
                print galaxy_api.upload_directory(library_id, folder['id'],
                                                  store_dir, dbkey, access_role)
    if galaxy_api and not run_info_yaml:
        add_run_summary_metrics(analysis_dir, galaxy_api)

# LIMS specific code for retrieving information on what to upload from
# the Galaxy NGLIMs.
# Also includes function for selecting files to upload from flow cell and
# analysis directories.
# These should be edited to match a local workflow if adjusting this.

def lims_run_details(run_info, base_folder_name):
    """Retrieve run infomation on a flow cell from Next Gen LIMS.
    """
    for lane_items in run_info["details"]:
        for lane_info in lane_items:
            if not run_info["run_id"] or lane_info.has_key("researcher"):
                if lane_info.get("private_libs", None) is not None:
                    libname, role = _get_galaxy_libname(lane_info["private_libs"],
                                                        lane_info["lab_association"],
                                                        lane_info["researcher"])
                elif lane_info.has_key("galaxy_library"):
                    libname = lane_info["galaxy_library"]
                    role = lane_info["galaxy_role"]
                else:
                    libname, role = (None, None)
                remote_folder = str(lane_info.get("name", lane_info["lane"]))
                description = ": ".join([lane_info[n] for n in ["researcher", "description"]
                                         if lane_info.has_key(n)])
                if lane_info.get("description_filenames", False):
                    fname_out = lane_info["description"]
                else:
                    fname_out = None
                local_name = "%s_%s" % (lane_info["lane"], base_folder_name)
                if lane_info["barcode_id"] is not None:
                    remote_folder += "_%s" % lane_info["barcode_id"]
                    local_name += "_%s" % lane_info["barcode_id"]
                yield (libname, role, lane_info["genome_build"],
                       lane_info["lane"], lane_info["barcode_id"],
                       remote_folder, description, local_name, fname_out)

def _get_galaxy_libname(private_libs, lab_association, researcher):
    """Retrieve most appropriate Galaxy data library.

    Gives preference to private data libraries associated with the user. If not
    found will create a user specific library.
    """
    print private_libs, lab_association
    # simple case -- one private library. Upload there
    if len(private_libs) == 1:
        return private_libs[0]
    # no private libraries -- use the lab association or researcher name
    elif len(private_libs) == 0:
        if not lab_association:
            return researcher, ""
        else:
            return lab_association, ""
    # multiple libraries -- find the one that matches the lab association
    else:
        check_libs = [l.lower() for (l, _) in private_libs]
        try:
            i = check_libs.index(lab_association.lower())
            return private_libs[i]
        # can't find the lab association, give us the first library
        except (IndexError, ValueError):
            return private_libs[0]

def select_upload_files(base, bc_id, fc_dir, analysis_dir, config, fname_out=None):
    """Select fastq, bam alignment and summary files for upload to Galaxy.
    """
    def _name_with_ext(orig_file, ext):
        """Return a normalized filename without internal processing names.

        Use specific base out filename if specific, allowing configuration
        named output files.
        """
        if fname_out is None:
            base = os.path.basename(orig_file).split("-")[0]
        else:
            base = fname_out
        for extra in ["_trim"]:
            if base.endswith(extra):
                base = base[:-len(extra)]
        return "%s%s" % (base, ext)

    base_glob = _dir_glob(base, analysis_dir)
    # Configurable upload of fastq files -- BAM provide same information, compacted
    if config["algorithm"].get("upload_fastq", True):
        # look for fastq files in a barcode directory or the main fastq directory
        bc_base = base.rsplit("_", 1)[0] if bc_id else base
        bc_dir = os.path.join(analysis_dir, "%s_barcode" % bc_base)
        fastq_glob = "%s_*fastq.txt" % base
        found_fastq = False
        for fname in glob.glob(os.path.join(bc_dir, fastq_glob)):
            found_fastq = True
            yield (fname, os.path.basename(fname))
        if not found_fastq:
            fastq_dir = get_fastq_dir(fc_dir)
            for fname in glob.glob(os.path.join(fastq_dir, fastq_glob)):
                yield (fname, os.path.basename(fname))
    for summary_file in base_glob("summary.pdf"):
        yield (summary_file, _name_with_ext(summary_file, "-summary.pdf"))
    for wig_file in base_glob(".bigwig"):
        yield (wig_file, _name_with_ext(wig_file, "-coverage.bigwig"))
    # upload BAM files, preferring recalibrated and realigned files
    found_bam = False
    for orig_ext, new_ext in [("gatkrecal-realign-dup.bam", "-gatkrecal-realign.bam"),
                              ("gatkrecal-realign.bam", "-gatkrecal-realign.bam"),
                              ("gatkrecal.bam", "-gatkrecal.bam"),
                              ("sort-dup.bam", ".bam"),
                              ("sort.bam", ".bam")]:
        if not found_bam:
            for bam_file in base_glob(orig_ext):
                yield (bam_file, _name_with_ext(bam_file, new_ext))
                found_bam = True
    # Genotype files produced by SNP calling
    found = False
    for orig_ext, new_ext in [("variants-combined-annotated.vcf", "-variants.vcf"),
                              ("variants-*-annotated.vcf", "-variants.vcf")]:
        if not found:
            for snp_file in base_glob(orig_ext):
                yield (snp_file, _name_with_ext(bam_file, new_ext))
                found = True
    # Effect information on SNPs
    for snp_file in base_glob("variants-*-effects.tsv"):
        yield (snp_file, _name_with_ext(bam_file, "-variants-effects.tsv"))

def _dir_glob(base, work_dir):
    # Allowed characters that can trail the base. This prevents picking up
    # NAME_10 when globbing for NAME_1
    trailers = "[-_.]"
    def _safe_glob(ext):
        return glob.glob(os.path.join(work_dir, "%s%s*%s" % (base, trailers, ext)))
    return _safe_glob

def add_run_summary_metrics(analysis_dir, galaxy_api):
    """Upload YAML file of run information to Galaxy though the NGLims API.
    """
    run_file = os.path.join(analysis_dir, "run_summary.yaml")
    if os.path.exists(run_file):
        with open(run_file) as in_handle:
            run_summary = yaml.load(in_handle)
        galaxy_api.sqn_run_summary(run_summary)

# General functionality for interacting with Galaxy via the Library API

def get_galaxy_folder(library_id, folder_name, lane, description, galaxy_api):
    """Return or create a folder within the given library.

    Creates or retrieves a top level directory for a run, and then creates
    a lane specific directory within this run.
    """
    items = galaxy_api.library_contents(library_id)
    root = _folders_by_name('/', items)[0]
    run_folders = _safe_get_folders("/%s" % folder_name, items,
                                    library_id, root["id"], folder_name, "",
                                    galaxy_api)
    lane_folders = _safe_get_folders("/%s/%s" % (folder_name, lane), items,
                                     library_id, run_folders[0]['id'],
                                     str(lane), description, galaxy_api)
    cur_files = [f for f in items if f['type'] == 'file'
                 and f['name'].startswith("/%s/%s" % (folder_name, lane))]
    return lane_folders[0], cur_files

def _safe_get_folders(base_name, items, library_id, base_folder_id, name,
                      description, galaxy_api):
    """Retrieve folders for a run or lane, retrying in the case of network errors.
    """
    max_tries = 5
    num_tries = 0
    while 1:
        try:
            folders = _folders_by_name(base_name, items)
            if len(folders) == 0:
                folders = galaxy_api.create_folder(library_id, base_folder_id,
                                                   name, description)
            break
        except ValueError:
            if num_tries > max_tries:
                raise
            time.sleep(2)
            num_tries += 1
    return folders

def _folders_by_name(name, items):
    return [f for f in items if f['type'] == 'folder' and
                                f['name'] == name]

def move_to_storage(lane, bc_id, fc_dir, select_files, cur_galaxy_files,
                    config, config_file, fname_out=None):
    """Create directory for long term storage before linking to Galaxy.
    """
    galaxy_config_file = utils.add_full_path(config["galaxy_config"],
                                             os.path.dirname(config_file))
    galaxy_conf = ConfigParser.SafeConfigParser({'here' : ''})
    galaxy_conf.read(galaxy_config_file)
    try:
        lib_import_dir = galaxy_conf.get("app:main", "library_import_dir")
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        raise ValueError("Galaxy config %s needs library_import_dir to be set."
                         % galaxy_config_file)
    storage_dir = _get_storage_dir(fc_dir, lane, bc_id, os.path.join(lib_import_dir,
                                   "storage"), fname_out)
    existing_files = [os.path.basename(f['name']) for f in cur_galaxy_files]
    need_upload = False
    for orig_file, new_file in select_files:
        if new_file not in existing_files:
            new_file = os.path.join(storage_dir, new_file)
            if not os.path.exists(new_file):
                shutil.copy(orig_file, new_file)
            need_upload = True
    return (storage_dir if need_upload else None)

def _get_storage_dir(cur_folder, lane, bc_id, storage_base, fname_out=None):
    if fname_out:
        base = str(fname_out)
    else:
        base = "%s_%s" % (lane, bc_id) if bc_id else str(lane)
    store_dir = os.path.join(storage_base, cur_folder, base)
    utils.safe_makedir(store_dir)
    return store_dir

def get_galaxy_library(lab_association, galaxy_api):
    ret_info = None
    for lib_info in galaxy_api.get_libraries():
        if lib_info["name"].find(lab_association) >= 0:
            ret_info = lib_info
            break
    # need to add a new library
    if ret_info is None:
        ret_info = galaxy_api.create_library(lab_association)[0]
    return ret_info["id"]

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print "Incorrect arguments"
        print __doc__
        sys.exit()
    main(*sys.argv[1:])

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

from bcbio.solexa.flowcell import (get_flowcell_info, get_fastq_dir)
from bcbio.galaxy.api import GalaxyApiAccess
from bcbio.broad.metrics import PicardMetricsParser
from bcbio import utils
from bcbio.pipeline.config_utils import load_config

def main(config_file, fc_dir):
    work_dir = os.getcwd()
    config = load_config(config_file)
    galaxy_api = GalaxyApiAccess(config['galaxy_url'], config['galaxy_api_key'])
    fc_name, fc_date = get_flowcell_info(fc_dir)
    run_info = galaxy_api.run_details(fc_name)
    fastq_dir = get_fastq_dir(fc_dir)
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

from bcbio.solexa import samplesheet

if __name__ == "__main__":
    samplesheet.csv2yaml(sys.argv[1])

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
__FILENAME__ = test_bed2interval
import yaml
import unittest
from bcbio.broad.picardrun import bed2interval
from bcbio.utils import replace_suffix
import os
from tempfile import NamedTemporaryFile
import filecmp


class TestBed2interval(unittest.TestCase):

    def setUp(self):
        self.config_file = "tests/bed2interval/test_bed2interval.yaml"
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
__FILENAME__ = test_split_vcf
import yaml
import unittest
from bcbio.variation.split import split_vcf
import filecmp
import shutil
import os


class TestVcf(unittest.TestCase):

    def setUp(self):
        self.config_file = "tests/split_vcf/test_split_vcf.yaml"
        with open(self.config_file) as in_handle:
            self.config = yaml.load(in_handle)

    def test_splitvcf(self):
        in_file = self.config["input_split"]
        correct = self.config["correct_split"]
        out_files = split_vcf(in_file, self.config)
        self.assertTrue(all(map(filecmp.cmp, out_files, correct)))

        # cleanup
        data_dir = os.path.dirname(in_file)
        shutil.rmtree(os.path.join(data_dir, "split"))
        os.remove(in_file + ".gz")
        os.remove(in_file + ".gz.tbi")

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

from nose.plugins.attrib import attr

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
        yield
    finally:
        os.chdir(orig_dir)

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
                         DlInfo("genomes_automated_test.tar.gz", "genomes", 8),
                         DlInfo("110907_ERP000591.tar.gz", None, None),
                         DlInfo("100326_FC6107FAAXX.tar.gz", None, 3)]
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

    def _get_post_process_yaml(self):
        std = os.path.join(self.data_dir, "post_process.yaml")
        sample = os.path.join(self.data_dir, "post_process-sample.yaml")
        if os.path.exists(std):
            return std
        else:
            return sample

    @attr(speed=3)
    def test_3_full_pipeline(self):
        """Run full automated analysis pipeline with multiplexing.
        """
        self._install_test_files(self.data_dir)
        with make_workdir():
            cl = ["bcbio_nextgen.py",
                  self._get_post_process_yaml(),
                  os.path.join(self.data_dir, os.pardir, "110106_FC70BUKAAXX"),
                  os.path.join(self.data_dir, "run_info.yaml")]
            subprocess.check_call(cl)

    @attr(speed=3)
    def test_4_empty_fastq(self):
        """Handle analysis of empty fastq inputs from failed runs.
        """
        with make_workdir():
            cl = ["bcbio_nextgen.py",
                  self._get_post_process_yaml(),
                  os.path.join(self.data_dir, os.pardir, "110221_empty_FC12345AAXX"),
                  os.path.join(self.data_dir, "run_info-empty.yaml")]
            subprocess.check_call(cl)

    @attr(speed=2)
    def test_2_rnaseq(self):
        """Run an RNA-seq analysis with TopHat and Cufflinks.
        """
        self._install_test_files(self.data_dir)
        with make_workdir():
            cl = ["bcbio_nextgen.py",
                  self._get_post_process_yaml(),
                  os.path.join(self.data_dir, os.pardir, "110907_ERP000591"),
                  os.path.join(self.data_dir, "run_info-rnaseq.yaml")]
            subprocess.check_call(cl)

    @attr(speed=1)
    def test_1_variantcall(self):
        """Test variant calling with GATK pipeline.
        """
        self._install_test_files(self.data_dir)
        with make_workdir():
            cl = ["bcbio_nextgen.py",
                  self._get_post_process_yaml(),
                  os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-variantcall.yaml")]
            subprocess.check_call(cl)

    @attr(speed=2)
    def test_5_bam(self):
        """Allow BAM files as input to pipeline.
        """
        self._install_test_files(self.data_dir)
        with make_workdir():
            cl = ["bcbio_nextgen.py",
                  self._get_post_process_yaml(),
                  os.path.join(self.data_dir, os.pardir, "100326_FC6107FAAXX"),
                  os.path.join(self.data_dir, "run_info-bam.yaml")]
            subprocess.check_call(cl)



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
        self.root_dir = os.path.join(__file__, "data/fastq/")

    def test_groom(self):
        illumina_dir = os.path.join(self.root_dir, "illumina")
        test_data = locate("*.fastq", illumina_dir)
        sanger_dir = tempfile.mkdtemp()
        out_files = [groom(x, in_qual="fastq-illumina", out_dir=sanger_dir) for
                     x in test_data]
        self.assertTrue(all(map(file_exists, out_files)))

########NEW FILE########
__FILENAME__ = test_pipeline
"""Test individual components of the analysis pipeline.
"""
import os
import unittest

from nose.plugins.attrib import attr

from bcbio.pipeline.run_info import _generate_lane, get_run_info

class RunInfoTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")

    @attr(speed="std")
    def test_lanename(self):
        """Generate lane names from supplied filenames.
        """
        assert _generate_lane(["s_1_sequence.txt"], 2) == "1"
        assert _generate_lane(["aname-sequence.fastq"], 2) == "aname"
        assert _generate_lane(["s_1_1-sequence.txt", "s_1_2-sequence.txt"], 2) == "1"
        assert _generate_lane(["one.txt", "two.txt"], 2) == "3"

    @attr(speed=1)
    def test_run_info_combine(self):
        """Combine multiple lanes in a test run into a single combined lane.
        """
        run_info_yaml = os.path.join(self.data_dir, "run_info-alternatives.yaml")
        _, _, run_info = get_run_info("", {}, run_info_yaml)
        assert len(run_info["details"]) == 2
        assert len(run_info["details"][0]) == 3
        x1, x2, x3 = run_info["details"][0]
        assert x1["description"] == "1: BC1"
        assert x2["description"] == "1: BC2"
        assert x3["genome_build"] == "mm9"
        x1 = run_info["details"][1][0]
        assert x1["barcode_id"] is None

########NEW FILE########
__FILENAME__ = test_SequencingDump
"""Tests associated with detecting sequencing results dumped from a machine.
"""
import os
import unittest

from nose.plugins.attrib import attr
import yaml

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

        @filter_to("sorted")
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
        stem = "stem"
        word = __name__

        @utils.memoize_outfile(stem=stem)
        def f(in_file, word, out_file=None):
            return self._write_word(out_file, word)
        self._run_calls_no_dir(f, temp_file, word)

    def test_memoize_outfile_stem_with_dir(self):
        temp_file = tempfile.NamedTemporaryFile(dir=self.out_dir,
                                                suffix=".sam")
        temp_dir = tempfile.mkdtemp()
        stem = "stem"
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
__FILENAME__ = fix_bibfile
import sys

in_file, out_file = sys.argv[1:]

with open(in_file) as in_handle:
    with open(out_file, "w") as out_handle:
        for line in in_handle:
            if line.strip().startswith("language"):
                line = None
            elif line.strip().startswith("@misc"):
                base, cite = line.split("{")
                cite_parts = [x.strip() for x in cite.split("_") if x.strip()]
                line = base + "{" + cite_parts[0] + ",\n"
            if line:
                out_handle.write(line)

########NEW FILE########
__FILENAME__ = compare_discordants_to_replicates
#!/usr/bin/env python
"""Compare discordant variants between quality binning to replicates.

The goal is to identify if discordant variants are highly trusted or
potential false positives so we get a sense of how much real variation
we might be missing.

Usage:
    compare_discordants_to_replicates.py <config_yaml>
"""
import collections
import glob
import operator
import os
import sys

import yaml

def main(config):
    discordants = _get_all_discordants(config["dir"]["discordant"])
    replicates = _read_replicate_locs(config["dir"]["replicate"])
    filtered = _get_filtered(config["dir"]["orig"], config["orig"])
    all_reasons = []
    for (name1, name2), fname in discordants.iteritems():
        locs = collections.defaultdict(int)
        reasons = collections.defaultdict(int)
        other_discordant_locs = read_coords(discordants[(name2, name1)], only_pos=True)
        with open(fname) as in_handle:
            for line in (x for x in in_handle if not x.startswith("#")):
                coords = coords_from_line(line)
                cur_type = "missing"
                for rep_name, rep_locs in replicates.iteritems():
                    if coords in rep_locs:
                        cur_type = rep_name
                        break
                locs["total"] += 1
                locs[cur_type] += 1
                if cur_type.endswith("concordance"):
                    filter_name = filtered[name2].get(coords)
                    dp = get_info_item(line, "DP")
                    if filter_name is not None:
                        reasons[filter_name[0].replace("GATKStandard", "")] += 1
                    elif tuple(coords[:2]) in other_discordant_locs:
                        reasons["het/hom/indel"] += 1
                    elif dp < 10:
                        reasons["low_depth"] += 1
                    elif dp < 25:
                        reasons["mod_depth"] += 1
                    else:
                        if "allbin" in [name1, name2]:
                            print line.strip()
                        reasons["other"] += 1
        print name1, name2, dict(reasons), dict(locs)
        if "allbin" in [name1, name2]:
            all_reasons.append(dict(reasons))
    combine_reasons(all_reasons)

def combine_reasons(xs):
    final = xs[0]
    for x in xs[1:]:
        for k, v in x.iteritems():
            if not k.startswith("het/hom"):
                try:
                    final[k] += v
                except KeyError:
                    final[k] = v
    items = sorted(final.iteritems(), key=operator.itemgetter(1), reverse=True)
    for k, v in items:
        print k, v

def get_info_item(line, name):
    info_parts = line.split("\t")[7].split(";")
    item_part = [x for x in info_parts if x.startswith("%s=" % name)][0]
    _, item = item_part.split("=")
    return float(item)

def _get_all_discordants(dname):
    out = {}
    for fname in glob.glob(os.path.join(dname, "*discordance.vcf")):
        _, name1, name2, _ = os.path.basename(fname).split("-")
        if "std" in [name1, name2]:
            out[(name1, name2)] = fname
    return out

def _get_filtered(dname, orig_by_name):
    out = {}
    for name, fname in orig_by_name.iteritems():
        filtered = {}
        with open(os.path.join(dname, fname)) as in_handle:
            for line in (x for x in in_handle if not x.startswith("#")):
                if line.split("\t")[6] != "PASS":
                    filtered[coords_from_line(line)] = (line.split("\t")[6],
                                                        get_info_item(line, "MQ"),
                                                        get_info_item(line, "QD"))
        out[name] = filtered
    return out

def _read_replicate_locs(dname):
    out = {}
    for fname in glob.glob(os.path.join(dname, "*.vcf")):
        name = os.path.splitext(os.path.basename(fname))[0]
        out[name] = read_coords(fname)
    return out

def coords_from_line(line, only_pos=False):
    parts = line.split("\t")
    if only_pos:
        return tuple(parts[:2])
    else:
        return tuple(parts[:2] + parts[3:5])

def read_coords(f, only_pos=False):
    coords = []
    with open(f) as in_handle:
        for line in in_handle:
            if not line.startswith("#"):
                coords.append(coords_from_line(line, only_pos))
    return set(coords)

if __name__ == "__main__":
    with open(sys.argv[1]) as in_handle:
        config = yaml.load(in_handle)
    main(config)

########NEW FILE########
__FILENAME__ = ensembl_remote_rest
"""Provide a remote REST-like API interface to Ensembl.

This provides a wrapping around screen-scraping of Ensembl
with the goal of retrieving comparative genomics information.

Usage:
    ensembl_remote_rest.py Organism Gene_id
Example:
    ensembl_remote_rest.py Homo_sapiens ENSG00000173894
"""
from __future__ import with_statement
import sys
import re
import urllib2
import os
import time

from BeautifulSoup import BeautifulSoup
from Bio import SeqIO
import newick
import networkx
    
#gene_ids = [("Homo_sapiens", "ENSG00000173894")]
#gene_ids = [("Homo_sapiens", "ENSG00000168283")]
#gene_ids = [("Homo_sapiens", "ENSG00000183741")]

def main(organism, gene_id):
    write_fasta = False
    cache_dir = os.path.join(os.getcwd(), "cache")
    ensembl_rest = EnsemblComparaRest(cache_dir)
    orthologs = ensembl_rest.orthologs(organism, gene_id)
    compara_tree = ensembl_rest.compara_tree(organism, gene_id)
    compara_tree = '(' + compara_tree[:-1] + ');'
    tree_rec = newick.parse_tree(compara_tree.strip())
    d_vis = DistanceVisitor()
    tree_rec.dfs_traverse(d_vis)
    tree_proteins = [l.identifier for l in tree_rec.leaves]
    orthologs = [(organism, gene_id)] + orthologs
    out_recs = []
    root_id = None
    all_items = []
    for o_organism, o_id in orthologs:
        transcripts = ensembl_rest.transcripts(o_organism, o_id)
        tx, p = [(tx, p) for (tx, p) in transcripts if p in
                tree_proteins][0]
        cur_item = EnsemblComparaTranscript(o_organism, o_id, tx, p)
        if root_id is None:
            root_id = p
        cur_item.distance = networkx.dijkstra_path_length(d_vis.graph,
                "'%s'" % root_id, "'%s'" % p)
        #print o_organism, o_id, p
        cur_item.domains = ensembl_rest.protein_domains(o_organism, o_id,
                tx)
        cur_item.statistics = ensembl_rest.protein_stats(o_organism, o_id,
                tx)
        all_items.append(cur_item)
        if write_fasta:
            out_rec = ensembl_rest.protein_fasta(o_organism, o_id,
                    tx)
            out_rec.id = o_id
            out_rec.description = o_organism
            out_recs.append(out_rec)
    if len(out_recs) > 0:
        with open("%s_%s_orthologs.txt" % (organism, gene_id), "w") as \
                out_handle:
            SeqIO.write(out_recs, out_handle, "fasta")
    analyze_comparative_set(all_items)

def analyze_comparative_set(all_items):
    def distance_cmp(one, two):
        return cmp(one.distance, two.distance)
    all_items.sort(distance_cmp)
    for item in all_items:
        print item.organism, item.distance, item.domains, \
                item.statistics.get('Charge', '').strip()

class EnsemblComparaTranscript:
    """Hold comparative information retrieved from Ensembl on a transcript.
    """
    def __init__(self, organism, g_id, t_id, p_id):
        self.organism = organism
        self.g_id = g_id
        self.t_id = t_id
        self.p_id = p_id
        self.distance = None
        self.domains = []
        self.statistics = {}

class DistanceVisitor(newick.tree.TreeVisitor):
    def __init__(self):
        self.graph = networkx.Graph()
        
    def pre_visit_edge(self, src, b, l, dest):
        self.graph.add_edge(repr(src), repr(dest), l)

class EnsemblComparaRest:
    """Provide a REST-like API interface to Ensembl.
    """
    def __init__(self, cache_dir):
        self._base_url = "http://www.ensembl.org"
        self._cache_dir = cache_dir
        if not(os.path.exists(cache_dir)):
            os.makedirs(cache_dir)

    def protein_stats(self, organism, gene_id, tx_id):
        """Retrieve dictionary of statistics for a gene transcript.
        """
        stats = {}
        with self._get_open_handle("Transcript", "ProteinSummary",
                organism, gene_id, tx_id) as in_handle:
            soup = BeautifulSoup(in_handle)
            stats_possibilities = soup.findAll("dl", "summary")
            for stats_check in stats_possibilities:
                stats_assert = stats_check.find("dt", text="Statistics")
                if stats_assert:
                    stats_line = stats_check.find("p")
                    for stats_part in stats_line:
                        if stats_part.find(":") > 0:
                            key, value = stats_part.split(":")
                            stats[key] = value
        return stats

    def protein_domains(self, organism, gene_id, tx_id):
        """Retrieve characterized domains in a gene transcript.
        """
        domains = []
        with self._get_open_handle("Transcript", "Domains", organism,
                gene_id, tx_id) as in_handle:
            soup = BeautifulSoup(in_handle)
            domain_table = soup.find("table", "ss autocenter")
            if domain_table is not None:
                domain_links = domain_table.findAll("a", href =
                        re.compile("interpro"))
                for domain_link in domain_links:
                    domains.append(domain_link.string)
        domains = list(set(domains))
        return domains

    def protein_fasta(self, organism, gene_id, tx_id):
        """Retrieve the fasta sequence for a given gene and transcript.
        """
        final_url = "%s/%s/Transcript/Export?db=core;g=%s;output=fasta;t=%s;"\
                "st=peptide;_format=Text" % (self._base_url, organism,
                        gene_id, tx_id)
        handle = self._safe_open(final_url)
        rec = SeqIO.read(handle, "fasta")
        handle.close()
        return rec

    def transcripts(self, organism, gene_id):
        """Retrieve a list of (transcript, protein) ids for the given gene_id.
        """
        txs = []
        ps = []
        valid_gene_starts = ["EN", "FB", "AA", "AG"]
        with self._get_open_handle("Gene", "Summary", organism,
                gene_id) as in_handle:
            soup = BeautifulSoup(in_handle)
            tx_info = soup.find("table", {"id" : "transcripts"})
            if tx_info is None:
                tx_info = soup.find(True, {"id" : "transcripts_text"})
            #print tx_info
            tx_links = tx_info.findAll("a", 
                    href = re.compile("Transcript/Summary"))
            for tx_link in tx_links:
                if tx_link.string and tx_link.string[:2] in valid_gene_starts:
                    txs.append(tx_link.string)
            p_links = tx_info.findAll("a", 
                    href = re.compile("Transcript/ProteinSummary"))
            for p_link in p_links:
                if p_link.string:
                    ps.append(p_link.string)
        assert len(txs) == len(ps), (organism, gene_id, txs, ps)
        return zip(txs, ps)

    def orthologs(self, organism, gene_id):
        """Retrieve a list of orthologs for the given gene ID.
        """
        orthologs = []
        with self._get_open_handle("Gene", "Compara_Ortholog",
                organism, gene_id) as in_handle:
            soup = BeautifulSoup(in_handle)
            orth_table = soup.find("table", "orthologues")
            orth_links = orth_table.findAll("a", 
                    href = re.compile("Gene/Summary"))
            for orth_link in orth_links:
                href_parts = [x for x in orth_link['href'].split('/') if x]
                orthologs.append((href_parts[0], orth_link.string))
        return orthologs

    def compara_tree(self, organism, gene_id):
        """Retrieve the comparative tree calculated by compara.
        """
        with self._get_open_handle("Component/Gene/Web/ComparaTree", "text",
                organism, gene_id) as in_handle:
            soup = BeautifulSoup(in_handle)
            tree_details = soup.find("pre")
            return tree_details.string

    def _get_open_handle(self, item_type, action, organism, gene_id,
                         tx_id = None):
        full_url = "%s/%s/%s/%s?g=%s" % (self._base_url, organism,
                item_type, action, gene_id)
        if tx_id:
            full_url += ";t=%s" % (tx_id)
        url_parts = [p for p in full_url.split("/") if p]
        cache_file = os.path.join(self._cache_dir, "_".join(url_parts[1:]))
        if not os.path.exists(cache_file):
            #print full_url, cache_file
            in_handle = self._safe_open(full_url)
            with open(cache_file, 'w') as out_handle:
                out_handle.write(in_handle.read())
            in_handle.close()
        return open(cache_file, 'r')

    def _safe_open(self, url):
        while 1:
            try:
                in_handle = urllib2.urlopen(url)
                return in_handle
            except urllib2.URLError, msg:
                print msg
                time.sleep(5)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = find_geo_data
"""Retrieve GEO data for an experiment, classifying groups by expression data.
"""
import sys
import os
import csv
import collections
import json
import cPickle

from Bio import Entrez
import rpy2.robjects as robjects

def main():
    organism = "Mus musculus"
    cell_types = ["proB", "ProB", "pro-B"]
    email = "chapmanb@50mail.com"
    save_dir = os.getcwd()
    exp_data = get_geo_data(organism, cell_types, email, save_dir,
        _is_wild_type)

def _is_wild_type(result):
    """Check if a sample is wild type from the title.
    """
    return result.samples[0][0].startswith("WT")

def get_geo_data(organism, cell_types, email, save_dir, is_desired_result):
    save_file = os.path.join(save_dir, "%s-results.pkl" % cell_types[0])
    if not os.path.exists(save_file):
        results = cell_type_gsms(organism, cell_types, email)
        for result in results:
            if is_desired_result(result):
                with open(save_file, "w") as out_handle:
                    cPickle.dump(result, out_handle)
                break

    with open(save_file) as save_handle:
        result = cPickle.load(save_handle)
    print result
    exp = result.get_expression(save_dir)
    for gsm_id, exp_info in exp.items():
        print gsm_id, exp_info.items()[:5]
    return exp

class GEOResult:
    """Represent a GEO summary with associated samples, getting expression data.
    """
    def __init__(self, summary, samples):
        self.summary = summary
        self.samples = samples

    def __str__(self):
        out = "- %s\n" % self.summary
        for title, accession in self.samples:
            out += " %s %s\n" % (title, accession)
        return out

    def get_expression(self, save_dir):
        """Retrieve microarray results for our samples mapped to transcript IDs
        """
        results = dict()
        for (title, gsm_id) in self.samples:
            tx_to_exp = self.get_gsm_tx_values(gsm_id, save_dir)
            results[title] = tx_to_exp
        return results

    def get_gsm_tx_values(self, gsm_id, save_dir):
        """Retrieve a map of transcripts to expression from a GEO GSM file.
        """
        gsm_meta_file = os.path.join(save_dir, "%s-meta.txt" % gsm_id)
        gsm_table_file = os.path.join(save_dir, "%s-table.txt" % gsm_id)
        if (not os.path.exists(gsm_meta_file) or 
                not os.path.exists(gsm_table_file)):
            self._write_gsm_map(gsm_id, gsm_meta_file, gsm_table_file)

        with open(gsm_meta_file) as in_handle:
            gsm_meta = json.load(in_handle)
        id_to_tx = self.get_gpl_map(gsm_meta['platform_id'], save_dir)
        tx_to_vals = collections.defaultdict(list)
        with open(gsm_table_file) as in_handle:
            reader = csv.reader(in_handle, dialect='excel-tab')
            reader.next() # header
            for probe_id, probe_val in reader:
                for tx_id in id_to_tx.get(probe_id, []):
                    tx_to_vals[tx_id].append(float(probe_val))
        return tx_to_vals

    def _write_gsm_map(self, gsm_id, meta_file, table_file):
        """Retrieve GEO expression values using Bioconductor, saving to a table.
        """
        robjects.r.assign("gsm.id", gsm_id)
        robjects.r.assign("table.file", table_file)
        robjects.r.assign("meta.file", meta_file)
        robjects.r('''
          library(GEOquery)
          library(rjson)
          gsm <- getGEO(gsm.id)
          write.table(Table(gsm), file = table.file, sep = "\t", row.names = FALSE,
                      col.names = TRUE)
          cat(toJSON(Meta(gsm)), file = meta.file)
        ''')

    def get_gpl_map(self, gpl_id, save_dir):
        """Retrieve a map of IDs to transcript information from a GEO GPL file.
        """
        gpl_file = os.path.join(save_dir, "%s-map.txt" % gpl_id)
        if not os.path.exists(gpl_file):
            self._write_gpl_map(gpl_id, gpl_file)
        gpl_map = collections.defaultdict(list)
        with open(gpl_file) as in_handle:
            reader = csv.reader(in_handle, dialect='excel-tab')
            reader.next() # header
            for probe_id, tx_id_str in reader:
                for tx_id in tx_id_str.split(' /// '):
                    if tx_id:
                        gpl_map[probe_id].append(tx_id)
        return dict(gpl_map)

    def _write_gpl_map(self, gpl_id, gpl_file):
        """Retrieve GEO platform data using R and save to a table.
        """
        robjects.r.assign("gpl.id", gpl_id)
        robjects.r.assign("gpl.file", gpl_file)
        robjects.r('''
          library(GEOquery)
          gpl <- getGEO(gpl.id)
          gpl.map <- subset(Table(gpl), select=c("ID", "RefSeq.Transcript.ID"))
          write.table(gpl.map, file = gpl.file, sep = "\t", row.names = FALSE,
                      col.names = TRUE)
        ''')

def cell_type_gsms(organism, cell_types, email):
    """Use Entrez to retrieve GEO entries for an organism and cell type.
    """
    Entrez.email = email
    search_term = "%s[ORGN] %s" % (organism, " OR ".join(cell_types))
    print "Searching GEO and retrieving results: %s" % search_term
    
    hits = []
    handle = Entrez.esearch(db="gds", term=search_term)
    results = Entrez.read(handle)
    for geo_id in results['IdList']:
        handle = Entrez.esummary(db="gds", id=geo_id)
        summary = Entrez.read(handle)
        samples = []
        for sample in summary[0]['Samples']:
            for cell_type in cell_types:
                if sample['Title'].find(cell_type) >= 0:
                    samples.append((sample['Title'], sample['Accession']))
                    break
        if len(samples) > 0:
            hits.append(GEOResult(summary[0]['summary'], samples))
    return hits

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = uniprot_query_cluster
#!/usr/bin/env python
"""Classify a set of proteins from an InterPro query based on descriptions.

This uses a download of InterPro IDs and groups them based on metadata retrieved
through Zemanta analysis of the functional descriptions. This will be useful for
well-characterized organisms that contain hand-written descriptions.

Usage:
    interpro_query_classify.py <input tab file> <API key>
"""
from __future__ import with_statement
import sys
import os
import urllib, urllib2
import xml.etree.ElementTree as ET
import time
import simplejson
import shelve
import operator
import collections

import numpy
from Bio import Cluster

def main(target_id, in_file, api_key):
    cache_dir = os.path.join(os.getcwd(), "cache")
    uniprot_retriever = UniprotRestRetrieval(cache_dir)
    cur_db = shelve.open("%s.db" % os.path.splitext(in_file)[0])
    # load the database
    with open(in_file) as in_handle:
        in_handle.readline() # header
        for index, line in enumerate(in_handle):
            uniprot_id = line.split()[0].strip()
            if uniprot_id not in cur_db.keys():
                cur_terms = get_description_terms(uniprot_retriever,
                        uniprot_id, api_key)
                if len(cur_terms) > 0:
                    cur_db[uniprot_id] = cur_terms
    # cluster and print out cluster details
    term_matrix, uniprot_ids = organize_term_array(cur_db)
    cluster_ids, error, nfound = Cluster.kcluster(term_matrix,
            nclusters=10, npass=20, method='a', dist='e')
    cluster_dict = collections.defaultdict(lambda: [])
    for i, cluster_id in enumerate(cluster_ids):
        cluster_dict[cluster_id].append(uniprot_ids[i])
    for cluster_group in cluster_dict.values():
        if target_id in cluster_group:
            for item in cluster_group:
                print item, cur_db[item]
    cur_db.close()
    
def organize_term_array(cur_db):
    """Organize a set of terms into a binary matrix for classification.

    The rows in the final matrix are the database ids, while the columns are
    terms. Each value is 1 if the term is relevant to that ID and 0 otherwise.
    """
    # flatten all terms and get a unique set
    all_terms = reduce(operator.add, cur_db.values())
    term_counts = collections.defaultdict(lambda: 0)
    for term in all_terms:
        term_counts[term] += 1
    all_terms = list(set(all_terms))
    term_matrix = []
    all_ids = []
    for uniprot_id, cur_terms in cur_db.items():
        cur_row = [(1 if t in cur_terms else 0) for t in all_terms]
        term_matrix.append(cur_row)
        all_ids.append(uniprot_id)
    return numpy.array(term_matrix), all_ids

def get_description_terms(retriever, cur_id, api_key):
    metadata = retriever.get_xml_metadata(cur_id)
    if metadata.has_key("function_descr"):
        #print metadata["function_descr"]
        keywords = zemanta_link_kws(metadata["function_descr"], api_key)
        if len(keywords) > 0:
            return keywords
    return []

def zemanta_link_kws(search_text, api_key):
    """Query Zemanta for keywords linked out to wikipedia or freebase.
    """
    gateway = 'http://api.zemanta.com/services/rest/0.0/'
    args = {'method': 'zemanta.suggest',
            'api_key': api_key,
            'text': search_text,
            'return_categories': 'dmoz',
            'return_images': 0,
            'return_rdf_links' : 1,
            'format': 'json'}
    args_enc = urllib.urlencode(args)
    raw_output = urllib2.urlopen(gateway, args_enc).read()
    output = simplejson.loads(raw_output)

    link_kws = []
    for link in output['markup']['links']:
        for target in link['target']:
            if target['type'] in ['wikipedia', 'rdf']:
                link_kws.append(target['title'])
    return list(set(link_kws))

class _BaseCachingRetrieval:
    """Provide a base class for web retrieval with local file caching.
    """
    def __init__(self, cache_dir):
        self._cache_dir = cache_dir
        if not(os.path.exists(cache_dir)):
            os.makedirs(cache_dir)
        # cache 404 errors so we don't call the page multiple times
        self._not_found_file = os.path.join(self._cache_dir,
                '404_not_found.txt')
        self._not_found = []
        if os.path.exists(self._not_found_file):
            with open(self._not_found_file) as in_handle:
                self._not_found = in_handle.read().split()

    def _get_open_handle(self, full_url):
        if full_url in self._not_found:
            return None
        url_parts = [p for p in full_url.split("/") if p]
        cache_file = os.path.join(self._cache_dir, "_".join(url_parts[1:]))
        if not os.path.exists(cache_file):
            #print full_url, cache_file
            in_handle = self._safe_open(full_url)
            if in_handle is None:
                return None
            with open(cache_file, 'w') as out_handle:
                out_handle.write(in_handle.read())
            in_handle.close()
        return open(cache_file, 'r')

    def _safe_open(self, url):
        while 1:
            try:
                in_handle = urllib2.urlopen(url)
                return in_handle
            except urllib2.URLError, msg:
                if str(msg).find("404: Not Found") >= 0:
                    self._add_not_found(url)
                    return None
                print msg
                time.sleep(5)

    def _add_not_found(self, url):
        with open(self._not_found_file, 'a') as out_handle:
            out_handle.write("%s\n" % url)
        self._not_found.append(url)

class UniprotRestRetrieval(_BaseCachingRetrieval):
    """Retrieve RDF data from UniProt for proteins of interest.
    """
    def __init__(self, cache_dir):
        _BaseCachingRetrieval.__init__(self, cache_dir)
        self._server = "http://www.uniprot.org"
        self._xml_ns = "{http://uniprot.org/uniprot}"

    def get_xml_metadata(self, uniprot_id):
        """Retrieve data from the UniProt XML for a record.

        XXX This retrieves only a subset of metadata right now. Needs to
        be complete.
        """
        url_base = "%s/uniprot/%s.xml"
        full_url = url_base % (self._server, uniprot_id)
        # check for empty files -- which have been deleted
        with self._get_open_handle(full_url) as in_handle:
            if in_handle.readline() == "":
                return {}
        metadata = {}
        with self._get_open_handle(full_url) as in_handle:
            root = ET.parse(in_handle).getroot()
            metadata = self._get_org_metadata(root, metadata)
            metadata = self._get_interpro_metadata(root, metadata)
            metadata = self._get_function_metadata(root, metadata)
        return metadata

    def _get_org_metadata(self, root, metadata):
        """Retrieve the organism information from UniProt XML.
        """
        org = root.find("%sentry/%sorganism" % (self._xml_ns, self._xml_ns))
        for org_node in org:
            if org_node.tag == "%sname" % self._xml_ns:
                if org_node.attrib["type"] == "scientific":
                    metadata["org_scientific_name"] = org_node.text
                elif org_node.attrib["type"] == "common":
                    metadata["org_common_name"] = org_node.text
            elif org_node.tag == "%slineage" % self._xml_ns:
                metadata["org_lineage"] = [n.text for n in org_node]
        return metadata

    def _get_interpro_metadata(self, root, metadata):
        """Retrieve InterPro domains present in the protein.
        """
        db_refs = root.findall("%sentry/%sdbReference" % (self._xml_ns,
            self._xml_ns))
        all_refs = []
        for db_ref in db_refs:
            if db_ref.attrib["type"] in ["InterPro"]:
                all_refs.append("%s:%s" % (db_ref.attrib["type"],
                    db_ref.attrib["id"]))
        if len(all_refs) > 0:
            metadata["db_refs"] = all_refs
        return metadata

    def _get_function_metadata(self, root, metadata):
        """Retrieve an InterPro function description.
        """
        comments = root.findall("%sentry/%scomment" % (self._xml_ns,
            self._xml_ns))
        for comment in comments:
            if comment.attrib["type"] in ["function"]:
                for comment_node in comment:
                    if comment_node.tag == "%stext" % (self._xml_ns):
                        metadata["function_descr"] = comment_node.text
        return metadata

    def get_rdf_metadata(self, uniprot_id):
        """Retrieve RDF metadata for the given UniProt accession.

        XXX Not finished. XML parsing looks to be more straightforward
        """
        from rdflib import ConjunctiveGraph as Graph
        url_base = "%s/uniprot/%s.rdf"
        full_url = url_base % (self._server, uniprot_id)
        graph = Graph()
        with self._get_open_handle(full_url) as in_handle:
            graph.parse(in_handle)
        main_subject = [s for s in list(set(graph.subjects())) if
                s.split('/')[-1] == uniprot_id][0]
        for sub, pred, obj in graph:
            print sub, pred, obj

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Incorrect arguments"
        print __doc__
        sys.exit()
    main(sys.argv[1], sys.argv[2], sys.argv[3])

########NEW FILE########
__FILENAME__ = biomart
"""Python API to query BioMart SPARQL endpoints.

BioMart SPARQL documentation is at: http://www.biomart.org/rc6_documentation.pdf (p83-85)

Some useful BioMart servers:
BMC:  http://bm-test.res.oicr.on.ca:9084/
ICGC: http://bm-test.res.oicr.on.ca:9085/
"""
import unittest
from xml.etree import ElementTree as ET
from collections import namedtuple

import SPARQLWrapper

class SematicBioMart:
    """Given SPARQL query, retrieve results from remote BioMart SPARQL endpoint.
    """
    def __init__(self, base_url):
        self._base_url = base_url
        self._query_url = "http://{url}/martsemantics/{ap}/SPARQLXML/get/"
        self._result_ns = "{http://www.w3.org/2005/sparql-results#}"
        self._prefixes = [
          ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
          ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
          ("owl", "http://www.w3.org/2002/07/owl#"),
          ("accesspoint", "http://{url}/martsemantics/{ap}/ontology#"),
          ("class", "biomart://{url}/martsemantics/{ap}/ontology/class#"),
          ("dataset", "biomart://{url}/martsemantics/{ap}/ontology/dataset#"),
          ("attribute", "biomart://{url}/martsemantics/{ap}/ontology/attribute#"),
         ]

    def _get_prefix_str(self, access_point):
        """Convert to prefix strings: PREFIX owl: <http://www.w3.org/2002/07/owl#>
        """
        out = ["PREFIX {name}: <{url}>".format(name=n, url=u.format(url=self._base_url,
                                                                    ap=access_point))
               for n, u in self._prefixes]
        return "\n".join(out) + "\n\n"

    def _do_query(self, statement, access_point):
        sparql = SPARQLWrapper.SPARQLWrapper(self._query_url.format(url=self._base_url,
                                                                    ap=access_point))
        sparql.setReturnFormat(SPARQLWrapper.XML)
        query = self._get_prefix_str(access_point) + statement
        #print query
        sparql.setQuery(query)
        #for line in sparql.query().response:
        #    print line.rstrip()
        return self._parse_response(sparql.query().response)

    def _parse_response(self, in_handle):
        tree = ET.parse(in_handle).getroot()
        out = []
        Result = None
        for results in tree.findall(self._result_ns + "results"):
            for result in results.findall(self._result_ns + "result"):
                names = []
                vals = []
                for bind in result.findall(self._result_ns + "binding"):
                    names.append(self._parse_biomart_name(bind.get("name")))
                    vals.append(bind.find(self._result_ns + "literal").text)
                if Result is None:
                    Result = namedtuple("Result", names)
                out.append(Result(*vals))
        return out 

    def _parse_biomart_name(self, name):
        """Retrieve last part of long BioMart name as attribute.
        """
        return name.split("__")[-1]

    def search(self, builder):
        access_point = "{dataset}_config".format(dataset=builder.dataset)
        return self._do_query(builder.sparql(), access_point)

class BioMartQueryBuilder:
    def __init__(self, dataset, sub_dataset):
        self.dataset = dataset
        self.sub_dataset = sub_dataset
        self._attrs = []
        self._filters = []
        mart_content = {
            ("simple_somatic_mutation", "dm") : ["consequence_type", "validation_status",
                                                 "aa_mutation", "gene_affected",
                                                 "probability", "mutation"],
            ("feature", "main") : ["chromosome", "chromosome_start", "chromosome_end"]}
        self._attr_lookup = self._content_lookup(mart_content)

    def _content_lookup(self, mart_content):
        """Provide mapping of attributes to content and type values.
        """
        out = {}
        for (content, mart_type), attrs in mart_content.iteritems():
            for attr in attrs:
                out[attr] = (content, mart_type)
        return out

    def add_attributes(self, attrs):
        self._attrs.extend([self._biomart_name(a) for a in attrs])

    def add_filter(self, attr, val):
        self._filters.append((self._biomart_name(attr), val))

    def _biomart_name(self, attr):
        """Generate long BioMart attribute name from shortened name.

        These consist of 4 parts (section 4.1 http://www.biomart.org/install.html):
        - dataset
        - content: a free text description
        - type: main or dm (dimension tables)
        - short attribute name
        """
        content, mart_type = self._attr_lookup[attr]
        return "__".join([self.dataset, content, mart_type, attr])

    def sparql(self):
        """Retrieve the SPARQL query for currently set attributes and filters.
        """
        return "\n".join([self._sparql_select(),
                          self._sparql_from(),
                          self._sparql_where()])

    def _sparql_select(self):
        """Build SELECT portion of SPARQL query.
        """
        return "SELECT {attrs}".format(attrs=" ".join(["?{0}".format(a) for a in self._attrs]))

    def _sparql_from(self):
        """Build FROM portion of SPARQL query
        """
        return "FROM dataset:{main}_{sub}".format(main=self.dataset, sub=self.sub_dataset)

    def _sparql_where(self):
        """WHERE clause of SPARQL query.
        """
        select_lines = []
        for attr, val in self._filters:
            select_lines.append('?x attribute:{attr} "{value}" .'.format(attr=attr, value=val))
        for attr in self._attrs:
            select_lines.append("?x attribute:{attr} ?{attr} .".format(attr=attr))
        return "WHERE {{\n{0}\n}}".format("\n".join(select_lines))

class BioMartSematicTest(unittest.TestCase):
    def test_snp_positions(self):
        """Find positions and changes of validated SNPs
        """
        builder = BioMartQueryBuilder("snp", "jpNCCLiver")
        builder.add_attributes(["chromosome", "chromosome_start", "chromosome_end",
                                "aa_mutation", "gene_affected", "probability", "mutation"])
        builder.add_filter("consequence_type", "non_synonymous_coding")
        builder.add_filter("validation_status", "validated")
        icgc_server = SematicBioMart("bm-test.res.oicr.on.ca:9085")
        results = icgc_server.search(builder)
        print results[0]
        assert results[0].chromosome == "1"
        assert results[0].aa_mutation == "D>Y"

example_query = """
SELECT ?snp__feature__main__chromosome ?snp__feature__main__chromosome_start ?snp__feature__main__chromosome_end
       ?snp__simple_somatic_mutation__dm__aa_mutation ?snp__simple_somatic_mutation__dm__gene_affected
       ?snp__simple_somatic_mutation__dm__probability ?snp__simple_somatic_mutation__dm__mutation
FROM dataset:snp_jpNCCLiver
WHERE {
  ?x attribute:snp__simple_somatic_mutation__dm__consequence_type "non_synonymous_coding" .
  ?x attribute:snp__simple_somatic_mutation__dm__validation_status "validated" .
  ?x attribute:snp__feature__main__chromosome ?snp__feature__main__chromosome .
  ?x attribute:snp__feature__main__chromosome_start ?snp__feature__main__chromosome_start .
  ?x attribute:snp__feature__main__chromosome_end ?snp__feature__main__chromosome_end .
  ?x attribute:snp__simple_somatic_mutation__dm__aa_mutation ?snp__simple_somatic_mutation__dm__aa_mutation .
  ?x attribute:snp__simple_somatic_mutation__dm__gene_affected ?snp__simple_somatic_mutation__dm__gene_affected .
  ?x attribute:snp__simple_somatic_mutation__dm__probability ?snp__simple_somatic_mutation__dm__probability .
  ?x attribute:snp__simple_somatic_mutation__dm__mutation ?snp__simple_somatic_mutation__dm__mutation
}
"""

########NEW FILE########
__FILENAME__ = intermine
"""Provide access to servers running Intermine web services.

http://www.intermine.org/wiki/WebService

Intermine is a open source database used for holding experimental data from a
number of model organisms. For instance, the modENCODE project makes their data
available at modMine:

http://intermine.modencode.org/

Queries to do:

    - by lab, affiliation, PI name
"""
import string
import unittest
import StringIO
import urllib, urllib2
from xml.etree import ElementTree as et

import numpy

class Intermine:
    """Provide query based access to data through Intermine web services.
    """
    def __init__(self, base_url):
        self._base = "%s/query/service/query/results" % base_url

    def _do_query(self, query):
        #print query
        req = urllib2.Request(self._base,
                urllib.urlencode(dict(query=query)))
        response = urllib2.urlopen(req)
        vals = []
        for line in response:
            parts = line.split('\t')
            parts[-1] = parts[-1].strip()
            vals.append(parts)
        return vals

    def search(self, builder):
        """Query intermine and return results based on the provided builder.
        """
        # build our filter statements
        nodes = []
        constraints = []
        i = 0
        for filter_group in builder.filters:
            group_names = []
            for fname, fval in filter_group:
                name = string.uppercase[i]
                group_names.append(name)
                node = et.Element("node", path=fname, type="String")
                et.SubElement(node, "constraint",
                        op=builder.get_compare_op(fname),
                        value=fval, code=name)
                nodes.append(node)
                i += 1
            constraints.append("(%s)" % " or ".join(group_names))
        # now build the query
        query = et.Element('query', model="genomic", 
                view=" ".join(builder.attributes),
                constraintLogic=" and ".join(constraints))
        for node in nodes:
            query.append(node)
        # serialize and send
        query_handle = StringIO.StringIO()
        et.ElementTree(query).write(query_handle)
        vals = self._do_query(query_handle.getvalue())
        term_names = builder.get_out_names()
        return numpy.core.records.array(vals, names=",".join(term_names))

class _AbstractBuilder:
    """Base class to derive specific query builders from.
    """
    def __init__(self, paths):
        """Provide an initial set of standard items of interest.
        
        paths is a dictionary of object paths to the base class
        of various items. Common retrieval items are automatically added
        for retrieval and selection.
        """
        self._paths = paths
        self._names = {
            "submission_id" : self._path("submission", "DCCid"),
            "organism": self._path("organism", "name"),
            "submission_title" : self._path("submission", "title"),
            "experiment_name" : self._path("experiment", "name"),
            }
        self._back_map = None

        self.attributes = []
        self.filters = []
        
    def _get_back_map(self):
        if self._back_map is None:
            self._back_map = {}
            for key, val in self._names.items():
                self._back_map[val] = key
        return self._back_map

    def get_compare_op(self, out_name):
        """Define comparison operations for different types of values.

        This contains useful operations for various data types.
        """
        back_map = self._get_back_map()
        name = back_map[out_name]
        if name == "start":
            return ">"
        elif name == "end":
            return "<"
        else:
            return "CONTAINS"

    def _path(self, name, attribute):
        return "%s%s" % (self._paths[name], attribute)
    
    def get_out_names(self):
        back_map = self._get_back_map()
        return [back_map[n] for n in self.attributes]

    def available_attributes(self):
        return self._names.keys()

    def add_attributes(self, names):
        if not isinstance(names, (list, tuple)):
            names = [names]
        for name in names:
            self.attributes.append(self._names[name])
    
    def add_filter(self, *args):
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            name_vals = args[0]
        elif len(args) == 2:
            name_vals = [args]
        else:
            raise ValueError("Need a name and value or list of name values")
        filter_group = []
        for name, val in name_vals:
            # A ':' in the name indicates an optional attribute, while a '.'
            # makes it required. All select fields are required to be present
            # since we are selecting on them.
            intermine_name = self._names[name]
            self._names[name] = intermine_name.replace(":", ".")
            if intermine_name.find(":") >= 0:
                #to_swap = ".".join(intermine_name.split(".")[:-1])
                to_swap = intermine_name.split(".")[0]
                new_swap = to_swap.replace(":", ".")
                # change the select in all of our default names
                for sname, sval in self._names.items():
                    if sval.startswith(to_swap):
                        new_val = sval.replace(to_swap, new_swap)
                        self._names[sname] = new_val
                # also swap it in anything we've added
                for i, attr in enumerate(self.attributes):
                    if attr.startswith(to_swap):
                        self.attributes[i] = attr.replace(to_swap, new_swap)
            filter_group.append((self._names[name], val))
        self.filters.append(filter_group)

class LocationQueryBuilder(_AbstractBuilder):
    """Retrieve data associated with a chromosomal region.
    """
    def __init__(self):
        paths = {
                "submission" : "LocatedSequenceFeature:submissions.",
                "organism" : "LocatedSequenceFeature:organism.",
                "experiment": "LocatedSequenceFeature:submissions.experiment",
                }
        _AbstractBuilder.__init__(self, paths)
        self._names.update({
            "chromosome" : "LocatedSequenceFeature:chromosome.name",
            "start" : "LocatedSequenceFeature:chromosomeLocation.start",
            "end": "LocatedSequenceFeature:chromosomeLocation.end",
            "strand": "LocatedSequenceFeature:chromosomeLocation.strand",
        })

class SubmissionQueryBuilder(_AbstractBuilder):
    """Retrieve submissions based on specific submission properties.
    """
    def __init__(self):
        paths = {
                "submission" : "Submission:",
                "organism" : "Submission:organism.",
                "experiment": "Submission:experiment",
                }
        _AbstractBuilder.__init__(self, paths)
        self._names.update({
            "antibody_name" : self._path("submission", "antibodies.name"),
            "cell_line" : self._path("submission", "cellLines.name"),
            "developmental_stage": self._path("submission",
                "developmentalStages.name"),
        })

class ExperimentQueryBuilder(_AbstractBuilder):
    """Provide a mechanism to build high level Experiment queries.
        
    This uses Experiment as a base to perform queries against Itermine.
    The general notion is high level experiment discovery.
    """
    def __init__(self):
        paths = {
                "submission" : "Experiment:project.submissions.",
                "organism" : "Experiment:project.organisms.",
                "experiment" : "Experiment.",
                }
        _AbstractBuilder.__init__(self, paths)
        self._names.update({
          "project_name" : "Experiment:project.name",
          "submission_description": self._path("submission", "description"),
          "experiment_type": self._path("submission", "experimentType"),
        })

    def free_text_filter(self, search_val):
        """Provide a free text style search for the given value.
        """
        self.add_filter([("submission_description", search_val),
                         ("experiment_type", search_val),
                         ("submission_title", search_val)])

# --- Test Code

# Some example XML, for testing
q = """
<query name="" model="genomic" view=" Experiment.project.submissions.DCCid Experiment.name Experiment.project.name" constraintLogic="B and (A or C or D)">
  <node path="Experiment.project.organisms.name" type="String">
    <constraint op="=" value="Caenorhabditis elegans" description="" identifier="" code="B" extraValue="">
    </constraint>
  </node>
  <node path="Experiment.project.submissions.description" type="String">
    <constraint op="CONTAINS" value="ChIP-seq" description="" identifier="" code="A" extraValue="">
    </constraint>
  </node>
  <node path="Experiment.project.submissions.experimentType" type="String">
    <constraint op="=" value="ChIP-seq" description="" identifier="" code="C" extraValue="">
    </constraint>
  </node>
  <node path="Experiment.project.submissions.title" type="String">
    <constraint op="CONTAINS" value="ChIP-seq" description="" identifier="" code="D" extraValue="">
    </constraint>
  </node>
</query>
"""

class IntermineTest(unittest.TestCase):
    def setUp(self):
        self._server = Intermine("http://intermine.modencode.org")
       
    def test_query(self):
        """Simple string based query with Intermine XML.
        """
        vals = self._server._do_query(q)

    def test_filter_query(self):
        """Provide experiment filtering based on organism and keywords.
        """
        builder = ExperimentQueryBuilder()
        builder.add_attributes([
            "submission_id", "experiment_name"])
        builder.add_filter("organism", "Caenorhabditis elegans")
        builder.free_text_filter("ChIP-seq")

        table = self._server.search(builder)
        print table.dtype.names
        print table
        result = table[0]
        print result['submission_id'], result['experiment_name']

    def test_submission_query(self):
        """Retrieve submissions based on various details of the submission.
        """
        builder = SubmissionQueryBuilder()
        builder.add_attributes(["submission_id", 
            "submission_title", "developmental_stage"])
        builder.add_filter("organism", "Caenorhabditis elegans")
        builder.add_filter("antibody_name", "H3K4me3")
        
        table = self._server.search(builder)
        print table.dtype.names
        print table

    def test_location_query(self):
        """Retrieve submissions with data in particular chromosome locations.
        """
        builder = LocationQueryBuilder()
        builder.add_attributes(["submission_id",
            "submission_title"])
        builder.add_filter("organism", "Caenorhabditis elegans")
        builder.add_filter("chromosome", "I")
        builder.add_filter("start", "5000")
        builder.add_filter("end", "20000")
        
        table = self._server.search(builder)
        print table.dtype.names
        print table

########NEW FILE########
__FILENAME__ = sadi_sparql
import json
import time
import urllib, urllib2
from rdflib.Graph import Graph

result_url_base = "http://biordf.net/tmp/"
query_url = "http://biordf.net/cardioSHARE/query"

query = """
PREFIX pred: <http://sadiframework.org/ontologies/predicates.owl#> 
PREFIX uniprot: <http://lsrn.org/UniProt:> 
SELECT ?name WHERE { 
    uniprot:P15923 pred:hasName ?name 
    }
"""

query = " ".join(query.split("\n"))
req = urllib2.Request(query_url, urllib.urlencode(dict(query=query)))
response = urllib2.urlopen(req)

info = json.loads(response.read())
poll_url = query_url + "?" + urllib.urlencode(dict(poll=info["taskId"]))
while 1:
    response = urllib2.urlopen(poll_url)
    poll_text = response.read()
    # got our JSON response -- means we are ready to retrieve
    if poll_text.startswith("{"):
        break
    time.sleep(3)
poll_info = json.loads(poll_text)

results_url = result_url_base + info["taskId"]

g = Graph()
g.parse(results_url)
for stmt in g:
    print stmt

########NEW FILE########
__FILENAME__ = sparta_ex
import urllib
from rdflib import ConjunctiveGraph as Graph
import sparta

url = 'http://www.gopubmed.org/GoMeshPubMed/gomeshpubmed/Search/RDF?q=18463287&type=RdfExportAll'
gopubmed_handle = urllib.urlopen(url)
graph = Graph()
graph.parse(gopubmed_handle)
gopubmed_handle.close()

graph_subjects = list(set(graph.subjects()))
sparta_factory = sparta.ThingFactory(graph)
for subject in graph_subjects:
    sparta_graph = sparta_factory(subject)
    print subject, [unicode(i) for i in sparta_graph.dc_title][0]

########NEW FILE########
__FILENAME__ = systemsbio
"""Provide a client API to do queries on resources at Semantic Systems Biology.

This wraps the SPARQL query endpoint for Biogateway:

http://www.semantic-systems-biology.org/biogateway
"""
import unittest

import numpy
from SPARQLWrapper import SPARQLWrapper, JSON

class Biogateway:
    """Provide a query builder for getting Biogateway resources.
    """
    def __init__(self):
        self._base_url = "http://www.semantic-systems-biology.org/"
        self._query_url = "%s/biogateway/endpoint" % self._base_url

        self._org_map = None

        self._ns = {
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "ssb": "%sSSB#" % self._base_url,
                }

    def _query_header(self):
        header = "BASE   <%s>\n" % self._base_url
        for short, nurl in self._ns.items():
            header += "PREFIX %s:<%s>\n" % (short, nurl)
        return header

    def _strip_ns(self, data):
        if data.startswith("http"):
            for rem in self._ns.values():
                data = data.replace(rem, "")
        return data

    def _do_query(self, query):
        """Perform the actual work of doing a SPARQL query and parsing results.
        """
        sparql = SPARQLWrapper(self._query_url)
        query = self._query_header() + query
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        out = []
        for result in results["results"]["bindings"]:
            cur_out = dict()
            for var in results["head"]["vars"]:
                try:
                    data = result[var]["value"]
                    data = self._strip_ns(data)
                except KeyError:
                    data = ""
                cur_out[var] = data
            out.append(cur_out)
        return out

    def get_organisms(self):
        """Retrieve organisms available in the database.
        """
        query = """
        SELECT distinct ?taxon ?graph
        WHERE {
          GRAPH <metaonto> {
            ?graph ssb:about_taxon ?taxon_id.
          }
          GRAPH <ncbi> {
            ?taxon_id rdfs:label   ?taxon.
          }
          FILTER(?graph != <SSB> && ?graph != <GOA> && ?graph != <SSB_tc>).
        }
        """
        if self._org_map is None:
            self._org_map = dict()
            for taxon_info in self._do_query(query):
                if not taxon_info["graph"].endswith("_tc"):
                    if not self._org_map.has_key(taxon_info["taxon"]):
                        self._org_map[taxon_info["taxon"]] = taxon_info["graph"]
        orgs = self._org_map.keys()
        orgs.sort()
        return orgs

    def search(self, builder):
        """Retrieve protein IDs from Uniprot with given selection terms.

        Returns a numpy named record array representing the table of results:

        http://www.scipy.org/RecordArrays
        """
        self.get_organisms() # load up our organism mapping
        #XXX for testing
        #self._org_map = {"Homo sapiens" : "25.H_sapiens"}
        all_terms = builder.attributes + builder.filters
        stmt = self._get_sparql_piece("SELECT distinct", "select",
                all_terms, " ")
        stmt += "\nWHERE {"
        if builder.organism is not None:
            stmt += self._get_sparql_piece("GRAPH <%s> {" %
                    self._org_map[builder.organism],
                    "org_graph", all_terms, "\n", "}\n")
        for (graph_name, attr_name) in [("uniprot_sprot", "uniprot_graph"),
                                        ("SSB", "ssb"),
                                        ("gene_ontology_edit", "go_graph"),
                                        ("evidence_code", "evidence_graph")]:
            stmt += self._get_sparql_piece("GRAPH <%s> {" % graph_name,
                    attr_name, all_terms, "\n", "}\n")
        stmt += self._get_sparql_piece("", "to_filter", all_terms, "\n")
        stmt += "\n}"
        results = self._do_query(stmt)
        term_names = [t.select[1:] for t in all_terms if t.select]
        vals = []
        for r in results:
            vals.append([r[n] for n in term_names])
        if len(vals) > 0:
            vals = numpy.core.records.array(vals, names=",".join(term_names))
        else:
            vals = None
        return vals

    def _get_sparql_piece(self, base, attr, terms, join, end = ""):
        stmt = ""
        for term in terms:
            to_add = getattr(term, attr, None)
            if to_add:
                stmt += "%s%s" % (join, to_add)
        if stmt:
            stmt = base + stmt + end
        return stmt

class _AbstractBuilder:
    """Base class to derive specific query builders from.
    """
    def __init__(self):
        self._terms = {}
        self._selects = {}
        self.organism = None
        self.attributes = []
        self.filters = []

    def available_attributes(self):
        return sorted(self._terms.keys())

    def add_attributes(self, names):
        for n in names:
            self.attributes.append(self._terms[n]())

    def available_filters(self):
        return sorted(self._selects.keys())

    def add_filter(self, *args):
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            name_vals = args[0]
        elif len(args) == 2:
            name_vals = [args]
        else:
            raise ValueError("Need a name and value or list of name values")
        for name, val in name_vals:
            self.filters.append(self._selects[name](val))

class UniProtGOQueryBuilder(_AbstractBuilder):
    """Build queries for retrieval against UniProt and GO.

    Biogateway contains the SwissProt database integrated with associated Gene
    Ontology terms. This provides a builder to help attain common linked
    information of interest.
    """
    def __init__(self, organism):
        _AbstractBuilder.__init__(self)
        for tclass in [_RetrieveProtein, _RetrieveInteractor,
                _RetrieveGeneName]:
            self._terms[tclass.select] = tclass
        for tclass in [_SelectByGOTerm, _SelectByDisease]:
            self._selects[tclass.select] = tclass

        self.organism = organism

class ReferenceBuilder(_AbstractBuilder):
    """Build queries to retrieve GO annotations and references.
    """
    def __init__(self):
        _AbstractBuilder.__init__(self)
        for tclass in [_RetrieveReference, _RetrieveEvidence,
                _RetrieveGODescription]:
            self._terms[tclass.select] = tclass
        for tclass in [_SelectByProteinName]:
            self._selects[tclass.select] = tclass

# -- Useful definitions for retrieving and selecting by common items

FILTER_BASE = "FILTER regex(str(%s), '%s')."

class _RetrieveProtein:
    select = "protein_name"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.org_graph = "?protein_id rdfs:label %s." % self.select

class _RetrieveInteractor:
    select = "interactor"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.org_graph = "?interactor_id rdfs:label %s." % self.select
        self.uniprot_graph = """OPTIONAL {
         ?protein_id ssb:interacts_with ?interactor_id.
        }
        """

class _RetrieveGeneName:
    select = "gene_name"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.org_graph = """
        OPTIONAL{
          ?protein_id ssb:encoded_by %s.
          }
         """ % self.select

class _RetrieveReference:
    select = "reference"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.ssb = """
        ?GOA_triple rdf:subject ?protein_id.
        ?GOA_triple ssb:supported_by ?support_node.
        ?support_node ssb:refer %s.
        """ % self.select

class _RetrieveEvidence:
    select = "evidence"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.ssb = """
        ?GOA_triple rdf:subject ?protein_id.
        ?GOA_triple ssb:supported_by ?support_node.
        ?support_node ssb:has_evidence ?evidence_id.
        """
        self.evidence_graph = """
        ?evidence_id rdfs:label %s.
        ?evidence_id a ?type1.
        """ % self.select

class _RetrieveGODescription:
    select = "go_desc"
    def __init__(self):
        self.select = "?%s" % self.__class__.select
        self.ssb = "?GOA_triple rdf:object ?object."
        self.go_graph = """
          ?object rdfs:label %s.
          ?object a ?type2.
          """ % self.select

class _SelectByGOTerm:
    """Provide selection of information based on GO keywords.
    """
    select = "GO_term"
    def __init__(self, keyword):
        self.select = "?%s" % self.__class__.select
        self.to_filter = FILTER_BASE % (self.select, keyword)
        self.go_graph = "?GO_id rdfs:label %s.\n" % self.select
        self.org_graph = "?protein_id ?relation_id ?GO_id."

class _SelectByDisease:
    select = "disease_description"
    def __init__(self, keyword):
        self.select = "?%s" % self.__class__.select
        self.to_filter = FILTER_BASE % (self.select, keyword)
        self.uniprot_graph = "?protein_id ssb:disease %s." % self.select

class _SelectByProteinName:
    select = "protein_id"
    def __init__(self, keyword):
        self.select = "?%s" % self.__class__.select
        self.to_filter = "FILTER regex(?found_in_name,'%s','i')" % keyword
        self.uniprot_graph = """
          {%s ssb:name ?found_in_name.}
                UNION
          {%s ssb:mnemonic ?found_in_name.}
                UNION
          {%s ssb:encoded_by ?found_in_name.}
        """ % ((self.select,) * 3)

class BiogatewayTest(unittest.TestCase):
    """Test retrieval from the Biogateway Systems Bio server.
    """
    def setUp(self):
        self._server = Biogateway()

    def test_organism(self):
        """Retrieve organisms available for querying.
        """
        orgs = self._server.get_organisms()
        print orgs[:5]

    def test_search_query(self):
        """Build a query for searching based on GO terms and diseases.
        """
        builder = UniProtGOQueryBuilder("Homo sapiens")
        builder.add_attributes(["protein_name", "interactor", "gene_name"])
        builder.add_filter("GO_term", "insulin")
        builder.add_filter("disease_description", "diabetes")
        results = self._server.search(builder)
        print len(results), results.dtype.names
        result = results[0]
        print result['protein_name'], result['GO_term'], result['interactor'], \
              result['disease_description']

    def needsupdatetest_reference_query(self):
        """Retrieve GO associations from a UniProt name.
        """
        builder = ReferenceBuilder()
        builder.add_attributes(["reference"])
        builder.add_filter("protein_id", "1433B_HUMAN")
        results = self._server.search(builder)
        print len(results), results.dtype.names
        result = results[0]
        print result
        print result['protein_id'], result['reference']

########NEW FILE########
__FILENAME__ = count_diffexp
#!/usr/bin/env python
"""Calculate differentially expressed genes using EdgeR from bioconductor.

http://bioconductor.org/packages/2.5/bioc/html/edgeR.html

Usage:
    count_diffexp.py <count_file>
"""
import os
import sys
import csv
import collections

import numpy
import rpy2.robjects as robjects
import rpy2.robjects.numpy2ri

def main(count_file):
    base, ext = os.path.splitext(count_file)
    outfile = "%s-diffs.csv" % (base)
    counts = read_count_file(count_file)
    data, groups, sizes, conditions, genes = edger_matrices(counts)
    probs = run_edger(data, groups, sizes, genes)
    write_outfile(outfile, genes, conditions, counts, probs)

def write_outfile(outfile, genes, conditions, work_counts, probs):
    with open(outfile, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(["Region"] +
                ["%s count" % c for c in conditions] + ["edgeR p-value"])
        out_info = []
        for i, gene in enumerate(genes):
            counts = [int(work_counts[c][gene]) for c in conditions]
            out_info.append((probs[i], [gene] + counts))
        out_info.sort()
        [writer.writerow(start + [prob]) for prob, start in out_info]

def run_edger(data, groups, sizes, genes):
    """Call edgeR in R and organize the resulting differential expressed genes.
    """
    robjects.r('''
        library(edgeR)
    ''')
    # find the version we are running -- check for edgeR exactTest function
    try:
        robjects.r["exactTest"]
        is_13_plus = True
    except LookupError:
        is_13_plus = False

    params = {'group' : groups, 'lib.size' : sizes}
    dgelist = robjects.r.DGEList(data, **params)
    # 1.3+ version has a different method of calling and retrieving p values
    if is_13_plus:
        # perform Poisson adjustment and assignment as recommended in the manual
        robjects.globalEnv['dP'] = dgelist
        robjects.r('''
            msP <- de4DGE(dP, doPoisson = TRUE)
            dP$pseudo.alt <- msP$pseudo
            dP$common.dispersion <- 1e-06
            dP$conc <- msP$conc
            dP$common.lib.size <- msP$M
        ''')
        dgelist = robjects.globalEnv['dP']
        de = robjects.r.exactTest(dgelist)
        tags = robjects.r.topTags(de, n=len(genes))
        tag_table = tags[0]
        indexes = [int(t) - 1 for t in tag_table.rownames()]
        # can retrieve either raw or adjusted p-values
        #pvals = list(tags.r['p.value'][0])
        pvals = list(tag_table.r['adj.p.val'][0])
    # older 1.2 version of edgeR
    else:
        ms = robjects.r.deDGE(dgelist, doPoisson=True)
        tags = robjects.r.topTags(ms, pair=groups, n=len(genes))
        indexes = [int(t) - 1 for t in tags.rownames()]
        # can retrieve either raw or adjusted p-values
        #pvals = list(tags.r['P.Value'][0])
        pvals = list(tags.r['adj.P.Val'][0])
    assert len(indexes) == len(pvals)
    pvals_w_index = zip(indexes, pvals)
    pvals_w_index.sort()
    assert len(pvals_w_index) == len(indexes)
    return [p for i,p in pvals_w_index]

def get_conditions_and_genes(work_counts): 
    conditions = work_counts.keys()
    conditions.sort()
    all_genes = []
    for c in conditions:
        all_genes.extend(work_counts[c].keys())
    all_genes = list(set(all_genes))
    all_genes.sort()
    sizes = [work_counts[c]["Total"] for c in conditions]
    all_genes.remove("Total")
    return conditions, all_genes, sizes
    
def edger_matrices(work_counts):
    """Retrieve matrices for input into edgeR differential expression analysis.
    """
    conditions, all_genes, sizes = get_conditions_and_genes(work_counts)
    assert len(sizes) == 2
    groups = [1, 2]
    data = []
    final_genes = []
    for g in all_genes:
        cur_row = [int(work_counts[c][g]) for c in conditions]
        if sum(cur_row) > 0:
            data.append(cur_row)
            final_genes.append(g)
    return (numpy.array(data), numpy.array(groups), numpy.array(sizes),
            conditions, final_genes)

def read_count_file(in_file):
    """Read count information from a simple CSV file into a dictionary.
    """
    counts = collections.defaultdict(dict)
    with open(in_file) as in_handle:
        reader = csv.reader(in_handle)
        header = reader.next()
        conditions = header[1:]
        for parts in reader:
            region_name = parts[0]
            region_counts = [float(x) for x in parts[1:]]
            for ci, condition in enumerate(conditions):
                counts[condition][region_name] = region_counts[ci]
    return dict(counts)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print __doc__
        sys.exit()
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = count_diffexp_general
#!/usr/bin/env python
"""Calculate differentially expressed genes using EdgeR from bioconductor.

http://bioconductor.org/packages/2.5/bioc/html/edgeR.html

Usage:
    count_diffexp.py <count_file>
"""
import os
import sys
import csv
import collections

import numpy
import rpy2.robjects as robjects
import rpy2.robjects.numpy2ri

def main(count_file):
    base, ext = os.path.splitext(count_file)
    outfile = "%s-diffs.csv" % (base)
    counts, all_regions, conditions, groups, sizes = read_count_file(count_file)
    data, regions, sizes = edger_matrix(counts, conditions, all_regions)
    probs = run_edger(data, groups, sizes, regions)
    write_outfile(outfile, regions, conditions, counts, probs, sizes)

def write_outfile(outfile, genes, conditions, work_counts, probs, sizes):
    with open(outfile, "w") as out_handle:
        writer = csv.writer(out_handle)
        writer.writerow(["Region"] +
                ["%s count" % c for c in conditions] + ["edgeR p-value"])
        writer.writerow(["total"] + [str(s) for s in sizes])
        out_info = []
        for i, gene in enumerate(genes):
            counts = [int(work_counts[c][gene]) for c in conditions]
            out_info.append((probs[i], [gene] + counts))
        out_info.sort()
        [writer.writerow(start + [prob]) for prob, start in out_info]

def run_edger(data, groups, sizes, regions):
    """Call edgeR in R and organize the resulting differential expressed genes.
    """
    robjects.r('''
        library(edgeR)
    ''')
    # find the version we are running -- check for edgeR exactTest function
    try:
        robjects.r["exactTest"]
    except LookupError:
        raise ValueError("Need edgeR 1.3+ to run analysis.")
    params = {'group' : numpy.array(groups), 'lib.size' : sizes}
    dgelist = robjects.r.DGEList(data, **params)
    # perform Poisson adjustment and assignment as recommended in the manual
    robjects.globalEnv['dP'] = dgelist
    # if we have replicates, can estimate common and tagwise dispersion
    if len(groups) > 2:
        robjects.r('''
          dP <- estimateCommonDisp(dP)
          prior.weight <- estimateSmoothing(dP)
          dP <- estimateTagwiseDisp(dP, prior.n=10)
        ''')
    # otherwise use a Poisson distribution estimation (Section 9 of manual)
    else:
        robjects.r('''
            msP <- de4DGE(dP, doPoisson = TRUE)
            dP$pseudo.alt <- msP$pseudo
            dP$common.dispersion <- 1e-06
            dP$conc <- msP$conc
            dP$common.lib.size <- msP$M
        ''')
    dgelist = robjects.globalEnv['dP']
    de = robjects.r.exactTest(dgelist)
    tag_table = robjects.r.topTags(de, n=len(regions))[0]
    print robjects.r.head(tag_table)
    indexes = [int(t.replace("tag.", "")) - 1 for t in tag_table.rownames()]
    # can retrieve either raw or adjusted p-values
    #pvals = list(tags.r['p.value'][0])
    pvals = list(tag_table.r['PValue'][0])

    assert len(indexes) == len(pvals)
    pvals_w_index = zip(indexes, pvals)
    pvals_w_index.sort()
    assert len(pvals_w_index) == len(indexes)
    return [p for i,p in pvals_w_index]

def edger_matrix(work_counts, conditions, regions):
    """Count matrices for input into edgeR differential expression analysis.
    """
    data = []
    final_regions = []
    for r in regions:
        cur_row = [int(work_counts[c][r]) for c in conditions]
        if sum(cur_row) > 0:
            final_regions.append(r)
            data.append(cur_row)
    sizes = numpy.sum(data, axis=0)
    return numpy.array(data), final_regions, sizes

def read_count_file(in_file):
    """Read count information from a simple CSV file into a dictionary.
    """
    counts = collections.defaultdict(dict)
    regions = []
    with open(in_file) as in_handle:
        reader = csv.reader(in_handle)
        conditions = reader.next()[1:]
        groups = [int(p) for p in reader.next()[1:]]
        totals = [int(p) for p in reader.next()[1:]]
        for parts in reader:
            region_name = parts[0]
            regions.append(region_name)
            region_counts = [float(x) for x in parts[1:]]
            for ci, condition in enumerate(conditions):
                counts[condition][region_name] = region_counts[ci]
    return dict(counts), regions, conditions, groups, totals

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print __doc__
        sys.exit()
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = diffexp_go_analysis
#!/usr/bin/env python
"""Provide topGO analysis of overrepresented GO annotation terms in a dataset.

Usage:
    stats_go_analysis.py <input CVS> <gene to GO file>
"""
from __future__ import with_statement
import sys
import csv
import collections

import rpy2.robjects as robjects

def main(input_csv, gene_to_go_file):
    gene_pval = 1e-2
    go_pval = 0.2
    go_term_type = "MF"
    topgo_method = "classic" # choice of classic, elim, weight

    with open(input_csv) as in_handle:
        genes_w_pvals = parse_input_csv(in_handle)
    with open(gene_to_go_file) as in_handle:
        gene_to_go, go_to_gene = parse_go_map_file(in_handle, genes_w_pvals)
    if len(gene_to_go) == 0:
        raise ValueError("No GO terms match to input genes. "
              "Check that the identifiers between the input and GO file match.")
    go_terms = run_topGO(genes_w_pvals, gene_to_go, go_term_type,
            gene_pval, go_pval, topgo_method)
    print_go_info(go_terms, go_term_type, go_to_gene)

def print_go_info(go_terms, go_term_type, go_to_gene):
    for final_pval, go_id, go_term in go_terms:
        genes = []
        for check_go in [go_id] + get_go_children(go_id, go_term_type):
            genes.extend(go_to_gene.get(check_go, []))
        genes = sorted(list(set(genes)))
        print "-> %s (%s) : %0.4f" % (go_id, go_term, final_pval)
        for g in genes:
            print g

def get_go_children(go_term, go_term_type):
    """Retrieve all more specific GO children from a starting GO term.
    """
    robjects.r('''
        library(GO.db)
    ''')
    child_map = robjects.r["GO%sCHILDREN" % (go_term_type)]
    children = []
    to_check = [go_term]
    while len(to_check) > 0:
        new_children = []
        for check_term in to_check:
            new_children.extend(list(robjects.r.get(check_term, child_map)))
        new_children = list(set([c for c in new_children if c]))
        children.extend(new_children)
        to_check = new_children
    children = list(set(children))
    return children

def _dict_to_namedvector(init_dict):
    """Call R to create a named vector from an input dictionary.
    """
    return robjects.r.c(**init_dict)

def run_topGO(gene_vals, gene_to_go, go_term_type, gene_pval, go_pval,
        topgo_method):
    """Run topGO, returning a list of pvalues and terms of interest.
    """
    # run topGO with our GO and gene information
    robjects.r('''
        library(topGO)
    ''')
    robjects.r('''
        topDiffGenes = function(allScore) {
          return (allScore < %s)
        }
    ''' % gene_pval)
    params = {"ontology" : go_term_type,
              "annot" : robjects.r["annFUN.gene2GO"],
              "geneSelectionFun" : robjects.r["topDiffGenes"],
              "allGenes" : _dict_to_namedvector(gene_vals),
              "gene2GO" : _dict_to_namedvector(gene_to_go)
              }
    go_data = robjects.r.new("topGOdata", **params)
    results = robjects.r.runTest(go_data, algorithm=topgo_method,
            statistic="fisher")
    scores = robjects.r.score(results)
    num_summarize = min(100, len(scores.names))
    # extract term names from the topGO summary dataframe
    results_table = robjects.r.GenTable(go_data, elimFisher=results,
            orderBy="elimFisher", topNodes=num_summarize)
    print results_table
    GO_ID_INDEX = 0
    TERM_INDEX = 1
    ids_to_terms = dict()
    for index, go_id in enumerate(results_table[GO_ID_INDEX]):
        ids_to_terms[go_id] = results_table[TERM_INDEX][index]
    go_terms = []
    # convert the scores and results information info terms to return
    for index, item in enumerate(scores):
        if item < go_pval:
            go_id = scores.names[index]
            go_terms.append((item, go_id, ids_to_terms.get(go_id, "")))
    go_terms.sort()
    return go_terms

def parse_go_map_file(in_handle, genes_w_pvals):
    gene_list = genes_w_pvals.keys()
    gene_to_go = collections.defaultdict(list)
    go_to_gene = collections.defaultdict(list)
    for line in in_handle:
        parts = line.split("\t")
        gene_id = parts[0]
        go_id = parts[1].strip()
        if gene_id in gene_list:
            gene_to_go[gene_id].append(go_id)
            go_to_gene[go_id].append(gene_id)
    return dict(gene_to_go), dict(go_to_gene)

def parse_input_csv(in_handle):
    reader = csv.reader(in_handle)
    reader.next() # header
    all_genes = dict()
    for (gene_name, _, _, pval) in reader:
        all_genes[gene_name] = float(pval)
    return all_genes

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print __doc__
        sys.exit()
    main(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = build
"""Convert IPython notebook into HTML reveal.js slides.

Overrides some standard functionality:
  - Uses a local reveal.js with customized CSS.
  - Avoids writing out the standard IPython reveal CSS overrides in favor of the default style.
"""
from IPython.nbconvert.exporters import RevealExporter
from IPython.config import Config

from IPython.nbformat import current as nbformat

infile = "chapmanb_bosc2013_bcbio.ipynb"
outfile = "chapmanb_bosc2013_bcbio.html"

notebook = open(infile).read()
notebook_json = nbformat.reads_json(notebook)

c = Config({'RevealHelpTransformer': {'enabled': True,
                                      'url_prefix':'../reveal.js',},
            "CSSHTMLHeaderTransformer": {'enabled': False}
            })

exportHtml = RevealExporter(config=c)
(body,resources) = exportHtml.from_notebook_node(notebook_json)

with open(outfile, "w") as out_handle:
    in_css_override = False
    for line in body.encode('utf-8').split("\n"):
        if line.startswith("/* Overrides of notebook CSS"):
            in_css_override = True
        if in_css_override:
            if line.startswith("</style>"):
                in_css_override = False
        if not in_css_override:
            out_handle.write(line + "\n")

########NEW FILE########
__FILENAME__ = plot_depth_ratio
#!/usr/bin/env python
"""Plot depth for a set of heterozygous calls relative to quality and allele ratio.

Used to help identify cutoff for filtering false positives by comparing
distribution to true positives.

Usage:
  plot_depth_ratio.py <VCF file of het calls> '<Plot title>'
"""
import os
import sys

import vcf
import prettyplotlib as ppl
import matplotlib.pyplot as plt

def main(in_file, title):
    depths, ratios, quals = get_ad_depth(in_file)
    plot_qual_hist(quals, in_file)
    plot_depth_ratios(depths, ratios, quals, in_file, title)

def plot_depth_ratios(depths, ratios, quals, in_file, title):
    out_file = "%s-depthratios.png" % os.path.splitext(in_file)[0]
    fig, ax = plt.subplots(1)
    for ds, rs, qualrange in _group_ratios_by_qual(depths, ratios, quals):
        print qualrange, len(ds)
        ppl.scatter(ax, x=depths, y=ratios, label=qualrange)
    ppl.legend(ax, title="Quality score range")
    ax.set_title(title)
    ax.set_xlabel("Depth")
    ax.set_ylabel("Variant/Total ratio")
    fig.savefig(out_file)

def _group_ratios_by_qual(depths, ratios, quals):
    #ranges = [(0, 100), (100, 250), (250, 500), (500, 1000), (1000, 2500)]
    #ranges = [(0, 50), (50, 100), (100, 150), (150, 250)]
    ranges = [(0, 250), (250, 500)]
    for qs, qe in ranges:
        cur_ds = []
        cur_rs = []
        for d, r, q in zip(depths, ratios, quals):
            if q >= qs and q < qe:
                cur_ds.append(d)
                cur_rs.append(r)
        yield cur_ds, cur_rs, "%s-%s" % (qs, qe)

def plot_qual_hist(quals, in_file):
    quals = [x for x in quals if x < 500.0]
    out_file = "%s-hist.png" % os.path.splitext(in_file)[0]
    fig, ax = plt.subplots(1)
    ppl.hist(ax, [quals], bins=100)
    fig.savefig(out_file)

def get_ad_depth(in_file):
    depths = []
    ratios = []
    quals = []
    with open(in_file) as in_handle:
        reader = vcf.Reader(in_handle)
        for rec in reader:
            for sample in rec.samples:
                try:
                    ad = sample["AD"]
                except AttributeError:
                    ad = []
                if len(ad) == 2:
                    ref, alt = sample["AD"]
                    depth = ref + alt
                    if depth > 0:
                        depths.append(min(rec.INFO["DP"], 500))
                        ratios.append(alt / float(depth))
                        quals.append(rec.QUAL)
    return depths, ratios, quals

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = plot_validation
#!/usr/bin/env python
"""Plot validation results from variant calling comparisons.

Handles data normalization and plotting, emphasizing comparisons on methodology
differences. Works with output from bcbio-nextgen pipeline and combines the previous
2-step process that relied on R/ggplot.

Usage:
  plot_validation.py <grading_summary.csv> <bcbio_sample.yaml>
"""
import bisect
import collections
import math
import os
import sys

import numpy as np
import pandas as pd
import yaml

import prettyplotlib as ppl
from prettyplotlib import plt

from bcbio.variation import bamprep

def main(in_file, config_file):
    df = pd.read_csv(in_file)
    config = read_config(config_file)
    df["aligner"] = [get_aligner(x, get_sample_config(x, config)) for x in df["sample"]]
    df["bamprep"] = [get_bamprep(x, get_sample_config(x, config)) for x in df["sample"]]
    floors = get_group_floors(df)
    df["value.floor"] = [get_floor_value(x, cat, vartype, floors)
                         for (x, cat, vartype) in zip(df["value"], df["category"], df["variant.type"])]
    print(df.head())
    for i, prep in enumerate(df["bamprep"].unique()):
        plot_prep_methods(df, prep, i, in_file)

def plot_prep_methods(df, prep, prepi, in_file):
    """Plot comparison between BAM preparation methods.
    """
    out_file = "%s-%s.png" % (os.path.splitext(in_file)[0], prep)
    cats = ["concordant", "discordant-missing-total",
            "discordant-extra-total", "discordant-shared-total"]
    cat_labels = {"concordant": "Concordant",
                  "discordant-missing-total": "Discordant (missing)",
                  "discordant-extra-total": "Discordant (extra)",
                  "discordant-shared-total": "Discordant (shared)"}
    vtype_labels = {"snp": "SNPs", "indel": "Indels"}
    prep_labels = {"gatk": "GATK best-practice BAM preparation (recalibration, realignment)",
                   "none": "Minimal BAM preparation (samtools de-duplication only)"}
    caller_labels = {"ensemble": "Ensemble", "freebayes": "FreeBayes",
                     "gatk": "GATK Unified\nGenotyper", "gatk-haplotype": "GATK Haplotype\nCaller"}
    vtypes = df["variant.type"].unique()
    fig, axs = plt.subplots(len(vtypes), len(cats))
    callers = sorted(df["caller"].unique())
    width = 0.8
    for i, vtype in enumerate(vtypes):
        for j, cat in enumerate(cats):
            ax = axs[i][j]
            if i == 0:
                ax.set_title(cat_labels[cat], size=14)
            ax.get_yaxis().set_ticks([])
            if j == 0:
                ax.set_ylabel(vtype_labels[vtype], size=14)
            vals, labels, maxval = _get_chart_info(df, vtype, cat, prep, callers)
            ppl.bar(ax, left=np.arange(len(callers)),
                    color=ppl.set2[prepi], width=width, height=vals)
            ax.set_ylim(0, maxval)
            if i == len(vtypes) - 1:
                ax.set_xticks(np.arange(len(callers)) + width / 2.0)
                ax.set_xticklabels([caller_labels[x] for x in callers], size=8, rotation=45)
            else:
                ax.get_xaxis().set_ticks([])
            _annotate(ax, labels, vals, np.arange(len(callers)), width)
    fig.text(.5, .95, prep_labels[prep], horizontalalignment='center', size=16)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.87, bottom=0.15, wspace=0.1, hspace=0.1)
    #fig.tight_layout()
    fig.set_size_inches(10, 5)
    fig.savefig(out_file)
    return out_file

def _get_chart_info(df, vtype, cat, prep, callers):
    """Retrieve values for a specific variant type, category and prep method.
    """
    maxval_raw = max(list(df["value.floor"]))
    norm_ylim = 1000.0 # ceil to make plots more comparable
    maxval = math.ceil(maxval_raw / norm_ylim) * norm_ylim
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
    return vals, labels, maxval

def _annotate(ax, annotate, height, left, width):
    """Annotate axis with labels. Adjusted from prettyplotlib to be more configurable.
    Needed to adjust label size.
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

        # Finally, add the text to the axes
        ax.annotate(annotation, (x, h + offset),
                    verticalalignment=verticalalignment,
                    horizontalalignment='center',
                    size=10,
                    color=ppl.almost_black)

def get_floor_value(x, cat, vartype, floors):
    base = floors[(cat, vartype)]
    #print cat, vartype, x, base
    return x - base

def get_group_floors(df):
    """Floor values to nearest 5,000 for each category.
    """
    floors = {}
    floor_vals = [x * 5e3 for x in range(50)]
    for name, group in df.groupby(["category", "variant.type"]):
        floors[name] = int(floor_vals[bisect.bisect(floor_vals, min(group["value"])) - 1])
    return floors

def get_aligner(x, config):
    return config["algorithm"]["aligner"]

def get_bamprep(x, config):
    params = bamprep._get_prep_params({"config": {"algorithm": config["algorithm"]}})
    if params["realign"] == "gatk" and params["recal"] == "gatk":
        return "gatk"
    elif not params["realign"] and not params["recal"]:
        return "none"
    else:
        raise ValueError("Unexpected bamprep approach: %s" % params)

def get_sample_config(x, config):
    for c in config["details"]:
        if c["description"] == x:
            return c
    raise ValueError("Did not find %s in config %s" % (x, config["details"]))

def read_config(in_file):
    with open(in_file) as in_handle:
        return yaml.load(in_handle)

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = prep_multicmp_results
#!/usr/bin/env python
"""Prepare subsets of data from multi-method variant calling comparison.

Usage:
  prep_multicmp_results.py <in_csv>
"""
import bisect
import os
import sys

import pandas as pd

def main(in_file):
    out_file = "%s-prep%s" % os.path.splitext(in_file)
    df = pd.read_csv(in_file)
    df["aligner"] = [get_aligner(x) for x in df["sample"]]
    df["bamprep"] = [get_bamprep(x) for x in df["sample"]]
    df["sample"] = ["%s %s" % (x, y) if x and y else s
                    for (x, y, s) in zip(df["aligner"], df["bamprep"], df["sample"])]
    floors = get_group_floors(df)
    df["value.floor"] = [get_floor_value(x, cat, vartype, floors)
                         for (x, cat, vartype) in zip(df["value"], df["category"], df["variant.type"])]
    df.to_csv(out_file)

def get_floor_value(x, cat, vartype, floors):
    base = floors[(cat, vartype)]
    print cat, vartype, x, base
    return x - base

def get_group_floors(df):
    """Floor values to nearest 10,000 for each category.
    """
    floors = {}
    floor_vals = [x * 1e4 for x in range(50)]
    for name, group in df.groupby(["category", "variant.type"]):
        floors[name] = int(floor_vals[bisect.bisect(floor_vals, min(group["value"])) - 1])
    return floors

def get_aligner(x):
    if x in ["NA12878-1", "NA12878-3"]:
        return "novoalign"
    elif x in ["NA12878-2", "NA12878-4"]:
        return "bwa"
    else:
        return ""

def get_bamprep(x):
    if x in ["NA12878-1", "NA12878-2"]:
        return "gatk"
    elif x in ["NA12878-3", "NA12878-4"]:
        return "gkno"
    else:
        return ""

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = prep_rm_subset
"""Prepare subset regions of full NIST NA12878 reference materials for evaluation.

Allows preparation of exome or targeted reference materials from
the full NIST NA12878 genome.

Requires:
  vcflib: https://github.com/ekg/vcflib
  bedtools: http://bedtools.readthedocs.org/en/latest/

Usage:
  prep_rm_subset.py <input_config.yaml>
"""
import os
import sys
import subprocess

import yaml
import pybedtools

def main(config_file):
    config = load_config(config_file)
    config["out_base"] = os.path.join(config["dirs"]["rm"],
                                      config["subset"]["name"])
    region_bed = intersect_beds(config["subset"]["interval"],
                                config["rm"]["interval"], config)
    final_vcf = combine_subset_vcfs(config["rm"]["vcfs"],
                                    config["rm"]["ref"],
                                    region_bed, config)
    filter_vcf(final_vcf)

def filter_vcf(in_vcf):
    out_vcf = "%s-pass%s" % os.path.splitext(in_vcf)
    with open(in_vcf) as in_handle:
        with open(out_vcf, "w") as out_handle:
            for line in in_handle:
                passes = False
                if line.startswith("#"):
                    passes = True
                else:
                    parts = line.split("\t")
                    if parts[6] in [".", "PASS"]:
                        passes = True
                if passes:
                    out_handle.write(line)

def combine_subset_vcfs(vcfs, ref_file, region_bed, config):
    out_file = os.path.join(config["dirs"]["rm"],
                            "%s.vcf" % config["subset"]["name"])
    tmp_files = []
    for i, vcf in enumerate(vcfs):
        tmp_out_file = "%s-%s.vcf" % (os.path.splitext(out_file)[0], i)
        cmd = "vcfintersect -b {region_bed} {vcf} > {tmp_out_file}"
        subprocess.check_call(cmd.format(**locals()), shell=True)
        tmp_files.append(tmp_out_file)
    # Need to generalize for multiple VCFs
    one_vcf, two_vcf = tmp_files
    cmd = "vcfintersect -r {ref_file} -u {two_vcf} {one_vcf} > {out_file}"
    subprocess.check_call(cmd.format(**locals()), shell=True)
    for tmp_file in tmp_files:
        os.remove(tmp_file)
    return out_file

def intersect_beds(base_bed, rm_bed, config):
    out_file = os.path.join(config["dirs"]["rm"],
                            "%s-regions.bed" % config["subset"]["name"])
    if not os.path.exists(out_file):
        base_bt = pybedtools.BedTool(base_bed)
        base_bt.intersect(rm_bed).saveas(out_file)
    return out_file

def load_config(config_file):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    dirs = config["dirs"]
    config["rm"]["vcfs"] = [os.path.join(dirs["rm"], x) for x in config["rm"]["vcfs"]]
    config["rm"]["interval"] = os.path.join(dirs["rm"], config["rm"]["interval"])
    config["subset"]["interval"] = os.path.join(dirs["rm"], config["subset"]["interval"])
    config["rm"]["ref"] = os.path.join(dirs["genome"], config["rm"]["ref"])
    return config

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = pull_bwa_novoalign_diffs
#!/usr/bin/env python
"""Extract concordant variant differences between bwa and novoalign, focusing on mapping differences.

Requires:
  bedtools, pybedtools, vcflib
"""
import os
import subprocess
import sys

import pybedtools
import yaml

def main(config_file):
   with open(config_file) as in_handle:
       config = yaml.load(in_handle)
   out_dir = config["dirs"]["work"]
   if not os.path.exists(out_dir):
       os.makedirs(out_dir)
   consub_vcf = get_concordant_subset(config["calls"]["bwa"],
                                      config["calls"]["novoalign"],
                                      config["ref"], out_dir)
   if config.get("callable"):
      nocall_vcf = get_nocallable_subset(consub_vcf, config["callable"]["novoalign"])
   else:
      nocall_vcf = consub_vcf
   orig_nocall_vcf = subset_original_vcf(nocall_vcf, config["calls"]["bwa-orig"],
                                         config["ref"])
   for fname in [consub_vcf, nocall_vcf, orig_nocall_vcf]:
       with open(fname) as in_handle:
           total = sum([1 for line in in_handle if not line.startswith("#")])
       print fname, total

def subset_original_vcf(base_vcf, orig_vcf, ref_file):
    out_file = "{base}-orig.vcf".format(base=os.path.splitext(base_vcf)[0])
    if not os.path.exists(out_file):
        cmd = "vcfintersect -i {base_vcf} -r {ref_file} {orig_vcf} > {out_file}"
        subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

def get_nocallable_subset(base_vcf, cmp_bed):
    """Retrieve subset of calls in base_vcf not in cmp_bed.
    """
    out_file = "{base}-nocallable.vcf".format(base=os.path.splitext(base_vcf)[0])
    if not os.path.exists(out_file):
        base_bt = pybedtools.BedTool(base_vcf)
        cmp_bt = pybedtools.BedTool(cmp_bed)
        base_bt.intersect(cmp_bt, v=True).saveas(out_file + ".bt")
        with open(out_file, "w") as out_handle:
            with open(base_vcf) as in_handle:
                for line in in_handle:
                    if line.startswith("#"):
                        out_handle.write(line)
            with open(out_file + ".bt") as in_handle:
                for line in in_handle:
                    out_handle.write(line)
    return out_file

def get_concordant_subset(base_vcf, cmp_vcf, ref_file, out_dir):
    """Retrieve subset of calls in base_vcf not in cmp_vcf.
    """
    out_file = os.path.join(out_dir, "{base}-unique.vcf"
                            .format(base=os.path.splitext(os.path.basename(base_vcf))[0]))
    if not os.path.exists(out_file):
        cmd = "vcfintersect -v -i {cmp_vcf} -r {ref_file} {base_vcf} > {out_file}"
        subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = pull_shared_discordants
#!/usr/bin/env python
"""Extract discordant variants found in multiple calling methods.

These are potential incorrect calls in the reference materials.

Requires:
  vcfintersect
"""
import itertools
import os
import subprocess
import sys

import yaml

def main(config_file):
    with open(config_file) as in_handle:
        config = yaml.load(in_handle)
    out_dir = config["dirs"]["work"]
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    call_cmps = get_call_cmps(config["calls"], config["ref"], out_dir)
    union_file = get_union(call_cmps, config["ref"], out_dir)
    for f in list(config["calls"].itervalues()) + call_cmps + [union_file]:
       print f, variant_count(f)

def variant_count(fname):
    with open(fname) as in_handle:
        return sum([1 for line in in_handle if not line.startswith("#")])

def get_union(call_cmps, ref_file, out_dir):
   cur_union = call_cmps[0]
   for i, next_cmp in enumerate(call_cmps[1:]):
       out_file = os.path.join(out_dir, "union-{i}.vcf".format(i=i))
       cur_union = combine_two_vcfs(cur_union, next_cmp, ref_file, out_file)
   return cur_union

def combine_two_vcfs(f1, f2, ref_file, out_file):
    if not os.path.exists(out_file):
        cmd = "vcfintersect -u {f1} -r {ref_file} {f2} > {out_file}"
        subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

def get_call_cmps(calls, ref_file, out_dir):
   """Retrieve pairwise intersections between all pairs of variants.
   """
   return [intersect_two_vcfs(c1, c2, calls[c1], calls[c2], ref_file, out_dir)
           for c1, c2 in itertools.combinations(calls.keys(), 2)]

def intersect_two_vcfs(n1, n2, f1, f2, ref_file, out_dir):
    out_file = os.path.join(out_dir, "{n1}-{n2}-intersect.vcf".format(**locals()))
    if not os.path.exists(out_file):
        cmd = "vcfintersect -i {f1} -r {ref_file} {f2} > {out_file}"
        subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

if __name__ == "__main__":
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = blast_conservation_plot
#!/usr/bin/env python
"""Examine conservation of a protein by comparison to BLAST hits.

Given a UniProt protein ID or accession number as input (really anything that
can be queried in NCBI), this performs a BLAST search against the
non-redundant protein database and parses the results. Using them, a plot is
generated of average conservation across the protein. This provides a quick
evaluation of conserved and fluctuating regions.

Usage:
    blast_conservation_plot.py <accession>
"""
from __future__ import with_statement
import sys
import os

from Bio import Entrez
from Bio.Blast import NCBIWWW
from Bio.Blast import NCBIXML
from Bio.SubsMat import MatrixInfo
import pylab
import numpy

def main(accession):
    window_size = 29
    cache_dir = os.path.join(os.getcwd(), "cache")
    ncbi_manager = NCBIManager(cache_dir)
    protein_gi = ncbi_manager.search_for_gi(accession, "protein")
    blast_rec = ncbi_manager.remote_blast(protein_gi, "blastp")
    cons_caculator = BlastConservationCalculator()
    data_smoother = SavitzkyGolayDataSmoother(window_size)
    cons_dict = cons_caculator.conservation_dict(blast_rec)
    indexes = cons_dict.keys()
    indexes.sort()
    pos_data = []
    cons_data = []
    for pos in indexes:
        pos_data.append(pos + 1)
        if len(cons_dict[pos]) > 0:
            cons_data.append(numpy.median(cons_dict[pos]))
        else:
            cons_data.append(0)
    smooth_data = data_smoother.smooth_values(cons_data)
    smooth_pos_data = pos_data[data_smoother.half_window():
            len(pos_data) - data_smoother.half_window()]
    pylab.plot(smooth_pos_data, smooth_data)
    pylab.axis(xmin=min(pos_data), xmax=max(pos_data))
    pylab.xlabel("Amino acid position")
    pylab.ylabel("Conservation")
    pylab.savefig('%s_conservation.png' % accession.replace(".", "_"))

class SavitzkyGolayDataSmoother:
    """Smooth data using the Savitzky-Golay technique from:

    http://www.dalkescientific.com/writings/NBN/plotting.html
    """
    def __init__(self, window_size):
        self._window_size = window_size
        if self._window_size%2 != 1:
            raise TypeError("smoothing requires an odd number of weights")

    def half_window(self):
        return (self._window_size-1)/2

    def smooth_values(self, values):
        half_window = (self._window_size-1)/2
        weights = self.savitzky_golay_weights(self._window_size)
        weights = [w*100.0 for w in weights]

        # Precompute the offset values for better performance.
        offsets = range(-half_window, half_window+1)
        offset_data = zip(offsets, weights)

        # normalize the weights in case the sum != 1
        total_weight = sum(weights)

        weighted_values = []
        for i in range(half_window, len(values)-half_window):
            weighted_value = 0.0
            for offset, weight in offset_data:
                weighted_value += weight*values[i+offset]
            weighted_values.append(weighted_value / total_weight)

        return weighted_values

    def savitzky_golay(self, window_size=None, order=2):
        if window_size is None:
            window_size = order + 2

        if window_size % 2 != 1 or window_size < 1:
            raise TypeError("window size must be a positive odd number")
        if window_size < order + 2:
            raise TypeError("window size is too small for the polynomial")

        # A second order polynomial has 3 coefficients
        order_range = range(order+1)
        half_window = (window_size-1)//2
        B = numpy.array(
            [ [k**i for i in order_range] for k in range(-half_window, half_window+1)] )

        #           -1
        # [  T     ]      T
        # [ B  * B ]  *  B
        M = numpy.dot(
               numpy.linalg.inv(numpy.dot(numpy.transpose(B), B)),
               numpy.transpose(B)
               )
        return M

    def savitzky_golay_weights(self, window_size=None, order=2, derivative=0):
        # The weights are in the first row
        # The weights for the 1st derivatives are in the second, etc.
        return self.savitzky_golay(window_size, order)[derivative]

class BlastConservationCalculator:
    """Calculate conservation across a protein from a BLAST record.
    """
    def __init__(self, matrix_name="blosum62"):
        """Initialize with the name of a substitution matrix for comparisons.
        """
        self._subs_mat = getattr(MatrixInfo, matrix_name)
        self._no_use_thresh = 0.95

    def conservation_dict(self, blast_rec):
        """Get dictionary containing substitution scores based on BLAST HSPs.
        """
        cons_dict = {}
        rec_size = int(blast_rec.query_letters)
        for base_index in range(rec_size):
            cons_dict[base_index] = []
        for align in blast_rec.alignments:
            for hsp in align.hsps:
                if (float(hsp.identities) / float(rec_size) <=
                        self._no_use_thresh):
                    cons_dict = self._add_hsp_conservation(hsp, cons_dict)
        return cons_dict

    def _add_hsp_conservation(self, hsp, cons_dict):
        """Add conservation information from an HSP BLAST alignment.
        """
        start_index = int(hsp.query_start) - 1
        hsp_index = 0
        for q_index in range(len(hsp.query)):
            if (hsp.query[q_index] != '-'):
                if (hsp.sbjct[q_index] != '-'):
                    try:
                        sub_val = self._subs_mat[(hsp.query[q_index],
                                                  hsp.sbjct[q_index])]
                    except KeyError:
                        sub_val = self._subs_mat[(hsp.sbjct[q_index],
                                                  hsp.query[q_index])]
                    cons_dict[start_index + hsp_index].append(sub_val)
                hsp_index += 1
        return cons_dict

class NCBIManager:
    """Manage interactions with NCBI through Biopython
    """
    def __init__(self, cache_dir):
        self._cache_dir = cache_dir
        if not(os.path.exists(cache_dir)):
            os.makedirs(cache_dir)

    def search_for_gi(self, uniprot_id, db_name):
        """Find the NCBI GI number corresponding to the given input ID.
        """
        handle = Entrez.esearch(db=db_name, term=uniprot_id)
        record = Entrez.read(handle)
        ids = record["IdList"]
        if len(ids) == 0:
            raise ValueError("Not found in NCBI: %s" % ids)
        return ids[0]

    def remote_blast(self, search_gi, blast_method):
        """Perform a BLAST against the NCBI server, returning the record.
        """
        out_file = os.path.join(self._cache_dir, "%s_%s_blo.xml" % (blast_method,
            search_gi))
        if not os.path.exists(out_file):
            blast_handle = NCBIWWW.qblast(blast_method, "nr", search_gi)
            with open(out_file, 'w') as out_handle:
                for line in blast_handle:
                    out_handle.write(line)
            blast_handle.close()
        with open(out_file) as in_handle:
            rec_it = NCBIXML.parse(in_handle)
            return rec_it.next()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Incorrect arguments"
        print __doc__
        sys.exit()
    main(sys.argv[1])

########NEW FILE########
