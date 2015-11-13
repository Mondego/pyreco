__FILENAME__ = dbsnp
"""Download variation data from dbSNP and install within directory structure.

Uses Broad's GATK resource bundles:

 http://www.broadinstitute.org/gsa/wiki/index.php/GATK_resource_bundle

Retrieves dbSNP plus training data for variant recalibration:
  - dbsnp_132.hg19.vcf.gz
  - hapmap_3.3.hg19.sites.vcf
  - 1000G_omni2.5.hg19.sites.vcf
  - Mills_and_1000G_gold_standard.indels.hg19.sites.vcf

For MuTect and cancer calling:
  - cosmic

For structural variant calling and SNP/indel filtering
  - low complexity regions
  - centromere and telomere regions
"""
import os

from fabric.api import env
from fabric.contrib.files import cd

from cloudbio.custom import shared

def download_dbsnp(genomes, bundle_version, dbsnp_version):
    """Download and install dbSNP variation data for supplied genomes.
    """
    folder_name = "variation"
    genome_dir = os.path.join(env.data_files, "genomes")
    for (orgname, gid, manager) in ((o, g, m) for (o, g, m) in genomes
                                    if m.config.get("dbsnp", False)):
        vrn_dir = os.path.join(genome_dir, orgname, gid, folder_name)
        if not env.safe_exists(vrn_dir):
            env.safe_run('mkdir -p %s' % vrn_dir)
        with cd(vrn_dir):
            if gid in ["GRCh37", "hg19"]:
                _dbsnp_human(env, gid, manager, bundle_version, dbsnp_version)
            elif gid in ["mm10", "canFam3"]:
                _dbsnp_custom(env, gid)

def _dbsnp_custom(env, gid):
    """Retrieve resources for dbsnp builds from custom S3 biodata bucket.
    """
    remote_dir = "https://s3.amazonaws.com/biodata/variants/"
    files = {"mm10": ["mm10-dbSNP-2013-09-12.vcf.gz"],
             "canFam3": ["canFam3-dbSNP-2014-05-10.vcf.gz"]}
    for f in files[gid]:
        for ext in ["", ".tbi"]:
            fname = f + ext
            if not env.safe_exists(fname):
                shared._remote_fetch(env, "%s%s" % (remote_dir, fname))

def _dbsnp_human(env, gid, manager, bundle_version, dbsnp_version):
    """Retrieve resources for human variant analysis from Broad resource bundles.
    """
    to_download = ["dbsnp_{ver}".format(ver=dbsnp_version),
                   "hapmap_3.3",
                   "1000G_omni2.5",
                   "1000G_phase1.snps.high_confidence",
                   "Mills_and_1000G_gold_standard.indels"]
    for dl_name in to_download:
        for ext in [""]:
            _download_broad_bundle(manager.dl_name, bundle_version, dl_name, ext)
    _download_cosmic(gid)
    _download_repeats(gid)
    # XXX Wait to get this by default until it is used more widely
    #_download_background_vcf(gid)

def _download_broad_bundle(gid, bundle_version, name, ext):
    broad_fname = "{name}.{gid}.vcf{ext}".format(gid=gid, name=name, ext=ext)
    fname = broad_fname.replace(".{0}".format(gid), "").replace(".sites", "") + ".gz"
    base_url = "ftp://gsapubftp-anonymous:@ftp.broadinstitute.org/bundle/" + \
               "{bundle}/{gid}/{fname}.gz".format(
                   bundle=bundle_version, fname=broad_fname, gid=gid)
    # compress and prepare existing uncompressed versions
    if env.safe_exists(fname.replace(".vcf.gz", ".vcf")):
        env.safe_run("bgzip %s" % fname.replace(".vcf.gz", ".vcf"))
        env.safe_run("tabix -f -p vcf %s" % fname)
    # otherwise, download and bgzip and tabix index
    if not env.safe_exists(fname):
        out_file = shared._remote_fetch(env, base_url, allow_fail=True)
        if out_file:
            env.safe_run("gunzip -c %s | bgzip -c > %s" % (out_file, fname))
            env.safe_run("tabix -f -p vcf %s" % fname)
            env.safe_run("rm -f %s" % out_file)
        else:
            env.logger.warn("dbSNP resources not available for %s" % gid)
    # clean up old files
    for ext in [".vcf", ".vcf.idx"]:
        if env.safe_exists(fname.replace(".vcf.gz", ext)):
            env.safe_run("rm -f %s" % (fname.replace(".vcf.gz", ext)))
    return fname

def _download_cosmic(gid):
    """Prepared versions of COSMIC, pre-sorted and indexed.
    utils/prepare_cosmic.py handles the work of creating the VCFs from standard
    COSMIC resources.
    """
    base_url = "https://s3.amazonaws.com/biodata/variants"
    version = "v68"
    supported = ["hg19", "GRCh37"]
    if gid in supported:
        url = "%s/cosmic-%s-%s.vcf.gz" % (base_url, version, gid)
        fname = os.path.basename(url)
        if not env.safe_exists(fname):
            shared._remote_fetch(env, url)
        if not env.safe_exists(fname + ".tbi"):
            shared._remote_fetch(env, url + ".tbi")

def _download_background_vcf(gid):
    """Download background file of variant to use in calling.
    """
    base_url = "https://s3.amazonaws.com/biodata/variants"
    base_name = "background-diversity-1000g.vcf"
    if gid in ["GRCh37"] and not env.safe_exists("{0}.gz".format(base_name)):
        for ext in ["gz", "gz.tbi"]:
            shared._remote_fetch(env, "{0}/{1}.{2}".format(base_url, base_name, ext))

def _download_repeats(gid):
    _download_sv_repeats(gid)
    _download_lcrs(gid)

def _download_sv_repeats(gid):
    """Retrieve telomere and centromere exclusion regions for structural variant calling.
    From Delly: https://github.com/tobiasrausch/delly
    """
    mere_url = "https://raw.githubusercontent.com/chapmanb/delly/master/human.hg19.excl.tsv"
    out_file = "sv_repeat_telomere_centromere.bed"
    if not env.safe_exists(out_file):
        def _select_by_gid(env, orig_file):
            if gid == "hg19":
                env.safe_run("grep ^chr %s > %s" % (orig_file, out_file))
            else:
                assert gid == "GRCh37"
                env.safe_run("grep -v ^chr %s > %s" % (orig_file, out_file))
            return out_file
        shared._remote_fetch(env, mere_url, fix_fn=_select_by_gid)

def _download_lcrs(gid):
    """Retrieve low complexity regions from Heng Li's variant analysis paper.
    """
    lcr_url = "https://github.com/lh3/varcmp/raw/master/scripts/LCR-hs37d5.bed.gz"
    out_file = "LCR.bed.gz"
    if not env.safe_exists(out_file):
        def _fix_chrom_names(env, orig_file):
            if gid == "hg19":
                convert_cmd = "| grep -v ^GL | grep -v ^NC | grep -v ^hs | sed 's/^/chr/'"
            else:
                assert gid == "GRCh37"
                convert_cmd = ""
            env.safe_run("zcat %s %s | bgzip -c > %s" % (orig_file, convert_cmd, out_file))
            return out_file
        shared._remote_fetch(env, lcr_url, fix_fn=_fix_chrom_names)
        env.safe_run("tabix -p vcf -f %s" % out_file)

########NEW FILE########
__FILENAME__ = galaxy
"""Retrieve indexed genomes using Galaxy's rsync server resources.

http://wiki.galaxyproject.org/Admin/Data%20Integration
"""
from xml.etree import ElementTree

from fabric.api import *
from fabric.contrib.files import *

# ## Compatibility definitions

server = "rsync://datacache.g2.bx.psu.edu"

index_map = {"bowtie": "bowtie_index",
             "bowtie2": "bowtie2_index",
             "bwa": "bwa_index",
             "novoalign": "novoalign_index",
             "ucsc": "seq",
             "seq": "sam_index"}

org_remap = {"phix": "phiX",
             "GRCh37": "hg_g1k_v37",
             "araTha_tair9": "Arabidopsis_thaliana_TAIR9",
             "araTha_tair10": "Arabidopsis_thaliana_TAIR10",
             "WS210": "ce10",
             "WS220": "ce10"}

galaxy_subdirs = ["", "/microbes"]

# ## Galaxy location files

class LocCols(object):
    # Hold all possible .loc file column fields making sure the local
    # variable names match column names in Galaxy's tool_data_table_conf.xml
    def __init__(self, config, dbkey, file_path):
        self.dbkey = dbkey
        self.path = file_path
        self.value = config.get("value", dbkey)
        self.name = config.get("name", dbkey)
        self.species = config.get('species', '')
        self.index = config.get('index', 'index')
        self.formats = config.get('index', 'fastqsanger')
        self.dbkey1 = config.get('index', dbkey)
        self.dbkey2 = config.get('index', dbkey)

def _get_tool_conf(tool_name):
    """
    Parse the tool_data_table_conf.xml from installed_files subfolder and extract
    values for the 'columns' tag and 'path' parameter for the 'file' tag, returning
    those as a dict.
    """
    tool_conf = {}
    tdtc = ElementTree.parse(env.tool_data_table_conf_file)
    tables = tdtc.getiterator('table')
    for t in tables:
        if tool_name in t.attrib.get('name', ''):
            tool_conf['columns'] = t.find('columns').text.replace(' ', '').split(',')
            tool_conf['file'] = t.find('file').attrib.get('path', '')
    return tool_conf

def _build_galaxy_loc_line(dbkey, file_path, config, prefix, tool_name):
    """Prepare genome information to write to a Galaxy *.loc config file.
    """
    if tool_name:
        str_parts = []
        tool_conf = _get_tool_conf(tool_name)
        loc_cols = LocCols(config, dbkey, file_path)
        # Compose the .loc file line as str_parts list by looking for column values
        # from the retrieved tool_conf (as defined in tool_data_table_conf.xml).
        # Any column values required but missing in the tool_conf are
        # supplemented by the defaults defined in LocCols class
        for col in tool_conf.get('columns', []):
            str_parts.append(config.get(col, getattr(loc_cols, col)))
    else:
        str_parts = [dbkey, file_path]
    if prefix:
        str_parts.insert(0, prefix)
    return str_parts

def update_loc_file(ref_file, line_parts):
    """Add a reference to the given genome to the base index file.
    """
    if getattr(env, "galaxy_home", None) is not None:
        tools_dir = os.path.join(env.galaxy_home, "tool-data")
        if not env.safe_exists(tools_dir):
            env.safe_run("mkdir -p %s" % tools_dir)
        dt_file = os.path.join(env.galaxy_home, "tool_data_table_conf.xml")
        if not env.safe_exists(dt_file):
            env.safe_put(env.tool_data_table_conf_file, dt_file)
        add_str = "\t".join(line_parts)
        with cd(tools_dir):
            if not env.safe_exists(ref_file):
                env.safe_run("touch %s" % ref_file)
            if not env.safe_contains(ref_file, add_str):
                env.safe_append(ref_file, add_str)

def prep_locs(gid, indexes, config):
    """Prepare Galaxy location files for all available indexes.
    """
    for ref_index_file, cur_index, prefix, tool_name in [
            ("sam_fa_indices.loc", indexes.get("seq", None), "", 'sam_fa_indexes'),
            ("picard_index.loc", indexes.get("seq", None), "", "picard_indexes"),
            ("gatk_sorted_picard_index.loc", indexes.get("seq", None), "", "gatk_picard_indexes"),
            ("alignseq.loc", indexes.get("ucsc", None), "seq", None),
            ("twobit.loc", indexes.get("ucsc", None), "", None),
            ("bowtie_indices.loc", indexes.get("bowtie", None), "", 'bowtie_indexes'),
            ("bowtie2_indices.loc", indexes.get("bowtie2", None), "", 'bowtie2_indexes'),
            ("mosaik_index.loc", indexes.get("mosaik", None), "", "mosaik_indexes"),
            ("bwa_index.loc", indexes.get("bwa", None), "", 'bwa_indexes'),
            ("novoalign_indices.loc", indexes.get("novoalign", None), "", "novoalign_indexes")]:
        if cur_index:
            str_parts = _build_galaxy_loc_line(gid, cur_index, config, prefix, tool_name)
            update_loc_file(ref_index_file, str_parts)

# ## Finalize downloads

def index_picard(ref_file):
    """Provide a Picard style dict index file for a reference genome.
    """
    index_file = "%s.dict" % os.path.splitext(ref_file)[0]
    dirs_to_try = ["%s/share/java/picard" % env.system_install,
                   getattr(env, "picard_home", None)]
    picard_jar = None
    for dname in dirs_to_try:
        if dname:
            test_jar = os.path.join(dname, "CreateSequenceDictionary.jar")
            if env.safe_exists(test_jar):
                picard_jar = test_jar
                break
    if picard_jar and not env.safe_exists(index_file):
        env.safe_run("java -Xms500m -Xmx1g -jar {jar} REFERENCE={ref} OUTPUT={out}".format(
            jar=picard_jar, ref=ref_file, out=index_file))
    return index_file

def _finalize_index_seq(fname):
    """Convert UCSC 2bit file into fasta file.
    """
    out_fasta = fname + ".fa"
    if not env.safe_exists(out_fasta):
        env.safe_run("twoBitToFa {base}.2bit {out}".format(
            base=fname, out=out_fasta))

finalize_fns = {"ucsc": _finalize_index_seq,
                "seq": index_picard}

def _finalize_index(idx, fname):
    """Perform final processing on an rsync'ed index file if necessary.
    """
    finalize_fn = finalize_fns.get(idx)
    if finalize_fn:
        finalize_fn(fname)

# ## Retrieve data from Galaxy

def rsync_genomes(genome_dir, genomes, genome_indexes):
    """Top level entry point to retrieve rsync'ed indexes from Galaxy.
    """
    for gid in (x[1] for x in genomes):
        galaxy_gid = org_remap.get(gid, gid)
        indexes = _get_galaxy_genomes(galaxy_gid, genome_dir, genomes, genome_indexes)
        _finalize_index("ucsc", indexes["ucsc"])
        for idx, fname in indexes.iteritems():
            _finalize_index(idx, fname)
        prep_locs(galaxy_gid, indexes, {})

def _get_galaxy_genomes(gid, genome_dir, genomes, genome_indexes):
    """Retrieve the provided genomes and indexes from Galaxy rsync.
    """
    out = {}
    org_dir = os.path.join(genome_dir, gid)
    if not env.safe_exists(org_dir):
        env.safe_run('mkdir -p %s' % org_dir)
    for idx in genome_indexes:
        galaxy_index_name = index_map.get(idx)
        index_file = None
        if galaxy_index_name:
            index_file = _rsync_genome_index(gid, galaxy_index_name, org_dir)
        if index_file:
            out[idx] = index_file
        else:
            print "Galaxy does not support {0} for {1}".format(idx, gid)
    return out

def _rsync_genome_index(gid, idx, org_dir):
    """Retrieve index for a genome from rsync server, returning path to files.
    """
    idx_dir = os.path.join(org_dir, idx)
    if not env.safe_exists(idx_dir):
        org_rsync = None
        for subdir in galaxy_subdirs:
            test_rsync = "{server}/indexes{subdir}/{gid}/{idx}/".format(
                server=server, subdir=subdir, gid=gid, idx=idx)
            with quiet():
                check_dir = env.safe_run("rsync --list-only {server}".format(server=test_rsync))
            if check_dir.succeeded:
                org_rsync = test_rsync
                break
        if org_rsync is None:
            raise ValueError("Could not find genome %s on Galaxy rsync" % gid)
        with quiet():
            check_dir = env.safe_run("rsync --list-only {server}".format(server=org_rsync))
        if check_dir.succeeded:
            if not env.safe_exists(idx_dir):
                env.safe_run('mkdir -p %s' % idx_dir)
            with cd(idx_dir):
                env.safe_run("rsync -avzP {server} {idx_dir}".format(server=org_rsync,
                                                            idx_dir=idx_dir))
    if env.safe_exists(idx_dir):
        with quiet():
            has_fa_ext = env.safe_run("ls {idx_dir}/{gid}.fa*".format(idx_dir=idx_dir,
                                                                      gid=gid))
        ext = ".fa" if (has_fa_ext.succeeded and idx not in ["seq"]) else ""
        return os.path.join(idx_dir, gid + ext)

########NEW FILE########
__FILENAME__ = genomes
"""Download and install structured genome data and aligner index files.

Downloads prepared FASTA, indexes for aligners like BWA, Bowtie and novoalign
and other genome data in automated pipelines. Specify the genomes and aligners
to use in an input biodata.yaml configuration file.

The main targets are fabric functions:

  - install_data -- Install biological data from scratch, including indexing genomes.
  - install_data_s3 -- Install biological data, downloading pre-computed indexes from S3.
  - upload_s3 -- Upload created indexes to biodata S3 bucket.

"""
import os
import operator
import socket
import subprocess
from contextlib import contextmanager

from fabric.api import *
from fabric.contrib.files import *
from fabric.context_managers import path
try:
    import yaml
except ImportError:
    yaml = None
try:
    import boto
except ImportError:
    boto = None

from cloudbio.biodata import galaxy
from cloudbio.biodata.dbsnp import download_dbsnp
from cloudbio.biodata.rnaseq import download_transcripts
from cloudbio.custom import shared

# -- Configuration for genomes to download and prepare

class _DownloadHelper:
    def __init__(self):
        self.config = {}

    def ucsc_name(self):
        return None

    def _exists(self, fname, seq_dir):
        """Check if a file exists in either download or final destination.
        """
        return env.safe_exists(fname) or env.safe_exists(os.path.join(seq_dir, fname))

class UCSCGenome(_DownloadHelper):
    def __init__(self, genome_name, dl_name=None):
        _DownloadHelper.__init__(self)
        self.data_source = "UCSC"
        self._name = genome_name
        self.dl_name = dl_name if dl_name is not None else genome_name
        self._url = "ftp://hgdownload.cse.ucsc.edu/goldenPath/%s/bigZips" % \
                genome_name

    def ucsc_name(self):
        return self._name

    def _karyotype_sort(self, xs):
        """Sort reads in karyotypic order to work with GATK's defaults.
        """
        def karyotype_keyfn(x):
            base = os.path.splitext(os.path.basename(x))[0]
            if base.startswith("chr"):
                base = base[3:]
            parts = base.split("_")
            try:
                parts[0] =  int(parts[0])
            except ValueError:
                pass
            # unplaced at the very end
            if parts[0] == "Un":
                parts.insert(0, "z")
            # mitochondrial special case -- after X/Y
            elif parts[0] in ["M", "MT"]:
                parts.insert(0, "x")
            # sort random and extra chromosomes after M
            elif len(parts) > 1:
                parts.insert(0, "y")
            return parts
        return sorted(xs, key=karyotype_keyfn)

    def _split_multifasta(self, fasta_file):
        chrom = ""
        file_handle = None
        file_names = []
        out_dir = os.path.dirname(fasta_file)
        with open(fasta_file) as in_handle:
            for line in in_handle:
                if line.startswith(">"):
                    chrom = line.split(">")[1].strip()
                    file_handle.close() if file_handle else None
                    file_names.append(chrom + ".fa")
                    file_handle = open(os.path.join(out_dir, chrom + ".fa"), "w")
                    file_handle.write(line)
                else:
                    file_handle.write(line)
        file_handle.close()
        return file_names


    def download(self, seq_dir):
        zipped_file = None
        genome_file = "%s.fa" % self._name
        if not self._exists(genome_file, seq_dir):
            prep_dir = "seq_prep"
            env.safe_run("mkdir -p %s" % prep_dir)
            with cd(prep_dir):
                zipped_file = self._download_zip(seq_dir)
                if zipped_file.endswith(".tar.gz"):
                    env.safe_run("tar -xzpf %s" % zipped_file)
                elif zipped_file.endswith(".zip"):
                    env.safe_run("unzip %s" % zipped_file)
                elif zipped_file.endswith(".gz"):
                    if not env.safe_exists("out.fa"):
                        env.safe_run("gunzip -c %s > out.fa" % zipped_file)
                else:
                    raise ValueError("Do not know how to handle: %s" % zipped_file)
                tmp_file = genome_file.replace(".fa", ".txt")
                result = env.safe_run_output("find `pwd` -name '*.fa'")
                result = [x.strip() for x in result.split("\n")]
                if len(result) == 1:
                    result = self._split_multifasta(result[0])
                result = self._karyotype_sort(result)
                env.safe_run("cat %s > %s" % (" ".join(result), tmp_file))
                env.safe_run("rm -f *.fa")
                env.safe_run("mv %s %s" % (tmp_file, genome_file))
                zipped_file = os.path.join(prep_dir, zipped_file)
                genome_file = os.path.join(prep_dir, genome_file)
        return genome_file, [zipped_file]

    def _download_zip(self, seq_dir):
        for zipped_file in ["chromFa.tar.gz", "%s.fa.gz" % self._name,
                            "chromFa.zip"]:
            if not self._exists(zipped_file, seq_dir):
                result = shared._remote_fetch(env, "%s/%s" % (self._url, zipped_file), allow_fail=True)
                if result:
                    break
            else:
                break
        return zipped_file

class NCBIRest(_DownloadHelper):
    """Retrieve files using the TogoWS REST server pointed at NCBI.
    """
    def __init__(self, name, refs, dl_name=None):
        _DownloadHelper.__init__(self)
        self.data_source = "NCBI"
        self._name = name
        self._refs = refs
        self.dl_name = dl_name if dl_name is not None else name
        self._base_url = "http://togows.dbcls.jp/entry/ncbi-nucleotide/%s.fasta"

    def download(self, seq_dir):
        genome_file = "%s.fa" % self._name
        if not self._exists(genome_file, seq_dir):
            for ref in self._refs:
                shared._remote_fetch(env, self._base_url % ref)
                env.safe_run("ls -l")
                env.safe_sed('%s.fasta' % ref, '^>.*$', '>%s' % ref, '1')
            tmp_file = genome_file.replace(".fa", ".txt")
            env.safe_run("cat *.fasta > %s" % tmp_file)
            env.safe_run("rm -f *.fasta")
            env.safe_run("rm -f *.bak")
            env.safe_run("mv %s %s" % (tmp_file, genome_file))
        return genome_file, []

class VectorBase(_DownloadHelper):
    """Retrieve genomes from VectorBase) """

    def __init__(self, name, genus, species, strain, release, assembly_types):
        _DownloadHelper.__init__(self)
        self._name = name
        self.data_source = "VectorBase"
        self._base_url = ("http://www.vectorbase.org/sites/default/files/ftp/"
                     "downloads/")
        _base_file = ("{genus}-{species}-{strain}_{assembly}"
                      "_{release}.fa.gz")
        self._to_get = []
        for assembly in assembly_types:
            self._to_get.append(_base_file.format(**locals()))

    def download(self, seq_dir):
        print os.getcwd()
        genome_file = "%s.fa" % self._name
        for fn in self._to_get:
            url = self._base_url + fn
            if not self._exists(fn, seq_dir):
                shared._remote_fetch(env, url)
                env.safe_run("gunzip -c %s >> %s" % (fn, genome_file))
        return genome_file, []


class EnsemblGenome(_DownloadHelper):
    """Retrieve genome FASTA files from Ensembl.

    ftp://ftp.ensemblgenomes.org/pub/plants/release-3/fasta/
    arabidopsis_thaliana/dna/Arabidopsis_thaliana.TAIR9.55.dna.toplevel.fa.gz
    ftp://ftp.ensembl.org/pub/release-56/fasta/
    caenorhabditis_elegans/dna/Caenorhabditis_elegans.WS200.56.dna.toplevel.fa.gz
    """
    def __init__(self, ensembl_section, release_number, release2, organism,
            name, convert_to_ucsc=False, dl_name = None):
        _DownloadHelper.__init__(self)
        self.data_source = "Ensembl"
        if ensembl_section == "standard":
            url = "ftp://ftp.ensembl.org/pub/"
        else:
            url = "ftp://ftp.ensemblgenomes.org/pub/%s/" % ensembl_section
        url += "release-%s/fasta/%s/dna/" % (release_number, organism.lower())
        self._url = url
        release2 = ".%s" % release2 if release2 else ""
        self._get_file = "%s.%s%s.dna.toplevel.fa.gz" % (organism, name,
                release2)
        self._name = name
        self.dl_name = dl_name if dl_name is not None else name
        self._convert_to_ucsc = convert_to_ucsc

    def download(self, seq_dir):
        genome_file = "%s.fa" % self._name
        if not self._exists(self._get_file, seq_dir):
            shared._remote_fetch(env, "%s%s" % (self._url, self._get_file))
        if not self._exists(genome_file, seq_dir):
            env.safe_run("gunzip -c %s > %s" % (self._get_file, genome_file))
        if self._convert_to_ucsc:
            #run("sed s/ / /g %s" % genome_file)
            raise NotImplementedError("Replace with chr")
        return genome_file, [self._get_file]

class BroadGenome(_DownloadHelper):
    """Retrieve genomes organized and sorted by Broad for use with GATK.

    Uses the UCSC-name compatible versions of the GATK bundles.
    """
    def __init__(self, name, bundle_version, target_fasta, dl_name=None):
        _DownloadHelper.__init__(self)
        self.data_source = "UCSC"
        self._name = name
        self.dl_name = dl_name if dl_name is not None else name
        self._target = target_fasta
        self._ftp_url = "ftp://gsapubftp-anonymous:@ftp.broadinstitute.org/bundle/" + \
                        "{ver}/{org}/".format(ver=bundle_version, org=self.dl_name)

    def download(self, seq_dir):
        org_file = "%s.fa" % self._name
        if not self._exists(org_file, seq_dir):
            shared._remote_fetch(env, "%s%s.gz" % (self._ftp_url, self._target))
            env.safe_run("gunzip %s.gz" % self._target)
            env.safe_run("mv %s %s" % (self._target, org_file))
        return org_file, []

BROAD_BUNDLE_VERSION = "2.8"
DBSNP_VERSION = "138"

GENOMES_SUPPORTED = [
           ("phiX174", "phix", NCBIRest("phix", ["NC_001422.1"])),
           ("Scerevisiae", "sacCer2", UCSCGenome("sacCer2")),
           ("Mmusculus", "mm10", UCSCGenome("mm10")),
           ("Mmusculus", "mm9", UCSCGenome("mm9")),
           ("Mmusculus", "mm8", UCSCGenome("mm8")),
           ("Hsapiens", "hg18", BroadGenome("hg18", BROAD_BUNDLE_VERSION,
                                            "Homo_sapiens_assembly18.fasta")),
           ("Hsapiens", "hg19", BroadGenome("hg19", BROAD_BUNDLE_VERSION,
                                            "ucsc.hg19.fasta")),
           ("Hsapiens", "GRCh37", BroadGenome("GRCh37", BROAD_BUNDLE_VERSION,
                                              "human_g1k_v37.fasta", "b37")),
           ("Rnorvegicus", "rn5", UCSCGenome("rn5")),
           ("Rnorvegicus", "rn4", UCSCGenome("rn4")),
           ("Xtropicalis", "xenTro2", UCSCGenome("xenTro2")),
           ("Athaliana", "araTha_tair9", EnsemblGenome("plants", "6", "",
               "Arabidopsis_thaliana", "TAIR9")),
           ("Dmelanogaster", "dm3", UCSCGenome("dm3")),
           ("Celegans", "WS210", EnsemblGenome("standard", "60", "60",
               "Caenorhabditis_elegans", "WS210")),
           ("Mtuberculosis_H37Rv", "mycoTube_H37RV", NCBIRest("mycoTube_H37RV",
               ["NC_000962"])),
           ("Msmegmatis", "92", NCBIRest("92", ["NC_008596.1"])),
           ("Paeruginosa_UCBPP-PA14", "386", NCBIRest("386", ["CP000438.1"])),
           ("Ecoli", "eschColi_K12", NCBIRest("eschColi_K12", ["U00096.2"])),
           ("Amellifera_Honeybee", "apiMel3", UCSCGenome("apiMel3")),
           ("Cfamiliaris_Dog", "canFam3", UCSCGenome("canFam3")),
           ("Cfamiliaris_Dog", "canFam2", UCSCGenome("canFam2")),
           ("Drerio_Zebrafish", "Zv9", UCSCGenome("danRer7")),
           ("Ecaballus_Horse", "equCab2", UCSCGenome("equCab2")),
           ("Fcatus_Cat", "felCat3", UCSCGenome("felCat3")),
           ("Ggallus_Chicken", "galGal3", UCSCGenome("galGal3")),
           ("Tguttata_Zebra_finch", "taeGut1", UCSCGenome("taeGut1")),
           ("Aalbimanus", "AalbS1", VectorBase("AalbS1", "Anopheles",
                                               "albimanus", "STECLA",
                                               "AalbS1", ["SCAFFOLDS"])),
           ("Agambiae", "AgamP3", VectorBase("AgamP3", "Anopheles",
                                               "gambiae", "PEST",
                                               "AgamP3", ["CHROMOSOMES"])),]


GENOME_INDEXES_SUPPORTED = ["bowtie", "bowtie2", "bwa", "maq", "novoalign", "novoalign-cs",
                            "ucsc", "mosaik", "star"]
DEFAULT_GENOME_INDEXES = ["seq"]

# -- Fabric instructions

def _check_version():
    version = env.version
    if int(version.split(".")[0]) < 1:
        raise NotImplementedError("Please install fabric version 1 or better")

def install_data(config_source, approaches=None):
    """Main entry point for installing useful biological data.
    """
    PREP_FNS = {"s3": _download_s3_index,
                "raw": _prep_raw_index}
    if approaches is None: approaches = ["raw"]
    ready_approaches = []
    for approach in approaches:
        ready_approaches.append((approach, PREP_FNS[approach]))
    _check_version()
    # Append a potentially custom system install path to PATH so tools are found
    with path(os.path.join(env.system_install, 'bin')):
        genomes, genome_indexes, config = _get_genomes(config_source)
        genome_indexes += [x for x in DEFAULT_GENOME_INDEXES if x not in genome_indexes]
        _make_genome_directories(env, genomes)
        download_transcripts(genomes, env)
        _prep_genomes(env, genomes, genome_indexes, ready_approaches)
        _install_additional_data(genomes, genome_indexes, config)

def install_data_s3(config_source):
    """Install data using pre-existing genomes present on Amazon s3.
    """
    _check_version()
    genomes, genome_indexes, config = _get_genomes(config_source)
    genome_indexes += [x for x in DEFAULT_GENOME_INDEXES if x not in genome_indexes]
    _make_genome_directories(env, genomes)
    download_transcripts(genomes, env)
    _download_genomes(genomes, genome_indexes)
    _install_additional_data(genomes, genome_indexes, config)

def install_data_rsync(config_source):
    """Install data using pre-existing genomes from Galaxy rsync servers.
    """
    _check_version()
    genomes, genome_indexes, config = _get_genomes(config_source)
    genome_indexes += [x for x in DEFAULT_GENOME_INDEXES if x not in genome_indexes]
    # Galaxy stores FASTAs in ucsc format and generates on the fly
    if "ucsc" not in genome_indexes:
        genome_indexes.append("ucsc")
    genome_dir = _make_genome_dir()
    galaxy.rsync_genomes(genome_dir, genomes, genome_indexes)

def upload_s3(config_source):
    """Upload prepared genome files by identifier to Amazon s3 buckets.
    """
    if boto is None:
        raise ImportError("install boto to upload to Amazon s3")
    if env.host != "localhost" and not env.host.startswith(socket.gethostname()):
        raise ValueError("Need to run S3 upload on a local machine")
    _check_version()
    genomes, genome_indexes, config = _get_genomes(config_source)
    genome_indexes += [x for x in DEFAULT_GENOME_INDEXES if x not in genome_indexes]
    _data_ngs_genomes(genomes, genome_indexes)
    _upload_genomes(genomes, genome_indexes)


def _install_additional_data(genomes, genome_indexes, config):
    download_dbsnp(genomes, BROAD_BUNDLE_VERSION, DBSNP_VERSION)
    for custom in (config.get("custom") or []):
        _prep_custom_genome(custom, genomes, genome_indexes, env)
    if config.get("install_liftover", False):
        lift_over_genomes = [g.ucsc_name() for (_, _, g) in genomes if g.ucsc_name()]
        _data_liftover(lift_over_genomes)
    if config.get("install_uniref", False):
        _data_uniref()

def _get_genomes(config_source):
    if isinstance(config_source, dict):
        config = config_source
    else:
        if yaml is None:
            raise ImportError("install yaml to read configuration from %s" % config_source)
        with open(config_source) as in_handle:
            config = yaml.load(in_handle)
    genomes = []
    genomes_config = config["genomes"] or []
    env.logger.info("List of genomes to get (from the config file at '{0}'): {1}"\
        .format(config_source, ', '.join(g.get('name', g["dbkey"]) for g in genomes_config)))
    for g in genomes_config:
        ginfo = None
        for info in GENOMES_SUPPORTED:
            if info[1] == g["dbkey"]:
                ginfo = info
                break
        assert ginfo is not None, "Did not find download info for %s" % g["dbkey"]
        name, gid, manager = ginfo
        manager.config = g
        genomes.append((name, gid, manager))
    indexes = config["genome_indexes"] or []
    return genomes, indexes, config

# ## Decorators and context managers

def _if_installed(pname):
    """Run if the given program name is installed.
    """
    def argcatcher(func):
        def decorator(*args, **kwargs):
            if not shared._executable_not_on_path(pname):
                return func(*args, **kwargs)
        return decorator
    return argcatcher

# ## Generic preparation functions

def _make_genome_dir():
    genome_dir = os.path.join(env.data_files, "genomes")
    if not env.safe_exists(genome_dir):
        with settings(warn_only=True):
            result = env.safe_run_output("mkdir -p %s" % genome_dir)
    else:
        result = None
    if result is not None and result.failed:
        env.safe_sudo("mkdir -p %s" % genome_dir)
        env.safe_sudo("chown -R %s %s" % (env.user, genome_dir))
    return genome_dir


def _make_genome_directories(env, genomes):
    genome_dir = _make_genome_dir()
    for (orgname, gid, manager) in genomes:
        org_dir = os.path.join(genome_dir, orgname, gid)
        if not env.safe_exists(org_dir):
            env.safe_run('mkdir -p %s' % org_dir)

def _prep_genomes(env, genomes, genome_indexes, retrieve_fns):
    """Prepare genomes with the given indexes, supporting multiple retrieval methods.
    """
    genome_dir = _make_genome_dir()
    for (orgname, gid, manager) in genomes:
        org_dir = os.path.join(genome_dir, orgname, gid)
        if not env.safe_exists(org_dir):
            env.safe_run('mkdir -p %s' % org_dir)
        for idx in genome_indexes:
            with cd(org_dir):
                if not env.safe_exists(idx):
                    finished = False
                    for method, retrieve_fn in retrieve_fns:
                        try:
                            retrieve_fn(env, manager, gid, idx)
                            finished = True
                            break
                        except KeyboardInterrupt:
                            raise
                        except:
                            env.logger.exception("Genome preparation method {0} failed, trying next".format(method))
                    if not finished:
                        raise IOError("Could not prepare index {0} for {1} by any method".format(idx, gid))
        ref_file = os.path.join(org_dir, "seq", "%s.fa" % gid)
        if not env.safe_exists(ref_file):
            ref_file = os.path.join(org_dir, "seq", "%s.fa" % manager._name)
        assert env.safe_exists(ref_file), ref_file
        cur_indexes = manager.config.get("indexes", genome_indexes)
        _index_to_galaxy(org_dir, ref_file, gid, cur_indexes, manager.config)

# ## Genomes index for next-gen sequencing tools

def _get_ref_seq(env, manager):
    """Check for or retrieve the reference sequence.
    """
    seq_dir = os.path.join(env.cwd, "seq")
    ref_file, base_zips = manager.download(seq_dir)
    ref_file = _move_seq_files(ref_file, base_zips, seq_dir)
    return ref_file

def _prep_raw_index(env, manager, gid, idx):
    """Prepare genome from raw downloads and indexes.
    """
    env.logger.info("Preparing genome {0} with index {1}".format(gid, idx))
    ref_file = _get_ref_seq(env, manager)
    get_index_fn(idx)(ref_file)

def _data_ngs_genomes(genomes, genome_indexes):
    """Download and create index files for next generation genomes.
    """
    genome_dir = _make_genome_dir()
    for organism, genome, manager in genomes:
        cur_dir = os.path.join(genome_dir, organism, genome)
        env.logger.info("Processing genome {0} and putting it to {1}"\
            .format(organism, cur_dir))
        if not env.safe_exists(cur_dir):
            env.safe_run('mkdir -p %s' % cur_dir)
        with cd(cur_dir):
            if hasattr(env, "remove_old_genomes") and env.remove_old_genomes:
                _clean_genome_directory()
            seq_dir = 'seq'
            ref_file, base_zips = manager.download(seq_dir)
            ref_file = _move_seq_files(ref_file, base_zips, seq_dir)
        cur_indexes = manager.config.get("indexes", genome_indexes)
        _index_to_galaxy(cur_dir, ref_file, genome, cur_indexes, manager.config)

def _index_to_galaxy(work_dir, ref_file, gid, genome_indexes, config):
    """Index sequence files and update associated Galaxy loc files.
    """
    indexes = {}
    with cd(work_dir):
        for idx in genome_indexes:
            index_file = get_index_fn(idx)(ref_file)
            if index_file:
                indexes[idx] = os.path.join(work_dir, index_file)
    galaxy.prep_locs(gid, indexes, config)

class CustomMaskManager:
    """Create a custom genome based on masking an existing genome.
    """
    def __init__(self, custom, config):
        assert custom.has_key("mask")
        self._custom = custom
        self.config = config

    def download(self, seq_dir):
        base_seq = os.path.join(os.pardir, self._custom["base"],
                                "seq", "{0}.fa".format(self._custom["base"]))
        assert env.safe_exists(base_seq)
        mask_file = os.path.basename(self._custom["mask"])
        ready_mask = apply("{0}-complement{1}".format, os.path.splitext(mask_file))
        out_fasta = "{0}.fa".format(self._custom["dbkey"])
        if not env.safe_exists(os.path.join(seq_dir, out_fasta)):
            if not env.safe_exists(mask_file):
                shared._remote_fetch(env, self._custom["mask"])
            if not env.safe_exists(ready_mask):
                env.safe_run("bedtools complement -i {i} -g {g}.fai > {o}".format(
                    i=mask_file, g=base_seq, o=ready_mask))
            if not env.safe_exists(out_fasta):
                env.safe_run("bedtools maskfasta -fi {fi} -bed {bed} -fo {fo}".format(
                    fi=base_seq, bed=ready_mask, fo=out_fasta))
        return out_fasta, [mask_file, ready_mask]

def _prep_custom_genome(custom, genomes, genome_indexes, env):
    """Prepare a custom genome derived from existing genome.
    Allows creation of masked genomes for specific purposes.
    """
    cur_org = None
    cur_manager = None
    for org, gid, manager in genomes:
        if gid == custom["base"]:
            cur_org = org
            cur_manager = manager
            break
    assert cur_org is not None
    _data_ngs_genomes([[cur_org, custom["dbkey"],
                        CustomMaskManager(custom, cur_manager.config)]],
                      genome_indexes)

def _clean_genome_directory():
    """Remove any existing sequence information in the current directory.
    """
    for dirname in GENOME_INDEXES_SUPPORTED + DEFAULT_GENOME_INDEXES:
        if env.safe_exists(dirname):
            env.safe_run("rm -rf %s" % dirname)

def _move_seq_files(ref_file, base_zips, seq_dir):
    if not env.safe_exists(seq_dir):
        env.safe_run('mkdir %s' % seq_dir)
    for move_file in [ref_file] + base_zips:
        if env.safe_exists(move_file):
            env.safe_run("mv %s %s" % (move_file, seq_dir))
    path, fname = os.path.split(ref_file)
    moved_ref = os.path.join(path, seq_dir, fname)
    assert env.safe_exists(moved_ref), moved_ref
    return moved_ref

# ## Indexing for specific aligners

def _index_w_command(dir_name, command, ref_file, pre=None, post=None, ext=None):
    """Low level function to do the indexing and paths with an index command.
    """
    index_name = os.path.splitext(os.path.basename(ref_file))[0]
    if ext is not None: index_name += ext
    full_ref_path = os.path.join(os.pardir, ref_file)
    if not env.safe_exists(dir_name):
        env.safe_run("mkdir %s" % dir_name)
        with cd(dir_name):
            if pre:
                full_ref_path = pre(full_ref_path)
            env.safe_run(command.format(ref_file=full_ref_path, index_name=index_name))
            if post:
                post(full_ref_path)
    return os.path.join(dir_name, index_name)

@_if_installed("faToTwoBit")
def _index_twobit(ref_file):
    """Index reference files using 2bit for random access.
    """
    dir_name = "ucsc"
    cmd = "faToTwoBit {ref_file} {index_name}"
    return _index_w_command(dir_name, cmd, ref_file)

def _index_bowtie(ref_file):
    dir_name = "bowtie"
    cmd = "bowtie-build -f {ref_file} {index_name}"
    return _index_w_command(dir_name, cmd, ref_file)

def _index_bowtie2(ref_file):
    dir_name = "bowtie2"
    cmd = "bowtie2-build {ref_file} {index_name}"
    out_suffix = _index_w_command(dir_name, cmd, ref_file)
    bowtie_link = os.path.join(os.path.dirname(ref_file), os.path.pardir,
                               out_suffix + ".fa")
    if not os.path.exists(bowtie_link):
        os.symlink(ref_file, bowtie_link)
    return out_suffix

def _index_bwa(ref_file):
    dir_name = "bwa"
    local_ref = os.path.split(ref_file)[-1]
    if not env.safe_exists(dir_name):
        env.safe_run("mkdir %s" % dir_name)
        with cd(dir_name):
            env.safe_run("ln -s %s" % os.path.join(os.pardir, ref_file))
            with settings(warn_only=True):
                result = env.safe_run("bwa index -a bwtsw %s" % local_ref)
            # work around a bug in bwa indexing for small files
            if result.failed:
                env.safe_run("bwa index %s" % local_ref)
            env.safe_run("rm -f %s" % local_ref)
    return os.path.join(dir_name, local_ref)

def _index_maq(ref_file):
    dir_name = "maq"
    cmd = "maq fasta2bfa {ref_file} {index_name}"
    def link_local(ref_file):
        local = os.path.basename(ref_file)
        env.safe_run("ln -s {0} {1}".format(ref_file, local))
        return local
    def rm_local(local_file):
        env.safe_run("rm -f {0}".format(local_file))
    return _index_w_command(dir_name, cmd, ref_file, pre=link_local, post=rm_local)

@_if_installed("novoindex")
def _index_novoalign(ref_file):
    dir_name = "novoalign"
    cmd = "novoindex {index_name} {ref_file}"
    return _index_w_command(dir_name, cmd, ref_file)

@_if_installed("novoalignCS")
def _index_novoalign_cs(ref_file):
    dir_name = "novoalign_cs"
    cmd = "novoindex -c {index_name} {ref_file}"
    return _index_w_command(dir_name, cmd, ref_file)

def _index_sam(ref_file):
    (ref_dir, local_file) = os.path.split(ref_file)
    with cd(ref_dir):
        if not env.safe_exists("%s.fai" % local_file):
            env.safe_run("samtools faidx %s" % local_file)
    galaxy.index_picard(ref_file)
    return ref_file

def _index_star(ref_file):
    (ref_dir, local_file) = os.path.split(ref_file)
    gtf_file = os.path.join(ref_dir, os.pardir, "rnaseq", "ref-transcripts.gtf")
    if not os.path.exists(gtf_file):
        print "%s not found, skipping creating the STAR index." % (gtf_file)
        return None
    dir_name = "star"
    cmd = ("STAR --genomeDir . --genomeFastaFiles {ref_file} "
           "--runMode genomeGenerate --sjdbOverhang 99 --sjdbGTFfile %s" % (gtf_file))
    return  _index_w_command(dir_name, cmd, ref_file)

@_if_installed("MosaikJump")
def _index_mosaik(ref_file):
    hash_size = 15
    dir_name = "mosaik"
    cmd = "MosaikBuild -fr {ref_file} -oa {index_name}"
    def create_jumpdb(ref_file):
        jmp_base = os.path.splitext(os.path.basename(ref_file))[0]
        dat_file = "{0}.dat".format(jmp_base)
        if not env.safe_exists("{0}_keys.jmp".format(jmp_base)):
            cmd = "export MOSAIK_TMP=`pwd` && MosaikJump -hs {hash_size} -ia {ref_file} -out {index_name}".format(
                hash_size=hash_size, ref_file=dat_file, index_name=jmp_base)
            env.safe_run(cmd)
    return _index_w_command(dir_name, cmd, ref_file,
                            post=create_jumpdb, ext=".dat")

# -- Genome upload and download to Amazon s3 buckets

def _download_s3_index(env, manager, gid, idx):
    env.logger.info("Downloading genome from s3: {0} {1}".format(gid, idx))
    url = "https://s3.amazonaws.com/biodata/genomes/%s-%s.tar.xz" % (gid, idx)
    out_file = shared._remote_fetch(env, url)
    env.safe_run("xz -dc %s | tar -xvpf -" % out_file)
    env.safe_run("rm -f %s" % out_file)

def _download_genomes(genomes, genome_indexes):
    """Download a group of genomes from Amazon s3 bucket.
    """
    genome_dir = _make_genome_dir()
    for (orgname, gid, manager) in genomes:
        org_dir = os.path.join(genome_dir, orgname, gid)
        if not env.safe_exists(org_dir):
            env.safe_run('mkdir -p %s' % org_dir)
        for idx in genome_indexes:
            with cd(org_dir):
                if not env.safe_exists(idx):
                    _download_s3_index(env, manager, gid, idx)
        ref_file = os.path.join(org_dir, "seq", "%s.fa" % gid)
        if not env.safe_exists(ref_file):
            ref_file = os.path.join(org_dir, "seq", "%s.fa" % manager._name)
        assert env.safe_exists(ref_file), ref_file
        cur_indexes = manager.config.get("indexes", genome_indexes)
        _index_to_galaxy(org_dir, ref_file, gid, cur_indexes, manager.config)

def _upload_genomes(genomes, genome_indexes):
    """Upload our configured genomes to Amazon s3 bucket.
    """
    conn = boto.connect_s3()
    bucket = conn.create_bucket("biodata")
    genome_dir = os.path.join(env.data_files, "genomes")
    for (orgname, gid, _) in genomes:
        cur_dir = os.path.join(genome_dir, orgname, gid)
        _clean_directory(cur_dir, gid)
        for idx in genome_indexes:
            idx_dir = os.path.join(cur_dir, idx)
            tarball = _tar_directory(idx_dir, "%s-%s" % (gid, idx))
            _upload_to_s3(tarball, bucket)
    bucket.make_public()

def _upload_to_s3(tarball, bucket):
    """Upload the genome tarball to s3.
    """
    upload_script = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                                 "utils", "s3_multipart_upload.py")
    s3_key_name = os.path.join("genomes", os.path.basename(tarball))
    if not bucket.get_key(s3_key_name):
        gb_size = int(run("du -sm %s" % tarball).split()[0]) / 1000.0
        print "Uploading %s %.1fGb" % (s3_key_name, gb_size)
        cl = ["python", upload_script, tarball, bucket.name, s3_key_name, "--public"]
        subprocess.check_call(cl)

def _tar_directory(dir, tar_name):
    """Create a tarball of the directory.
    """
    base_dir, tar_dir = os.path.split(dir)
    tarball = os.path.join(base_dir, "%s.tar.xz" % tar_name)
    if not env.safe_exists(tarball):
        with cd(base_dir):
            env.safe_run("tar -cvpf - %s | xz -zc - > %s" % (tar_dir,
                                                             os.path.basename(tarball)))
    return tarball

def _clean_directory(dir, gid):
    """Clean duplicate files from directories before tar and upload.
    """
    # get rid of softlinks
    bowtie_ln = os.path.join(dir, "bowtie", "%s.fa" % gid)
    maq_ln = os.path.join(dir, "maq", "%s.fa" % gid)
    for to_remove in [bowtie_ln, maq_ln]:
        if env.safe_exists(to_remove):
            env.safe_run("rm -f %s" % to_remove)
    # remove any downloaded original sequence files
    remove_exts = ["*.gz", "*.zip"]
    with cd(os.path.join(dir, "seq")):
        for rext in remove_exts:
            fnames = env.safe_run("find . -name '%s'" % rext)
            for fname in (f.strip() for f in fnames.split("\n") if f.strip()):
                env.safe_run("rm -f %s" % fname)

# == Liftover files

def _data_liftover(lift_over_genomes):
    """Download chain files for running liftOver.

    Does not install liftOver binaries automatically.
    """
    lo_dir = os.path.join(env.data_files, "liftOver")
    if not env.safe_exists(lo_dir):
        env.safe_run("mkdir %s" % lo_dir)
    lo_base_url = "ftp://hgdownload.cse.ucsc.edu/goldenPath/%s/liftOver/%s"
    lo_base_file = "%sTo%s.over.chain.gz"
    for g1 in lift_over_genomes:
        for g2 in [g for g in lift_over_genomes if g != g1]:
            g2u = g2[0].upper() + g2[1:]
            cur_file = lo_base_file % (g1, g2u)
            non_zip = os.path.splitext(cur_file)[0]
            worked = False
            with cd(lo_dir):
                if not env.safe_exists(non_zip):
                    result = shared._remote_fetch(env, "%s" % (lo_base_url % (g1, cur_file)), allow_fail=True)
                    # Lift over back and forths don't always exist
                    # Only move forward if we found the file
                    if result:
                        worked = True
                        env.safe_run("gunzip %s" % result)
            if worked:
                ref_parts = [g1, g2, os.path.join(lo_dir, non_zip)]
                galaxy.update_loc_file("liftOver.loc", ref_parts)

# == UniRef
def _data_uniref():
    """Retrieve and index UniRef databases for protein searches.

    http://www.ebi.ac.uk/uniref/

    These are currently indexed for FASTA searches. Are other indexes desired?
    Should this be separated out and organized by program like genome data?
    This should also check the release note and automatically download and
    replace older versions.
    """
    site = "ftp://ftp.uniprot.org"
    base_url = site + "/pub/databases/uniprot/" \
               "current_release/uniref/%s/%s"
    for uniref_db in ["uniref50", "uniref90", "uniref100"]:
        work_dir = os.path.join(env.data_files, "uniref", uniref_db)
        if not env.safe_exists(work_dir):
            env.safe_run("mkdir -p %s" % work_dir)
        base_work_url = base_url % (uniref_db, uniref_db)
        fasta_url = base_work_url + ".fasta.gz"
        base_file = os.path.splitext(os.path.basename(fasta_url))[0]
        with cd(work_dir):
            if not env.safe_exists(base_file):
                out_file = shared._remote_fetch(env, fasta_url)
                env.safe_run("gunzip %s" % out_file)
                shared._remote_fetch(env, base_work_url + ".release_note")
        _index_blast_db(work_dir, base_file, "prot")

def _index_blast_db(work_dir, base_file, db_type):
    """Index a database using blast+ for similary searching.
    """
    type_to_ext = dict(prot = ("phr", "pal"), nucl = ("nhr", "nal"))
    db_name = os.path.splitext(base_file)[0]
    with cd(work_dir):
        if not reduce(operator.or_,
            (env.safe_exists("%s.%s" % (db_name, ext)) for ext in type_to_ext[db_type])):
            env.safe_run("makeblastdb -in %s -dbtype %s -out %s" %
                         (base_file, db_type, db_name))


def get_index_fn(index):
    """
    return the index function for an index, if it is missing return a function
    that is a no-op
    """
    INDEX_FNS = {
        "seq" : _index_sam,
        "bwa" : _index_bwa,
        "bowtie": _index_bowtie,
        "bowtie2": _index_bowtie2,
        "maq": _index_maq,
        "mosaik": _index_mosaik,
        "novoalign": _index_novoalign,
        "novoalign_cs": _index_novoalign_cs,
        "ucsc": _index_twobit,
        "star": _index_star
        }
    return INDEX_FNS.get(index, lambda x: None)

########NEW FILE########
__FILENAME__ = rnaseq
"""Prepare supplemental files to work with RNA-seq transcriptome experiments.

Retrieves annotations in a format usable by Cufflinks, using repositories
provided by Illumina:

http://cufflinks.cbcb.umd.edu/igenomes.html
"""
import os

from fabric.api import cd

from cloudbio.custom import shared
from cloudbio.fabutils import warn_only

VERSIONS = {"rn5": "2014-05-02",
            "GRCh37": "2014-05-02",
            "hg19": "2014-05-02",
            "mm10": "2014-05-02",
            "canFam3": "2014-05-02"}

def download_transcripts(genomes, env):
    folder_name = "rnaseq"
    genome_dir = os.path.join(env.data_files, "genomes")
    for (orgname, gid, manager) in ((o, g, m) for (o, g, m) in genomes
                                    if m.config.get("rnaseq", False)):
        version = VERSIONS.get(gid, "")
        base_url = "https://s3.amazonaws.com/biodata/annotation/{gid}-rnaseq-{version}.tar.xz"
        org_dir = os.path.join(genome_dir, orgname)
        tx_dir = os.path.join(org_dir, gid, folder_name)
        version_dir = "%s-%s" % (tx_dir, version)
        if not env.safe_exists(version_dir):
            with cd(org_dir):
                has_rnaseq = _download_annotation_bundle(env, base_url.format(gid=gid, version=version), gid)
                if version and has_rnaseq:
                    _symlink_version(env, tx_dir, version_dir)
        if version:
            _symlink_refgenome(env, gid, org_dir)

def _symlink_refgenome(env, gid, org_dir):
    """Provide symlinks back to reference genomes so tophat avoids generating FASTA genomes.
    """
    for aligner in ["bowtie", "bowtie2"]:
        aligner_dir = os.path.join(org_dir, gid, aligner)
        if env.safe_exists(aligner_dir):
            with cd(aligner_dir):
                for ext in ["", ".fai"]:
                    orig_seq = os.path.join(os.pardir, "seq", "%s.fa%s" % (gid, ext))
                    if env.safe_exists(orig_seq) and not env.safe_exists(os.path.basename(orig_seq)):
                        env.safe_run("ln -s %s" % orig_seq)

def _symlink_version(env, tx_dir, version_dir):
    """Symlink the expected base output directory to our current version.
    """
    if env.safe_exists(tx_dir):
        env.safe_run("rm -rf %s" % tx_dir)
    with cd(os.path.dirname(version_dir)):
        env.safe_run("ln -s %s %s" % (os.path.basename(version_dir), os.path.basename(tx_dir)))

def _download_annotation_bundle(env, url, gid):
    """Download bundle of RNA-seq data from S3 biodata/annotation
    """
    tarball = shared._remote_fetch(env, url, allow_fail=True)
    if tarball and env.safe_exists(tarball):
        env.logger.info("Extracting RNA-seq references: %s" % tarball)
        env.safe_run("xz -dc %s | tar -xpf -" % tarball)
        env.safe_run("rm -f %s" % tarball)
        return True
    else:
        env.logger.warn("RNA-seq transcripts not available for %s" % gid)
        return False

########NEW FILE########
__FILENAME__ = cloudbiolinux
"""CloudBioLinux specific scripts
"""
import os
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.custom import shared

def _freenx_scripts(env):
    """Provide graphical access to clients via FreeNX.
    """
    home_dir = env.safe_run_output("echo $HOME")
    setup_script = "setupnx.sh"
    bin_dir = shared._get_bin_dir(env)
    install_file_dir = os.path.join(env.config_dir, os.pardir, "installed_files")
    if not env.safe_exists(os.path.join(bin_dir, setup_script)):
        env.safe_put(os.path.join(install_file_dir, setup_script),
                     os.path.join(home_dir, setup_script))
        env.safe_run("chmod 0777 %s" % os.path.join(home_dir, setup_script))
        env.safe_sudo("mv %s %s" % (os.path.join(home_dir, setup_script), bin_dir))
    remote_login = "configure_freenx.sh"
    if not env.safe_exists(os.path.join(home_dir, remote_login)):
        env.safe_put(os.path.join(install_file_dir, 'bash_login'), os.path.join(home_dir, remote_login))
        env.safe_run("chmod 0777 %s" % os.path.join(home_dir, remote_login))
    _configure_gnome(env)

def _cleanup_space(env):
    """Cleanup to recover space from builds and packages.
    """
    if env.edition.short_name not in ["minimal"]:
        env.logger.info("Cleaning up space from package builds")
        env.safe_sudo("rm -rf .cpanm")
        env.safe_sudo("rm -f /var/crash/*")
        env.safe_run("rm -f ~/*.dot")
        env.safe_run("rm -f ~/*.log")

def _configure_gnome(env):
    """Configure NX server to use classic GNOME.

    http://askubuntu.com/questions/50503/why-do-i-get-unity-instead-of-classic-when-using-nx
    http://notepad2.blogspot.com/2012/04/install-freenx-server-on-ubuntu-1110.html
    """
    add = 'COMMAND_START_GNOME="gnome-session --session gnome-fallback"'
    fname = "/etc/nxserver/node.conf"
    if env.safe_exists("/etc/nxserver/"):
        env.safe_append(fname, add, use_sudo=True)

########NEW FILE########
__FILENAME__ = cloudman
"""Build instructions associated with CloudMan.

http://wiki.g2.bx.psu.edu/Admin/Cloud

Adapted from Enis Afgan's code: https://bitbucket.org/afgane/mi-deployment
"""

cm_upstart = """
description     "Start CloudMan contextualization script"

start on runlevel [2345]

task
exec python %s 2> %s.log
"""
import os

from fabric.api import sudo, cd, run, put
from fabric.contrib.files import exists, settings

from cloudbio.galaxy import _setup_users
from cloudbio.flavor.config import get_config_file
from cloudbio.package.shared import _yaml_to_packages
from cloudbio.custom.shared import (_make_tmp_dir, _write_to_file, _get_install,
                                    _configure_make, _if_not_installed,
                                    _setup_conf_file, _add_to_profiles,
                                    _create_python_virtualenv,
                                    _setup_simple_service,
                                    _read_boolean)
from cloudbio.package.deb import (_apt_packages, _setup_apt_automation)

MI_REPO_ROOT_URL = "https://bitbucket.org/afgane/mi-deployment/raw/tip"
CM_REPO_ROOT_URL = "https://bitbucket.org/galaxy/cloudman/raw/tip"


def _configure_cloudman(env, use_repo_autorun=False):
    """
    Configure the machine to be capable of running CloudMan.

    ..Also see: ``custom/cloudman.py``
    """
    _setup_users(env)
    _setup_env(env)
    _configure_logrotate(env)
    _configure_ec2_autorun(env, use_repo_autorun)
    _configure_sge(env)
    _configure_hadoop(env)
    _configure_nfs(env)
    _configure_novnc(env)
    _configure_desktop(env)
    install_s3fs(env)


def _configure_desktop(env):
    """
    Configure a desktop manager to work with VNC. Note that `xfce4` (or `jwm`)
    and `vnc4server` packages need to be installed for this to have effect.
    """
    if not _read_boolean(env, "configure_desktop", False):
        return
    # Set nginx PAM module to allow logins for any system user
    if env.safe_exists("/etc/pam.d"):
        env.safe_sudo('echo "@include common-auth" > /etc/pam.d/nginx')
    env.safe_sudo('usermod -a -G shadow galaxy')
    # Create a start script for X
    _setup_conf_file(env, "/home/ubuntu/.vnc/xstartup", "xstartup", default_source="xstartup")
    # Create jwmrc config file (uncomment this if using jwm window manager)
    # _setup_conf_file(env, "/home/ubuntu/.jwmrc", "jwmrc.xml",
    #     default_source="jwmrc.xml", mode="0644")
    env.logger.info("----- Done configuring desktop -----")


def _configure_novnc(env):
    if not _read_boolean(env, "configure_novnc", False):
        # Longer term would like this enabled by default. -John
        return
    if not "novnc_install_dir" in env:
        env.novnc_install_dir = "/opt/novnc"
    if not "vnc_password" in env:
        env.vnc_password = "cl0udbi0l1nux"
    if not "vnc_user" in env:
        env.vnc_user = env.user
    if not "vnc_display" in env:
        env.vnc_display = "1"
    if not "vnc_depth" in env:
        env.vnc_depth = "16"
    if not "vnc_geometry" in env:
        env.vnc_geometry = "1024x768"

    _configure_vncpasswd(env)

    novnc_dir = env.novnc_install_dir
    env.safe_sudo("mkdir -p '%s'" % novnc_dir)
    env.safe_sudo("chown %s '%s'" % (env.user, novnc_dir))
    clone_cmd = "NOVNC_DIR='%s'; rm -rf $NOVNC_DIR; git clone https://github.com/kanaka/noVNC.git $NOVNC_DIR" % novnc_dir
    run(clone_cmd)
    ## Move vnc_auto.html which takes vnc_password as query argument
    ## to index.html and rewrite it so that password is autoset, no
    ## need to specify via query parameter.
    run("sed s/password\\ =\\ /password\\ =\\ \\\'%s\\\'\\;\\\\\\\\/\\\\\\\\// '%s/vnc_auto.html' > '%s/index.html'" % (env.vnc_password, novnc_dir, novnc_dir))

    _setup_conf_file(env, "/etc/init.d/novnc", "novnc_init", default_source="novnc_init")
    _setup_conf_file(env, "/etc/default/novnc", "novnc_default", default_source="novnc_default.template")
    _setup_conf_file(env, "/etc/init.d/vncserver", "vncserver_init", default_source="vncserver_init")
    _setup_conf_file(env, "/etc/default/vncserver", "vncserver_default", default_source="vncserver_default.template")
    _setup_simple_service("novnc")
    _setup_simple_service("vncserver")


def _configure_vncpasswd(env):
    with cd("~"):
        run("mkdir -p ~/.vnc")
        run("rm -rf vncpasswd")
        run("git clone https://github.com/trinitronx/vncpasswd.py vncpasswd")
        run("python vncpasswd/vncpasswd.py '%s' -f ~/.vnc/passwd" % env.vnc_password)
        run("chmod 600 ~/.vnc/passwd")
        run("rm -rf vncpasswd")


def _setup_env(env):
    """
    Setup the system environment required to run CloudMan. This means
    installing required system-level packages (as defined in CBL's
    ``packages.yaml``, or a flavor thereof) and Python dependencies
    (i.e., libraries) as defined in CloudMan's ``requirements.txt`` file.
    """
    # Get and install required system packages
    if env.distribution in ["debian", "ubuntu"]:
        config_file = get_config_file(env, "packages.yaml")
        (packages, _) = _yaml_to_packages(config_file.base, 'cloudman')
        # Allow editions and flavors to modify the package list
        packages = env.edition.rewrite_config_items("packages", packages)
        packages = env.flavor.rewrite_config_items("packages", packages)
        _setup_apt_automation()
        _apt_packages(pkg_list=packages)
    elif env.distribution in ["centos", "scientificlinux"]:
        env.logger.warn("No CloudMan system package dependencies for CentOS")
        pass
    # Get and install required Python libraries
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            url = os.path.join(CM_REPO_ROOT_URL, 'requirements.txt')
            _create_python_virtualenv(env, 'CM', reqs_url=url)
    # Add a custom vimrc
    vimrc_url = os.path.join(MI_REPO_ROOT_URL, 'conf_files', 'vimrc')
    remote_file = '/etc/vim/vimrc'
    if env.safe_exists("/etc/vim"):
        env.safe_sudo("wget --output-document=%s %s" % (remote_file, vimrc_url))
        env.logger.debug("Added a custom vimrc to {0}".format(remote_file))
    # Setup profile
    aliases = ['alias lt="ls -ltr"', 'alias ll="ls -l"']
    for alias in aliases:
        _add_to_profiles(alias, ['/etc/bash.bashrc'])
    env.logger.info("Done setting up CloudMan's environment")


def _configure_logrotate(env):
    """
    Add logrotate config file, which will automatically rotate CloudMan's log
    """
    conf_file = "cloudman.logrotate"
    remote = '/etc/logrotate.d/cloudman'
    url = os.path.join(MI_REPO_ROOT_URL, 'conf_files', conf_file)
    env.safe_sudo("wget --output-document=%s %s" % (remote, url))
    env.logger.info("----- Added logrotate file to {0} -----".format(remote))


def _configure_ec2_autorun(env, use_repo_autorun=False):
    """
    ec2autorun.py is a script that launches CloudMan on instance boot
    and is thus required on an instance. See the script itself for the
    details of what it does.

    This script also adds a cloudman service to ``/etc/init``, which
    actually runs ec2autorun.py as a system-level service at system boot.
    """
    script = "ec2autorun.py"
    remote = os.path.join(env.install_dir, "bin", script)
    if not env.safe_exists(os.path.dirname(remote)):
        env.safe_sudo('mkdir -p {0}'.format(os.path.dirname(remote)))
    if use_repo_autorun:
        # Is this used, can we eliminate use_repo_autorun?
        url = os.path.join(MI_REPO_ROOT_URL, script)
        env.safe_sudo("wget --output-document=%s %s" % (remote, url))
    else:
        install_file_dir = os.path.join(env.config_dir, os.pardir, "installed_files")
        tmp_remote = os.path.join("/tmp", os.path.basename(remote))
        env.safe_put(os.path.join(install_file_dir, script), tmp_remote)
        env.safe_sudo("mv %s %s" % (tmp_remote, remote))
        env.safe_sudo("chmod 0777 %s" % remote)
    # Create upstart configuration file for boot-time script
    cloudman_boot_file = 'cloudman.conf'
    remote_file = '/etc/init/%s' % cloudman_boot_file
    _write_to_file(cm_upstart % (remote, os.path.splitext(remote)[0]), remote_file, mode="0644")
    # Setup default image user data (if configured by image_user_data_path or
    # image_user_data_template_path). This specifies defaults for CloudMan when
    # used with resulting image, normal userdata supplied by user will override
    # these defaults.
    image_user_data_path = os.path.join(env.install_dir, "bin", "IMAGE_USER_DATA")
    if "image_user_data_dict" in env:
        # Explicit YAML contents defined in env, just dump them as is.
        import yaml
        _write_to_file(yaml.dump(env.get("image_user_data_dict")), image_user_data_path, mode="0644")
    else:
        # Else use file or template file.
        _setup_conf_file(env, image_user_data_path, "image_user_data", default_source="image_user_data")
    env.logger.info("Done configuring CloudMan's ec2_autorun")


def _configure_sge(env):
    """
    This method sets up the environment for SGE w/o
    actually setting up SGE; it basically makes sure system paths expected
    by CloudMan exist on the system.

    TODO: Merge this with ``install_sge`` method in ``custom/cloudman.py``.
    """
    sge_root = '/opt/sge'
    if not env.safe_exists(sge_root):
        env.safe_sudo("mkdir -p %s" % sge_root)
        env.safe_sudo("chown sgeadmin:sgeadmin %s" % sge_root)
    # Link our installed SGE to CloudMan's expected directory
    sge_package_dir = "/opt/galaxy/pkg"
    sge_dir = "ge6.2u5"
    if not env.safe_exists(os.path.join(sge_package_dir, sge_dir)):
        env.safe_sudo("mkdir -p %s" % sge_package_dir)
    if not env.safe_exists(os.path.join(sge_package_dir, sge_dir)):
        env.safe_sudo("ln --force -s %s/%s %s/%s" % (env.install_dir, sge_dir, sge_package_dir, sge_dir))
    env.logger.info("Done configuring SGE for CloudMan")


def _configure_hadoop(env):
    """
    Grab files required by CloudMan to setup a Hadoop cluster atop SGE.
    """
    hadoop_root = '/opt/hadoop'
    url_root = 'https://s3.amazonaws.com/cloudman'
    hcm_file = 'hadoop.1.0.4__1.0.tar.gz'
    si_file = 'sge_integration.1.0.tar.gz'
    # Make sure we're working with a clean hadoop_home dir to avoid any version conflicts
    env.safe_sudo("rm -rf {0}".format(hadoop_root))
    env.safe_sudo("mkdir -p %s" % hadoop_root)
    with cd(hadoop_root):
        env.safe_sudo("wget --output-document={0} {1}/{0}".format(hcm_file, url_root))
        env.safe_sudo("wget --output-document={0} {1}/{0}".format(si_file, url_root))
    env.safe_sudo("chown -R {0} {1}".format(env.user, hadoop_root))
    env.logger.info("Done configuring Hadoop for CloudMan")


def _configure_nfs(env):
    """
    Edit ``/etc/exports`` to append paths that are shared over NFS by CloudMan.

    In addition to the hard coded paths listed here, additional paths
    can be included by setting ``extra_nfs_exports`` in ``fabricrc.txt`` as
    a comma-separated list of directories.
    """
    nfs_dir = "/export/data"
    cloudman_dir = "/mnt/galaxy/export"
    if not env.safe_exists(nfs_dir):
        # For the case of rerunning this script, ensure the nfs_dir does
        # not exist (exists() method does not recognize it as a file because
        # by default it points to a non-existing dir/file).
        with settings(warn_only=True):
            env.safe_sudo('rm -rf {0}'.format(nfs_dir))
        env.safe_sudo("mkdir -p %s" % os.path.dirname(nfs_dir))
        env.safe_sudo("ln -s %s %s" % (cloudman_dir, nfs_dir))
    env.safe_sudo("chown -R %s %s" % (env.user, os.path.dirname(nfs_dir)))
    # Setup /etc/exports paths, to be used as NFS mount points
    galaxy_data_mount = env.get("galaxy_data_mount", "/mnt/galaxyData")
    galaxy_indices_mount = env.get("galaxy_indices_mount", "/mnt/galaxyIndices")
    galaxy_tools_mount = env.get("galaxy_tools_mount", "/mnt/galaxyTools")
    exports = ['/opt/sge           *(rw,sync,no_root_squash,no_subtree_check)',
               '/opt/hadoop           *(rw,sync,no_root_squash,no_subtree_check)',
               '%s    *(rw,sync,no_root_squash,subtree_check,no_wdelay)' % galaxy_data_mount,
               '%s *(rw,sync,no_root_squash,no_subtree_check)' % galaxy_indices_mount,
               '%s   *(rw,sync,no_root_squash,no_subtree_check)' % galaxy_tools_mount,
               '%s       *(rw,sync,no_root_squash,no_subtree_check)' % nfs_dir,
               '%s/openmpi         *(rw,sync,no_root_squash,no_subtree_check)' % env.install_dir]
    extra_nfs_exports = env.get("extra_nfs_exports", "")
    for extra_nfs_export in extra_nfs_exports.split(","):
        exports.append('%s   *(rw,sync,no_root_squash,no_subtree_check)' % extra_nfs_export)
    env.safe_append('/etc/exports', exports, use_sudo=True)
    # Create a symlink for backward compatibility where all of CloudMan's
    # stuff is expected to be in /opt/galaxy
    old_dir = '/opt/galaxy'
    # Because stow is used, the equivalent to CloudMan's expected path
    # is actually the parent of the install_dir so use it for the symlink
    new_dir = os.path.dirname(env.install_dir)
    if not env.safe_exists(old_dir) and exists(new_dir):
        env.safe_sudo('ln -s {0} {1}'.format(new_dir, old_dir))
    env.logger.info("Done configuring NFS for CloudMan")


@_if_not_installed("s3fs")
def install_s3fs(env):
    """
    Install s3fs, allowing S3 buckets to be mounted as ~POSIX file systems
    """
    default_version = "1.61"
    version = env.get("tool_version", default_version)
    url = "http://s3fs.googlecode.com/files/s3fs-%s.tar.gz" % version
    _get_install(url, env, _configure_make)


def _cleanup_ec2(env):
    """
    Clean up any extra files after building. This method must be called
    on an instance after being built and before creating a new machine
    image. *Note* that after this method has run, key-based ssh access
    to the machine is no longer possible.
    """
    env.logger.info("Cleaning up for EC2 AMI creation")
    # Clean up log files and such
    fnames = [".bash_history", "/var/log/firstboot.done", ".nx_setup_done",
              "/var/crash/*", "%s/ec2autorun.py.log" % env.install_dir,
              "%s/ec2autorun.err" % env.install_dir, "%s/ec2autorun.log" % env.install_dir,
              "%s/bin/ec2autorun.log" % env.install_dir]
    for fname in fnames:
        sudo("rm -f %s" % fname)
    rmdirs = ["/mnt/galaxyData", "/mnt/cm", "/tmp/cm"]
    for rmdir in rmdirs:
        sudo("rm -rf %s" % rmdir)
    # Seed the history with frequently used commands
    env.logger.debug("Setting bash history")
    local = os.path.join(env.config_dir, os.pardir, "installed_files", "bash_history")
    remote = os.path.join('/home', 'ubuntu', '.bash_history')
    put(local, remote, mode=0660, use_sudo=True)
    # Make sure the default config dir is owned by ubuntu
    sudo("chown ubuntu:ubuntu ~/.config")
    # Stop Apache from starting automatically at boot (it conflicts with Galaxy's nginx)
    sudo('/usr/sbin/update-rc.d -f apache2 remove')
    with settings(warn_only=True):
        # RabbitMQ fails to start if its database is embedded into the image
        # because it saves the current IP address or host name so delete it now.
        # When starting up, RabbitMQ will recreate that directory.
        sudo('/etc/init.d/rabbitmq-server stop')
        sudo('service rabbitmq-server stop')
        # Clean up packages that are causing issues or are unnecessary
        pkgs_to_remove = ['tntnet', 'tntnet-runtime', 'libtntnet9', 'vsftpd']
        for ptr in pkgs_to_remove:
            sudo('apt-get -y --force-yes remove --purge {0}'.format(ptr))
    sudo('initctl reload-configuration')
    for db_location in ['/var/lib/rabbitmq/mnesia', '/mnesia']:
        if exists(db_location):
            sudo('rm -rf %s' % db_location)
    # remove existing ssh host key pairs
    # http://docs.amazonwebservices.com/AWSEC2/latest/UserGuide/AESDG-chapter-sharingamis.html
    sudo("rm -f /etc/ssh/ssh_host_*")
    sudo("rm -f ~/.ssh/authorized_keys*")
    sudo("rm -f /root/.ssh/authorized_keys*")

########NEW FILE########
__FILENAME__ = chef
import os
import json

from fabric.api import cd
from fabric.contrib import files
from fabric.state import _AttributeDict

from cloudbio.flavor.config import get_config_file
from utils import build_properties, upload_config, config_dir


# Code based heavily on fabric-provision. https://github.com/caffeinehit/fabric-provision

DEFAULTS = dict(
    path='/var/chef',
    data_bags=config_dir(os.path.join('chef', 'data_bags')),
    roles=config_dir(os.path.join('chef', 'roles')),
    cookbooks=config_dir(os.path.join('chef', 'cookbooks')),
    log_level='info',
    recipes=[],
    run_list=[],
    json={},
)

SOLO_RB = """
log_level            :%(log_level)s
log_location         STDOUT
file_cache_path      "%(path)s"
data_bag_path        "%(path)s/data_bags"
role_path            [ "%(path)s/roles" ]
cookbook_path        [ "%(path)s/cookbooks" ]
Chef::Log::Formatter.show_time = true
"""


class ChefDict(_AttributeDict):
    def add_recipe(self, recipe):
        self.run_list.append('recipe[{0}]'.format(recipe))

    def add_role(self, role):
        self.run_list.append('role[{0}]'.format(role))

    def _get_json(self):
        the_json = self['json'].copy()
        the_json['run_list'] = self['run_list']
        return the_json

    json = property(fget=_get_json)

chef = ChefDict(DEFAULTS)


def omnibus(env):
    """
    Install Chef from Opscode's Omnibus installer
    """
    ctx = {
        'filename': '%(path)s/install-chef.sh' % chef,
        'url': 'http://opscode.com/chef/install.sh',
    }
    if not files.exists(ctx['filename']):
        env.safe_sudo('wget -O %(filename)s %(url)s' % ctx)
        with cd(chef.path):
            env.safe_sudo('bash install-chef.sh')


def _chef_provision(env, _omnibus=True):
    env.safe_sudo('mkdir -p %(path)s' % chef)

    omnibus(env)

    config_files = {'node.json': json.dumps(chef.json),
                    'solo.rb': SOLO_RB % chef}
    upload_config(chef, config_folder_names=['cookbooks', 'data_bags', 'roles'], config_files=config_files)

    with cd(chef.path):
        env.safe_sudo('chef-solo -c solo.rb -j node.json')


def _configure_chef(env, chef):

    # Set node json properties
    node_json_path = get_config_file(env, "node_extra.json").base
    chef.json = _build_chef_properties(env, node_json_path)

    # Set whether to use the Opscode Omnibus Installer to load Chef.
    use_omnibus_installer_str = env.get("use_chef_omnibus_installer", "false")
    chef.use_omnibus_installer = use_omnibus_installer_str.upper() in ["TRUE", "YES"]


def _build_chef_properties(env, config_file):
    """
    Build python object representation of the Chef-solo node.json file from
    node_extra.json in config dir and the fabric environment.
    """

    json_properties = _parse_json(config_file)
    return build_properties(env, "chef", json_properties)


def _parse_json(filename):
    """ Parse a JSON file
        First remove comments and then use the json module package
        Comments look like :
            // ...
    """
    with open(filename) as f:
        lines = f.readlines()
        content = ''.join([line for line in lines if not line.startswith('//')])
        print content
        return json.loads(content)

########NEW FILE########
__FILENAME__ = puppet
from fabric.state import _AttributeDict
from fabric.api import cd

from utils import upload_config, config_dir, build_properties
from cloudbio.package.deb import _apt_packages
import os

DEFAULTS = dict(
    path='/var/puppet',
    log_level='info',
    modules=config_dir(os.path.join('puppet', 'modules'))
)

puppet = _AttributeDict(DEFAULTS)


def _puppet_provision(env, classes):
    env.safe_sudo('mkdir -p %(path)s' % puppet)
    manifest_body = "node default {\n%s\n}\n" % _build_node_def_body(env, classes)
    config_files = {"manifest.pp": manifest_body}
    upload_config(puppet, config_folder_names=["modules"], config_files=config_files)
    # TODO: Allow yum based install
    _apt_packages(pkg_list=["puppet"])
    with cd(puppet.path):
        env.safe_sudo("sudo puppet apply --modulepath=modules manifest.pp")


def _build_node_def_body(env, classes):
    contents = ""
    properties = build_properties(env, "puppet")
    contents += "\n".join(["$%s = '%s'" % (key, value.replace("'", r"\'")) for key, value in properties.iteritems()])
    contents += "\n"
    contents += "\n".join([_build_class_include(env, class_name) for class_name in classes])
    return contents


def _build_class_include(env, class_name):
    """
    If parentns::classname is included and fabric
    properties such as puppet_parentns__classname_prop = val1
    are set, the class included in puppet will be something like

    class { 'parentns::classname':
        prop => 'val1',
    }
    """
    include_def = "class { '%s': \n" % class_name
    property_prefix = _property_prefix(class_name)
    for name, value in env.iteritems():
        if name.startswith(property_prefix):
            property_name = name[len(property_prefix):]
            if not property_name.startswith("_"):  # else subclass property
                include_def += "  %s => '%s',\n" % (property_name, value)
    include_def += "\n}"
    return include_def


def _property_prefix(class_name):
    return "puppet_%s_" % class_name.replace("::", "__")

########NEW FILE########
__FILENAME__ = utils
from tempfile import mkdtemp
import os
from fabric.api import settings, local, put, sudo, cd
from fabric.contrib import files


def config_dir(relative_path):
    cloudbiolinux_dir = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    return os.path.join(cloudbiolinux_dir, "config", relative_path)


def build_properties(env, prefix, overrides={}):
    # Prefix will be either chef or puppet
    prefix = "%s_" % prefix
    # Clone fresh dictonary to modify
    overrides = dict(overrides)

    # Load fabric environment properties into properties.
    for key, value in env.iteritems():
        # Skip invalid properties.
        if key in overrides or not isinstance(value, str):
            continue

        if key.startswith(prefix):
            # If a property starts with chef_ assume it is meant for chef and
            # add without this prefix. So chef_apache_dir would be available
            # as apache_dir.
            overrides[key[len(prefix):]] = value
        else:
            # Otherwise, allow chef to access property anyway but prefix with
            # cloudbiolinux_ so it doesn't clash with anything explicitly
            # configured for chef.
            overrides["cloudbiolinux_%s" % key] = value
    return overrides


def upload_config(config, config_folder_names=[], config_files={}):
    """ Common code to upload puppet and chef config files
    to remote server.

    Heavily based on upload procedure from fabric-provision:
    https://github.com/caffeinehit/fabric-provision/blob/master/provision/__init__.py
    """
    names = config_folder_names + config_files.keys()
    ctx = dict(map(lambda name: (name, '%s/%s' % (config.path, name)), names))

    tmpfolder = mkdtemp()

    listify = lambda what: what if isinstance(what, list) else [what]

    for folder_name in config_folder_names:
        setattr(config, folder_name, listify(getattr(config, folder_name)))

    for folder_name in config_folder_names:
        local('mkdir %s/%s' % (tmpfolder, folder_name))

    def copyfolder(folder, what):
        if not os.path.exists(folder):
            os.makedirs(folder)

        with settings(warn_only=True):
            local('cp -r %(folder)s/* %(tmpfolder)s/%(what)s' % dict(
                    folder=folder,
                    tmpfolder=tmpfolder,
                    what=what))

    for what in config_folder_names:
        map(lambda f: copyfolder(f, what), getattr(config, what))

    folder_paths = " ".join(map(lambda folder_name: "./%s" % folder_name, config_folder_names))
    local('cd %s && tar -f config_dir.tgz -cz %s' % (tmpfolder, folder_paths))

    # Get rid of old files
    with settings(warn_only=True):
        map(lambda what: sudo("rm -rf '%s'" % ctx[what]), ctx.keys())

    # Upload
    put('%s/config_dir.tgz' % tmpfolder, config.path, use_sudo=True)

    with cd(config.path):
        sudo('tar -xf config_dir.tgz')

    for file, contents in config_files.iteritems():
        files.append(ctx[file], contents, use_sudo=True)

########NEW FILE########
__FILENAME__ = bio_general
"""Custom installs for biological packages.
"""
import os

from fabric.api import *
from fabric.contrib.files import *

from cloudbio.custom import shared
from shared import (_if_not_installed, _get_install, _configure_make, _java_install,
                    _make_tmp_dir)

def install_anaconda(env):
    """Pre-packaged Anaconda Python installed from Continuum.
    http://docs.continuum.io/anaconda/index.html
    """
    version = "1.7.0"
    outdir = os.path.join(env.system_install, "anaconda")
    if env.distribution in ["ubuntu", "centos", "scientificlinux", "debian"]:
        platform = "Linux"
    elif env.distribution in ["macosx"]:
        platform = "MacOSX"
    else:
        raise ValueError("Unexpected distribution: %s" % env.distribution)
    url = "http://09c8d0b2229f813c1b93-c95ac804525aac4b6dba79b00b39d1d3.r79.cf1.rackcdn.com/" \
          "Anaconda-%s-%s-x86_64.sh" % (version, platform)
    if not env.safe_exists(outdir):
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                installer = shared._remote_fetch(env, url)
                env.safe_sed(os.path.basename(url), "more <<EOF", "cat  <<EOF")
                env.safe_sudo("echo -e '\nyes\n%s\nyes\n' | bash %s" % (outdir, installer))
                env.safe_sudo("chown -R %s %s" % (env.user, outdir))
                comment_line = "# added by Ananconda %s installer" % version
                if not env.safe_contains(env.shell_config, comment_line):
                    env.safe_append(env.shell_config, comment_line)
                    env.safe_append(env.shell_config, "export PATH=%s/bin:$PATH" % outdir)
                # remove curl library with broken certificates
                env.safe_run("%s/bin/conda remove --yes curl" % outdir)
                env.safe_run("%s/bin/conda install --yes pip" % outdir)

@_if_not_installed("embossversion")
def install_emboss(env):
    """EMBOSS: A high-quality package of free, Open Source software for molecular biology.
    http://emboss.sourceforge.net/
    Emboss target for platforms without packages (CentOS -- rpm systems).
    """
    default_version = "6.6.0"
    version = env.get("tool_version", default_version)
    url = "ftp://emboss.open-bio.org/pub/EMBOSS/EMBOSS-%s.tar.gz" % version
    _get_install(url, env, _configure_make)

def install_pgdspider(env):
    """PGDSpider format conversion for population genetics programs.
    http://www.cmpg.unibe.ch/software/PGDSpider/
    """
    if os.path.exists(os.path.join(shared._get_bin_dir(env), "PGDSpider2.sh")):
        return
    version = "2.0.2.0"
    url = "http://www.cmpg.unibe.ch/software/PGDSpider/PGDSpider_{v}.zip".format(
        v=version)
    def _install_fn(env, install_dir):
        env.safe_sudo("mv *.jar %s" % install_dir)
        bin_dir = shared._get_bin_dir(env)
        exe_file = "PGDSpider2.sh"
        jar = "PGDSpider2.jar"
        env.safe_sed(exe_file, jar, "{dir}/{jar}".format(dir=install_dir, jar=jar))
        env.safe_run("chmod a+x {0}".format(exe_file))
        env.safe_sudo("mv {exe} {bin}".format(exe=exe_file, bin=bin_dir))
    _java_install("PGDSpider", version, url, env, install_fn=_install_fn)

def install_bio4j(env):
    """Bio4j graph based database built on Neo4j with UniProt, GO, RefSeq and more.
    http://www.bio4j.com/
    """
    version = "0.8"
    url = "https://s3-eu-west-1.amazonaws.com/bio4j-public/releases/" \
          "{v}/bio4j-{v}.zip".format(v=version)
    def _install_fn(env, install_dir):
        targets = ["conf", "doc", "jars", "lib", "README"]
        for x in targets:
            env.safe_sudo("mv {0} {1}".format(x, install_dir))
    _java_install("bio4j", version, url, env, install_fn=_install_fn)

########NEW FILE########
__FILENAME__ = bio_nextgen
"""Install next gen sequencing analysis tools not currently packaged.
"""
import os
import re

from fabric.api import *
from fabric.contrib.files import *
import yaml

from shared import (_if_not_installed, _make_tmp_dir,
                    _get_install, _get_install_local, _make_copy, _configure_make,
                    _java_install, _python_cmd,
                    _symlinked_java_version_dir, _fetch_and_unpack, _python_make,
                    _get_lib_dir, _get_include_dir, _apply_patch)
from cloudbio.custom import shared, versioncheck

from cloudbio import libraries
from cloudbio.flavor.config import get_config_file


@_if_not_installed("twoBitToFa")
def install_ucsc_tools(env):
    """Useful executables from UCSC.

    todo: install from source to handle 32bit and get more programs
    http://hgdownload.cse.ucsc.edu/admin/jksrc.zip
    """
    tools = ["liftOver", "faToTwoBit", "bedToBigBed",
             "bigBedInfo", "bigBedSummary", "bigBedToBed",
             "bedGraphToBigWig", "bigWigInfo", "bigWigSummary",
             "bigWigToBedGraph", "bigWigToWig",
             "fetchChromSizes", "wigToBigWig", "faSize", "twoBitInfo",
             "twoBitToFa", "faCount", "gtfToGenePred"]
    url = "http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/"
    _download_executables(env, url, tools)


@_if_not_installed("blat")
def install_kent_tools(env):
    """

    Please note that the Blat source and executables are freely available for
    academic, nonprofit and personal use. Commercial licensing information is
    available on the Kent Informatics website (http://www.kentinformatics.com/).
    """
    tools = ["blat", "gfClient", "gfServer"]
    url = "http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/blat/"
    _download_executables(env, url, tools)


def _download_executables(env, base_url, tools):
    install_dir = shared._get_bin_dir(env)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            for tool in tools:
                final_tool = os.path.join(install_dir, tool)
                if not env.safe_exists(final_tool) and shared._executable_not_on_path(tool):
                    shared._remote_fetch(env, "%s%s" % (base_url, tool))
                    env.safe_sudo("cp -f %s %s" % (tool, install_dir))

# --- Alignment tools
def install_featurecounts(env):
    """
    featureCounts from the subread package for counting reads mapping to
    genomic features
    """
    default_version = "1.4.4"
    version = env.get("tool_version", default_version)
    if versioncheck.up_to_date(env, "featureCounts", version, stdout_flag="Version"):
        return
    platform = "MacOS" if env.distribution == "macosx" else "Linux"
    url = ("http://downloads.sourceforge.net/project/subread/"
           "subread-%s/subread-%s-%s-x86_64.tar.gz"
           % (version, version, platform))
    _get_install(url, env, _make_copy("find . -type f -perm -100 -name 'featureCounts'",
                                      do_make=False))


@_if_not_installed("bowtie")
def install_bowtie(env):
    """The bowtie short read aligner.
    http://bowtie-bio.sourceforge.net/index.shtml
    """
    default_version = "1.0.0"
    version = env.get("tool_version", default_version)
    url = "http://downloads.sourceforge.net/project/bowtie-bio/bowtie/%s/" \
          "bowtie-%s-src.zip" % (version, version)
    _get_install(url, env, _make_copy("find . -perm -100 -name 'bowtie*'"))

@_if_not_installed("bowtie2")
def install_bowtie2(env):
    """bowtie2 short read aligner, with gap support.
    http://bowtie-bio.sourceforge.net/bowtie2/index.shtml
    """
    default_version = "2.1.0"
    version = env.get("tool_version", default_version)
    url = "http://downloads.sourceforge.net/project/bowtie-bio/bowtie2/%s/" \
          "bowtie2-%s-source.zip" % (version, version)
    _get_install(url, env, _make_copy("find . -perm -100 -name 'bowtie2*'"))

@_if_not_installed("bfast")
def install_bfast(env):
    """BFAST: Blat-like Fast Accurate Search Tool.
    http://sourceforge.net/apps/mediawiki/bfast/index.php?title=Main_Page
    """
    default_version = "0.7.0a"
    version = env.get("tool_version", default_version)
    major_version_regex = "\d+\.\d+\.\d+"
    major_version = re.search(major_version_regex, version).group(0)
    url = "http://downloads.sourceforge.net/project/bfast/bfast/%s/bfast-%s.tar.gz"\
            % (major_version, version)
    _get_install(url, env, _configure_make)

@_if_not_installed("perm")
def install_perm(env):
    """Efficient mapping of short sequences accomplished with periodic full sensitive spaced seeds.
    https://code.google.com/p/perm/
    """
    default_version = "4"
    version = env.get("tool_version", default_version)
    url = "http://perm.googlecode.com/files/PerM%sSource.tar.gz" % version
    def gcc44_makefile_patch():
        gcc_cmd = "g++44"
        with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                      warn_only=True):
            result = env.safe_run("%s -v" % gcc_cmd)
        print result.return_code
        if result.return_code == 0:
            env.safe_sed("makefile", "g\+\+", gcc_cmd)
    _get_install(url, env, _make_copy("ls -1 perm", gcc44_makefile_patch))

@_if_not_installed("snap")
def install_snap(env):
    """Scalable Nucleotide Alignment Program
    http://snap.cs.berkeley.edu/
    """
    version = "0.15"
    url = "http://github.com/downloads/amplab/snap/" \
          "snap-%s-linux.tar.gz" % version
    _get_install(url, env, _make_copy("find . -perm -100 -type f", do_make=False))

def install_stampy(env):
    """Stampy: mapping of short reads from illumina sequencing machines onto a reference genome.
    http://www.well.ox.ac.uk/project-stampy
    """
    version = "1.0.21"
    #version = base_version
    #revision = "1654"
    #version = "{0}r{1}".format(base_version, revision)
    #url = "http://www.well.ox.ac.uk/bioinformatics/Software/" \
    #      "stampy-%s.tgz" % (version)
    # Ugh -- Stampy now uses a 'Stampy-latest' download target
    url = "http://www.well.ox.ac.uk/bioinformatics/Software/" \
          "Stampy-latest.tgz"
    def _clean_makefile(env):
        env.safe_sed("makefile", " -Wl", "")
    _get_install_local(url, env, _make_copy(),
                       dir_name="stampy-{0}".format(version),
                       post_unpack_fn=_clean_makefile)

@_if_not_installed("gmap")
def install_gmap(env):
    """GMAP and GSNAP: A Genomic Mapping and Alignment Program for mRNA EST and short reads.
    http://research-pub.gene.com/gmap/
    """
    version = "2012-11-09"
    url = "http://research-pub.gene.com/gmap/src/gmap-gsnap-%s.tar.gz" % version
    _get_install(url, env, _configure_make)

def _wget_with_cookies(ref_url, dl_url):
    env.safe_run("wget --cookies=on --keep-session-cookies --save-cookies=cookie.txt %s"
                 % (ref_url))
    env.safe_run("wget --referer=%s --cookies=on --load-cookies=cookie.txt "
                 "--keep-session-cookies --save-cookies=cookie.txt %s" %
                 (ref_url, dl_url))

@_if_not_installed("novoalign")
def install_novoalign(env):
    """Novoalign short read aligner using Needleman-Wunsch algorithm with affine gap penalties.
    http://www.novocraft.com/main/index.php
    """
    base_version = "V3.00.02"
    cs_version = "V1.03.02"
    _url = "http://www.novocraft.com/downloads/%s/" % base_version
    ref_url = "http://www.novocraft.com/main/downloadpage.php"
    base_url = "%s/novocraft%s.gcc.tar.gz" % (_url, base_version)
    cs_url = "%s/novoalignCS%s.gcc.tar.gz" % (_url, cs_version)
    install_dir = shared._get_bin_dir(env)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _wget_with_cookies(ref_url, base_url)
            env.safe_run("tar -xzvpf novocraft%s.gcc.tar.gz" % base_version)
            with cd("novocraft"):
                for fname in ["isnovoindex", "novo2maq", "novo2paf",
                              "novo2sam.pl", "novoalign", "novobarcode",
                              "novoindex", "novope2bed.pl", "novorun.pl",
                              "novoutil"]:
                    env.safe_sudo("mv %s %s" % (fname, install_dir))
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _wget_with_cookies(ref_url, cs_url)
            env.safe_run("tar -xzvpf novoalignCS%s.gcc.tar.gz" % cs_version)
            with cd("novoalignCS"):
                for fname in ["novoalignCS"]:
                    env.safe_sudo("mv %s %s" % (fname, install_dir))

@_if_not_installed("novosort")
def install_novosort(env):
    """Multithreaded sort and merge for BAM files.
    http://www.novocraft.com/wiki/tiki-index.php?page=Novosort
    """
    base_version = "V3.00.02"
    version = "V1.00.02"
    url = "http://www.novocraft.com/downloads/%s/novosort%s.gcc.tar.gz" % (base_version, version)
    ref_url = "http://www.novocraft.com/main/downloadpage.php"
    install_dir = shared._get_bin_dir(env)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _wget_with_cookies(ref_url, url)
            env.safe_run("tar -xzvpf novosort%s.gcc.tar.gz" % version)
            with cd("novosort"):
                for fname in ["novosort"]:
                    env.safe_sudo("mv %s %s" % (fname, install_dir))

@_if_not_installed("lastz")
def install_lastz(env):
    """LASTZ sequence alignment program.
    http://www.bx.psu.edu/miller_lab/dist/README.lastz-1.02.00/README.lastz-1.02.00a.html
    """
    default_version = "1.02.00"
    version = env.get("tool_version", default_version)
    url = "http://www.bx.psu.edu/miller_lab/dist/" \
          "lastz-%s.tar.gz" % version
    def _remove_werror(env):
        env.safe_sed("src/Makefile", " -Werror", "")
    _get_install(url, env, _make_copy("find . -perm -100 -name 'lastz'"),
                 post_unpack_fn=_remove_werror)

@_if_not_installed("MosaikAligner")
def install_mosaik(env):
    """MOSAIK: reference-guided aligner for next-generation sequencing technologies
    http://code.google.com/p/mosaik-aligner/
    """
    version = "2.1.73"
    url = "http://mosaik-aligner.googlecode.com/files/" \
          "MOSAIK-%s-binary.tar" % version
    _get_install(url, env, _make_copy("find . -perm -100 -type f", do_make=False))

# --- Utilities

def install_samtools(env):
    """SAM Tools provide various utilities for manipulating alignments in the SAM format.
    http://samtools.sourceforge.net/
    """
    default_version = "0.1.19"
    version = env.get("tool_version", default_version)
    if versioncheck.up_to_date(env, "samtools", version, stdout_flag="Version:"):
        env.logger.info("samtools version {0} is up to date; not installing"
                        .format(version))
        return
    url = "http://downloads.sourceforge.net/project/samtools/samtools/" \
          "%s/samtools-%s.tar.bz2" % (version, version)
    def _safe_ncurses_make(env):
        """Combine samtools, removing ncurses refs if not present on system.
        """
        with settings(warn_only=True):
            result = env.safe_run("make")
        # no ncurses, fix Makefile and rebuild
        if result.failed:
            env.safe_sed("Makefile", "-D_CURSES_LIB=1", "-D_CURSES_LIB=0")
            env.safe_sed("Makefile", "-lcurses", "# -lcurses")
            env.safe_run("make clean")
            env.safe_run("make")
        install_dir = shared._get_bin_dir(env)
        for fname in env.safe_run_output("ls -1 samtools bcftools/bcftools bcftools/vcfutils.pl misc/wgsim").split("\n"):
            env.safe_sudo("cp -f %s %s" % (fname.rstrip("\r"), install_dir))
    _get_install(url, env, _safe_ncurses_make)

def install_gemini(env):
    """A lightweight db framework for disease and population genetics.
    https://github.com/arq5x/gemini
    """
    version = "0.6.4"
    if versioncheck.up_to_date(env, "gemini -v", version, stdout_flag="gemini"):
        return
    elif not shared._executable_not_on_path("gemini -v"):
        env.safe_run("gemini update")
    else:
        iurl = "https://raw.github.com/arq5x/gemini/master/gemini/scripts/gemini_install.py"
        data_dir = os.path.join(env.system_install,
                                "local" if env.system_install.find("/local") == -1 else "",
                                "share", "gemini")
        with _make_tmp_dir(ext="-gemini") as work_dir:
            with cd(work_dir):
                if env.safe_exists(os.path.basename(iurl)):
                    env.safe_run("rm -f %s" % os.path.basename(iurl))
                installer = shared._remote_fetch(env, iurl)
                env.safe_run("%s %s %s %s %s" %
                             (_python_cmd(env), installer, "" if env.use_sudo else "--nosudo",
                              env.system_install, data_dir))
                env.safe_run("rm -f gemini_install.py")

@_if_not_installed("vtools")
def install_varianttools(env):
    """Annotation, selection, and analysis of variants in the context of next-gen sequencing analysis.
    http://varianttools.sourceforge.net/
    """
    version = "1.0.6"
    url = "http://downloads.sourceforge.net/project/varianttools/" \
          "{ver}/variant_tools-{ver}-src.tar.gz".format(ver=version)
    _get_install(url, env, _python_make)

@_if_not_installed("pseq")
def install_plink_seq(env):
    """A toolset for working with human genetic variation data.
    http://atgu.mgh.harvard.edu/plinkseq/
    """
    version = "0.08"
    url = "http://atgu.mgh.harvard.edu/plinkseq/dist/" \
          "version-{v}/plinkseq-{v}-x86_64.tar.gz".format(v=version)
    def _plink_copy(env):
        for x in ["pseq"]:
            env.safe_sudo("cp {0} {1}/bin".format(x, env.system_install))
    _get_install(url, env, _plink_copy)

@_if_not_installed("dwgsim")
def install_dwgsim(env):
    """DWGSIM: simulating NGS data and evaluating mappings and variant calling.
    http://sourceforge.net/apps/mediawiki/dnaa/index.php?title=Main_Page
    """
    version = "0.1.10"
    samtools_version = "0.1.18"
    url = "http://downloads.sourceforge.net/project/dnaa/dwgsim/" \
          "dwgsim-{0}.tar.gz".format(version)
    samtools_url = "http://downloads.sourceforge.net/project/samtools/samtools/" \
                   "{ver}/samtools-{ver}.tar.bz2".format(ver=samtools_version)
    def _get_samtools(env):
        shared._remote_fetch(env, samtools_url)
        env.safe_run("tar jxf samtools-{0}.tar.bz2".format(samtools_version))
        env.safe_run("ln -s samtools-{0} samtools".format(samtools_version))
    _get_install(url, env, _make_copy("ls -1 dwgsim dwgsim_eval scripts/dwgsim_pileup_eval.pl"),
                 post_unpack_fn=_get_samtools)

@_if_not_installed("fastqc --version")
def install_fastqc(env):
    """A quality control tool for high throughput sequence data.
    http://www.bioinformatics.babraham.ac.uk/projects/fastqc/
    """
    version = "0.10.1"
    url = "http://www.bioinformatics.bbsrc.ac.uk/projects/fastqc/" \
          "fastqc_v%s.zip" % version
    executable = "fastqc"
    install_dir = _symlinked_java_version_dir("fastqc", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_run("unzip %s" % out_file)
                with cd("FastQC"):
                    env.safe_sudo("chmod a+rwx %s" % executable)
                    env.safe_sudo("mv * %s" % install_dir)
                env.safe_sudo("ln -s %s/%s %s/bin/%s" % (install_dir, executable,
                                                         env.system_install, executable))


@_if_not_installed("fastq_screen")
def install_fastq_screen(env):
    """A screening application for high througput sequence data.
    http://www.bioinformatics.babraham.ac.uk/projects/fastq_screen/
    """
    version = "0.4"
    url = "http://www.bioinformatics.babraham.ac.uk/projects/fastq_screen/" \
          "fastq_screen_v%s.tar.gz" % version
    install_dir = shared._symlinked_shared_dir("fastqc_screen", version, env)
    executable = "fastq_screen"
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_run("tar -xzvpf %s" % out_file)
                with cd("fastq_screen_v%s" % version):
                    env.safe_sudo("mv * %s" % install_dir)
                env.safe_sudo("ln -s %s/%s %s/bin/%s" % (install_dir, executable,
                                                         env.system_install, executable))

def install_bedtools(env):
    """A flexible suite of utilities for comparing genomic features.
    https://code.google.com/p/bedtools/
    """
    version = "2.17.0"
    if versioncheck.up_to_date(env, "bedtools --version", version, stdout_flag="bedtools"):
        return
    url = "https://bedtools.googlecode.com/files/" \
          "BEDTools.v%s.tar.gz" % version
    _get_install(url, env, _make_copy("ls -1 bin/*"))

_shrec_run = """
#!/usr/bin/perl
use warnings;
use strict;
use FindBin qw($RealBin);
use Getopt::Long;

my @java_args;
my @args;
foreach (@ARGV) {
  if (/^\-X/) {push @java_args,$_;}
  else {push @args,$_;}}
system("java -cp $RealBin @java_args Shrec @args");
"""

@_if_not_installed("shrec")
def install_shrec(env):
    """Shrec is a bioinformatics tool for error correction of HTS read data.
    http://sourceforge.net/projects/shrec-ec/
    """
    version = "2.2"
    url = "http://downloads.sourceforge.net/project/shrec-ec/SHREC%%20%s/bin.zip" % version
    install_dir = _symlinked_java_version_dir("shrec", version, env)
    if install_dir:
        shrec_script = "%s/shrec" % install_dir
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_run("unzip %s" % out_file)
                env.safe_sudo("mv *.class %s" % install_dir)
                for line in _shrec_run.split("\n"):
                    if line.strip():
                        env.safe_append(shrec_script, line, use_sudo=env.use_sudo)
                env.safe_sudo("chmod a+rwx %s" % shrec_script)
                env.safe_sudo("ln -s %s %s/bin/shrec" % (shrec_script, env.system_install))

def install_echo(env):
    """ECHO: A reference-free short-read error correction algorithm
    http://uc-echo.sourceforge.net/
    """
    version = "1_12"
    url = "http://downloads.sourceforge.net/project/uc-echo/source%20release/" \
          "echo_v{0}.tgz".format(version)
    _get_install_local(url, env, _make_copy())

# -- Analysis

def install_picard(env):
    """Command-line utilities that manipulate BAM files with a Java API.
    http://picard.sourceforge.net/
    """
    version = "1.96"
    url = "http://downloads.sourceforge.net/project/picard/" \
          "picard-tools/%s/picard-tools-%s.zip" % (version, version)
    _java_install("picard", version, url, env)

def install_alientrimmer(env):
    """
    Adapter removal tool
    http://www.ncbi.nlm.nih.gov/pubmed/23912058
    """
    version = "0.3.2"
    url = ("ftp://ftp.pasteur.fr/pub/gensoft/projects/AlienTrimmer/"
           "AlienTrimmer_%s.tar.gz" % version)
    _java_install("AlienTrimmer", version, url, env)

def install_rnaseqc(env):
    """Quality control metrics for RNA-seq data
    https://www.broadinstitute.org/cancer/cga/rna-seqc
    """
    version = "1.1.7"
    url = ("http://www.broadinstitute.org/cancer/cga/sites/default/files/"
           "data/tools/rnaseqc/RNA-SeQC_v%s.jar" % version)
    install_dir = _symlinked_java_version_dir("RNA-SeQC", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_sudo("mv %s %s" % (out_file, install_dir))

def install_gatk(env):
    """GATK-lite: library for writing efficient analysis tools using next-generation sequencing data
    http://www.broadinstitute.org/gatk/
    """
    # Install main gatk executable
    version = "2.3-9-gdcdccbb"
    ext = ".tar.bz2"
    url = "ftp://anonymous:anon@ftp.broadinstitute.org/pub/gsa/GenomeAnalysisTK/"\
          "GenomeAnalysisTKLite-%s%s" % (version, ext)
    _java_install("gatk", version, url, env)

def install_varscan(env):
    """Variant detection in massively parallel sequencing data
    http://varscan.sourceforge.net/
    """
    version = "2.3.6"
    url = "http://downloads.sourceforge.net/project/varscan/VarScan.v%s.jar" % version
    install_dir = _symlinked_java_version_dir("varscan", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_sudo("mv %s %s" % (out_file, install_dir))

def install_mutect(env):
    version = "1.1.5"
    url = "https://github.com/broadinstitute/mutect/releases/download/" \
          "%s/muTect-%s-bin.zip" % (version, version)
    install_dir = _symlinked_java_version_dir("mutect", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                out_file = shared._remote_fetch(env, url)
                env.safe_run("unzip %s" % out_file)
                env.safe_sudo("mv *.jar version.txt LICENSE* %s" % install_dir)

@_if_not_installed("bam")
def install_bamutil(env):
    """Utilities for working with BAM files, from U of M Center for Statistical Genetics.
    http://genome.sph.umich.edu/wiki/BamUtil
    """
    version = "1.0.7"
    url = "http://genome.sph.umich.edu/w/images/5/5d/BamUtilLibStatGen.%s.tgz" % version
    _get_install(url, env, _make_copy("ls -1 bamUtil/bin/bam"),
                 dir_name="bamUtil_%s" % version)

@_if_not_installed("tabix")
def install_tabix(env):
    """Generic indexer for TAB-delimited genome position files
    http://samtools.sourceforge.net/tabix.shtml
    """
    version = "0.2.6"
    url = "http://downloads.sourceforge.net/project/samtools/tabix/tabix-%s.tar.bz2" % version
    _get_install(url, env, _make_copy("ls -1 tabix bgzip"))

@_if_not_installed("disambiguate.py")
def install_disambiguate(env):
    """a  tool for disambiguating reads aligning to multiple genomes
    https://github.com:mjafin/disambiguate
    """
    repository = "git clone https://github.com/mjafin/disambiguate.git"
    _get_install(repository, env, _python_make)

def install_grabix(env):
    """a wee tool for random access into BGZF files
    https://github.com/arq5x/grabix
    """
    version = "0.1.2"
    revision = "a78cbaf488"
    try:
        uptodate = versioncheck.up_to_date(env, "grabix", version, stdout_flag="version:")
    # Old versions will not have any version information
    except IOError:
        uptodate = False
    if uptodate:
        return
    repository = "git clone https://github.com/arq5x/grabix.git"
    _get_install(repository, env, _make_copy("ls -1 grabix"),
                 revision=revision)

@_if_not_installed("pbgzip")
def install_pbgzip(env):
    """Parallel blocked bgzip -- compatible with bgzip but with thread support.
    https://github.com/nh13/samtools/tree/master/pbgzip
    """
    repository = "git clone https://github.com/chapmanb/samtools.git"
    revision = "2cce3ffa97"
    def _build(env):
        with cd("pbgzip"):
            env.safe_run("make")
            install_dir = shared._get_bin_dir(env)
            env.safe_sudo("cp -f pbgzip %s" % (install_dir))
    _get_install(repository, env, _build, revision=revision)

def install_snpeff(env):
    """Variant annotation and effect prediction tool.
    http://snpeff.sourceforge.net/
    """
    version = "3_4"
    genomes = []
    #genomes = ["GRCh37.74", "hg19", "GRCm38.74", "athalianaTair10"]
    url = "http://downloads.sourceforge.net/project/snpeff/" \
          "snpEff_v%s_core.zip" % version
    genome_url_base = "http://downloads.sourceforge.net/project/snpeff/"\
                      "databases/v%s/snpEff_v%s_%s.zip"
    install_dir = _symlinked_java_version_dir("snpeff", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                dir_name = _fetch_and_unpack(url)
                with cd(dir_name):
                    env.safe_sudo("mv *.jar %s" % install_dir)
                    env.safe_run("sed -i.bak -e 's/^data_dir.*=.*/data_dir = %s\/data/' %s" %
                                 (install_dir.replace("/", "\/"), "snpEff.config"))
                    env.safe_run("chmod a+r *.config")
                    env.safe_sudo("mv *.config %s" % install_dir)
                    data_dir = os.path.join(install_dir, "data")
                    env.safe_sudo("mkdir %s" % data_dir)
                    for org in genomes:
                        if not env.safe_exists(os.path.join(data_dir, org)):
                            gurl = genome_url_base % (version, version, org)
                            _fetch_and_unpack(gurl, need_dir=False)
                            env.safe_sudo("mv data/%s %s" % (org, data_dir))

def install_vep(env):
    """Variant Effects Predictor (VEP) from Ensembl.
    http://ensembl.org/info/docs/variation/vep/index.html
    """
    version = "branch-ensembl-74"
    url = "http://cvs.sanger.ac.uk/cgi-bin/viewvc.cgi/ensembl-tools/scripts/" \
          "variant_effect_predictor.tar.gz?view=tar&root=ensembl" \
          "&pathrev={0}".format(version)
    def _vep_install(env):
        env.safe_run("export FTP_PASSIVE=1 && perl INSTALL.pl -a a")
    _get_install_local(url, env, _vep_install)

@_if_not_installed("bamtools")
def install_bamtools(env):
    """command-line toolkit for working with BAM data
    https://github.com/pezmaster31/bamtools
    """
    version = "3fe66b9"
    repository = "git clone --recursive https://github.com/pezmaster31/bamtools.git"
    def _cmake_bamtools(env):
        env.safe_run("mkdir build")
        with cd("build"):
            env.safe_run("cmake ..")
            env.safe_run("make")
        env.safe_sudo("cp bin/* %s" % shared._get_bin_dir(env))
        env.safe_sudo("cp lib/* %s" % shared._get_lib_dir(env))
    _get_install(repository, env, _cmake_bamtools,
                 revision=version)

@_if_not_installed("ogap")
def install_ogap(env):
    """gap opening realigner for BAM data streams
    https://github.com/ekg/ogap
    """
    version = "652c525"
    repository = "git clone --recursive https://github.com/ekg/ogap.git"
    _get_install(repository, env, _make_copy("ls ogap"),
                 revision=version)

def _install_samtools_libs(env):
    repository = "svn co --non-interactive " \
                 "https://samtools.svn.sourceforge.net/svnroot/samtools/trunk/samtools"
    def _samtools_lib_install(env):
        lib_dir = _get_lib_dir(env)
        include_dir = os.path.join(env.system_install, "include", "bam")
        env.safe_run("make")
        env.safe_sudo("mv -f libbam* %s" % lib_dir)
        env.safe_sudo("mkdir -p %s" % include_dir)
        env.safe_sudo("mv -f *.h %s" % include_dir)
    check_dir = os.path.join(_get_include_dir(env), "bam")
    if not env.safe_exists(check_dir):
        _get_install(repository, env, _samtools_lib_install)

def _install_boost(env):
    version = "1.49.0"
    url = "http://downloads.sourceforge.net/project/boost/boost" \
          "/%s/boost_%s.tar.bz2" % (version, version.replace(".", "_"))
    check_version = "_".join(version.split(".")[:2])
    boost_dir = os.path.join(env.system_install, "boost")
    boost_version_file = os.path.join(boost_dir, "include", "boost", "version.hpp")
    def _boost_build(env):
        env.safe_run("./bootstrap.sh --prefix=%s --with-libraries=thread" % boost_dir)
        env.safe_run("./b2")
        env.safe_sudo("./b2 install")
    thread_lib = "libboost_thread.so.%s" % version
    final_thread_lib = os.path.join(env.system_install, "lib", thread_lib)
    if (not env.safe_exists(boost_version_file) or not env.safe_contains(boost_version_file, check_version)
          or not env.safe_exists(final_thread_lib)):
        _get_install(url, env, _boost_build)
        orig_lib = os.path.join(boost_dir, "lib", thread_lib)
        if not env.safe_exists(final_thread_lib):
            env.safe_sudo("ln -s %s %s" % (orig_lib, final_thread_lib))

def _cufflinks_configure_make(env):
    orig_eigen = "%s/include/eigen3" % env.system_install
    need_eigen = "%s/include/eigen3/include" % env.system_install
    if not env.safe_exists(need_eigen):
        env.safe_sudo("ln -s %s %s" % (orig_eigen, need_eigen))
    env.safe_run("./configure --disable-werror --prefix=%s --with-eigen=%s"
                 % (env.system_install, orig_eigen))
    #run("./configure --disable-werror --prefix=%s --with-eigen=%s" \
    #    " --with-boost=%s/boost" % (env.system_install, orig_eigen, env.system_install))
    env.safe_run("make")
    env.safe_sudo("make install")

@_if_not_installed("tophat")
def SRC_install_tophat(env):
    """TopHat is a fast splice junction mapper for RNA-Seq reads
    http://tophat.cbcb.umd.edu/
    """
    _install_samtools_libs(env)
    _install_boost(env)
    default_version = "2.0.9"
    version = env.get("tool_version", default_version)
    url = "http://tophat.cbcb.umd.edu/downloads/tophat-%s.tar.gz" % version
    _get_install(url, env, _cufflinks_configure_make)

@_if_not_installed("cufflinks")
def SRC_install_cufflinks(env):
    """Cufflinks assembles transcripts and tests for differential expression and regulation in RNA-Seq samples.
    http://cufflinks.cbcb.umd.edu/
    """
    _install_samtools_libs(env)
    _install_boost(env)
    default_version = "2.1.1"
    version = env.get("tool_version", default_version)
    url = "http://cufflinks.cbcb.umd.edu/downloads/cufflinks-%s.tar.gz" % version
    _get_install(url, env, _cufflinks_configure_make)

def install_tophat(env):
    """TopHat is a fast splice junction mapper for RNA-Seq reads
    http://tophat.cbcb.umd.edu/
    """
    default_version = "2.0.9"
    version = env.get("tool_version", default_version)
    if versioncheck.is_version(env, "tophat", version, args="--version", stdout_flag="TopHat"):
        env.logger.info("tophat version {0} is up to date; not installing"
            .format(version))
        return
    platform = "OSX" if env.distribution == "macosx" else "Linux"
    url = "http://tophat.cbcb.umd.edu/downloads/" \
          "tophat-%s.%s_x86_64.tar.gz" % (version, platform)

    _get_install(url, env,
                 _make_copy("find . -perm -100 -type f", do_make=False))

install_tophat2 = install_tophat

@_if_not_installed("cufflinks")
def install_cufflinks(env):
    """Cufflinks assembles transcripts and tests for differential expression and regulation in RNA-Seq samples.
    http://cufflinks.cbcb.umd.edu/
    """
    default_version = "2.1.1"
    version = env.get("tool_version", default_version)
    url = "http://cufflinks.cbcb.umd.edu/downloads/" \
          "cufflinks-%s.Linux_x86_64.tar.gz" % version
    _get_install(url, env, _make_copy("find . -perm -100 -type f",
                                      do_make=False))

# --- Assembly

@_if_not_installed("ABYSS")
def install_abyss(env):
    """Assembly By Short Sequences - a de novo, parallel, paired-end sequence assembler.
    http://www.bcgsc.ca/platform/bioinfo/software/abyss
    """
    # XXX check for no sparehash on non-ubuntu systems
    default_version = "1.3.4"
    version = env.get("tool_version", default_version)
    url = "http://www.bcgsc.ca/downloads/abyss/abyss-%s.tar.gz" % version
    def _remove_werror_get_boost(env):
        env.safe_sed("configure", " -Werror", "")
        # http://osdir.com/ml/abyss-users-science/2011-10/msg00108.html
        url = "http://downloads.sourceforge.net/project/boost/boost/1.47.0/boost_1_47_0.tar.bz2"
        dl_file = shared._remote_fetch(env, url)
        env.safe_run("tar jxf %s" % dl_file)
        env.safe_run("ln -s boost_1_47_0/boost boost")
    _get_install(url, env, _configure_make, post_unpack_fn=_remove_werror_get_boost)

def install_transabyss(env):
    """Analyze ABySS multi-k-assembled shotgun transcriptome data.
    http://www.bcgsc.ca/platform/bioinfo/software/trans-abyss
    """
    version = "1.4.4"
    url = "http://www.bcgsc.ca/platform/bioinfo/software/trans-abyss/" \
          "releases/%s/trans-ABySS-v%s.tar.gz" % (version, version)
    _get_install_local(url, env, _make_copy(do_make=False))

@_if_not_installed("velvetg")
def install_velvet(env):
    """Sequence assembler for very short reads.
    http://www.ebi.ac.uk/~zerbino/velvet/
    """
    default_version = "1.2.08"
    version = env.get("tool_version", default_version)
    url = "http://www.ebi.ac.uk/~zerbino/velvet/velvet_%s.tgz" % version
    def _fix_library_order(env):
        """Fix library order problem in recent gcc versions
        http://biostar.stackexchange.com/questions/13713/
        error-installing-velvet-assembler-1-1-06-on-ubuntu-server
        """
        env.safe_sed("Makefile", "Z_LIB_FILES=-lz", "Z_LIB_FILES=-lz -lm")
    _get_install(url, env, _make_copy("find . -perm -100 -name 'velvet*'"),
                 post_unpack_fn=_fix_library_order)

@_if_not_installed("Ray")
def install_ray(env):
    """Ray -- Parallel genome assemblies for parallel DNA sequencing
    http://denovoassembler.sourceforge.net/
    """
    default_version = "2.2.0"
    version = env.get("tool_version", default_version)
    url = "http://downloads.sourceforge.net/project/denovoassembler/Ray-v%s.tar.bz2" % version
    def _ray_do_nothing(env):
        return
    _get_install(url, env, _make_copy("find . -name Ray"),
                 post_unpack_fn=_ray_do_nothing)

def install_trinity(env):
    """Efficient and robust de novo reconstruction of transcriptomes from RNA-seq data.
    http://trinityrnaseq.sourceforge.net/
    """
    version = "r2012-10-05"
    url = "http://downloads.sourceforge.net/project/trinityrnaseq/" \
          "trinityrnaseq_%s.tgz" % version
    def _remove_werror(env):
        env.safe_sed("trinity-plugins/jellyfish/Makefile.in", " -Werror", "")
    _get_install_local(url, env, _make_copy(),
                       post_unpack_fn=_remove_werror)

def install_cortex_var(env):
    """De novo genome assembly and variation analysis from sequence data.
    http://cortexassembler.sourceforge.net/index_cortex_var.html
    """
    version = "1.0.5.21"
    url = "http://downloads.sourceforge.net/project/cortexassembler/cortex_var/" \
          "latest/CORTEX_release_v{0}.tgz".format(version)
    def _cortex_build(env):
        env.safe_sed("Makefile", "\-L/full/path/\S*",
                     "-L{0}/lib -L/usr/lib -L/usr/local/lib".format(env.system_install))
        env.safe_sed("Makefile", "^IDIR_GSL =.*$",
                     "IDIR_GSL={0}/include -I/usr/include -I/usr/local/include".format(env.system_install))
        env.safe_sed("Makefile", "^IDIR_GSL_ALSO =.*$",
                     "IDIR_GSL_ALSO={0}/include/gsl -I/usr/include/gsl -I/usr/local/include/gsl".format(
                         env.system_install))
        with cd("libs/gsl-1.15"):
            env.safe_run("make clean")
        with cd("libs/htslib"):
            env.safe_run("make clean")
            env.safe_run("make")
        for cols in ["1", "2", "3", "4", "5"]:
            for kmer in ["31", "63", "95"]:
                env.safe_run("make MAXK={0} NUM_COLS={1} cortex_var".format(kmer, cols))
        with cd("scripts/analyse_variants/needleman_wunsch"):
            env.safe_sed("Makefile", "string_buffer.c", "string_buffer.c -lz")
            # Fix incompatibilities with gzfile struct in zlib 1.2.6+
            for fix_gz in ["libs/string_buffer/string_buffer.c", "libs/bioinf/bioinf.c",
                           "libs/string_buffer/string_buffer.h", "libs/bioinf/bioinf.h"]:
                env.safe_sed(fix_gz, "gzFile \*", "gzFile ")
                env.safe_sed(fix_gz, "gzFile\*", "gzFile")
            env.safe_run("make")
    _get_install_local(url, env, _cortex_build)

def install_bcbio_variation(env):
    """Toolkit to analyze genomic variation data with comparison and ensemble approaches.
    https://github.com/chapmanb/bcbio.variation
    """
    version = "0.1.6"
    url = "https://github.com/chapmanb/bcbio.variation/releases/download/" \
          "v%s/bcbio.variation-%s-standalone.jar" % (version, version)
    install_dir = _symlinked_java_version_dir("bcbio_variation", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                jar_file = shared._remote_fetch(env, url)
                env.safe_sudo("mv %s %s" % (jar_file, install_dir))

# --- ChIP-seq

@_if_not_installed("macs14")
def install_macs(env):
    """Model-based Analysis for ChIP-Seq.
    http://liulab.dfci.harvard.edu/MACS/
    """
    default_version = "1.4.2"
    version = env.get("tool_version", default_version)
    url = "https://github.com/downloads/taoliu/MACS/" \
          "MACS-%s.tar.gz" % version
    _get_install(url, env, _python_make)

# --- Structural variation
@_if_not_installed("hydra")
def install_hydra(env):
    """Hydra detects structural variation breakpoints in both unique and duplicated genomic regions.
    https://code.google.com/p/hydra-sv/
    """
    version = "0.5.3"
    url = "http://hydra-sv.googlecode.com/files/Hydra.v{0}.tar.gz".format(version)
    def clean_libs(env):
        env.safe_run("make clean")
    _get_install(url, env, _make_copy("ls -1 bin/* scripts/*"),
                 post_unpack_fn=clean_libs)

def install_freec(env):
    """Control-FREEC: a tool for detection of copy number changes and allelic imbalances.
    http://bioinfo-out.curie.fr/projects/freec/
    """
    version = "6.4"
    if env.distribution in ["ubuntu", "debian"]:
        if env.is_64bit:
            url = "http://bioinfo-out.curie.fr/projects/freec/src/FREEC_Linux64.tar.gz"
        else:
            url = "http://bioinfo-out.curie.fr/projects/freec/src/FREEC_LINUX32.tar.gz"

        if not versioncheck.up_to_date(env, "freec", version, stdout_index=1):
            _get_install(url, env, _make_copy("find . -name 'freec'"), dir_name=".")

@_if_not_installed("CRISP.py")
def install_crisp(env):
    """Detect SNPs and short indels from pooled sequencing data.
    https://sites.google.com/site/vibansal/software/crisp/
    """
    version = "5"
    url = "https://sites.google.com/site/vibansal/software/crisp/" \
          "CRISP-linux-v{0}.tar.gz".format(version)
    def _make_executable():
        env.safe_run("chmod a+x *.py")
    _get_install(url, env, _make_copy("ls -1 CRISP.py crisp_to_vcf.py",
                                      premake_cmd=_make_executable,
                                      do_make=False))

@_if_not_installed("run_pipeline.pl")
def install_tassel(env):
    """TASSEL: evaluate traits associations, evolutionary patterns, and linkage disequilibrium.
    http://www.maizegenetics.net/index.php?option=com_content&task=view&id=89&/Itemid=119
    """
    version = "4.0"
    url = "http://www.maizegenetics.net/tassel/tassel{0}_standalone.zip".format(version)
    executables = ["start_tassel.pl", "run_pipeline.pl"]
    install_dir = _symlinked_java_version_dir("tassel", version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                dl_file = shared._remote_fetch(env, url)
                env.safe_run("unzip %s" % dl_file)
                with cd("tassel{0}_standalone".format(version)):
                    for x in executables:
                        env.safe_sed(x, "^my \$top.*;",
                                     "use FindBin qw($RealBin); my $top = $RealBin;")
                        env.safe_sudo("chmod a+rwx %s" % x)
                    env.safe_sudo("mv * %s" % install_dir)
                for x in executables:
                    env.safe_sudo("ln -s %s/%s %s/bin/%s" % (install_dir, x,
                                                             env.system_install, x))

@_if_not_installed("ustacks")
def install_stacks(env):
    """Stacks: build loci out of a set of short-read sequenced samples.
    http://creskolab.uoregon.edu/stacks/
    """
    version = "0.9999"
    url = "http://creskolab.uoregon.edu/stacks/source/" \
          "stacks-{0}.tar.gz".format(version)
    _get_install(url, env, _configure_make)

@_if_not_installed("seqlogo")
def install_weblogo(env):
    """Weblogo
    http://weblogo.berkeley.edu/
    """
    version = "2.8.2"
    url = "http://weblogo.berkeley.edu/release/weblogo.%s.tar.gz" % version
    _get_install(url, env, _make_copy("find . -perm -100 -type f", do_make=False))
    def _cp_pm(env):
        for perl_module in ["template.pm", "logo.pm", "template.eps"]:
            env.safe_sudo("cp %s %s/lib/perl5" % (perl_module, env.system_install))
    _get_install(url, env, _cp_pm(env))

########NEW FILE########
__FILENAME__ = bio_proteomics
"""Install proteomics tools not currently packaged.
"""

import os
import re

from fabric.api import cd
from fabric.context_managers import prefix

from shared import (_if_not_installed, _make_tmp_dir,
                    _get_install, _make_copy,
                    _java_install, _symlinked_java_version_dir,
                    _get_bin_dir, _get_install_subdir,
                    _fetch_and_unpack,
                    _create_python_virtualenv,
                    _get_bitbucket_download_url,
                    _write_to_file)
from cloudbio.galaxy.utils import _chown_galaxy

# Tools from Tabb lab are only available via TeamCity builds that
# and the artifacts eventually are deleted (I think), storing versions
# for CloudBioLinux at getgalaxyp.msi.umn.edu for safe keeping.
PROTEOMICS_APP_ARCHIVE_URL = "http://getgalaxyp.msi.umn.edu/downloads"


# TODO: Define TPP install root
@_if_not_installed("xinteract")
def install_transproteomic_pipeline(env):
    """
    """
    ## version should be of form X.X.X-codename
    default_version = "4.6.1-occupy"
    version = env.get("tool_version", default_version)
    version_parts = re.match("(\d\.\d)\.(\d)-(.*)", version)
    major_version = version_parts.group(1)
    revision = version_parts.group(2)
    codename = version_parts.group(3)
    if revision == "0":
        download_rev = ""
    else:
        download_rev = ".%s" % revision
    download_version = ("%s%s" % (major_version, download_rev))
    url_pieces = (major_version, codename, revision, download_version)
    url = 'http://sourceforge.net/projects/sashimi/files/Trans-Proteomic Pipeline (TPP)/TPP v%s (%s) rev %s/TPP-%s.tgz' % url_pieces

    def _chdir_src(work_cmd):
        def do_work(env):
            src_dir = "trans_proteomic_pipeline/src" if version == "4.6.1-occupy" else "src"
            with cd(src_dir):
                env.safe_append("Makefile.config.incl", "TPP_ROOT=%s/" % env["system_install"])
                env.safe_append("Makefile.config.incl", "TPP_WEB=/tpp/")
                env.safe_append("Makefile.config.incl", "XSLT_PROC=/usr/bin/xsltproc")
                env.safe_append("Makefile.config.incl", "CGI_USERS_DIR=${TPP_ROOT}cgi-bin")
                work_cmd(env)
        return do_work

    def _make(env):
        env.safe_run("make")
        env.safe_sudo("make install")
    _get_install(url, env, _chdir_src(_make))


@_if_not_installed("omssacl")
def install_omssa(env):
    default_version = "2.1.9"
    version = env.get("tool_version", default_version)
    url = 'ftp://ftp.ncbi.nih.gov/pub/lewisg/omssa/%s/omssa-%s.linux.tar.gz' % (version, version)
    env.safe_sudo("mkdir -p '%s'" % env["system_install"])
    ## OMSSA really wants mods.xml, usermods.xml, etc... in the same directory
    ## so just copying everything there.
    _get_install(url, env, _make_copy(find_cmd="ls -1", do_make=False))


@_if_not_installed("OpenMSInfo")
def install_openms(env):
    """
    See comments above, working on getting this to compile from source. In
    the meantime installing from deb will have to do.
    """
    default_version = "1.10.0"
    version = env.get("tool_version", default_version)
    dot_version = version[0:version.rindex('.')]
    url = 'http://downloads.sourceforge.net/project/open-ms/OpenMS/OpenMS-%s/OpenMS-%s.tar.gz' % (dot_version, version)

    def _make(env):
        with cd("contrib"):
            env.safe_run("cmake -DINSTALL_PREFIX=%s ." % env.get('system_install'))
            env.safe_run("make")
        env.safe_run("cmake -DINSTALL_PREFIX=%s ." % env.get('system_install'))
        env.safe_run("make")
        env.safe_sudo("make install")
    _get_install(url, env, _make)


@_if_not_installed("LTQ-iQuant")
def install_tint_proteomics_scripts(env):
    default_version = "1.19.19"
    version = env.get("tool_version", default_version)
    url = "http://artifactory.msi.umn.edu/simple/ext-release-local/msi/umn/edu/tint-proteomics-scripts/%s/tint-proteomics-scripts-%s.zip" % (version, version)

    def install_fn(env, install_dir):
        env.safe_sudo("mv * '%s'" % install_dir)
        bin_dir = _get_bin_dir(env)
        for script in ["ITraqScanSummarizer", "LTQ-iQuant", "LTQ-iQuant-cli", "MgfFormatter"]:
            env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, script), bin_dir))
        env.safe_sudo("chmod +x '%s'/*" % bin_dir)

    _java_install("tint-proteomics-scripts", version, url, env, install_fn)


@_if_not_installed("ms2preproc")
def install_ms2preproc(env):
    default_version = "2009"
    version = env.get("tool_version", default_version)
    get_cmd = 'wget "http://software.steenlab.org/ms2preproc/ms2preproc.zip" -O ms2preproc.zip'

    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run(get_cmd)
            env.safe_run("unzip ms2preproc.zip")
            with cd("ms2preproc"):
                env.safe_run("mv ms2preproc-r2821-x86_64 ms2preproc-x86_64")
                env.safe_run("chmod +x ms2preproc-x86_64")
                install_dir = _get_bin_dir(env)
                env.safe_sudo("mv ms2preproc-x86_64 '%s'/ms2preproc" % install_dir)


@_if_not_installed("MZmine")
def install_mzmine(env):
    default_version = "2.10"
    version = env.get("tool_version", default_version)
    url = "http://downloads.sourceforge.net/project/mzmine/mzmine2/%s/MZmine-%s.zip" % (version, version)

    def install_fn(env, install_dir):
        ## Enhanced MZmine startup script that works when used a symbolic link and tailored for CloudBioLinux.
        _get_gist_script(env, "https://gist.github.com/jmchilton/5474421/raw/15f3b817fa82d5f5e2143ee08bd248efee951d6a/MZmine")
        # Hack for multi-user environment.
        env.safe_sudo("chmod -R o+w conf")
        env.safe_sudo("mv * '%s'" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "MZmine"), os.path.join(bin_dir, "MZmine")))

    _java_install("mzmine2", version, url, env, install_fn)


@_if_not_installed("SearchGUI")
def install_searchgui(env):
    default_version = "1.13.1"
    version = env.get("tool_version", default_version)
    url = "http://searchgui.googlecode.com/files/SearchGUI-%s_mac_and_linux.zip" % version

    def install_fn(env, install_dir):
        dir_name = "SearchGUI-%s_mac_and_linux" % version
        env.safe_sudo("tar -xf %s.tar" % dir_name)
        with cd(dir_name):
            _get_gist_script(env, "https://gist.github.com/jmchilton/5002161/raw/dc9fa36dd0e6eddcdf43cd2b659e4ecee5ad29df/SearchGUI")
            _get_gist_script(env, "https://gist.github.com/jmchilton/5002161/raw/b97fb4d9fe9927de1cfc5433dd1702252e9c0348/SearchCLI")
            # Fix known bug with SearchGUI version 1.12.2
            env.safe_sudo("find -iname \"*.exe\" -exec rename s/.exe// {} \;")
            # Hack for multi-user environment.
            env.safe_sudo("chmod -R o+w resources")
            env.safe_sudo("mv * '%s'" % install_dir)
            bin_dir = os.path.join(env.get("system_install"), "bin")
            env.safe_sudo("mkdir -p '%s'" % bin_dir)
            env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "SearchGUI"), os.path.join(bin_dir, "SearchGUI")))
            env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "SearchCLI"), os.path.join(bin_dir, "SearchCLI")))

    _unzip_install("SearchGUI", version, url, env, install_fn)


@_if_not_installed("psm_eval")
def install_psm_eval(env):
    default_version = "0.1.0"
    version = env.get("tool_version", default_version)
    url = "git clone https://github.com/jmchilton/psm-eval.git"

    def install_fn(env, install_dir):
        env.safe_sudo("cp -r psm-eval/* '%s'" % install_dir)
        _create_python_virtualenv(env, "psme", "%s/requirements.txt" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "psm_eval"), os.path.join(bin_dir, "psm_eval")))

    _unzip_install("psm_eval", version, url, env, install_fn)


@_if_not_installed("PeptideShaker")
def install_peptide_shaker(env):
    default_version = "0.20.1"
    version = env.get("tool_version", default_version)
    url = "http://peptide-shaker.googlecode.com/files/PeptideShaker-%s.zip" % version

    def install_fn(env, install_dir):
        _get_gist_script(env, "https://gist.github.com/jmchilton/5002161/raw/f1fe76d6e6eed99a768ed0b9f41c2d0a6a4b24b7/PeptideShaker")
        _get_gist_script(env, "https://gist.github.com/jmchilton/5002161/raw/8a17d5fb589984365284e55a98a455c2b47da54f/PeptideShakerCLI")
        # Hack for multi-user environment.
        env.safe_sudo("chmod -R o+w resources")
        env.safe_sudo("mv * '%s'" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "PeptideShaker"), os.path.join(bin_dir, "PeptideShaker")))
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "PeptideShakerCLI"), os.path.join(bin_dir, "PeptideShakerCLI")))

    _java_install("PeptideShaker", version, url, env, install_fn)


def _get_gist_script(env, url):
    name = url.split("/")[-1]
    env.safe_sudo("wget '%s'" % url)
    env.safe_sudo("chmod +x '%s'" % name)


@_if_not_installed("Mayu")
def install_mayu(env):
    default_version = "1.06"
    version = env.get("tool_version", default_version)
    url = "http://proteomics.ethz.ch/muellelu/web/LukasReiter/Mayu/package/Mayu.zip"

    def install_fn(env, install_dir):
        share_dir = _get_install_subdir(env, "share")
        env.safe_sudo("mv Mayu '%s'" % share_dir)
        bin_dir = _get_bin_dir(env)
        executable = "%s/Mayu" % bin_dir
        env.safe_sudo("""echo '#!/bin/bash\ncd %s/Mayu; perl Mayu.pl \"$@\"' > %s """ % (share_dir, executable))
        env.safe_sudo("chmod +x '%s'" % executable)

    _unzip_install("mayu", version, url, env, install_fn)


def install_pride_inspector(env):
    default_version = "1.3.0"
    version = env.get("tool_version", default_version)
    url = "http://pride-toolsuite.googlecode.com/files/pride-inspector-%s.zip" % version

    def install_fn(env, install_dir):
        _get_gist_script(env, "https://gist.github.com/jmchilton/5474788/raw/6bcffd8680ec0e0301af44961184529a1f76dd3b/pride-inspector")
        # Hack for multi-user environment.
        env.safe_sudo("chmod -R o+w log config")
        env.safe_sudo("mv * '%s'" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "pride-inspector"), os.path.join(bin_dir, "pride-inspector")))

    _unzip_install("pride_inspector", version, url, env, install_fn, "PRIDE_Inspector")


def install_pride_converter2(env):
    default_version = "2.0.17"
    version = env.get("tool_version", default_version)
    url = "http://pride-converter-2.googlecode.com/files/pride-converter-%s-bin.zip" % version

    def install_fn(env, install_dir):
        _get_gist_script(env, "https://gist.github.com/jmchilton/5475119/raw/4e9135ada5114ba149f3ebc8965aee242bfc776f/pride-converter")
        # Hack for multi-user environment.
        env.safe_sudo("mkdir log; chmod o+w log")
        env.safe_sudo("mv * '%s'" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' %s" % (os.path.join(install_dir, "pride-converter"), os.path.join(bin_dir, "pride-converter")))

    _unzip_install("pride_converter2", version, url, env, install_fn, ".")


def _unzip_install(pname, version, url, env, install_fn, dir_name="."):
    install_dir = _symlinked_java_version_dir(pname, version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                _fetch_and_unpack(url, need_dir=False)
                with cd(dir_name):
                    install_fn(env, install_dir)


@_if_not_installed("SuperHirnv03")
def install_superhirn(env):
    default_version = "0.03"
    version = env.get("tool_version", default_version)
    url = "https://github.com/jmchilton/SuperHirn/zipball/%s/SuperHirn.zip" % version

    def _chdir(work_cmd):
        def do_work(env):
            with cd("SuperHirnv03/make"):
                work_cmd(env)
        return do_work

    _get_install(url, env, _chdir(_make_copy(find_cmd="find -perm -100 -name 'SuperHirn*'")))


@_if_not_installed("percolator")
def install_percolator(env):
    default_version = "2_04"
    version = env.get("tool_version", default_version)
    url = "https://github.com/downloads/percolator/percolator/percolator_%s_full_src.tar.gz" % version

    def make(env):
        with cd(".."):
            env.safe_run("env")
            env.safe_run("cmake -DCMAKE_INSTALL_PREFIX='%s' . " % env.system_install)
            env.safe_run("make -j8")
            env.safe_sudo("make install")

    _get_install(url, env, make)


@_if_not_installed("PepNovo")
def install_pepnovo(env):
    default_version = "20120423"
    version = env.get("tool_version", default_version)
    url = "http://proteomics.ucsd.edu/Downloads/PepNovo.%s.zip" % version

    def install_fn(env, install_dir):
        with cd("src"):
            env.safe_run("make")
            env.safe_sudo("mkdir -p '%s/bin'" % env.system_install)
            env.safe_sudo("mkdir -p '%s/share/pepnovo'" % env.system_install)
            env.safe_sudo("mv PepNovo_bin '%s/bin/PepNovo'" % env.system_install)
            env.safe_sudo("cp -r '../Models' '%s/share/pepnovo'" % env.system_install)

    _unzip_install("pepnovo", version, url, env, install_fn)


@_if_not_installed("crux")
def install_crux(env):
    default_version = "1.39"
    version = env.get("tool_version", default_version)
    url = "http://noble.gs.washington.edu/proj/crux/download/crux_%s-x86_64-Linux.zip" % version

    def _move(env):
        bin_dir = _get_bin_dir(env)
        env.safe_sudo("mv bin/* '%s'" % (bin_dir))

    _get_install(url, env, _move)


@_if_not_installed("Fido")
def install_fido(env):
    version = "2011"
    url = 'http://noble.gs.washington.edu/proj/fido/fido.tar.gz'

    # Adapted from Jorrit Boekel's mi-deployment fork
    # https://bitbucket.org/glormph/mi-deployment-protoeimcs
    def _chdir_src(work_cmd):
        def do_work(env):
            with cd("src/cpp"):
                env.safe_append('tmpmake', 'SHELL=/bin/bash')
                env.safe_append('tmpmake', 'prefix=%s' % env.get("system_install"))
                env.safe_append('tmpmake', 'CPPFLAGS=-Wall -ffast-math -march=x86-64 -pipe -O4 -g')
                env.safe_run('cat makefile |grep BINPATH -A 9999 >> tmpmake')
                env.safe_run('cp tmpmake makefile')
                work_cmd(env)
        return do_work

    _get_install(url, env, _chdir_src(_make_copy(find_cmd="find ../../bin -perm -100 -name 'Fido*'")))


def install_ipig(env):
    """ This tool is installed in Galaxy's jars dir """
    # This galaxy specific download probable doesn't belong in this file.
    default_version = "r5"
    version = env.get("tool_version", default_version)
    url = 'http://downloads.sourceforge.net/project/ipig/ipig_%s.zip' % version
    pkg_name = 'ipig'
    install_dir = os.path.join(env.galaxy_jars_dir, pkg_name)
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    install_cmd("mkdir -p %s" % install_dir)
    with cd(install_dir):
        install_cmd("wget %s -O %s" % (url, os.path.split(url)[-1]))
        install_cmd("unzip -u %s" % (os.path.split(url)[-1]))
        install_cmd("rm %s" % (os.path.split(url)[-1]))
        install_cmd('chown --recursive %s:%s %s' % (env.galaxy_user, env.galaxy_user, install_dir))


def install_peptide_to_gff(env):
    default_version = "master"
    version = env.get("tool_version", default_version)
    repository = "hg clone https://jmchilton@bitbucket.org/galaxyp/peptide_to_gff"

    def install_fn(env, install_dir):
        env.safe_sudo("cp -r peptide_to_gff/* '%s'" % install_dir)
        _create_python_virtualenv(env, "peptide_to_gff", "%s/requirements.txt" % install_dir)
        bin_dir = os.path.join(env.get("system_install"), "bin")
        env.safe_sudo("mkdir -p '%s'" % bin_dir)
        env.safe_sudo("ln -s '%s' '%s'" % (os.path.join(install_dir, "peptide_to_gff"), os.path.join(bin_dir, "peptide_to_gff")))

    _unzip_install("peptide_to_gff", version, repository, env, install_fn)


def install_galaxy_protk(env):
    """This method installs Ira Cooke's ProtK framework. Very galaxy specific,
    can only be installed in context of custom Galaxy tool.


    By default this will install ProtK from rubygems server, but if
    env.protk_version is set to <version>@<url> (e.g.
    1.1.5@https://bitbucket.org/iracooke/protk-working) the
    gem will be cloned with hg and installed from source.
    """
    if not env.get('galaxy_tool_install', False):
        from cloudbio.custom.galaxy import _prep_galaxy
        _prep_galaxy(env)
    default_version = "1.2.2"
    version = env.get("tool_version", default_version)
    version_and_revision = version
    install_from_source = version_and_revision.find("@") > 0
    # e.g. protk_version = 1.1.5@https://bitbucket.org/iracooke/protk-working
    if install_from_source:
        (version, revision) = version_and_revision.split("@")
        url = _get_bitbucket_download_url(revision, "https://bitbucket.org/iracooke/protk")
    else:
        version = version_and_revision

    ruby_version = "1.9.3"
    force_rvm_install = False
    with prefix("HOME=~%s" % env.galaxy_user):
        def rvm_exec(env, cmd="", rvm_cmd="use", with_gemset=False):
            target = ruby_version if not with_gemset else "%s@%s" % (ruby_version, "protk-%s" % version)
            prefix = ". $HOME/.rvm/scripts/rvm; rvm %s %s; " % (rvm_cmd, target)
            env.safe_sudo("%s %s" % (prefix, cmd), user=env.galaxy_user)
        if not env.safe_exists("$HOME/.rvm") or force_rvm_install:
            env.safe_sudo("curl -L get.rvm.io | bash -s stable; source ~%s/.rvm/scripts/rvm" % (env.galaxy_user), user=env.galaxy_user)
            rvm_exec(env, rvm_cmd="install")
            rvm_exec(env, cmd="rvm gemset create protk-%s" % version)
        if not install_from_source:
            # Typical rubygem install
            rvm_exec(env, "gem install  --no-ri --no-rdoc protk -v %s" % version, with_gemset=True)
        else:
            with cd("~%s" % env.galaxy_user):
                env.safe_sudo("rm -rf protk_source; hg clone '%s' protk_source" % url, user=env.galaxy_user)
                rvm_exec(env, "cd protk_source; gem build protk.gemspec; gem install protk", with_gemset=True)

        protk_properties = {}
        ## ProtK can set these up itself, should make that an option.
        protk_properties["tpp_root"] = os.path.join(env.galaxy_tools_dir, "transproteomic_pipeline", "default")
        protk_properties['openms_root'] = "/usr"  # os.path.join(env.galaxy_tools_dir, "openms", "default", "bin")
        ### Assumes omssa, blast, and transproteomic_pipeline CBL galaxy installs.
        protk_properties['omssa_root'] = os.path.join(env.galaxy_tools_dir, "omssa", "default", "bin")
        protk_properties['blast_root'] = os.path.join(env.galaxy_tools_dir, "blast+", "default")
        protk_properties['pwiz_root'] = os.path.join(env.galaxy_tools_dir, "transproteomic_pipeline", "default", "bin")
        # Other properties: log_file, blast_root
        env.safe_sudo("mkdir -p \"$HOME/.protk\"", user=env.galaxy_user)
        env.safe_sudo("mkdir -p \"$HOME/.protk/Databases\"", user=env.galaxy_user)
        import  yaml
        _write_to_file(yaml.dump(protk_properties), "/home/%s/.protk/config.yml" % env.galaxy_user, "0755")

        rvm_exec(env, "protk_setup.rb galaxyenv", with_gemset=True)

        install_dir = os.path.join(env.galaxy_tools_dir, "galaxy_protk", version)
        env.safe_sudo("mkdir -p '%s'" % install_dir)
        _chown_galaxy(env, install_dir)
        env.safe_sudo('ln -s -f "$HOME/.protk/galaxy/env.sh" "%s/env.sh"' % install_dir, user=env.galaxy_user)
        with cd(install_dir):
            with cd(".."):
                env.safe_sudo("ln -s -f '%s' default" % version)


@_if_not_installed("myrimatch")
def install_myrimatch(env):
    default_version = "2.1.131"
    _install_tabb_tool(env, default_version, "myrimatch-bin-linux-x86_64-gcc41-release", ["myrimatch"])


@_if_not_installed("pepitome")
def install_pepitome(env):
    default_version = "1.0.45"
    _install_tabb_tool(env, default_version, "pepitome-bin-linux-x86_64-gcc41-release", ["pepitome"])


@_if_not_installed("directag")
def install_directag(env):
    default_version = "1.3.62"
    _install_tabb_tool(env, default_version, "directag-bin-linux-x86_64-gcc41-release", ["adjustScanRankerScoreByGroup", "directag"])


@_if_not_installed("tagrecon")
def install_tagrecon(env):
    default_version = "1.4.63"
    # TODO: Should consider a better way to handle the unimod xml and blosum matrix.
    _install_tabb_tool(env, default_version, "tagrecon-bin-linux-x86_64-gcc41-release", ["tagrecon", "unimod.xml", "blosum62.fas"])


@_if_not_installed("idpQonvert")
def install_idpqonvert(env):
    default_version = "3.0.475"
    version = env.get("tool_version", default_version)
    url = "%s/idpQonvert_%s" % (PROTEOMICS_APP_ARCHIVE_URL, version)
    env.safe_run("wget --no-check-certificate -O %s '%s'" % ("idpQonvert", url))
    env.safe_run("chmod 755 idpQonvert")
    env.safe_sudo("mkdir -p '%s/bin'" % env["system_install"])
    env.safe_sudo("mv %s '%s/bin'" % ("idpQonvert", env["system_install"]))
    env.safe_sudo("chmod +x '%s/bin/idpQonvert'" % env["system_install"])


def _install_tabb_tool(env, default_version, download_name, exec_names):
    version = env.get("tool_version", default_version)
    url = "%s/%s-%s.tar.bz2" \
        % (PROTEOMICS_APP_ARCHIVE_URL, download_name, version.replace(".", "_"))
    _fetch_and_unpack(url, False)
    env.safe_sudo("mkdir -p '%s/bin'" % env["system_install"])
    for exec_name in exec_names:
        env.safe_sudo("mv %s '%s/bin'" % (exec_name, env["system_install"]))

########NEW FILE########
__FILENAME__ = bio_proteomics_wine
from fabric.api import cd

from shared import (_make_tmp_dir, _fetch_and_unpack, _write_to_file, _get_bin_dir)

import os


def install_proteomics_wine_env(env):
    script_src = env.get("setup_proteomics_wine_env_script")
    script_dest = "%s/bin/setup_proteomics_wine_env.sh" % env.get("system_install")
    if not env.safe_exists(script_dest):
        env.safe_put(script_src, script_dest, mode=0755, use_sudo=True)


def install_multiplierz(env):
    """
    Assumes your wine environment contains an install Python 2.6
    in C:\Python26.
    """
    wine_user = _get_wine_user(env)

    install_proteomics_wine_env(env)
    env.safe_sudo("setup_proteomics_wine_env.sh", user=wine_user)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _fetch_and_unpack("hg clone http://multiplierz.hg.sourceforge.net:8000/hgroot/multiplierz/multiplierz")
            with cd("multiplierz"):
                wine_prefix = _get_wine_prefix(env)
                env.safe_sudo("%s; wine %s/drive_c/Python26/python.exe setup.py install" % (_conf_wine(env), wine_prefix), user=wine_user)


def install_proteowizard(env):
    build_id = "85131"
    version = "3_0_4624"
    url = "http://teamcity.labkey.org:8080/repository/download/bt36/%s:id/pwiz-bin-windows-x86-vc100-release-%s.tar.bz2?guest=1" % (build_id, version)
    install_dir = env.get("install_dir")
    share_dir = "%s/share/proteowizard" % install_dir
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _fetch_and_unpack(url, need_dir=False)
            env.safe_sudo("cp -r . '%s'" % share_dir)
    proteowizard_apps = ["msconvert", "msaccess", "chainsaw", "msdiff", "mspicture", "mscat", "txt2mzml", "MSConvertGUI", "Skyline", "Topograph", "SeeMS"]
    for app in proteowizard_apps:
        setup_wine_wrapper(env, "%s/%s" % (share_dir, app))


def install_morpheus(env):
    url = "http://www.chem.wisc.edu/~coon/Downloads/Morpheus/latest/Morpheus.zip"  # TODO:
    install_dir = env.get("install_dir")
    share_dir = "%s/share/morpheus" % install_dir
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _fetch_and_unpack(url, need_dir=False)
            env.safe_sudo("cp -r Morpheus '%s'" % share_dir)
    morpheus_exes = ["morpheus_cl.exe", "Morpheus.exe"]
    for app in morpheus_exes:
        setup_wine_wrapper(env, "%s/%s" % (share_dir, app))


def setup_wine_wrapper(env, to):
    basename = os.path.basename(to)
    contents = """#!/bin/bash
setup_proteomics_wine_env.sh
export WINEPREFIX=$HOME/.wine-proteomics
wine %s "$@"
""" % to
    bin_dir = _get_bin_dir(env)
    dest = "%s/%s" % (bin_dir, basename)
    _write_to_file(contents, dest, '0755')


def _conf_wine(env):
    return "export WINEPREFIX=%s" % _get_wine_prefix(env)


def _get_wine_prefix(env):
    wine_user = _get_wine_user(env)
    return "~%s/.wine-proteomics" % wine_user


def _get_wine_user(env):
    return env.get("wine_user", env.get("user"))

########NEW FILE########
__FILENAME__ = cloudman
"""Custom install scripts for CloudMan environment.

From Enis Afgan: https://bitbucket.org/afgane/mi-deployment
"""
import os
import contextlib

from fabric.api import cd
from fabric.contrib.files import settings, hide

from cloudbio.custom.shared import (_make_tmp_dir, _setup_conf_file)
from cloudbio.cloudman import (_configure_cloudman, _configure_novnc,
    _configure_desktop, _configure_ec2_autorun)
from cloudbio.galaxy import _install_nginx

CDN_ROOT_URL = "http://userwww.service.emory.edu/~eafgan/content"
REPO_ROOT_URL = "https://bitbucket.org/afgane/mi-deployment/raw/tip"


def install_cloudman(env):
    """ A meta method for installing all of CloudMan components.
        Allows CloudMan and all of its dependencies to be installed via:
        fab -f fabfile.py -i <key> -H ubuntu@<IP> install_custom:cloudman
    """
    _configure_cloudman(env, use_repo_autorun=False)
    install_nginx(env)
    install_proftpd(env)
    install_sge(env)


def install_ec2_autorun(env):
    _configure_ec2_autorun(env)


def install_novnc(env):
    _configure_novnc(env)
    _configure_desktop(env)


def install_nginx(env):
    _install_nginx(env)


def install_proftpd(env):
    """Highly configurable GPL-licensed FTP server software.
    http://proftpd.org/
    """
    version = "1.3.4c"
    postgres_ver = "9.1"
    url = "ftp://ftp.tpnet.pl/pub/linux/proftpd/distrib/source/proftpd-%s.tar.gz" % version
    modules = "mod_sql:mod_sql_postgres:mod_sql_passwd"
    extra_modules = env.get("extra_proftp_modules", "")  # Comma separated list of extra modules
    if extra_modules:
        modules = "%s:%s" % (modules, extra_modules.replace(",", ":"))
    install_dir = os.path.join(env.install_dir, 'proftpd')
    remote_conf_dir = os.path.join(install_dir, "etc")
    # Skip install if already available
    if env.safe_exists(remote_conf_dir):
        env.logger.debug("ProFTPd seems to already be installed in {0}".format(install_dir))
        return
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s" % url)
            with settings(hide('stdout')):
                env.safe_run("tar xvzf %s" % os.path.split(url)[1])
            with cd("proftpd-%s" % version):
                env.safe_run("CFLAGS='-I/usr/include/postgresql' ./configure --prefix=%s "
                    "--disable-auth-file --disable-ncurses --disable-ident --disable-shadow "
                    "--enable-openssl --with-modules=%s "
                    "--with-libraries=/usr/lib/postgresql/%s/lib" % (install_dir, modules, postgres_ver))
                env.safe_sudo("make")
                env.safe_sudo("make install")
                env.safe_sudo("make clean")
    # Get the init.d startup script
    initd_script = 'proftpd.initd'
    initd_url = os.path.join(REPO_ROOT_URL, 'conf_files', initd_script)
    remote_file = "/etc/init.d/proftpd"
    env.safe_sudo("wget --output-document=%s %s" % (remote_file, initd_url))
    env.safe_sed(remote_file, 'REPLACE_THIS_WITH_CUSTOM_INSTALL_DIR', install_dir, use_sudo=True)
    env.safe_sudo("chmod 755 %s" % remote_file)
    # Set the configuration file
    conf_file = 'proftpd.conf'
    remote_file = os.path.join(remote_conf_dir, conf_file)
    if "postgres_port" not in env:
        env.postgres_port = '5910'
    if "galaxy_ftp_user_password" not in env:
        env.galaxy_ftp_user_password = 'fu5yOj2sn'
    proftpd_conf = {'galaxy_uid': env.safe_run('id -u galaxy'),
                    'galaxy_fs': '/mnt/galaxy',  # Should be a var but uncertain how to get it
                    'install_dir': install_dir}
    _setup_conf_file(env, remote_file, conf_file, overrides=proftpd_conf,
        default_source="proftpd.conf.template")
    # Get the custom welcome msg file
    welcome_msg_file = 'welcome_msg.txt'
    welcome_url = os.path.join(REPO_ROOT_URL, 'conf_files', welcome_msg_file)
    env.safe_sudo("wget --output-document=%s %s" %
       (os.path.join(remote_conf_dir, welcome_msg_file), welcome_url))
    # Stow
    env.safe_sudo("cd %s; stow proftpd" % env.install_dir)
    env.logger.debug("----- ProFTPd %s installed to %s -----" % (version, install_dir))


def install_sge(env):
    """Sun Grid Engine.
    """
    out_dir = "ge6.2u5"
    url = "%s/ge62u5_lx24-amd64.tar.gz" % CDN_ROOT_URL
    install_dir = env.install_dir
    if env.safe_exists(os.path.join(install_dir, out_dir)):
        return
    with _make_tmp_dir() as work_dir:
        with contextlib.nested(cd(work_dir), settings(hide('stdout'))):
            env.safe_run("wget %s" % url)
            env.safe_sudo("chown %s %s" % (env.user, install_dir))
            env.safe_run("tar -C %s -xvzf %s" % (install_dir, os.path.split(url)[1]))
    env.logger.debug("SGE setup")

########NEW FILE########
__FILENAME__ = distributed
"""Install instructions for distributed MapReduce style programs.
"""
import os

from fabric.api import *
from fabric.contrib.files import *

from shared import (_if_not_python_lib, _pip_cmd, _is_anaconda)

@_if_not_python_lib("pydoop")
def install_pydoop(env):
    """pydoop; provides Hadoop access for Python.
    http://pydoop.sourceforge.net/docs/
    """
    java_home = env.java_home if "java_home" in env else os.environ["JAVA_HOME"]
    export_str = "export JAVA_HOME=%s" % (java_home)
    cmd = env.safe_run if _is_anaconda(env) else env.safe_sudo
    cmd("%s && %s install pydoop" % (export_str, _pip_cmd(env)))

@_if_not_python_lib("bl.mr.seq.seqal")
def install_seal(env):
    """Install seal: process high-throughput sequencing with Hadoop.

    http://biodoop-seal.sf.net/
    """
    install_pydoop(env)

    java_home = env.java_home if "java_home" in env else os.environ["JAVA_HOME"]
    export_str = "export JAVA_HOME=%s" % (java_home)
    cmd = env.safe_run if _is_anaconda(env) else env.safe_sudo
    cmd("%s && %s install --pre seal" % (export_str, _pip_cmd(env)))

########NEW FILE########
__FILENAME__ = galaxy
"""
Install any components that fall under 'galaxy' directive in main.yaml
"""
from cloudbio.galaxy import _setup_users
from cloudbio.galaxy import _setup_galaxy_env_defaults
from cloudbio.galaxy import _install_galaxy
from cloudbio.galaxy import _configure_galaxy_options


def install_galaxy_webapp(env):
    _prep_galaxy(env)
    _install_galaxy(env)
    _configure_galaxy_options(env)


def _prep_galaxy(env):
    _setup_users(env)
    _setup_galaxy_env_defaults(env)

########NEW FILE########
__FILENAME__ = galaxyp
"""
"""

from cloudbio.galaxy.utils import _chown_galaxy

from fabric.contrib.files import *

from shared import _write_to_file


def install_protvis(env):
    """ Installs Andrew Brock's proteomics visualize tool.
    https://bitbucket.org/Andrew_Brock/proteomics-visualise/
    """
    _setup_protvis_env(env)
    protvis_home = env["protvis_home"]
    env.safe_sudo("sudo apt-get -y --force-yes install libxml2-dev libxslt-dev")

    run("rm -rf protvis")
    run("git clone -b lorikeet https://github.com/jmchilton/protvis.git")
    with cd("protvis"):
        run("git submodule init")
        run("git submodule update")
        env.safe_sudo("rsync -avur --delete-after . %s" % (protvis_home))
        _chown_galaxy(env, protvis_home)
        with cd(protvis_home):
            env.safe_sudo("./setup.sh", user=env.get("galaxy_user", "galaxy"))

    #default_revision = "8cc6af1c492c"
    #
    #revision = env.get("protvis_revision", default_revision)
    #url = _get_bitbucket_download_url(revision, "https://bitbucket.org/Andrew_Brock/proteomics-visualise")
    #def _make(env):
    #_get_install(url, env, _make)

    galaxy_data_dir = env.get('galaxy_data_dir', "/mnt/galaxyData/")
    protvis_converted_files_dir = env.get('protvis_converted_files_dir')
    _write_to_file('''GALAXY_ROOT = "%s"
PATH_WHITELIST = ["%s/files/", "%s"]
CONVERTED_FILES = "%s"
''' % (env.galaxy_home, galaxy_data_dir, protvis_converted_files_dir, protvis_converted_files_dir), "%s/conf.py" % protvis_home, 0755)
    _setup_protvis_service(env)


def _setup_protvis_env(env):
    if not "protvis_home" in env:
        env["protvis_home"] = "%s/%s" % (env.galaxy_tools_dir, "protvis")
    if not "protvis_user" in env:
        env["protvis_user"] = "galaxy"
    if not "protvis_port" in env:
        env["protvis_port"] = "8500"
    if not "protvis_converted_files_dir" in env:
        galaxy_data_dir = env.get('galaxy_data_dir', "/mnt/galaxyData/")
        env['protvis_converted_files_dir'] = "%s/tmp/protvis" % galaxy_data_dir


def _setup_protvis_service(env):
    _setup_conf_file(env, os.path.join("/etc/init.d/protvis"), "protvis_init", default_source="protvis_init")
    _setup_conf_file(env, os.path.join("/etc/default/protvis"), "protvis_default")
    _setup_simple_service("protvis")

########NEW FILE########
__FILENAME__ = galaxy_tools
"""
Install any components that fall under 'galaxy_tools' directive in main.yaml
"""
from cloudbio.galaxy.tools import _install_tools
from cloudbio.custom.galaxy import _prep_galaxy


def install_cbl_galaxy_tools(env):
    _prep_galaxy(env)
    _install_tools(env)

########NEW FILE########
__FILENAME__ = java
"""Install instructions for non-packaged java programs.
"""
import os

from fabric.api import *
from fabric.contrib.files import *

from shared import (_if_not_installed, _make_tmp_dir)
from cloudbio.custom import shared

@_if_not_installed("lein -v")
def install_leiningen(env):
    """Clojure tool for project configuration and automation.
    http://github.com/technomancy/leiningen
    """
    bin_dir = os.path.join(env.system_install, "bin")
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            shared._remote_fetch(env, "https://raw.github.com/technomancy/leiningen/stable/bin/lein")
            env.safe_run("chmod a+rwx lein")
            env.safe_sudo("mv lein %s" % bin_dir)
            env.safe_run("%s/lein" % bin_dir)

########NEW FILE########
__FILENAME__ = phylogeny
"""Install instructions for non-packaged phyologeny programs.
"""
import os

from fabric.api import *
from fabric.contrib.files import *

from cloudbio.custom.shared import _if_not_installed, _make_tmp_dir

def install_tracer(env):
    """A program for analysing results from Bayesian MCMC programs such as BEAST & MrBayes.
    http://tree.bio.ed.ac.uk/software/tracer/
    """
    version = "1.5"
    install_dir = os.path.join(env.system_install, "bioinf")
    final_exe = os.path.join(env.system_install, "bin", "tracer")
    if env.safe_exists(final_exe):
        return
    if not env.safe_exists(final_exe):
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                env.safe_run("wget -O Tracer_v{0}.tgz 'http://tree.bio.ed.ac.uk/download.php?id=80&num=3'".format(
                    version))
                env.safe_run("tar xvzf Tracer_v{0}.tgz".format(version))
                env.safe_run("chmod a+x Tracer_v{0}/bin/tracer".format(version))
                env.safe_sudo("mkdir -p %s" % install_dir)
                env.safe_sudo("rm -rvf %s/tracer" % install_dir)
                env.safe_sudo("mv -f Tracer_v%s %s/tracer" % (version, install_dir))
                env.safe_sudo("ln -sf %s/tracer/bin/tracer %s" % (install_dir, final_exe))

@_if_not_installed("beast -help")
def install_beast(env):
    """BEAST: Bayesian MCMC analysis of molecular sequences.
    http://beast.bio.ed.ac.uk
    """
    version = "1.7.4"
    install_dir = os.path.join(env.system_install, "bioinf")
    final_exe = os.path.join(env.system_install, "bin", "beast")
    if not env.safe_exists(final_exe):
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                env.safe_run("wget -c http://beast-mcmc.googlecode.com/files/BEASTv%s.tgz" % version)
                env.safe_run("tar xvzf BEASTv%s.tgz" % version)
                env.safe_sudo("mkdir -p %s" % install_dir)
                env.safe_sudo("rm -rvf %s/beast" % install_dir)
                env.safe_sudo("mv -f BEASTv%s %s/beast" % (version, install_dir))
                for l in ["beast","beauti","loganalyser","logcombiner","treeannotator","treestat"]:
                    env.safe_sudo("ln -sf %s/beast/bin/%s %s/bin/%s" % (install_dir, l,
                                                                        env.system_install, l))


########NEW FILE########
__FILENAME__ = python
"""Install instructions for python libraries not ready for easy_install.
"""
import os

from fabric.api import *
from fabric.contrib.files import *

from shared import (_if_not_python_lib, _get_install, _python_make, _pip_cmd,
                    _is_anaconda)

@_if_not_python_lib("bx")
def install_bx_python(env):
    """Tools for manipulating biological data, particularly multiple sequence alignments
    https://bitbucket.org/james_taylor/bx-python/wiki/Home
    """
    version = "bitbucket"
    url = "https://bitbucket.org/james_taylor/bx-python/get/tip.tar.bz2"
    cmd = env.safe_run if _is_anaconda(env) else env.safe_sudo
    if not _is_anaconda(env):
        cmd("%s install --upgrade distribute" % _pip_cmd(env))
    cmd("%s install --upgrade %s" % (_pip_cmd(env), url))

@_if_not_python_lib("rpy")
def install_rpy(env):
    """RPy is a very simple, yet robust, Python interface to the R Programming Language.
    http://rpy.sourceforge.net/
    """
    version = "1.0.3"
    ext = "a"
    url = "http://downloads.sourceforge.net/project/rpy/rpy/" \
          "%s/rpy-%s%s.zip" % (version, version, ext)
    def _fix_libraries(env):
        env.safe_run("""sed -i.bak -r -e "s/,'Rlapack'//g" setup.py""")
    with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                  warn_only=True):
        result = env.safe_run("R --version")
        if result.failed:
            return
    _get_install(url, env, _python_make, post_unpack_fn=_fix_libraries)

@_if_not_python_lib("netsa")
def install_netsa_python(env):
    """A suite of open source tools for monitoring large-scale networks using flow data.
    http://tools.netsa.cert.org/index.html
    """
    version = "1.3"
    url = "http://tools.netsa.cert.org/releases/netsa-python-%s.tar.gz" % version
    cmd = env.safe_run if _is_anaconda(env) else env.safe_sudo
    cmd("%s install %s" % (_pip_cmd(env), url))

########NEW FILE########
__FILENAME__ = shared
"""Reusable decorators and functions for custom installations.
"""
from contextlib import contextmanager
import datetime
import functools
import os
import socket
from string import Template
import tempfile
from tempfile import NamedTemporaryFile
import urllib
import uuid
import subprocess

from fabric.api import *
from fabric.contrib.files import *
from cloudbio.fabutils import quiet, warn_only

CBL_REPO_ROOT_URL = "https://raw.github.com/chapmanb/cloudbiolinux/master/"

# -- decorators and context managers


def _if_not_installed(pname):
    """Decorator that checks if a callable program is installed.
    """
    def argcatcher(func):
        functools.wraps(func)

        def decorator(*args, **kwargs):
            if _galaxy_tool_install(args):
                run_function = not _galaxy_tool_present(args)
            else:
                run_function = _executable_not_on_path(pname)

            if run_function:
                return func(*args, **kwargs)
        return decorator
    return argcatcher

def _all_cbl_paths(env, ext):
    """Add paths to other non-system directories installed by CloudBioLinux.
    """
    return ":".join("%s/%s" % (p, ext) for p in [env.system_install,
                                                 os.path.join(env.system_install, "anaconda")])
def _executable_not_on_path(pname):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                  warn_only=True):
        result = env.safe_run("export PATH=%s:$PATH && "
                              "export LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH && %s" %
                              (_all_cbl_paths(env, "bin"), _all_cbl_paths(env, "lib"), pname))
    return result.return_code == 127


def _galaxy_tool_install(args):
    try:
        return args[0]["galaxy_tool_install"]
    except:
        return False


def _galaxy_tool_present(args):
    return env.safe_exists(os.path.join(args[0]["system_install"], "env.sh"))


def _if_not_python_lib(library):
    """Decorator that checks if a python library is installed.
    """
    def argcatcher(func):
        functools.wraps(func)

        def decorator(*args, **kwargs):
            with settings(warn_only=True):
                result = env.safe_run("%s -c 'import %s'" % (_python_cmd(env), library))
            if result.failed:
                return func(*args, **kwargs)
        return decorator
    return argcatcher


@contextmanager
def _make_tmp_dir(ext=None):
    """
    Setup a temporary working directory for building custom software. First checks
    fabric environment for a `work_dir` path, if that is not set it will use the
    remote path $TMPDIR/cloudbiolinux if $TMPDIR is defined remotely, finally falling
    back on remote $HOME/cloudbiolinux otherwise.
    `ext` allows creation of tool specific temporary directories to avoid conflicts
    using CloudBioLinux inside of CloudBioLinux.
    """
    work_dir = __work_dir()
    if ext:
        work_dir += ext
    use_sudo = False
    if not env.safe_exists(work_dir):
        with settings(warn_only=True):
            # Try to create this directory without using sudo, but
            # if needed fallback.
            result = env.safe_run("mkdir -p '%s'" % work_dir)
            if result.return_code != 0:
                use_sudo = True
        if use_sudo:
            env.safe_sudo("mkdir -p '%s'" % work_dir)
            env.safe_sudo("chown -R %s '%s'" % (env.user, work_dir))
    yield work_dir
    if env.safe_exists(work_dir):
        run_func = env.safe_sudo if use_sudo else env.safe_run
        run_func("rm -rf %s" % work_dir)


def __work_dir():
    work_dir = env.get("work_dir", None)
    if not work_dir:
        with quiet():
            tmp_dir = env.safe_run_output("echo $TMPDIR")
        if tmp_dir.failed or not tmp_dir.strip():
            home_dir = env.safe_run_output("echo $HOME")
            tmp_dir = os.path.join(home_dir, "tmp")
        work_dir = os.path.join(tmp_dir.strip(), "cloudbiolinux")
    return work_dir


# -- Standard build utility simplifiers


def _get_expected_file(url, dir_name=None, safe_tar=False, tar_file_name=None):
    if tar_file_name:
        tar_file = tar_file_name
    else:
        tar_file = os.path.split(url.split("?")[0])[-1]
    safe_tar = "--pax-option='delete=SCHILY.*,delete=LIBARCHIVE.*'" if safe_tar else ""
    exts = {(".tar.gz", ".tgz"): "tar %s -xzpf" % safe_tar,
            (".tar",): "tar %s -xpf" % safe_tar,
            (".tar.bz2",): "tar %s -xjpf" % safe_tar,
            (".zip",): "unzip"}
    for ext_choices, tar_cmd in exts.iteritems():
        for ext in ext_choices:
            if tar_file.endswith(ext):
                if dir_name is None:
                    dir_name = tar_file[:-len(ext)]
                return tar_file, dir_name, tar_cmd
    raise ValueError("Did not find extract command for %s" % url)


def _safe_dir_name(dir_name, need_dir=True):
    replace_try = ["", "-src", "_core"]
    for replace in replace_try:
        check = dir_name.replace(replace, "")
        if env.safe_exists(check):
            return check
    # still couldn't find it, it's a nasty one
    for check_part in (dir_name.split("-")[0].split("_")[0],
                       dir_name.split("-")[-1].split("_")[-1],
                       dir_name.split(".")[0],
                       dir_name.lower().split(".")[0]):
        with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                      warn_only=True):
            dirs = env.safe_run_output("ls -d1 *%s*/" % check_part).split("\n")
            dirs = [x for x in dirs if "cannot access" not in x and "No such" not in x]
        if len(dirs) == 1 and dirs[0]:
            return dirs[0]
    if need_dir:
        raise ValueError("Could not find directory %s" % dir_name)

def _remote_fetch(env, url, out_file=None, allow_fail=False, fix_fn=None):
    """Retrieve url using wget, performing download in a temporary directory.

    Provides a central location to handle retrieval issues and avoid
    using interrupted downloads.
    """
    if out_file is None:
        out_file = os.path.basename(url)
    if not env.safe_exists(out_file):
        orig_dir = env.safe_run_output("pwd").strip()
        temp_ext = "/%s" % uuid.uuid3(uuid.NAMESPACE_URL,
                                      str("file://%s/%s/%s/%s" %
                                          (env.host, socket.gethostname(),
                                           datetime.datetime.now().isoformat(), out_file)))
        with _make_tmp_dir(ext=temp_ext) as tmp_dir:
            with cd(tmp_dir):
                with warn_only():
                    result = env.safe_run("wget --no-check-certificate -O %s '%s'" % (out_file, url))
                if result.succeeded:
                    if fix_fn:
                        out_file = fix_fn(env, out_file)
                    env.safe_run("mv %s %s" % (out_file, orig_dir))
                elif allow_fail:
                    out_file = None
                else:
                    raise IOError("Failure to retrieve remote file")
    return out_file

def _fetch_and_unpack(url, need_dir=True, dir_name=None, revision=None,
                      safe_tar=False, tar_file_name=None):
    if url.startswith(("git", "svn", "hg", "cvs")):
        base = os.path.splitext(os.path.basename(url.split()[-1]))[0]
        if env.safe_exists(base):
            env.safe_sudo("rm -rf {0}".format(base))
        env.safe_run(url)
        if revision:
            if url.startswith("git"):
                env.safe_run("cd %s && git checkout %s" % (base, revision))
            else:
                raise ValueError("Need to implement revision retrieval for %s" % url.split()[0])
        return base
    else:
        # If tar_file_name is provided, use it instead of the inferred one
        tar_file, dir_name, tar_cmd = _get_expected_file(url, dir_name, safe_tar, tar_file_name=tar_file_name)
        tar_file = _remote_fetch(env, url, tar_file)
        env.safe_run("%s %s" % (tar_cmd, tar_file))
        return _safe_dir_name(dir_name, need_dir)


def _configure_make(env):
    env.safe_run("export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:%s/lib/pkgconfig && " \
                 "./configure --disable-werror --prefix=%s " %
                 (env.system_install, env.system_install))
    lib_export = "export LD_LIBRARY_PATH=%s/lib:$LD_LIBRARY_PATH" % env.system_install
    env.safe_run("%s && make" % lib_export)
    env.safe_sudo("%s && make install" % lib_export)

def _ac_configure_make(env):
    env.safe_run("autoreconf -i -f")
    _configure_make(env)

def _make_copy(find_cmd=None, premake_cmd=None, do_make=True):
    def _do_work(env):
        if premake_cmd:
            premake_cmd()
        if do_make:
            env.safe_run("make")
        if find_cmd:
            install_dir = _get_bin_dir(env)
            for fname in env.safe_run_output(find_cmd).split("\n"):
                env.safe_sudo("cp -rf %s %s" % (fname.rstrip("\r"), install_dir))
    return _do_work


def _get_install(url, env, make_command, post_unpack_fn=None, revision=None, dir_name=None,
                 safe_tar=False, tar_file_name=None):
    """Retrieve source from a URL and install in our system directory.
    """
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            dir_name = _fetch_and_unpack(url, revision=revision, dir_name=dir_name,
                                         safe_tar=safe_tar, tar_file_name=tar_file_name)
        with cd(os.path.join(work_dir, dir_name)):
            if post_unpack_fn:
                post_unpack_fn(env)
            make_command(env)

def _apply_patch(env, url):
    patch = os.path.basename(url)
    cmd = "wget {url}; patch -p0 < {patch}".format(url=url, patch=patch)
    env.safe_run(cmd)

def _get_install_local(url, env, make_command, dir_name=None,
                       post_unpack_fn=None, safe_tar=False, tar_file_name=None):
    """Build and install in a local directory.
    """
    (_, test_name, _) = _get_expected_file(url, safe_tar=safe_tar, tar_file_name=tar_file_name)
    test1 = os.path.join(env.local_install, test_name)
    if dir_name is not None:
        test2 = os.path.join(env.local_install, dir_name)
    elif "-" in test1:
        test2, _ = test1.rsplit("-", 1)
    else:
        test2 = os.path.join(env.local_install, test_name.split("_")[0])
    if not env.safe_exists(test1) and not env.safe_exists(test2):
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                dir_name = _fetch_and_unpack(url, dir_name=dir_name, safe_tar=safe_tar,
                    tar_file_name=tar_file_name)
                print env.local_install, dir_name
                if not env.safe_exists(os.path.join(env.local_install, dir_name)):
                    with cd(dir_name):
                        if post_unpack_fn:
                            post_unpack_fn(env)
                        make_command(env)
                    # Copy instead of move because GNU mv does not have --parents flag.
                    # The source dir will get cleaned up anyhow so just leave it.
                    destination_dir = env.local_install
                    env.safe_sudo("mkdir -p '%s'" % destination_dir)
                    env.safe_sudo("cp --recursive %s %s" % (dir_name, destination_dir))

# --- Language specific utilities

def _symlinked_install_dir(pname, version, env, extra_dir=None):
    if extra_dir:
        base_dir = os.path.join(env.system_install, "share", extra_dir, pname)
    else:
        base_dir = os.path.join(env.system_install, "share", pname)
    return base_dir, "%s-%s" % (base_dir, version)

def _symlinked_dir_exists(pname, version, env, extra_dir=None):
    """Check if a symlinked directory exists and is non-empty.
    """
    _, install_dir = _symlinked_install_dir(pname, version, env, extra_dir)
    if env.safe_exists(install_dir):
        items = env.safe_run_output("ls %s" % install_dir)
        if items.strip() != "":
            return True
    return False

def _symlinked_shared_dir(pname, version, env, extra_dir=None):
    """Create a symlinked directory of files inside the shared environment.
    """
    base_dir, install_dir = _symlinked_install_dir(pname, version, env, extra_dir)
    # Does not exist, change symlink to new directory
    if not env.safe_exists(install_dir):
        env.safe_sudo("mkdir -p %s" % install_dir)
        if env.safe_exists(base_dir):
            env.safe_sudo("rm -f %s" % base_dir)
        env.safe_sudo("ln -s %s %s" % (install_dir, base_dir))
        return install_dir
    items = env.safe_run_output("ls %s" % install_dir)
    # empty directory, change symlink and re-download
    if items.strip() == "":
        if env.safe_exists(base_dir):
            env.safe_sudo("rm -f %s" % base_dir)
        env.safe_sudo("ln -s %s %s" % (install_dir, base_dir))
        return install_dir
    # Create symlink if previously deleted
    if not env.safe_exists(base_dir):
        env.safe_sudo("ln -s %s %s" % (install_dir, base_dir))
    return None

def _symlinked_java_version_dir(pname, version, env):
    return _symlinked_shared_dir(pname, version, env, extra_dir="java")


def _java_install(pname, version, url, env, install_fn=None,
                  pre_fetch_fn=None):
    """Download java jars into versioned input directories.

    pre_fetch_fn runs before URL retrieval, allowing insertion of
    manual steps like restricted downloads.
    """
    install_dir = _symlinked_java_version_dir(pname, version, env)
    if install_dir:
        with _make_tmp_dir() as work_dir:
            with cd(work_dir):
                if pre_fetch_fn:
                    out = pre_fetch_fn(env)
                    if out is None:
                        return
                dir_name = _fetch_and_unpack(url)
                with cd(dir_name):
                    if install_fn is not None:
                        install_fn(env, install_dir)
                    else:
                        env.safe_sudo("mv *.jar %s" % install_dir)


def _python_cmd(env):
    """Retrieve python command, handling tricky situations on CentOS.
    """
    anaconda_py = os.path.join(env.system_install, "anaconda", "bin", "python")
    if env.safe_exists(anaconda_py):
        return anaconda_py
    if "python_version_ext" in env and env.python_version_ext:
        major, minor = env.safe_run("python --version").split()[-1].split(".")[:2]
        check_major, check_minor = env.python_version_ext.split(".")[:2]
        if major != check_major or int(check_minor) > int(minor):
            return "python%s" % env.python_version_ext
        else:
            return "python"
    else:
        return "python"

def _pip_cmd(env):
    """Retrieve pip command for installing python packages, allowing configuration.
    """
    anaconda_pip = os.path.join(env.system_install, "anaconda", "bin", "pip")
    if env.safe_exists(anaconda_pip):
        to_check = [anaconda_pip]
    else:
        to_check = ["pip"]
    if "pip_cmd" in env and env.pip_cmd:
        to_check.append(env.pip_cmd)
    if not env.use_sudo:
        to_check.append(os.path.join(env.system_install, "bin", "pip"))
    if "python_version_ext" in env and env.python_version_ext:
        to_check.append("pip-{0}".format(env.python_version_ext))
    for cmd in to_check:
        with quiet():
            pip_version = env.safe_run("%s --version" % cmd)
        if pip_version.succeeded:
            return cmd
    raise ValueError("Could not find pip installer from: %s" % to_check)

def _conda_cmd(env):
    to_check = [os.path.join(env.system_install, "anaconda", "bin", "conda"), "conda"]
    for cmd in to_check:
        with quiet():
            test = env.safe_run("%s --version" % cmd)
        if test.succeeded:
            return cmd
    return None

def _is_anaconda(env):
    """Check if we have a conda command or are in an anaconda subdirectory.
    """
    with quiet():
        conda = _conda_cmd(env)
        has_conda = conda and env.safe_run_output("%s -h" % conda).startswith("usage: conda")
    with quiet():
        full_pip = env.safe_run_output("which %s" % _pip_cmd(env))
    in_anaconda_dir = "/anaconda/" in full_pip
    return has_conda or in_anaconda_dir

def _python_make(env):
    run_cmd = env.safe_run if _is_anaconda(env) else env.safe_sudo
    # Clean up previously failed builds
    env.safe_sudo("rm -rf /tmp/pip-build-%s" % env.user)
    env.safe_sudo("rm -rf /tmp/pip-*-build")
    run_cmd("%s install --upgrade ." % _pip_cmd(env))
    for clean in ["dist", "build", "lib/*.egg-info"]:
        env.safe_sudo("rm -rf %s" % clean)


def _get_installed_file(env, local_file):
    installed_files_dir = \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "installed_files")
    path = os.path.join(installed_files_dir, local_file)
    if not os.path.exists(path):
        # If using cloudbiolinux as a library, this won't be available,
        # download the file from github instead
        f = NamedTemporaryFile(delete=False)
        cloudbiolinx_repo_url = env.get("cloudbiolinux_repo_url", CBL_REPO_ROOT_URL)
        url = os.path.join(cloudbiolinx_repo_url, 'installed_files', local_file)
        urllib.urlretrieve(url, f.name)
        path = f.name
    return path


def _get_installed_file_contents(env, local_file):
    return open(_get_installed_file(env, local_file), "r").read()


def _write_to_file(contents, path, mode):
    """
    Use fabric to write string contents to remote file specified by path.
    """
    fd, local_path = tempfile.mkstemp()
    try:
        os.write(fd, contents)
        tmp_path = os.path.join("/tmp", os.path.basename(path))
        env.safe_put(local_path, tmp_path)
        env.safe_sudo("mv %s %s" % (tmp_path, path))
        env.safe_sudo("chmod %s %s" % (mode, path))
        os.close(fd)
    finally:
        os.unlink(local_path)


def _get_bin_dir(env):
    """
    When env.system_install is /usr this exists, but in the Galaxy
    it may not already exist.
    """
    return _get_install_subdir(env, "bin")


def _get_include_dir(env):
    return _get_install_subdir(env, "include")


def _get_lib_dir(env):
    return _get_install_subdir(env, "lib")


def _get_install_subdir(env, subdir):
    path = os.path.join(env.system_install, subdir)
    if not env.safe_exists(path):
        env.safe_sudo("mkdir -p '%s'" % path)
    return path


def _set_default_config(env, install_dir, sym_dir_name="default"):
    """
    Sets up default galaxy config directory symbolic link (if needed). Needed
    when it doesn't exists or when installing a new version of software.
    """
    version = env["tool_version"]
    if env.safe_exists(install_dir):
        install_dir_root = "%s/.." % install_dir
        sym_dir = "%s/%s" % (install_dir_root, sym_dir_name)
        replace_default = False
        if not env.safe_exists(sym_dir):
            replace_default = True
        if not replace_default:
            default_version = env.safe_sudo("basename `readlink -f %s`" % sym_dir)
            if version > default_version:  # Bug: Wouldn't work for 1.9 < 1.10
                print "default version %s is older than version %s just installed, replacing..." % (default_version, version)
                replace_default = True
        if replace_default:
            env.safe_sudo("rm -rf %s; ln -f -s %s %s" % (sym_dir, install_dir, sym_dir))


def _setup_simple_service(service_name):
    """
    Very Ubuntu/Debian specific, will need to be modified if used on other
    archs.
    """
    sudo("ln -f -s /etc/init.d/%s /etc/rc0.d/K01%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc1.d/K01%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc2.d/S99%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc3.d/S99%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc4.d/S99%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc5.d/S99%s" % (service_name, service_name))
    sudo("ln -f -s /etc/init.d/%s /etc/rc6.d/K01%s" % (service_name, service_name))


def _render_config_file_template(env, name, defaults={}, overrides={}, default_source=None):
    """
    If ``name` is say ``nginx.conf``, check fabric environment for
    ``nginx_conf_path`` and then ``nginx_conf_template_path``. If
    ``nginx_conf_path`` is set, return the contents of that file. If
    nginx_conf_template_path is set, return the contents of that file
    but with variable interpolation performed. Variable interpolation
    is performed using a derivative of the fabric environment defined
    using the supplied ``defaults`` and ``overrides`` using the
    ``_extend_env`` function below.

    Finally, if neither ``nginx_conf_path`` or
    ``nginx_conf_template_path`` are set, check the
    ``installed_files`` directory for ``nginx.conf`` and finally
    ``nginx.conf.template``.
    """
    param_prefix = name.replace(".", "_")
    # Deployer can specify absolute path for config file, check this first
    path_key_name = "%s_path" % param_prefix
    template_key_name = "%s_template_path" % param_prefix
    if env.get(path_key_name, None):
        source_path = env[path_key_name]
        source_template = False
    elif env.get(template_key_name, None):
        source_path = env[template_key_name]
        source_template = True
    elif default_source:
        source_path = _get_installed_file(env, default_source)
        source_template = source_path.endswith(".template")
    else:
        default_template_name = "%s.template" % name
        source_path = _get_installed_file(env, default_template_name)
        source_template = True

    if source_template:
        template = Template(open(source_path, "r").read())
        template_params = _extend_env(env, defaults=defaults, overrides=overrides)
        contents = template.substitute(template_params)
    else:
        contents = open(source_path, "r").read()
    return contents


def _extend_env(env, defaults={}, overrides={}):
    """
    Create a new ``dict`` from fabric's ``env``, first adding defaults
    specified via ``defaults`` (if available). Finally, override
    anything in env, with values specified by ``overrides``.
    """
    new_env = {}
    for key, value in defaults.iteritems():
        new_env[key] = value
    for key, value in env.iteritems():
        new_env[key] = value
    for key, value in overrides.iteritems():
        new_env[key] = value
    return new_env


def _setup_conf_file(env, dest, name, defaults={}, overrides={}, default_source=None, mode="0755"):
    conf_file_contents = _render_config_file_template(env, name, defaults, overrides, default_source)
    _write_to_file(conf_file_contents, dest, mode=mode)


def _add_to_profiles(line, profiles=[], use_sudo=True):
    """
    If it's not already there, append ``line`` to shell profiles files.
    By default, these are ``/etc/profile`` and ``/etc/bash.bashrc`` but can be
    overridden by providing a list of file paths to the ``profiles`` argument.
    """
    if not profiles:
        profiles = ['/etc/bash.bashrc', '/etc/profile']
    for profile in profiles:
        if not env.safe_contains(profile, line):
            env.safe_append(profile, line, use_sudo=use_sudo)


def install_venvburrito():
    """
    If not already installed, install virtualenv-burrito
    (https://github.com/brainsik/virtualenv-burrito) as a convenient
    method for installing and managing Python virtualenvs.
    """
    url = "https://raw.github.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh"
    if not env.safe_exists("$HOME/.venvburrito/startup.sh"):
        env.safe_run("curl -s {0} | $SHELL".format(url))
        # Add the startup script into the ubuntu user's bashrc
        _add_to_profiles(". $HOME/.venvburrito/startup.sh", [env.shell_config], use_sudo=False)

def _create_python_virtualenv(env, venv_name, reqs_file=None, reqs_url=None):
    """
    Using virtual-burrito, create a new Python virtualenv named ``venv_name``.
    Do so only if the virtualenv of the given name does not already exist.
    virtual-burrito installs virtualenvs in ``$HOME/.virtualenvs``.

    By default, an empty virtualenv is created. Python libraries can be
    installed into the virutalenv at the time of creation by providing a path
    to the requirements.txt file (``reqs_file``). Instead of providing the file,
    a url to the file can be provided via ``reqs_url``, in which case the
    requirements file will first be downloaded. Note that if the ``reqs_url``
    is provided, the downloaded file will take precedence over ``reqs_file``.
    """
    # First make sure virtualenv-burrito is installed
    install_venvburrito()
    activate_vburrito = ". $HOME/.venvburrito/startup.sh"

    def create():
        if "venv_directory" not in env:
            _create_global_python_virtualenv(env, venv_name, reqs_file, reqs_url)
        else:
            _create_local_python_virtualenv(env, venv_name, reqs_file, reqs_url)

    # TODO: Terrible hack here, figure it out and fix it.
    #   prefix or vburrito does not work with is_local or at least deployer+is_local
    if env.is_local:
        create()
    else:
        with prefix(activate_vburrito):
            create()


def _create_local_python_virtualenv(env, venv_name, reqs_file, reqs_url):
    """
    Use virtualenv directly to setup virtualenv in specified directory.
    """
    venv_directory = env.get("venv_directory")
    if not env.safe_exists(venv_directory):
        if reqs_url:
            _remote_fetch(env, reqs_url, reqs_file)
        env.logger.debug("Creating virtualenv in directory %s" % venv_directory)
        env.safe_sudo("virtualenv --no-site-packages '%s'" % venv_directory)
        env.logger.debug("Activating")
        env.safe_sudo(". %s/bin/activate; pip install -r '%s'" % (venv_directory, reqs_file))


def _create_global_python_virtualenv(env, venv_name, reqs_file, reqs_url):
    """
    Use mkvirtualenv to setup this virtualenv globally for user.
    """
    if venv_name in env.safe_run_output("bash -l -c lsvirtualenv | grep {0} || true"
        .format(venv_name)):
        env.logger.info("Virtualenv {0} already exists".format(venv_name))
    else:
        with _make_tmp_dir():
            if reqs_file or reqs_url:
                if not reqs_file:
                    # This mean the url only is provided so 'standardize ' the file name
                    reqs_file = 'requirements.txt'
                cmd = "bash -l -c 'mkvirtualenv -r {0} {1}'".format(reqs_file, venv_name)
            else:
                cmd = "bash -l -c 'mkvirtualenv {0}'".format(venv_name)
            if reqs_url:
                _remote_fetch(env, reqs_url, reqs_file)
            env.safe_run(cmd)
            env.logger.info("Finished installing virtualenv {0}".format(venv_name))


def _get_bitbucket_download_url(revision, default_repo):
    if revision.startswith("http"):
        url = revision
    else:
        url = "%s/get/%s.tar.gz" % (default_repo, revision)
    return url


def _read_boolean(env, name, default):
    property_str = env.get(name, str(default))
    return property_str.upper() in ["TRUE", "YES"]

########NEW FILE########
__FILENAME__ = system
"""
Install system programs not available from packages.
"""
import os

from fabric.api import cd

from cloudbio.custom import shared
from cloudbio.custom.shared import _if_not_installed, _get_install, _configure_make
from cloudbio.fabutils import quiet

def install_homebrew(env):
    """Homebrew package manager for OSX and Linuxbrew for linux systems.

    https://github.com/mxcl/homebrew
    https://github.com/Homebrew/linuxbrew
    """
    if env.distribution == "macosx":
        with quiet():
            test_brewcmd = env.safe_run("brew --version")
        if not test_brewcmd.succeeded:
            env.safe_run('ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go/install)"')
    else:
        brewcmd = os.path.join(env.system_install, "bin", "brew")
        with quiet():
            test_brewcmd = env.safe_run("%s --version" % brewcmd)
        if not test_brewcmd.succeeded or _linuxbrew_origin_problem(brewcmd):
            with shared._make_tmp_dir() as tmp_dir:
                with cd(tmp_dir):
                    if env.safe_exists("linuxbrew"):
                        env.safe_run("rm -rf linuxbrew")
                    for cleandir in ["Library", ".git"]:
                        if env.safe_exists("%s/%s" % (env.system_install, cleandir)):
                            env.safe_run("rm -rf %s/%s" % (env.system_install, cleandir))
                    env.safe_run("git clone https://github.com/Homebrew/linuxbrew.git")
                    with cd("linuxbrew"):
                        if not env.safe_exists(env.system_install):
                            env.safe_sudo("mkdir -p %s" % env.system_install)
                        env.safe_sudo("chown %s %s" % (env.user, env.system_install))
                        paths = ["bin", "etc", "include", "lib", "lib/pkgconfig", "Library",
                                 "sbin", "share", "var", "var/log", "share/java", "share/locale",
                                 "share/man", "share/man/man1", "share/man/man2",
                                 "share/man/man3", "share/man/man4", "share/man/man5",
                                 "share/man/man6", "share/man/man7", "share/man/man8",
                                 "share/info", "share/doc", "share/aclocal",
                                 "lib/python2.7/site-packages", "lib/python2.6/site-packages",
                                 "lib/python3.2/site-packages", "lib/python3.3/site-packages",
                                 "lib/perl5", "lib/perl5/site_perl"]
                        if not env.safe_exists("%s/bin" % env.system_install):
                            env.safe_sudo("mkdir -p %s/bin" % env.system_install)
                        for path in paths:
                            if env.safe_exists("%s/%s" % (env.system_install, path)):
                                env.safe_sudo("chown %s %s/%s" % (env.user, env.system_install, path))
                        if not env.safe_exists("%s/Library" % env.system_install):
                            env.safe_run("mv Library %s" % env.system_install)
                        if not env.safe_exists("%s/.git" % env.system_install):
                            env.safe_run("mv .git %s" % env.system_install)
                        man_dir = "share/man/man1"
                        if not env.safe_exists("%s/%s" % (env.system_install, man_dir)):
                            env.safe_run("mkdir -p %s/%s" % (env.system_install, man_dir))
                        env.safe_run("mv -f %s/brew.1 %s/%s" % (man_dir, env.system_install, man_dir))
                        env.safe_run("mv -f bin/brew %s/bin" % env.system_install)

def _linuxbrew_origin_problem(brewcmd):
    """Check for linuxbrew origins which point to Homebrew instead of Linuxbrew.
    """
    config_file = os.path.abspath(os.path.normpath((os.path.expanduser(
        os.path.join(os.path.dirname(brewcmd), os.pardir, ".git", "config")))))
    if not os.path.exists(config_file):
        return True
    with open(config_file) as in_handle:
        return "linuxbrew" not in in_handle.read()

@_if_not_installed("s3fs")
def install_s3fs(env):
    """FUSE-based file system backed by Amazon S3.
    https://code.google.com/p/s3fs/
    """
    version = "1.61"
    url = "http://s3fs.googlecode.com/files/s3fs-{0}.tar.gz".format(version)
    _get_install(url, env, _configure_make)

########NEW FILE########
__FILENAME__ = vcr
#
# vcr.py
#  - Configures the environment for running the Viral Assembly (viral_assembly_pipeline.py) and VIGOR (VIGOR3.pl) pipelines (creating directory structure and installs software). 
#

import os.path, re, mmap
from fabric.api import cd, env, hide, local, run, settings, sudo, task
from fabric.network import disconnect_all

# Common variables
dependency_URL = "http://s3.amazonaws.com/VIGOR-GSC"


# Galaxy VCR
galaxy_central = "/mnt/galaxyTools/galaxy-central"
galaxy_VCR_path = "/%s/tools/viral_assembly_annotation" % galaxy_central

# Galaxy VCR - install method
def install_galaxy_vcr(env):
	with cd("~"):
		print("Installing galaxy VCR tools (python and xml scripts).")
		sudo("git clone git://github.com/JCVI-Cloud/galaxy-tools-vcr.git")
		sudo("cp -R galaxy-tools-vcr/tools/viral_assembly_annotation %s" % galaxy_VCR_path)
		sudo("chown -R galaxy:galaxy %s" % galaxy_VCR_path)
	with cd(galaxy_central):
		print("Adding VCR to tool_conf.xml.")
		tcx_file = "tool_conf.xml"
		_set_pre_VCR(tcx_file,"galaxy","galaxy")
		tcx_string = _get_file_string(tcx_file,galaxy_central)
		
		vcr_header = "<section name=\"Viral Assembly and Annotation\" id=\"viral_assembly_annotation\">\""
		if (tcx_string.find(vcr_header) != -1):
			print("Galaxy VCR tools already included in tools_conf.xml!")
		else:
			sudo("sed -i '$d' %s/%s" % (galaxy_central,tcx_file))
			sudo("echo -e '  <section name=\"Viral Assembly and Annotation\" id=\"viral_assembly_annotation\">' >> %s" % tcx_file)
			sudo("echo -e '    <tool file=\"viral_assembly_annotation/viral_assembly.xml\" />' >> %s" % tcx_file)
			sudo("echo -e '    <tool file=\"viral_assembly_annotation/VIGOR.xml\" />' >> %s" % tcx_file)
			sudo("echo -e '  </section>' >> %s" % tcx_file)
			sudo("echo -e '</toolbox>' >> %s" % tcx_file)
		
		print("Adding 'sanitize_all_html = False' to universe_wsgi.ini to enable JBrowse for VICVB.")
		uwi_file = "universe_wsgi.ini"
		_set_pre_VCR(uwi_file,"galaxy","galaxy")
		uwi_string = _get_file_string(uwi_file,galaxy_central)
		
		if (uwi_string.find("sanitize_all_html") != -1):
			print("Setting sanitize_all_html in %s to False." % uwi_file)
			sudo("sed -i '/^sanitize_all_html/c\sanitize_all_html = False' %s" % uwi_file)
		else:
			print("No sanitize_all_html present! Adding...")
			sudo("sed -i '/^\[app:main\]/a\\\nsanitize_all_html = False' %s" % uwi_file)


# Viral Assembly
viral_dirs = {}
viral_urls = {}
viral_tars = {}

# Viral Assembly - install methods
def install_viralassembly(env):
	try:
		_initialize_area_viral()
		_add_tools_viral()
		_add_refs()
		sudo("chmod -R 755 %(VIRAL_ROOT_DIR)s" % env)
	finally:
		disconnect_all()

def install_viralassembly_cleanall(env):
	try:
		_initialize_env("viral")
		_remove_dir("%(VIRAL_ROOT_DIR)s" % env)
		print("Viral Assembly Removed\n")
	finally:
		disconnect_all()

# Viral Assembly - utility methods

def _initialize_area_viral():
	_initialize_env("viral")
	
	env.VIRAL_SCRIPT = "%s/viral_assembly_pipeline.py" % dependency_URL
	
	viral_dirs["PROJECT_DIR"] = "%(VIRAL_ROOT_DIR)s/project" % env
	viral_dirs["REF_DIR"] = "%(VIRAL_ROOT_DIR)s/references"  % env
	viral_dirs["TOOLS_DIR"] = "%(VIRAL_ROOT_DIR)s/tools"     % env
	viral_dirs["TOOLS_BINARIES_DIR"] = "%s/BINARIES"         % viral_dirs["TOOLS_DIR"]
	viral_dirs["TOOLS_PERL_DIR"] = "%s/PERL"                 % viral_dirs["TOOLS_DIR"]
	
	env.VIRAL_REF_FILES = "corona_virus,hadv,influenza_a_virus,jev,mpv,norv,rota_virus,rsv,veev,vzv,yfv"
	
	viral_urls["BIO_LINUX_URL"] = "http://nebc.nerc.ac.uk/bio-linux/"
	
	viral_tars["BINARIES_TARBALL"] = "BINARIES.tgz"
	viral_tars["PERL_TARBALL"] = "PERL.tgz"
	
	print("user:   %(user)s" % env)
	print("host:   %(host)s" % env)
	print("ROOT DIR:   %(VIRAL_ROOT_DIR)s" % env)
	print("VIRAL ASSEMBLY SCRIPT:   %(VIRAL_SCRIPT)s" % env)
	for name in sorted(viral_dirs.keys()):
		if not _path_is_dir(viral_dirs[name]):
			sudo("mkdir -p %s" % viral_dirs[name])
		print("%s:   %s" % (name,viral_dirs[name]))
	print("VIRAL ASSEMBLY REFS FILES: %(VIRAL_REF_FILES)s" % env)
	for name in sorted(viral_urls.keys()):
		print("%s:   %s" % (name,viral_urls[name]))
	for name in sorted(viral_tars.keys()):
		print("%s:   %s" % (name,viral_tars[name]))

def _add_tools_viral():
	with cd("/home/ubuntu/"):
		bashrc_file = ".bashrc"
		_set_pre_VCR(bashrc_file,"ubuntu","ubuntu")
		bashrc_string = _get_file_string(bashrc_file,"/home/ubuntu/")
		
		if (bashrc_string.find("DEBIAN_FRONTEND") != -1):
			print("Setting DEBIAN_FRONTEND in %s to noninteractive." % bashrc_file)
			sudo("sed -i \"/DEBIAN_FRONTEND/c\DEBIAN_FRONTEND=noninteractive\" %s/%s" % ("/home/ubuntu",bashrc_file))
		else:
			print("No DEBIAN_FRONTEND present! Adding...")
			sudo("echo -e \"DEBIAN_FRONTEND=noninteractive\" >> %s" % bashrc_file)
	
	sudo("wget --no-check-certificate -O %s/viral_assembly_pipeline.py %s" % (env.VIRAL_ROOT_DIR,env.VIRAL_SCRIPT))
	_add_package(dependency_URL,viral_tars["BINARIES_TARBALL"],viral_dirs["TOOLS_BINARIES_DIR"],"tar")
	_add_package(dependency_URL,viral_tars["PERL_TARBALL"],viral_dirs["TOOLS_PERL_DIR"],"tar")
	_apt_get_install("csh")
	_apt_get_install("gawk")
	_initialize_bio_linux()

def _add_refs():
	files = (env.VIRAL_REF_FILES).split(",")
	for file in files:
		_add_package(dependency_URL,"%s.tgz" % file,viral_dirs["REF_DIR"],"tar")

def _initialize_bio_linux():
	sudo("echo -e \"deb %s unstable bio-linux\" >> /etc/apt/sources.list" % viral_urls["BIO_LINUX_URL"])
	sudo("sudo apt-get update")
	_apt_get_install("bio-linux-keyring")
	_apt_get_install("bwa")
	_apt_get_install("samtools")
	_apt_get_install("bio-linux-cap3")
	_apt_get_install("emboss")


# VIGOR

vigor_dirs = {}
vigor_urls = {}
vigor_tars = {}
vigor_names = {}

# VIGOR - install methods

def install_viralvigor(env):
	try:
		_initialize_area_vigor()
		_initialize_host()
		_add_vigor()
		_add_tools_vigor()
	finally:
		disconnect_all()

def install_viralvigor_test(env):
	try:
		_initialize_area_vigor()
		cmd = ("""%s/VIGOR3.pl \
				-D yfv \
				-i %s/westnile.fasta \
				-O %s/westnile \
				> %s/westnile_test_run.log 2>&1 \
				""") % (vigor_dirs["VIGOR_RUNTIME_DIR"],vigor_dirs["VIGOR_SAMPLE_DATA_DIR"],vigor_dirs["VIGOR_TEST_OUTPUT_DIR"],env.VIGOR_SCRATCH_DIR)
		print("DEBUG: cmd[%s]" % cmd)
		run(cmd)
	finally:
		disconnect_all()

def install_viralvigor_validate(env):
	try:
		_initialize_area_vigor()
		sudo("rm -f %s/westnile.rpt" % vigor_dirs["VIGOR_TEST_OUTPUT_DIR"])
		sudo("rm -f %s/westnile.rpt" % vigor_dirs["VIGOR_SAMPLE_DATA_DIR"])
		with settings(hide("running","stdout")):
			results = run("""diff -Bwr %s %s || echo 'VALIDATION FAILED'""" % (vigor_dirs["VIGOR_SAMPLE_DATA_DIR"],vigor_dirs["VIGOR_TEST_OUTPUT_DIR"]))
		if results:
			print("\n\nValidation Failed:\n\n%s\n" % results)
	finally:
		disconnect_all()

def install_viralvigor_cleanall(env):
	try:
		_initialize_env("vigor")
		_remove_dir(env.VIGOR_ROOT_DIR)
		_remove_dir(env.VIGOR_SCRATCH_DIR)
		print("Vigor Removed\n")
	finally:
		disconnect_all()

# VIGOR - utility methods

def _initialize_area_vigor():
	machine = run("uname -m")
	
	if machine.find('64')>0:
		env.ARCH = 'x64-linux'
	else:
		env.ARCH = 'ia32-linux'
	
	_initialize_env("vigor")
	
	vigor_dirs["TOOLS_DIR"] = "%s/tools"                                     % env.VIGOR_ROOT_DIR
	vigor_dirs["VIGOR_STORED_DIR"] = "%s/vigor"                              % vigor_dirs["TOOLS_DIR"]
	vigor_dirs["VIGOR_RUNTIME_DIR"] = "%s/prod3"                             % vigor_dirs["VIGOR_STORED_DIR"]
	vigor_dirs["VIGOR_TEMPSPACE_DIR"] = "%s/tempspace"                       % env.VIGOR_SCRATCH_DIR
	vigor_dirs["VIGOR_SAMPLE_DATA_DIR"] = "%s/samples"                       % vigor_dirs["VIGOR_STORED_DIR"]
	vigor_dirs["VIGOR_TEST_OUTPUT_DIR"] = "%s/test"                          % vigor_dirs["VIGOR_STORED_DIR"]
	vigor_dirs["BLAST_DIR"] = "%s/blast"                                     % vigor_dirs["TOOLS_DIR"]
	vigor_dirs["CLUSTALW_DIR"] = "%s/clustalw"                               % vigor_dirs["TOOLS_DIR"]
	vigor_dirs["EXE_DIR"] = vigor_dirs["VIGOR_RUNTIME_DIR"]
	
	vigor_names["BLAST_NAME"] = 'blast-2.2.15'
	vigor_names["CLUSTALW_NAME"] = 'clustalw-1.83'
	vigor_names["VIGOR_NAME"] = 'vigor-GSCcloud'
	
	vigor_tars["VIGOR_TAR_FILENAME"] = "%s.tgz"                              % vigor_names["VIGOR_NAME"]
	vigor_tars["BLAST_TAR_FILENAME"] = "%s-%s.tar.gz"                        % (vigor_names["BLAST_NAME"],env.ARCH)
	vigor_tars["CLUSTALW_TAR_FILENAME"] = "%s-%s.deb"                        % (vigor_names["CLUSTALW_NAME"],env.ARCH)
	
	print("user:   %(user)s" % env)
	print("host:   %(host)s" % env)
	print("ARCH:   %(ARCH)s" % env)
	print("ROOT DIR:   %(VIGOR_ROOT_DIR)s" % env)
	print("SCRATCH DIR:   %(VIGOR_SCRATCH_DIR)s" % env)
	for name in sorted(vigor_dirs.keys()):
		print("%s:   %s" % (name,vigor_dirs[name]))
	for name in sorted(vigor_urls.keys()):
		print("%s:   %s" % (name,vigor_urls[name]))
	print("BLAST_NAME:   %s" % vigor_names["BLAST_NAME"])
	print("CLUSTALW_NAME:   %s" % vigor_names["CLUSTALW_NAME"])
	print("VIGOR_NAME:   %s" % vigor_names["VIGOR_NAME"])
	for name in sorted(vigor_tars.keys()):
		print("%s:   %s" % (name,vigor_tars[name]))

def _initialize_host():
	local("ssh-keygen -R %(host)s" % env)
	_fix_etc_hosts()
	_create_vigor_scratch_dir()

def _add_vigor():
	print("Installing VIGOR...")
	_create_vigor_tempspace_dir()
	_create_vigor_scratch_dir()
	_add_package(dependency_URL, vigor_tars["VIGOR_TAR_FILENAME"], vigor_dirs["VIGOR_STORED_DIR"], "tar")
	sudo("chmod 755 %s" % os.path.join(vigor_dirs["VIGOR_RUNTIME_DIR"], "*.pl"))
	if not _path_exists(os.path.join(vigor_dirs["EXE_DIR"], "perl")):
		sudo("ln -sf %s %s" % ("/usr/bin/perl", vigor_dirs["EXE_DIR"]))
		sudo("ln -sf %s %s" % ("/usr/bin/perl", "/usr/local/bin"))
	if not _path_exists(os.path.join(vigor_dirs["EXE_DIR"], "vigorscratch")):
		sudo("ln -sf %s %s/vigorscratch" % (vigor_dirs["VIGOR_TEMPSPACE_DIR"], vigor_dirs["EXE_DIR"]))

def _add_tools_vigor():
	print("Install tools...")
	_create_tools_dir()
	_add_blast()
	_add_clustalw()
	_apt_get_install("libapache-dbi-perl")
	_apt_get_install("libclass-dbi-sqlite-perl")

def _fix_etc_hosts():
	internal_ip = sudo("hostname")
	print("internal_ip[%s]" % internal_ip)
	filespec = "/etc/hosts"
	sudo("echo '127.0.0.1 %s' >> %s" % (internal_ip, filespec))

def _create_vigor_tempspace_dir():
	if not _path_is_dir(vigor_dirs["VIGOR_TEMPSPACE_DIR"]):
		sudo("mkdir -p %s" % vigor_dirs["VIGOR_TEMPSPACE_DIR"])
		sudo("chown -R %s:%s %s" % (env.user, env.user, vigor_dirs["VIGOR_TEMPSPACE_DIR"]))
		sudo("find %s -type d -exec chmod 777 {} \;" % vigor_dirs["VIGOR_TEMPSPACE_DIR"])

def _create_vigor_scratch_dir():
	if not _path_is_dir(env.VIGOR_SCRATCH_DIR):
		sudo("mkdir -p %s" % env.VIGOR_SCRATCH_DIR)
	sudo("find %s -type f -exec chmod 666 {} \;" % env.VIGOR_SCRATCH_DIR)
	sudo("find %s -type d -exec chmod 777 {} \;" % env.VIGOR_SCRATCH_DIR)

def _create_tools_dir():
	if not _path_is_dir(vigor_dirs["TOOLS_DIR"]):
		sudo("mkdir -p %s" % vigor_dirs["TOOLS_DIR"])
	sudo("chown -R %s:%s %s" % (env.user,env.user,vigor_dirs["TOOLS_DIR"]))

def _add_blast():
	print("    Installing blast...")
	_create_tools_dir()
	_add_package(dependency_URL, vigor_tars["BLAST_TAR_FILENAME"], vigor_dirs["BLAST_DIR"], "tar")
	if not _path_exists(os.path.join(vigor_dirs["EXE_DIR"], "blastall")):
		sudo("ln -sf %s %s" % (os.path.join(vigor_dirs["BLAST_DIR"], vigor_names["BLAST_NAME"], "bin", "bl2seq"), vigor_dirs["EXE_DIR"]))
		sudo("ln -sf %s %s" % (os.path.join(vigor_dirs["BLAST_DIR"], vigor_names["BLAST_NAME"], "bin", "blastall"), vigor_dirs["EXE_DIR"]))
		sudo("ln -sf %s %s" % (os.path.join(vigor_dirs["BLAST_DIR"], vigor_names["BLAST_NAME"], "bin", "fastacmd"), vigor_dirs["EXE_DIR"]))
		sudo("ln -sf %s %s" % (os.path.join(vigor_dirs["BLAST_DIR"], vigor_names["BLAST_NAME"], "bin", "formatdb"), vigor_dirs["EXE_DIR"]))

def _add_clustalw():
	print("    Installing clustalw...")
	_create_tools_dir()
	_add_package(dependency_URL, vigor_tars["CLUSTALW_TAR_FILENAME"], vigor_dirs["CLUSTALW_DIR"], "deb")
	if not _path_exists(os.path.join(vigor_dirs["EXE_DIR"], "clustalw")):
		sudo("ln -sf %s %s" % (os.path.join(vigor_dirs["CLUSTALW_DIR"], vigor_names["CLUSTALW_NAME"], "clustalw"), vigor_dirs["EXE_DIR"]))


# VICVB - install methods

def install_vicvb(env):
	try:
		_initialize_env("vicvb")
		
		_apt_get_install("libperlio-gzip-perl")
		_apt_get_install("liblocal-lib-perl")
		
		tbl2asn_download_dir = "/usr/local/tbl2asn_download"
		tbl2asn_dir = "/usr/local/bin"
		if _path_exists(os.path.join(tbl2asn_dir,"tbl2asn")):
			sudo("mv %s/tbl2asn %s/tbl2asn_pre_VCR" % (tbl2asn_dir,tbl2asn_dir))
		_add_package("ftp://ftp.ncbi.nih.gov/toolbox/ncbi_tools/converters/by_program/tbl2asn","linux64.tbl2asn.gz",tbl2asn_download_dir,"gzip")
		sudo("chmod 777 %s/linux64.tbl2asn" % tbl2asn_download_dir)
		sudo("mv %s/linux64.tbl2asn %s/tbl2asn" % (tbl2asn_download_dir,tbl2asn_dir))
		_remove_dir(tbl2asn_download_dir)
		
		with cd("~"):
			sudo("git clone git://github.com/JCVI-Cloud/VICVB.git")
		with cd("~/VICVB"):
			sudo("lib/VICVB/data/install/install_to_dir_full.sh %s /mnt/galaxyTools/galaxy-central /" % (env.VICVB_LOCAL_DIR))
	finally:
		disconnect_all()

def install_vicvb_cleanall(env):
	try:
		_initialize_env("vicvb")
		_remove_dir(env.VICVB_LOCAL_DIR)
		_remove_dir(env.VICVB_GALAXY_DIR)
		with cd ("~"):
			sudo("rm -fr ~/VICVB")
		print("VICVB Removed\n")
	finally:
		disconnect_all()


# Common methods

def _initialize_env(pipeline):
	if pipeline == "viral":
		env.VIRAL_ROOT_DIR = "/usr/local/VHTNGS"
		if not _path_exists(env.VIRAL_ROOT_DIR):
			sudo("mkdir -p %s" % env.VIRAL_ROOT_DIR)
	elif pipeline == "vigor":
		env.VIGOR_ROOT_DIR = "/usr/local/VIGOR"
		if not _path_exists(env.VIGOR_ROOT_DIR):
			sudo("mkdir -p %s" % env.VIGOR_ROOT_DIR)
		env.VIGOR_SCRATCH_DIR = "/usr/local/scratch/vigor"
		if not _path_exists(env.VIGOR_SCRATCH_DIR):
			sudo("mkdir -p %s" % env.VIGOR_SCRATCH_DIR)
			sudo("find %s -type f -exec chmod 666 {} \;" % env.VIGOR_SCRATCH_DIR)
			sudo("find %s -type d -exec chmod 777 {} \;" % env.VIGOR_SCRATCH_DIR)
	else:
		env.VICVB_LOCAL_DIR = "/usr/local/VICVB";
		env.VICVB_GALAXY_DIR = "/mnt/galaxyTools/galaxy-central/static/vicvb";

def _add_package(download_url, filename, install_dir, type):
	if not _path_is_dir(install_dir):
		sudo("mkdir -p %s" % install_dir)
	with cd(install_dir):
		if not _path_exists(os.path.join(install_dir, filename)):
			sudo("""wget --no-host-directories --cut-dirs=1 --directory-prefix=%s %s/%s""" % (install_dir, download_url, filename))
			if type == "tar":
				sudo("tar xvfz %s" % filename)
			elif type == "bz2":
				sudo("tar xfj %s" % filename)
			elif type == "gzip":
				sudo("gunzip %s" % filename)
			else: 
				sudo("dpkg -x %s %s" % (filename,install_dir))
				sudo("mkdir %s/%s" % (install_dir, vigor_names["CLUSTALW_NAME"]))
				sudo("cp %s/usr/bin/* %s/%s" % (install_dir,install_dir,vigor_names["CLUSTALW_NAME"]))
	sudo("chown -R %s:%s %s" % (env.user, env.user, install_dir))
	sudo("find %s -type d -exec chmod 755 {} \;" % install_dir)

def _remove_dir(dirspec):
	if _path_is_dir(dirspec):
		_unlock_dir(dirspec)
		sudo("rm -rf %s" % dirspec)
	else:
		print("DEBUG: _remove_dir[%s] -- NOT FOUND" % dirspec)

def _unlock_dir(dirspec):
	with settings(hide("running","stdout")):
		sudo("find %s -type d -exec chmod 755 {} \;" % dirspec)
		sudo("find %s -type d -exec chmod g+s {} \;" % dirspec)
		sudo("find %s -type f -exec chmod 644 {} \;" % dirspec)

def _apt_get_install(tool):
	sudo("apt-get -q -y --force-yes install %s" % tool)

def _path_exists(path):
	found = False
	with settings(hide("running","stdout")):
		result = sudo("test -e '%s' || echo 'FALSE'" % path)
	if result != "FALSE": found = True
	return found

def _path_is_dir(path):
	found = False
	with settings(hide("running","stdout")):
		result = sudo("test -d '%s' || echo 'FALSE'" % path)
	if result != "FALSE": found = True
	return found

def _set_pre_VCR(filename,user,group):
	sudo("cp %s %s_pre_VCR" %(filename,filename))
	sudo("chown %s:%s %s_pre_VCR" % (user,group,filename))

def _get_file_string(filename,directory):
	fh = open("%s/%s" % (directory,filename))
	string = mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)
	fh.close()
	return string

########NEW FILE########
__FILENAME__ = versioncheck
"""Tool specific version checking to identify out of date dependencies.

This provides infrastructure to check version strings against installed
tools, enabling re-installation if a version doesn't match. This is a
lightweight way to avoid out of date dependencies.
"""
from distutils.version import LooseVersion

from cloudbio.custom import shared
from cloudbio.fabutils import quiet

def _parse_from_stdoutflag(out, flag, stdout_index=-1):
    """Extract version information from a flag in verbose stdout.

    flag -- text information to identify the line we should split for a version
    stdout_index -- Position of the version information in the split line. Defaults
    to the last item.
    """
    for line in out.split("\n") + out.stderr.split("\n"):
        if line.find(flag) >= 0:
            parts = line.split()
            return parts[stdout_index].strip()
    print "Did not find version information with flag %s from: \n %s" % (flag, out)
    return ""

def _clean_version(x):
    if x.startswith("upstream/"):
        x = x.replace("upstream/", "")
    if x.startswith("("):
        x = x[1:].strip()
    if x.endswith(")"):
        x = x[:-1].strip()
    if x.startswith("v"):
        x = x[1:].strip()
    return x

def up_to_date(env, cmd, version, args=None, stdout_flag=None,
               stdout_index=-1):
    iversion = get_installed_version(env, cmd, version, args, stdout_flag,
                                     stdout_index)
    if not iversion:
        return False
    else:
        return LooseVersion(iversion) >= LooseVersion(version)

def is_version(env, cmd, version, args=None, stdout_flag=None,
               stdout_index=-1):
    iversion = get_installed_version(env, cmd, version, args, stdout_flag,
                                     stdout_index)
    if not iversion:
        return False
    else:
        return LooseVersion(iversion) == LooseVersion(version)

def get_installed_version(env, cmd, version, args=None, stdout_flag=None,
                          stdout_index=-1):
    """Check if the given command is up to date with the provided version.
    """
    if shared._executable_not_on_path(cmd):
        return False
    if args:
        cmd = cmd + " " + " ".join(args)
    with quiet():
        path_safe = ("export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:{s}/lib/pkgconfig && "
                     "export PATH=$PATH:{s}/bin && "
                     "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{s}/lib && ".format(s=env.system_install))
        out = env.safe_run_output(path_safe + cmd)
    if stdout_flag:
        iversion = _parse_from_stdoutflag(out, stdout_flag, stdout_index)
    else:
        iversion = out.strip()
    iversion = _clean_version(iversion)
    if " not found in the pkg-config search path" in iversion:
        return False
    return iversion

########NEW FILE########
__FILENAME__ = config
import inspect
import os
import yaml


def parse_settings(name="deploy/settings.yaml"):
    return _read_yaml(_path_from_root(name))


def _path_from_root(name):
    root_path = os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), "..", "..")
    file_path = os.path.join(root_path, name)
    return file_path


def _read_yaml(yaml_file):
    with open(yaml_file) as in_handle:
        return yaml.load(in_handle)

########NEW FILE########
__FILENAME__ = main
from argparse import ArgumentParser
import yaml

from cloudbio.deploy import deploy

DESC = "Creates an on-demand cloud instance, sets up applications, and transfer files to it."

## Properties that may be specified as args or in settings file,
## argument takes precedence.
ARG_PROPERTIES = [
  # VM launcher options
  "files",
  "compressed_files",
  "actions",
  "runtime_properties",
  "vm_provider",
  "hostname",

  # CloudBioLinux options
  "target",
  "flavor",
  "package",

  # CloudMan options
  "target_bucket",

  # Galaxy options
  "galaxy_tool_version",
  "galaxy_tool_name",
  "galaxy_tool_dir",
]


def main():
    args = parse_args()
    options = parse_settings(args.settings)

    for property in ARG_PROPERTIES:
        _copy_arg_to_options(options, args, property)

    for fabric_property, fabric_value in zip(args.fabric_properties, args.fabric_values):
        if "fabricrc_overrides" not in options:
            options["fabricrc_overrides"] = {}
        options["fabricrc_overrides"][fabric_property] = fabric_value

    deploy(options)


def _copy_arg_to_options(options, args, property):
    arg_property = getattr(args, property)
    if arg_property or not property in options:
        options[property] = arg_property


def parse_args():
    parser = ArgumentParser(DESC)
    parser.add_argument("--settings", dest="settings", default="settings.yaml")
    parser.add_argument('--action', dest="actions", action="append", default=[])
    parser.add_argument('--runtime_property', dest="runtime_properties", action="append", default=[])
    parser.add_argument('--compressed_file', dest="compressed_files", action="append", default=[], help="file to transfer to new instance and decompress")
    parser.add_argument('--file', dest="files", action="append", default=[], help="file to transfer to new instance")
    parser.add_argument("--vm_provider", dest="vm_provider", default=None, help="libcloud driver to use (or vagrant) (e.g. aws, openstack)")
    parser.add_argument("--hostname", dest="hostname", default=None, help="Newly created nodes are created with this specified hostname.")

    # CloudBioLinux options
    parser.add_argument("--target", dest="target", default=None, help="Specify a CloudBioLinux target, used with action install_biolinux action")
    parser.add_argument("--flavor", dest="flavor", default=None, help="Specify a CloudBioLinux flavor, used with action install_biolinux action")
    parser.add_argument("--package", dest="package", default=None, help="Specify a CloudBioLinux package, used with action install_custom")

    # CloudMan related options
    parser.add_argument("--target_bucket", dest="target_bucket", default=None, help="Specify a target bucket for CloudMan bucket related actions.")

    # Galaxy options
    parser.add_argument("--galaxy_tool_version", dest="galaxy_tool_version")
    parser.add_argument("--galaxy_tool_name", dest="galaxy_tool_name")
    parser.add_argument("--galaxy_tool_dir", dest="galaxy_tool_dir")

    parser.add_argument('--fabric_property', dest="fabric_properties", action="append", default=[])
    parser.add_argument('--fabric_value', dest="fabric_values", action="append", default=[])

    args = parser.parse_args()
    if len(args.actions) == 0:
        args.actions = ["transfer"]
    return args


def parse_settings(name):
    if not name == "__none__":
        # Rather just die if settings.yaml does not exist or is not set, but would also
        # like to support pure command-line driven mode so make settings.yaml if
        # --settings=__none__ is passed to application.
        return _read_yaml(name)
    else:
        return {}


def _read_yaml(yaml_file):
    with open(yaml_file) as in_handle:
        return yaml.load(in_handle)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = cloudman
from datetime import datetime
from os.path import exists, join
from os import listdir
from tempfile import mkdtemp

from cloudbio.deploy.util import eval_template

from boto.exception import S3ResponseError
from boto.s3.key import Key

import yaml

from fabric.api import local, lcd, env

DEFAULT_BUCKET_NAME = 'cloudman'

DEFAULT_CLOUDMAN_PASSWORD = 'adminpass'
DEFAULT_CLOUDMAN_CLUSTER_NAME = 'cloudman'


def bundle_cloudman(vm_launcher, options):
    cloudman_options = options.get('cloudman')
    cloudman_repository_path = cloudman_options['cloudman_repository']
    delete_repository = False
    bucket_source = cloudman_options.get("bucket_source")
    if cloudman_repository_path.startswith("http"):
        # Not a local path, lets clone it out of a remote repostiroy,
        temp_directory = mkdtemp()
        if cloudman_repository_path.endswith(".git"):
            branch_opts = ""
            repository_branch = cloudman_options.get('repository_branch', None)
            if repository_branch:
                branch_opts = "-b '%s'" % repository_branch
            clone_command = "git clone " + branch_opts + " '%s' '%s'"
        else:
            clone_command = "hg clone '%s' '%s'"
        local(clone_command % (cloudman_repository_path, temp_directory))
        cloudman_repository_path = temp_directory
        delete_repository = True
    try:
        with lcd(cloudman_repository_path):
            try:
                local("tar czvf cm.tar.gz *")
                local("mv cm.tar.gz '%s'" % bucket_source)
            finally:
                local("rm -f cm.tar.gz")
    finally:
        if delete_repository:
            local("rm -rf '%s'" % cloudman_repository_path)


def cloudman_launch(vm_launcher, options):
    cloudman_options = options.get('cloudman')
    image_id = cloudman_options.get('image_id', None)
    if str(image_id).lower() == "__use_snaps__":
        # TODO: Make more flexible
        bucket_source = cloudman_options.get("bucket_source")
        snaps_path = join(bucket_source, "snaps.yaml")
        if not exists(snaps_path):
            raise Exception("CloudMan AMI set to __use_snaps__ but now snaps.yaml file could be found with path %s" % snaps_path)
        snaps = {}
        with open(snaps_path, "r") as in_handle:
            snaps = yaml.load(in_handle)
        clouds = snaps["clouds"]
        if len(clouds) != 1:
            raise Exception("Exactly one cloud must be defined snaps.yaml for the deployer's CloudMan launch to work.")
        regions = clouds[0]["regions"]
        if len(regions) != 1:
            raise Exception("Exactly one region must be defined snaps.yaml for the deployer's CloudMan launch to work.")
        deployments = regions[0]["deployments"]
        if len(deployments) != 1:
            raise Exception("Exactly one deployment must be defined snaps.yaml for the deployer's CloudMan launch to work.")
        image_id = deployments[0]["default_mi"]

    size_id = cloudman_options.get('size_id', None)
    user_data = _prepare_user_data(vm_launcher, cloudman_options)
    vm_launcher.create_node('cloudman',
                            image_id=image_id,
                            size_id=size_id,
                            ex_userdata=user_data)


def sync_cloudman_bucket(vm_launcher, options):
    bucket = options.get("target_bucket", None)
    if not bucket:
        bucket = __get_bucket_default(options)
    bucket_source = options.get("cloudman", {}).get("bucket_source", None)
    if not bucket or not bucket_source:
        print "Warning: Failed to sync cloud bucket, bucket or bucket_source is undefined."
        return
    conn = vm_launcher.boto_s3_connection()
    for file_name in listdir(bucket_source):
        _save_file_to_bucket(conn, bucket, file_name, join(bucket_source, file_name))


def _save_file_to_bucket(conn, bucket_name, remote_filename, local_file, **kwargs):
    """ Save the local_file to bucket_name as remote_filename. Also, any additional
    arguments passed as key-value pairs, are stored as file's metadata on S3."""
    # print "Establishing handle with bucket '%s'..." % bucket_name
    b = _get_bucket(conn, bucket_name)
    if b is not None:
        # print "Establishing handle with key object '%s'..." % remote_filename
        k = Key( b, remote_filename )
        print "Attempting to save file '%s' to bucket '%s'..." % (remote_filename, bucket_name)
        try:
            # Store some metadata (key-value pairs) about the contents of the file being uploaded
            # Note that the metadata must be set *before* writing the file
            k.set_metadata('date_uploaded', str(datetime.utcnow()))
            for args_key in kwargs:
                print "Adding metadata to file '%s': %s=%s" % (remote_filename, args_key, kwargs[args_key])
                k.set_metadata(args_key, kwargs[args_key])
            print "Saving file '%s'" % local_file
            k.set_contents_from_filename(local_file)
            print "Successfully added file '%s' to bucket '%s'." % (remote_filename, bucket_name)
            make_public = True
            if make_public:
                k.make_public()
        except S3ResponseError, e:
            print "Failed to save file local file '%s' to bucket '%s' as file '%s': %s" % ( local_file, bucket_name, remote_filename, e )
            return False
        return True
    else:
        return False


def __get_bucket_default(options):
    cloudman_options = options.get("cloudman", {})
    user_data = cloudman_options = cloudman_options.get('user_data', None) or {}
    bucket = user_data.get("bucket_default", None)
    return bucket


def _prepare_user_data(vm_launcher, cloudman_options):
    cloudman_user_data = cloudman_options.get('user_data', None) or {}
    cluster_name = \
        cloudman_options.get('cluster_name', DEFAULT_CLOUDMAN_CLUSTER_NAME)
    password = cloudman_options.get('password', DEFAULT_CLOUDMAN_PASSWORD)
    access_key = vm_launcher.access_id()
    secret_key = vm_launcher.secret_key()

    _set_property_if_needed(cloudman_user_data, 'access_key', access_key)
    _set_property_if_needed(cloudman_user_data, 'secret_key', secret_key)
    cluster_name = eval_template(env, cluster_name)
    _set_property_if_needed(cloudman_user_data, 'cluster_name', cluster_name)
    _set_property_if_needed(cloudman_user_data, 'password', password)

    return yaml.dump(cloudman_user_data)


def _set_property_if_needed(user_data, property, value):
    if property not in user_data:
        user_data[property] = value


def _get_bucket(s3_conn, bucket_name):
    b = None
    for i in range(0, 5):
        try:
            b = s3_conn.get_bucket(bucket_name)
            break
        except S3ResponseError:
            print "Bucket '%s' not found, attempt %s/5" % (bucket_name, i)
            return None
    return b


local_actions = {
    "cloudman_launch": cloudman_launch,
    "sync_cloudman_bucket": sync_cloudman_bucket,
    "bundle_cloudman": bundle_cloudman,
}

########NEW FILE########
__FILENAME__ = galaxy
from cloudbio.galaxy.tools import _install_application


def install_tool(options):
    version = options.get("galaxy_tool_version")
    name = options.get("galaxy_tool_name")
    install_dir = options.get("galaxy_tool_dir", None)
    _install_application(name, version, tool_install_dir=install_dir)


configure_actions = {
    "install_galaxy_tool": install_tool,
}

########NEW FILE########
__FILENAME__ = gvl
"""
Deployer plugin containing actions related to older galaxy-vm-launcher functionality.
"""

import os
import time

from cloudbio.biodata.genomes import install_data, install_data_s3
from cloudbio.deploy import get_main_options_string, _build_transfer_options, _do_transfer, transfer_files, get_boolean_option
from cloudbio.deploy.util import wget, start_service, ensure_can_sudo_into, sudoers_append
from cloudbio.galaxy.utils import _chown_galaxy
from cloudbio.galaxy.tools import _setup_install_dir
from cloudbio.custom.galaxy import install_galaxy_webapp
from cloudbio.galaxy import _setup_users, _setup_xvfb, _install_nginx_standalone, _setup_postgresql
from cloudbio.package import _configure_and_install_native_packages
from cloudbio.package.deb import _apt_packages


from fabric.api import put, run, env, sudo, get, cd
from fabric.context_managers import prefix
from fabric.contrib.files import append, contains, exists


## Deprecated galaxy-vm-launcher way of setting up biodata.
def setup_genomes(options):
    install_proc = install_data
    sudo("mkdir -p %s" % env.data_files)
    sudo("chown -R %s:%s %s" % (env.user, env.user, env.data_files))
    put("config/tool_data_table_conf.xml", "%s/tool_data_table_conf.xml" % env.galaxy_home)
    indexing_packages = ["bowtie", "bwa", "samtools"]
    path_extensions = ":".join(map(lambda package: "/opt/galaxyTools/tools/%s/default" % package, indexing_packages))
    with prefix("PATH=$PATH:%s" % path_extensions):
        if 'S3' == options['genome_source']:
            install_proc = install_data_s3
        install_proc(options["genomes"])
    if options.get("setup_taxonomy_data", False):
        setup_taxonomy_data()
    stash_genomes_where = get_main_options_string(options, "stash_genomes")
    if stash_genomes_where:
        stash_genomes(stash_genomes_where)


def setup_taxonomy_data():
    """
    Setup up taxonomy data required by Galaxy. Need to find another place to put
    this, it is useful.
    """
    taxonomy_directory = os.path.join(env.data_files, "taxonomy")
    env.safe_sudo("mkdir -p '%s'" % taxonomy_directory, user=env.user)
    with cd(taxonomy_directory):
        taxonomy_url = "ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
        gi_taxid_nucl = "ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_nucl.dmp.gz"
        gi_taxid_prot = "ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_prot.dmp.gz"
        wget(taxonomy_url)
        wget(gi_taxid_nucl)
        wget(gi_taxid_prot)
        run("gunzip -c taxdump.tar.gz | tar xvf -")
        run("gunzip gi_taxid_nucl.dmp.gz")
        run("gunzip gi_taxid_prot.dmp.gz")
        run("cat gi_taxid_nucl.dmp gi_taxid_prot.dmp > gi_taxid_all.dmp")
        run("sort -n -k 1 gi_taxid_all.dmp > gi_taxid_sorted.txt")
        run("rm gi_taxid_nucl.dmp gi_taxid_prot.dmp gi_taxid_all.dmp")
        run("cat names.dmp | sed s/[\\(\\)\\'\\\"]/_/g > names.temporary")
        run("mv names.dmp names.dmp.orig")
        run("mv names.temporary names.dmp")


def stash_genomes(where):
    with _cd_indices_parent():
        sudo("chown %s:%s ." % (env.user, env.user))
        indices_dir_name = _indices_dir_name()
        remote_compressed_indices = "%s.tar.gz" % indices_dir_name
        run("tar czvf %s %s" % (remote_compressed_indices, indices_dir_name))
        if where == 'download':
            get(remote_path=remote_compressed_indices,
                local_path="compressed_genomes.tar.gz")
        elif where == 'opt':
            sudo("cp %s /opt/compressed_genomes.tar.gz" % remote_compressed_indices)
        else:
            print "Invalid option specified for stash_genomes [%s] - valid values include download and opt." % where


def upload_genomes(options):
    with _cd_indices_parent():
        sudo("chown %s:%s ." % (env.user, env.user))
        indices_dir_name = _indices_dir_name()
        _transfer_genomes(options)
        run("rm -rf %s" % indices_dir_name)
        run("tar xzvfm compressed_genomes.tar.gz")
        sudo("/etc/init.d/galaxy restart")


def purge_genomes():
    sudo("rm -rf %s" % env.data_files)


def _cd_indices_parent():
    return cd(_indices_parent())


def _indices_parent():
    parent_dir = os.path.abspath(os.path.join(env.data_files, ".."))
    return parent_dir


def _indices_dir_name():
    indices_dir = env.data_files
    if indices_dir.endswith("/"):
        indices_dir = indices_dir[0:(len(indices_dir) - 1)]
    indices_dir_name = os.path.basename(indices_dir)
    return indices_dir_name


def galaxy_transfer(vm_launcher, options):
    transfer_files(options)
    # Upload local compressed genomes to the cloud image, obsecure option.
    do_upload_genomes = get_boolean_option(options, 'upload_genomes', False)
    if do_upload_genomes:
        upload_genomes(options)
    if not _seed_at_configure_time(options):
        seed_database()
        seed_workflows(options)
    wait_for_galaxy()
    create_data_library_for_uploads(options)


def create_data_library_for_uploads(options):
    with cd(os.path.join(env.galaxy_home, "scripts", "api")):
        db_key_arg = get_main_options_string(options, 'db_key')
        transfer_history_name = get_main_options_string(options, 'transfer_history_name')
        transfer_history_api_key = get_main_options_string(options, 'transfer_history_api_key')
        cmd_template = 'python handle_uploads.py --api_key="%s" --db_key="%s" --history="%s" --history_api_key="%s" '
        galaxy_data = options["galaxy"]
        admin_user_api_key = galaxy_data["users"][0]["api_key"]
        cmd = cmd_template % (admin_user_api_key, db_key_arg, transfer_history_name, transfer_history_api_key)
        sudo("bash -c 'export PYTHON_EGG_CACHE=eggs; %s'" % cmd, user="galaxy")


def _seed_at_configure_time(options):
    if 'seed_galaxy' in options:
        return options['seed_galaxy'] == 'configure'
    else:
        return True


def copy_runtime_properties(vm_launcher, options):
    fqdn = vm_launcher.get_ip()
    runtime_properties_raw = options.get("runtime_properties", {})
    runtime_properties = {"FQDN": fqdn}
    for runtime_property_raw in runtime_properties_raw:
        (name, value) = runtime_property_raw.split(":")
        runtime_properties[name] = value
    export_file = ""
    for (name, value) in runtime_properties.iteritems():
        export_file = "export %s=%s\n%s" % (name, value, export_file)
    sudo('mkdir -p %s' % env.galaxy_home)
    _chown_galaxy(env, env.galaxy_home)
    sudo("echo '%s' > %s/runtime_properties" % (export_file, env.galaxy_home), user=env.galaxy_user)


def _transfer_genomes(options):
    # Use just transfer settings in YAML
    options = options['transfer']
    transfer_options = _build_transfer_options(options, _indices_parent(), env.user)
    transfer_options["compress"] = False
    _do_transfer(transfer_options, ["compressed_genomes.tar.gz"])


def wait_for_galaxy():

    while not "8080" in run("netstat -lant"):
        # Check if galaxy has started
        print "Waiting for galaxy to start."
        time.sleep(10)


def purge_galaxy():
    sudo("/etc/init.d/galaxy stop")
    sudo("rm -rf %s" % env.galaxy_home)
    init_script = "postgresql"
    # if env.postgres_version[0] < '9':
    #    # Postgres 8.4 had different name for script
    #    init_script = "postgresql-%s" % env.postgres_version
    sudo("/etc/init.d/%s restart" % init_script)
    sudo('psql  -c "drop database galaxy;"', user="postgres")
    sudo('psql  -c "create database galaxy;"', user="postgres")


def setup_galaxy(options):
    seed = _seed_at_configure_time(options)
    setup_galaxy(options, seed=seed)
    if seed:
        seed_workflows(options)


def _setup_galaxy(options, seed=True):
    """Deploy a Galaxy server along with some tools.
    """
    _setup_install_dir(env)  # Still needed? -John
    install_galaxy_webapp(env)
    #_fix_galaxy_permissions()
    _setup_shed_tools_dir()
    _setup_galaxy_log_dir()
    _migrate_galaxy_database()
    if seed:
        seed_database(options["galaxy"])
    _start_galaxy()


def _migrate_galaxy_database():
    with cd(env.galaxy_home):
        sudo("bash -c 'export PYTHON_EGG_CACHE=eggs; python ./scripts/build_universe_config.py conf.d; python -ES ./scripts/fetch_eggs.py; ./create_db.sh'", user="galaxy")


def seed_database(galaxy_data):
    with cd(env.galaxy_home):
        sudo("rm -f seed.py")
        _setup_database_seed_file(galaxy_data)
        sudo("bash -c 'export PYTHON_EGG_CACHE=eggs; python ./scripts/build_universe_config.py conf.d; python -ES ./scripts/fetch_eggs.py; python seed.py'", user="galaxy")


def seed_workflows(options):
    wait_for_galaxy()
    galaxy_data = options["galaxy"]
    with cd(os.path.join(env.galaxy_home, "workflows")):
        for user in galaxy_data["users"]:
            api_key = user["api_key"]
            workflows = None
            if "workflows" in user:
                workflows = user["workflows"]
            if not workflows:
                continue
            for workflow in workflows:
                sudo("bash -c 'export PYTHON_EGG_CACHE=eggs; bash import_all.sh %s %s'" % (api_key, workflow), user=env.galaxy_user)


def _setup_database_seed_file(galaxy_data):
    _seed_append("""from scripts.db_shell import *
from galaxy.util.bunch import Bunch
from galaxy.security import GalaxyRBACAgent
bunch = Bunch( **globals() )
bunch.engine = engine
# model.flush() has been removed.
bunch.session = db_session
# For backward compatibility with "model.context.current"
bunch.context = db_session
security_agent = GalaxyRBACAgent( bunch )
security_agent.sa_session = sa_session

def add_user(email, password, key=None):
    query = sa_session.query( User ).filter_by( email=email )
    if query.count() > 0:
        return query.first()
    else:
        user = User(email)
        user.set_password_cleartext(password)
        sa_session.add(user)
        sa_session.flush()

        security_agent.create_private_user_role( user )
        if not user.default_permissions:
            security_agent.user_set_default_permissions( user, history=True, dataset=True )

        if key is not None:
            api_key = APIKeys()
            api_key.user_id = user.id
            api_key.key = key
            sa_session.add(api_key)
            sa_session.flush()
        return user

def add_history(user, name):
    query = sa_session.query( History ).filter_by( user=user ).filter_by( name=name )
    if query.count() == 0:
        history = History(user=user, name=name)
        sa_session.add(history)
        sa_session.flush()
        return history
    else:
        return query.first()

""")
    i = 0
    for user in galaxy_data["users"]:
        username = user["username"]
        password = user["password"]
        api_key = user["api_key"]
        histories = None
        if "histories" in user:
            histories = user["histories"]
        user_object = "user_%d" % i
        _seed_append("""%s = add_user("%s", "%s", "%s")""" % (user_object, username, password, api_key))
        _import_histories(user_object, histories)
        i = i + 1


def _import_histories(user_object, histories):
    if not histories:
        return
    for history_name in histories:
        _import_history(user_object, history_name)


def _import_history(user_object, history_name):
    history_name_stripped = history_name.strip()
    if history_name_stripped:
        _seed_append("""add_history(%s, "%s")""" % (user_object, history_name_stripped))


def _seed_append(text):
    append("%s/seed.py" % env.galaxy_home, text, use_sudo=True)


def _start_galaxy():
    # Create directory to store galaxy service's pid file.
    _make_dir_for_galaxy("/var/lib/galaxy")
    start_service("galaxy")


def refresh_galaxy(target_galaxy_repo):
    _update_galaxy(target_galaxy_repo)
    sudo("/etc/init.d/galaxy restart", pty=False)


def _setup_galaxy_log_dir():
    _make_dir_for_galaxy("/var/log/galaxy")


def _setup_shed_tools_dir():
    _make_dir_for_galaxy("%s/../shed_tools" % env.galaxy_home)


def _make_dir_for_galaxy(path):
    sudo("mkdir -p '%s'" % path)
    _chown_galaxy(env, path)


def _update_galaxy(target_galaxy_repo):
    # Need to merge? -John
    hg_command = "hg pull %s; hg update" % target_galaxy_repo
    with cd(env.galaxy_home):
        sudo(hg_command, user=env.galaxy_user)


def refresh_galaxy_action(vm_launcher, options):
    refresh_galaxy(env.galaxy_repository)


def setup_image(options):
    _configure_package_holds(options)
    configure_MI(env)
    configure_smtp(options)
    configure_sudoers(options)


def _configure_package_holds(options):
    # No longer respected. TODO: Implement.
    if 'package_holds' in options:
        env.package_holds = options['package_holds']
    else:
        env.package_holds = None


def configure_smtp(options):
    if 'smtp_server' in options:
        smtp_server = options['smtp_server']
        username = options['smtp_user']
        password = options['smtp_password']
        conf_file_contents = """mailhub=%s
UseSTARTTLS=YES
AuthUser=%s
AuthPass=%s
FromLineOverride=YES
""" % (smtp_server, username, password)
        _apt_packages(pkg_list=["ssmtp"])
        sudo("""echo "%s" > /etc/ssmtp/ssmtp.conf""" % conf_file_contents)
        aliases = """root:%s:%s
galaxy:%s:%s
%s:%s:%s""" % (username, smtp_server, username, smtp_server, env.user, username, smtp_server)
        sudo("""echo "%s" > /etc/ssmtp/revaliases""" % aliases)


def configure_sudoers(options):
    if "sudoers_additions" in options:
        for addition in options["sudoers_additions"]:
            sudoers_append(addition)


def configure_MI(env):
    # Clean this next line up.
    _configure_and_install_native_packages(env, ["minimal", "cloudman", "galaxy"])
    # _update_system()
    _setup_users(env)
    _setup_xvfb(env)
    _required_programs(env)


# == required programs
def _required_programs(env):
    """ Install required programs """
    if not exists(env.install_dir):
        sudo("mkdir -p %s" % env.install_dir)
        sudo("chown %s %s" % (env.user, env.install_dir))

    # Setup global environment for all users
    install_dir = os.path.split(env.install_dir)[0]
    exports = ["export PATH=%s/bin:%s/sbin:$PATH" % (install_dir, install_dir),
               "export LD_LIBRARY_PATH=%s/lib" % install_dir]
    for e in exports:
        _ensure_export(e)
    # Install required programs
    _install_nginx_standalone(env)
    _start_nginx(env)
    _deploy_setup_postgresql(env)

    # Verify this is not needed.
    # _install_samtools()


def _ensure_export(command):
    if not contains('/etc/bash.bashrc', command):
        append('/etc/bash.bashrc', command, use_sudo=True)


def _start_nginx(env):
    galaxy_data = env.galaxy_data_mount
    env.safe_sudo("mkdir -p '%s'" % env.galaxy_data)
    _chown_galaxy(env, galaxy_data)
    start_service("nginx")


def _deploy_setup_postgresql(env):
    ensure_can_sudo_into("postgres")
    _setup_postgresql(env)


configure_actions = {"setup_image": setup_image,
                     "setup_genomes": setup_genomes,
                     "purge_genomes": purge_genomes,
                     "setup_galaxy": setup_galaxy,
                     "purge_galaxy": purge_galaxy,
                    }

ready_actions = {"galaxy_transfer": galaxy_transfer,
                 "refresh_galaxy": refresh_galaxy_action,
                 "copy_runtime_properties": copy_runtime_properties,
}

compound_actions = {"configure": ["setup_image", "setup_tools", "setup_genomes", "setup_galaxy", "setup_ssh_key"],
                    "reinstall_galaxy": ["purge_galaxy", "setup_galaxy"],
                    "reinstall_genomes": ["purge_genomes", "setup_genomes"],
                    "reinstall_tools": ["purge_tools", "setup_tools"]
}

########NEW FILE########
__FILENAME__ = util
from string import Template
from time import strftime
import os

from fabric.api import local, sudo, env, put, get
from fabric.contrib.files import exists, append


def setup_install_dir():
    """Sets up install dir and ensures its owned by Galaxy"""
    if not exists(env.install_dir):
        sudo("mkdir -p %s" % env.install_dir)
    if not exists(env.jars_dir):
        sudo("mkdir -p %s" % env.jars_dir)
    # TODO: Fix bug here
    chown_galaxy(os.path.split(env.install_dir)[0])


def eval_template(env, template_str):
    props = {
        "env": env,
        "the_date": strftime('%Y%m%d'),
        "the_date_with_time": strftime('%Y%m%d_%H%M%S'),
    }
    return Template(template_str).safe_substitute(props)


def ensure_can_sudo_into(user):
    sudoers_append("%admin  ALL = (" + user + ") NOPASSWD: ALL")


def sudoers_append(line):
    append("/etc/sudoers", line, use_sudo=True)


def start_service(service_name):
    # For reasons I don't understand this doesn't work for galaxy init
    # script unless pty=False
    sudo("/etc/init.d/%s start" % service_name, pty=False)


def wget(url, install_command=sudo, file_name=None):
    if not file_name:
        file_name = os.path.split(url)[-1]
        if '?' in file_name:
            file_name = file_name[0:file_name.index('?')]
    if ("cache_source_downloads" in env) and (not env.cache_source_downloads):
        install_command("wget %s -O %s" % (url, file_name))
    else:
        cache_dir = env.source_cache_dir
        if not cache_dir:
            cache_dir = ".downloads"
        cached_file = os.path.join(cache_dir, file_name)
        if os.path.exists(cached_file):
            put(cached_file, file_name)
        else:
            install_command("wget %s -O %s" % (url, file_name))
            local("mkdir -p '%s'" % cache_dir)
            get(file_name, cached_file)

########NEW FILE########
__FILENAME__ = transfer
import os
import gzip

from operator import itemgetter
from sys import exit
from threading import Thread
from threading import Condition
from Queue import Queue

from fabric.api import local, put, sudo, cd
from fabric.colors import red



class FileSplitter:
    """
    Works like the UNIX split command break up a file into parts like:
        filename_aaaaaaaaa
        filename_aaaaaaaab
        etc...
    """

    def __init__(self, chunk_size, destination_directory, callback):
        self.chunk_size = chunk_size * 1024 * 1024
        self.destination_directory = destination_directory
        self.chunk_callback = callback

    def split_file(self, path, compress, transfer_target):
        basename = os.path.basename(path)
        file_size = os.path.getsize(path)
        total_bytes = 0
        chunk_num = 0
        suffix = ''
        if compress:
            suffix = '.gz'

        input = open(path, 'rb')
        while True:
            chunk_name = "%s_part%08d%s" % (basename, chunk_num, suffix)
            chunk_path = os.path.join(self.destination_directory, chunk_name)
            this_chunk_size = min(self.chunk_size, file_size - total_bytes)
            if this_chunk_size <= 0:
                break

            chunk = input.read(this_chunk_size)
            total_bytes += len(chunk)
            if compress:
                chunk_output = gzip.open(chunk_path, 'wb')
            else:
                chunk_output = file(chunk_path, 'wb')
            chunk_output.write(chunk)
            chunk_output.close()

            self.chunk_callback.handle_chunk(chunk_path, transfer_target)
            chunk_num += 1


class TransferTarget:

    def __init__(self, file, precompressed, transfer_manager):
        self.file = file
        self.precompressed = precompressed
        self.do_compress = transfer_manager.compress
        self.do_split = transfer_manager.chunk_size > 0
        self.local_temp = transfer_manager.local_temp
        basename = os.path.basename(file)
        if len(basename) < 1:
            print red(Exception("Invalid file specified - %s" % file))
            exit(-1)
        self.basename = basename

    def should_compress(self):
        return not self.precompressed and self.do_compress

    def split_up(self):
        return self.do_split

    def clean(self):
        if self.should_compress():
            local("rm -rf '%s'" % self.compressed_file())

    def compressed_basename(self):
        if not self.precompressed:
            compressed_basename = "%s.gz" % self.basename
        else:
            compressed_basename = self.basename
        return compressed_basename

    def decompressed_basename(self):
        basename = self.basename
        if basename.endswith(".gz"):
            decompressed_basename = basename[:-len(".gz")]
        else:
            decompressed_basename = basename
        return decompressed_basename

    def compressed_file(self):
        compressed_file = "%s/%s.gz" % (self.local_temp, self.basename)
        return compressed_file

    def build_simple_chunk(self):
        if self.should_compress():
            compressed_file = self.compressed_file()
            local("gzip -f -9 '%s' -c > '%s'" % (self.file, compressed_file))
            return TransferChunk(compressed_file, self)
        else:
            return TransferChunk(self.file, self)


class TransferChunk:

    def __init__(self, chunk_path, transfer_target):
        self.chunk_path = chunk_path
        self.transfer_target = transfer_target

    def clean_up(self):
        was_split = self.transfer_target.split_up()
        was_compressed = self.transfer_target.should_compress()
        if was_split or was_compressed:
            local("rm '%s'" % self.chunk_path)


class FileTransferManager:

    def __init__(self,
                 compress=True,
                 num_compress_threads=1,
                 num_transfer_threads=1,
                 num_decompress_threads=1,
                 chunk_size=0,
                 transfer_retries=3,
                 destination="/tmp",
                 transfer_as="root",
                 local_temp=None):
        self.compress = compress
        self.num_compress_threads = num_compress_threads
        self.num_transfer_threads = num_transfer_threads
        self.num_decompress_threads = num_decompress_threads
        self.chunk_size = chunk_size
        self.transfer_retries = transfer_retries
        self.destination = destination
        self.transfer_as = transfer_as
        self.local_temp = local_temp

        if not self.local_temp:
            self.local_temp = "/tmp"

        local("mkdir -p '%s'" % self.local_temp)
        self.file_splitter = FileSplitter(self.chunk_size, self.local_temp, self)

    def handle_chunk(self, chunk, transfer_target):
        self._enqueue_chunk(TransferChunk(chunk, transfer_target))

    def transfer_files(self, files=[], compressed_files=[]):
        self.transfer_complete = False
        self.transfer_complete_condition = Condition()

        self._setup_destination_directory()

        self._setup_workers()

        self._enqueue_files(files, compressed_files)

        self._wait_for_completion()

    def _setup_workers(self):
        self._setup_compress_threads()
        self._setup_transfer_threads()
        self._setup_decompress_threads()

    def _setup_destination_directory(self):
        sudo("mkdir -p %s" % self.destination)
        self._chown(self.destination)

    def _setup_compress_threads(self):
        self.compress_queue = Queue()
        self._launch_threads(self.num_compress_threads, self._compress_files)

    def _setup_decompress_threads(self):
        self.decompress_queue = Queue()
        self._launch_threads(self.num_decompress_threads, self._decompress_files)

    def _setup_transfer_threads(self):
        self.transfer_queue = Queue()  # For now just transfer one file at a time
        self._launch_threads(self.num_transfer_threads, self._put_files)

    def _launch_threads(self, num_threads, func):
        for thread_index in range(num_threads):
            t = Thread(target=func)
            t.daemon = True
            t.start()

    def _enqueue_files(self, files, compressed_files):
        transfer_targets = []

        for file in files:
            transfer_target = TransferTarget(file, False, self)
            transfer_targets.append(transfer_target)

        for compressed_file in compressed_files:
            transfer_target = TransferTarget(compressed_file, True, self)
            transfer_targets.append(transfer_target)

        transfer_targets = self._sort_transfer_targets(transfer_targets)
        for transfer_target in transfer_targets:
            self.compress_queue.put(transfer_target)

    def _sort_transfer_targets(self, transfer_targets):
        for i in range(len(transfer_targets)):
            transfer_target = transfer_targets[i]
            transfer_targets[i] = transfer_target, os.stat(transfer_target.file).st_size
        transfer_targets.sort(key=itemgetter(1), reverse=True)
        return  [transfer_target[0] for transfer_target in transfer_targets]

    def _wait_for_completion(self):
        self.compress_queue.join()
        self.transfer_queue.join()
        self.transfer_complete_condition.acquire()
        self.transfer_complete = True
        self.transfer_complete_condition.notifyAll()
        self.transfer_complete_condition.release()
        self.decompress_queue.join()

    def _compress_files(self):
        while True:
            try:
                transfer_target = self.compress_queue.get()
                file = transfer_target.file
                if self.chunk_size > 0:
                    should_compress = transfer_target.should_compress()
                    self.file_splitter.split_file(file, should_compress, transfer_target)
                    self.decompress_queue.put(transfer_target)
                else:
                    simple_chunk = transfer_target.build_simple_chunk()
                    self._enqueue_chunk(simple_chunk)
            except Exception as e:
                print red("Failed to compress a file to transfer")
                print red(e)
            finally:
                self.compress_queue.task_done()

    def _decompress_files(self):
        if self.chunk_size > 0:
            self.transfer_complete_condition.acquire()
            while not self.transfer_complete:
                self.transfer_complete_condition.wait()
            self.transfer_complete_condition.release()
        while True:
            try:
                transfer_target = self.decompress_queue.get()
                basename = transfer_target.basename
                chunked = transfer_target.split_up()
                compressed = transfer_target.do_compress or transfer_target.precompressed
                with cd(self.destination):
                    if compressed and chunked:
                        destination = transfer_target.decompressed_basename()
                        if transfer_target.precompressed:
                            sudo("cat '%s_part'* | gunzip -c > %s" % (basename, destination), user=self.transfer_as)
                        else:
                            sudo("zcat '%s_part'* > %s" % (basename, destination), user=self.transfer_as)
                        sudo("rm '%s_part'*" % (basename), user=self.transfer_as)
                    elif compressed:
                        sudo("gunzip -f '%s'" % transfer_target.compressed_basename(), user=self.transfer_as)
                    elif chunked:
                        sudo("cat '%s'_part* > '%s'" % (basename, basename), user=self.transfer_as)
                        sudo("rm '%s_part'*" % (basename), user=self.transfer_as)
            except Exception as e:
                print red("Failed to decompress or unsplit a transfered file.")
                print red(e)
            finally:
                self.decompress_queue.task_done()

    def _put_files(self):
        while True:
            try:
                transfer_chunk = self.transfer_queue.get()
                transfer_target = transfer_chunk.transfer_target
                compressed_file = transfer_chunk.chunk_path
                basename = os.path.basename(compressed_file)
                self._put_as_user(compressed_file, "%s/%s" % (self.destination, basename))
                if not transfer_target.split_up():
                    self.decompress_queue.put(transfer_target)
            except Exception as e:
                print red("Failed to upload a file.")
                print red(e)
            finally:
                transfer_chunk.clean_up()
                self.transfer_queue.task_done()

    def _chown(self, destination):
        sudo("chown %s:%s '%s'" % (self.transfer_as, self.transfer_as, destination))

    def _put_as_user(self, source, destination):
        for attempt in range(self.transfer_retries):
            retry = False
            try:
                put(source, destination, use_sudo=True)
                self._chown(destination)
            except BaseException as e:
                retry = True
                print red(e)
                print red("Failed to upload %s on attempt %d" % (source, attempt + 1))
            except:
                # Should never get here, delete this block when more confident
                retry = True
                print red("Failed to upload %s on attempt %d" % (source, attempt + 1))
            finally:
                if not retry:
                    return
        print red("Failed to transfer file %s, exiting..." % source)
        exit(-1)

    def _enqueue_chunk(self, transfer_chunk):
        self.transfer_queue.put(transfer_chunk)

########NEW FILE########
__FILENAME__ = volume
from fabric.api import run, env
from time import sleep
from boto.exception import EC2ResponseError
from .util import eval_template


def attach_volumes(vm_launcher, options, format=False):
    """
    """
    volumes = options.get("volumes", [])
    if not volumes:
        return
    boto_connection = vm_launcher.boto_connection()
    instance_id = run("curl --silent http://169.254.169.254/latest/meta-data/instance-id")
    for volume in volumes:
        volume_id = volume['id']
        device_id = volume['device']
        if not _get_attached(boto_connection, instance_id, device_id, valid_states=["attached", "attaching"]):
            boto_connection.attach_volume(volume_id, instance_id, device_id)
    for volume in volumes:
        volume_id = volume['id']
        device_id = volume['device']
        path = volume.get("path")

        while True:
            if _get_attached(boto_connection, instance_id, device_id):
                break

            sleep(5)
            print "Waiting for volume corresponding to device %s to attach" % device_id
            break

        # Don't mount if already mounted
        if _find_mounted_device_id(path):
            continue

        format = str(volume.get('format', "False")).lower()
        if format == "true":
            _format_device(device_id)
        env.safe_sudo("mkdir -p '%s'" % path)
        try:
            _mount(device_id, path)
        except:
            if format == "__auto__":
                print "Failed to mount device. format is set to __auto__ so will now format device and retry mount"
                _format_device(device_id)
                _mount(device_id, path)
            else:
                raise


def _mount(device_id, path):
    env.safe_sudo("mount '%s' '%s'" % (device_id, path))


def _format_device(device_id):
    env.safe_sudo("mkfs -t ext3 %s" % device_id)


def detach_volumes(vm_launcher, options):
    volumes = options.get("volumes", [])
    if not volumes:
        return

    boto_connection = vm_launcher.boto_connection()
    instance_id = run("curl --silent http://169.254.169.254/latest/meta-data/instance-id")
    for volume in volumes:
        volume_id = volume['id']
        path = volume.get("path")
        env.safe_sudo("umount '%s'" % path)
        _detach(boto_connection, instance_id, volume_id)


def make_snapshots(vm_launcher, options):
    volumes = options.get("volumes", [])
    for volume in volumes:
        path = volume.get("path")
        desc = volume.get("description", "Snapshot of path %s" % path)
        desc = eval_template(env, desc)
        # Allow volume to specify it should not be snapshotted, e.g. if
        # piggy backing on core teams snapshots for galaxyIndicies for instance.
        snapshot = volume.get("snapshot", True)
        if snapshot:
            _make_snapshot(vm_launcher, path, desc)


def _get_attached(conn, instance_id, device_id, valid_states=['attached']):
    vol_list = conn.get_all_volumes()
    fs_vol = None
    for vol in vol_list:
        if vol.attach_data.instance_id == instance_id and vol.attach_data.device == device_id:
            if vol.attach_data.status in valid_states:
                fs_vol = vol
                break
    return fs_vol


def _make_snapshot(vm_launcher, fs_path, desc):
    """ Create a snapshot of an existing volume that is currently attached to an
    instance, taking care of the unmounting and detaching. If you specify the
    optional argument (:galaxy), the script will pull the latest Galaxy code
    from bitbucket and perform an update before snapshotting. Else, the script
    will prompt for the file system path to be snapshoted.

    In order for this to work, an instance on EC2 needs to be running with a
    volume that wants to be snapshoted attached and mounted. The script will
    unmount the volume, create a snaphost and offer to reattach and mount the
    volume or create a new one from the freshly created snapshot.

    Except for potentially Galaxy, MAKE SURE there are no running processes
    using the volume and that no one is logged into the instance and sitting
    in the given directory.
    """
    instance_id = run("curl --silent http://169.254.169.254/latest/meta-data/instance-id")
    availability_zone = run("curl --silent http://169.254.169.254/latest/meta-data/placement/availability-zone")
    instance_region = availability_zone[:-1]  # Truncate zone letter to get region name
    # Find the device where the file system is mounted to
    # Find the EBS volume where the file system resides
    device_id = _find_mounted_device_id(fs_path)
    ec2_conn = vm_launcher.boto_connection()
    fs_vol = _get_attached(ec2_conn, instance_id, device_id)
    if fs_vol:
        env.safe_sudo("umount %s" % fs_path)
        _detach(ec2_conn, instance_id, fs_vol.id)
        snap_id = _create_snapshot(ec2_conn, fs_vol.id, desc)
        # TODO: Auto Update snaps?
        make_public = True
        if make_public:  # Make option
            ec2_conn.modify_snapshot_attribute(snap_id, attribute='createVolumePermission', operation='add', groups=['all'])
        reattach = True
        if reattach:
            _attach(ec2_conn, instance_id, fs_vol.id, device_id)
            env.safe_sudo("mount %s %s" % (device_id, fs_path))
        delete_old_volume = False
        if delete_old_volume:
            _delete_volume(ec2_conn, fs_vol.id)
        print "----- Done snapshoting volume '%s' for file system '%s' -----" % (fs_vol.id, fs_path)
    else:
        print "ERROR: Failed to find require file system, is boto installed? Is it not actually mounted?"


def _find_mounted_device_id(path):
    # Adding dollar sign to grep to distinguish between /mnt/galaxy and /mnt/galaxyIndices
    device_id = env.safe_sudo("df | grep '%s$' | awk '{print $1}'" % path)
    return device_id


def _attach(ec2_conn, instance_id, volume_id, device):
    """
    Attach EBS volume to the given device (using boto).
    Try it for some time.
    """
    try:
        print "Attaching volume '%s' to instance '%s' as device '%s'" % (volume_id, instance_id, device)
        volumestatus = ec2_conn.attach_volume(volume_id, instance_id, device)
    except EC2ResponseError, e:
        print "Attaching volume '%s' to instance '%s' as device '%s' failed. Exception: %s" % (volume_id, instance_id, device, e)
        return False

    for counter in range(30):
        print "Attach attempt %s, volume status: %s" % (counter, volumestatus)
        if volumestatus == 'attached':
            print "Volume '%s' attached to instance '%s' as device '%s'" % (volume_id, instance_id, device)
            break
        if counter == 29:
            print "Volume '%s' FAILED to attach to instance '%s' as device '%s'. Aborting." % (volume_id, instance_id, device)
            return False
        volumes = ec2_conn.get_all_volumes([volume_id])
        volumestatus = volumes[0].attachment_state()
        sleep(3)
    return True


def _detach(ec2_conn, instance_id, volume_id):
    """
    Detach EBS volume from the given instance (using boto).
    Try it for some time.
    """
    try:
        volumestatus = ec2_conn.detach_volume( volume_id, instance_id, force=True )
    except EC2ResponseError, ( e ):
        print "Detaching volume '%s' from instance '%s' failed. Exception: %s" % ( volume_id, instance_id, e )
        return False

    for counter in range( 30 ):
        print "Volume '%s' status '%s'" % ( volume_id, volumestatus )
        if volumestatus == 'available':
            print "Volume '%s' successfully detached from instance '%s'." % ( volume_id, instance_id )
            break
        if counter == 29:
            print "Volume '%s' FAILED to detach to instance '%s'." % ( volume_id, instance_id )
        sleep(3)
        volumes = ec2_conn.get_all_volumes( [volume_id] )
        volumestatus = volumes[0].status


def _delete_volume(ec2_conn, vol_id):
    try:
        ec2_conn.delete_volume(vol_id)
        print "Deleted volume '%s'" % vol_id
    except EC2ResponseError, e:
        print "ERROR deleting volume '%s': %s" % (vol_id, e)


def _create_snapshot(ec2_conn, volume_id, description=None):
    """
    Create a snapshot of the EBS volume with the provided volume_id.
    Wait until the snapshot process is complete (note that this may take quite a while)
    """
    snapshot = ec2_conn.create_snapshot(volume_id, description=description)
    if snapshot:
        while snapshot.status != 'completed':
            sleep(6)
            snapshot.update()
        print "Creation of snapshot for volume '%s' completed: '%s'" % (volume_id, snapshot)
        return snapshot.id
    else:
        print "Could not create snapshot from volume with ID '%s'" % volume_id
        return False

########NEW FILE########
__FILENAME__ = distribution
"""Configuration details for specific server types.

This module contains functions that help with initializing a Fabric environment
for standard server types.
"""
import os
import subprocess

from fabric.api import env

from cloudbio.fabutils import quiet
from cloudbio.fabutils import configure_runsudo
from cloudbio.custom import system

def _setup_distribution_environment(ignore_distcheck=False):
    """Setup distribution environment.

    In low-level terms, this method attempts to populate various values in the fabric
    env data structure for use other places in CloudBioLinux.
    """
    if "distribution" not in env:
        env.distribution = "__auto__"
    if "dist_name" not in env:
        env.dist_name = "__auto__"
    env.logger.info("Distribution %s" % env.distribution)

    if env.hosts == ["vagrant"]:
        _setup_vagrant_environment()
    elif env.hosts == ["localhost"]:
        _setup_local_environment()
    configure_runsudo(env)
    if env.distribution == "__auto__":
        env.distribution = _determine_distribution(env)
    if env.distribution == "ubuntu":
        ## TODO: Determine if dist_name check works with debian.
        if env.dist_name == "__auto__":
            env.dist_name = _ubuntu_dist_name(env)
        _setup_ubuntu()
    elif env.distribution == "centos":
        _setup_centos()
    elif env.distribution == "scientificlinux":
        _setup_scientificlinux()
    elif env.distribution == "debian":
        if env.dist_name == "__auto__":
            env.dist_name = _debian_dist_name(env)
        _setup_debian()
    elif env.distribution == "macosx":
        _setup_macosx(env)
        ignore_distcheck = True
    else:
        raise ValueError("Unexpected distribution %s" % env.distribution)
    if not ignore_distcheck:
        _validate_target_distribution(env.distribution, env.get('dist_name', None))
    _cloudman_compatibility(env)
    _setup_nixpkgs()
    _setup_fullpaths(env)
    # allow us to check for packages only available on 64bit machines
    machine = env.safe_run_output("uname -m")
    env.is_64bit = machine.find("_64") > 0


def _setup_fullpaths(env):
    home_dir = env.safe_run_output("echo $HOME")
    for attr in ["data_files", "galaxy_home", "local_install"]:
        if hasattr(env, attr):
            x = getattr(env, attr)
            if x.startswith("~"):
                x = x.replace("~", home_dir)
                setattr(env, attr, x)


def _cloudman_compatibility(env):
    """Environmental variable naming for compatibility with CloudMan.
    """
    env.install_dir = env.system_install


def _validate_target_distribution(dist, dist_name=None):
    """Check target matches environment setting (for sanity)

    Throws exception on error
    """
    env.logger.debug("Checking target distribution " + env.distribution)
    if dist in ["debian", "ubuntu"]:
        tag = env.safe_run_output("cat /proc/version")
        if tag.lower().find(dist) == -1:
           # hmmm, test issue file
            tag2 = env.safe_run_output("cat /etc/issue")
            if tag2.lower().find(dist) == -1:
                raise ValueError("Distribution does not match machine; are you using correct fabconfig for " + dist)
        if env.edition.short_name in ["minimal"]:
            # "minimal editions don't actually change any of the apt
            # source except adding biolinux, so won't cause this
            # problem and don't need to match dist_name"
            return
        if not dist_name:
            raise ValueError("Must specify a dist_name property when working with distribution %s" % dist)
        # Does this new method work with CentOS, do we need this.
        actual_dist_name = _ubuntu_dist_name(env)
        if actual_dist_name != dist_name:
            raise ValueError("Distribution does not match machine; are you using correct fabconfig for " + dist)
    else:
        env.logger.debug("Unknown target distro")


def _setup_ubuntu():
    env.logger.info("Ubuntu setup")
    shared_sources = _setup_deb_general()
    # package information. This is ubuntu/debian based and could be generalized.
    sources = [
      "deb http://us.archive.ubuntu.com/ubuntu/ %s universe",  # unsupported repos
      "deb http://us.archive.ubuntu.com/ubuntu/ %s multiverse",
      "deb http://us.archive.ubuntu.com/ubuntu/ %s-updates universe",
      "deb http://us.archive.ubuntu.com/ubuntu/ %s-updates multiverse",
      "deb http://archive.canonical.com/ubuntu %s partner",  # partner repositories
      "deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen",  # mongodb
      "deb http://cran.fhcrc.org/bin/linux/ubuntu %s/",  # lastest R versions
      "deb http://archive.cloudera.com/debian maverick-cdh3 contrib",  # Hadoop
      "deb http://archive.canonical.com/ubuntu %s partner",  # sun-java
      "deb http://ppa.launchpad.net/freenx-team/ppa/ubuntu precise main",  # Free-NX
      "deb http://ppa.launchpad.net/nebc/bio-linux/ubuntu precise main",  # Free-NX
      "deb [arch=amd64 trusted=yes] http://research.cs.wisc.edu/htcondor/debian/stable/ squeeze contrib"  # HTCondor
    ] + shared_sources
    env.std_sources = _add_source_versions(env.dist_name, sources)


def _setup_debian():
    env.logger.info("Debian setup")
    unstable_remap = {"sid": "squeeze"}
    shared_sources = _setup_deb_general()
    sources = [
        "deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen",  # mongodb
        "deb http://cran.fhcrc.org/bin/linux/debian %s-cran/",  # lastest R versions
        "deb http://archive.cloudera.com/debian lenny-cdh3 contrib"  # Hadoop
        ] + shared_sources
    # fill in %s
    dist_name = unstable_remap.get(env.dist_name, env.dist_name)
    env.std_sources = _add_source_versions(dist_name, sources)


def _setup_deb_general():
    """Shared settings for different debian based/derived distributions.
    """
    env.logger.debug("Debian-shared setup")
    env.sources_file = "/etc/apt/sources.list.d/cloudbiolinux.list"
    env.global_sources_file = "/etc/apt/sources.list"
    env.apt_preferences_file = "/etc/apt/preferences"
    if not hasattr(env, "python_version_ext"):
        env.python_version_ext = ""
    if not hasattr(env, "ruby_version_ext"):
        env.ruby_version_ext = "1.9.1"
    if not env.has_key("java_home"):
        # Try to determine java location from update-alternatives
        java_home = "/usr/lib/jvm/java-7-openjdk-amd64"
        with quiet():
            java_info = env.safe_run_output("update-alternatives --display java")
        for line in java_info.split("\n"):
            if line.strip().startswith("link currently points to"):
                java_home = line.split()[-1].strip()
                java_home = java_home.replace("/jre/bin/java", "")
        env.java_home = java_home
    shared_sources = [
        "deb http://nebc.nerc.ac.uk/bio-linux/ unstable bio-linux",  # Bio-Linux
        "deb http://download.virtualbox.org/virtualbox/debian %s contrib",  # virtualbox
    ]
    return shared_sources


def _setup_centos():
    env.logger.info("CentOS setup")
    if not hasattr(env, "python_version_ext"):
        # use installed anaconda version instead of package 2.6
        #env.python_version_ext = "2.6"
        env.python_version_ext = ""
    #env.pip_cmd = "pip-python"
    if not hasattr(env, "ruby_version_ext"):
        env.ruby_version_ext = ""
    if not env.has_key("java_home"):
        env.java_home = "/etc/alternatives/java_sdk"


def _setup_scientificlinux():
    env.logger.info("ScientificLinux setup")
    if not hasattr(env, "python_version_ext"):
        env.python_version_ext = ""
    env.pip_cmd = "pip-python"
    if not env.has_key("java_home"):
        env.java_home = "/etc/alternatives/java_sdk"

def _setup_macosx(env):
    # XXX Only framework in place; needs testing
    env.logger.info("MacOSX setup")
    # XXX Ensure XCode is installed and provide useful directions if not
    system.install_homebrew(env)
    # XXX find java correctly
    env.java_home = ""

def _setup_nixpkgs():
    # for now, Nix packages are only supported in Debian - it can
    # easily be done for others - just get Nix installed from the .rpm
    nixpkgs = False
    if env.has_key("nixpkgs"):
        if env.distribution in ["debian", "ubuntu"]:
            if env.nixpkgs == "True":
                nixpkgs = True
            else:
                nixpkgs = False
        else:
            env.logger.warn("NixPkgs are currently not supported for " + env.distribution)
    if nixpkgs:
        env.logger.info("NixPkgs: supported")
    else:
        env.logger.debug("NixPkgs: Ignored")
    env.nixpkgs = nixpkgs


def _setup_local_environment():
    """Setup a localhost environment based on system variables.
    """
    env.logger.info("Get local environment")
    if not env.has_key("user"):
        env.user = os.environ["USER"]


def _setup_vagrant_environment():
    """Use vagrant commands to get connection information.
    https://gist.github.com/1d4f7c3e98efdf860b7e
    """
    env.logger.info("Get vagrant environment")
    raw_ssh_config = subprocess.Popen(["vagrant", "ssh-config"],
                                      stdout=subprocess.PIPE).communicate()[0]
    env.logger.info(raw_ssh_config)
    ssh_config = dict([l.strip().split() for l in raw_ssh_config.split("\n") if l])
    env.user = ssh_config["User"]
    env.hosts = [ssh_config["HostName"]]
    env.port = ssh_config["Port"]
    env.host_string = "%s@%s:%s" % (env.user, env.hosts[0], env.port)
    env.key_filename = ssh_config["IdentityFile"].replace('"', '')
    env.logger.debug("ssh %s" % env.host_string)


def _add_source_versions(version, sources):
    """Patch package source strings for version, e.g. Debian 'stable'
    """
    name = version
    env.logger.debug("Source=%s" % name)
    final = []
    for s in sources:
        if s.find("%s") > 0:
            s = s % name
        final.append(s)
    return final


def _ubuntu_dist_name(env):
    """
    Determine Ubuntu dist name (e.g. precise or quantal).
    """
    return env.safe_run_output("cat /etc/*release | grep DISTRIB_CODENAME | cut -f 2 -d =")


def _debian_dist_name(env):
    """
    Determine Debian dist name (e.g. squeeze).
    """
    return env.safe_run_output("lsb_release -a | grep Codename | cut -f 2")


def _determine_distribution(env):
    """
    Attempt to automatically determine the distribution of the target machine.

    Currently works for Ubuntu, CentOS, Debian, Scientific Linux and Mac OS X.
    """
    with quiet():
        output = env.safe_run_output("cat /etc/*release").lower()
    if output.find("distrib_id=ubuntu") >= 0:
        return "ubuntu"
    elif output.find("centos release") >= 0:
        return "centos"
    elif output.find("red hat enterprise linux server release") >= 0:
        return "centos"
    elif output.find("fedora release") >= 0:
        return "centos"
    elif output.find("scientific linux release") >= 0:
        return "scientificlinux"
    elif env.safe_exists("/etc/debian_version"):
        return "debian"
    # check for file used by Python's platform.mac_ver
    elif env.safe_exists("/System/Library/CoreServices/SystemVersion.plist"):
        return "macosx"
    else:
        raise Exception("Attempt to automatically determine Linux distribution of target machine failed, please manually specify distribution in fabricrc.txt")

########NEW FILE########
__FILENAME__ = base
"""Base editions supplying CloudBioLinux functionality which can be customized.

These are a set of testing and supported edition classes.
"""
from fabric.api import *

from cloudbio.cloudman import _configure_cloudman
from cloudbio.cloudbiolinux import _freenx_scripts

class Edition:
    """Base class. Every edition derives from this
    """
    def __init__(self, env):
        self.name = "BioLinux base Edition"
        self.short_name = "biolinux"
        self.version = env.version
        self.env = env
        self.check_distribution()

    def check_distribution(self):
        """Ensure the distribution matches an expected type for this edition.

        Base supports multiple distributions.
        """
        pass

    def check_packages_source(self):
        """Override for check package definition file before updating
        """
        pass

    def rewrite_apt_sources_list(self, sources):
        """Allows editions to modify the sources list
        """
        return sources

    def rewrite_apt_preferences(self, preferences):
        """Allows editions to modify the apt preferences policy file
        """
        return preferences

    def rewrite_apt_automation(self, package_info):
        """Allows editions to modify the apt automation list
        """
        return package_info

    def rewrite_apt_keys(self, standalone, keyserver):
        """Allows editions to modify key list"""
        return standalone, keyserver

    def apt_upgrade_system(self, env=None):
        """Upgrade system through apt - so this behaviour can be overridden
        """
        sudo_cmd = env.safe_sudo if env else sudo
        sudo_cmd("apt-get -y --force-yes upgrade")

    def post_install(self, pkg_install=None):
        """Post installation hook"""
        pass

    def rewrite_config_items(self, name, items):
        """Generic hook to rewrite a list of configured items.

        Can define custom dispatches based on name: packages, custom,
        python, ruby, perl
        """
        return items

class CloudBioLinux(Edition):
    """Specific customizations for CloudBioLinux builds.
    """
    def __init__(self, env):
        Edition.__init__(self,env)
        self.name = "CloudBioLinux Edition"
        self.short_name = "cloudbiolinux"

    def rewrite_config_items(self, name, items):
        """Generic hook to rewrite a list of configured items.

        Can define custom dispatches based on name: packages, custom,
        python, ruby, perl
        """
        to_add = ["galaxy", "galaxy_tools", "cloudman"]
        for x in to_add:
            if x not in items:
                items.append(x)
        return items

    def post_install(self, pkg_install=None):
        """Add scripts for starting FreeNX and CloudMan.
        """
        _freenx_scripts(self.env)
        if pkg_install is not None and 'cloudman' in pkg_install:
            _configure_cloudman(self.env)

class BioNode(Edition):
    """BioNode specialization of BioLinux
    """
    def __init__(self, env):
        Edition.__init__(self,env)
        self.name = "BioNode Edition"
        self.short_name = "bionode"

    def check_distribution(self):
        # if self.env.distribution not in ["debian"]:
        #    raise ValueError("Distribution is not pure Debian")
        pass

    def check_packages_source(self):
        # Bionode always removes sources, just to be sure
        self.env.logger.debug("Clearing %s" % self.env.sources_file)
        sudo("cat /dev/null > %s" % self.env.sources_file)

    def rewrite_apt_sources_list(self, sources):
        """BioNode will pull packages from Debian 'testing', if not
           available in stable. Also BioLinux packages are included.
        """
        self.env.logger.debug("BioNode.rewrite_apt_sources_list!")
        new_sources = []
        if self.env.distribution in ["debian"]:
          # See if the repository is defined in env
          if not env.get('debian_repository'):
              main_repository = 'http://ftp.us.debian.org/debian/'
          else:
              main_repository = env.debian_repository
          # The two basic repositories
          new_sources += ["deb {repo} {dist} main contrib non-free".format(repo=main_repository,
                                                                          dist=env.dist_name),
                         "deb {repo} {dist}-updates main contrib non-free".format(
                             repo=main_repository, dist=env.dist_name),
                         "deb {repo} testing main contrib non-free".format(
                             repo=main_repository)
                        ]
        new_sources = new_sources + [ "deb http://nebc.nerc.ac.uk/bio-linux/ unstable bio-linux" ]

        return new_sources

    def rewrite_apt_preferences(self, preferences):
        """Allows editions to modify apt preferences (load order of
        packages, i.e. the package dowload policy. Here we use
        'stable' packages, unless only available in 'testing'.
        """
        preferences = """Package: *
Package: *
Pin: release n=natty
Pin-Priority: 900

Package: *
Pin: release a=stable
Pin-Priority: 700

Package: *
Pin: release a=testing
Pin-Priority: 650

Package: *
Pin: release a=bio-linux
Pin-Priority: 400
"""
        return preferences.split('\n')

    def rewrite_apt_automation(self, package_info):
        return []

    def rewrite_apt_keys(self, standalone, keyserver):
        return [], []

    def rewrite_config_items(self, name, items):
        # BioLinux add keyring
        if name == 'minimal':
            return items + [ 'bio-linux-keyring' ]
        return items

class Minimal(Edition):
    """Minimal specialization of BioLinux
    """
    def __init__(self, env):
        Edition.__init__(self, env)
        self.name = "Minimal Edition"
        self.short_name = "minimal"

    def rewrite_apt_sources_list(self, sources):
        """Allows editions to modify the sources list. Minimal, by
           default, assumes system has stable packages configured
           and adds only the biolinux repository.
        """
        return ["deb http://nebc.nerc.ac.uk/bio-linux/ unstable bio-linux"]

    def rewrite_apt_automation(self, package_info):
        return []

    def rewrite_apt_keys(self, standalone, keyserver):
        return [], []

    def apt_upgrade_system(self, env=None):
        """Do nothing"""
        env.logger.debug("Skipping forced system upgrade")

    def rewrite_config_items(self, name, items):
        """Generic hook to rewrite a list of configured items.

        Can define custom dispatches based on name: packages, custom,
        python, ruby, perl
        """
        return items

########NEW FILE########
__FILENAME__ = fabutils
"""Utilities to generalize usage of fabric for local and remote builds.

Handles:
  - Providing a local equivalent of standard functions that avoid
    the need to ssh to a local machine.
    Adds generalized targets to the global `env` object which cleanly
    handle local and remote execution:
    - safe_run: Run a command
    - safe_run_output: Run a command, capturing the output
    - safe_sudo: Run a command as sudo user
    - safe_exists: Check for existence of a file.
    - safe_sed: Run sed command.
"""
import hashlib
import os
import re
import shutil

from fabric.api import env, run, sudo, local, settings, hide, put
from fabric.contrib.files import exists, sed, contains, append, comment

SUDO_ENV_KEEPS = []  # Environment variables passed through to sudo environment when using local sudo.
SUDO_ENV_KEEPS += ["http_proxy", "https_proxy"]  # Required for local sudo to work behind a proxy.


# ## Local non-ssh access
def local_exists(path, use_sudo=False):
    func = env.safe_sudo if use_sudo else env.safe_run
    cmd = 'test -e "$(echo %s)"' % path
    cmd_symbolic = 'test -h "$(echo %s)"' % path
    with settings(hide('everything'), warn_only=True):
        env.lcwd = env.cwd
        return (not func(cmd).failed) or (not func(cmd_symbolic).failed)

def run_local(use_sudo=False, capture=False):
    def _run(command, *args, **kwags):
        if use_sudo:
            sudo_env = " ".join(["%s=$%s" % (keep, keep) for keep in SUDO_ENV_KEEPS])
            sudo_to = ""
            if "user" in kwags:
                sudo_to = "su - %s" % kwags["user"]
            sudo_prefix = "sudo %s %s bash -c " % (sudo_env, sudo_to)

            command = sudo_prefix + '"%s"' % command.replace('"', '\\"')
        env.lcwd = env.cwd
        return local(command, capture=capture)
    return _run

def local_put(orig_file, new_file):
    shutil.copyfile(orig_file, new_file)

def local_sed(filename, before, after, limit='', use_sudo=False, backup='.bak',
              flags='', shell=False):
    """ Run a search-and-replace on ``filename`` with given regex patterns.

    From main fabric contrib, modified to handle local.
    """
    func = env.safe_sudo if use_sudo else env.safe_run
    # Characters to be escaped in both
    for char in "/'":
        before = before.replace(char, r'\%s' % char)
        after = after.replace(char, r'\%s' % char)
    # Characters to be escaped in replacement only (they're useful in regexen
    # in the 'before' part)
    for char in "()":
        after = after.replace(char, r'\%s' % char)
    if limit:
        limit = r'/%s/ ' % limit
    context = {
        'script': r"'%ss/%s/%s/%sg'" % (limit, before, after, flags),
        'filename': '"$(echo %s)"' % filename,
        'backup': backup
    }
    # Test the OS because of differences between sed versions

    with hide('running', 'stdout'):
        platform = env.safe_run("uname")
    if platform in ('NetBSD', 'OpenBSD', 'QNX'):
        # Attempt to protect against failures/collisions
        hasher = hashlib.sha1()
        hasher.update(env.host_string)
        hasher.update(filename)
        context['tmp'] = "/tmp/%s" % hasher.hexdigest()
        # Use temp file to work around lack of -i
        expr = r"""cp -p %(filename)s %(tmp)s \
&& sed -r -e %(script)s %(filename)s > %(tmp)s \
&& cp -p %(filename)s %(filename)s%(backup)s \
&& mv %(tmp)s %(filename)s"""
    else:
        context['extended_regex'] = '-E' if platform == 'Darwin' else '-r'
        expr = r"sed -i%(backup)s %(extended_regex)s -e %(script)s %(filename)s"
    command = expr % context
    return func(command, shell=shell)

def local_comment(filename, regex, use_sudo=False, char='#', backup='.bak', shell=False):
    carot, dollar = '', ''
    if regex.startswith('^'):
        carot = '^'
        regex = regex[1:]
    if regex.endswith('$'):
        dollar = '$'
        regex = regex[:-1]
    regex = "%s(%s)%s" % (carot, regex, dollar)
    return local_sed(
        filename,
        before=regex,
        after=r'%s\1' % char,
        use_sudo=use_sudo,
        backup=backup,
        shell=shell
    )

def _escape_for_regex(text):
    """Escape ``text`` to allow literal matching using egrep"""
    regex = re.escape(text)
    # Seems like double escaping is needed for \
    regex = regex.replace('\\\\', '\\\\\\')
    # Triple-escaping seems to be required for $ signs
    regex = regex.replace(r'\$', r'\\\$')
    # Whereas single quotes should not be escaped
    regex = regex.replace(r"\'", "'")
    return regex

def _expand_path(path):
    return '"$(echo %s)"' % path

def local_contains(filename, text, exact=False, use_sudo=False, escape=True,
    shell=False):
    func = use_sudo and env.safe_sudo or env.safe_run
    if escape:
        text = _escape_for_regex(text)
        if exact:
            text = "^%s$" % text
    with settings(hide('everything'), warn_only=True):
        egrep_cmd = 'egrep "%s" %s' % (text, _expand_path(filename))
        return func(egrep_cmd, shell=shell).succeeded

def local_append(filename, text, use_sudo=False, partial=False, escape=True, shell=False):
    func = use_sudo and env.safe_sudo or env.safe_run
    # Normalize non-list input to be a list
    if isinstance(text, basestring):
        text = [text]
    for line in text:
        regex = '^' + _escape_for_regex(line)  + ('' if partial else '$')
        if (env.safe_exists(filename, use_sudo=use_sudo) and line
            and env.safe_contains(filename, regex, use_sudo=use_sudo, escape=False,
                                  shell=shell)):
            continue
        line = line.replace("'", r"'\\''") if escape else line
        func("echo '%s' >> %s" % (line, _expand_path(filename)))

def run_output(*args, **kwargs):
    if not 'shell' in kwargs:
        kwargs['shell'] = False
    return run(*args, **kwargs)

def configure_runsudo(env):
    """Setup env variable with safe_sudo and safe_run,
    supporting non-privileged users and local execution.
    """
    env.is_local = env.hosts == ["localhost"]
    if env.is_local:
        env.safe_put = local_put
        env.safe_sed = local_sed
        env.safe_comment = local_comment
        env.safe_contains = local_contains
        env.safe_append = local_append
        env.safe_exists = local_exists
        env.safe_run = run_local()
        env.safe_run_output = run_local(capture=True)
    else:
        env.safe_put = put
        env.safe_sed = sed
        env.safe_comment = comment
        env.safe_contains = contains
        env.safe_append = append
        env.safe_exists = exists
        env.safe_run = run
        env.safe_run_output = run_output
    if isinstance(getattr(env, "use_sudo", "true"), basestring):
        if getattr(env, "use_sudo", "true").lower() in ["true", "yes"]:
            env.use_sudo = True
            if env.is_local:
                env.safe_sudo = run_local(True)
            else:
                env.safe_sudo = sudo
        else:
            env.use_sudo = False
            if env.is_local:
                env.safe_sudo = run_local()
            else:
                env.safe_sudo = run

def find_cmd(env, cmd, args):
    """Retrieve location of a command, checking in installation directory.
    """
    local_cmd = os.path.join(env.system_install, "bin", cmd)
    for cmd in [local_cmd, cmd]:
        with quiet():
            test_version = env.safe_run("%s %s" % (cmd, args))
        if test_version.succeeded:
            return cmd
    return None

try:
    from fabric.api import quiet
except ImportError:
    def quiet():
        return settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True)

try:
    from fabric.api import warn_only
except ImportError:
    def warn_only():
        return settings(warn_only=True)

########NEW FILE########
__FILENAME__ = config
"""
Handle alternative configuration file locations for flavor customizations.
"""
import os
import collections

def _find_fname(env, fname):
    for dirname in [env.get("flavor_dir", None), env.config_dir]:
        if dirname:
            full_path = os.path.join(dirname, fname)
            if os.path.exists(full_path):
                return full_path
    return None

def get_config_file(env, fname):
    """
    Retrieve YAML configuration file from the default config directory or flavor directory.

    This combines all options for getting distribution or flavor specific customizations.
    """
    base, ext = os.path.splitext(fname)
    distribution_fname = "{0}-{1}{2}".format(base, env.get("distribution", "notspecified"), ext)
    Config = collections.namedtuple("Config", "base dist")
    out = Config(base=_find_fname(env, fname), dist=_find_fname(env, distribution_fname))
    env.logger.debug("Using config file {0}".format(out.base))
    return out

########NEW FILE########
__FILENAME__ = applications
"""
This file is largely derived from a similar file in mi-deployment written Dr.
Enis Afgan.

https://bitbucket.org/afgane/mi-deployment/src/8cba95baf98f/tools_fabfile.py

Long term it will be best to install these packages for Galaxy via the Tool
Shed, however many of these tools are not yet in the tool shed and the tool
shed installation is not currently available via the Galaxy API. Until such a
time as that is available, Galaxy dependencies may be installed via these
functions.

I have taken a first crack at harmonizing this with the rest of CloudBioLinux.
Wasn't able to reuse fastx_toolkit, tophat, cufflinks.

"""
import os

from fabric.api import cd

from cloudbio.custom.shared import _make_tmp_dir, _if_not_installed, _set_default_config
from cloudbio.custom.shared import _get_install, _configure_make, _fetch_and_unpack, _get_bin_dir


@_if_not_installed(None)
def install_fastx_toolkit(env):
    version = env.tool_version
    gtext_version = "0.6.1"
    url_base = "http://hannonlab.cshl.edu/fastx_toolkit/"
    fastx_url = "%sfastx_toolkit-%s.tar.bz2" % (url_base, version)
    gtext_url = "%slibgtextutils-%s.tar.bz2" % (url_base, gtext_version)
    pkg_name = 'fastx_toolkit'
    install_dir = os.path.join(env.galaxy_tools_dir, pkg_name, version)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s" % gtext_url)
            env.safe_run("tar -xjvpf %s" % (os.path.split(gtext_url)[-1]))
            install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
            with cd("libgtextutils-%s" % gtext_version):
                env.safe_run("./configure --prefix=%s" % (install_dir))
                env.safe_run("make")
                install_cmd("make install")
            env.safe_run("wget %s" % fastx_url)
            env.safe_run("tar -xjvpf %s" % os.path.split(fastx_url)[-1])
            with cd("fastx_toolkit-%s" % version):
                env.safe_run("export PKG_CONFIG_PATH=%s/lib/pkgconfig; ./configure --prefix=%s" % (install_dir, install_dir))
                env.safe_run("make")
                install_cmd("make install")


## TODO: Rework to use more of custom enhancements
@_if_not_installed("maq")
def install_maq(env):
    version = env["tool_version"]
    url = "http://downloads.sourceforge.net/project/maq/maq/%s/maq-%s.tar.bz2" \
            % (version, version)
    _get_install(url, env, _configure_make)


@_if_not_installed("macs14")
def install_macs(env):
    from cloudbio.custom.bio_nextgen  import install_macs as cbl_install_macs
    install_dir = env.system_install
    cbl_install_macs(env)
    env.safe_sudo("echo 'PATH=%s/bin:$PATH' > %s/env.sh" % (install_dir, install_dir))
    env.safe_sudo("echo 'PYTHONPATH=%s/lib/python%s/site-packages:$PYTHONPATH' >> %s/env.sh" % (env.python_version, install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("megablast")
def install_megablast(env):
    version = env.tool_version
    url = 'ftp://ftp.ncbi.nlm.nih.gov/blast/executables/release/%s/blast-%s-x64-linux.tar.gz' % (version, version)
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s" % url)
            env.safe_run("tar -xvzf %s" % os.path.split(url)[-1])
            with cd('blast-%s/bin' % version):
                    install_cmd("mv * %s" % install_dir)


@_if_not_installed("blastn")
def install_blast(env):
    version = env.tool_version
    url = 'ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/%s/ncbi-blast-%s-x64-linux.tar.gz' % (version[:-1], version)
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s" % url)
            env.safe_run("tar -xvzf %s" % os.path.split(url)[-1])
            with cd('ncbi-blast-%s/bin' % version):
                bin_dir = _get_bin_dir(env)
                install_cmd("mv * '%s'" % bin_dir)


@_if_not_installed("sputnik")
def install_sputnik(env):
    version = env.tool_version
    url = 'http://bitbucket.org/natefoo/sputnik-mononucleotide/downloads/sputnik_%s_linux2.6_x86_64' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget -O sputnik %s" % url)
            install_cmd("mv sputnik %s" % install_dir)


@_if_not_installed("taxonomy2tree")
def install_taxonomy(env):
    version = env.tool_version
    url = 'http://bitbucket.org/natefoo/taxonomy/downloads/taxonomy_%s_linux2.6_x86_64.tar.gz' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s" % url)
            env.safe_run("tar -xvzf %s" % os.path.split(url)[-1])
            with cd(os.path.split(url)[-1].split('.tar.gz')[0]):
                install_cmd("mv * %s" % install_dir)


@_if_not_installed("add_scores")
def install_add_scores(env):
    version = env.tool_version
    url = 'http://bitbucket.org/natefoo/add_scores/downloads/add_scores_%s_linux2.6_x86_64' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget -O add_scores %s" % url)
            install_cmd("mv add_scores %s" % install_dir)


@_if_not_installed("HYPHY")
def install_hyphy(env):
    version = env.tool_version
    url = 'http://www.datam0nk3y.org/svn/hyphy'
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("svn co -r %s %s src" % (version, url))
            env.safe_run("mkdir -p build/Source/Link")
            env.safe_run("mkdir build/Source/SQLite")
            env.safe_run("cp src/trunk/Core/*.{h,cp,cpp} build/Source")
            env.safe_run("cp src/trunk/HeadlessLink/*.{h,cpp} build/Source/SQLite")
            env.safe_run("cp src/trunk/NewerFunctionality/*.{h,cpp} build/Source/")
            env.safe_run("cp src/SQLite/trunk/*.{c,h} build/Source/SQLite/")
            env.safe_run("cp src/trunk/Scripts/*.sh build/")
            env.safe_run("cp src/trunk/Mains/main-unix.cpp build/Source/main-unix.cxx")
            env.safe_run("cp src/trunk/Mains/hyphyunixutils.cpp build/Source/hyphyunixutils.cpp")
            env.safe_run("cp -R src/trunk/{ChartAddIns,DatapanelAddIns,GeneticCodes,Help,SubstitutionClasses,SubstitutionModels,TemplateBatchFiles,TopologyInference,TreeAddIns,UserAddins} build")
            env.safe_run("rm build/Source/preferences.cpp")
            with cd("build"):
                env.safe_run("bash build.sh SP")
            install_cmd("mv build/* %s" % install_dir)
    _update_default(env, install_dir)


@_if_not_installed(None)
def install_gatk(env):
    version = env.tool_version
    url = 'ftp://ftp.broadinstitute.org/pub/gsa/GenomeAnalysisTK/GenomeAnalysisTK-%s.tar.bz2' % version
    pkg_name = 'gatk'
    install_dir = os.path.join(env.galaxy_tools_dir, pkg_name, version)
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
        install_cmd("mkdir -p %s/bin" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget -O gatk.tar.bz2 %s" % url)
            env.safe_run("tar -xjf gatk.tar.bz2")
            install_cmd("cp GenomeAnalysisTK-%s/*.jar %s/bin" % (version, install_dir))
    # Create shell script to wrap jar
    env.safe_sudo("echo '#!/bin/sh' > %s/bin/gatk" % (install_dir))
    env.safe_sudo("echo 'java -jar %s/bin/GenomeAnalysisTK.jar $@' >> %s/bin/gatk" % (install_dir, install_dir))
    env.safe_sudo("chmod +x %s/bin/gatk" % install_dir)
    # env file
    env.safe_sudo("echo 'PATH=%s/bin:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)
    # Link jar to Galaxy's jar dir
    jar_dir = os.path.join(env.galaxy_jars_dir, pkg_name)
    if not env.safe_exists(jar_dir):
        install_cmd("mkdir -p %s" % jar_dir)
    tool_dir = os.path.join(env.galaxy_tools_dir, pkg_name, 'default', 'bin')
    install_cmd('ln --force --symbolic %s/*.jar %s/.' % (tool_dir, jar_dir))
    install_cmd('chown --recursive %s:%s %s' % (env.galaxy_user, env.galaxy_user, jar_dir))


@_if_not_installed("srma.jar")
def install_srma(env):
    version = env.tool_version
    mirror_info = "?use_mirror=voxel"
    url = 'http://downloads.sourceforge.net/project/srma/srma/%s/srma-%s.jar' \
            % (version[:3], version)
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s%s -O %s" % (url, mirror_info, os.path.split(url)[-1]))
            install_cmd("mv srma-%s.jar %s" % (version, install_dir))
            install_cmd("ln -f -s srma-%s.jar %s/srma.jar" % (version, install_dir))
    env.safe_sudo("touch %s/env.sh" % install_dir)
    _update_default(env, install_dir)


@_if_not_installed("BEAM2")
def install_beam(env):
    url = 'http://www.stat.psu.edu/~yuzhang/software/beam2.tar'
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("tar xf %s" % (os.path.split(url)[-1]))
            install_cmd("mv BEAM2 %s" % install_dir)
    env.safe_sudo("echo 'PATH=%s:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("pass2")
def install_pass(env):
    url = 'http://www.stat.psu.edu/~yuzhang/software/pass2.tar'
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("tar xf %s" % (os.path.split(url)[-1]))
            install_cmd("mv pass2 %s" % install_dir)
    env.safe_sudo("echo 'PATH=%s:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("lps_tool")
def install_lps_tool(env):
    version = env.tool_version
    url = 'http://www.bx.psu.edu/miller_lab/dist/lps_tool.%s.tar.gz' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("tar zxf %s" % (os.path.split(url)[-1]))
            install_cmd("./lps_tool.%s/MCRInstaller.bin -P bean421.installLocation=\"%s/MCR\" -silent" % (version, install_dir))
            install_cmd("mv lps_tool.%s/lps_tool %s" % (version, install_dir))
    env.safe_sudo("echo 'PATH=%s:$PATH' > %s/env.sh" % (install_dir, install_dir))
    env.safe_sudo("echo 'MCRROOT=%s/MCR/v711; export MCRROOT' >> %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("plink")
def install_plink(env):
    version = env.tool_version
    url = 'http://pngu.mgh.harvard.edu/~purcell/plink/dist/plink-%s-x86_64.zip' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("unzip %s" % (os.path.split(url)[-1]))
            install_cmd("mv plink-%s-x86_64/plink %s" % (version, install_dir))
    env.safe_sudo("echo 'PATH=%s:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed(None)
def install_fbat(env):
    version = env.tool_version
    url = 'http://www.biostat.harvard.edu/~fbat/software/fbat%s_linux64.tar.gz' % version.replace('.', '')
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("tar zxf %s" % (os.path.split(url)[-1]))
            install_cmd("mv fbat %s" % install_dir)
    env.safe_sudo("echo 'PATH=%s:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("Haploview_beta.jar")
def install_haploview(env):
    url = 'http://www.broadinstitute.org/ftp/pub/mpg/haploview/Haploview_beta.jar'
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            install_cmd("mv %s %s" % (os.path.split(url)[-1], install_dir))
            install_cmd("ln -s %s %s/haploview.jar" % (os.path.split(url)[-1], install_dir))
    _update_default(env, install_dir)


@_if_not_installed("eigenstrat")
def install_eigenstrat(env):
    version = env.tool_version
    url = 'http://www.hsph.harvard.edu/faculty/alkes-price/files/EIG%s.tar.gz' % version
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s -O %s" % (url, os.path.split(url)[-1]))
            env.safe_run("tar zxf %s" % (os.path.split(url)[-1]))
            install_cmd("mv bin %s" % install_dir)
    env.safe_sudo("echo 'PATH=%s/bin:$PATH' > %s/env.sh" % (install_dir, install_dir))
    _update_default(env, install_dir)


@_if_not_installed("augustus")
def install_augustus(env):
    default_version = "2.7"
    version = env.get('tool_version', default_version)
    url = "http://bioinf.uni-greifswald.de/augustus/binaries/augustus.%s.tar.gz" % version
    install_dir = env.system_install
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            _fetch_and_unpack(url, need_dir=False)
            env.safe_sudo("mkdir -p '%s'" % install_dir)
            env.safe_sudo("mv augustus.%s/* '%s'" % (version, install_dir))


@_if_not_installed("SortSam.jar")
def install_picard(env):
    version = env.tool_version
    mirror_info = "?use_mirror=voxel"
    url = 'http://downloads.sourceforge.net/project/picard/picard-tools/%s/picard-tools-%s.zip' % (version, version)
    pkg_name = 'picard'
    install_dir = env.system_install
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with _make_tmp_dir() as work_dir:
        with cd(work_dir):
            env.safe_run("wget %s%s -O %s" % (url, mirror_info, os.path.split(url)[-1]))
            env.safe_run("unzip %s" % (os.path.split(url)[-1]))
            install_cmd("mv picard-tools-%s/*.jar %s" % (version, install_dir))
    _update_default(env, install_dir)
    # set up the jars directory
    jar_dir = os.path.join(env.galaxy_jars_dir, 'picard')
    if not env.safe_exists(jar_dir):
        install_cmd("mkdir -p %s" % jar_dir)
    tool_dir = os.path.join(env.galaxy_tools_dir, pkg_name, 'default')
    install_cmd('ln --force --symbolic %s/*.jar %s/.' % (tool_dir, jar_dir))
    install_cmd('chown --recursive %s:%s %s' % (env.galaxy_user, env.galaxy_user, jar_dir))


@_if_not_installed("fastqc")
def install_fastqc(env):
    """ This tool is installed in Galaxy's jars dir """
    version = env.tool_version
    url = 'http://www.bioinformatics.bbsrc.ac.uk/projects/fastqc/fastqc_v%s.zip' % version
    pkg_name = 'FastQC'
    install_dir = os.path.join(env.galaxy_jars_dir)
    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
    if not env.safe_exists(install_dir):
        install_cmd("mkdir -p %s" % install_dir)
    with cd(install_dir):
        install_cmd("wget %s -O %s" % (url, os.path.split(url)[-1]))
        install_cmd("unzip -u %s" % (os.path.split(url)[-1]))
        install_cmd("rm %s" % (os.path.split(url)[-1]))
        with cd(pkg_name):
            install_cmd('chmod 755 fastqc')
        install_cmd('chown --recursive %s:%s %s' % (env.galaxy_user, env.galaxy_user, pkg_name))


def _update_default(env, install_dir):
    env.safe_sudo("touch %s/env.sh" % install_dir)
    env.safe_sudo("chmod +x %s/env.sh" % install_dir)
    _set_default_config(env, install_dir)

#@if_tool_not_found()
#def install_emboss(env):
#    version = env.tool_version
#    url = 'ftp://emboss.open-bio.org/pub/EMBOSS/old/%s/EMBOSS-%s.tar.gz' % (version, version)
#    pkg_name = 'emboss'
#    install_dir = os.path.join(env.galaxy_tools_dir, pkg_name, version)
#    install_cmd = env.safe_sudo if env.use_sudo else env.safe_run
#    if not env.safe_exists(install_dir):
#        install_cmd("mkdir -p %s" % install_dir)
#    with _make_tmp_dir() as work_dir:
#        with cd(work_dir):
#            env.safe_run("wget %s" % url)
#            env.safe_run("tar -xvzf %s" % os.path.split(url)[-1])
#            with cd(os.path.split(url)[-1].split('.tar.gz')[0]):
#                env.safe_run("./configure --prefix=%s" % install_dir)
#                env.safe_run("make")
#                install_cmd("make install")
#    phylip_version = '3.6b'
#    url = 'ftp://emboss.open-bio.org/pub/EMBOSS/old/%s/PHYLIP-%s.tar.gz' % (version, phylip_version)
#    with _make_tmp_dir() as work_dir:
#        with cd(work_dir):
#            env.safe_run("wget %s" % url)
#            env.safe_run("tar -xvzf %s" % os.path.split(url)[-1])
#            with cd(os.path.split(url)[-1].split('.tar.gz')[0]):
#                env.safe_run("./configure --prefix=%s" % install_dir)
#                env.safe_run("make")
#                install_cmd("make install")


########NEW FILE########
__FILENAME__ = r
import os
import tempfile


from cloudbio.custom.shared import _make_tmp_dir
from fabric.api import sudo, put, cd

r_packages_template = """
r <- getOption("repos");
r["CRAN"] <- "http://watson.nci.nih.gov/cran_mirror";
options(repos=r);
install.packages( c( %s ), dependencies = TRUE);
source("http://bioconductor.org/biocLite.R");
biocLite( c( %s ) );
"""


def _install_r_packages(tools_conf):
    f = tempfile.NamedTemporaryFile()
    r_packages = tools_conf["r_packages"]
    bioconductor_packages = tools_conf["bioconductor_packages"]
    if not r_packages and not bioconductor_packages:
        return
    r_cmd = r_packages_template % (_concat_strings(r_packages), _concat_strings(bioconductor_packages))
    f.write(r_cmd)
    f.flush()
    with _make_tmp_dir() as work_dir:
        put(f.name, os.path.join(work_dir, 'install_packages.r'))
        with cd(work_dir):
            sudo("R --vanilla --slave < install_packages.r")
    f.close()


def _concat_strings(strings):
    if strings:
        return ", ".join(map(lambda x: '"%s"' % x, strings))
    else:
        return ""

########NEW FILE########
__FILENAME__ = tools
import os
from string import Template

import yaml

from cloudbio.custom.bio_general import *
from cloudbio.custom.bio_nextgen import *
from cloudbio.custom.bio_proteomics import *
from cloudbio.custom.shared import _set_default_config, _add_to_profiles
from cloudbio.galaxy.applications import *
from cloudbio.galaxy.r import _install_r_packages
from cloudbio.galaxy.utils import _chown_galaxy, _read_boolean

FAILED_INSTALL_MESSAGE = \
    "Failed to install application %s as a Galaxy application. This may be a transient problem (e.g. mirror for download is currently unavailable) or misconfiguration. The contents of the CloudBioLinux temporary working directory may need to be deleted."


def _install_tools(env, tools_conf=None):
    """
    Install tools needed for Galaxy along with tool configuration
    directories needed by Galaxy.
    """

    if not tools_conf:
        tools_conf = _load_tools_conf(env)

    if _read_boolean(env, "galaxy_install_dependencies", False):
       # Need to ensure the install dir exists and is owned by env.galaxy_user
        _setup_install_dir(env)
        _install_configured_applications(env, tools_conf)
        _chown_galaxy(env, env.galaxy_tools_dir)
        _chown_galaxy(env, env.galaxy_jars_dir)

    if _read_boolean(env, "galaxy_install_r_packages", False):
        _install_r_packages(tools_conf)


def _tools_conf_path(env):
    """
    Load path to galaxy_tools_conf file from env, allowing expansion of $__contrib_dir__.
    Default to $__contrib_dir__/flavor/cloudman/tools.yaml.
    """
    contrib_dir = os.path.join(env.config_dir, os.pardir, "contrib")
    default_tools_conf_path = os.path.join(contrib_dir, "flavor", "cloudman", "tools.yaml")
    tools_conf_path = env.get("galaxy_tools_conf", default_tools_conf_path)
    ## Allow expansion of __config_dir__ in galaxy_tools_conf property.
    return Template(tools_conf_path).safe_substitute({"__contrib_dir__": contrib_dir})


def _load_tools_conf(env):
    with open(_tools_conf_path(env)) as in_handle:
        full_data = yaml.load(in_handle)
    return full_data


def _setup_install_dir(env):
    """Sets up install dir and ensures its owned by Galaxy"""
    if not env.safe_exists(env.galaxy_tools_dir):
        env.safe_sudo("mkdir -p %s" % env.galaxy_tools_dir)
        _chown_galaxy(env, env.galaxy_tools_dir)
    # Create a general-purpose ``bin`` directory under the galaxy_tools_dir
    # and put it on the PATH so users can more easily add custom tools
    bin_dir = os.path.join(env.galaxy_tools_dir, 'bin')
    if not env.safe_exists(bin_dir):
        env.safe_sudo("mkdir -p %s" % bin_dir)
        _chown_galaxy(env, bin_dir)
        line = "export PATH={0}:$PATH".format(bin_dir)
        _add_to_profiles(line)
    if not env.safe_exists(env.galaxy_jars_dir):
        env.safe_sudo("mkdir -p %s" % env.galaxy_jars_dir)
        _chown_galaxy(env, env.galaxy_jars_dir)


def _install_configured_applications(env, tools_conf):
    """
    Install external tools defined by YAML or dictionary data structure.  Instead of
    installing in system_install (e.g. /usr), these custom tools will be installed as
    Galaxy dependency applications.
    """
    applications = tools_conf["applications"] or {}
    # Changing the default behavior here to install all tools and
    # just record exceptions as they occur, but wait until the end
    # raise an exception out of this block. Disable this behavior
    # by setting galaxay_tool_defer_errors to False.
    defer_errors = env.get("galaxy_tool_defer_errors", True)
    exceptions = {}
    for (name, tool_conf) in applications.iteritems():
        if not __check_conditional(tool_conf):
            continue

        try:
            _install_application(name, tool_conf)
        except BaseException, e:
            exceptions[name] = e
            if not defer_errors:
                break

    if exceptions:
        for name, exception in exceptions.iteritems():
            env.logger.warn(FAILED_INSTALL_MESSAGE % name)
        first_exception = exceptions.values()[0]
        raise first_exception


def _install_application(name, versions, tool_install_dir=None):
    """
    Install single custom tool as Galaxy dependency application.

    TODO: Rename versions and document options.
    """
    if type(versions) is str:
        versions = [versions]
    for version_info in versions:
        if type(version_info) is str:
            _install_tool(env, name, version=version_info, requirement_name=name, tool_install_dir=tool_install_dir)
        else:
            version = version_info["version"]
            bin_dirs = version_info.get("bin_dirs", ["bin"])
            env_vars = version_info.get("env_vars", {})
            provides = version_info.get("provides", [])
            if isinstance(provides, (str, unicode, basestring)):
                provides = [provides]
            for provide_conf in provides[:]:
                if isinstance(provide_conf, dict):
                    provides.remove(provide_conf)
                    if __check_conditional(provide_conf):
                        provies.append(provide_conf["name"])

            # Some requirements (e.g. blast+) maybe not have valid python
            # identifiers as name. Use install_blast to setup but override
            # requirement directory name with requirement_name field.
            requirement_name = version_info.get("requirement_name", name)
            tool_env = _install_tool(env, name, version, bin_dirs=bin_dirs, env_vars=env_vars, requirement_name=requirement_name, tool_install_dir=tool_install_dir)
            symlink_versions = version_info.get("symlink_versions", [])
            if type(symlink_versions) is str:
                symlink_versions = [symlink_versions]
            for symlink_version in symlink_versions:
                _set_default_config(tool_env, tool_env["system_install"], symlink_version)

            if provides:
                install_dir = tool_env["system_install"]
                ## Create additional symlinked packages from this one.
                tool_dir = "%s/.." % install_dir
                tools_dir = "%s/.." % tool_dir
                for package in provides:
                    link_dir = "%s/%s" % (tools_dir, package)
                    env.safe_sudo("ln -f -s '%s' '%s'" % (requirement_name, link_dir))


def _install_tool(env, name, version, requirement_name, bin_dirs=["bin"], env_vars={}, tool_install_dir=None):
    tool_env = _build_tool_env(env, requirement_name, version, tool_install_dir)
    env.logger.debug("Installing a Galaxy tool via 'install_%s'" % name)
    eval("install_%s" % name)(tool_env)
    _install_galaxy_config(tool_env, bin_dirs, env_vars=env_vars)
    return tool_env


def _build_tool_env(env, name, version, tool_install_dir):
    """ Build new env to have tool installed for Galaxy instead of into /usr. """
    tool_env = {"tool_version": version,
                "galaxy_tool_install": True}
    for key, value in env.iteritems():
        tool_env[key] = value
    if not tool_install_dir:
        tool_install_dir = os.path.join(env.galaxy_tools_dir, name, version)
    tool_env["system_install"] = tool_install_dir
    tool_env["local_install"] = tool_install_dir
    tool_env["venv_directory"] = "%s/%s" % (tool_env["system_install"], "venv")
    return AttributeDict(tool_env)


def __check_conditional(conf_dict):
    passes = True
    try:
        if "if" in conf_dict:
            value = conf_dict["if"]
            passes = _read_boolean(env, value, False)
        elif "unless" in conf_dict:
            value = conf_dict["unless"]
            passes = not _read_boolean(env, value, False)
    except TypeError:
        # configuration is not a dictionary, default to True
        pass
    return passes


class AttributeDict(dict):
    """
    Dictionary that allows attribute access to values.

    This is needed because cloudbio.custom.* accesses env extensively via
    attributes (e.g. env.system_install).

    http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def _install_galaxy_config(tool_env, bin_dirs, env_vars):
    """
    Setup galaxy tool config files (env.sh-es) and default version
    symbolic links.
    """
    install_dir = tool_env["system_install"]
    env_path = os.path.join(install_dir, "env.sh")
    bin_paths = [os.path.join(install_dir, bin_dir) for bin_dir in bin_dirs]
    path_pieces = [bin_path for bin_path in bin_paths if env.safe_exists(bin_path)]
    if len(path_pieces) > 0 and not env.safe_exists(env_path):
        path_addtion = ":".join(path_pieces)
        # Standard bin install, just add it to path
        env.safe_sudo("echo 'PATH=%s:$PATH' > %s" % (path_addtion, env_path))
        venv_path = "%s/%s" % (install_dir, "venv")
        if env.safe_exists(venv_path):
            #  Have env.sh activate virtualdirectory
            env.safe_sudo("echo '. %s/bin/activate' >> %s" % (venv_path, env_path))
        env.safe_sudo("chmod +x %s" % env_path)
        for env_var, env_var_value in env_vars.iteritems():
            env_var_template = Template(env_var_value)
            expanded_env_var_value = env_var_template.substitute(tool_env)
            env.safe_sudo("echo 'export %s=%s' >> %s" % (env_var, expanded_env_var_value, env_path))
        env.logger.debug("Added Galaxy env.sh file: %s" % env_path)

    # TODO: If a direct install (i.e. tool_install_dir specified instead of galaxy_tools_dir)
    # default is still setup. This is not really desired.
    _set_default_config(tool_env, install_dir)
    if _read_boolean(tool_env, "autoload_galaxy_tools", False) and env.safe_exists(env_path):
        # In this case, the web user (e.g. ubuntu) should auto-load all of
        # galaxy's default env.sh files so they are available for direct use
        # as well.
        _add_to_profiles(". %s" % env_path, profiles=["~/.bashrc"])

########NEW FILE########
__FILENAME__ = utils
from fabric.api import sudo
from fabric.contrib.files import exists


def _read_boolean(env, name, default):
    ## TODO: Replace calls to this with calls to cloudbio.custom.shared version
    property_str = env.get(name, str(default))
    return property_str.upper() in ["TRUE", "YES"]


def _chown_galaxy(env, path):
    """
    Recursively change ownership of ``path``, first checking if ``path`` exists.
    """
    chown_command = "chown --recursive %s:%s %s"
    galaxy_user = env.get("galaxy_user", "galaxy")
    if env.safe_exists(path):
        env.safe_sudo(chown_command % (galaxy_user, galaxy_user, path))


def _dir_is_empty(path):
    """
    Return ``True`` is ``path`` directory has no files or folders in it.
    Return ``False`` otherwise.
    """
    if "empty" in sudo('[ "$(ls -A {0})" ] || echo "empty"'.format(path)):
        return True
    return False

########NEW FILE########
__FILENAME__ = libraries
"""Installers for programming language specific libraries.
"""
import os

from fabric.api import env
from cloudbio import fabutils

def r_library_installer(config):
    """Install R libraries using CRAN and Bioconductor.
    """
    # Create an Rscript file with install details.
    out_file = "install_packages.R"
    if env.safe_exists(out_file):
        env.safe_run("rm -f %s" % out_file)
    env.safe_run("touch %s" % out_file)
    lib_loc = os.path.join(env.system_install, "lib", "R", "site-library")
    env.safe_sudo("mkdir -p %s" % lib_loc)
    repo_info = """
    .libPaths(c("%s"))
    library(methods)
    cran.repos <- getOption("repos")
    cran.repos["CRAN" ] <- "%s"
    options(repos=cran.repos)
    source("%s")
    """ % (lib_loc, config["cranrepo"], config["biocrepo"])
    env.safe_append(out_file, repo_info)
    install_fn = """
    repo.installer <- function(repos, install.fn) {
      %s
      maybe.install <- function(pname) {
        if (!(pname %%in%% installed.packages()))
          install.fn(pname)
      }
    }
    """
    if config.get("update_packages", True):
        update_str = """
        update.packages(lib.loc="%s", repos=repos, ask=FALSE)
        """ % lib_loc
    else:
        update_str = "\n"
    env.safe_append(out_file, install_fn % update_str)
    std_install = """
    std.pkgs <- c(%s)
    std.installer = repo.installer(cran.repos, install.packages)
    lapply(std.pkgs, std.installer)
    """ % (", ".join('"%s"' % p for p in config['cran']))
    env.safe_append(out_file, std_install)
    if len(config.get("bioc", [])) > 0:
        bioc_install = """
        bioc.pkgs <- c(%s)
        bioc.installer = repo.installer(biocinstallRepos(), biocLite)
        lapply(bioc.pkgs, bioc.installer)
        """ % (", ".join('"%s"' % p for p in config['bioc']))
        env.safe_append(out_file, bioc_install)
    # run the script and then get rid of it
    rscript = fabutils.find_cmd(env, "Rscript", "--version")
    if rscript:
        env.safe_sudo("%s %s" % (rscript, out_file))
    else:
        env.logger.warn("Rscript not found; skipping install of R libraries.")
    env.safe_run("rm -f %s" % out_file)

########NEW FILE########
__FILENAME__ = manifest
"""Provide dump of software and libraries installed on CloudBioLinux image.

This provides an output YAML file with package details, providing a complete
dump of installed software and packages. The YAML output feeds into a BioGems
style webpage that provides a more human friendly view of installed packages.
The version information provides a reproducible dump of software on a system.
"""
import os
import collections
import inspect
import urllib2
import subprocess
import sys

import yaml
try:
    import yolk.yolklib
    import yolk.metadata
except ImportError:
    yolk = None

def create(out_dir, tooldir="/usr/local", fetch_remote=False):
    """Create a manifest in the output directory with installed packages.
    """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    write_debian_pkg_info(out_dir, fetch_remote)
    write_python_pkg_info(out_dir)
    write_r_pkg_info(out_dir)
    write_brew_pkg_info(out_dir, tooldir)
    write_custom_pkg_info(out_dir, tooldir)

# ## Custom packages

def _get_custom_pkg_info(name, fn):
    """Retrieve information about the installed package from the install function.
    """
    vals = dict((k, v) for k, v in inspect.getmembers(fn))
    code = inspect.getsourcelines(fn)
    if vals["__name__"] == "decorator":
        fn = [x for x in fn.func_closure if not isinstance(x.cell_contents, str)][0].cell_contents
        vals = dict((k, v) for k, v in inspect.getmembers(fn))
        code = inspect.getsourcelines(fn)
    version = ""
    for line in (l.strip() for l in code[0]):
        if line.find("version") >= 0 and line.find(" =") > 0:
            version = line.split()[-1].replace('"', '').replace("'", "")
        if version:
            break
    doc = vals.get("func_doc", "")
    descr, homepage = "", ""
    if doc is not None:
        descr = doc.split("\n")[0]
        for line in doc.split("\n"):
            if line.strip().startswith("http"):
                homepage = line.strip()
    return {"name": name.replace("install_", ""),
            "description": descr,
            "homepage_uri": homepage,
            "version": version}

def _handle_gatk_custom(tooldir):
    """Determine version of GATK enabled. Handle special cases.
    """
    # Installed via custom package system, encorporating gatk_protected
    gatk_symlink = os.path.join(tooldir, "share", "java", "gatk")
    if os.path.lexists(gatk_symlink):
        gatk_name = os.path.basename(os.path.realpath(gatk_symlink))
        return gatk_name.replace("gatk-", "")

def write_custom_pkg_info(out_dir, tooldir):
    custom_names = ["bio_general", "bio_nextgen", "cloudman", "distributed",
                    "java", "python", "phylogeny", "system"]
    out_file = os.path.join(out_dir, "custom-packages.yaml")
    if not os.path.exists(out_file):
        out = {}
        for modname in custom_names:
            mod = getattr(__import__("cloudbio.custom", globals(), locals(),
                                     [modname], -1),
                          modname)
            for prog in [x for x in dir(mod) if x.startswith("install")]:
                pkg = _get_custom_pkg_info(prog, getattr(mod, prog))
                out[pkg["name"]] = pkg
        gatk_custom_v = _handle_gatk_custom(tooldir)
        if gatk_custom_v:
            out["gatk"]["version"] = gatk_custom_v
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

# ## Homebrew/Linuxbrew packages

def write_brew_pkg_info(out_dir, tooldir):
    """Extract information for packages installed by homebrew/linuxbrew.
    """
    out_file = os.path.join(out_dir, "brew-packages.yaml")
    if not os.path.exists(out_file):
        brew_cmd = os.path.join(tooldir, "bin", "brew") if tooldir else None
        if not brew_cmd or not os.path.exists(brew_cmd):
            brew_cmd = "brew"
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
                out[name] = {"name": name, "version": v}
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

# ## R packages

def get_r_pkg_info():
    r_command = ("options(width=10000); subset(installed.packages(fields=c('Title', 'URL')), "
                 "select=c('Version', 'Title','URL'))")
    try:
        out = subprocess.check_output(["Rscript", "-e", r_command])
    except (subprocess.CalledProcessError, OSError):
        out = ""
    pkg_raw_list = []
    for line in out.split("\n")[1:]:
        pkg_raw_list.append(filter(None, [entry.strip(' ') for entry in line.split('"')]))
    for pkg in pkg_raw_list:
        if len(pkg) > 2:
            yield {"name": pkg[0], "version": pkg[1],
                   "description": pkg[2],
                   "homepage_uri": (pkg[3], '')[pkg[3] == 'NA'] if len(pkg) > 3 else ""}

def write_r_pkg_info(out_dir):
    out_file = os.path.join(out_dir, "r-packages.yaml")
    if not os.path.exists(out_file):
        out = {}
        for pkg in get_r_pkg_info():
            out[pkg["name"]] = pkg
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

# ## Python packages

def get_python_pkg_info():
    if yolk:
        for dist in yolk.yolklib.Distributions().get_packages("all"):
            md = yolk.metadata.get_metadata(dist)
            yield {"name": md["Name"].lower(), "version": md["Version"],
                   "description": md.get("Summary", ""),
                   "homepage_uri": md.get("Home-page", "")}
    else:
        base_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(base_dir, "conda")):
            for line in subprocess.check_output([os.path.join(base_dir, "conda"), "list"]).split("\n"):
                if line.strip() and not line.startswith("#"):
                    name, version = line.split()[:2]
                    yield {"name": name.lower(), "version": version}
        else:
            for line in subprocess.check_output([os.path.join(base_dir, "pip"), "list"]).split("\n"):
                if line.strip() and not line.startswith("#"):
                    name, version = line.split()[:2]
                    yield {"name": name.lower(), "version": version[1:-1]}

def _resolve_latest_pkg(pkgs):
    if len(pkgs) == 1:
        return pkgs[0]
    else:
        latest_version = yolk.yolklib.Distributions().get_highest_installed(pkgs[0]["name"])
        return [x for x in pkgs if x["version"] == latest_version][0]

def write_python_pkg_info(out_dir):
    out_file = os.path.join(out_dir, "python-packages.yaml")
    if not os.path.exists(out_file):
        pkgs_by_name = collections.defaultdict(list)
        for pkg in get_python_pkg_info():
            pkgs_by_name[pkg["name"]].append(pkg)
        out = {}
        for name in sorted(pkgs_by_name.keys()):
            out[name] = _resolve_latest_pkg(pkgs_by_name[name])
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

# ## Debian packages

def _get_pkg_popcon():
    """Retrieve popularity information for debian packages.
    """
    url = "http://popcon.debian.org/by_vote"
    popcon = {}
    for line in (l for l in urllib2.urlopen(url) if not l.startswith(("#", "--"))):
        parts = line.split()
        popcon[parts[1]] = int(parts[3])
    return popcon

def get_debian_pkg_info(fetch_remote=False):
    pkg_popcon = _get_pkg_popcon() if fetch_remote else {}
    cmd = ("dpkg-query --show --showformat "
           "'${Status}\t${Package}\t${Version}\t${Section}\t${Homepage}\t${binary:Summary}\n'")
    for pkg_line in [l for l in subprocess.check_output(cmd, shell=True).split("\n")
                     if l.startswith("install ok")]:
        parts = pkg_line.rstrip("\n").split("\t")
        pkg = {"name": parts[1], "version": parts[2],
               "section": parts[3], "homepage_uri": parts[4],
               "description": parts[5]}
        if pkg_popcon.get(pkg["name"]):
            pkg["downloads"] = pkg_popcon.get(pkg["name"], 0)
        yield pkg

def write_debian_pkg_info(out_dir, fetch_remote=False):
    base_sections = set(["gnome", "admin", "utils", "web", "games",
                         "sound", "devel", "kde", "x11", "net", "text",
                         "graphics", "misc", "editors", "fonts", "doc",
                         "mail", "otherosfs", "video", "kernel",
                         "libs", "libdevel", "comm", "metapackages", "tex",
                         "introspection"])
    for s in list(base_sections):
        base_sections.add("universe/%s" % s)
        base_sections.add("partner/%s" % s)
    out_file = os.path.join(out_dir, "debian-packages.yaml")
    out_base_file = os.path.join(out_dir, "debian-base-packages.yaml")
    try:
        subprocess.check_call(["dpkg", "--help"], stdout=subprocess.PIPE)
        has_dpkg = True
    except (subprocess.CalledProcessError, OSError):
        has_dpkg = False
    if has_dpkg and (not os.path.exists(out_file) or not os.path.exists(out_base_file)):
        out = {}
        out_base = {}
        for pkg in get_debian_pkg_info(fetch_remote):
            if pkg.get("section") in base_sections:
                out_base[pkg["name"]] = pkg
            else:
                out[pkg["name"]] = pkg
        with open(out_file, "w") as out_handle:
            yaml.safe_dump(out, out_handle, default_flow_style=False, allow_unicode=False)
        with open(out_base_file, "w") as out_handle:
            yaml.safe_dump(out_base, out_handle, default_flow_style=False, allow_unicode=False)
    return out_file

########NEW FILE########
__FILENAME__ = brew
"""Install packages via the MacOSX Homebrew and Linux Linuxbrew package manager.
https://github.com/mxcl/homebrew
https://github.com/Homebrew/linuxbrew
"""
import contextlib
from distutils.version import LooseVersion
import os

from cloudbio.custom import system
from cloudbio.flavor.config import get_config_file
from cloudbio.fabutils import quiet, find_cmd
from cloudbio.package.shared import _yaml_to_packages

from fabric.api import cd, settings

def install_packages(env, to_install=None, packages=None):
    """Install packages using the home brew package manager.

    Handles upgrading brew, tapping required repositories and installing or upgrading
    packages as appropriate.

    `to_install` is a CloudBioLinux compatible set of top level items to add,
    alternatively `packages` is a list of raw package names.
    """
    config_file = get_config_file(env, "packages-homebrew.yaml")
    if to_install:
        (packages, _) = _yaml_to_packages(config_file.base, to_install, config_file.dist)
    # if we have no packages to install, do not try to install or update brew
    if len(packages) == 0:
        return
    system.install_homebrew(env)
    brew_cmd = _brew_cmd(env)
    formula_repos = ["homebrew/science", "chapmanb/cbl"]
    current_taps = set([x.strip() for x in env.safe_run_output("%s tap" % brew_cmd).split()])
    _safe_update(env, brew_cmd, formula_repos, current_taps)
    for repo in formula_repos:
        if repo not in current_taps:
            env.safe_run("%s tap %s" % (brew_cmd, repo))
    env.safe_run("%s tap --repair" % brew_cmd)
    ipkgs = {"outdated": set([x.strip() for x in env.safe_run_output("%s outdated" % brew_cmd).split()]),
             "current": _get_current_pkgs(env, brew_cmd)}
    _install_brew_baseline(env, brew_cmd, ipkgs, packages)
    for pkg_str in packages:
        _install_pkg(env, pkg_str, brew_cmd, ipkgs)

def _safe_update(env, brew_cmd, formula_repos, cur_taps):
    """Revert any taps if we fail to update due to local changes.
    """
    with settings(warn_only=True):
        out = env.safe_run("%s update" % brew_cmd)
    if out.failed:
        for repo in formula_repos:
            if repo in cur_taps:
                env.safe_run("%s untap %s" % (brew_cmd, repo))
        env.safe_run("%s update" % brew_cmd)

def _get_current_pkgs(env, brew_cmd):
    out = {}
    with quiet():
        which_out = env.safe_run_output("{brew_cmd} list --versions".format(**locals()))
    for line in which_out.split("\n"):
        if line:
            parts = line.rstrip().split()
            if len(parts) == 2:
                pkg, version = line.rstrip().split()
                if pkg.endswith(":"):
                    pkg = pkg[:-1]
                out[pkg] = version
    return out

def _install_pkg(env, pkg_str, brew_cmd, ipkgs):
    """Install a specific brew package, handling versioning and existing packages.
    """
    pkg, version = _get_pkg_and_version(pkg_str)
    if version:
        _install_pkg_version(env, pkg, version, brew_cmd, ipkgs)
    else:
        _install_pkg_latest(env, pkg, brew_cmd, ipkgs)

def _install_pkg_version(env, pkg, version, brew_cmd, ipkgs):
    """Install a specific version of a package by retrieving from git history.
    https://gist.github.com/gcatlin/1847248
    Handles both global packages and those installed via specific taps.
    """
    if ipkgs["current"].get(pkg.split("/")[-1]) == version:
        return
    if version == "HEAD":
        env.safe_run("{brew_cmd} install --HEAD {pkg}".format(**locals()))
    else:
        raise ValueError("Cannot currently handle installing brew packages by version.")
        with _git_pkg_version(env, brew_cmd, pkg, version):
            if pkg.split("/")[-1] in ipkgs["current"]:
                with settings(warn_only=True):
                    env.safe_run("{brew_cmd} unlink {pkg}".format(
                        brew_cmd=brew_cmd, pkg=pkg.split("/")[-1]))
            # if we have a more recent version, uninstall that first
            cur_version_parts = env.safe_run_output("{brew_cmd} list --versions {pkg}".format(
                brew_cmd=brew_cmd, pkg=pkg.split("/")[-1])).strip().split()
            if len(cur_version_parts) > 1 and LooseVersion(cur_version_parts[1]) > LooseVersion(version):
                with settings(warn_only=True):
                    env.safe_run("{brew_cmd} uninstall {pkg}".format(**locals()))
            env.safe_run("{brew_cmd} install {pkg}".format(**locals()))
            with settings(warn_only=True):
                env.safe_run("{brew_cmd} switch {pkg} {version}".format(**locals()))
    env.safe_run("%s link --overwrite %s" % (brew_cmd, pkg))

@contextlib.contextmanager
def _git_pkg_version(env, brew_cmd, pkg, version):
    """Convert homebrew Git to previous revision to install a specific package version.
    """
    git_cmd = _git_cmd_for_pkg_version(env, brew_cmd, pkg, version)
    git_fname = git_cmd.split()[-1]
    brew_prefix = env.safe_run_output("{brew_cmd} --prefix".format(**locals()))
    if git_fname.startswith("{brew_prefix}/Library/Taps/".format(**locals())):
        brew_prefix = os.path.dirname(git_fname)
    try:
        with cd(brew_prefix):
            if version != "HEAD":
                env.safe_run(git_cmd)
        yield
    finally:
        # reset Git back to latest
        with cd(brew_prefix):
            if version != "HEAD":
                cmd_parts = git_cmd.split()
                env.safe_run("%s reset HEAD %s" % (cmd_parts[0], cmd_parts[-1]))
                cmd_parts[2] = "--"
                env.safe_run(" ".join(cmd_parts))

def _git_cmd_for_pkg_version(env, brew_cmd, pkg, version):
    """Retrieve git command to check out a specific version from homebrew.
    """
    git_cmd = None
    for git_line in env.safe_run_output("{brew_cmd} versions {pkg}".format(**locals())).split("\n"):
        if git_line.startswith(version):
            git_cmd = " ".join(git_line.rstrip().split()[1:])
            break
    if git_cmd is None:
        raise ValueError("Did not find version %s for %s" % (version, pkg))
    return git_cmd

def _latest_pkg_version(env, brew_cmd, pkg):
    """Retrieve the latest available version of a package.
    """
    for git_line in env.safe_run_output("{brew_cmd} info {pkg}".format(**locals())).split("\n"):
        if git_line.strip():
            _, version_str = git_line.split(":")
            versions = version_str.split(",")
            return versions[0].split()[-1].strip()

def _install_pkg_latest(env, pkg, brew_cmd, ipkgs, flags=""):
    """Install the latest version of the given package.
    """
    short_pkg = pkg.split("/")[-1]
    do_install = True
    remove_old = False
    if pkg in ipkgs["outdated"] or short_pkg in ipkgs["outdated"]:
        remove_old = True
    elif pkg in ipkgs["current"] or short_pkg in ipkgs["current"]:
        do_install = False
        pkg_version = _latest_pkg_version(env, brew_cmd, pkg)
        if ipkgs["current"].get(pkg, ipkgs["current"][short_pkg]) != pkg_version:
            remove_old = True
            do_install = True
    if do_install:
        if remove_old:
            env.safe_run("{brew_cmd} remove --force {short_pkg}".format(**locals()))
        perl_setup = "export PERL5LIB=%s/lib/perl5:${PERL5LIB}" % env.system_install
        compiler_setup = "export CC=${CC:-`which gcc`} && export CXX=${CXX:-`which g++`}"
        env.safe_run("%s && %s && %s install %s --env=inherit %s" % (compiler_setup, perl_setup,
                                                                     brew_cmd, flags, pkg))
        env.safe_run("%s link --overwrite %s" % (brew_cmd, pkg))

def _get_pkg_and_version(pkg_str):
    """Uses Python style package==0.1 version specifications.
    """
    parts = pkg_str.split("==")
    if len(parts) == 1:
        return parts[0], None
    else:
        assert len(parts) == 2
        return parts

def _install_brew_baseline(env, brew_cmd, ipkgs, packages):
    """Install baseline brew components not handled by dependency system.

    - Installation of required Perl libraries.
    - Ensures installed samtools does not overlap with bcftools
    - Upgrades any package dependencies
    """
    for dep in ["cpanminus", "expat"]:
        _install_pkg_latest(env, dep, brew_cmd, ipkgs)
    # if installing samtools, avoid bcftools conflicts
    if len([x for x in packages if x.find("samtools") >= 0]):
        with settings(warn_only=True):
            def _has_prog(prog):
                try:
                    return int(env.safe_run_output("{brew_cmd} list samtools | grep -c {prog}".format(
                        brew_cmd=brew_cmd, prog=prog)))
                except ValueError:
                    return 0
            if any(_has_prog(p) for p in ["bctools", "vcfutils.pl"]):
                env.safe_run("{brew_cmd} uninstall {pkg}".format(brew_cmd=brew_cmd, pkg="samtools"))
                ipkgs["current"].pop("samtools", None)
        _install_pkg_latest(env, "samtools", brew_cmd, ipkgs, "--without-bcftools")
    for dependency in ["htslib", "libmaus"]:
        if (dependency in ipkgs["outdated"] or "chapmanb/cbl/%s" % dependency in ipkgs["outdated"]
              or dependency not in ipkgs["current"]):
            _install_pkg_latest(env, dependency, brew_cmd, ipkgs)
    cpanm_cmd = os.path.join(os.path.dirname(brew_cmd), "cpanm")
    for perl_lib in ["Statistics::Descriptive"]:
        env.safe_run("%s -i --notest --local-lib=%s '%s'" % (cpanm_cmd, env.system_install, perl_lib))
    # Ensure paths we may have missed on install are accessible to regular user
    if env.use_sudo:
        paths = ["share", "share/java"]
        for path in paths:
            with quiet():
                test_access = env.safe_run("test -d %s/%s && test -O %s/%s" % (env.system_install, path,
                                                                               env.system_install, path))
            if test_access.failed and env.safe_exists("%s/%s" % (env.system_install, path)):
                env.safe_sudo("chown %s %s/%s" % (env.user, env.system_install, path))

def _brew_cmd(env):
    """Retrieve brew command for installing homebrew packages.
    """
    cmd = find_cmd(env, "brew", "--version")
    if cmd is None:
        raise ValueError("Did not find working installation of Linuxbrew/Homebrew")
    else:
        return cmd

########NEW FILE########
__FILENAME__ = deb
"""
Automated installation on debian package systems with apt.
"""
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.package.shared import _yaml_to_packages
from cloudbio.flavor.config import get_config_file


def _apt_packages(to_install=None, pkg_list=None):
    """
    Install packages available via apt-get.
    Note that ``to_install`` and ``pkg_list`` arguments cannot be used simultaneously.

    :type to_install:  list
    :param to_install: A list of strings (ie, groups) present in the ``main.yaml``
                       config file that will be used to filter out the specific
                       packages to be installed.

    :type pkg_list:  list
    :param pkg_list: An explicit list of packages to install. No other files,
                     flavors, or editions are considered.
    """
    if env.edition.short_name not in ["minimal"]:
        env.logger.info("Update the system")
        with settings(warn_only=True):
            env.safe_sudo("apt-get update")
    if to_install is not None:
        config_file = get_config_file(env, "packages.yaml")
        env.edition.apt_upgrade_system(env=env)
        (packages, _) = _yaml_to_packages(config_file.base, to_install, config_file.dist)
        # Allow editions and flavors to modify the package list
        packages = env.edition.rewrite_config_items("packages", packages)
        packages = env.flavor.rewrite_config_items("packages", packages)
    elif pkg_list is not None:
        env.logger.info("Will install specific packages: {0}".format(pkg_list))
        packages = pkg_list
    else:
        raise ValueError("Need a file with packages or a list of packages")
    # A single line install is much faster - note that there is a max
    # for the command line size, so we do 30 at a time
    group_size = 30
    i = 0
    env.logger.info("Installing %i packages" % len(packages))
    while i < len(packages):
        env.logger.info("Package install progress: {0}/{1}".format(i, len(packages)))
        env.safe_sudo("apt-get -y --force-yes install %s" % " ".join(packages[i:i + group_size]))
        i += group_size
    env.safe_sudo("apt-get clean")

def _add_apt_gpg_keys():
    """Adds GPG keys from all repositories
    """
    env.logger.info("Update GPG keys for repositories")
    standalone = [
        "http://archive.cloudera.com/debian/archive.key",
        'http://download.virtualbox.org/virtualbox/debian/oracle_vbox.asc'
    ]
    keyserver = [
            ("keyserver.ubuntu.com", "7F0CEB10"),
            ("keyserver.ubuntu.com", "E084DAB9"),
            ("subkeys.pgp.net", "D018A4CE"),
            ("keyserver.ubuntu.com", "D67FC6EAE2A11821"),
        ]
    standalone, keyserver = env.edition.rewrite_apt_keys(standalone, keyserver)
    for key in standalone:
        with settings(warn_only=True):
            env.safe_sudo("wget -q -O- %s | apt-key add -" % key)
    for url, key in keyserver:
        with settings(warn_only=True):
            env.safe_sudo("apt-key adv --keyserver %s --recv %s" % (url, key))
    with settings(warn_only=True):
        env.safe_sudo("apt-get update")
        env.safe_sudo("sudo apt-get install -y --force-yes bio-linux-keyring")

def _setup_apt_automation():
    """Setup the environment to be fully automated for tricky installs.

    Sun Java license acceptance:
    http://www.davidpashley.com/blog/debian/java-license

    MySQL root password questions; install with empty root password:
    http://snowulf.com/archives/540-Truly-non-interactive-unattended-apt-get-install.html

    Postfix, setup for no configuration. See more on issues here:
    http://www.uluga.ubuntuforums.org/showthread.php?p=9120196
    """
    interactive_cmd = "export DEBIAN_FRONTEND=noninteractive"
    if not env.safe_contains(env.shell_config, interactive_cmd):
        env.safe_append(env.shell_config, interactive_cmd)
    # Remove interactive checks in .bashrc which prevent
    # bash customizations
    env.safe_comment(env.shell_config, "^[ ]+\*\) return;;$")
    package_info = [
            "postfix postfix/not_configured boolean true",
            "postfix postfix/main_mailer_type select 'No configuration'",
            "mysql-server-5.1 mysql-server/root_password string '(password omitted)'",
            "mysql-server-5.1 mysql-server/root_password_again string '(password omitted)'",
            "sun-java6-jdk shared/accepted-sun-dlj-v1-1 select true",
            "sun-java6-jre shared/accepted-sun-dlj-v1-1 select true",
            "sun-java6-bin shared/accepted-sun-dlj-v1-1 select true",
            "grub-pc grub2/linux_cmdline string ''",
            "grub-pc grub-pc/install_devices_empty boolean true",
            "acroread acroread/default-viewer boolean false",
            "rabbitmq-server rabbitmq-server/upgrade_previous note",
            "condor condor/wantdebconf boolean false",
            "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula boolean true",
            "ttf-mscorefonts-installer msttcorefonts/present-mscorefonts-eula note",
            "gdm shared/default-x-display-manager select gdm",
            "lightdm shared/default-x-display-manager select gdm",
            "postfix postfix/mailname string notusedexample.org",
            # Work harder to avoid gdm dialogs
            # https://bugs.launchpad.net/ubuntu/+source/gdm/+bug/1020770
            "debconf debconf/priority select critical"
            ]
    package_info = env.edition.rewrite_apt_automation(package_info)
    cmd = ""
    for l in package_info:
        cmd += 'echo "%s" | /usr/bin/debconf-set-selections;' % l
    env.safe_sudo(cmd)

def _setup_apt_sources():
    """Add sources for retrieving library packages.
       Using add-apt-repository allows processing PPAs (on Ubuntu)

       This method modifies the apt sources file.

       Uses python-software-properties, which provides an abstraction of apt repositories
    """

    # It may be sudo is not installed - which has fab fail - therefor
    # we'll try to install it by default, assuming we have root access
    # already (e.g. on EC2). Fab will fail anyway, otherwise.
    if not env.safe_exists('/usr/bin/sudo') or not env.safe_exists('/usr/bin/curl'):
        env.safe_sudo('apt-get update')
        env.safe_sudo('apt-get -y --force-yes install sudo curl')

    env.logger.debug("_setup_apt_sources " + env.sources_file + " " + env.edition.name)
    env.edition.check_packages_source()
    comment = "# This file was modified for " + env.edition.name
    # Setup apt download policy (default is None)
    # (see also https://help.ubuntu.com/community/PinningHowto)
    preferences = env.edition.rewrite_apt_preferences([])
    if len(preferences):
        # make sure it exists, and is empty
        env.safe_sudo("rm -f %s" % env.apt_preferences_file)
        env.safe_sudo("touch %s" % env.apt_preferences_file)
        env.safe_append(env.apt_preferences_file, comment, use_sudo=True)
        lines = "\n".join(preferences)
        env.logger.debug("Policy %s" % lines)
        # append won't duplicate, so we use echo
        env.safe_sudo("/bin/echo -e \"%s\" >> %s" % (lines, env.apt_preferences_file))
        # check there is no error parsing the file
        env.logger.debug(env.safe_sudo("apt-cache policy"))

    # Make sure a source file exists
    if not env.safe_exists(env.sources_file):
        env.safe_sudo("touch %s" % env.sources_file)
    # Add a comment
    if not env.safe_contains(env.sources_file, comment):
        env.safe_append(env.sources_file, comment, use_sudo=True)
    for source in env.edition.rewrite_apt_sources_list(env.std_sources):
        env.logger.debug("Source %s" % source)
        if source.startswith("ppa:"):
            env.safe_sudo("apt-get install -y --force-yes python-software-properties")
            env.safe_sudo("add-apt-repository '%s'" % source)
        elif (not env.safe_contains(env.sources_file, source) and
              not env.safe_contains(env.global_sources_file, source)):
            env.safe_append(env.sources_file, source, use_sudo=True)

########NEW FILE########
__FILENAME__ = nix
"""Install software with the Nix package manager.
"""
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.package.shared import _yaml_to_packages
from cloudbio.flavor.config import get_config_file

def _setup_nix_sources():
    if env.nixpkgs:
        target_info = run("uname -a")
        env.logger.info("Target: "+target_info)
        # find the target architecture, if not preset
        if not env.has_key("arch"):
          env.arch = run("uname -m")

     # first override the path
        append("/root/.bashrc", "export PATH=$HOME/.nix-profile/bin:$PATH", use_sudo=True)
        env.logger.info("Checking NixPkgs")
        if not exists("/nix/store"):
            # first time installation
            if not exists("/usr/bin/nix-env"):
               # install Nix (standard Debian release)
               nix_deb = "nix_0.16-1_"+env.arch+".deb"
               if not exists(nix_deb):
                   # run("wget http://hydra.nixos.org/build/565031/download/1/nix_0.16-1_i386.deb")
                   run("wget http://hydra.nixos.org/build/565048/download/1/"+nix_deb)
                   sudo("dpkg -i "+nix_deb)
        run("nix-channel --list")
        if run("nix-channel --list") == "":
            # Setup channel
            sudo("nix-channel --add http://nixos.org/releases/nixpkgs/channels/nixpkgs-unstable")
        sudo("nix-channel --update")
        # upgrade Nix to latest (and remove the older version, as it is much slower)
        sudo("nix-env -b -i nix")
        if exists("/usr/bin/nix-env"):
            env.logger.info("uninstall older Nix (Debian release)")
            sudo("dpkg -r nix")

def _nix_packages(to_install):
    """Install packages available via nixpkgs (optional)
    """
    if env.nixpkgs:
        env.logger.info("Update and install NixPkgs packages")
        pkg_config_file = get_config_file(env, "packages-nix.yaml").base
        sudo("nix-channel --update")
        # Retrieve final package names
        (packages, _) = _yaml_to_packages(pkg_config_file, to_install)
        packages = env.edition.rewrite_config_items("packages", packages)
        packages = env.flavor.rewrite_config_items("packages", packages)
        for p in packages:
            sudo("nix-env -b -i %s" % p)

########NEW FILE########
__FILENAME__ = rpm
"""Automated installation on RPM systems with the yum package manager.
"""
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.package.shared import _yaml_to_packages
from cloudbio.flavor.config import get_config_file

def _yum_packages(to_install):
    """Install rpm packages available via yum.
    """
    if env.distribution == "scientificlinux":
        package_file = "packages-scientificlinux.yaml"
    else:
        package_file = "packages-yum.yaml"
    pkg_config = get_config_file(env, package_file).base
    with settings(warn_only=True):
        env.safe_sudo("yum check-update")
    if env.edition.short_name not in ["minimal"]:
        env.safe_sudo("yum -y upgrade")
    # Retrieve packages to get and install each of them
    (packages, _) = _yaml_to_packages(pkg_config, to_install)
    # At this point allow the Flavor to rewrite the package list
    packages = env.flavor.rewrite_config_items("packages", packages)
    for package in packages:
        env.safe_sudo("yum -y install %s" % package)

def _setup_yum_bashrc():
    """Fix the user bashrc to update compilers.
    """
    if env.distribution in ["centos"]:
        to_include = ["export PKG_CONFIG_PATH=${PKG_CONFIG_PATH}:/usr/lib/pkgconfig"]
        # gcc fixes no longer necessary on recent CentOS versions
        #"export CC=gcc44", "export CXX=g++44", "export FC=gfortran44",
        fname = env.safe_run_output("ls %s" % env.shell_config)
        for line in to_include:
            if not env.safe_contains(fname, line.split("=")[0]):
                env.safe_append(fname, line)

def _setup_yum_sources():
    """Add additional useful yum repositories.
    """
    repos = [
      "http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm",
      "http://archive.cloudera.com/redhat/6/x86_64/cdh/cdh3-repository-1.0-1.noarch.rpm"
    ]
    for repo in repos:
        with settings(warn_only=True):
            env.safe_sudo("rpm -Uvh %s" % repo)

########NEW FILE########
__FILENAME__ = shared
"""Shared functionality useful for multiple package managers.
"""
import yaml
from fabric.api import *
from fabric.contrib.files import *

def _yaml_to_packages(yaml_file, to_install, subs_yaml_file = None):
    """Read a list of packages from a nested YAML configuration file.
    """
    env.logger.info("Reading %s" % yaml_file)
    with open(yaml_file) as in_handle:
        full_data = yaml.load(in_handle)
    if subs_yaml_file is not None:
        with open(subs_yaml_file) as in_handle:
            subs = yaml.load(in_handle)
    else:
        subs = {}
    # filter the data based on what we have configured to install
    data = [(k, v) for (k, v) in full_data.iteritems()
            if to_install is None or k in to_install]
    data.sort()
    packages = []
    pkg_to_group = dict()
    while len(data) > 0:
        cur_key, cur_info = data.pop(0)
        if cur_info:
            if isinstance(cur_info, (list, tuple)):
                packages.extend(_filter_subs_packages(cur_info, subs))
                for p in cur_info:
                    pkg_to_group[p] = cur_key
            elif isinstance(cur_info, dict):
                for key, val in cur_info.iteritems():
                    # if we are okay, propagate with the top level key
                    if key == 'needs_64bit':
                        if env.is_64bit:
                            data.insert(0, (cur_key, val))
                    elif key.startswith(env.distribution):
                        if key.endswith(env.dist_name):
                            data.insert(0, (cur_key, val))
                    else:
                        data.insert(0, (cur_key, val))
            else:
                raise ValueError(cur_info)
    env.logger.debug("Packages to install: {0}".format(",".join(packages)))
    return packages, pkg_to_group

def _filter_subs_packages(initial, subs):
    """Rename and filter package list with subsitutions; for similar systems.
    """
    final = []
    for p in initial:
        try:
            new_p = subs[p]
        except KeyError:
            new_p = p
        if new_p:
            final.append(new_p)
    return sorted(final)

########NEW FILE########
__FILENAME__ = utils
"""Utilities for logging and progress tracking.
"""
import logging
import os
import sys

from fabric.main import load_settings
from fabric.colors import yellow, red, green, magenta
from fabric.api import settings, hide, cd, run
from fabric.contrib.files import exists

from cloudbio.edition import _setup_edition
from cloudbio.distribution import _setup_distribution_environment
from cloudbio.flavor import Flavor
from cloudbio.flavor.config import get_config_file


class ColorFormatter(logging.Formatter):
    """ Format log message based on the message level
        http://stackoverflow.com/questions/1343227/can-pythons-logging-format-be-modified-depending-on-the-message-log-level
    """
    # Setup formatters for each of the levels
    err_fmt  = red("ERR [%(filename)s(%(lineno)d)] %(msg)s")
    warn_fmt  = magenta("WARN [%(filename)s(%(lineno)d)]: %(msg)s")
    dbg_fmt  = yellow("DBG [%(filename)s]: %(msg)s")
    info_fmt = green("INFO: %(msg)s")

    def __init__(self, fmt="%(name)s %(levelname)s: %(msg)s"):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._fmt
        # Replace the original format with one customized by logging level
        if record.levelno == 10:   # DEBUG
            self._fmt = ColorFormatter.dbg_fmt
        elif record.levelno == 20: # INFO
            self._fmt = ColorFormatter.info_fmt
        elif record.levelno == 30: # WARN
            self._fmt = ColorFormatter.warn_fmt
        elif record.levelno == 40: # ERROR
            self._fmt = ColorFormatter.err_fmt
        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)
        # Restore the original format configured by the user
        self._fmt = format_orig
        return result

def _setup_logging(env):
    env.logger = logging.getLogger("cloudbiolinux")
    env.logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # Use custom formatter
    ch.setFormatter(ColorFormatter())
    env.logger.addHandler(ch)

def _update_biolinux_log(env, target, flavor):
    """Updates the VM so it contains information on the latest BioLinux
       update in /var/log/biolinux.log.

       The latest information is appended to the file and can be used to see if
       an installation/update has completed (see also ./test/test_vagrant).
    """
    if not target:
        target = env.get("target", None)
        if not target:
            target = "unknown"
        else:
            target = target.name
    if not flavor:
        flavor = env.get("flavor", None)
        if not flavor:
            flavor = "unknown"
        else:
            flavor = flavor.name
    logfn = "/var/log/biolinux.log"
    info = "Target="+target+"; Edition="+env.edition.name+"; Flavor="+flavor
    env.logger.info(info)
    if env.use_sudo:
        env.safe_sudo("date +\"%D %T - Updated "+info+"\" >> "+logfn)


def _configure_fabric_environment(env, flavor=None, fabricrc_loader=None,
                                  ignore_distcheck=False):
    if not fabricrc_loader:
        fabricrc_loader = _parse_fabricrc

    _setup_flavor(env, flavor)
    fabricrc_loader(env)
    _setup_edition(env)
    # get parameters for distro, packages etc.
    _setup_distribution_environment(ignore_distcheck=ignore_distcheck)
    _create_local_paths(env)


def _setup_flavor(env, flavor):
    """Setup a flavor, providing customization hooks to modify CloudBioLinux installs.

    Specify flavor as a name, in which case we look it up in the standard flavor
    directory (contrib/flavor/your_flavor), or as a path to a flavor directory outside
    of cloudbiolinux.
    """
    env.flavor = Flavor(env)
    env.flavor_dir = None
    if flavor:
        # setup the directory for flavor customizations
        if os.path.isabs(flavor):
            flavor_dir = flavor
        else:
            flavor_dir = os.path.join(os.path.dirname(__file__), "..", "contrib", "flavor", flavor)
        assert os.path.exists(flavor_dir), \
            "Did not find directory {0} for flavor {1}".format(flavor_dir, flavor)
        env.flavor_dir = flavor_dir
        # Load python customizations to base configuration if present
        for ext in ["", "flavor"]:
            py_flavor = os.path.split(os.path.realpath(flavor_dir))[1] + ext
            flavor_custom_py = os.path.join(flavor_dir, "{0}.py".format(py_flavor))
            if os.path.exists(flavor_custom_py):
                sys.path.append(flavor_dir)
                mod = __import__(py_flavor, fromlist=[py_flavor])
    env.logger.info("This is a %s" % env.flavor.name)

def _parse_fabricrc(env):
    """Defaults from fabricrc.txt file; loaded if not specified at commandline.
    """
    env.config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
    env.tool_data_table_conf_file = os.path.join(env.config_dir, "..",
                                                 "installed_files",
                                                 "tool_data_table_conf.xml")
    if not env.has_key("distribution") and not env.has_key("system_install"):
        env.logger.info("Reading default fabricrc.txt")
        env.update(load_settings(get_config_file(env, "fabricrc.txt").base))


def _create_local_paths(env):
    """Expand any paths defined in terms of shell shortcuts (like ~).
    """
    with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                  warn_only=True):
        # This is the first point we call into a remote host - make sure
        # it does not fail silently by calling a dummy run
        env.logger.info("Now, testing connection to host...")
        test = env.safe_run("pwd")
        # If there is a connection failure, the rest of the code is (sometimes) not
        # reached - for example with Vagrant the program just stops after above run
        # command.
        if test != None:
            env.logger.info("Connection to host appears to work!")
        else:
            raise NotImplementedError("Connection to host failed")
        env.logger.debug("Expand paths")
        if "local_install" in env:
            if not env.safe_exists(env.local_install):
                env.safe_sudo("mkdir -p %s" % env.local_install)
                user = env.safe_run_output("echo $USER")
                env.safe_sudo("chown -R %s %s" % (user, env.local_install))
            with cd(env.local_install):
                result = env.safe_run_output("pwd")
                env.local_install = result

########NEW FILE########
__FILENAME__ = boincflavor
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.flavor import Flavor

from cloudbio.custom.shared import (_fetch_and_unpack)

class BoincFlavor(Flavor):
    """A VM flavor for running Boinc
    """
    def __init__(self, env):
        Flavor.__init__(self,env)
        self.name = "Boinc Flavor"

    def rewrite_config_items(self, name, packages):
        if name == 'packages':
          packages += [ 'openssh-server', 'unzip', 'tar', 'sudo' ]
        for package in packages:
          env.logger.info("Selected: "+name+" "+package)
        return packages

    def post_install(self):
        env.logger.info("Starting post-install")
        pass

env.flavor = BoincFlavor(env)

########NEW FILE########
__FILENAME__ = phylogenyflavor
from fabric.api import *
from fabric.contrib.files import *
from fabfile import _freenx_scripts

from cloudbio.flavor import Flavor

from cloudbio.custom.shared import (_fetch_and_unpack)

class PhylogenyFlavor(Flavor):
    """A VM flavor for running Phylogeny
    """
    def __init__(self, env):
        Flavor.__init__(self,env)
        self.name = "Phylogeny Flavor"

    def rewrite_config_items(self, name, packages):
        if name == 'packages':
          packages += [ 'openssh-server', 'unzip', 'tar', 'sudo', 'openjdk-6-jre']
          packages += [ 'openmpi-bin' ]  # required for MrBayes-MPI
          # if 'bio-linux-mrbayes-multi' in packages:
          #   (Debian version is still not OK)
          #   packages.remove('bio-linux-mrbayes-multi')

        for package in packages:
          env.logger.info("Selected: "+name+" "+package)
        return packages

    def post_install(self):
        env.logger.info("Starting post-install")
        _freenx_scripts()
        pass

env.flavor = PhylogenyFlavor(env)

########NEW FILE########
__FILENAME__ = biotestflavor
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.flavor import Flavor

from cloudbio.custom.shared import (_fetch_and_unpack)

class BioTestFlavor(Flavor):
    """A Flavor for cross Bio* tests
    """
    def __init__(self, env):
        Flavor.__init__(self,env)
        self.name = "Bio* cross-lang flavor"

    def rewrite_config_items(self, name, items):
        if name == "packages":
            # list.remove('screen')
            # list.append('test')
            return items
        elif name == "python":
            return [ 'biopython' ]
        elif name == "perl":
            return [ 'bioperl' ]
        elif name == "ruby":
            return [ 'bio' ]
        elif name == "custom":
            return []
        else:
            return items

    def post_install(self):
        env.logger.info("Starting post-install")
        env.logger.info("Load Scalability tests")
        if exists('Scalability'):
            with cd('Scalability'):
               run('git pull')
        else:
           _fetch_and_unpack("git clone git://github.com/pjotrp/Scalability.git")
        # Now run a post installation routine (for the heck of it)
        run('./Scalability/scripts/hello.sh')

        env.logger.info("Load Cross-language tests")
        if exists('Cross-language-interfacing'):
            with cd('Cross-language-interfacing'):
               run('git pull')
        else:
           _fetch_and_unpack("git clone git://github.com/pjotrp/Cross-language-interfacing.git")
        # Special installs for the tests
        with cd('Cross-language-interfacing'):
            sudo('./scripts/install-packages-root.sh ')
            run('./scripts/install-packages.sh')
            run('./scripts/create_test_files.rb')


env.flavor = BioTestFlavor(env)

########NEW FILE########
__FILENAME__ = sealflavor
from fabric.api import *
from fabric.contrib.files import *

from cloudbio.flavor import Flavor

from cloudbio.custom.shared import (_fetch_and_unpack)

import sys

# This flavour installs the Seal toolkit for processing high-throughput
# sequencing data on Hadoop.
#   http://biodoop-seal.sf.net/
#
# It pulls in quite a few dependencies, including Hadoop itself and
# Pydoop (http://pydoop.sf.net/).
#
# The dependencies it pulls into Cloudbiolinux are structured as follows:
#
# contrib/flavor/seal/main.yaml
#   sealdist
#   customsealdist
#
# config/packages-yum.yaml
#   sealdist (metapackage)
# config/custom.yaml
#   customsealdist (metapackage)
#     - pydoop
#     - seal
#
# The components of the customsealdist metapackage are installed through
# the functions in cloudbio/custom/customsealdist.py
#
#
# This flavour has only been installed on Scientific Linux and has not
# yet been well tested.
#
# To try installing it run the following:
#   cd <your cloudbiolinux directory>
#   fab -f ./fabfile.py -H root@<your host> -c ./contrib/flavor/seal/fabricrc_sl.txt  install_biolinux:packagelist=contrib/flavor/seal/main.yaml
#
# Authors:  Roman Valls Guimera <roman.valls.guimera@scilifelab.se>
#           Luca Pireddu <luca.pireddu@crs4.it>

class SealFlavor(Flavor):
	"""A flavour for installing Seal
	"""
	def __init__(self, env):
		Flavor.__init__(self,env)
		self.name = "Seal Flavor"

	def rewrite_config_items(self, name, packages):
		if name == 'packages':
			if sys.version_info < (2,7):
				# for versions of Python prior to 2.7 we need to add importlib
				# and argparse
				packages.extend([ 
					"python-importlib",
					"python-argparse"
				])
		return packages


	def post_install(self):
		env.logger.info("Starting post-install")
		pass

env.flavor = SealFlavor(env)

########NEW FILE########
__FILENAME__ = data_fabfile
"""Fabric deployment file to install genomic data on remote instances.

Designed to automatically download and manage biologically associated
data on cloud instances like Amazon EC2.

Fabric (http://docs.fabfile.org) manages automation of remote servers.

Usage:
    fab -i key_file -H servername -f data_fabfile.py install_data
"""
import os
import sys

from fabric.main import load_settings
from fabric.api import *
from fabric.contrib.files import *
from fabric.context_managers import path
try:
    import boto
except ImportError:
    boto = None

# preferentially use local cloudbio directory
for to_remove in [p for p in sys.path if p.find("cloudbiolinux-") > 0]:
    sys.path.remove(to_remove)
sys.path.append(os.path.dirname(__file__))

from cloudbio.utils import _setup_logging, _configure_fabric_environment
from cloudbio.biodata import genomes

# -- Host specific setup

env.remove_old_genomes = False

def setup_environment():
    """Setup environment with required data file locations.
    """
    _setup_logging(env)
    _add_defaults()
    _configure_fabric_environment(env, ignore_distcheck=True)

def _add_defaults():
    """Defaults from fabricrc.txt file; loaded if not specified at commandline.
    """
    env.config_dir = os.path.join(os.path.dirname(__file__), "config")
    conf_file = "tool_data_table_conf.xml"
    env.tool_data_table_conf_file = os.path.join(os.path.dirname(__file__),
                                                 "installed_files", conf_file)
    if not env.has_key("distribution"):
        config_file = os.path.join(env.config_dir, "fabricrc.txt")
        if os.path.exists(config_file):
            env.update(load_settings(config_file))

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "biodata.yaml")

def install_data(config_source=CONFIG_FILE):
    """Main entry point for installing useful biological data.
    """
    setup_environment()
    genomes.install_data(config_source)

def install_data_s3(config_source=CONFIG_FILE, do_setup_environment=True):
    """Install data using pre-existing genomes present on Amazon s3.
    """
    setup_environment()
    genomes.install_data_s3(config_source)

def install_data_rsync(config_source=CONFIG_FILE):
    """Install data using Galaxy rsync data servers.
    """
    setup_environment()
    genomes.install_data_rsync(config_source)

def upload_s3(config_source=CONFIG_FILE):
    """Upload prepared genome files by identifier to Amazon s3 buckets.
    """
    setup_environment()
    genomes.upload_s3(config_source)

########NEW FILE########
__FILENAME__ = test_install_galaxy_tool
"""
Test script for building Python API for installing Galaxy tools using
CBL without any dependencies (i.e. it clones down CBL and utilizes it
like bcbio-nextgen's installer).

Goal is to ultimately fold something like this to Galaxy tool shed
client code to provide high-level support for easy CloudBioLinux based
tool installations as @chapmanb described at the 2013 BOSC Codefest.

  <action type="cloudbiolinux_install"
          [cbl_revision="<cbl_git_changeset(default=master)>"]
          [cbl_url="<cbl_repo_url(default=https://github.com/chapmanb/cloudbiolinux)>"]
          [tool_name="<tool_name(default=use dependency package name)>"]
          [tool_version="<tool_version(default=use dependency package version)>"]
          />

"""

import os
from subprocess import check_call
from tempfile import mkdtemp
from getpass import getuser


DEFAULT_CBL_URL = "https://github.com/chapmanb/cloudbiolinux.git"


def __clone_cloudbiolinux(cbl_config):
    """Clone CloudBioLinux to a temporary directory.

    TODO: Support particular revision.
    """
    cbl_url = cbl_config.get("repository", DEFAULT_CBL_URL)
    cbl_dir = mkdtemp(suffix="cbl")
    check_call(["git", "clone", cbl_url, cbl_dir])

    revision = cbl_config.get("revision", None)
    if revision:
        git_dir = os.path.join(cbl_dir, ".git")
        check_call(["git", "--work-tree", cbl_dir, "--git-dir", git_dir, "checkout", revision])
    return cbl_dir


def install_cbl_tool(tool_name, tool_version, install_dir, cbl_config={}):
    cbl_dir = __clone_cloudbiolinux(cbl_config)
    cbl_install_command = [os.path.join(cbl_dir, "deploy", "deploy.sh"), "--action", "install_galaxy_tool"]
    deployer_args = {"vm_provider": "novm",
                     "galaxy_tool_name": tool_name,
                     "galaxy_tool_version": tool_version,
                     "galaxy_tool_dir": install_dir,
                     "settings": "__none__"}
    for prop, val in deployer_args.iteritems():
        cbl_install_command.append("--%s" % prop)
        cbl_install_command.append(val)

    fabric_properties = {"use_sudo": "False",
                         "galaxy_user": getuser()}
    for prop, val in fabric_properties.iteritems():
        cbl_install_command.append("--fabric_property")
        cbl_install_command.append(prop)
        cbl_install_command.append("--fabric_value")
        cbl_install_command.append(val)
    check_call(cbl_install_command)

cbl_config = {"repository": "https://github.com/jmchilton/cloudbiolinux.git"}
install_cbl_tool("tint_proteomics_scripts", "1.19.20", os.path.abspath("test_tool_dir"), cbl_config)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# CloudBioLinux documentation build configuration file, created by
# sphinx-quickstart on Wed Jul 17 09:14:27 2013.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'CloudBioLinux'
copyright = u'2013, CloudBioLinux contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

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
exclude_patterns = []

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
htmlhelp_basename = 'CloudBioLinuxdoc'


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
  ('index', 'CloudBioLinux.tex', u'CloudBioLinux Documentation',
   u'CloudBioLinux contributors', 'manual'),
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
    ('index', 'cloudbiolinux', u'CloudBioLinux Documentation',
     [u'CloudBioLinux contributors'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'CloudBioLinux', u'CloudBioLinux Documentation',
   u'CloudBioLinux contributors', 'CloudBioLinux', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = fabfile
"""Main Fabric deployment file for CloudBioLinux distribution.

This installs a standard set of useful biological applications on a remote
server. It is designed for bootstrapping a machine from scratch, as with new
Amazon EC2 instances.

Usage:

    fab -H hostname -i private_key_file install_biolinux

which will call into the 'install_biolinux' method below. See the README for
more examples.

Requires:
    Fabric http://docs.fabfile.org
    PyYAML http://pyyaml.org/wiki/PyYAMLDocumentation
"""
import os
import sys
from datetime import datetime

from fabric.api import *
from fabric.contrib.files import *
import yaml

# use local cloudbio directory
for to_remove in [p for p in sys.path if p.find("cloudbiolinux-") > 0]:
    sys.path.remove(to_remove)
sys.path.append(os.path.dirname(__file__))
import cloudbio

from cloudbio import libraries
from cloudbio.utils import _setup_logging, _configure_fabric_environment
from cloudbio.cloudman import _cleanup_ec2
from cloudbio.cloudbiolinux import _cleanup_space
from cloudbio.custom import shared
from cloudbio.package.shared import _yaml_to_packages
from cloudbio.package import brew
from cloudbio.package import (_configure_and_install_native_packages,
                              _connect_native_packages)
from cloudbio.package.nix import _setup_nix_sources, _nix_packages
from cloudbio.flavor.config import get_config_file
from cloudbio.config_management.puppet import _puppet_provision
from cloudbio.config_management.chef import _chef_provision, chef, _configure_chef

# ### Shared installation targets for all platforms

def install_biolinux(target=None, flavor=None):
    """Main entry point for installing BioLinux on a remote server.

    `flavor` allows customization of CloudBioLinux behavior. It can either
    be a flavor name that maps to a corresponding directory in contrib/flavor
    or the path to a custom directory. This can contain:

      - alternative package lists (main.yaml, packages.yaml, custom.yaml)
      - custom python code (nameflavor.py) that hooks into the build machinery

    `target` allows running only particular parts of the build process. Valid choices are:

      - packages     Install distro packages
      - custom       Install custom packages
      - chef_recipes Provision chef recipes
      - libraries    Install programming language libraries
      - post_install Setup CloudMan, FreeNX and other system services
      - cleanup      Remove downloaded files and prepare images for AMI builds
    """
    _setup_logging(env)
    time_start = _print_time_stats("Config", "start")
    _check_fabric_version()
    _configure_fabric_environment(env, flavor,
                                  ignore_distcheck=(target is not None
                                                    and target in ["libraries", "custom"]))
    env.logger.debug("Target is '%s'" % target)
    _perform_install(target, flavor)
    _print_time_stats("Config", "end", time_start)

def _perform_install(target=None, flavor=None, more_custom_add=None):
    """
    Once CBL/fabric environment is setup, this method actually
    runs the required installation procedures.

    See `install_biolinux` for full details on arguments
    `target` and `flavor`.
    """
    pkg_install, lib_install, custom_ignore, custom_add = _read_main_config()
    if more_custom_add:
        if custom_add is None:
            custom_add = {}
        for k, vs in more_custom_add.iteritems():
            if k in custom_add:
                custom_add[k].extend(vs)
            else:
                custom_add[k] = vs
    if target is None or target == "packages":
        env.keep_isolated = getattr(env, "keep_isolated", "false").lower() in ["true", "yes"]
        # Only touch system information if we're not an isolated installation
        if not env.keep_isolated:
            # can only install native packages if we have sudo access or are root
            if env.use_sudo or env.safe_run_output("whoami").strip() == "root":
                _configure_and_install_native_packages(env, pkg_install)
            else:
                _connect_native_packages(env, pkg_install, lib_install)
        if env.nixpkgs:  # ./doc/nixpkgs.md
            _setup_nix_sources()
            _nix_packages(pkg_install)
    if target is None or target == "custom":
        _custom_installs(pkg_install, custom_ignore, custom_add)
    if target is None or target == "chef_recipes":
        _provision_chef_recipes(pkg_install, custom_ignore)
    if target is None or target == "puppet_classes":
        _provision_puppet_classes(pkg_install, custom_ignore)
    if target is None or target == "brew":
        install_brew(flavor=flavor, automated=True)
    if target is None or target == "libraries":
        _do_library_installs(lib_install)
    if target is None or target == "post_install":
        env.edition.post_install(pkg_install=pkg_install)
        env.flavor.post_install()
    if target is None or target == "cleanup":
        _cleanup_space(env)
        if "is_ec2_image" in env and env.is_ec2_image.upper() in ["TRUE", "YES"]:
            _cleanup_ec2(env)

def _print_time_stats(action, event, prev_time=None):
    """ A convenience method for displaying time event during configuration.

    :type action: string
    :param action: Indicates type of action (eg, Config, Lib install, Pkg install)

    :type event: string
    :param event: The monitoring event (eg, start, stop)

    :type prev_time: datetime
    :param prev_time: A timeststamp of a previous event. If provided, duration between
                      the time the method is called and the time stamp is included in
                      the printout

    :rtype: datetime
    :return: A datetime timestamp of when the method was called
    """
    time = datetime.utcnow()
    s = "{0} {1} time: {2}".format(action, event, time)
    if prev_time: s += "; duration: {0}".format(str(time-prev_time))
    env.logger.info(s)
    return time

def _check_fabric_version():
    """Checks for fabric version installed
    """
    version = env.version
    if int(version.split(".")[0]) < 1:
        raise NotImplementedError("Please install fabric version 1 or higher")

def _custom_installs(to_install, ignore=None, add=None):
    if not env.safe_exists(env.local_install) and env.local_install:
        env.safe_run("mkdir -p %s" % env.local_install)
    pkg_config = get_config_file(env, "custom.yaml").base
    packages, pkg_to_group = _yaml_to_packages(pkg_config, to_install)
    packages = [p for p in packages if ignore is None or p not in ignore]
    if add is not None:
        for key, vals in add.iteritems():
            for v in vals:
                pkg_to_group[v] = key
                packages.append(v)
    for p in env.flavor.rewrite_config_items("custom", packages):
        install_custom(p, True, pkg_to_group)


def _provision_chef_recipes(to_install, ignore=None):
    """
    Much like _custom_installs, read config file, determine what to install,
    and install it.
    """
    pkg_config = get_config_file(env, "chef_recipes.yaml").base
    packages, _ = _yaml_to_packages(pkg_config, to_install)
    packages = [p for p in packages if ignore is None or p not in ignore]
    recipes = [recipe for recipe in env.flavor.rewrite_config_items("chef_recipes", packages)]
    if recipes:  # Don't bother running chef if nothing to configure
        install_chef_recipe(recipes, True)


def _provision_puppet_classes(to_install, ignore=None):
    """
    Much like _custom_installs, read config file, determine what to install,
    and install it.
    """
    pkg_config = get_config_file(env, "puppet_classes.yaml").base
    packages, _ = _yaml_to_packages(pkg_config, to_install)
    packages = [p for p in packages if ignore is None or p not in ignore]
    classes = [recipe for recipe in env.flavor.rewrite_config_items("puppet_classes", packages)]
    if classes:  # Don't bother running chef if nothing to configure
        install_puppet_class(classes, True)


def install_chef_recipe(recipe, automated=False, flavor=None):
    """Install one or more chef recipes by name.

    Usage: fab [-i key] [-u user] -H host install_chef_recipe:recipe

    :type recipe:  string or list
    :param recipe: TODO

    :type automated:  bool
    :param automated: If set to True, the environment is not loaded.
    """
    _setup_logging(env)
    if not automated:
        _configure_fabric_environment(env, flavor)

    time_start = _print_time_stats("Chef provision for recipe(s) '{0}'".format(recipe), "start")
    _configure_chef(env, chef)
    recipes = recipe if isinstance(recipe, list) else [recipe]
    for recipe_to_add in recipes:
        chef.add_recipe(recipe_to_add)
    _chef_provision(env, recipes)
    _print_time_stats("Chef provision for recipe(s) '%s'" % recipe, "end", time_start)


def install_puppet_class(classes, automated=False, flavor=None):
    """Install one or more puppet classes by name.

    Usage: fab [-i key] [-u user] -H host install_puppet_class:class

    :type classes:  string or list
    :param classes: TODO

    :type automated:  bool
    :param automated: If set to True, the environment is not loaded.
    """
    _setup_logging(env)
    if not automated:
        _configure_fabric_environment(env, flavor)

    time_start = _print_time_stats("Puppet provision for class(es) '{0}'".format(classes), "start")
    classes = classes if isinstance(classes, list) else [classes]
    _puppet_provision(env, classes)
    _print_time_stats("Puppet provision for classes(s) '%s'" % classes, "end", time_start)


def install_custom(p, automated=False, pkg_to_group=None, flavor=None):
    """
    Install a single custom program or package by name.

    This method fetches program name from ``config/custom.yaml`` and delegates
    to a method in ``custom/*name*.py`` to proceed with the installation.
    Alternatively, if a program install method is defined in the appropriate
    package, it will be called directly (see param ``p``).

    Usage: fab [-i key] [-u user] -H host install_custom:program_name

    :type p:  string
    :param p: A name of the custom program to install. This has to be either a name
              that is listed in ``custom.yaml`` as a subordinate to a group name or a
              program name whose install method is defined in either ``cloudbio`` or
              ``custom`` packages
              (e.g., ``cloudbio/custom/cloudman.py -> install_cloudman``).

    :type automated:  bool
    :param automated: If set to True, the environment is not loaded and reading of
                      the ``custom.yaml`` is skipped.
    """
    p = p.lower() # All packages listed in custom.yaml are in lower case
    if not automated:
        _setup_logging(env)
        _configure_fabric_environment(env, flavor, ignore_distcheck=True)
        pkg_config = get_config_file(env, "custom.yaml").base
        packages, pkg_to_group = _yaml_to_packages(pkg_config, None)
    time_start = _print_time_stats("Custom install for '{0}'".format(p), "start")
    fn = _custom_install_function(env, p, pkg_to_group)
    fn(env)
    ## TODO: Replace the previous 4 lines with the following one, barring
    ## objections. Slightly different behavior because pkg_to_group will be
    ## loaded regardless of automated if it is None, but IMO this shouldn't
    ## matter because the following steps look like they would fail if
    ## automated is True and pkg_to_group is None.
    # _install_custom(p, pkg_to_group)
    _print_time_stats("Custom install for '%s'" % p, "end", time_start)


def _install_custom(p, pkg_to_group=None):
    if pkg_to_group is None:
        pkg_config = get_config_file(env, "custom.yaml").base
        packages, pkg_to_group = _yaml_to_packages(pkg_config, None)
    fn = _custom_install_function(env, p, pkg_to_group)
    fn(env)

def install_brew(p=None, version=None, flavor=None, automated=False):
    """Top level access to homebrew/linuxbrew packages.
    p is a package name to install, or all configured packages if not specified.
    """
    if not automated:
        _setup_logging(env)
        _configure_fabric_environment(env, flavor, ignore_distcheck=True)
    if p is not None:
        if version:
            p = "%s==%s" % (p, version)
        brew.install_packages(env, packages=[p])
    else:
        pkg_install = _read_main_config()[0]
        brew.install_packages(env, to_install=pkg_install)

def _custom_install_function(env, p, pkg_to_group):
    """
    Find custom install function to execute based on package name to
    pkg_to_group dict.
    """
    try:
        # Allow direct calling of a program install method, even if the program
        # is not listed in the custom list (ie, not contained as a key value in
        # pkg_to_group). For an example, see 'install_cloudman' or use p=cloudman.
        mod_name = pkg_to_group[p] if p in pkg_to_group else p
        env.logger.debug("Importing module cloudbio.custom.%s" % mod_name)
        mod = __import__("cloudbio.custom.%s" % mod_name,
                         fromlist=["cloudbio", "custom"])
    except ImportError:
        raise ImportError("Need to write module cloudbio.custom.%s" %
                pkg_to_group[p])
    replace_chars = ["-"]
    try:
        for to_replace in replace_chars:
            p = p.replace(to_replace, "_")
        env.logger.debug("Looking for custom install function %s.install_%s"
            % (mod.__name__, p))
        fn = getattr(mod, "install_%s" % p)
    except AttributeError:
        raise ImportError("Need to write a install_%s function in custom.%s"
                % (p, pkg_to_group[p]))
    return fn


def _read_main_config():
    """Pull a list of groups to install based on our main configuration YAML.

    Reads 'main.yaml' and returns packages and libraries
    """
    yaml_file = get_config_file(env, "main.yaml").base
    with open(yaml_file) as in_handle:
        full_data = yaml.load(in_handle)
    packages = full_data.get('packages', [])
    packages = env.edition.rewrite_config_items("main_packages", packages)
    libraries = full_data.get('libraries', [])
    custom_ignore = full_data.get('custom_ignore', [])
    custom_add = full_data.get("custom_additional")
    if packages is None: packages = []
    if libraries is None: libraries = []
    if custom_ignore is None: custom_ignore = []
    env.logger.info("Meta-package information from {2}\n- Packages: {0}\n- Libraries: "
            "{1}".format(",".join(packages), ",".join(libraries), yaml_file))
    return packages, sorted(libraries), custom_ignore, custom_add

# ### Library specific installation code

def _python_library_installer(config):
    """Install python specific libraries using pip, conda and easy_install.
    Handles using isolated anaconda environments.
    """
    if shared._is_anaconda(env):
        conda_bin = shared._conda_cmd(env)
        for pname in env.flavor.rewrite_config_items("python", config.get("conda", [])):
            env.safe_run("{0} install --yes {1}".format(conda_bin, pname))
        cmd = env.safe_run
        with settings(warn_only=True):
            cmd("%s -U distribute" % os.path.join(os.path.dirname(conda_bin), "easy_install"))
    else:
        pip_bin = shared._pip_cmd(env)
        ei_bin = pip_bin.replace("pip", "easy_install")
        env.safe_sudo("%s -U pip" % ei_bin)
        with settings(warn_only=True):
            env.safe_sudo("%s -U distribute" % ei_bin)
        cmd = env.safe_sudo
    for pname in env.flavor.rewrite_config_items("python", config['pypi']):
        cmd("{0} install --upgrade {1} --allow-unverified {1} --allow-external {1}".format(shared._pip_cmd(env), pname)) # fixes problem with packages not being in pypi

def _ruby_library_installer(config):
    """Install ruby specific gems.
    """
    gem_ext = getattr(env, "ruby_version_ext", "")
    def _cur_gems():
        with settings(
                hide('warnings', 'running', 'stdout', 'stderr')):
            gem_info = env.safe_run_output("gem%s list --no-versions" % gem_ext)
        return [l.rstrip("\r") for l in gem_info.split("\n") if l.rstrip("\r")]
    installed = _cur_gems()
    for gem in env.flavor.rewrite_config_items("ruby", config['gems']):
        # update current gems only to check for new installs
        if gem not in installed:
            installed = _cur_gems()
        if gem in installed:
            env.safe_sudo("gem%s update %s" % (gem_ext, gem))
        else:
            env.safe_sudo("gem%s install %s" % (gem_ext, gem))

def _perl_library_installer(config):
    """Install perl libraries from CPAN with cpanminus.
    """
    with shared._make_tmp_dir() as tmp_dir:
        with cd(tmp_dir):
            env.safe_run("wget --no-check-certificate -O cpanm "
                         "https://raw.github.com/miyagawa/cpanminus/master/cpanm")
            env.safe_run("chmod a+rwx cpanm")
            env.safe_sudo("mv cpanm %s/bin" % env.system_install)
    sudo_str = "--sudo" if env.use_sudo else ""
    for lib in env.flavor.rewrite_config_items("perl", config['cpan']):
        # Need to hack stdin because of some problem with cpanminus script that
        # causes fabric to hang
        # http://agiletesting.blogspot.com/2010/03/getting-past-hung-remote-processes-in.html
        env.safe_run("cpanm %s --skip-installed --notest %s < /dev/null" % (sudo_str, lib))

def _haskell_library_installer(config):
    """Install haskell libraries using cabal.
    """
    run("cabal update")
    for lib in config["cabal"]:
        sudo_str = "--root-cmd=sudo" if env.use_sudo else ""
        env.safe_run("cabal install %s --global %s" % (sudo_str, lib))

lib_installers = {
    "r-libs" : libraries.r_library_installer,
    "python-libs" : _python_library_installer,
    "ruby-libs" : _ruby_library_installer,
    "perl-libs" : _perl_library_installer,
    "haskell-libs": _haskell_library_installer,
    }

def install_libraries(language):
    """High level target to install libraries for a specific language.
    """
    _setup_logging(env)
    _check_fabric_version()
    _configure_fabric_environment(env, ignore_distcheck=True)
    _do_library_installs(["%s-libs" % language])

def _do_library_installs(to_install):
    for iname in to_install:
        yaml_file = get_config_file(env, "%s.yaml" % iname).base
        with open(yaml_file) as in_handle:
            config = yaml.load(in_handle)
        lib_installers[iname](config)

########NEW FILE########
__FILENAME__ = ec2autorun
#!/usr/bin/env python
"""
This is a contextualization script required by CloudMan; it is automatically run
at instance startup (via an upstart job).

Requires:
    PyYAML http://pyyaml.org/wiki/PyYAMLDocumentation (easy_install pyyaml)
    boto http://code.google.com/p/boto/ (easy_install boto)

Assumptions:
    DEFAULT_BUCKET_NAME and DEFAULT_BOOT_SCRIPT_NAME are publicly accessible and
    do not require any form of authentication
"""

import os, sys, yaml, urllib2, logging, hashlib, time, subprocess, random
from urlparse import urlparse

from boto.s3.key import Key
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from boto.s3.connection import OrdinaryCallingFormat

logging.getLogger('boto').setLevel(logging.INFO) # Only log boto messages >=INFO
log = None

USER_DATA_URL = 'http://169.254.169.254/latest/user-data'
# USER_DATA_URL = 'http://userwww.service.emory.edu/~eafgan/content/userData.yaml.sample' # used for testing
# USER_DATA_URL = 'http://userwww.service.emory.edu/~eafgan/content/url_ud.txt' # used for testing
LOCAL_PATH = '/tmp/cm' # Local path destination used for storing/reading any files created by this script
USER_DATA_FILE_NAME = 'userData.yaml' # Local file with user data formatted by this script
USER_DATA_FILE = os.path.join(LOCAL_PATH, USER_DATA_FILE_NAME) # The final/processed UD file
# Local file containing UD in its original format
USER_DATA_ORIG = os.path.join(LOCAL_PATH, 'original_%s' % USER_DATA_FILE_NAME)
SERVICE_ROOT = 'http://s3.amazonaws.com/' # Obviously, customized for Amazon's S3
DEFAULT_BUCKET_NAME = 'cloudman' # Ensure this bucket is accessible to anyone!
DEFAULT_BOOT_SCRIPT_NAME = 'cm_boot.py' # Ensure this file is accessible to anyone in the public bucket!
CLOUDMAN_HOME = '/mnt/cm'

# ====================== Utility methods ======================

def _setup_logging():
    # Logging setup
    formatter = logging.Formatter("[%(levelname)s] %(module)s:%(lineno)d %(asctime)s: %(message)s")
    console = logging.StreamHandler() # log to console - used during testing
    # console.setLevel(logging.INFO) # accepts >INFO levels
    console.setFormatter(formatter)
    # log_file = logging.FileHandler(os.path.join(LOCAL_PATH, "%s.log" % os.path.splitext(sys.argv[0])[0]), 'w')
    # log_file.setLevel(logging.DEBUG) # accepts all levels
    # log_file.setFormatter(formatter)
    log = logging.root
    log.addHandler(console)
    # log.addHandler(log_file)
    log.setLevel(logging.DEBUG)
    return log

def _get_user_data():
    ud = ''
    for i in range(0, 5):
          try:
              log.info("Getting user data from '%s', attempt %s" % (USER_DATA_URL, i))
              fp = urllib2.urlopen(USER_DATA_URL)
              ud = fp.read()
              fp.close()
              log.debug("Saving user data in its original format to file '%s'" % USER_DATA_ORIG)
              with open(USER_DATA_ORIG, 'w') as ud_orig:
                  ud_orig.write(ud)
              if ud:
                  log.debug("Got user data")
                  return ud
          except IOError:
              log.info("User data not found. Setting it to empty.")
              return ''
    # Used for testing
    # return 'http://s3.amazonaws.com/cloudman/cm_boot'
    # return ''
    # return "gc_dev1|<account_key>|<secret_key>|somePWD"
    # with open('sample.yaml') as ud_yaml:
    #     ud = ud_yaml.read()
    if ud == '':
        log.debug("Received empty/no user data")
    return ud

def _get_bucket_name(cluster_name, access_key):
    """Compose bucket name based on the user-provided cluster name and user access key"""
    m = hashlib.md5()
    m.update( cluster_name + access_key )
    return "cm-" + m.hexdigest()

def _isurl(path):
    """Test if path is a net location. Tests the scheme and netloc."""
    # BUG : URLs require a scheme string ('http://') to be used.
    #       www.google.com will fail.
    #       Should we prepend the scheme for those that don't have it and
    #       test that also?
    scheme, netloc, upath, uparams, uquery, ufrag = urlparse(path)
    return bool(scheme and netloc)

def _get_s3_conn(ud):
    try:
        if 'cloud_type' in ud and ud['cloud_type'] != 'ec2':
            # If the user has specified a cloud type other than EC2,
            # create an s3 connection using the info from their user data
            log.debug('Establishing boto S3 connection to a custom Object Store')
            try:
                s3_conn = S3Connection(aws_access_key_id=ud['access_key'],
                        aws_secret_access_key=ud['secret_key'],
                        is_secure=ud.get('is_secure', True),
                        host=ud.get('s3_host', ''),
                        port=ud.get('s3_port', 8888),
                        calling_format=OrdinaryCallingFormat(),
                        path=ud.get('s3_conn_path', '/'))
            except S3ResponseError, e:
                log.error("Trouble connecting to a custom Object Store. User data: {0}; Exception: {1}"\
                    .format(ud, e))
        else:
            # Use the default Amazon S3 connection
            log.debug('Establishing boto S3 connection to Amazon')
            s3_conn = S3Connection(ud['access_key'], ud['secret_key'])
    except Exception, e:
        log.error("Exception getting S3 connection: %s" % e)
        return None
    return s3_conn


def _bucket_exists(s3_conn, bucket_name):
    bucket = None
    for i in range(1, 6):
        try:
            # log.debug("Looking for bucket '%s'" % bucket_name)
            bucket = s3_conn.lookup(bucket_name)
            break
        except S3ResponseError:
            log.error ("Bucket '%s' not found, attempt %s/5" % (bucket_name, i+1))
            time.sleep(2)

    if bucket is not None:
        log.debug("Cluster bucket '%s' found." % bucket_name)
        return True
    else:
        log.debug("Cluster bucket '%s' not found." % bucket_name)
        return False

def _remote_file_exists(s3_conn, bucket_name, remote_filename):
    b = None
    for i in range(0, 5):
        try:
            b = s3_conn.get_bucket(bucket_name)
            break
        except S3ResponseError:
            log.error ("Problem connecting to bucket '%s', attempt %s/5" % (bucket_name, i))
            time.sleep(2)

    if b is not None:
        k = Key(b, remote_filename)
        if k.exists():
            return True
    return False

def _save_file_to_bucket(s3_conn, bucket_name, remote_filename, local_file, force=False):
    local_file = os.path.join(LOCAL_PATH, local_file)
    # log.debug( "Establishing handle with bucket '%s'..." % bucket_name)
    b = None
    for i in range(0, 5):
        try:
            b = s3_conn.get_bucket(bucket_name)
            break
        except S3ResponseError, e:
            log.error ("Problem connecting to bucket '%s', attempt %s/5" % (bucket_name, i))
            time.sleep(2)

    if b is not None:
        # log.debug("Establishing handle with key object '%s'..." % remote_filename)
        k = Key(b, remote_filename)
        if k.exists() and not force:
            log.debug("Remote file '%s' already exists. Not overwriting it." % remote_filename)
            return True
        log.debug( "Attempting to save local file '%s' to bucket '%s' as '%s'"
            % (local_file, bucket_name, remote_filename))
        try:
            k.set_contents_from_filename(local_file)
            log.info( "Successfully saved file '%s' to bucket '%s'." % (remote_filename, bucket_name))
            return True
        except S3ResponseError, e:
             log.error("Failed to save file local file '%s' to bucket '%s' as file '%s': %s"
                % (local_file, bucket_name, remote_filename, e))
             return False
    else:
        return False

def _get_file_from_bucket(s3_conn, bucket_name, remote_filename, local_filename):
    local_filename = os.path.join(LOCAL_PATH, local_filename)
    try:
        # log.debug("Establishing handle with bucket '%s'" % bucket_name)
        b = s3_conn.get_bucket(bucket_name)

        # log.debug("Establishing handle with file object '%s'" % remote_filename)
        k = Key(b, remote_filename)

        log.debug("Attempting to retrieve file '%s' from bucket '%s'" % (remote_filename, bucket_name))
        if k.exists():
            k.get_contents_to_filename(local_filename)
            log.info("Successfully retrieved file '%s' from bucket '%s' to '%s'."
                % (remote_filename, bucket_name, local_filename))
            return True
        else:
            log.error("File '%s' in bucket '%s' not found." % (remote_filename, bucket_name))
            return False
    except S3ResponseError, e:
        log.error("Failed to get file '%s' from bucket '%s': %s" % (remote_filename, bucket_name, e))
        return False

def _get_file_from_url(url):
    local_filename = os.path.join(LOCAL_PATH, os.path.split(url)[1])
    log.info("Getting boot script from '%s' and saving it locally to '%s'" % (url, local_filename))
    try:
        f = urllib2.urlopen(url)
        with open(local_filename, 'w') as local_file:
            local_file.write(f.read())
        os.chmod(local_filename, 0744)
        if f:
            log.debug("Got boot script from '%s'" % url)
            return True
        return False
    except IOError:
        log.error("Boot script at '%s' not found." % url)
        return False

def _get_boot_script(ud):
    # Test if cluster bucket exists; if it does not, resort to the default
    # bucket for downloading the boot script
    use_default_bucket = ud.get("use_default_bucket", False)
    if ud.has_key('bucket_default'):
        default_bucket_name = ud['bucket_default']
    else:
        default_bucket_name = DEFAULT_BUCKET_NAME
    if not use_default_bucket and ud.has_key('bucket_cluster') and ud['access_key'] is not None and ud['secret_key'] is not None:
        s3_conn = _get_s3_conn(ud)
        # Check if cluster bucket exists or use the default one
        if not _bucket_exists(s3_conn, ud['bucket_cluster']) or \
           not _remote_file_exists(s3_conn, ud['bucket_cluster'], ud['boot_script_name']):
            log.debug("Using default bucket '%s'" % default_bucket_name)
            use_default_bucket = True
        else:
            log.debug("Using cluster bucket '%s'" % ud['bucket_cluster'])
            use_default_bucket = False
    else:
        log.debug("bucket_clutser not specified or no credentials provided; defaulting to bucket '%s'"
            % default_bucket_name)
        use_default_bucket = True

    # If using cluster bucket, use credentials because the boot script may not be accessible to everyone
    got_boot_script = False
    if use_default_bucket is False:
        log.debug("Trying to get boot script '%s' from cluster bucket '%s'"
            % (ud['boot_script_name'], ud.get('bucket_cluster', None)))
        got_boot_script = _get_file_from_bucket(s3_conn, ud['bucket_cluster'], ud['boot_script_name'],
            DEFAULT_BOOT_SCRIPT_NAME)
        if got_boot_script:
            os.chmod(os.path.join(LOCAL_PATH, DEFAULT_BOOT_SCRIPT_NAME), 0744)
    # If did not get the boot script, fall back on the publicly available one
    if not got_boot_script or use_default_bucket:
        boot_script_url = os.path.join(_get_default_bucket_url(ud), ud.get('boot_script_name',
            DEFAULT_BOOT_SCRIPT_NAME))
        log.debug("Could not get boot script '%s' from cluster bucket '%s'; "
            "retrieving the public one from bucket url '%s'" \
            % (ud['boot_script_name'], ud.get('bucket_cluster', None), boot_script_url))
        got_boot_script = _get_file_from_url(boot_script_url)
    if got_boot_script:
        log.debug("Saved boot script to '%s'" % os.path.join(LOCAL_PATH, DEFAULT_BOOT_SCRIPT_NAME))
        # Save the downloaded boot script to cluster bucket for future invocations
        use_object_store = ud.get("use_object_store", True)
        if use_object_store and ud.has_key('bucket_cluster') and ud['bucket_cluster']:
            s3_conn = _get_s3_conn(ud)
            if _bucket_exists(s3_conn, ud['bucket_cluster']) and \
               not _remote_file_exists(s3_conn, ud['bucket_cluster'], ud['boot_script_name']):
                _save_file_to_bucket(s3_conn, ud['bucket_cluster'], ud['boot_script_name'], \
                    DEFAULT_BOOT_SCRIPT_NAME)
        return True
    log.debug("**Could not get the boot script**")
    return False

def _run_boot_script(boot_script_name):
    script = os.path.join(LOCAL_PATH, boot_script_name)
    log.info("Running boot script '%s'" % script)
    process = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        log.debug("Successfully ran boot script '%s'" % script)
        return True
    else:
        log.error("Error running boot script '%s'. Process returned code '%s' and following stderr: %s"
            % (script, process.returncode, stderr))
        return False

def _create_basic_user_data_file():
    # Create a basic YAML file that is expected by CloudMan
    with open(USER_DATA_FILE, 'w') as ud_file:
        ud_formatted = {'access_key': None,
                        'boot_script_name': DEFAULT_BOOT_SCRIPT_NAME,
                        'boot_script_path': LOCAL_PATH,
                        'bucket_default': DEFAULT_BUCKET_NAME,
                        'bucket_cluster': None,
                        'cloudman_home': CLOUDMAN_HOME,
                        'cluster_name': 'aGalaxyCloudManCluster_%s' % random.randrange(1, 9999999),
                        'role': 'master',
                        'secret_key': None}
        yaml.dump(ud_formatted, ud_file, default_flow_style=False)
    return ud_formatted

def _get_default_bucket_url(ud=None):
    if ud and ud.has_key('bucket_default'):
        default_bucket_name = ud['bucket_default']
    else:
        default_bucket_name = DEFAULT_BUCKET_NAME
    # TODO: Check if th bucket 'default_bucket_name' is accessible to everyone
    # because it is being accessed as a URL
    if ud:
        bucket_url = ud.get("default_bucket_url", None)
    else:
        bucket_url = None
    if not bucket_url:
        bucket_url = os.path.join(SERVICE_ROOT, default_bucket_name)
    log.debug("Default bucket url: %s" % bucket_url)
    return bucket_url

def _user_exists(username):
    """ Check if the given username exists as a system user
    """
    with open('/etc/passwd', 'r') as f:
        ep = f.read()
    return ep.find(username) > 0

def _allow_password_logins(passwd):
    for user in ["ubuntu", "galaxy"]:
        if _user_exists(user):
            log.info("Setting up password-based login for user '{0}'".format(user))
            p1 = subprocess.Popen(["echo", "%s:%s" % (user, passwd)], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["chpasswd"], stdin=p1.stdout, stdout=subprocess.PIPE)
            p1.stdout.close()
            p2.communicate()[0]
            cl = ["sed", "-i", "s/^PasswordAuthentication .*/PasswordAuthentication yes/",
                  "/etc/ssh/sshd_config"]
            subprocess.check_call(cl)
            cl = ["/usr/sbin/service", "ssh", "reload"]
            subprocess.check_call(cl)

def _handle_freenx(passwd):
    # Check if FreeNX is installed on the image before trying to configure it
    cl = "/usr/bin/dpkg --get-selections | /bin/grep freenx"
    retcode = subprocess.call(cl, shell=True)
    if retcode == 0:
        log.info("Setting up FreeNX")
        cl = ["dpkg-reconfigure", "-pcritical", "freenx-server"]
        # On slower/small instance types, there can be a conflict when running
        # debconf so try this a few times
        for i in range(5):
            retcode = subprocess.call(cl)
            if retcode == 0:
                break
            else:
                time.sleep(5)
    else:
        log.info("freenx-server is not installed; not configuring it")

# ====================== Actions methods ======================

def _handle_empty():
    log.info("Received empty user data; assuming default contextualization")
    _create_basic_user_data_file() # This file is expected by CloudMan
    # Get & run boot script
    file_url = os.path.join(_get_default_bucket_url(), DEFAULT_BOOT_SCRIPT_NAME)
    log.debug("Resorting to the default bucket to get the boot script: %s" % file_url)
    _get_file_from_url(file_url)
    _run_boot_script(DEFAULT_BOOT_SCRIPT_NAME)

def _handle_url(url):
    log.info("Handling user data provided URL: '%s'" % url)
    _get_file_from_url(url)
    boot_script_name = os.path.split(url)[1]
    _run_boot_script(boot_script_name)


#http://stackoverflow.com/questions/823196/yaml-merge-in-python
def _merge(specific, default):
    """
    Recursively merges two yaml produced data structures,
    a more specific input (`specific`) and defaults
    (`default`).
    """
    if isinstance(specific, dict) and isinstance(default, dict):
        for k, v in default.iteritems():
            if k not in specific:
                specific[k] = v
            else:
                specific[k] = _merge(specific[k], v)
    return specific

def _load_user_data(user_data):
    """ Loads user data into dict (using pyyaml). If machine image
    contains default data this is loaded and populated in resulting
    data structure as well. These separate options are merged using
    the `_merge` function above and priority is always given to
    user supplied options.
    """
    ud = yaml.load(user_data)
    if ud == user_data:
        # Bad user data, cannot merge default
        return ud
    default_user_data_path = \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'IMAGE_USER_DATA')
    if os.path.exists(default_user_data_path):
        image_ud = yaml.load(open(default_user_data_path, 'r').read())
        if image_ud:
            ud = _merge(ud, image_ud)
    return ud

def _handle_yaml(user_data):
    """ Process user data in YAML format"""
    log.info("Handling user data in YAML format.")
    ud = _load_user_data(user_data)
    # Handle bad user data as a string
    if ud == user_data:
        return _handle_empty()
    # Allow password based logins. Do so also in case only NX is being setup.
    if "freenxpass" in ud or "password" in ud:
        passwd = ud.get("freenxpass", None) or ud.get("password", None)
        _allow_password_logins(passwd)
    # Handle freenx passwords and the case with only a NX password sent
    if "freenxpass" in ud:
        _handle_freenx(ud["freenxpass"])
        if len(ud) == 1:
            return _handle_empty()
    # Create a YAML file from user data and store it as USER_DATA_FILE
    # This code simply ensures fields required by CloudMan are in the
    # created file. Any other fields that might be included as user data
    # are also included in the created USER_DATA_FILE
    if ud.get('no_start', None) is not None:
        log.info("Received 'no_start' user data option. Not doing anything else.")
        return
    if not ud.has_key('cluster_name'):
        log.warning("The provided user data should contain cluster_name field.")
        ud['cluster_name'] = 'aCloudManCluster_%s' % random.randrange(1, 9999999)
    elif ud['cluster_name'] == '':
        log.warning("The cluster_name field of user data should not be empty.")
        ud['cluster_name'] = 'aCloudManCluster_%s' % random.randrange(1, 9999999)

    if not ud.has_key('access_key'):
        log.info("The provided user data does not contain access_key field; setting it to None..")
        ud['access_key'] = None
    elif ud['access_key'] == '' or ud['access_key'] is None:
        log.warning("The access_key field of user data should not be empty; setting it to None.")
        ud['access_key'] = None

    if not ud.has_key('secret_key'):
        log.info("The provided user data does not contain secret_key field; setting it to None.")
        ud['secret_key'] = None
    elif ud['secret_key'] == '' or ud['secret_key'] is None:
        log.warning("The secret_key field of user data should not be empty; setting it to None.")
        ud['secret_key'] = None

    if not ud.has_key('password'):
        log.warning("The provided user data should contain password field.")
    elif ud['password'] == '':
        log.warning("The password field of user data should not be empty.")
    else: # ensure the password is a string
        ud['password'] = str(ud['password'])

    if not ud.has_key('bucket_default'):
        log.debug("The provided user data does not contain bucket_default field; setting it to '%s'."
            % DEFAULT_BUCKET_NAME)
        ud['bucket_default'] = DEFAULT_BUCKET_NAME
    elif ud['bucket_default'] == '':
        log.warning("The bucket_default field of user data was empty; setting it to '%s'."
            % DEFAULT_BUCKET_NAME)
        ud['bucket_default'] = DEFAULT_BUCKET_NAME

    if not ud.has_key('bucket_cluster'):
        if ud['access_key'] is not None and ud['secret_key'] is not None:
            ud['bucket_cluster'] = _get_bucket_name(ud['cluster_name'], ud['access_key'])

    if not ud.has_key('role'):
        ud['role'] = 'master'

    if not ud.has_key('cloudman_home'):
        ud['cloudman_home'] = CLOUDMAN_HOME

    if not ud.has_key('boot_script_name'):
        ud['boot_script_name'] = DEFAULT_BOOT_SCRIPT_NAME
    ud['boot_script_path'] = LOCAL_PATH # Marks where boot script was saved

    log.debug("Composed user data: %s" % ud)
    with open(USER_DATA_FILE, 'w') as ud_yaml:
        yaml.dump(ud, ud_yaml, default_flow_style=False)

    # Get & run boot script
    if _get_boot_script(ud):
        _run_boot_script(DEFAULT_BOOT_SCRIPT_NAME)

# ====================== Driver code ======================

def _parse_user_data(ud):
    if ud == '':
        _handle_empty()
    elif _isurl(ud):
        _handle_url(ud)
    else: # default to yaml
        _handle_yaml(ud)

def main():
    if not os.path.exists(LOCAL_PATH):
        os.mkdir(LOCAL_PATH)
    global log
    log = _setup_logging()
    ud = _get_user_data()
    _parse_user_data(ud)
    log.info("---> %s done <---" % sys.argv[0])

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ipython_config
# Configuration file for ipython.

c = get_config()

c.InteractiveShell.autoindent = True
c.InteractiveShell.colors = 'Linux'
c.InteractiveShell.confirm_exit = False
c.AliasManager.user_aliases = [
 ('ll', 'ls -l'),
 ('lt', 'ls -ltr'),
]

#------------------------------------------------------------------------------
# InteractiveShellApp configuration
#------------------------------------------------------------------------------

# A Mixin for applications that start InteractiveShell instances.
#
# Provides configurables for loading extensions and executing files as part of
# configuring a Shell environment.
#
# Provides init_extensions() and init_code() methods, to be called after
# init_shell(), which must be implemented by subclasses.

# Execute the given command string.
# c.InteractiveShellApp.code_to_run = ''

# lines of code to run at IPython startup.
# c.InteractiveShellApp.exec_lines = []

# If true, an 'import *' is done from numpy and pylab, when using pylab
# c.InteractiveShellApp.pylab_import_all = True

# A list of dotted module names of IPython extensions to load.
# c.InteractiveShellApp.extensions = []

# dotted module name of an IPython extension to load.
# c.InteractiveShellApp.extra_extension = ''

# List of files to run at IPython startup.
# c.InteractiveShellApp.exec_files = []

# A file to be run
# c.InteractiveShellApp.file_to_run = ''

#------------------------------------------------------------------------------
# TerminalIPythonApp configuration
#------------------------------------------------------------------------------

# TerminalIPythonApp will inherit config from: BaseIPythonApplication,
# Application, InteractiveShellApp

# Execute the given command string.
# c.TerminalIPythonApp.code_to_run = ''

# The IPython profile to use.
# c.TerminalIPythonApp.profile = u'default'

# Set the log level by value or name.
# c.TerminalIPythonApp.log_level = 30

# lines of code to run at IPython startup.
# c.TerminalIPythonApp.exec_lines = []

# Enable GUI event loop integration ('qt', 'wx', 'gtk', 'glut', 'pyglet').
# c.TerminalIPythonApp.gui = None

# Pre-load matplotlib and numpy for interactive use, selecting a particular
# matplotlib backend and loop integration.
# c.TerminalIPythonApp.pylab = None

# Suppress warning messages about legacy config files
# c.TerminalIPythonApp.ignore_old_config = False

# Create a massive crash report when IPython enconters what may be an internal
# error.  The default is to append a short message to the usual traceback
# c.TerminalIPythonApp.verbose_crash = False

# If a command or file is given via the command-line, e.g. 'ipython foo.py
# c.TerminalIPythonApp.force_interact = False

# If true, an 'import *' is done from numpy and pylab, when using pylab
# c.TerminalIPythonApp.pylab_import_all = True

# The name of the IPython directory. This directory is used for logging
# configuration (through profiles), history storage, etc. The default is usually
# $HOME/.ipython. This options can also be specified through the environment
# variable IPYTHON_DIR.
# c.TerminalIPythonApp.ipython_dir = u'/home/ubuntu/.ipython'

# Whether to display a banner upon starting IPython.
# c.TerminalIPythonApp.display_banner = True

# Start IPython quickly by skipping the loading of config files.
# c.TerminalIPythonApp.quick = False

# A list of dotted module names of IPython extensions to load.
# c.TerminalIPythonApp.extensions = []

# Whether to install the default config files into the profile dir. If a new
# profile is being created, and IPython contains config files for that profile,
# then they will be staged into the new directory.  Otherwise, default config
# files will be automatically generated.
# c.TerminalIPythonApp.copy_config_files = False

# dotted module name of an IPython extension to load.
# c.TerminalIPythonApp.extra_extension = ''

# List of files to run at IPython startup.
# c.TerminalIPythonApp.exec_files = []

# Whether to overwrite existing config files when copying
# c.TerminalIPythonApp.overwrite = False

# A file to be run
# c.TerminalIPythonApp.file_to_run = ''

#------------------------------------------------------------------------------
# TerminalInteractiveShell configuration
#------------------------------------------------------------------------------

# TerminalInteractiveShell will inherit config from: InteractiveShell

# auto editing of files with syntax errors.
# c.TerminalInteractiveShell.autoedit_syntax = False

# Use colors for displaying information about objects. Because this information
# is passed through a pager (like 'less'), and some pagers get confused with
# color codes, this capability can be turned off.
# c.TerminalInteractiveShell.color_info = True

#
# c.TerminalInteractiveShell.history_length = 10000

# Don't call post-execute functions that have failed in the past.
# c.TerminalInteractiveShell.disable_failing_post_execute = False

# Show rewritten input, e.g. for autocall.
# c.TerminalInteractiveShell.show_rewritten_input = True

# Set the color scheme (NoColor, Linux, or LightBG).
# c.TerminalInteractiveShell.colors = 'LightBG'

# Autoindent IPython code entered interactively.
# c.TerminalInteractiveShell.autoindent = True

#
# c.TerminalInteractiveShell.separate_in = '\n'

# Deprecated, use PromptManager.in2_template
# c.TerminalInteractiveShell.prompt_in2 = '   .\\D.: '

#
# c.TerminalInteractiveShell.separate_out = ''

# Deprecated, use PromptManager.in_template
# c.TerminalInteractiveShell.prompt_in1 = 'In [\\#]: '

# Enable deep (recursive) reloading by default. IPython can use the deep_reload
# module which reloads changes in modules recursively (it replaces the reload()
# function, so you don't need to change anything to use it). deep_reload()
# forces a full reload of modules whose code may have changed, which the default
# reload() function does not.  When deep_reload is off, IPython will use the
# normal reload(), but deep_reload will still be available as dreload().
# c.TerminalInteractiveShell.deep_reload = False

# Make IPython automatically call any callable object even if you didn't type
# explicit parentheses. For example, 'str 43' becomes 'str(43)' automatically.
# The value can be '0' to disable the feature, '1' for 'smart' autocall, where
# it is not applied if there are no more arguments on the line, and '2' for
# 'full' autocall, where all callable objects are automatically called (even if
# no arguments are present).
# c.TerminalInteractiveShell.autocall = 0

# Number of lines of your screen, used to control printing of very long strings.
# Strings longer than this number of lines will be sent through a pager instead
# of directly printed.  The default value for this is 0, which means IPython
# will auto-detect your screen size every time it needs to print certain
# potentially long strings (this doesn't change the behavior of the 'print'
# keyword, it's only triggered internally). If for some reason this isn't
# working well (it needs curses support), specify it yourself. Otherwise don't
# change the default.
# c.TerminalInteractiveShell.screen_length = 0

# Set the editor used by IPython (default to $EDITOR/vi/notepad).
# c.TerminalInteractiveShell.editor = 'vi'

# Deprecated, use PromptManager.justify
# c.TerminalInteractiveShell.prompts_pad_left = True

# The part of the banner to be printed before the profile
# c.TerminalInteractiveShell.banner1 = 'Python 2.7.1 (r271:86832, Jun 25 2011, 05:09:01) \nType "copyright", "credits" or "license" for more information.\n\nIPython 0.12 -- An enhanced Interactive Python.\n?         -> Introduction and overview of IPython\'s features.\n%quickref -> Quick reference.\nhelp      -> Python\'s own help system.\nobject?   -> Details about \'object\', use \'object??\' for extra details.\n'

#
# c.TerminalInteractiveShell.readline_parse_and_bind = ['tab: complete', '"\\C-l": clear-screen', 'set show-all-if-ambiguous on', '"\\C-o": tab-insert', '"\\C-r": reverse-search-history', '"\\C-s": forward-search-history', '"\\C-p": history-search-backward', '"\\C-n": history-search-forward', '"\\e[A": history-search-backward', '"\\e[B": history-search-forward', '"\\C-k": kill-line', '"\\C-u": unix-line-discard']

# The part of the banner to be printed after the profile
# c.TerminalInteractiveShell.banner2 = ''

#
# c.TerminalInteractiveShell.separate_out2 = ''

#
# c.TerminalInteractiveShell.wildcards_case_sensitive = True

#
# c.TerminalInteractiveShell.debug = False

# Set to confirm when you try to exit IPython with an EOF (Control-D in Unix,
# Control-Z/Enter in Windows). By typing 'exit' or 'quit', you can force a
# direct exit without any confirmation.
# c.TerminalInteractiveShell.confirm_exit = True

#
# c.TerminalInteractiveShell.ipython_dir = ''

#
# c.TerminalInteractiveShell.readline_remove_delims = '-/~'

# Start logging to the default log file.
# c.TerminalInteractiveShell.logstart = False

# The name of the logfile to use.
# c.TerminalInteractiveShell.logfile = ''

# The shell program to be used for paging.
# c.TerminalInteractiveShell.pager = 'less'

# Enable magic commands to be called without the leading %.
# c.TerminalInteractiveShell.automagic = True

# Save multi-line entries as one entry in readline history
# c.TerminalInteractiveShell.multiline_history = True

#
# c.TerminalInteractiveShell.readline_use = True

# Start logging to the given file in append mode.
# c.TerminalInteractiveShell.logappend = ''

#
# c.TerminalInteractiveShell.xmode = 'Context'

#
# c.TerminalInteractiveShell.quiet = False

# Enable auto setting the terminal title.
# c.TerminalInteractiveShell.term_title = False

#
# c.TerminalInteractiveShell.object_info_string_level = 0

# Deprecated, use PromptManager.out_template
# c.TerminalInteractiveShell.prompt_out = 'Out[\\#]: '

# Set the size of the output cache.  The default is 1000, you can change it
# permanently in your config file.  Setting it to 0 completely disables the
# caching system, and the minimum value accepted is 20 (if you provide a value
# less than 20, it is reset to 0 and a warning is issued).  This limit is
# defined because otherwise you'll spend more time re-flushing a too small cache
# than working
# c.TerminalInteractiveShell.cache_size = 1000

# Automatically call the pdb debugger after every exception.
# c.TerminalInteractiveShell.pdb = False

#------------------------------------------------------------------------------
# PromptManager configuration
#------------------------------------------------------------------------------

# This is the primary interface for producing IPython's prompts.

# Output prompt. '\#' will be transformed to the prompt number
# c.PromptManager.out_template = 'Out[\\#]: '

# Continuation prompt.
# c.PromptManager.in2_template = '   .\\D.: '

# If True (default), each prompt will be right-aligned with the preceding one.
# c.PromptManager.justify = True

# Input prompt.  '\#' will be transformed to the prompt number
# c.PromptManager.in_template = 'In [\\#]: '

#
# c.PromptManager.color_scheme = 'Linux'

#------------------------------------------------------------------------------
# ProfileDir configuration
#------------------------------------------------------------------------------

# An object to manage the profile directory and its resources.
#
# The profile directory is used by all IPython applications, to manage
# configuration, logging and security.
#
# This object knows how to find, create and manage these directories. This
# should be used by any code that wants to handle profiles.

# Set the profile location directly. This overrides the logic used by the
# `profile` option.
# c.ProfileDir.location = u''

#------------------------------------------------------------------------------
# PlainTextFormatter configuration
#------------------------------------------------------------------------------

# The default pretty-printer.
#
# This uses :mod:`IPython.external.pretty` to compute the format data of the
# object. If the object cannot be pretty printed, :func:`repr` is used. See the
# documentation of :mod:`IPython.external.pretty` for details on how to write
# pretty printers.  Here is a simple example::
#
#     def dtype_pprinter(obj, p, cycle):
#         if cycle:
#             return p.text('dtype(...)')
#         if hasattr(obj, 'fields'):
#             if obj.fields is None:
#                 p.text(repr(obj))
#             else:
#                 p.begin_group(7, 'dtype([')
#                 for i, field in enumerate(obj.descr):
#                     if i > 0:
#                         p.text(',')
#                         p.breakable()
#                     p.pretty(field)
#                 p.end_group(7, '])')

# PlainTextFormatter will inherit config from: BaseFormatter

#
# c.PlainTextFormatter.type_printers = {}

#
# c.PlainTextFormatter.newline = '\n'

#
# c.PlainTextFormatter.float_precision = ''

#
# c.PlainTextFormatter.verbose = False

#
# c.PlainTextFormatter.deferred_printers = {}

#
# c.PlainTextFormatter.pprint = True

#
# c.PlainTextFormatter.max_width = 79

#
# c.PlainTextFormatter.singleton_printers = {}

#------------------------------------------------------------------------------
# IPCompleter configuration
#------------------------------------------------------------------------------

# Extension of the completer class with IPython-specific features

# IPCompleter will inherit config from: Completer

# Instruct the completer to omit private method names
#
# Specifically, when completing on ``object.<tab>``.
#
# When 2 [default]: all names that start with '_' will be excluded.
#
# When 1: all 'magic' names (``__foo__``) will be excluded.
#
# When 0: nothing will be excluded.
# c.IPCompleter.omit__names = 2

# Whether to merge completion results into a single list
#
# If False, only the completion results from the first non-empty completer will
# be returned.
# c.IPCompleter.merge_completions = True

# Activate greedy completion
#
# This will enable completion on elements of lists, results of function calls,
# etc., but can be unsafe because the code is actually evaluated on TAB.
# c.IPCompleter.greedy = False

########NEW FILE########
__FILENAME__ = cbl_installed_software
#!/usr/bin/env python
"""Provide dump of software and libraries installed on CloudBioLinux image.

Run from the top level of the cloudbiolinux source directory:
    python utils/cbl_installed_software.py
"""
import os

from cloudbio import manifest

def main():
    out_dir = os.path.join(os.getcwd(), "manifest")
    manifest.create(out_dir)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = convert_to_xz
#!/usr/bin/env python
"""Convert gzipped files on s3 biodata to xz compression format.

This conversion is designed to save time and space for download.

Some download utilities to speed things up:
axel, aria2, lftp
"""
import os
import sys
import socket
import subprocess

import boto
import fabric.api as fabric

def main(bucket_name):
    conn = boto.connect_s3()
    bucket = conn.get_bucket("biodata")
    for s3_item in bucket.list("genomes/"):
        if s3_item.name.endswith(".gz"):
            print "xzipping", s3_item.name
            local_file = os.path.basename(s3_item.name)
            local_xz = "%s.xz" % os.path.splitext(local_file)[0]
            if not os.path.exists(local_xz):
                if not os.path.exists(local_file):
                    download_parallel(s3_item.generate_url(7200))
                    #s3_item.get_contents_to_filename(local_file)
                local_xz = gzip_to_xz(local_file)
            swap_s3_item(local_xz, bucket, s3_item)
            os.remove(local_xz)

def download_parallel(url):
    host = socket.gethostbyaddr(socket.gethostname())[0]
    user = os.environ["USER"]
    with fabric.settings(host_string="%s@%s" % (user, host)):
        ncores = fabric.run("cat /proc/cpuinfo | grep processor | wc -l")
        with fabric.cd(os.getcwd()):
            fabric.run("axel -a -n %s '%s'" % (ncores, url), shell=False)
            #fabric.run("aria2c -j %s -s %s '%s'" % (ncores, ncores, url),
            #           shell=False)

def swap_s3_item(xz_file, bucket, orig_s3_item):
    print " Uploading to S3"
    assert os.path.exists(xz_file)
    new_name = orig_s3_item.name.replace(".gz", ".xz")
    upload_script = os.path.join(os.path.dirname(__file__), "s3_multipart_upload.py")
    cl = ["python2.6", upload_script, xz_file, bucket.name, new_name]
    subprocess.check_call(cl)
    orig_s3_item.delete()

def gzip_to_xz(local_file):
    cl = ["gunzip", local_file]
    subprocess.check_call(cl)
    tar_file, _ = os.path.splitext(local_file)
    cl = ["xz", "-z", tar_file]
    subprocess.check_call(cl)
    return "%s.xz" % tar_file

if __name__ == "__main__":
    bucket_name = "biodata"
    main(bucket_name)

########NEW FILE########
__FILENAME__ = get_biolinux_packages
"""Scrape the Biolinux website to retrieve a list of packages they install.

http://www.jcvi.org/cms/research/projects/jcvi-cloud-biolinux/included-software

This needs to run on a machine with an apt system to check for the existance of
package names.
"""
import sys
import urllib2
import re
import subprocess
import StringIO

from BeautifulSoup import BeautifulSoup

def main():
    url = "http://www.jcvi.org/cms/research/projects/jcvi-cloud-biolinux/included-software"
    in_handle = urllib2.urlopen(url)
    soup = BeautifulSoup(in_handle)
    tables = soup.findAll("table", {"class": "contenttable"})
    to_check = []
    for t in tables:
        for row in soup.findAll("tr", {"class" : re.compile("tableRow.*")}):
            for i, item in enumerate(row.findAll("p", {"class": "bodytext"})):
                if i == 0:
                    to_check.append(str(item.contents[0]))
    to_check = list(set(to_check))
    packages = [get_package(n) for n in to_check]
    not_ported = [to_check[i] for i, p in enumerate(packages) if p is None]
    packages = [p for p in packages if p]
    print len(to_check), len(packages)
    with open("biolinux-packages.txt", "w") as out_handle:
        out_handle.write("\n".join(sorted(packages)))
    with open("biolinux-missing.txt", "w") as out_handle:
        out_handle.write("\n".join(sorted(not_ported)))

def get_package(pname):
    """Try and retrieve a standard or biolinux package for the package name.
    """
    # custom hacking for painfully general names that take forever
    if pname in ["act", "documentation"]:
        pname = "bio-linux-%s" % pname
    print 'In', pname
    cl = subprocess.Popen(["apt-cache", "search", pname], stdout=subprocess.PIPE)
    cl.wait()
    for line in cl.stdout.read().split():
        package = line.split()[0]
        if package == pname or package == "bio-linux-%s" % pname:
            print 'Out', package
            return package
    return None

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = get_yum_packages
"""Convert list of apt packages to matching yum packages.

This needs to run on a machine with yum to check for the existance of
package names.
"""
import os
import re
import sys
import subprocess
import platform
from contextlib import nested
import StringIO

def main(orig_file):
    new_file = "%s-yum%s" % os.path.splitext(orig_file)
    with nested(open(orig_file), open(new_file, "w")) as \
               (orig_handle, new_handle):
        for line in orig_handle:
            if line.lstrip().startswith("- "):
                base, orig_package = line.split("- ")
                yum_package = get_yum_package(orig_package.strip())
                if yum_package:
                    new_handle.write("%s- %s\n" % (base, yum_package))
            else:
                new_handle.write(line)

def get_yum_package(pname):
    print 'In', pname
    # hacks for package names that cause it to hang
    if pname in ["ri"]:
        return None
    elif pname in ["perl"]:
        return pname
    cl = subprocess.Popen(["yum", "search", pname], stdout=subprocess.PIPE)
    cl.wait()
    arch_pname = "%s.%s" % (pname, platform.machine())
    for line in cl.stdout.read().split("\n"):
        if line.startswith(arch_pname):
            return pname
    return None

if __name__ == "__main__":
    main(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = images_and_snapshots
import boto
import collections

OWNER = '678711657553' # Brad's owner ID

def images_and_snapshots(owner):
    """Retrieve Biolinux image and snapshot information.
    """
    conn = boto.connect_ec2()
    images = conn.get_all_images(owners=[owner])
    images32 = _sorted_images(images, "CloudBioLinux 32")
    images64 = _sorted_images(images, "CloudBioLinux 64")
    datalibs = _data_libraries(conn, owner)
    print images32
    print images64
    print datalibs

def _data_libraries(conn, owner):
    library_types = collections.defaultdict(list)
    snaps = conn.get_all_snapshots(owner=owner)
    for snap in snaps:
        if snap.description.startswith("CloudBioLinux Data"):
            # the type is everything except the start and date
            data_type = " ".join(snap.description.split()[2:-1])
            library_types[data_type].append(snap)
    final = dict()
    for name, snaps in library_types.iteritems():
        snaps = [(s.description, s) for s in snaps]
        snaps.sort(reverse=True)
        final[name] = [(s.id, d) for (d, s) in snaps]
    return final

def _sorted_images(images, start_name):
    """Retrieve a sorted list of images with most recent first.
    """
    images = [(i.name, i) for i in images if i.name.startswith(start_name)]
    images.sort(reverse=True)
    return [(i.id, name) for (name, i) in images]

images_and_snapshots(OWNER)

########NEW FILE########
__FILENAME__ = prepare_cosmic
#!/usr/bin/env python
"""Prepare combined VCF files of COSMIC resource for cancer variant calling.

http://cancer.sanger.ac.uk/cancergenome/projects/cosmic/
ftp://ngs.sanger.ac.uk/production/cosmic/
http://gatkforums.broadinstitute.org/discussion/2226/cosmic-and-dbsnp-files-for-mutect
"""
import os
import subprocess
import sys

FTP_DIR = "ftp://ngs.sanger.ac.uk/production/cosmic/"
VERSION = "v68"
BCBIO_NEXTGEN_BASE = "/usr/local"

def main():
    work_dir = "tmp-cosmic-GRCh37"
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    os.chdir(work_dir)
    ref_file = BCBIO_NEXTGEN_BASE + "/share/bcbio_nextgen/genomes/Hsapiens/GRCh37/seq/GRCh37.fa"
    fnames = [reorder_reference(x, ref_file) for x in get_cosmic_files()]
    grc_cosmic = combine_cosmic(fnames, ref_file)
    hg_cosmic = map_coords_to_ucsc(grc_cosmic, ref_file)
    for ready_file in [bgzip_vcf(x) for x in [grc_cosmic, hg_cosmic]]:
        upload_to_s3(ready_file)
        upload_to_s3(ready_file.replace(".gz", ".idx"))
        upload_to_s3(ready_file + ".tbi")

def upload_to_s3(fname):
    upload_script = os.path.join(os.path.dirname(__file__), "s3_multipart_upload.py")
    subprocess.check_call([sys.executable, upload_script, fname, "biodata",
                           "variants/%s" % os.path.basename(fname), "--public"])

def map_coords_to_ucsc(grc_cosmic, ref_file):
    hg19_ref_file = ref_file.replace("GRCh37", "hg19")
    out_file = grc_cosmic.replace("GRCh37.vcf", "hg19.vcf")
    if not os.path.exists(out_file):
        tmp_file = "%s-raw%s" % os.path.splitext(out_file)
        with open(tmp_file, "w") as out_handle:
            # header
            with open(grc_cosmic) as in_handle:
                for line in in_handle:
                    if line.startswith("#") and not line.startswith("##contig"):
                        out_handle.write(line)
            # chromsome M
            with open(grc_cosmic) as in_handle:
                for line in in_handle:
                    if line.startswith("MT"):
                        line = _rename_to_ucsc(line)
                        out_handle.write(line)
            # rest
            with open(grc_cosmic) as in_handle:
                for line in in_handle:
                    if not line.startswith(("MT", "#")):
                        line = _rename_to_ucsc(line)
                        out_handle.write(line)
        # Create clean VCF and index for upload
        subprocess.check_call(["gatk-framework", "-R", hg19_ref_file, "-T", "SelectVariants",
                               "--variant", tmp_file, "--out", out_file])
    return out_file

def _rename_to_ucsc(line):
    chrom, rest = line.split("\t", 1)
    if chrom == "MT":
        new_chrom = "chrM"
    else:
        new_chrom = "chr%s" % chrom
    return "%s\t%s" % (new_chrom, rest)

def combine_cosmic(fnames, ref_file):
    out_file = "cosmic-%s-GRCh37.vcf" % VERSION
    if not os.path.exists(out_file):
        cmd = ["gatk-framework", "-T", "CombineVariants", "-R", ref_file, "--out", out_file,
               "--suppressCommandLineHeader", "--setKey", "null"]
        for v in fnames:
            cmd += ["--variant", v]
        subprocess.check_call(cmd)
    return out_file

def reorder_reference(fname, ref_file):
    """Move mitochondrial calls to end to match GATK reference ordering.
    """
    out_file = "%s-prep%s" % os.path.splitext(fname)
    bcbiov_jar = BCBIO_NEXTGEN_BASE + "/share/java/bcbio_variation/bcbio.variation-0.1.6-SNAPSHOT-standalone.jar"
    if not os.path.exists(out_file):
        cmd = ["java", "-jar", bcbiov_jar, "variant-utils", "sort-vcf", fname, ref_file, ""]
        subprocess.check_call(cmd)
    return out_file

def get_cosmic_files():
    fnames = []
    for ctype in ["CodingMuts", "NonCodingVariants"]:
        to_get = "%sCosmic%s_%s.vcf.gz" % (FTP_DIR, ctype, VERSION)
        fname_gz = os.path.basename(to_get)
        fname = os.path.splitext(fname_gz)[0]
        if not os.path.exists(fname):
            if not os.path.exists(fname_gz):
                subprocess.check_call(["wget", to_get])
            subprocess.check_call(["gunzip", fname_gz])
        fnames.append(fname)
    return fnames

def bgzip_vcf(in_file):
    out_file = in_file + ".gz"
    if not os.path.exists(out_file):
        subprocess.check_call("bgzip -c %s > %s" % (in_file, out_file), shell=True)
    tabix_file = out_file + ".tbi"
    if not os.path.exists(tabix_file):
        subprocess.check_call(["tabix", "-p", "vcf", out_file])
    return out_file

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = prepare_dbsnp
"""Prepare sorted and consolidated dbSNP resources for mouse mm10/GRCh38 in VCF format.
"""
import datetime
import ftplib
import gzip
import os
import subprocess
from argparse import ArgumentParser
import re
import shutil

FTP = "ftp.ncbi.nih.gov"

REMOTES = {"mm10": "snp/organisms/mouse_10090/VCF",
           "canFam3": "snp/organisms/dog_9615/VCF/"}

def main(org):
    work_dir = "tmp-dbsnp-%s" % org
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    conn = ftplib.FTP(FTP, "anonymous", "me@example.com")
    conn.cwd(REMOTES[org])

    os.chdir(work_dir)
    files = []
    def add_files(x):
        if x.endswith("vcf.gz"):
            files.append(get_file(x, REMOTES[org], conn))
    conn.retrlines("NLST", add_files)
    out_file = "%s-dbSNP-%s.vcf" % (org, datetime.datetime.now().strftime("%Y-%m-%d"))
    with open(out_file, "w") as out_handle:
        for i, f in enumerate(karyotype_sort(files)):
            with gzip.open(f) as in_handle:
                for line in in_handle:
                    if line.startswith("#"):
                        if i == 0:
                            out_handle.write(line)
                    else:
                        out_handle.write("\t".join(fix_info(fix_chrom(line.rstrip().split("\t")))) + "\n")
    subprocess.check_call(["bgzip", out_file])
    shutil.move(out_file + ".gz", os.path.join(os.pardir, out_file + ".gz"))
    os.chdir(os.pardir)
    subprocess.check_call(["tabix", "-p", "vcf", out_file + ".gz"])
    shutil.rmtree(work_dir)

multi_whitespace = re.compile(r"\s+")

def fix_info(parts):
    """Fix the INFO file to remove whitespace.
    """
    parts[7] = multi_whitespace.sub("_", parts[7])
    return parts

def fix_chrom(parts):
    MAX_CHROMOSOMES = 50
    if parts[0] in [str(x) for x in range(1, MAX_CHROMOSOMES)] + ["X", "Y"]:
        new_chrom = "chr%s" % parts[0]
    elif parts[0] == "MT":
        new_chrom = "chrM"
    else:
        raise NotImplementedError(parts)
    parts[0] = new_chrom
    return parts

def get_file(x, ftp_dir, conn):
    if not os.path.exists(x):
        print "Retrieving %s" % x
        with open(x, "wb") as out_handle:
            conn = ftplib.FTP(FTP, "anonymous", "me@example.com")
            conn.cwd(ftp_dir)
            conn.retrbinary("RETR %s" % x, out_handle.write)
    return x

def karyotype_sort(xs):
    """Sort in karyotypic order to work with GATK's defaults.
    """
    def karyotype_keyfn(x):
        for suffix in [".gz"]:
            if x.endswith(suffix):
                x = x[:-len(suffix)]
        base = os.path.splitext(os.path.basename(x))[0]
        for prefix in ["chr", "vcf_chr_"]:
            if base.startswith(prefix):
                base = base[len(prefix):]
        parts = base.split("_")
        try:
            parts[0] =  int(parts[0])
        except ValueError:
            pass
        # unplaced at the very end
        if isinstance(parts[0], basestring) and parts[0].startswith(("Un", "Alt", "Multi", "NotOn")):
            parts.insert(0, "z")
        # mitochondrial special case -- after X/Y
        elif parts[0] in ["M", "MT"]:
            parts.insert(0, "x")
        # sort random and extra chromosomes after M
        elif len(parts) > 1:
            parts.insert(0, "y")
        return parts
    return sorted(xs, key=karyotype_keyfn)

if __name__ == "__main__":
    parser = ArgumentParser(description="Prepare a dbSNP file from NCBI.")
    parser.add_argument("org_build", choices=REMOTES.keys(),
                        help="genome build")
    args = parser.parse_args()
    main(args.org_build)

########NEW FILE########
__FILENAME__ = prepare_tx_gff
#!/usr/bin/env python
"""Prepare GFF transcript files for use as input to RNA-seq pipelines

Usage, from within the main genome directory of your organism:
  prepare_tx_gff.py <org_build>

requires these python packages which may not be installed
---------------------------------------------------------
mysql-python (via conda)
pandas (via conda)

"""
import os
import sys
import shutil
import collections
import datetime
import subprocess
import tempfile
import glob
from argparse import ArgumentParser

import gffutils

try:
    import MySQLdb
except:
    MySQLdb = None


from bcbio.utils import chdir, safe_makedir, file_exists


# ##  Version and retrieval details for Ensembl and UCSC
ensembl_release = "74"
base_ftp = "ftp://ftp.ensembl.org/pub/release-{release}/gtf"

# taxname:
# biomart_name: name of ensembl gene_id on biomart
# ucsc_map:
# fbase: the base filename for ensembl files using this genome

Build = collections.namedtuple("Build", ["taxname", "biomart_name",
                                         "ucsc_map", "fbase"])

def ucsc_ensembl_map_via_download(org_build):
    ensembl_dict_file = get_ensembl_dict(org_build)
    ucsc_dict_file = get_ucsc_dict(org_build)
    ensembl_dict = parse_sequence_dict(ensembl_dict_file)
    ucsc_dict = parse_sequence_dict(ucsc_dict_file)
    return ensembl_to_ucsc(ensembl_dict, ucsc_dict)

def ensembl_to_ucsc(ensembl_dict, ucsc_dict):
    name_map = {}
    for md5, name in ensembl_dict.items():
        name_map[name] = ucsc_dict.get(md5, None)
    return name_map

def ucsc_ensembl_map_via_query(org_build):
    """Retrieve UCSC to Ensembl name mappings from UCSC MySQL database.
    """
    # if MySQLdb is not installed, figure it out via download
    if not MySQLdb:
        return ucsc_ensembl_map_via_download(org_build)

    db = MySQLdb.connect(host=ucsc_db, user=ucsc_user, db=org_build)
    cursor = db.cursor()
    cursor.execute("select * from ucscToEnsembl")
    ucsc_map = {}
    for ucsc, ensembl in cursor.fetchall():
        # workaround for GRCh37/hg19 additional haplotype contigs.
        # Coordinates differ between builds so do not include these regions.
        if org_build == "hg19" and "hap" in ucsc:
            continue
        else:
            ucsc_map[ensembl] = ucsc
    return ucsc_map


build_info = {
    "hg19": Build("homo_sapiens", "hsapiens_gene_ensembl",
                  ucsc_ensembl_map_via_query,
                  "Homo_sapiens.GRCh37." + ensembl_release),
    "mm9": Build("mus_musculus", "mmusculus_gene_ensembl",
                 ucsc_ensembl_map_via_query,
                 "Mus_musculus.NCBIM37.67"),
    "mm10": Build("mus_musculus", "mmusculus_gene_ensembl",
                  ucsc_ensembl_map_via_query,
                  "Mus_musculus.GRCm38." + ensembl_release),
    "rn5": Build("rattus_norvegicus", None,
                 ucsc_ensembl_map_via_download,
                 "Rattus_norvegicus.Rnor_5.0." + ensembl_release),
    "GRCh37": Build("homo_sapiens", "hsapiens_gene_ensembl",
                    None,
                    "Homo_sapiens.GRCh37." + ensembl_release),
    "canFam3": Build("canis_familiaris", None,
                     ucsc_ensembl_map_via_download,
                     "Canis_familiaris.CanFam3.1." + ensembl_release)
}

ucsc_db = "genome-mysql.cse.ucsc.edu"
ucsc_user = "genome"


def parse_sequence_dict(fasta_dict):
    def _tuples_from_line(line):
        name = line.split("\t")[1].split(":")[1]
        md5 = line.split("\t")[4].split(":")[1]
        return md5, name
    with open(fasta_dict) as dict_handle:
        tuples = [_tuples_from_line(x) for x in dict_handle if "@SQ" in x]
        md5_dict = {x[0]: x[1] for x in tuples}
    return md5_dict

class SequenceDictParser(object):

    def __init__(self, fname):
        self.fname = fname

    def _get_sequences_in_genome_dict(self):
        with open(self.fname) as genome_handle:
            sequences = [self._sequence_from_line(x) for x in genome_handle if "@SQ" in x]
        return sequences

    def _sequence_from_line(self, line):
        name = line.split("\t")[1].split(":")[1]
        md5 = line.split("\t")[4].split(":")[1]
        return md5, name


def get_ensembl_dict(org_build):
    genome_dict = org_build + ".dict"
    if not os.path.exists(genome_dict):
        genome = _download_ensembl_genome(org_build)
        org_fa = org_build + ".fa"
        shutil.move(genome, org_fa)
        genome_dict = make_fasta_dict(org_fa)
    return genome_dict

def get_ucsc_dict(org_build):
    fa_dict = os.path.join(os.getcwd(), os.pardir, "seq", org_build + ".dict")
    if not file_exists(fa_dict):
        fa_file = os.path.splitext(fa_dict)[0] + ".fa"
        fa_dict = make_fasta_dict(fa_file)
    return fa_dict


def make_fasta_dict(fasta_file):
    dict_file = os.path.splitext(fasta_file)[0] + ".dict"
    if not os.path.exists(dict_file):
        picard_jar = os.path.join(PICARD_DIR, "CreateSequenceDictionary.jar")
        subprocess.check_call("java -jar {picard_jar} R={fasta_file} "
                              "O={dict_file}".format(**locals()), shell=True)
    return dict_file


def _download_ensembl_genome(org_build):
    build = build_info[org_build]
    fname = build.fbase + ".dna_sm.toplevel.fa.gz"
    dl_url = ("ftp://ftp.ensembl.org/pub/release-{release}/"
                   "fasta/{taxname}/dna/{fname}").format(release=ensembl_release,
                                                         taxname=build.taxname,
                                                         fname=fname)
    out_file = os.path.splitext(os.path.basename(dl_url))[0]
    if not os.path.exists(out_file):
        subprocess.check_call(["wget", dl_url])
        subprocess.check_call(["gunzip", os.path.basename(dl_url)])
    return out_file

def prepare_gff_db(gff_file):
    """
    make a database of a GTF file with gffutils
    """
    dbfn = gff_file + ".db"
    if not os.path.exists(dbfn):
        db = gffutils.create_db(gff_file, dbfn=dbfn, keep_order=False,
                                merge_strategy='merge', force=False,
                                infer_gene_extent=False)
    return dbfn

# ## Main driver functions

def main(org_build, gtf_file=None):
    work_dir = os.path.join(os.getcwd(), org_build, "tmpcbl")
    out_dir = os.path.join(os.getcwd(), org_build,
                           "rnaseq-%s" % datetime.datetime.now().strftime("%Y-%m-%d"))
    tophat_dir = os.path.join(out_dir, "tophat")
    safe_makedir(work_dir)
    with chdir(work_dir):
        if not gtf_file:
            build = build_info[org_build]
            gtf_file = prepare_tx_gff(build, org_build)
        db = prepare_gff_db(gtf_file)
        gtf_to_refflat(gtf_file)
        mask_gff = prepare_mask_gtf(gtf_file)
        rrna_gtf = prepare_rrna_gtf(gtf_file)
        gtf_to_interval(rrna_gtf, org_build)
        prepare_tophat_index(gtf_file, org_build)
        cleanup(work_dir, out_dir, org_build)
    tar_dirs = [out_dir]
    upload_to_s3(tar_dirs, org_build)


def cleanup(work_dir, out_dir, org_build):
    try:
        os.remove(os.path.join(work_dir, org_build + ".dict"))
        os.remove(os.path.join(work_dir, org_build + ".fa"))
    except:
        pass
    shutil.move(work_dir, out_dir)

def upload_to_s3(tar_dirs, org_build):
    str_tar_dirs = " ".join(os.path.relpath(d) for d in tar_dirs)
    tarball = "{org}-{dir}.tar.xz".format(org=org_build, dir=os.path.basename(tar_dirs[0]))
    if not os.path.exists(tarball):
        subprocess.check_call("tar -cvpf - {out_dir} | xz -zc - > {tarball}".format(
            out_dir=str_tar_dirs, tarball=tarball), shell=True)
    upload_script = os.path.join(os.path.dirname(__file__), "s3_multipart_upload.py")
    subprocess.check_call([sys.executable, upload_script, tarball, "biodata",
                           os.path.join("annotation", os.path.basename(tarball)),
                           "--public"])

def genepred_to_UCSC_table(genepred):
    header = ["#bin", "name", "chrom", "strand",
              "txStart", "txEnd", "cdsStart", "cdsEnd",
              "exonCount", "exonStarts", "exonEnds", "score",
              "name2", "cdsStartStat", "cdsEndStat",
              "exonFrames"]
    out_file = os.path.splitext(genepred)[0] + ".UCSCTable"
    if file_exists(out_file):
        return out_file
    with open(genepred) as in_handle, open(out_file, "w") as out_handle:
        counter = -1
        current_item = None
        out_handle.write("\t".join(header) + "\n")
        for l in in_handle:
            item = l.split("\t")[0]
            if current_item != item:
                current_item = item
                counter = counter + 1
            out_handle.write("\t".join([str(counter), l]))
    return out_file

def gtf_to_genepred(gtf):
    out_file = os.path.splitext(gtf)[0] + ".genePred"
    if file_exists(out_file):
        return out_file

    cmd = "gtfToGenePred -allErrors -genePredExt {gtf} {out_file}"
    subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

def gtf_to_refflat(gtf):
    out_file = os.path.splitext(gtf)[0] + ".refFlat"
    if file_exists(out_file):
        return out_file

    genepred = gtf_to_genepred(gtf)
    with open(genepred) as in_handle, open(out_file, "w") as out_handle:
        for l in in_handle:
            first = l.split("\t")[0]
            out_handle.write("\t".join([first, l]))

    return out_file

def make_miso_events(gtf, org_build):

    genepred = gtf_to_genepred(gtf)
    genepred = genepred_to_UCSC_table(genepred)
    pred_dir = tempfile.mkdtemp()
    miso_dir = os.path.join(os.path.dirname(gtf), "miso")
    tmp_pred = os.path.join(pred_dir, "ensGene.txt")
    os.symlink(os.path.abspath(genepred), tmp_pred)
    make_miso_annotation(pred_dir, miso_dir, org_build)

    gff_files = glob.glob(os.path.join(miso_dir, "commonshortest", "*.gff3"))

    cmd = "index_gff --index {f} {prefix}"

    for f in gff_files:
        prefix = f.split(".")[0] + "_indexed"
        if not file_exists(prefix):
            print prefix
            print f
            print cmd.format(**locals())
            subprocess.check_call(cmd.format(**locals()), shell=True)

def prepare_tophat_index(gtf, org_build):
    tophat_dir = os.path.abspath(os.path.join(os.path.dirname(gtf), "tophat",
                                              org_build + "_transcriptome"))
    bowtie_dir = os.path.abspath(os.path.join(os.path.dirname(gtf),
                                              os.path.pardir, "bowtie2",
                                              org_build))
    out_dir = tempfile.mkdtemp()
    fastq = _create_dummy_fastq()
    cmd = ("tophat --transcriptome-index {tophat_dir} -G {gtf} "
           "-o {out_dir} {bowtie_dir} {fastq}")
    subprocess.check_call(cmd.format(**locals()), shell=True)
    make_large_exons_gtf(gtf)
    shutil.rmtree(out_dir)
    os.remove(fastq)


def make_large_exons_gtf(gtf_file):
    """
    Save all exons > 1000 bases to a separate file for estimating the
    insert size distribution
    """
    out_dir = os.path.abspath(os.path.join(os.path.dirname(gtf_file), "tophat"))
    out_file = os.path.join(out_dir, "large_exons.gtf")

    if file_exists(out_file):
        return out_file

    dbfn = gtf_file + ".db"
    if not file_exists(dbfn):
        db = gffutils.create_db(gtf_file, dbfn=dbfn, keep_order=True,
                                merge_strategy='merge', force=False,
                                infer_gene_extent=False)
    else:
        db = gffutils.FeatureDB(dbfn)
    processed_count = 0
    kept_exons = []
    for exon in db.features_of_type('exon'):
        processed_count += 1
        if processed_count % 10000 == 0:
            print("Processed %d exons." % processed_count)
        if exon.end - exon.start > 1000:
            kept_exons.append(exon)

    with open(out_file, "w") as out_handle:
        print("Writing %d large exons to %s." % (processed_count,
                                                 out_file))
        for exon in kept_exons:
            out_handle.write(str(exon) + "\n")
    return out_file


def _create_dummy_fastq():
    read = ("@HWI-ST333_0178_FC:5:1101:1107:2112#ATCTCG/1\n"
            "GGNCTTTCCTGCTTCTATGTCTTGATCGCCTGTAGGCAGG\n"
            "+HWI-ST333_0178_FC:5:1101:1107:2112#ATCTCG/1\n"
            "[[BS\\a`ceeagfhhhhhaefhcdfhcf`efeg[cg_b__\n")
    fn = "dummy.fq"
    with open(fn, "w") as out_handle:
        out_handle.write(read)
    return fn

def gtf_to_interval(gtf, build):
    fa_dict = get_ucsc_dict(build)
    db = _get_gtf_db(gtf)
    out_file = os.path.splitext(gtf)[0] + ".interval_list"
    if file_exists(out_file):
        return out_file

    with open(out_file, "w") as out_handle:
        with open(fa_dict) as in_handle:
            for l in in_handle:
                out_handle.write(l)

        for l in db.all_features():
            out_handle.write("\t".join([str(l.seqid), str(l.start),
                                        str(l.end), str(l.strand),
                                        str(l.attributes.get("transcript_id",
                                                             ["."])[0])]) + "\n")
    return out_file

def prepare_mask_gtf(gtf):
    """
    make a mask file of usually-masked RNA biotypes
    """

    mask_biotype = ["rRNA", "Mt_rRNA", "misc_RNA", "snRNA", "snoRNA",
                    "tRNA", "Mt_tRNA"]
    mask_chrom = ["MT"]
    out_file = os.path.join(os.path.dirname(gtf), "ref-transcripts-mask.gtf")
    if file_exists(out_file):
        return out_file

    db = _get_gtf_db(gtf)
    with open(out_file, "w") as out_handle:
        for g in db.all_features():
            biotype = g.attributes.get("gene_biotype", None)
            if ((biotype and biotype[0] in mask_biotype) or
               g.chrom in mask_chrom):
                out_handle.write(str(g) + "\n")
    return out_file

def prepare_rrna_gtf(gtf):
    """
    extract out just the rRNA biotypes, for assessing rRNA contamination
    """
    mask_biotype = ["rRNA", "Mt_rRNA", "tRNA", "MT_tRNA"]

    out_file = os.path.join(os.path.dirname(gtf), "rRNA.gtf")
    if os.path.exists(out_file):
        return out_file

    db = _get_gtf_db(gtf)

    with open(out_file, "w") as out_handle:
        for g in db.all_features():
            biotype = g.attributes.get("gene_biotype", None)
            if biotype and biotype[0] in mask_biotype:
                out_handle.write(str(g) + "\n")

    return out_file

def gtf_to_genepred(gtf):
    out_file = os.path.splitext(gtf)[0] + ".genePred"
    if file_exists(out_file):
        return out_file

    cmd = "gtfToGenePred -allErrors -genePredExt {gtf} {out_file}"
    subprocess.check_call(cmd.format(**locals()), shell=True)
    return out_file

def prepare_tx_gff(build, org_name):
    """Prepare UCSC ready transcript file given build information.
    """
    ensembl_gff = _download_ensembl_gff(build)
    # if we need to do the name remapping
    if build.ucsc_map:
        ucsc_name_map = build.ucsc_map(org_name)
        tx_gff = _remap_gff(ensembl_gff, ucsc_name_map)
        os.remove(ensembl_gff)
    else:
        tx_gff = "ref-transcripts.gtf"
        os.rename(ensembl_gff, tx_gff)
    return tx_gff

def _remap_gff(base_gff, name_map):
    """Remap chromosome names to UCSC instead of Ensembl
    """
    out_file = "ref-transcripts.gtf"
    if not os.path.exists(out_file):
        with open(out_file, "w") as out_handle, \
             open(base_gff) as in_handle:
            for line in in_handle:
                parts = line.split("\t")
                ucsc_name = name_map.get(parts[0], None)
                if ucsc_name:
                    out_handle.write("\t".join([ucsc_name] + parts[1:]))
    return out_file

def _download_ensembl_gff(build):
    """Given build details, download and extract the relevant ensembl GFF.
    """
    fname = build.fbase + ".gtf.gz"
    dl_url = "/".join([base_ftp, build.taxname, fname]).format(release=ensembl_release)
    out_file = os.path.splitext(os.path.basename(dl_url))[0]
    if not os.path.exists(out_file):
        subprocess.check_call(["wget", dl_url])
        subprocess.check_call(["gunzip", os.path.basename(dl_url)])
    return out_file

def _get_gtf_db(gtf):
    db_file = gtf + ".db"
    if not file_exists(db_file):
        gffutils.create_db(gtf, dbfn=db_file)

    return gffutils.FeatureDB(db_file)

if __name__ == "__main__":
    parser = ArgumentParser(description="Prepare the transcriptome files for an "
                            "organism.")
    parser.add_argument("--gtf",
                        help="Optional GTF file (instead of downloading from Ensembl.",
                        default=None),
    parser.add_argument("picard",
                        help="Path to Picard")
    parser.add_argument("org_build", help="Build of organism to run.")
    args = parser.parse_args()
    global PICARD_DIR
    PICARD_DIR = args.picard
    main(args.org_build, args.gtf)

########NEW FILE########
__FILENAME__ = s3_multipart_upload
#!/usr/bin/env python
"""Split large file into multiple pieces for upload to S3.

S3 only supports 5Gb files for uploading directly, so for larger CloudBioLinux
box images we need to use boto's multipart file support.

This parallelizes the task over available cores using multiprocessing.

It checks for an up to date version of the file remotely, skipping transfer
if found.

Usage:
  s3_multipart_upload.py <file_to_transfer> <bucket_name> [<s3_key_name>]
    if <s3_key_name> is not specified, the filename will be used.

    --norr -- Do not use reduced redundancy storage.
    --public -- Make uploaded files public.
    --cores=n -- Number of cores to use for upload

    Files are stored at cheaper reduced redundancy storage by default.
"""
import os
import sys
import glob
import subprocess
import contextlib
import functools
import multiprocessing
from multiprocessing.pool import IMapIterator
from optparse import OptionParser
import rfc822

import boto

def main(transfer_file, bucket_name, s3_key_name=None, use_rr=True,
         make_public=True, cores=None):
    if s3_key_name is None:
        s3_key_name = os.path.basename(transfer_file)
    conn = boto.connect_s3()
    bucket = conn.lookup(bucket_name)
    if bucket is None:
        bucket = conn.create_bucket(bucket_name)
    if s3_has_uptodate_file(bucket, transfer_file, s3_key_name):
        print "S3 has up to date version of %s in %s. Not transferring." % \
            (s3_key_name, bucket.name)
        return
    mb_size = os.path.getsize(transfer_file) / 1e6
    if mb_size < 50:
        _standard_transfer(bucket, s3_key_name, transfer_file, use_rr)
    else:
        _multipart_upload(bucket, s3_key_name, transfer_file, mb_size, use_rr,
                          cores)
    s3_key = bucket.get_key(s3_key_name)
    if make_public:
        s3_key.set_acl("public-read")

def s3_has_uptodate_file(bucket, transfer_file, s3_key_name):
    """Check if S3 has an existing, up to date version of this file.
    """
    s3_key = bucket.get_key(s3_key_name)
    if s3_key:
        s3_size = s3_key.size
        local_size = os.path.getsize(transfer_file)
        s3_time = rfc822.mktime_tz(rfc822.parsedate_tz(s3_key.last_modified))
        local_time = os.path.getmtime(transfer_file)
        return s3_size == local_size and s3_time >= local_time
    return False

def upload_cb(complete, total):
    sys.stdout.write(".")
    sys.stdout.flush()

def _standard_transfer(bucket, s3_key_name, transfer_file, use_rr):
    print " Upload with standard transfer, not multipart",
    new_s3_item = bucket.new_key(s3_key_name)
    new_s3_item.set_contents_from_filename(transfer_file, reduced_redundancy=use_rr,
                                           cb=upload_cb, num_cb=10)
    print

def map_wrap(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return apply(f, *args, **kwargs)
    return wrapper

def mp_from_ids(mp_id, mp_keyname, mp_bucketname):
    """Get the multipart upload from the bucket and multipart IDs.

    This allows us to reconstitute a connection to the upload
    from within multiprocessing functions.
    """
    conn = boto.connect_s3()
    bucket = conn.lookup(mp_bucketname)
    mp = boto.s3.multipart.MultiPartUpload(bucket)
    mp.key_name = mp_keyname
    mp.id = mp_id
    return mp

@map_wrap
def transfer_part(mp_id, mp_keyname, mp_bucketname, i, part):
    """Transfer a part of a multipart upload. Designed to be run in parallel.
    """
    mp = mp_from_ids(mp_id, mp_keyname, mp_bucketname)
    print " Transferring", i, part
    with open(part) as t_handle:
        mp.upload_part_from_file(t_handle, i+1)
    os.remove(part)

def _multipart_upload(bucket, s3_key_name, tarball, mb_size, use_rr=True,
                      cores=None):
    """Upload large files using Amazon's multipart upload functionality.
    """
    def split_file(in_file, mb_size, split_num=5):
        prefix = os.path.join(os.path.dirname(in_file),
                              "%sS3PART" % (os.path.basename(s3_key_name)))
        # require a split size between 5Mb (AWS minimum) and 250Mb
        split_size = int(max(min(mb_size / (split_num * 2.0), 250), 5))
        if not os.path.exists("%saa" % prefix):
            cl = ["split", "-b%sm" % split_size, in_file, prefix]
            subprocess.check_call(cl)
        return sorted(glob.glob("%s*" % prefix))

    mp = bucket.initiate_multipart_upload(s3_key_name, reduced_redundancy=use_rr)
    with multimap(cores) as pmap:
        for _ in pmap(transfer_part, ((mp.id, mp.key_name, mp.bucket_name, i, part)
                                      for (i, part) in
                                      enumerate(split_file(tarball, mb_size, cores)))):
            pass
    mp.complete_upload()

@contextlib.contextmanager
def multimap(cores=None):
    """Provide multiprocessing imap like function.

    The context manager handles setting up the pool, worked around interrupt issues
    and terminating the pool on completion.
    """
    if cores is None:
        cores = max(multiprocessing.cpu_count() - 1, 1)
    def wrapper(func):
        def wrap(self, timeout=None):
            return func(self, timeout=timeout if timeout is not None else 1e100)
        return wrap
    IMapIterator.next = wrapper(IMapIterator.next)
    pool = multiprocessing.Pool(cores)
    yield pool.imap
    pool.terminate()

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-r", "--norr", dest="use_rr",
                      action="store_false", default=True)
    parser.add_option("-p", "--public", dest="make_public",
                      action="store_true", default=False)
    parser.add_option("-c", "--cores", dest="cores",
                      default=multiprocessing.cpu_count())
    (options, args) = parser.parse_args()
    if len(args) < 2:
        print __doc__
        sys.exit()
    kwargs = dict(use_rr=options.use_rr, make_public=options.make_public,
                  cores=int(options.cores))
    main(*args, **kwargs)

########NEW FILE########
