__FILENAME__ = manifest
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import binascii
import hashlib
import logging
import os.path
import subprocess

import lxml.etree
import lxml.objectify

import euca2ools.bundle


class BundleManifest(object):
    def __init__(self, loglevel=None):
        self.log = logging.getLogger(self.__class__.__name__)
        if loglevel is not None:
            self.log.level = loglevel
        self.image_arch = None
        self.kernel_id = None
        self.ramdisk_id = None
        self.block_device_mappings = {}  # virtual -> device
        self.product_codes = []
        self.image_name = None
        self.account_id = None
        self.image_type = None
        self.image_digest = None
        self.image_digest_algorithm = None
        self.image_size = None
        self.bundled_image_size = None
        self.enc_key = None
        self.enc_iv = None
        self.enc_algorithm = None
        self.image_parts = []

    @classmethod
    def read_from_file(cls, manifest_filename, privkey_filename=None):
        with open(manifest_filename) as manifest_fileobj:
            return cls.read_from_fileobj(manifest_fileobj, privkey_filename)

    @classmethod
    def read_from_fileobj(cls, manifest_fileobj, privkey_filename=None):
        xml = lxml.objectify.parse(manifest_fileobj).getroot()
        manifest = cls()
        mconfig = xml.machine_configuration
        manifest.image_arch = mconfig.architecture.text.strip()
        if hasattr(mconfig, 'kernel_id'):
            manifest.kernel_id = mconfig.kernel_id.text.strip()
        if hasattr(mconfig, 'ramdisk_id'):
            manifest.ramdisk_id = mconfig.ramdisk_id.text.strip()
        if hasattr(mconfig, 'block_device_mappings'):
            for xml_mapping in mconfig.block_device_mappings.iter(
                    tag='block_device_mapping'):
                device = xml_mapping.device.text.strip()
                virtual = xml_mapping.virtual.text.strip()
                manifest.block_device_mappings[virtual] = device
        if hasattr(mconfig, 'productcodes'):
            for xml_pcode in mconfig.productcodes.iter(tag='product_code'):
                manifest.product_codes.append(xml_pcode.text.strip())
        manifest.image_name = xml.image.name.text.strip()
        manifest.account_id = xml.image.user.text.strip()
        manifest.image_type = xml.image.type.text.strip()
        manifest.image_digest = xml.image.digest.text.strip()
        manifest.image_digest_algorithm = xml.image.digest.get('algorithm')
        manifest.image_size = int(xml.image.size.text.strip())
        manifest.bundled_image_size = int(xml.image.bundled_size.text.strip())
        if privkey_filename is not None:
            try:
                manifest.enc_key = _decrypt_hex(
                    xml.image.user_encrypted_key.text.strip(),
                    privkey_filename)
            except ValueError:
                manifest.enc_key = _decrypt_hex(
                    xml.image.ec2_encrypted_key.text.strip(), privkey_filename)
            manifest.enc_algorithm = xml.image.user_encrypted_key.get(
                'algorithm')
            try:
                manifest.enc_iv = _decrypt_hex(
                    xml.image.user_encrypted_iv.text.strip(), privkey_filename)
            except ValueError:
                manifest.enc_iv = _decrypt_hex(
                    xml.image.ec2_encrypted_iv.text.strip(), privkey_filename)

        manifest.image_parts = [None] * int(xml.image.parts.get('count'))
        for xml_part in xml.image.parts.iter(tag='part'):
            index = int(xml_part.get('index'))
            manifest.image_parts[index] = euca2ools.bundle.BundlePart(
                xml_part.filename.text.strip(), xml_part.digest.text.strip(),
                xml_part.digest.get('algorithm'))
        for index, part in enumerate(manifest.image_parts):
            if part is None:
                raise ValueError('part {0} must not be None'.format(index))
        return manifest

    def dump_to_str(self, privkey_filename, user_cert_filename,
                    ec2_cert_filename, pretty_print=False):
        if self.enc_key is None:
            raise ValueError('enc_key must not be None')
        if self.enc_iv is None:
            raise ValueError('enc_iv must not be None')
        ec2_fp = euca2ools.bundle.util.get_cert_fingerprint(ec2_cert_filename)
        self.log.info('creating manifest for EC2 service with fingerprint %s',
                      ec2_fp)
        self.log.debug('EC2 certificate:  %s', ec2_cert_filename)
        self.log.debug('user certificate: %s', user_cert_filename)
        self.log.debug('user private key: %s', privkey_filename)

        xml = lxml.objectify.Element('manifest')

        # Manifest version
        xml.version = '2007-10-10'

        # Our version
        xml.bundler = None
        xml.bundler.name = 'euca2ools'
        xml.bundler.version = euca2ools.__version__
        xml.bundler.release = 0

        # Target hardware
        xml.machine_configuration = None
        mconfig = xml.machine_configuration
        assert self.image_arch is not None
        mconfig.architecture = self.image_arch
        # kernel_id and ramdisk_id are normally meaningful only for machine
        # images, but eucalyptus also uses them to indicate kernel and ramdisk
        # images using the magic string "true", so their presence cannot be
        # made contingent on whether the image is a machine image or not.  Be
        # careful not to create invalid kernel or ramdisk manifests because of
        # this.
        if self.kernel_id:
            mconfig.kernel_id = self.kernel_id
        if self.ramdisk_id:
            mconfig.ramdisk_id = self.ramdisk_id
        if self.image_type == 'machine':
            if self.block_device_mappings:
                mconfig.block_device_mapping = None
                for virtual, device in sorted(
                        self.block_device_mappings.items()):
                    xml_mapping = lxml.objectify.Element('mapping')
                    xml_mapping.device = device
                    xml_mapping.virtual = virtual
                    mconfig.block_device_mapping.append(xml_mapping)
            if self.product_codes:
                mconfig.product_codes = None
                for code in self.product_codes:
                    xml_code = lxml.objectify.Element('product_code')
                    mconfig.product_codes.append(xml_code)
                    mconfig.product_codes.product_code[-1] = code

        # Image info
        xml.image = None
        assert self.image_name is not None
        xml.image.name = self.image_name
        assert self.account_id is not None
        xml.image.user = self.account_id
        assert self.image_digest is not None
        xml.image.digest = self.image_digest
        assert self.image_digest_algorithm is not None
        xml.image.digest.set('algorithm', self.image_digest_algorithm)

        assert self.image_size is not None
        xml.image.size = self.image_size
        assert self.bundled_image_size is not None
        xml.image.bundled_size = self.bundled_image_size
        assert self.image_type is not None

        xml.image.type = self.image_type

        # Bundle encryption keys (these are cloud-specific)
        assert self.enc_key is not None
        assert self.enc_iv is not None
        assert self.enc_algorithm is not None
        # xml.image.append(lxml.etree.Comment(' EC2 cert fingerprint:  {0} '
        #                                     .format(ec2_fp)))
        xml.image.ec2_encrypted_key = _public_encrypt(self.enc_key,
                                                      ec2_cert_filename)
        xml.image.ec2_encrypted_key.set('algorithm', self.enc_algorithm)
        # xml.image.append(lxml.etree.Comment(' User cert fingerprint: {0} '
        #                                     .format(user_fp)))
        xml.image.user_encrypted_key = _public_encrypt(self.enc_key,
                                                       user_cert_filename)
        xml.image.user_encrypted_key.set('algorithm', self.enc_algorithm)
        xml.image.ec2_encrypted_iv = _public_encrypt(self.enc_iv,
                                                     ec2_cert_filename)
        xml.image.user_encrypted_iv = _public_encrypt(self.enc_iv,
                                                      user_cert_filename)

        # Bundle parts
        xml.image.parts = None
        xml.image.parts.set('count', str(len(self.image_parts)))
        for index, part in enumerate(self.image_parts):
            if part is None:
                raise ValueError('part {0} must not be None'.format(index))
            part_elem = lxml.objectify.Element('part')
            part_elem.set('index', str(index))
            part_elem.filename = os.path.basename(part.filename)
            part_elem.digest = part.hexdigest
            part_elem.digest.set('algorithm', part.digest_algorithm)
            # part_elem.append(lxml.etree.Comment(
            #     ' size: {0} '.format(part.size)))
            xml.image.parts.append(part_elem)

        # Cleanup for signature
        lxml.objectify.deannotate(xml, xsi_nil=True)
        lxml.etree.cleanup_namespaces(xml)
        to_sign = (lxml.etree.tostring(xml.machine_configuration) +
                   lxml.etree.tostring(xml.image))
        self.log.debug('string to sign: %s', repr(to_sign))
        signature = _rsa_sha1_sign(to_sign, privkey_filename)
        xml.signature = signature
        self.log.debug('hex-encoded signature: %s', signature)
        lxml.objectify.deannotate(xml, xsi_nil=True)
        lxml.etree.cleanup_namespaces(xml)
        self.log.debug('-- manifest content --\n', extra={'append': True})
        pretty_manifest = lxml.etree.tostring(xml, pretty_print=True).strip()
        self.log.debug('%s', pretty_manifest, extra={'append': True})
        self.log.debug('-- end of manifest content --')
        return lxml.etree.tostring(xml, pretty_print=pretty_print).strip()

    def dump_to_file(self, manifest_file, privkey_filename,
                     user_cert_filename, ec2_cert_filename,
                     pretty_print=False):
        manifest_file.write(self.dump_to_str(
            privkey_filename, user_cert_filename, ec2_cert_filename,
            pretty_print=pretty_print))


def _decrypt_hex(hex_encrypted_key, privkey_filename):
    popen = subprocess.Popen(['openssl', 'rsautl', '-decrypt', '-pkcs',
                              '-inkey', privkey_filename],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    binary_encrypted_key = binascii.unhexlify(hex_encrypted_key)
    (decrypted_key, _) = popen.communicate(binary_encrypted_key)
    try:
        # Make sure it might actually be an encryption key.
        # This isn't perfect, but it's still better than nothing.
        int(decrypted_key, 16)
        return decrypted_key
    except ValueError:
        pass
    raise ValueError("Failed to decrypt the bundle's encryption key.  "
                     "Ensure the key supplied matches the one used for "
                     "bundling.")


def _public_encrypt(content, cert_filename):
    popen = subprocess.Popen(['openssl', 'rsautl', '-encrypt', '-pkcs',
                              '-inkey', cert_filename, '-certin'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, _) = popen.communicate(content)
    return binascii.hexlify(stdout)


def _rsa_sha1_sign(content, privkey_filename):
    digest = hashlib.sha1()
    digest.update(content)
    popen = subprocess.Popen(['openssl', 'pkeyutl', '-sign', '-inkey',
                              privkey_filename, '-pkeyopt', 'digest:sha1'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (stdout, _) = popen.communicate(digest.digest())
    return binascii.hexlify(stdout)

########NEW FILE########
__FILENAME__ = core
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib
import multiprocessing
import shutil
import subprocess
import tarfile

import euca2ools.bundle.util
from euca2ools.bundle.util import close_all_fds


def create_bundle_pipeline(infile, outfile, enc_key, enc_iv, tarinfo,
                           debug=False):
    pids = []

    # infile -> tar
    tar_out_r, tar_out_w = euca2ools.bundle.util.open_pipe_fileobjs()
    tar_p = multiprocessing.Process(target=_create_tarball_from_stream,
                                    args=(infile, tar_out_w, tarinfo),
                                    kwargs={'debug': debug})
    tar_p.start()
    pids.append(tar_p.pid)
    infile.close()
    tar_out_w.close()

    # tar -> sha1sum
    digest_out_r, digest_out_w = euca2ools.bundle.util.open_pipe_fileobjs()
    digest_result_r, digest_result_w = multiprocessing.Pipe(duplex=False)
    digest_p = multiprocessing.Process(
        target=_calc_sha1_for_pipe, kwargs={'debug': debug},
        args=(tar_out_r, digest_out_w, digest_result_w))
    digest_p.start()
    pids.append(digest_p.pid)
    tar_out_r.close()
    digest_out_w.close()
    digest_result_w.close()

    # sha1sum -> gzip
    try:
        gzip = subprocess.Popen(['pigz', '-c'], stdin=digest_out_r,
                                stdout=subprocess.PIPE, close_fds=True,
                                bufsize=-1)
    except OSError:
        gzip = subprocess.Popen(['gzip', '-c'], stdin=digest_out_r,
                                stdout=subprocess.PIPE, close_fds=True,
                                bufsize=-1)
    digest_out_r.close()
    pids.append(gzip.pid)

    # gzip -> openssl
    openssl = subprocess.Popen(['openssl', 'enc', '-e', '-aes-128-cbc',
                                '-K', enc_key, '-iv', enc_iv],
                               stdin=gzip.stdout, stdout=outfile,
                               close_fds=True, bufsize=-1)
    gzip.stdout.close()
    pids.append(openssl.pid)

    # Make sure something calls wait() on every child process
    for pid in pids:
        euca2ools.bundle.util.waitpid_in_thread(pid)

    # Return the connection the caller can use to obtain the final digest
    return digest_result_r


def create_unbundle_pipeline(infile, outfile, enc_key, enc_iv, debug=False):
    """
    Create a pipeline to perform the unbundle operation on infile input.
    The resulting unbundled image will be written to 'outfile'.

    :param outfile: file  obj to write unbundled image to
    :param enc_key: the encryption key used to bundle the image
    :param enc_iv: the encyrption initialization vector used in the bundle
    :returns multiprocess pipe to read sha1 digest of written image
    """
    pids = []

    # infile -> openssl
    openssl = subprocess.Popen(['openssl', 'enc', '-d', '-aes-128-cbc',
                                '-K', enc_key, '-iv', enc_iv],
                               stdin=infile, stdout=subprocess.PIPE,
                               close_fds=True, bufsize=-1)
    pids.append(openssl.pid)
    infile.close()

    # openssl -> gzip
    try:
        gzip = subprocess.Popen(['pigz', '-c', '-d'], stdin=openssl.stdout,
                                stdout=subprocess.PIPE, close_fds=True,
                                bufsize=-1)
    except OSError:
        gzip = subprocess.Popen(['gzip', '-c', '-d'], stdin=openssl.stdout,
                                stdout=subprocess.PIPE, close_fds=True,
                                bufsize=-1)
    pids.append(gzip.pid)
    openssl.stdout.close()

    # gzip -> sha1sum
    digest_out_r, digest_out_w = euca2ools.bundle.util.open_pipe_fileobjs()
    digest_result_r, digest_result_w = multiprocessing.Pipe(duplex=False)
    digest_p = multiprocessing.Process(
        target=_calc_sha1_for_pipe, kwargs={'debug': debug},
        args=(gzip.stdout, digest_out_w, digest_result_w))
    digest_p.start()
    pids.append(digest_p.pid)
    gzip.stdout.close()
    digest_out_w.close()
    digest_result_w.close()

    # sha1sum -> tar
    tar_p = multiprocessing.Process(
        target=_extract_from_tarball_stream,
        args=(digest_out_r, outfile), kwargs={'debug': debug})
    tar_p.start()
    digest_out_r.close()
    pids.append(tar_p.pid)

    # Make sure something calls wait() on every child process
    for pid in pids:
        euca2ools.bundle.util.waitpid_in_thread(pid)

    # Return the connection the caller can use to obtain the final digest
    return digest_result_r


def copy_with_progressbar(infile, outfile, progressbar=None):
    """
    Synchronously copy data from infile to outfile, updating a progress bar
    with the total number of bytes copied along the way if one was provided,
    and return the number of bytes copied.

    This method must be run on the main thread.

    :param infile: file obj to read input from
    :param outfile: file obj to write output to
    :param progressbar: progressbar object to update with i/o information
    :param maxbytes: Int maximum number of bytes to write
    """
    bytes_written = 0
    if progressbar:
        progressbar.start()
    try:
        while not infile.closed:
            chunk = infile.read(euca2ools.BUFSIZE)
            if chunk:
                outfile.write(chunk)
                outfile.flush()
                bytes_written += len(chunk)
                if progressbar:
                    progressbar.update(bytes_written)

            else:
                break
    finally:
        if progressbar:
            progressbar.finish()
        infile.close()
    return bytes_written


def _calc_sha1_for_pipe(infile, outfile, digest_out_pipe_w, debug=False):
    """
    Read data from infile and write it to outfile, calculating a running SHA1
    digest along the way.  When infile hits end-of-file, send the digest in
    hex form to result_mpconn and exit.
    :param infile: file obj providing input for digest
    :param outfile: file obj destination for writing output
    :param digest_out_pipe_w: fileobj to write digest to
    :param debug: boolean used in exception handling
    """
    close_all_fds([infile, outfile, digest_out_pipe_w])
    digest = hashlib.sha1()
    try:
        while True:
            chunk = infile.read(euca2ools.BUFSIZE)
            if chunk:
                digest.update(chunk)
                outfile.write(chunk)
                outfile.flush()
            else:
                break
        digest_out_pipe_w.send(digest.hexdigest())
    except IOError:
        # HACK
        if not debug:
            return
        raise
    finally:
        infile.close()
        outfile.close()
        digest_out_pipe_w.close()


def _create_tarball_from_stream(infile, outfile, tarinfo, debug=False):
    close_all_fds(except_fds=[infile, outfile])
    tarball = tarfile.open(mode='w|', fileobj=outfile,
                           bufsize=euca2ools.BUFSIZE)
    try:
        tarball.addfile(tarinfo, fileobj=infile)
    except IOError:
        # HACK
        if not debug:
            return
        raise
    finally:
        infile.close()
        tarball.close()
        outfile.close()


def _extract_from_tarball_stream(infile, outfile, debug=False):
    """
    Perform tar extract on infile and write to outfile
    :param infile: file obj providing input for tar
    :param outfile: file obj destination for tar output
    :param debug: boolean used in exception handling
    """
    close_all_fds([infile, outfile])
    tarball = tarfile.open(mode='r|', fileobj=infile)
    try:
        tarinfo = tarball.next()
        shutil.copyfileobj(tarball.extractfile(tarinfo), outfile)
    except IOError:
        # HACK
        if not debug:
            return
        raise
    finally:
        infile.close()
        tarball.close()
        outfile.close()

########NEW FILE########
__FILENAME__ = fittings
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib
import itertools
import multiprocessing
import os
import sys

import euca2ools.bundle.pipes
import euca2ools.bundle.util


def create_bundle_part_deleter(in_mpconn, out_mpconn=None):
    del_p = multiprocessing.Process(target=_delete_part_files,
                                    args=(in_mpconn,),
                                    kwargs={'out_mpconn': out_mpconn})
    del_p.start()
    euca2ools.bundle.util.waitpid_in_thread(del_p.pid)


def create_bundle_part_writer(infile, part_prefix, part_size,
                              part_write_sem=None, debug=False):
    partinfo_result_r, partinfo_result_w = multiprocessing.Pipe(duplex=False)

    writer_p = multiprocessing.Process(
        target=_write_parts,
        args=(infile, part_prefix, part_size, partinfo_result_w),
        kwargs={'part_write_sem': part_write_sem, 'debug': debug})
    writer_p.start()
    partinfo_result_w.close()
    infile.close()
    euca2ools.bundle.util.waitpid_in_thread(writer_p.pid)
    return partinfo_result_r


def create_mpconn_aggregator(in_mpconn, out_mpconn=None, debug=False):
    result_mpconn_r, result_mpconn_w = multiprocessing.Pipe(duplex=False)
    agg_p = multiprocessing.Process(
        target=_aggregate_mpconn_items, args=(in_mpconn, result_mpconn_w),
        kwargs={'out_mpconn': out_mpconn, 'debug': debug})
    agg_p.start()
    result_mpconn_w.close()
    euca2ools.bundle.util.waitpid_in_thread(agg_p.pid)
    return result_mpconn_r


def _delete_part_files(in_mpconn, out_mpconn=None):
    euca2ools.bundle.util.close_all_fds(except_fds=(in_mpconn, out_mpconn))
    try:
        while True:
            part = in_mpconn.recv()
            os.unlink(part.filename)
            if out_mpconn is not None:
                out_mpconn.send(part)
    except EOFError:
        return
    finally:
        in_mpconn.close()
        if out_mpconn is not None:
            out_mpconn.close()


def _aggregate_mpconn_items(in_mpconn, result_mpconn, out_mpconn=None,
                            debug=False):
    euca2ools.bundle.util.close_all_fds(
        except_fds=(in_mpconn, out_mpconn, result_mpconn))
    results = []
    try:
        while True:
            next_result = in_mpconn.recv()
            results.append(next_result)
            if out_mpconn is not None:
                out_mpconn.send(next_result)
    except EOFError:
        try:
            result_mpconn.send(results)
        except IOError:
            # HACK
            if not debug:
                return
            raise
    except IOError:
        # HACK
        if not debug:
            return
        raise
    finally:
        result_mpconn.close()
        in_mpconn.close()
        if out_mpconn is not None:
            out_mpconn.close()


def _write_parts(infile, part_prefix, part_size, partinfo_mpconn,
                 part_write_sem=None, debug=False):
    except_fds = [infile, partinfo_mpconn]
    if part_write_sem is not None and sys.platform == 'darwin':
        # When I ran close_all_fds on OS X and excluded only the FDs
        # listed above, all attempts to use the semaphore resulted in
        # complaints about bad file descriptors.  The following code
        # is a horrible hack that I stumbled upon while attempting
        # to figure out what FD number I needed to avoid closing to
        # preserve the semaphore.  It is probably incorrect and reliant
        # on implementation details, so I am happy to take a patch that
        # manages to deal with this problem in a more reasonable way.
        try:
            except_fds.append(int(part_write_sem._semlock.handle))
        except AttributeError:
            part_write_sem = None
        except ValueError:
            part_write_sem = None
    euca2ools.bundle.util.close_all_fds(except_fds=except_fds)
    for part_no in itertools.count():
        if part_write_sem is not None:
            part_write_sem.acquire()
        part_fname = '{0}.part.{1:02}'.format(part_prefix, part_no)
        part_digest = hashlib.sha1()
        with open(part_fname, 'w') as part:
            bytes_written = 0
            bytes_to_write = part_size
            while bytes_to_write > 0:
                try:
                    chunk = infile.read(min(bytes_to_write, euca2ools.BUFSIZE))
                except ValueError:  # I/O error on closed file
                    # HACK
                    if not debug:
                        partinfo_mpconn.close()
                        return
                    raise
                if chunk:
                    part.write(chunk)
                    part_digest.update(chunk)
                    bytes_to_write -= len(chunk)
                    bytes_written += len(chunk)
                else:
                    break
            partinfo = euca2ools.bundle.BundlePart(
                part_fname, part_digest.hexdigest(), 'SHA1', bytes_written)
            partinfo_mpconn.send(partinfo)
        if bytes_written < part_size:
            # That's the last part
            infile.close()
            partinfo_mpconn.close()
            return

########NEW FILE########
__FILENAME__ = util
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import subprocess
import threading


def close_all_fds(except_fds=None):
    except_filenos = [1, 2]
    if except_fds is not None:
        for except_fd in except_fds:
            if except_fd is None:
                pass
            elif isinstance(except_fd, int):
                except_filenos.append(except_fd)
            elif hasattr(except_fd, 'fileno'):
                except_filenos.append(except_fd.fileno())
            else:
                raise ValueError('{0} must be an int or have a fileno method'
                                 .format(repr(except_fd)))

    fileno_ranges = []
    next_range_min = 0
    for except_fileno in sorted(except_filenos):
        if except_fileno > next_range_min:
            fileno_ranges.append((next_range_min, except_fileno))
        next_range_min = max(next_range_min, except_fileno + 1)
    fileno_ranges.append((next_range_min, 1024))

    for fileno_range in fileno_ranges:
        os.closerange(fileno_range[0], fileno_range[1])


def get_cert_fingerprint(cert_filename):
    openssl = subprocess.Popen(('openssl', 'x509', '-in', cert_filename,
                                '-fingerprint', '-sha1', '-noout'),
                               stdout=subprocess.PIPE)
    (fingerprint, _) = openssl.communicate()
    return fingerprint.strip().rsplit('=', 1)[-1].replace(':', '').lower()


def open_pipe_fileobjs():
    pipe_r, pipe_w = os.pipe()
    return os.fdopen(pipe_r), os.fdopen(pipe_w, 'w')


def waitpid_in_thread(pid):
    """
    Start a thread that calls os.waitpid on a particular PID to prevent
    zombie processes from hanging around after they have finished.
    """
    pid_thread = threading.Thread(target=_wait_for_pid, args=(pid,))
    pid_thread.daemon = True
    pid_thread.start()


def _wait_for_pid(pid):
    if pid:
        try:
            os.waitpid(pid, 0)
        except OSError:
            pass

########NEW FILE########
__FILENAME__ = argtypes
# Copyright 2012-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import base64
import sys

from requestbuilder import EMPTY


def manifest_block_device_mappings(mappings_as_str):
    mappings = {}
    mapping_strs = mappings_as_str.split(',')
    for mapping_str in mapping_strs:
        if mapping_str.strip():
            bits = mapping_str.strip().split('=')
            if len(bits) == 2:
                mappings[bits[0].strip()] = bits[1].strip()
            else:
                raise argparse.ArgumentTypeError(
                    "invalid device mapping '{0}' (must have format "
                    "'VIRTUAL=DEVICE')".format(mapping_str))
    return mappings


def ec2_block_device_mapping(map_as_str):
    """
    Parse a block device mapping from an image registration command line.
    """
    try:
        (device, mapping) = map_as_str.split('=')
    except ValueError:
        raise argparse.ArgumentTypeError(
            'block device mapping "{0}" must have form DEVICE=MAPPED'
            .format(map_as_str))
    map_dict = {'DeviceName': device}
    if mapping.lower() == 'none':
        map_dict['NoDevice'] = 'true'
    elif mapping.startswith('ephemeral'):
        map_dict['VirtualName'] = mapping
    elif (mapping.startswith('snap-') or mapping.startswith('vol-') or
          mapping.startswith(':')):
        map_bits = mapping.split(':')
        while len(map_bits) < 5:
            map_bits.append(None)
        if len(map_bits) != 5:
            raise argparse.ArgumentTypeError(
                'EBS block device mapping "{0}" must have form '
                'DEVICE=[SNAP-ID]:[GiB]:[true|false]:[standard|TYPE[:IOPS]]'
                .format(map_as_str))

        map_dict['Ebs'] = {}
        if map_bits[0]:
            map_dict['Ebs']['SnapshotId'] = map_bits[0]
        if map_bits[1]:
            try:
                map_dict['Ebs']['VolumeSize'] = int(map_bits[1])
            except ValueError:
                raise argparse.ArgumentTypeError(
                    'second element of EBS block device mapping "{0}" must be '
                    'an integer'.format(map_as_str))
        if map_bits[2]:
            if map_bits[2].lower() not in ('true', 'false'):
                raise argparse.ArgumentTypeError(
                    'third element of EBS block device mapping "{0}" must be '
                    '"true" or "false"'.format(map_as_str))
            map_dict['Ebs']['DeleteOnTermination'] = map_bits[2].lower()
        if map_bits[3]:
            map_dict['Ebs']['VolumeType'] = map_bits[3]
        if map_bits[4]:
            if map_bits[3] == 'standard':
                raise argparse.ArgumentTypeError(
                    'fifth element of EBS block device mapping "{0}" is not '
                    'allowed with volume type "standard"'.format(map_as_str))
            map_dict['Ebs']['Iops'] = map_bits[4]
        if not map_dict['Ebs']:
            raise argparse.ArgumentTypeError(
                'EBS block device mapping "{0}" must specify at least one '
                'element.  Use "{1}=none" to suppress an existing mapping.'
                .format(map_as_str, device))
    elif not mapping:
        raise argparse.ArgumentTypeError(
            'invalid block device mapping "{0}".  Use "{1}=none" to suppress '
            'an existing mapping.'.format(map_as_str, device))
    else:
        raise argparse.ArgumentTypeError(
            'invalid block device mapping "{0}"'.format(map_as_str))
    return map_dict


def filesize(size):
    suffixes = 'kmgt'
    s_size = size.lower().rstrip('b')
    if len(s_size) > 0 and s_size[-1] in suffixes:
        multiplier = 1024 ** (suffixes.find(s_size[-1]) + 1)
        s_size = s_size[:-1]
    else:
        multiplier = 1
    return multiplier * int(s_size)


def vpc_interface(iface_as_str):
    """
    Nine-part VPC network interface definition:
    [INTERFACE]:INDEX:[SUBNET]:[DESCRIPTION]:[PRIV_IP]:[GROUP1,GROUP2,...]:
    [true|false]:[SEC_IP_COUNT|:SEC_IP1,SEC_IP2,...]
    """

    if len(iface_as_str) == 0:
        raise argparse.ArgumentTypeError(
            'network interface definitions must be non-empty'.format(
                iface_as_str))

    bits = iface_as_str.split(':')
    iface = {}

    if len(bits) < 2:
        raise argparse.ArgumentTypeError(
            'network interface definition "{0}" must consist of at least 2 '
            'elements ({1} provided)'.format(iface_as_str, len(bits)))
    elif len(bits) > 9:
        raise argparse.ArgumentTypeError(
            'network interface definition "{0}" must consist of at most 9 '
            'elements ({1} provided)'.format(iface_as_str, len(bits)))
    while len(bits) < 9:
        bits.append(None)

    if bits[0]:
        # Preexisting NetworkInterfaceId
        if bits[0].startswith('eni-') and len(bits[0]) == 12:
            iface['NetworkInterfaceId'] = bits[0]
        else:
            raise argparse.ArgumentTypeError(
                'first element of network interface definition "{0}" must be '
                'a network interface ID'.format(iface_as_str))
    if bits[1]:
        # DeviceIndex
        try:
            iface['DeviceIndex'] = int(bits[1])
        except ValueError:
            raise argparse.ArgumentTypeError(
                'second element of network interface definition "{0}" must be '
                'an integer'.format(iface_as_str))
    else:
        raise argparse.ArgumentTypeError(
            'second element of network interface definition "{0}" must be '
            'non-empty'.format(iface_as_str))
    if bits[2]:
        # SubnetId
        if bits[2].startswith('subnet-'):
            iface['SubnetId'] = bits[2]
        else:
            raise argparse.ArgumentTypeError(
                'third element of network interface definition "{0}" must be '
                'a subnet ID'.format(iface_as_str))
    if bits[3]:
        # Description
        iface['Description'] = bits[3]
    if bits[4]:
        # PrivateIpAddresses.n.PrivateIpAddress
        # PrivateIpAddresses.n.Primary
        iface.setdefault('PrivateIpAddresses', [])
        iface['PrivateIpAddresses'].append({'PrivateIpAddress': bits[4],
                                            'Primary': 'true'})
    if bits[5]:
        # SecurityGroupId.n
        groups = [bit for bit in bits[5].split(',') if bit]
        if not all(group.startswith('sg-') for group in groups):
            raise argparse.ArgumentTypeError(
                'sixth element of network interface definition "{0}" must '
                'refer to security groups by IDs, not names'
                .format(iface_as_str))
        iface['SecurityGroupId'] = groups
    if bits[6]:
        # DeleteOnTermination
        if bits[6] in ('true', 'false'):
            iface['DeleteOnTermination'] = bits[6]
        else:
            raise argparse.ArgumentTypeError(
                'seventh element of network interface definition "{0}" '
                'must be "true" or "false"'.format(iface_as_str))
    if bits[7]:
        # SecondaryPrivateIpAddressCount
        if bits[8]:
            raise argparse.ArgumentTypeError(
                'eighth and ninth elements of network interface definition '
                '"{0}" must not both be non-empty'.format(iface_as_str))
        try:
            iface['SecondaryPrivateIpAddressCount'] = int(bits[7])
        except ValueError:
            raise argparse.ArgumentTypeError(
                'eighth element of network interface definition "{0}" must be '
                'an integer'.format(iface_as_str))
    if bits[8]:
        # PrivateIpAddresses.n.PrivateIpAddress
        sec_ips = [{'PrivateIpAddress': addr} for addr in
                   bits[8].split(',') if addr]
        iface.setdefault('PrivateIpAddresses', [])
        iface['PrivateIpAddresses'].extend(sec_ips)
    return iface


def file_contents(filename):
    if filename == '-':
        return sys.stdin.read()
    else:
        with open(filename) as arg_file:
            return arg_file.read()


def b64encoded_file_contents(filename):
    if filename == '-':
        return base64.b64encode(sys.stdin.read())
    else:
        with open(filename) as arg_file:
            return base64.b64encode(arg_file.read())


def binary_tag_def(tag_str):
    """
    Parse a tag definition from the command line.  Return a dict that depends
    on the format of the string given:

     - 'key=value': {'Key': key, 'Value': value}
     - 'key=':      {'Key': key, 'Value': EMPTY}
     - 'key':       {'Key': key, 'Value': EMPTY}
    """
    if '=' in tag_str:
        (key, val) = tag_str.split('=', 1)
        return {'Key': key, 'Value': val or EMPTY}
    else:
        return {'Key': tag_str, 'Value': EMPTY}


def ternary_tag_def(tag_str):
    """
    Parse a tag definition from the command line.  Return a dict that depends
    on the format of the string given:

     - 'key=value': {'Key': key, 'Value': value}
     - 'key=':      {'Key': key, 'Value': EMPTY}
     - 'key':       {'Key': key}
    """
    if '=' in tag_str:
        (key, val) = tag_str.split('=', 1)
        return {'Key': key, 'Value': val or EMPTY}
    else:
        return {'Key': tag_str}


def delimited_list(delimiter, item_type=str):
    def _concrete_delimited_list(list_as_str):
        if isinstance(list_as_str, str) and len(list_as_str) > 0:
            return [item_type(item.strip()) for item in
                    list_as_str.split(delimiter) if len(item.strip()) > 0]
        else:
            return []
    return _concrete_delimited_list

########NEW FILE########
__FILENAME__ = arghelpers
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling.argtypes import autoscaling_tag_def
from requestbuilder import Arg


class TagArg(Arg):
    def __init__(self, required=False):
        helpstr = '''attributes of a tag to affect.  Tags follow the following
        format: "id=resource-name, t=resource-type, k=tag-key, v=tag-val,
        p=propagate-at-launch-flag", where k is the tag's name, v is the tag's
        value, id is a resource ID, t is a resource type, and p is whether to
        propagate tags to instances created by the group.  A value for 'k=' is
        required for each tag.  The rest are optional.  This argument may be
        used more than once.  Each time affects a different tag.'''

        if required:
            helpstr += '  (at least 1 required)'

        Arg.__init__(self, '--tag', dest='Tags.member', required=required,
                     action='append', type=autoscaling_tag_def, help=helpstr,
                     metavar=('"k=VALUE, id=VALUE, t=VALUE, v=VALUE, '
                              'p={true,false}"'))

########NEW FILE########
__FILENAME__ = argtypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from argparse import ArgumentTypeError


def autoscaling_filter_def(filter_str):
    filter_dict = {}
    pieces = filter_str.split(',')
    for piece in pieces:
        piece = piece.strip()
        if '=' not in piece:
            raise ArgumentTypeError(
                "invalid filter: each segment of '{0}' must have format "
                "KEY=VALUE".format(piece))
        key, val = piece.split('=', 1)
        filter_dict.setdefault(key.strip(), [])
        filter_dict[key.strip()].append(val.strip())
    filter_list = []
    for key, values in filter_dict.iteritems():
        filter_list.append({'Name': key, 'Values': values})
    return filter_list


def autoscaling_tag_def(tag_str):
    tag_dict = {}
    pieces = tag_str.split(',')
    for piece in pieces:
        piece = piece.strip()
        if '=' not in piece:
            raise ArgumentTypeError(
                "invalid tag definition: each segment of '{0}' must have "
                "format KEY=VALUE".format(piece))
        key, val = piece.split('=', 1)
        if key == 'k':
            tag_dict['Key'] = val
        elif key == 'id':
            tag_dict['ResourceId'] = val
        elif key == 't':
            tag_dict['ResourceType'] = val
        elif key == 'v':
            tag_dict['Value'] = val
        elif key == 'p':
            if val.lower() in ('true', 'false'):
                tag_dict['PropagateAtLaunch'] = val.lower()
            else:
                raise ArgumentTypeError(
                    "value for to 'p=' must be 'true' or 'false'")
        else:
            raise ArgumentTypeError(
                "unrecognized tag segment '{0}'".format(piece))
    if not tag_dict.get('Key'):
        raise ArgumentTypeError(
            "tag '{0}' must contain a 'k=' segment with a non-empty value")
    return tag_dict

########NEW FILE########
__FILENAME__ = createautoscalinggroup
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from euca2ools.commands.autoscaling.arghelpers import TagArg
from requestbuilder import Arg


class CreateAutoScalingGroup(AutoScalingRequest):
    DESCRIPTION = 'Create a new auto-scaling group'
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the new auto-scaling group (required)'),
            Arg('-l', '--launch-configuration', dest='LaunchConfigurationName',
                metavar='LAUNCHCONFIG', required=True, help='''name of the
                launch configuration to use with the new group (required)'''),
            Arg('-M', '--max-size', dest='MaxSize', metavar='COUNT', type=int,
                required=True, help='maximum group size (required)'),
            Arg('-m', '--min-size', dest='MinSize', metavar='COUNT', type=int,
                required=True, help='minimum group size (required)'),
            Arg('--default-cooldown', dest='DefaultCooldown',
                metavar='SECONDS', type=int,
                help='''amount of time, in seconds, after a scaling activity
                        completes before any further trigger-related scaling
                        activities may start'''),
            Arg('--desired-capacity', dest='DesiredCapacity', metavar='COUNT',
                type=int,
                help='number of running instances the group should contain'),
            Arg('--grace-period', dest='HealthCheckGracePeriod',
                metavar='SECONDS', type=int, help='''number of seconds to wait
                before starting health checks on newly-created instances'''),
            Arg('--health-check-type', dest='HealthCheckType',
                choices=('EC2', 'ELB'),
                help='service to obtain health check status from'),
            Arg('--load-balancers', dest='LoadBalancerNames.member',
                metavar='ELB1,ELB2,...', type=delimited_list(','),
                help='comma-separated list of load balancers to use'),
            Arg('--placement-group', dest='PlacementGroup',
                help='placement group in which to launch new instances'),
            TagArg(required=False),
            Arg('--termination-policies', dest='TerminationPolicies.member',
                metavar='POLICY1,POLICY2,...', type=delimited_list(','),
                help='''ordered list of termination policies.  The first has
                the highest precedence.'''),
            Arg('--vpc-zone-identifier', dest='VPCZoneIdentifier',
                metavar='ZONE1,ZONE2,...',
                help='''comma-separated list of subnet identifiers.  If you
                specify availability zones as well, ensure the subnets'
                availability zones match the ones you specified'''),
            Arg('-z', '--availability-zones', dest='AvailabilityZones.member',
                metavar='ZONE1,ZONE2,...', type=delimited_list(','),
                help='''comma-separated list of availability zones for the new
                group (required unless subnets are supplied)''')]

########NEW FILE########
__FILENAME__ = createlaunchconfiguration
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
import os.path

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.argtypes import (delimited_list,
                                         ec2_block_device_mapping)
from euca2ools.commands.autoscaling import AutoScalingRequest


class CreateLaunchConfiguration(AutoScalingRequest):
    DESCRIPTION = 'Create a new auto-scaling instance launch configuration'
    ARGS = [Arg('LaunchConfigurationName', metavar='LAUNCHCONFIG',
                help='name of the new launch configuration (required)'),
            Arg('-i', '--image-id', dest='ImageId', metavar='IMAGE',
                required=True,
                help='machine image to use for instances (required)'),
            Arg('-t', '--instance-type', dest='InstanceType', metavar='TYPE',
                required=True,
                help='instance type for use for instances (required)'),
            Arg('--block-device-mapping', dest='BlockDeviceMappings.member',
                metavar='DEVICE1=MAPPED1,DEVICE2=MAPPED2,...',
                type=delimited_list(',', item_type=ec2_block_device_mapping),
                help='''a comma-separated list of block device mappings for the
                image, in the form DEVICE=MAPPED, where "MAPPED" is "none",
                "ephemeral(0-3)", or "[SNAP-ID]:[GiB]:[true|false]'''),
            Arg('--ebs-optimized', dest='EbsOptimized', action='store_const',
                const='true',
                help='whether the instance is optimized for EBS I/O'),
            Arg('--group', dest='SecurityGroups.member',
                metavar='GROUP1,GROUP2,...', type=delimited_list(','),
                help='''a comma-separated list of security groups with which
                to associate instances.  Either all group names or all group
                IDs are allowed, but not both.'''),
            Arg('--iam-instance-profile', dest='IamInstanceProfile',
                metavar='PROFILE', help='''ARN of the instance profile
                associated with instances' IAM roles'''),
            Arg('--kernel', dest='KernelId', metavar='KERNEL',
                help='kernel image to use for instances'),
            Arg('--key', dest='KeyName', metavar='KEYPAIR',
                help='name of the key pair to use for instances'),
            Arg('--monitoring-enabled', dest='InstanceMonitoring.Enabled',
                action='store_const', const='true',
                help='enable detailed monitoring (enabled by default)'),
            Arg('--monitoring-disabled', dest='InstanceMonitoring.Enabled',
                action='store_const', const='false',
                help='disable detailed monitoring (enabled by default)'),
            Arg('--ramdisk', dest='RamdiskId', metavar='RAMDISK',
                help='ramdisk image to use for instances'),
            Arg('--spot-price', dest='SpotPrice', metavar='PRICE',
                help='maximum hourly price for any spot instances launched'),
            MutuallyExclusiveArgList(
                Arg('-d', '--user-data', metavar='DATA', route_to=None,
                    help='user data to make available to instances'),
                Arg('--user-data-force', metavar='DATA', route_to=None,
                    help='''same as -d/--user-data, but without checking if a
                    file by that name exists first'''),
                Arg('-f', '--user-data-file', metavar='FILE', route_to=None,
                    help='''file containing user data to make available to
                    instances'''))]

    # noinspection PyExceptionInherit
    def configure(self):
        AutoScalingRequest.configure(self)
        if self.args.get('user_data'):
            if os.path.isfile(self.args['user_data']):
                raise ArgumentError(
                    'argument -d/--user-data: to pass the contents of a file '
                    'as user data, use -f/--user-data-file.  To pass the '
                    "literal value '{0}' as user data even though it matches "
                    'the name of a file, use --user-data-force.')
            else:
                self.params['UserData'] = base64.b64encode(
                    self.args['user_data'])
        elif self.args.get('user_data_force'):
            self.params['UserData'] = base64.b64encode(
                self.args['user_data_force'])
        elif self.args.get('user_data_file'):
            with open(self.args['user_data_file']) as user_data_file:
                self.params['UserData'] = base64.b64encode(
                    user_data_file.read())

########NEW FILE########
__FILENAME__ = createorupdatetags
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from euca2ools.commands.autoscaling.arghelpers import TagArg


class CreateOrUpdateTags(AutoScalingRequest):
    DESCRIPTION = 'Create or update one or more resource tags'
    ARGS = [TagArg(required=True)]

########NEW FILE########
__FILENAME__ = deleteautoscalinggroup
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DeleteAutoScalingGroup(AutoScalingRequest):
    DESCRIPTION = 'Delete an auto-scaling group'
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to delete (required)'),
            Arg('-d', '--force-delete', dest='ForceDelete',
                action='store_const', const='true',
                help='''delete the group and all of its instances without
                waiting for all instances to terminate'''),
            Arg('-f', '--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deletelaunchconfiguration
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DeleteLaunchConfiguration(AutoScalingRequest):
    DESCRIPTION = 'Delete an auto-scaling instance launch configuration'
    ARGS = [Arg('LaunchConfigurationName', metavar='LAUNCHCONFIG',
                help='name of the launch configuration to delete (required)'),
            Arg('-f', '--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # For compatibility

########NEW FILE########
__FILENAME__ = deletenotificationconfiguration
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DeleteNotificationConfiguration(AutoScalingRequest):
    DESCRIPTION = "Delete an auto-scaling group's notification configuration"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('-t', '--topic-arn', dest='TopicARN', metavar='TOPIC',
                required=True, help='''ARN of the SNS topic associated with the
                configuration to delete'''),
            Arg('-f', '--force', route_to=None, action='store_true',
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deletepolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DeletePolicy(AutoScalingRequest):
    DESCRIPTION = 'Delete a scaling policy'
    ARGS = [Arg('PolicyName', metavar='POLICY',
                help='name of the policy to delete (required)'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP', required=True,
                help='''name of the auto-scaling group the policy is associated
                with (required)'''),
            Arg('-f', '--force', route_to=None, action='store_true',
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deletescheduledaction
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DeleteScheduledAction(AutoScalingRequest):
    DESCRIPTION = 'Delete a scheduled action'
    ARGS = [Arg('ScheduledActionName', metavar='ACTION',
                help='name of the scheduled action to delete (required)'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP', required=True,
                help='''name of the auto-scaling group the scheduled action is
                associated with (required)'''),
            Arg('-f', '--force', route_to=None, action='store_true',
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deletetags
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from euca2ools.commands.autoscaling.arghelpers import TagArg


class DeleteTags(AutoScalingRequest):
    DESCRIPTION = 'Delete one or more resource tags'
    ARGS = [TagArg(required=True)]

########NEW FILE########
__FILENAME__ = describeaccountlimits
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder.mixins import TabifyingMixin

from euca2ools.commands.autoscaling import AutoScalingRequest


class DescribeAccountLimits(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = "Describe your account's limits on auto-scaling resources"

    def print_result(self, result):
        for key, val in sorted(result.items()):
            print self.tabify((key, val))

########NEW FILE########
__FILENAME__ = describeadjustmenttypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder.mixins import TabifyingMixin


class DescribeAdjustmentTypes(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = ('Describe policy adjustment types usable with scaling '
                   'policies')
    LIST_TAGS = ['AdjustmentTypes']

    def print_result(self, result):
        for adj_type in result.get('AdjustmentTypes', []):
            print self.tabify(('ADJUSTMENT-TYPE',
                               adj_type.get('AdjustmentType')))

########NEW FILE########
__FILENAME__ = describeautoscalinggroups
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeAutoScalingGroups(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe auto-scaling groups'
    ARGS = [Arg('AutoScalingGroupNames.member', metavar='ASGROUP',
                nargs='*',
                help='limit results to specific auto-scaling groups'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the groups' info")]
    LIST_TAGS = ['AutoScalingGroups', 'AvailabilityZones', 'EnabledMetrics',
                 'Instances', 'LoadBalancerNames', 'SuspendedProcesses',
                 'Tags', 'TerminationPolicies']

    def main(self):
        return PaginatedResponse(self, (None,), ('AutoScalingGroups',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        lines = []
        for group in result.get('AutoScalingGroups', []):
            bits = ['AUTO-SCALING-GROUP',
                    group.get('AutoScalingGroupName'),
                    group.get('LaunchConfigurationName'),
                    ','.join(group.get('AvailabilityZones'))]
            if self.args['show_long']:
                bits.append(group.get('CreatedTime'))
            balancers = group.get('LoadBalancerNames')
            if balancers:
                bits.append(','.join(balancers))
            else:
                bits.append(None)
            if self.args['show_long']:
                bits.append(group.get('HealthCheckType'))
            bits.append(group.get('MinSize'))
            bits.append(group.get('MaxSize'))
            bits.append(group.get('DesiredCapacity'))
            if self.args['show_long']:
                bits.append(group.get('DefaultCooldown'))
                bits.append(group.get('HealthCheckGracePeriod'))
                bits.append(group.get('VPCZoneIdentifier'))
                bits.append(group.get('PlacementGroup'))
                bits.append(group.get('AutoScalingGroupARN'))
            policies = group.get('TerminationPolicies')
            if policies:
                bits.append(','.join(policies))
            else:
                bits.append(None)
            lines.append(self.tabify(bits))
            for instance in group.get('Instances', []):
                lines.append(self._get_tabified_instance(instance))
            scale_group = group.get('AutoScalingGroupName')
            for process in group.get('SuspendedProcesses', []):
                lines.append(self._get_tabified_suspended_process(process,
                                                                  scale_group))
            for metric in group.get('EnabledMetrics', []):
                lines.append(self._get_tabified_metric(metric))
        for line in lines:
            print line

    def _get_tabified_instance(self, instance):
        return self.tabify(['INSTANCE',
                            instance.get('InstanceId'),
                            instance.get('AvailabilityZone'),
                            instance.get('LifecycleState'),
                            instance.get('HealthStatus'),
                            instance.get('LaunchConfigurationName')
                            ])

    def _get_tabified_suspended_process(self, process, scale_group):
        return self.tabify(['SUSPENDED-PROCESS',
                            process.get('ProcessName'),
                            process.get('SuspensionReason'),
                            scale_group
                            ])

    def _get_tabified_metric(self, metric):
        return self.tabify(['ENABLED-METRICS',
                            metric.get('Metric'),
                            metric.get('Granularity')
                            ])

########NEW FILE########
__FILENAME__ = describeautoscalinginstances
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeAutoScalingInstances(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe instances in auto-scaling groups'
    ARGS = [Arg('InstanceIds.member', metavar='INSTANCE', nargs='*',
                help='limit results to specific instances'),
            Arg('--show-long', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # Often typed out of habit
    LIST_TAGS = ['AutoScalingInstances']

    def main(self):
        return PaginatedResponse(self, (None,), ('AutoScalingInstances',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for instance in result.get('AutoScalingInstances', []):
            print self.tabify(('INSTANCE',
                               instance.get('InstanceId'),
                               instance.get('AutoScalingGroupName'),
                               instance.get('AvailabilityZone'),
                               instance.get('LifecycleState'),
                               instance.get('HealthStatus'),
                               instance.get('LaunchConfigurationName')))

########NEW FILE########
__FILENAME__ = describeautoscalingnotificationtypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder.mixins import TabifyingMixin


class DescribeAutoScalingNotificationTypes(AutoScalingRequest,
                                           TabifyingMixin):
    DESCRIPTION = 'List all notification types supported by the service'
    LIST_TAGS = ['AutoScalingNotificationTypes']

    def print_result(self, result):
        for notif_type in result.get('AutoScalingNotificationTypes', []):
            print self.tabify(('NOTIFICATION-TYPE', notif_type))

########NEW FILE########
__FILENAME__ = describelaunchconfigurations
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeLaunchConfigurations(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe auto-scaling instance launch configurations'
    ARGS = [Arg('LaunchConfigurationNames.member', metavar='LAUNCHCONFIG',
                nargs='*',
                help='limit results to specific launch configurations'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the launch configurations' info")]
    LIST_TAGS = ['LaunchConfigurations', 'SecurityGroups',
                 'BlockDeviceMappings']

    def main(self):
        return PaginatedResponse(self, (None,), ('LaunchConfigurations',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for config in result.get('LaunchConfigurations', []):
            bits = ['LAUNCH-CONFIG',
                    config.get('LaunchConfigurationName'),
                    config.get('ImageId'),
                    config.get('InstanceType')]
            if self.args['show_long']:
                bits.append(config.get('KeyName'))
                bits.append(config.get('KernelId'))
                bits.append(config.get('RamdiskId'))
                block_maps = [convert_block_mapping_to_str(mapping) for mapping
                              in config.get('BlockDeviceMappings', [])]
                if len(block_maps) > 0:
                    bits.append('{' + ','.join(block_maps) + '}')
                else:
                    bits.append(None)
                bits.append(','.join(config.get('SecurityGroups', [])) or None)
                bits.append(config.get('CreatedTime'))
                bits.append(config.get('InstanceMonitoring', {}).get(
                    'Enabled'))
                bits.append(config.get('LaunchConfigurationARN'))
            bits.append(config.get('SpotPrice'))
            bits.append(config.get('IamInstanceProfile'))
            if self.args['show_long']:
                bits.append(config.get('EbsOptimized'))
            print self.tabify(bits)


def convert_block_mapping_to_str(mapping):
    if mapping.get('Ebs'):
        mapped = ':'.join((mapping['Ebs'].get('SnapshotId') or '',
                           mapping['Ebs'].get('VolumeSize') or ''))
    elif mapping.get('VirtualName'):
        mapped = mapping['VirtualName']
    else:
        raise ValueError('unexpected block device mapping: {0}'.format(
            mapping))
    return mapping['DeviceName'] + '=' + mapped

########NEW FILE########
__FILENAME__ = describemetriccollectiontypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder.mixins import TabifyingMixin


class DescribeMetricCollectionTypes(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe auto-scaling metrics and granularities'
    LIST_TAGS = ['Metrics', 'Granularities']

    def print_result(self, result):
        for metric in result.get('Metrics', []):
            print self.tabify(('METRIC-COLLECTION-TYPE', metric.get('Metric')))
        for granularity in result.get('Granularities', []):
            print self.tabify(('METRIC-GRANULARITY-TYPE',
                               granularity.get('Granularity')))

########NEW FILE########
__FILENAME__ = describenotificationconfigurations
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeNotificationConfigurations(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = ('Describe notification actions associated with '
                   'auto-scaling groups')
    ARGS = [Arg('AutoScalingGroupNames.member', metavar='ASGROUP',
                nargs='*',
                help='limit results to specific auto-scaling groups')]
    LIST_TAGS = ['NotificationConfigurations']

    def main(self):
        return PaginatedResponse(self, (None,),
                                 ('NotificationConfigurations',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for config in result.get('NotificationConfigurations', []):
            print self.tabify(('NOTIFICATION-CONFIG',
                               config.get('AutoScalingGroupName'),
                               config.get('TopicARN'),
                               config.get('NotificationType')))

########NEW FILE########
__FILENAME__ = describepolicies
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribePolicies(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe auto-scaling policies'
    ARGS = [Arg('PolicyNames.member', metavar='POLICY', nargs='*',
                help='limit results to specific auto-scaling policies'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the policies' info")]
    LIST_TAGS = ['ScalingPolicies', 'Alarms']

    def main(self):
        return PaginatedResponse(self, (None,), ('ScalingPolicies',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for policy in result.get('ScalingPolicies', []):
            bits = ['SCALING-POLICY',
                    policy.get('AutoScalingGroupName'),
                    policy.get('PolicyName'),
                    policy.get('ScalingAdjustment')]
            if self.args['show_long']:
                bits.append(policy.get('MinAdjustmentStep'))
            bits.append(policy.get('AdjustmentType'))
            if self.args['show_long']:
                bits.append(policy.get('Cooldown'))
            bits.append(policy.get('PolicyARN'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describescalingactivities
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeScalingActivities(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe past and current auto-scaling activities'
    ARGS = [Arg('ActivityIds.member', metavar='ACTIVITY', nargs='*',
                help='limit results to specific auto-scaling activities'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP', help='''name of an Auto Scaling group by
                which to filter the request'''),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the activities' info")]
    LIST_TAGS = ['Activities']

    def main(self):
        return PaginatedResponse(self, (None,), ('Activities',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for activity in result.get('Activities', []):
            bits = ['ACTIVITY',
                    activity.get('ActivityId'),
                    activity.get('EndTime'),
                    activity.get('AutoScalingGroupName'),
                    activity.get('StatusCode'),
                    activity.get('StatusMessage')]
            if self.args['show_long']:
                bits.append(activity.get('Cause'))
                bits.append(activity.get('Progress'))
                bits.append(activity.get('Description'))
                # The AWS tool refers to this as "UPDATE-TIME", but seeing as
                # the API doesn't actually have anything like that, the process
                # of elimination dictates that this be the Details element in
                # the response instead.
                bits.append(activity.get('Details'))
                bits.append(activity.get('StartTime'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describescalingprocesstypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder.mixins import TabifyingMixin


class DescribeScalingProcessTypes(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'List all types of scaling processes'
    LIST_TAGS = ['Processes']

    def print_result(self, result):
        for process in result.get('Processes', []):
            print self.tabify(('PROCESS', process.get('ProcessName')))

########NEW FILE########
__FILENAME__ = describescheduledactions
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeScheduledActions(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe scheduled auto-scaling group actions'
    ARGS = [Arg('ScheduledActionNames.member', metavar='ACTION', nargs='*',
                help='limit results to specific actions'),
            Arg('-g', '--group', dest='AutoScalingGroupName',
                metavar='ASGROUP'),
            Arg('--start-time', dest='StartTime',
                metavar='YYYY-MM-DDThh:mm:ssZ', help='''earliest start time to
                return scheduled actions for.  This is ignored when specific
                action names are provided.'''),
            Arg('--end-time', dest='EndTime',
                metavar='YYYY-MM-DDThh:mm:ssZ', help='''latest start time to
                return scheduled actions for.  This is ignored when specific
                action names are provided.'''),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the scheduled actions' info")]
    LIST_TAGS = ['ScheduledUpdateGroupActions']

    def main(self):
        return PaginatedResponse(self, (None,),
                                 ('ScheduledUpdateGroupActions',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for action in result.get('ScheduledUpdateGroupActions', []):
            bits = ['UPDATE-GROUP-ACTION',
                    action.get('AutoScalingGroupName'),
                    action.get('ScheduledActionName'),
                    action.get('StartTime'),
                    action.get('Recurrence'),
                    action.get('MinSize'),
                    action.get('MaxSize'),
                    action.get('DesiredCapacity')]
            if self.args['show_long']:
                bits.append(action.get('ScheduledActionARN'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describetags
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from euca2ools.commands.autoscaling.argtypes import autoscaling_filter_def
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeTags(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'Describe auto-scaling tags'
    ARGS = [Arg('--filter', dest='Filters.member', type=autoscaling_filter_def,
                metavar='NAME=VALUE,...', action='append',
                help='restrict results to those that meet criteria')]
    LIST_TAGS = ['Tags']

    def main(self):
        return PaginatedResponse(self, (None,), ('Tags',))

    def prepare_for_page(self, page):
        # Pages are defined by NextToken
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for tag in result.get('Tags', []):
            print self.tabify(('TAG', tag.get('ResourceId'),
                               tag.get('ResourceType'), tag.get('Key'),
                               tag.get('Value'), tag.get('PropagateAtLaunch')))

########NEW FILE########
__FILENAME__ = describeterminationpolicytypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder.mixins import TabifyingMixin


class DescribeTerminationPolicyTypes(AutoScalingRequest, TabifyingMixin):
    DESCRIPTION = 'List all termination policies supported by the service'
    LIST_TAGS = ['TerminationPolicyTypes']

    def print_result(self, result):
        for tp_type in result.get('TerminationPolicyTypes', []):
            print self.tabify(('TERMINATION-POLICY-TYPE', tp_type))

########NEW FILE########
__FILENAME__ = disablemetricscollection
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class DisableMetricsCollection(AutoScalingRequest):
    DESCRIPTION = "Disable monitoring of an auto-scaling group's group metrics"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('-m', '--metrics', dest='Metrics.member',
                metavar='METRIC1,METRIC2,...', type=delimited_list(','),
                help='list of metrics to disable (default: all metrics)')]

########NEW FILE########
__FILENAME__ = enablemetricscollection
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class EnableMetricsCollection(AutoScalingRequest):
    DESCRIPTION = "Enable monitoring of an auto-scaling group's group metrics"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('-g', '--granularity', dest='Granularity', required=True,
                help='''granularity at which to collect metrics (e.g.,
                '1Minute') (required)'''),
            Arg('-m', '--metrics', dest='Metrics.member',
                metavar='METRIC1,METRIC2,...', type=delimited_list(','),
                help='list of metrics to collect (default: all metrics)')]

########NEW FILE########
__FILENAME__ = executepolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class ExecutePolicy(AutoScalingRequest):
    DESCRIPTION = "Manually set an auto-scaling instance's health status"
    ARGS = [Arg('PolicyName', metavar='POLICY',
                help='name or ARN of the policy to run (required)'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP',
                help='name or ARN of the auto-scaling group'),
            Arg('-h', '--honor-cooldown', dest='HonorCooldown',
                action='store_const', const='true',
                help='''reject the request if the group is in cooldown
                (default: override any cooldown period)'''),
            Arg('-H', '--no-honor-cooldown', dest='HonorCooldown',
                action='store_const', const='false',
                help='override any cooldown period (this is the default)')]

########NEW FILE########
__FILENAME__ = putnotificationconfiguration
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class PutNotificationConfiguration(AutoScalingRequest):
    DESCRIPTION = ("Create or replace an auto-scaling group's notification "
                   "configuration")
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('-n', '--notification-types', dest='NotificationTypes.member',
                metavar='TYPE1,TYPE2,...', type=delimited_list(','),
                required=True, help=('''comma-separated list of event types
                that will trigger notification (required)''')),
            Arg('-t', '--topic-arn', dest='TopicARN', metavar='TOPIC',
                required=True, help='''ARN of the SNS topic to publish
                notifications to (required)''')]

########NEW FILE########
__FILENAME__ = putscalingpolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class PutScalingPolicy(AutoScalingRequest):
    DESCRIPTION = "Create or update an auto-scaling group's scaling policy"
    ARGS = [Arg('PolicyName', metavar='POLICY',
                help='name of the policy to create or update (required)'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP', required=True,
                help='''name of the auto-scaling group the policy is associated
                with (required)'''),
            Arg('-a', '--adjustment', dest='ScalingAdjustment',
                metavar='SCALE', type=int, required=True,
                help='''amount to scale the group's capacity of the group.  Use
                a negative value, as in "--adjustment=-1", to decrease
                capacity. (required)'''),
            Arg('-t', '--type', dest='AdjustmentType', required=True,
                choices=('ChangeInCapacity', 'ExactCapacity',
                         'PercentChangeInCapacity'), help='''whether the
                adjustment is the new desired size or an increment to the
                group's current capacity. An increment can either be a fixed
                number or a percentage of current capacity.  (required)'''),
            Arg('--cooldown', dest='Cooldown', metavar='SECONDS', type=int,
                help='''waiting period after successful auto-scaling activities
                during which later auto-scaling activities will not
                execute'''),
            Arg('-s', '--min-adjustment-step', dest='MinAdjustmentStep',
                type=int, metavar='PERCENT',
                help='''for a PercentChangeInCapacity type policy, guarantee
                that this policy will change the group's desired capacity by at
                least this much''')]

    def print_result(self, result):
        print result.get('PolicyARN')

########NEW FILE########
__FILENAME__ = putscheduledupdategroupaction
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class PutScheduledUpdateGroupAction(AutoScalingRequest):
    DESCRIPTION = 'Schedule a scaling action for an auto-scaling group'
    ARGS = [Arg('ScheduledActionName', metavar='ACTION',
                help='name of the new scheduled action'),
            Arg('-g', '--auto-scaling-group', dest='AutoScalingGroupName',
                metavar='ASGROUP', required=True, help='''auto-scaling group
                the new action should affect (required)'''),
            Arg('-b', '--start-time', dest='StartTime',
                metavar='YYYY-MM-DDThh:mm:ssZ',
                help='time for this action to start'),
            Arg('-e', '--end-time', dest='EndTime',
                metavar='YYYY-MM-DDThh:mm:ssZ',
                help='time for this action to end'),
            Arg('-r', '--recurrence', dest='Recurrence',
                metavar='"MIN HOUR DATE MONTH DAY"', help='''time when
                recurring future actions will start, in crontab format'''),
            Arg('--desired-capacity', dest='DesiredCapacity', metavar='COUNT',
                type=int, help='new capacity setting for the group'),
            Arg('--max-size', dest='MaxSize', metavar='COUNT', type=int,
                help='maximum number of instances to allow in the group'),
            Arg('--min-size', dest='MinSize', metavar='COUNT', type=int,
                help='minimum number of instances to allow in the group')]

########NEW FILE########
__FILENAME__ = resumeprocesses
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class ResumeProcesses(AutoScalingRequest):
    DESCRIPTION = "Resume an auto-scaling group's auto-scaling processes"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('--processes', dest='ScalingProcesses.member',
                metavar='PROCESS1,PROCESS2,...', type=delimited_list(','),
                help='''comma-separated list of auto-scaling processes to
                resume (default: all processes)''')]

########NEW FILE########
__FILENAME__ = setdesiredcapacity
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class SetDesiredCapacity(AutoScalingRequest):
    DESCRIPTION = "Set an auto-scaling group's desired capacity"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('-c', '--desired-capacity', dest='DesiredCapacity', type=int,
                required=True,
                help='new capacity setting for the group (required)'),
            Arg('-h', '--honor-cooldown', dest='HonorCooldown',
                action='store_const', const='true',
                help='''reject the request if the group is in cooldown
                (default: override any cooldown period)'''),
            Arg('-H', '--no-honor-cooldown', dest='HonorCooldown',
                action='store_const', const='false',
                help='override any cooldown period (this is the default)')]

########NEW FILE########
__FILENAME__ = setinstancehealth
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class SetInstanceHealth(AutoScalingRequest):
    DESCRIPTION = "Manually set an auto-scaling instance's health status"
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to update (required)'),
            Arg('-s', '--status', dest='HealthStatus', required=True,
                choices=('Healthy', 'Unhealthy'),
                help='new status (required)'),
            Arg('--respect-grace-period', dest='ShouldRespectGracePeriod',
                action='store_const', const='true',
                help="""respect the associated auto-scaling group's grace
                period (this is the default)"""),
            Arg('--no-respect-grace-period', dest='ShouldRespectGracePeriod',
                action='store_const', const='false',
                help="""ignore the associated auto-scaling group's grace period
                (default: respect the group's grace period)""")]

########NEW FILE########
__FILENAME__ = suspendprocesses
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class SuspendProcesses(AutoScalingRequest):
    DESCRIPTION = "Suspend an auto-scaling group's auto-scaling processes"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('--processes', dest='ScalingProcesses.member',
                metavar='PROCESS1,PROCESS2,...', type=delimited_list(','),
                help='''comma-separated list of auto-scaling processes to
                suspend (default: all processes)''')]

########NEW FILE########
__FILENAME__ = terminateinstanceinautoscalinggroup
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.mixins import TabifyingMixin

from euca2ools.commands.autoscaling import AutoScalingRequest


class TerminateInstanceInAutoScalingGroup(AutoScalingRequest,
                                          TabifyingMixin):
    DESCRIPTION = "Manually terminate an auto-scaling instance"
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to terminate (required)'),
            MutuallyExclusiveArgList(
                Arg('-d', '--decrement-desired-capacity', action='store_const',
                    dest='ShouldDecrementDesiredCapacity', const='true',
                    help='''also reduce the desired capacity of the
                    auto-scaling group by 1'''),
                Arg('-D', '--no-decrement-desired-capacity',
                    dest='ShouldDecrementDesiredCapacity',
                    action='store_const', const='false',
                    help='''leave the auto-scaling group's desired capacity
                    as-is.  A new instance may be launched to compensate for
                    the one being terminated.'''))
            .required(),
            Arg('--show-long', action='store_true', route_to=None,
                help='show extra info about the instance being terminated'),
            Arg('-f', '--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

    def print_result(self, result):
        activity = result['Activity']
        bits = ['INSTANCE',
                activity.get('ActivityId'),
                activity.get('EndTime'),
                activity.get('StatusCode'),
                activity.get('Cause')]
        if self.args['show_long']:
            bits.append(activity.get('StatusMessage'))
            bits.append(activity.get('Progress'))
            bits.append(activity.get('Description'))
            bits.append(activity.get('StartTime'))
        print self.tabify(bits)

########NEW FILE########
__FILENAME__ = updateautoscalinggroup
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.autoscaling import AutoScalingRequest
from requestbuilder import Arg


class UpdateAutoScalingGroup(AutoScalingRequest):
    DESCRIPTION = "Update an auto-scaling group's parameters"
    ARGS = [Arg('AutoScalingGroupName', metavar='ASGROUP',
                help='name of the auto-scaling group to update (required)'),
            Arg('--default-cooldown', dest='DefaultCooldown',
                metavar='SECONDS', type=int,
                help='''amount of time, in seconds, after a scaling activity
                        completes before any further trigger-related scaling
                        activities may start'''),
            Arg('--desired-capacity', dest='DesiredCapacity', metavar='COUNT',
                type=int,
                help='number of running instances the group should contain'),
            Arg('--grace-period', dest='HealthCheckGracePeriod',
                metavar='SECONDS', type=int, help='''number of seconds to wait
                before starting health checks on newly-created instances'''),
            Arg('--health-check-type', dest='HealthCheckType',
                choices=('EC2', 'ELB'),
                help='service to obtain health check status from'),
            Arg('-l', '--launch-configuration', dest='LaunchConfigurationName',
                metavar='LAUNCHCONFIG', help='''name of the launch
                configuration to use with the new group (required)'''),
            Arg('-M', '--max-size', dest='MaxSize', metavar='COUNT', type=int,
                help='maximum group size (required)'),
            Arg('-m', '--min-size', dest='MinSize', metavar='COUNT', type=int,
                help='minimum group size (required)'),
            Arg('--placement-group', dest='PlacementGroup',
                help='placement group in which to launch new instances'),
            Arg('--termination-policies', dest='TerminationPolicies.member',
                metavar='POLICY1,POLICY2,...', type=delimited_list(','),
                help='''ordered list of termination policies.  The first has
                the highest precedence.'''),
            Arg('--vpc-zone-identifier', dest='VPCZoneIdentifier',
                metavar='ZONE1,ZONE2,...',
                help='''comma-separated list of subnet identifiers.  If you
                specify availability zones as well, ensure the subnets'
                availability zones match the ones you specified'''),
            Arg('-z', '--availability-zones', dest='AvailabilityZones.member',
                metavar='ZONE1,ZONE2,...', type=delimited_list(','),
                help='''comma-separated list of availability zones for the new
                group (required unless subnets are supplied)''')]

########NEW FILE########
__FILENAME__ = bundleanduploadimage
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import multiprocessing
import os.path
import tarfile

from requestbuilder import Arg
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.bundle.pipes.core import create_bundle_pipeline
from euca2ools.bundle.pipes.fittings import (create_bundle_part_deleter,
                                             create_bundle_part_writer,
                                             create_mpconn_aggregator)
import euca2ools.bundle.manifest
import euca2ools.bundle.util
from euca2ools.commands.bundle.mixins import (BundleCreatingMixin,
                                              BundleUploadingMixin)
from euca2ools.commands.s3 import S3Request
from euca2ools.util import mkdtemp_for_large_files


class BundleAndUploadImage(S3Request, BundleCreatingMixin,
                           BundleUploadingMixin,
                           FileTransferProgressBarMixin):
    DESCRIPTION = 'Prepare and upload an image for use in the cloud'
    ARGS = [Arg('--preserve-bundle', action='store_true',
                help='do not delete the bundle as it is being uploaded'),
            Arg('--max-pending-parts', type=int, default=2,
                help='''pause the bundling process when more than this number
                of parts are waiting to be uploaded (default: 2)''')]

    # noinspection PyExceptionInherit
    def configure(self):
        self.configure_bundle_upload_auth()

        S3Request.configure(self)

        self.configure_bundle_creds()
        self.configure_bundle_properties()
        self.configure_bundle_output()
        self.generate_encryption_keys()

    def main(self):
        if self.args.get('destination'):
            path_prefix = os.path.join(self.args['destination'],
                                       self.args['prefix'])
            if not os.path.exists(self.args['destination']):
                os.mkdir(self.args['destination'])
        else:
            tempdir = mkdtemp_for_large_files(prefix='bundle-')
            path_prefix = os.path.join(tempdir, self.args['prefix'])
        self.log.debug('bundle path prefix: %s', path_prefix)

        key_prefix = self.get_bundle_key_prefix()
        self.ensure_dest_bucket_exists()

        # First create the bundle and upload it to the server
        digest, partinfo = self.create_and_upload_bundle(path_prefix,
                                                         key_prefix)

        # All done; now build the manifest, write it to disk, and upload it.
        manifest = self.build_manifest(digest, partinfo)
        manifest_filename = '{0}.manifest.xml'.format(path_prefix)
        with open(manifest_filename, 'w') as manifest_file:
            manifest.dump_to_file(manifest_file, self.args['privatekey'],
                                  self.args['cert'], self.args['ec2cert'])
        manifest_dest = key_prefix + os.path.basename(manifest_filename)
        self.upload_bundle_file(manifest_filename, manifest_dest,
                                show_progress=self.args.get('show_progress'))
        if not self.args.get('preserve_bundle', False):
            os.remove(manifest_filename)

        # Then we just inform the caller of all the files we wrote.
        # Manifests are returned in a tuple for future expansion, where we
        # bundle for more than one region at a time.
        return {'parts': tuple({'filename': part.filename,
                                'key': (key_prefix +
                                        os.path.basename(part.filename))}
                               for part in manifest.image_parts),
                'manifests': ({'filename': manifest_filename,
                               'key': manifest_dest},)}

    def print_result(self, result):
        if self.debug:
            for part in result['parts']:
                print 'Uploaded', part['key']
        if result['manifests'][0]['key'] is not None:
            print 'Uploaded', result['manifests'][0]['key']

    def create_and_upload_bundle(self, path_prefix, key_prefix):
        part_write_sem = multiprocessing.Semaphore(
            max(1, self.args['max_pending_parts']))

        # Fill out all the relevant info needed for a tarball
        tarinfo = tarfile.TarInfo(self.args['prefix'])
        tarinfo.size = self.args['image_size']

        # disk --(bytes)-> bundler
        partwriter_in_r, partwriter_in_w = \
            euca2ools.bundle.util.open_pipe_fileobjs()
        digest_result_mpconn = create_bundle_pipeline(
            self.args['image'], partwriter_in_w, self.args['enc_key'],
            self.args['enc_iv'], tarinfo, debug=self.debug)
        partwriter_in_w.close()

        # bundler --(bytes)-> part writer
        bundle_partinfo_mpconn = create_bundle_part_writer(
            partwriter_in_r, path_prefix, self.args['part_size'],
            part_write_sem=part_write_sem, debug=self.debug)
        partwriter_in_r.close()

        # part writer --(part info)-> part uploader
        # This must be driven on the main thread since it has a progress bar,
        # so for now we'll just set up its output pipe so we can attach it to
        # the remainder of the pipeline.
        uploaded_partinfo_mpconn_r, uploaded_partinfo_mpconn_w = \
            multiprocessing.Pipe(duplex=False)

        # part uploader --(part info)-> part deleter
        if not self.args.get('preserve_bundle', False):
            deleted_partinfo_mpconn_r, deleted_partinfo_mpconn_w = \
                multiprocessing.Pipe(duplex=False)
            create_bundle_part_deleter(uploaded_partinfo_mpconn_r,
                                       out_mpconn=deleted_partinfo_mpconn_w)
            uploaded_partinfo_mpconn_r.close()
            deleted_partinfo_mpconn_w.close()
        else:
            # Bypass this stage
            deleted_partinfo_mpconn_r = uploaded_partinfo_mpconn_r

        # part deleter --(part info)-> part info aggregator
        # (needed for building the manifest)
        bundle_partinfo_aggregate_mpconn = create_mpconn_aggregator(
            deleted_partinfo_mpconn_r, debug=self.debug)
        deleted_partinfo_mpconn_r.close()

        # Now drive the pipeline by uploading parts.
        try:
            self.upload_bundle_parts(
                bundle_partinfo_mpconn, key_prefix,
                partinfo_out_mpconn=uploaded_partinfo_mpconn_w,
                part_write_sem=part_write_sem,
                show_progress=self.args.get('show_progress'))
        finally:
            # Make sure the writer gets a chance to exit
            part_write_sem.release()

        # All done; now grab info about the bundle we just created
        try:
            digest = digest_result_mpconn.recv()
            partinfo = bundle_partinfo_aggregate_mpconn.recv()
        except EOFError:
            self.log.debug('EOFError from reading bundle info', exc_info=True)
            raise RuntimeError(
                'corrupt bundle: bundle process was interrupted')
        finally:
            digest_result_mpconn.close()
            bundle_partinfo_aggregate_mpconn.close()
        self.log.info('%i bundle parts uploaded to %s', len(partinfo),
                      self.args['bucket'])
        self.log.debug('bundle digest: %s', digest)
        return digest, partinfo

########NEW FILE########
__FILENAME__ = bundleimage
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os.path
import tarfile

from requestbuilder.command import BaseCommand
from requestbuilder.mixins import (FileTransferProgressBarMixin,
                                   RegionConfigurableMixin)

import euca2ools.bundle.manifest
from euca2ools.bundle.pipes.core import (create_bundle_pipeline,
                                         copy_with_progressbar)
from euca2ools.bundle.pipes.fittings import (create_bundle_part_writer,
                                             create_mpconn_aggregator)
import euca2ools.bundle.util
from euca2ools.commands import Euca2ools
from euca2ools.commands.bundle.mixins import BundleCreatingMixin
from euca2ools.util import mkdtemp_for_large_files, substitute_euca_region


class BundleImage(BaseCommand, BundleCreatingMixin,
                  FileTransferProgressBarMixin,
                  RegionConfigurableMixin):
    SUITE = Euca2ools
    DESCRIPTION = 'Prepare an image for use in the cloud'
    REGION_ENVVAR = 'AWS_DEFAULT_REGION'

    # noinspection PyExceptionInherit
    def configure(self):
        substitute_euca_region(self)
        self.update_config_view()

        BaseCommand.configure(self)

        self.configure_bundle_creds()
        self.configure_bundle_properties()
        self.configure_bundle_output()
        self.generate_encryption_keys()

    def main(self):
        if self.args.get('destination'):
            path_prefix = os.path.join(self.args['destination'],
                                       self.args['prefix'])
            if not os.path.exists(self.args['destination']):
                os.mkdir(self.args['destination'])
        else:
            tempdir = mkdtemp_for_large_files(prefix='bundle-')
            path_prefix = os.path.join(tempdir, self.args['prefix'])
        self.log.debug('bundle path prefix: %s', path_prefix)

        # First create the bundle
        digest, partinfo = self.create_bundle(path_prefix)

        # All done; now build the manifest and write it to disk
        manifest = self.build_manifest(digest, partinfo)
        manifest_filename = '{0}.manifest.xml'.format(path_prefix)
        with open(manifest_filename, 'w') as manifest_file:
            manifest.dump_to_file(manifest_file, self.args['privatekey'],
                                  self.args['cert'], self.args['ec2cert'])

        # Then we just inform the caller of all the files we wrote.
        # Manifests are returned in a tuple for future expansion, where we
        # bundle for more than one region at a time.
        return (part.filename for part in partinfo), (manifest_filename,)

    def print_result(self, result):
        for manifest_filename in result[1]:
            print 'Wrote manifest', manifest_filename

    def create_bundle(self, path_prefix):
        # Fill out all the relevant info needed for a tarball
        tarinfo = tarfile.TarInfo(self.args['prefix'])
        tarinfo.size = self.args['image_size']

        # The pipeline begins with self.args['image'] feeding a bundling pipe
        # segment through a progress meter, which has to happen on the main
        # thread, so we add that to the pipeline last.

        # meter --(bytes)--> bundler
        bundle_in_r, bundle_in_w = euca2ools.bundle.util.open_pipe_fileobjs()
        partwriter_in_r, partwriter_in_w = \
            euca2ools.bundle.util.open_pipe_fileobjs()
        digest_result_mpconn = create_bundle_pipeline(
            bundle_in_r, partwriter_in_w, self.args['enc_key'],
            self.args['enc_iv'], tarinfo, debug=self.debug)
        bundle_in_r.close()
        partwriter_in_w.close()

        # bundler --(bytes)-> part writer
        bundle_partinfo_mpconn = create_bundle_part_writer(
            partwriter_in_r, path_prefix, self.args['part_size'],
            debug=self.debug)
        partwriter_in_r.close()

        # part writer --(part info)-> part info aggregator
        # (needed for building the manifest)
        bundle_partinfo_aggr_mpconn = create_mpconn_aggregator(
            bundle_partinfo_mpconn, debug=self.debug)
        bundle_partinfo_mpconn.close()

        # disk --(bytes)-> bundler
        # (synchronous)
        label = self.args.get('progressbar_label') or 'Bundling image'
        pbar = self.get_progressbar(label=label,
                                    maxval=self.args['image_size'])
        with self.args['image'] as image:
            try:
                read_size = copy_with_progressbar(image, bundle_in_w,
                                                  progressbar=pbar)
            except ValueError:
                self.log.debug('error from copy_with_progressbar',
                               exc_info=True)
                raise RuntimeError('corrupt bundle: input size was larger '
                                   'than expected image size of {0}'
                                   .format(self.args['image_size']))
        bundle_in_w.close()
        if read_size != self.args['image_size']:
            raise RuntimeError('corrupt bundle: input size did not match '
                               'expected image size  (expected size: {0}, '
                               'read: {1})'
                               .format(self.args['image_size'], read_size))

        # All done; now grab info about the bundle we just created
        try:
            digest = digest_result_mpconn.recv()
            partinfo = bundle_partinfo_aggr_mpconn.recv()
        except EOFError:
            self.log.debug('EOFError from reading bundle info', exc_info=True)
            raise RuntimeError(
                'corrupt bundle: bundle process was interrupted')
        finally:
            digest_result_mpconn.close()
            bundle_partinfo_aggr_mpconn.close()
        self.log.info('%i bundle parts written to %s', len(partinfo),
                      os.path.dirname(path_prefix))
        self.log.debug('bundle digest: %s', digest)
        return digest, partinfo

########NEW FILE########
__FILENAME__ = bundlevolume
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import os.path
import pipes
import shutil
import subprocess
import sys
import tempfile
import time

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.command import BaseCommand
from requestbuilder.exceptions import ArgumentError, ClientError
from requestbuilder.mixins import FileTransferProgressBarMixin
import requests

import euca2ools
from euca2ools.commands import Euca2ools, SYSCONFDIR
from euca2ools.commands.argtypes import (delimited_list, filesize,
                                         manifest_block_device_mappings)
from euca2ools.commands.bundle.bundleimage import BundleImage


ALLOWED_FILESYSTEM_TYPES = ['btrfs', 'ext2', 'ext3', 'ext4', 'jfs', 'xfs']
EXCLUDES_FILE = os.path.join(SYSCONFDIR, 'bundle-vol', 'excludes')
FSTAB_TEMPLATE_FILE = os.path.join(SYSCONFDIR, 'bundle-vol', 'fstab')


class BundleVolume(BaseCommand, FileTransferProgressBarMixin):
    SUITE = Euca2ools
    DESCRIPTION = ("Prepare this machine's filesystem for use in the cloud\n\n"
                   "This command must be run as the superuser.")
    REGION_ENVVAR = 'AWS_DEFAULT_REGION'
    ARGS = [Arg('-p', '--prefix', help='''the file name prefix to give the
                bundle's files (default: image)'''),
            Arg('-d', '--destination', metavar='DIR', help='''location to place
                the bundle's files (default:  dir named by TMPDIR, TEMP, or TMP
                environment variables, or otherwise /var/tmp)'''),
            # -r/--arch is required, but to keep the UID check we do at the
            # beginning of configure() first we enforce that there instead.
            Arg('-r', '--arch', help="the image's architecture (required)",
                choices=('i386', 'x86_64', 'armhf', 'ppc', 'ppc64')),
            Arg('-e', '--exclude', metavar='PATH,...',
                type=delimited_list(','),
                help='comma-separated list of paths to exclude'),
            Arg('-i', '--include', metavar='PATH,...',
                type=delimited_list(','),
                help='comma-separated list of paths to include'),
            Arg('-s', '--size', metavar='MiB', type=int, default=10240,
                help='size of the image to create (default: 10240 MiB)'),
            Arg('--no-filter', action='store_true',
                help='do not filter out sensitive/system files'),
            Arg('--all', action='store_true',
                help='''include all filesystems regardless of type
                (default: only include local filesystems)'''),
            MutuallyExclusiveArgList(
                Arg('--inherit', dest='inherit', action='store_true',
                    help='''use the metadata service to provide metadata for
                    the bundle (this is the default)'''),
                Arg('--no-inherit', dest='inherit', action='store_false',
                    help='''do not use the metadata service for bundle
                    metadata''')),
            Arg('-v', '--volume', metavar='DIR', default='/', help='''location
                of the volume from which to create the bundle (default: /)'''),
            Arg('-P', '--partition', choices=('mbr', 'gpt', 'none'),
                help='''the type of partition table to create (default: attempt
                to guess based on the existing disk)'''),
            Arg('-S', '--script', metavar='FILE', help='''location of a script
                to run immediately before bundling.  It will receive the
                volume's mount point as its only argument.'''),
            MutuallyExclusiveArgList(
                Arg('--fstab', metavar='FILE', help='''location of an
                    fstab(5) file to copy into the bundled image'''),
                Arg('--generate-fstab', action='store_true',
                    help='''automatically generate an fstab(5) file for
                    the bundled image''')),
            Arg('--grub-config', metavar='FILE', help='''location of a GRUB 1
                configuration file to copy to /boot/grub/menu.lst on the
                bundled image'''),

            # Bundle-related stuff
            Arg('-k', '--privatekey', metavar='FILE', help='''file containing
                your private key to sign the bundle's manifest with.  This
                private key will also be required to unbundle the image in the
                future.'''),
            Arg('-c', '--cert', metavar='FILE',
                help='file containing your X.509 certificate'),
            Arg('--ec2cert', metavar='FILE', help='''file containing the
                cloud's X.509 certificate'''),
            Arg('-u', '--user', metavar='ACCOUNT', help='your account ID'),
            Arg('--kernel', metavar='IMAGE', help='''ID of the kernel image to
                associate with this machine image'''),
            Arg('--ramdisk', metavar='IMAGE', help='''ID of the ramdisk image
                to associate with this machine image'''),
            Arg('-B', '--block-device-mappings',
                metavar='VIRTUAL1=DEVICE1,VIRTUAL2=DEVICE2,...',
                type=manifest_block_device_mappings,
                help='''block device mapping scheme with which to launch
                instances of this machine image'''),
            Arg('--productcodes', metavar='CODE1,CODE2,...',
                type=delimited_list(','), default=[],
                help='comma-separated list of product codes for the image'),
            Arg('--part-size', type=filesize, default=10485760,
                help=argparse.SUPPRESS),
            Arg('--enc-key', type=(lambda s: int(s, 16)),
                help=argparse.SUPPRESS),
            Arg('--enc-iv', type=(lambda s: int(s, 16)),
                help=argparse.SUPPRESS)]

    def configure(self):
        if os.geteuid() != 0:
            raise RuntimeError('must be superuser')

        if not self.args.get('arch'):
            raise ArgumentError('argument -r/--arch is required')

        # Farm all the bundle arg validation out to BundleImage
        self.__build_bundle_command('/dev/null', image_size=1)

        root_device = _get_root_device()
        if self.args.get('inherit'):
            self.__populate_args_from_metadata()
        if not self.args.get('partition'):
            self.args['partition'] = _get_partition_table_type(root_device)
            if not self.args['partition']:
                self.log.warn('could not determine the partition table type '
                              'for root device %s', root_device)
                raise ArgumentError(
                    'could not determine the type of partition table to use; '
                    'specify one with -P/--partition'.format(root_device))
            self.log.info('discovered partition table type %s',
                          self.args['partition'])
        if not self.args.get('fstab') and not self.args.get('generate_fstab'):
            self.args['fstab'] = '/etc/fstab'

    def main(self):
        if self.args.get('destination'):
            destdir = self.args['destination']
        else:
            destdir = euca2ools.util.mkdtemp_for_large_files(prefix='bundle-')
        image = os.path.join(destdir, self.args.get('prefix') or 'image')
        mountpoint = tempfile.mkdtemp(prefix='target-', dir=destdir)

        # Prepare the disk image
        device = self.__create_disk_image(image, self.args['size'])
        try:
            self.__create_and_mount_filesystem(device, mountpoint)
            try:
                # Copy files
                exclude_opts = self.__get_exclude_and_include_args()
                exclude_opts.extend(['--exclude', image,
                                     '--exclude', mountpoint])
                self.__copy_to_target_dir(mountpoint, exclude_opts)
                self.__insert_fstab(mountpoint)
                self.__insert_grub_config(mountpoint)
                if self.args.get('script'):
                    cmd = [self.args['script'], mountpoint]
                    self.log.info("running user script ``%s''",
                                  _quote_cmd(cmd))
                    subprocess.check_call(cmd)

            except KeyboardInterrupt:
                self.log.info('received ^C; skipping to cleanup')
                msg = ('Cleaning up after ^C -- pressing ^C again will '
                       'result in the need for manual device cleanup')
                print >> sys.stderr, msg
                raise
            # Cleanup
            finally:
                time.sleep(0.2)
                self.__unmount_filesystem(device)
                os.rmdir(mountpoint)
        finally:
            self.__detach_disk_image(image, device)

        bundle_cmd = self.__build_bundle_command(image)
        result = bundle_cmd.main()
        os.remove(image)
        return result

    def print_result(self, result):
        for manifest_filename in result[1]:
            print 'Wrote manifest', manifest_filename

    def __build_bundle_command(self, image_filename, image_size=None):
        bundle_args = ('prefix', 'destination', 'arch', 'privatekey', 'cert',
                       'ec2cert', 'user', 'kernel', 'ramdisk',
                       'block_device_mappings', 'productcodes', 'part_size',
                       'enc_key', 'enc_iv', 'show_progress')
        bundle_args_dict = dict((key, self.args.get(key))
                                for key in bundle_args)
        return BundleImage.from_other(self, image=image_filename,
                                      image_size=image_size,
                                      image_type='machine', **bundle_args_dict)

    # INSTANCE METADATA #

    def __read_metadata_value(self, path):
        self.log.debug("reading metadata service value '%s'", path)
        url = 'http://169.254.169.254/2012-01-12/meta-data/' + path
        response = requests.get(url, timeout=1)
        if response.status_code == 200:
            return response.text
        return None

    def __read_metadata_list(self, path):
        value = self.__read_metadata_value(path)
        if value:
            return [line.rstrip('/') for line in value.splitlines() if line]
        return []

    def __read_metadata_dict(self, path):
        metadata = {}
        if not path.endswith('/'):
            path += '/'
        keys = self.__read_metadata_list(path)
        for key in keys:
            if key:
                metadata[key] = self.__read_metadata_value(path + key)
        return metadata

    def __populate_args_from_metadata(self):
        """
        Populate missing/empty values in self.args using info obtained
        from the metadata service.
        """
        try:
            if not self.args.get('kernel'):
                self.args['kernel'] = self.__read_metadata_value('kernel-id')
                self.log.info('inherited kernel: %s', self.args['kernel'])
            if not self.args.get('ramdisk'):
                self.args['ramdisk'] = self.__read_metadata_value('ramdisk-id')
                self.log.info('inherited ramdisk: %s', self.args['ramdisk'])
            if not self.args.get('productcodes'):
                self.args['productcodes'] = self.__read_metadata_list(
                    'product-codes')
                if self.args['productcodes']:
                    self.log.info('inherited product codes: %s',
                                  ','.join(self.args['productcodes']))
            if not self.args.get('block_device_mappings'):
                self.args['block_device_mappings'] = {}
                for key, val in (self.__read_metadata_dict(
                        'block-device-mapping') or {}).iteritems():
                    if not key.startswith('ebs'):
                        self.args['block_device_mappings'][key] = val
                for key, val in self.args['block_device_mappings'].iteritems():
                    self.log.info('inherited block device mapping: %s=%s',
                                  key, val)
        except requests.exceptions.Timeout:
            raise ClientError('metadata service is absent or unresponsive; '
                              'use --no-inherit to proceed without it')

    # DISK MANAGEMENT #

    def __create_disk_image(self, image, size_in_mb):
        subprocess.check_call(['dd', 'if=/dev/zero', 'of={0}'.format(image),
                               'bs=1M', 'count=1',
                               'seek={0}'.format(int(size_in_mb) - 1)])
        if self.args['partition'] == 'mbr':
            # Why use sfdisk when we can use parted?  :-)
            parted_script = (
                b'unit s', b'mklabel msdos', b'mkpart primary 64 -1s',
                b'set 1 boot on', b'print', b'quit')
            subprocess.check_call(['parted', '-s', image, '--',
                                   ' '.join(parted_script)])
        elif self.args['partition'] == 'gpt':
            # type 0xef02 == BIOS boot (we'll put it at the end of the list)
            subprocess.check_call(
                ['sgdisk', '--new', '128:1M:+1M', '--typecode', '128:ef02',
                 '--change-name', '128:BIOS Boot', image])
            # type 0x8300 == Linux filesystem data
            subprocess.check_call(
                ['sgdisk', '--largest-new=1', '--typecode', '1:8300',
                 '--change-name', '1:Image', image])
            subprocess.check_call(['sgdisk', '--print', image])

        mapped = self.__map_disk_image(image)
        assert os.path.exists(mapped)
        return mapped

    def __map_disk_image(self, image):
        if self.args['partition'] in ('mbr', 'gpt'):
            # Create /dev/mapper/loopXpY and return that.
            # We could do this with losetup -Pf as well, but that isn't
            # available on RHEL 6.
            self.log.debug('mapping partitioned image %s', image)
            kpartx = subprocess.Popen(['kpartx', '-s', '-v', '-a', image],
                                      stdout=subprocess.PIPE)
            try:
                for line in kpartx.stdout.readlines():
                    line_split = line.split()
                    if line_split[:2] == ['add', 'map']:
                        device = line_split[2]
                        if device.endswith('p1'):
                            return '/dev/mapper/{0}'.format(device)
                self.log.error('failed to get usable map output from kpartx')
                raise RuntimeError('device mapping failed')
            finally:
                # Make sure the process exits
                kpartx.communicate()
        else:
            # No partition table
            self.log.debug('mapping unpartitioned image %s', image)
            losetup = subprocess.Popen(['losetup', '-f', image, '--show'],
                                       stdout=subprocess.PIPE)
            loopdev, _ = losetup.communicate()
            return loopdev.strip()

    def __create_and_mount_filesystem(self, device, mountpoint):
        root_device = _get_root_device()
        fsinfo = _get_filesystem_info(root_device)
        self.log.info('creating filesystem on %s using metadata from %s: %s',
                      device, root_device, fsinfo)
        fs_cmds = [['mkfs', '-t', fsinfo['type']]]
        if fsinfo.get('label'):
            fs_cmds[0].extend(['-L', fsinfo['label']])
        elif fsinfo['type'] in ('ext2', 'ext3', 'ext4'):
            if fsinfo.get('uuid'):
                fs_cmds[0].extend(['-U', fsinfo['uuid']])
            # Time-based checking doesn't make much sense for cloud images
            fs_cmds.append(['tune2fs', '-i', '0'])
        elif fsinfo['type'] == 'jfs':
            if fsinfo.get('uuid'):
                fs_cmds.append(['jfs_tune', '-U', fsinfo['uuid']])
        elif fsinfo['type'] == 'xfs':
            if fsinfo.get('uuid'):
                fs_cmds.append(['xfs_admin', '-U', fsinfo['uuid']])
        for fs_cmd in fs_cmds:
            fs_cmd.append(device)
            self.log.info("formatting with ``%s''", _quote_cmd(fs_cmd))
            subprocess.check_call(fs_cmd)
        self.log.info('mounting %s filesystem %s at %s', fsinfo['type'],
                      device, mountpoint)
        subprocess.check_call(['mount', '-t', fsinfo['type'], device,
                               mountpoint])

    def __unmount_filesystem(self, device):
        self.log.info('unmounting %s', device)
        subprocess.check_call(['sync'])
        time.sleep(0.2)
        subprocess.check_call(['umount', device])

    def __detach_disk_image(self, image, device):
        if self.args['partition'] in ('mbr', 'gpt'):
            self.log.debug('unmapping partitioned image %s', image)
            cmd = ['kpartx', '-s', '-d', image]
        else:
            self.log.debug('unmapping unpartitioned device %s', device)
            cmd = ['losetup', '-d', device]
        subprocess.check_call(cmd)

    # FILE MANAGEMENT #

    def __get_exclude_and_include_args(self):
        args = []
        for exclude in self.args.get('exclude') or []:
            args.extend(['--exclude', exclude])
        for include in self.args.get('include') or []:
            args.extend(['--include', include])
        # Exclude remote filesystems
        if not self.args.get('all'):
            for device, mountpoint, fstype in _get_all_mounts():
                if fstype not in ALLOWED_FILESYSTEM_TYPES:
                    self.log.debug('excluding %s filesystem %s at %s',
                                   fstype, device, mountpoint)
                    args.extend(['--exclude', os.path.join(mountpoint, '**')])
        # Add pre-defined exclusions
        if not self.args.get('no_filter') and os.path.isfile(EXCLUDES_FILE):
            self.log.debug('adding path exclusions from %s', EXCLUDES_FILE)
            args.extend(['--exclude-from', EXCLUDES_FILE])
        return args

    def __copy_to_target_dir(self, dest, exclude_opts):
        source = self.args.get('volume') or '/'
        if not source.endswith('/'):
            source += '/'
        if not dest.endswith('/'):
            dest += '/'

        rsync_opts = ['-rHlpogDtS']
        if self.args.get('show_progress'):
            rsync = subprocess.Popen(['rsync', '--version'],
                                     stdout=subprocess.PIPE)
            out, _ = rsync.communicate()
            rsync_version = (out.partition('version ')[2] or '\0').split()[0]
            if rsync_version >= '3.1.0':
                # Use the new summarizing version
                rsync_opts.append('--info=progress2')
            else:
                rsync_opts.append('--progress')
        else:
            rsync_opts.append('--quiet')
        cmd = ['rsync', '-X'] + rsync_opts + exclude_opts + [source, dest]
        self.log.info("copying files with ``%s''", _quote_cmd(cmd))
        print 'Copying files...'
        rsync = subprocess.Popen(cmd)
        rsync.wait()
        if rsync.returncode == 1:
            # Try again without xattrs
            self.log.info('rsync exited with code %i; retrying without xattrs',
                          rsync.returncode)
            print 'Retrying without extended attributes'
            cmd = ['rsync'] + rsync_opts + exclude_opts + [source, dest]
            rsync = subprocess.Popen(cmd)
            rsync.wait()
        if rsync.returncode not in (0, 23):
            self.log.error('rsync exited with code %i', rsync.returncode)
            raise subprocess.CalledProcessError(rsync.returncode, 'rsync')

    def __insert_fstab(self, mountpoint):
        fstab_filename = os.path.join(mountpoint, 'etc', 'fstab')
        if os.path.exists(fstab_filename):
            fstab_bak = fstab_filename + '.bak'
            self.log.debug('backing up original fstab file as %s', fstab_bak)
            _copy_with_xattrs(fstab_filename, fstab_bak)
        if self.args.get('generate_fstab'):
            # This isn't really a template, but if the need arises we
            # can add something of that sort later.
            self.log.info('generating fstab file from %s', self.args['fstab'])
            _copy_with_xattrs(FSTAB_TEMPLATE_FILE, fstab_filename)
        elif self.args.get('fstab'):
            self.log.info('using fstab file %s', self.args['fstab'])
            _copy_with_xattrs(self.args['fstab'], fstab_filename)

    def __insert_grub_config(self, mountpoint):
        if self.args.get('grub_config'):
            grub_filename = os.path.join(mountpoint, 'boot', 'grub',
                                         'menu.lst')
            if os.path.exists(grub_filename):
                grub_back = grub_filename + '.bak'
                self.log.debug('backing up original grub1 config file as %s',
                               grub_back)
                _copy_with_xattrs(grub_filename, grub_back)
            self.log.info('using grub1 config file %s',
                          self.args['grub_config'])
            _copy_with_xattrs(self.args['grub_config'], grub_filename)


def _get_all_mounts():
    # This implementation is Linux-specific

    # We first load everything into a dict based on mount points so we
    # can return only the last filesystem to be mounted in each
    # location.  This is important for / on Linux, where a rootfs
    # volume has a real filesystem mounted on top of it, because
    # returning both of them will cause / to get excluded due to its
    # filesystem type.
    filesystems_dict = {}
    with open('/proc/mounts') as mounts:
        for line in mounts:
            device, mountpoint, fstype, _ = line.split(None, 3)
            filesystems_dict[mountpoint] = (device, fstype)
    filesystems_list = []
    for mountpoint, (device, fstype) in filesystems_dict.iteritems():
        filesystems_list.append((device, mountpoint, fstype))
    return filesystems_list


def _get_filesystem_info(device):
    blkid = subprocess.Popen(['blkid', '-d', '-o', 'export', device],
                             stdout=subprocess.PIPE)
    fsinfo = {}
    for line in blkid.stdout:
        key, _, val = line.strip().partition('=')
        if key == 'LABEL':
            fsinfo['label'] = val
        elif key == 'TYPE':
            fsinfo['type'] = val
        elif key == 'UUID':
            fsinfo['uuid'] = val
    blkid.wait()
    return fsinfo


def _get_partition_table_type(device, debug=False):
    if device[-1] in '0123456789':
        if device[-2] == 'd':
            # /dev/sda1, /dev/xvda1, /dev/vda1, etc.
            device = device[:-1]
        elif device[-2] == 'p':
            # /dev/loop0p1, /dev/sr0p1, etc.
            device = device[:-2]
    if debug:
        stderr_dest = subprocess.PIPE
    else:
        stderr_dest = None
    parted = subprocess.Popen(['parted', '-m', '-s', device, 'print'],
                              stdout=subprocess.PIPE, stderr=stderr_dest)
    stdout, _ = parted.communicate()
    for line in stdout:
        if line.startswith('/dev/'):
            # /dev/sda:500GB:scsi:512:512:msdos:ATA WDC WD5003ABYX-1;
            line_bits = line.split(':')
            if line_bits[5] == 'msdos':
                return 'mbr'
            elif line_bits[5] == 'gpt':
                return 'gpt'
            else:
                return 'none'


def _get_root_device():
    for device, mountpoint, _ in _get_all_mounts():
        if mountpoint == '/' and os.path.exists(device):
            root_device = device
            # Do not skip the rest of the mount points.  Another
            # / filesystem, such as a btrfs subvolume, may be
            # mounted on top of that.
    return root_device


def _quote_cmd(cmd):
    return ' '.join(pipes.quote(arg) for arg in cmd)


def _copy_with_xattrs(source, dest):
    """
    shutil.copy2 doesn't preserve xattrs until python 3.3, so here we
    attempt to leverage the cp command to do it for us.
    """
    try:
        subprocess.check_call(['cp', '-a', source, dest])
    except subprocess.CalledProcessError:
        shutil.copy2(source, dest)

########NEW FILE########
__FILENAME__ = deletebundle
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.exceptions import ServerError

from euca2ools.commands.bundle.mixins import BundleDownloadingMixin
from euca2ools.commands.s3 import S3Request
from euca2ools.commands.s3.deletebucket import DeleteBucket
from euca2ools.commands.s3.deleteobject import DeleteObject


class DeleteBundle(S3Request, BundleDownloadingMixin):
    DESCRIPTION = 'Delete a previously-uploaded bundle'
    ARGS = [Arg('--clear', dest='clear', action='store_true',
                help='attempt to delete the bucket as well')]

    def main(self):
        try:
            manifest = self.fetch_manifest(self.service)
        except ServerError as err:
            if err.status_code == 404 and self.args.get('clear'):
                try:
                    # We are supposed to try to delete the bucket even
                    # if the manifest isn't there.  If it works, the
                    # bundle is also gone and we can safely return.
                    #
                    # https://eucalyptus.atlassian.net/browse/TOOLS-379
                    self.__delete_bucket()
                    return
                except ServerError:
                    # If the bucket wasn't empty then we'll go back to
                    # complaining about the missing manifest.
                    self.log.error(
                        'failed to delete bucket %s after a failed '
                        'attempt to fetch the bundle manifest',
                        bucket=self.args['bucket'].split('/')[0],
                        exc_info=True)
            raise

        for _, part_s3path in self.map_bundle_parts_to_s3paths(manifest):
            req = DeleteObject.from_other(self, path=part_s3path)
            req.main()
        manifest_s3path = self.get_manifest_s3path()
        if manifest_s3path:
            req = DeleteObject.from_other(self, path=manifest_s3path)
            req.main()

        if self.args.get('clear'):
            self.__delete_bucket()

    def __delete_bucket(self):
        req = DeleteBucket.from_other(self,
                                      bucket=self.args['bucket'].split('/')[0])
        req.main()

########NEW FILE########
__FILENAME__ = downloadandunbundle
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import multiprocessing
import os.path
import sys

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.bundle.util import open_pipe_fileobjs
from euca2ools.bundle.util import waitpid_in_thread
from euca2ools.commands.bundle.downloadbundle import DownloadBundle
from euca2ools.commands.bundle.mixins import BundleDownloadingMixin
from euca2ools.commands.bundle.unbundlestream import UnbundleStream
from euca2ools.commands.s3 import S3Request


class DownloadAndUnbundle(S3Request, FileTransferProgressBarMixin,
                          BundleDownloadingMixin):
    DESCRIPTION = ('Download and unbundle a bundled image from the cloud\n\n '
                   'The key used to unbundle the image must match a '
                   'certificate that was used to bundle it.')
    ARGS = [Arg('-d', '--destination', dest='dest', metavar='(FILE | DIR)',
                default=".", help='''where to place the unbundled image
                (default: current directory)'''),
            Arg('-k', '--privatekey',
                help='''file containing the private key to decrypt the bundle
                with.  This must match a certificate used when bundling the
                image.''')]

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)

        # The private key could be the user's or the cloud's.  In the config
        # this is a user-level option.
        if not self.args.get('privatekey'):
            config_privatekey = self.config.get_user_option('private-key')
            if self.args.get('userregion'):
                self.args['privatekey'] = config_privatekey
            elif 'EC2_PRIVATE_KEY' in os.environ:
                self.args['privatekey'] = os.getenv('EC2_PRIVATE_KEY')
            elif config_privatekey:
                self.args['privatekey'] = config_privatekey
            else:
                raise ArgumentError(
                    'missing private key; please supply one with -k')
        self.args['privatekey'] = os.path.expanduser(os.path.expandvars(
            self.args['privatekey']))
        if not os.path.exists(self.args['privatekey']):
            raise ArgumentError("private key file '{0}' does not exist"
                                .format(self.args['privatekey']))
        if not os.path.isfile(self.args['privatekey']):
            raise ArgumentError("private key file '{0}' is not a file"
                                .format(self.args['privatekey']))
        self.log.debug('private key: %s', self.args['privatekey'])

    def __open_dest(self, manifest):
        if self.args['dest'] == '-':
            self.args['dest'] = sys.stdout
            self.args['show_progress'] = False
        elif isinstance(self.args['dest'], basestring):
            if os.path.isdir(self.args['dest']):
                image_filename = os.path.join(self.args['dest'],
                                              manifest.image_name)
            else:
                image_filename = self.args['dest']
            self.args['dest'] = open(image_filename, 'w')
            return image_filename
        # Otherwise we assume it's a file object

    def main(self):
        manifest = self.fetch_manifest(
            self.service, privkey_filename=self.args['privatekey'])
        download_out_r, download_out_w = open_pipe_fileobjs()
        try:
            self.__create_download_pipeline(download_out_w)
        finally:
            download_out_w.close()
        image_filename = self.__open_dest(manifest)
        unbundlestream = UnbundleStream.from_other(
            self, source=download_out_r, dest=self.args['dest'],
            enc_key=manifest.enc_key, enc_iv=manifest.enc_iv,
            image_size=manifest.image_size, sha1_digest=manifest.image_digest,
            show_progress=self.args.get('show_progress', False))
        unbundlestream.main()
        return image_filename

    def __create_download_pipeline(self, outfile):
        downloadbundle = DownloadBundle.from_other(
            self, dest=outfile, bucket=self.args['bucket'],
            manifest=self.args.get('manifest'),
            local_manifest=self.args.get('local_manifest'),
            show_progress=False)
        downloadbundle_p = multiprocessing.Process(target=downloadbundle.main)
        downloadbundle_p.start()
        waitpid_in_thread(downloadbundle_p.pid)
        outfile.close()

    def print_result(self, image_filename):
        if (image_filename and
                self.args['dest'].fileno() != sys.stdout.fileno()):
            print 'Wrote', image_filename

########NEW FILE########
__FILENAME__ = downloadbundle
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import os.path
import sys

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.bundle.mixins import BundleDownloadingMixin
from euca2ools.commands.s3 import S3Request


class DownloadBundle(S3Request, FileTransferProgressBarMixin,
                     BundleDownloadingMixin):
    DESCRIPTION = ('Download a bundled image from the cloud\n\nYou must run '
                   'euca-unbundle-image on the bundle you download to obtain '
                   'the original image.')
    ARGS = [Arg('-d', '--directory', dest='dest', metavar='DIR', default=".",
                help='''the directory to download the bundle parts to, or "-"
                to write the bundled image to stdout''')]

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)
        if self.args['dest'] == '-':
            self.args['dest'] = sys.stdout
            self.args['show_progress'] = False
        elif isinstance(self.args['dest'], basestring):
            if not os.path.exists(self.args['dest']):
                raise ArgumentError(
                    "argument -d/--directory: '{0}' does not exist"
                    .format(self.args['dest']))
            if not os.path.isdir(self.args['dest']):
                raise ArgumentError(
                    "argument -d/--directory: '{0}' is not a directory"
                    .format(self.args['dest']))
        # Otherwise we assume it is a file object

    # noinspection PyExceptionInherit
    def main(self):
        manifest = self.fetch_manifest(self.service)
        if isinstance(self.args['dest'], basestring):
            manifest_dest = self.download_bundle_to_dir(
                manifest, self.args['dest'], self.service)
        else:
            manifest_dest = self.download_bundle_to_fileobj(
                manifest, self.args['dest'], self.service)
        return manifest, manifest_dest

    def print_result(self, result):
        _, manifest_filename = result
        if (manifest_filename and
            (isinstance(self.args['dest'], basestring) or
             self.args['dest'].fileno() != sys.stdout.fileno())):
            print 'Wrote manifest', manifest_filename

########NEW FILE########
__FILENAME__ = installimage
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division

import argparse

from requestbuilder import Arg
from requestbuilder.auth import QuerySigV2Auth
from requestbuilder.mixins import FileTransferProgressBarMixin, TabifyingMixin

from euca2ools.commands.ec2 import EC2
from euca2ools.commands.ec2.registerimage import RegisterImage
from euca2ools.commands.s3 import S3Request
from euca2ools.commands.bundle.bundleanduploadimage import BundleAndUploadImage
from euca2ools.commands.bundle.mixins import BundleCreatingMixin, \
    BundleUploadingMixin


class InstallImage(S3Request, BundleCreatingMixin, BundleUploadingMixin,
                   FileTransferProgressBarMixin, TabifyingMixin):
    DESCRIPTION = 'Bundle, upload and register an image into the cloud'
    ARGS = [Arg('-n', '--name', route_to=None, required=True,
                help='name of the new image (required)'),
            Arg('--description', route_to=None,
                help='description of the new image'),
            Arg('--max-pending-parts', type=int, default=2,
                help='''pause the bundling process when more than this number
                of parts are waiting to be uploaded (default: 2)'''),
            Arg('--virtualization-type', route_to=None,
                choices=('paravirtual', 'hvm'),
                help='[Privileged] virtualization type for the new image'),
            Arg('--platform', route_to=None, metavar='windows',
                choices=('windows',),
                help="[Privileged] the new image's platform (windows)"),
            Arg('--ec2-url', route_to=None,
                help='compute service endpoint URL'),
            Arg('--ec2-auth', route_to=None, help=argparse.SUPPRESS),
            Arg('--ec2-service', route_to=None, help=argparse.SUPPRESS)]

    def configure(self):
        S3Request.configure(self)
        self.configure_bundle_upload_auth()
        self.configure_bundle_creds()
        self.configure_bundle_output()
        self.configure_bundle_properties()

        if not self.args.get("ec2_service"):
            self.args["ec2_service"] = EC2.from_other(
                self.service, url=self.args.get('ec2_url'))

        if not self.args.get("ec2_auth"):
            self.args["ec2_auth"] = QuerySigV2Auth.from_other(self.auth)

    def main(self):
        req = BundleAndUploadImage.from_other(
            self, image=self.args["image"], arch=self.args["arch"],
            bucket=self.args["bucket"], prefix=self.args.get("prefix"),
            destination=self.args.get("destination"),
            kernel=self.args.get("kernel"), ramdisk=self.args.get("ramdisk"),
            image_type=self.args.get("image_type"),
            image_size=self.args.get("image_size"), cert=self.args.get("cert"),
            privatekey=self.args.get("privatekey"),
            ec2cert=self.args.get("ec2cert"), user=self.args.get("user"),
            productcodes=self.args.get("productcodes"),
            enc_iv=self.args.get("enc_iv"), enc_key=self.args.get("enc_key"),
            max_pending_parts=self.args.get("max_pending_parts"),
            part_size=self.args.get("part_size"), batch=self.args.get("batch"),
            show_progress=self.args.get("show_progress"))
        result_bundle = req.main()
        image_location = result_bundle['manifests'][0]["key"]

        req = RegisterImage.from_other(
            self, service=self.args["ec2_service"], auth=self.args["ec2_auth"],
            Name=self.args["name"], Architecture=self.args["arch"],
            ImageLocation=image_location,
            Description=self.args.get("description"),
            VirtualizationType=self.args.get("virtualization_type"),
            Platform=self.args.get("platform"))
        result_register = req.main()
        return result_register

    def print_result(self, result):
        print self.tabify(('IMAGE', result.get('imageId')))

########NEW FILE########
__FILENAME__ = mixins
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import base64
import os.path
import random
import tempfile
import sys

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

import euca2ools.bundle.manifest
import euca2ools.bundle.util
from euca2ools.commands.argtypes import (b64encoded_file_contents,
                                         delimited_list, filesize,
                                         manifest_block_device_mappings)
from euca2ools.commands.s3.checkbucket import CheckBucket
from euca2ools.commands.s3.createbucket import CreateBucket
from euca2ools.commands.s3.getobject import GetObject
from euca2ools.commands.s3.postobject import PostObject
from euca2ools.commands.s3.putobject import PutObject
from euca2ools.exceptions import AWSError


EC2_BUNDLE_SIZE_LIMIT = 10 * 2 ** 30  # 10 GiB


class BundleCreatingMixin(object):
    ARGS = [Arg('-i', '--image', metavar='FILE', required=True,
                help='file containing the image to bundle (required)'),
            Arg('-p', '--prefix', help='''the file name prefix to give the
                bundle's files (required when bundling stdin; otherwise
                defaults to the image's file name)'''),
            Arg('-d', '--destination', metavar='DIR', help='''location to place
                the bundle's files (default:  dir named by TMPDIR, TEMP, or TMP
                environment variables, or otherwise /var/tmp)'''),
            Arg('-r', '--arch', required=True,
                choices=('i386', 'x86_64', 'armhf', 'ppc', 'ppc64'),
                help="the image's architecture (required)"),

            # User- and cloud-specific stuff
            Arg('-k', '--privatekey', metavar='FILE', help='''file containing
                your private key to sign the bundle's manifest with.  This
                private key will also be required to unbundle the image in the
                future.'''),
            Arg('-c', '--cert', metavar='FILE',
                help='file containing your X.509 certificate'),
            Arg('--ec2cert', metavar='FILE', help='''file containing the
                cloud's X.509 certificate'''),
            Arg('-u', '--user', metavar='ACCOUNT', help='your account ID'),
            Arg('--kernel', metavar='IMAGE', help='''ID of the kernel image to
                associate with this machine image'''),
            Arg('--ramdisk', metavar='IMAGE', help='''ID of the ramdisk image
                to associate with this machine image'''),

            # Obscurities
            Arg('-B', '--block-device-mappings',
                metavar='VIRTUAL1=DEVICE1,VIRTUAL2=DEVICE2,...',
                type=manifest_block_device_mappings,
                help='''block device mapping scheme with which to launch
                instances of this machine image'''),
            Arg('--productcodes', metavar='CODE1,CODE2,...',
                type=delimited_list(','), default=[],
                help='comma-separated list of product codes for the image'),
            Arg('--image-type', choices=('machine', 'kernel', 'ramdisk'),
                default='machine', help=argparse.SUPPRESS),

            # Stuff needed to fill out TarInfo when input comes from stdin.
            #
            # We technically could ask for a lot more, but most of it is
            # unnecessary since owners/modes/etc will be ignored at unbundling
            # time anyway.
            #
            # When bundling stdin we interpret --prefix as the image's file
            # name.
            Arg('--image-size', type=filesize, help='''the image's size
                (required when bundling stdin)'''),

            # Overrides for debugging and other entertaining uses
            Arg('--part-size', type=filesize, default=10485760,  # 10M
                help=argparse.SUPPRESS),
            Arg('--enc-key', type=(lambda s: int(s, 16)),
                help=argparse.SUPPRESS),  # a hex string
            Arg('--enc-iv', type=(lambda s: int(s, 16)),
                help=argparse.SUPPRESS),  # a hex string

            # Noop, for compatibility
            Arg('--batch', action='store_true', help=argparse.SUPPRESS)]

    # CONFIG METHODS #

    def configure_bundle_creds(self):
        # User's X.509 certificate (user-level in config)
        if not self.args.get('cert'):
            config_cert = self.config.get_user_option('certificate')
            if 'EC2_CERT' in os.environ:
                self.args['cert'] = os.getenv('EC2_CERT')
            elif 'EUCA_CERT' in os.environ:  # used by the NC
                self.args['cert'] = os.getenv('EUCA_CERT')
            elif config_cert:
                self.args['cert'] = config_cert
        if self.args.get('cert'):
            self.args['cert'] = os.path.expanduser(os.path.expandvars(
                self.args['cert']))
            _assert_is_file(self.args['cert'], 'user certificate')

        # User's private key (user-level in config)
        if not self.args.get('privatekey'):
            config_privatekey = self.config.get_user_option('private-key')
            if 'EC2_PRIVATE_KEY' in os.environ:
                self.args['privatekey'] = os.getenv('EC2_PRIVATE_KEY')
            if 'EUCA_PRIVATE_KEY' in os.environ:  # used by the NC
                self.args['privatekey'] = os.getenv('EUCA_PRIVATE_KEY')
            elif config_privatekey:
                self.args['privatekey'] = config_privatekey
        if self.args.get('privatekey'):
            self.args['privatekey'] = os.path.expanduser(os.path.expandvars(
                self.args['privatekey']))
            _assert_is_file(self.args['privatekey'], 'private key')

        # Cloud's X.509 cert (region-level in config)
        if not self.args.get('ec2cert'):
            config_privatekey = self.config.get_region_option('certificate')
            if 'EUCALYPTUS_CERT' in os.environ:
                # This has no EC2 equivalent since they just bundle their cert.
                self.args['ec2cert'] = os.getenv('EUCALYPTUS_CERT')
            elif config_privatekey:
                self.args['ec2cert'] = config_privatekey
        if self.args.get('ec2cert'):
            self.args['ec2cert'] = os.path.expanduser(os.path.expandvars(
                self.args['ec2cert']))
            _assert_is_file(self.args['ec2cert'], 'cloud certificate')

        # User's account ID (user-level)
        if not self.args.get('user'):
            config_account_id = self.config.get_user_option('account-id')
            if 'EC2_USER_ID' in os.environ:
                self.args['user'] = os.getenv('EC2_USER_ID')
            elif config_account_id:
                self.args['user'] = config_account_id

        # Now validate everything
        if not self.args.get('cert'):
            raise ArgumentError(
                'missing certificate; please supply one with -c')
        self.log.debug('certificate: %s', self.args['cert'])
        if not self.args.get('privatekey'):
            raise ArgumentError(
                'missing private key; please supply one with -k')
        self.log.debug('private key: %s', self.args['privatekey'])
        if not self.args.get('ec2cert'):
            raise ArgumentError(
                'missing cloud certificate; please supply one with --ec2cert')
        self.log.debug('cloud certificate: %s', self.args['ec2cert'])
        if not self.args.get('user'):
            raise ArgumentError(
                'missing account ID; please supply one with --user')
        self.log.debug('account ID: %s', self.args['user'])

    def configure_bundle_output(self):
        if (self.args.get('destination') and
                os.path.exists(self.args['destination']) and not
                os.path.isdir(self.args['destination'])):
            raise ArgumentError("argument -d/--destination: '{0}' is not a "
                                "directory".format(self.args['destination']))
        if self.args['image'] == '-':
            self.args['image'] = os.fdopen(os.dup(sys.stdin.fileno()))
            if not self.args.get('prefix'):
                raise ArgumentError(
                    'argument --prefix is required when bundling stdin')
            if not self.args.get('image_size'):
                raise ArgumentError(
                    'argument --image-size is required when bundling stdin')
        elif isinstance(self.args['image'], basestring):
            if not self.args.get('prefix'):
                self.args['prefix'] = os.path.basename(self.args['image'])
            if not self.args.get('image_size'):
                self.args['image_size'] = euca2ools.util.get_filesize(
                    self.args['image'])
            self.args['image'] = open(self.args['image'])
        else:
            # Assume it is already a file object
            if not self.args.get('prefix'):
                raise ArgumentError('argument --prefix is required when '
                                    'bundling a file object')
            if not self.args.get('image_size'):
                raise ArgumentError('argument --image-size is required when '
                                    'bundling a file object')
        if self.args['image_size'] > EC2_BUNDLE_SIZE_LIMIT:
            self.log.warn(
                'image is incompatible with EC2 due to its size (%i > %i)',
                self.args['image_size'], EC2_BUNDLE_SIZE_LIMIT)

    def configure_bundle_properties(self):
        if self.args.get('kernel') == 'true':
            self.args['image_type'] = 'kernel'
        if self.args.get('ramdisk') == 'true':
            self.args['image_type'] = 'ramdisk'
        if self.args['image_type'] == 'kernel':
            if self.args.get('kernel') and self.args['kernel'] != 'true':
                raise ArgumentError("argument --kernel: not compatible with "
                                    "image type 'kernel'")
            if self.args.get('ramdisk'):
                raise ArgumentError("argument --ramdisk: not compatible with "
                                    "image type 'kernel'")
            if self.args.get('block_device_mappings'):
                raise ArgumentError("argument -B/--block-device-mappings: not "
                                    "compatible with image type 'kernel'")
        if self.args['image_type'] == 'ramdisk':
            if self.args.get('kernel'):
                raise ArgumentError("argument --kernel: not compatible with "
                                    "image type 'ramdisk'")
            if self.args.get('ramdisk') and self.args['ramdisk'] != 'true':
                raise ArgumentError("argument --ramdisk: not compatible with "
                                    "image type 'ramdisk'")
            if self.args.get('block_device_mappings'):
                raise ArgumentError("argument -B/--block-device-mappings: not "
                                    "compatible with image type 'ramdisk'")

    def generate_encryption_keys(self):
        srand = random.SystemRandom()
        if self.args.get('enc_key'):
            self.log.info('using preexisting encryption key')
            enc_key_i = self.args['enc_key']
        else:
            enc_key_i = srand.getrandbits(128)
        if self.args.get('enc_iv'):
            self.log.info('using preexisting encryption IV')
            enc_iv_i = self.args['enc_iv']
        else:
            enc_iv_i = srand.getrandbits(128)
        self.args['enc_key'] = '{0:0>32x}'.format(enc_key_i)
        self.args['enc_iv'] = '{0:0>32x}'.format(enc_iv_i)

    # MANIFEST GENERATION METHODS #

    def build_manifest(self, digest, partinfo):
        manifest = euca2ools.bundle.manifest.BundleManifest(
            loglevel=self.log.level)
        manifest.image_arch = self.args['arch']
        manifest.kernel_id = self.args.get('kernel')
        manifest.ramdisk_id = self.args.get('ramdisk')
        if self.args.get('block_device_mappings'):
            manifest.block_device_mappings.update(
                self.args['block_device_mappings'])
        if self.args.get('productcodes'):
            manifest.product_codes.extend(self.args['productcodes'])
        manifest.image_name = self.args['prefix']
        manifest.account_id = self.args['user']
        manifest.image_type = self.args['image_type']
        manifest.image_digest = digest
        manifest.image_digest_algorithm = 'SHA1'  # shouldn't be hardcoded here
        manifest.image_size = self.args['image_size']
        manifest.bundled_image_size = sum(part.size for part in partinfo)
        manifest.enc_key = self.args['enc_key']
        manifest.enc_iv = self.args['enc_iv']
        manifest.enc_algorithm = 'AES-128-CBC'  # shouldn't be hardcoded here
        manifest.image_parts = partinfo
        return manifest

    def dump_manifest_to_file(self, manifest, filename, pretty_print=False):
        with open(filename, 'w') as manifest_file:
            manifest_file.write(self.dump_manifest_to_str(
                manifest, pretty_print=pretty_print))

    def dump_manifest_to_str(self, manifest, pretty_print=False):
        return manifest.dump_to_str(self.args['privatekey'], self.args['cert'],
                                    self.args['ec2cert'],
                                    pretty_print=pretty_print)


class BundleUploadingMixin(object):
    ARGS = [Arg('-b', '--bucket', metavar='BUCKET[/PREFIX]', required=True,
                help='bucket to upload the bundle to (required)'),
            Arg('--acl', default='aws-exec-read',
                choices=('public-read', 'aws-exec-read', 'ec2-bundle-read'),
                help='''canned ACL policy to apply to the bundle (default:
                aws-exec-read)'''),
            MutuallyExclusiveArgList(
                Arg('--upload-policy', dest='upload_policy', metavar='POLICY',
                    type=base64.b64encode,
                    help='upload policy to use for authorization'),
                Arg('--upload-policy-file', dest='upload_policy',
                    metavar='FILE', type=b64encoded_file_contents,
                    help='''file containing an upload policy to use for
                    authorization''')),
            Arg('--upload-policy-signature', metavar='SIGNATURE',
                help='''signature for the upload policy (required when an
                'upload policy is used)'''),
            Arg('--location', help='''location constraint of the destination
                bucket (default: inferred from s3-location-constraint in
                configuration, or otherwise none)'''),
            Arg('--retry', dest='retries', action='store_const', const=5,
                default=0, help='retry failed uploads up to 5 times')]

    def configure_bundle_upload_auth(self):
        if self.args.get('upload_policy'):
            if not self.args.get('key_id'):
                raise ArgumentError('-I/--access-key-id is required when '
                                    'using an upload policy')
            if not self.args.get('upload_policy_signature'):
                raise ArgumentError('--upload-policy-signature is required '
                                    'when using an upload policy')
            self.auth = None

    def get_bundle_key_prefix(self):
        (bucket, _, prefix) = self.args['bucket'].partition('/')
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        return bucket + '/' + prefix

    def ensure_dest_bucket_exists(self):
        if self.args.get('upload_policy'):
            # We won't have creds to sign our own requests
            self.log.info('using an upload policy; not verifying bucket '
                          'existence')
            return

        bucket = self.args['bucket'].split('/', 1)[0]
        try:
            req = CheckBucket.from_other(self, bucket=bucket)
            req.main()
        except AWSError as err:
            if err.status_code == 404:
                # No such bucket
                self.log.info("creating bucket '%s'", bucket)
                req = CreateBucket.from_other(
                    self, bucket=bucket, location=self.args.get('location'))
                req.main()
            else:
                raise
        # At this point we know we can at least see the bucket, but it's still
        # possible that we can't write to it with the desired key names.  So
        # many policies are in play here that it isn't worth trying to be
        # proactive about it.

    def upload_bundle_file(self, source, dest, show_progress=False,
                           **putobj_kwargs):
        if self.args.get('upload_policy'):
            if show_progress:
                # PostObject does not yet support show_progress
                print source, 'uploading...'
            req = PostObject.from_other(
                self, source=source, dest=dest,
                acl=self.args.get('acl') or 'aws-exec-read',
                Policy=self.args['upload_policy'],
                Signature=self.args['upload_policy_signature'],
                AWSAccessKeyId=self.args['key_id'], **putobj_kwargs)
        else:
            req = PutObject.from_other(
                self, source=source, dest=dest,
                acl=self.args.get('acl') or 'aws-exec-read',
                retries=self.args.get('retries') or 0,
                show_progress=show_progress, **putobj_kwargs)
        req.main()

    def upload_bundle_parts(self, partinfo_in_mpconn, key_prefix,
                            partinfo_out_mpconn=None, part_write_sem=None,
                            **putobj_kwargs):
        try:
            while True:
                part = partinfo_in_mpconn.recv()
                dest = key_prefix + os.path.basename(part.filename)
                self.upload_bundle_file(part.filename, dest, **putobj_kwargs)
                if part_write_sem is not None:
                    # Allow something that's waiting for the upload to finish
                    # to continue
                    part_write_sem.release()
                if partinfo_out_mpconn is not None:
                    partinfo_out_mpconn.send(part)
        except EOFError:
            return
        finally:
            partinfo_in_mpconn.close()
            if partinfo_out_mpconn is not None:
                partinfo_out_mpconn.close()


class BundleDownloadingMixin(object):
    # When fetching the manifest from the server there are two ways to get
    # its path:
    #  -m:  BUCKET[/PREFIX]/MANIFEST
    #  -p:  BUCKET[/PREFIX]/PREFIX.manifest.xml  (the PREFIXes are different)
    #
    # In all cases, after we obtain the manifest (whether it is local or not)
    # we choose key names for parts based on the file names in the manifest:
    #  BUCKET[/PREFIX]/PART

    ARGS = [Arg('-b', '--bucket', metavar='BUCKET[/PREFIX]', required=True,
                route_to=None, help='''the bucket that contains the bundle,
                with an optional path prefix (required)'''),
            MutuallyExclusiveArgList(
                Arg('-m', '--manifest', dest='manifest', route_to=None,
                    help='''the manifest's complete file name, not including
                    any path that may be specified using -b'''),
                Arg('-p', '--prefix', dest='manifest', route_to=None,
                    type=(lambda x: x + '.manifest.xml'),
                    help='''the portion of the manifest's file name that
                    precedes ".manifest.xml"'''),
                Arg('--local-manifest', dest='local_manifest', metavar='FILE',
                    route_to=None, help='''use a manifest on disk and ignore
                    any that appear on the server'''))
            .required()]

    def fetch_manifest(self, s3_service, privkey_filename=None):
        if self.args.get('local_manifest'):
            _assert_is_file(self.args['local_manifest'], 'manifest')
            return euca2ools.bundle.manifest.BundleManifest.read_from_file(
                self.args['local_manifest'], privkey_filename=privkey_filename)

        # It's on the server, so do things the hard way
        manifest_s3path = self.get_manifest_s3path()
        with tempfile.TemporaryFile() as manifest_tempfile:
            self.log.info('reading manifest from %s', manifest_s3path)
            req = GetObject.from_other(
                self, service=s3_service, source=manifest_s3path,
                dest=manifest_tempfile)
            try:
                req.main()
            except AWSError as err:
                if err.status_code == 404:
                    self.log.debug('failed to fetch manifest', exc_info=True)
                    raise ValueError("manifest '{0}' does not exist on the "
                                     "server".format(manifest_s3path))
                raise
            manifest_tempfile.flush()
            manifest_tempfile.seek(0)
            return euca2ools.bundle.manifest.BundleManifest.read_from_fileobj(
                manifest_tempfile, privkey_filename=privkey_filename)

    def get_manifest_s3path(self):
        if self.args.get('manifest'):
            return '/'.join((self.args['bucket'], self.args['manifest']))
        else:
            # With a local manifest we can't divine the manifest's key name is
            return None

    def download_bundle_to_dir(self, manifest, dest_dir, s3_service):
        parts = self.map_bundle_parts_to_s3paths(manifest)
        for part, part_s3path in parts:
            part.filename = os.path.join(dest_dir,
                                         os.path.basename(part_s3path))
            self.log.info('downloading part %s to %s',
                          part_s3path, part.filename)
            req = GetObject.from_other(
                self, service=s3_service, source=part_s3path,
                dest=part.filename,
                show_progress=self.args.get('show_progress', False))
            response = req.main()
            self.__check_part_sha1(part, part_s3path, response)

        manifest_s3path = self.get_manifest_s3path()
        if manifest_s3path:
            # Can't download a manifest if we're using a local one
            manifest_dest = os.path.join(dest_dir,
                                         os.path.basename(manifest_s3path))
            self.log.info('downloading manifest %s to %s',
                          manifest_s3path, manifest_dest)
            req = GetObject.from_other(
                self, service=s3_service, source=manifest_s3path,
                dest=manifest_dest,
                show_progress=self.args.get('show_progress', False))
            req.main()
            return manifest_dest
        return None

    def download_bundle_to_fileobj(self, manifest, fileobj, s3_service):
        # We can skip downloading the manifest since we're just writing all
        # parts to a file object.
        parts = self.map_bundle_parts_to_s3paths(manifest)
        for part, part_s3path in parts:
            self.log.info('downloading part %s', part_s3path)
            req = GetObject.from_other(
                self, service=s3_service, source=part_s3path,
                dest=fileobj,
                show_progress=self.args.get('show_progress', False))
            response = req.main()
            self.__check_part_sha1(part, part_s3path, response)

    def map_bundle_parts_to_s3paths(self, manifest):
        parts = []
        for part in manifest.image_parts:
            parts.append((part,
                          '/'.join((self.args['bucket'], part.filename))))
        return parts

    def __check_part_sha1(self, part, part_s3path, response):
        if response[part_s3path]['sha1'] != part.hexdigest:
            self.log.error('rejecting download due to manifest SHA1 '
                           'mismatch (expected: %s, actual: %s)',
                           part.hexdigest, response[part_s3path]['sha1'])
            raise RuntimeError('downloaded file {0} appears to be corrupt '
                               '(expected SHA1: {0}, actual: {1}'
                               .format(part.hexdigest,
                                       response[part_s3path]['sha1']))


def _assert_is_file(filename, filetype):
    if not os.path.exists(filename):
        raise ArgumentError("{0} file '{1}' does not exist"
                            .format(filetype, filename))
    if not os.path.isfile(filename):
        raise ArgumentError("{0} file '{1}' is not a file"
                            .format(filetype, filename))

########NEW FILE########
__FILENAME__ = unbundle
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib
import os
import multiprocessing

from requestbuilder import Arg
from requestbuilder.command import BaseCommand
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import (FileTransferProgressBarMixin,
                                   RegionConfigurableMixin)

from euca2ools.commands import Euca2ools
import euca2ools.bundle.pipes
from euca2ools.bundle.manifest import BundleManifest
from euca2ools.bundle.util import (close_all_fds, open_pipe_fileobjs,
                                   waitpid_in_thread)
from euca2ools.commands.bundle.unbundlestream import UnbundleStream


class Unbundle(BaseCommand, FileTransferProgressBarMixin,
               RegionConfigurableMixin):
    DESCRIPTION = ('Recreate an image from its bundled parts\n\nThe key used '
                   'to unbundle the image must match a certificate that was '
                   'used to bundle it.')
    SUITE = Euca2ools
    ARGS = [Arg('-m', '--manifest', type=open, metavar='FILE',
                required=True, help="the bundle's manifest file (required)"),
            Arg('-s', '--source', metavar='DIR', default='.',
                help='''directory containing the bundled image parts (default:
                current directory)'''),
            Arg('-d', '--destination', metavar='DIR', default='.',
                help='''where to place the unbundled image (default: current
                directory)'''),
            Arg('-k', '--privatekey', metavar='FILE', help='''file containing
                the private key to decrypt the bundle with.  This must match
                a certificate used when bundling the image.''')]

    # noinspection PyExceptionInherit
    def configure(self):
        BaseCommand.configure(self)
        self.update_config_view()

        # The private key could be the user's or the cloud's.  In the config
        # this is a user-level option.
        if not self.args.get('privatekey'):
            config_privatekey = self.config.get_user_option('private-key')
            if self.args.get('userregion'):
                self.args['privatekey'] = config_privatekey
            elif 'EC2_PRIVATE_KEY' in os.environ:
                self.args['privatekey'] = os.getenv('EC2_PRIVATE_KEY')
            elif config_privatekey:
                self.args['privatekey'] = config_privatekey
            else:
                raise ArgumentError(
                    'missing private key; please supply one with -k')
        self.args['privatekey'] = os.path.expanduser(os.path.expandvars(
            self.args['privatekey']))
        if not os.path.exists(self.args['privatekey']):
            raise ArgumentError("private key file '{0}' does not exist"
                                .format(self.args['privatekey']))
        if not os.path.isfile(self.args['privatekey']):
            raise ArgumentError("private key file '{0}' is not a file"
                                .format(self.args['privatekey']))
        self.log.debug('private key: %s', self.args['privatekey'])

        if not os.path.exists(self.args.get('source', '.')):
            raise ArgumentError("argument -s/--source: directory '{0}' does "
                                "not exist".format(self.args['source']))
        if not os.path.isdir(self.args.get('source', '.')):
            raise ArgumentError("argument -s/--source: '{0}' is not a "
                                "directory".format(self.args['source']))
        if not os.path.exists(self.args.get('destination', '.')):
            raise ArgumentError("argument -d/--destination: directory '{0}' "
                                "does not exist"
                                .format(self.args['destination']))
        if not os.path.isdir(self.args.get('destination', '.')):
            raise ArgumentError("argument -d/--destination: '{0}' is not a "
                                "directory".format(self.args['destination']))

    def __read_bundle_parts(self, manifest, outfile):
        close_all_fds(except_fds=[outfile])
        for part in manifest.image_parts:
            self.log.debug("opening part '%s' for reading", part.filename)
            digest = hashlib.sha1()
            with open(part.filename) as part_file:
                while True:
                    chunk = part_file.read(euca2ools.BUFSIZE)
                    if chunk:
                        digest.update(chunk)
                        outfile.write(chunk)
                        outfile.flush()
                    else:
                        break
                actual_hexdigest = digest.hexdigest()
                if actual_hexdigest != part.hexdigest:
                    self.log.error('rejecting unbundle due to part SHA1 '
                                   'mismatch (expected: %s, actual: %s)',
                                   part.hexdigest, actual_hexdigest)
                    raise RuntimeError(
                        "bundle part '{0}' appears to be corrupt (expected "
                        "SHA1: {1}, actual: {2}"
                        .format(part.filename, part.hexdigest,
                                actual_hexdigest))

    def main(self):
        manifest = BundleManifest.read_from_fileobj(
            self.args['manifest'], privkey_filename=self.args['privatekey'])

        for part in manifest.image_parts:
            part_path = os.path.join(self.args['source'], part.filename)
            while part_path.startswith('./'):
                part_path = part_path[2:]
            if os.path.exists(part_path):
                part.filename = part_path
            else:
                raise RuntimeError(
                    "bundle part '{0}' does not exist; you may need to use "
                    "-s to specify where to find the bundle's parts"
                    .format(part_path))

        part_reader_out_r, part_reader_out_w = open_pipe_fileobjs()
        part_reader = multiprocessing.Process(
            target=self.__read_bundle_parts,
            args=(manifest, part_reader_out_w))
        part_reader.start()
        part_reader_out_w.close()
        waitpid_in_thread(part_reader.pid)

        image_filename = os.path.join(self.args['destination'],
                                      manifest.image_name)
        with open(image_filename, 'w') as image:
            unbundlestream = UnbundleStream.from_other(
                self, source=part_reader_out_r, dest=image,
                enc_key=manifest.enc_key, enc_iv=manifest.enc_iv,
                image_size=manifest.image_size,
                sha1_digest=manifest.image_digest,
                show_progress=self.args.get('show_progress', False))
            unbundlestream.main()
        return image_filename

    def print_result(self, image_filename):
        print 'Wrote', image_filename

########NEW FILE########
__FILENAME__ = unbundlestream
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os.path
import sys

from requestbuilder import Arg
from requestbuilder.command import BaseCommand
from requestbuilder.mixins import (FileTransferProgressBarMixin,
                                   RegionConfigurableMixin)

from euca2ools.bundle.pipes.core import (create_unbundle_pipeline,
                                         copy_with_progressbar)
from euca2ools.bundle.util import open_pipe_fileobjs
from euca2ools.commands import Euca2ools
from euca2ools.commands.argtypes import filesize


class UnbundleStream(BaseCommand, FileTransferProgressBarMixin,
                     RegionConfigurableMixin):
    DESCRIPTION = ('Recreate an image solely from its combined bundled parts '
                   'without using a manifest\n\nUsually one would want to use '
                   'euca-unbundle instead.')
    SUITE = Euca2ools
    ARGS = [Arg('-i', dest='source', metavar='FILE',
                help='file to read the bundle from (default: stdin)'),
            Arg('-o', dest='dest', metavar='FILE',
                help='file to write the unbundled image to (default: stdout)'),
            Arg('--enc-key', metavar='HEX', required=True, help='''the
                symmetric key used to encrypt the bundle (required)'''),
            Arg('--enc-iv', metavar='HEX', required=True,
                help='''the initialization vector used to encrypt the bundle
                (required)'''),
            Arg('--image-size', metavar='BYTES', type=filesize,
                help='verify the unbundled image is a certain size'),
            Arg('--sha1-digest', metavar='HEX', help='''verify the image's
                contents against a SHA1 digest from its manifest file''')]

    # noinspection PyExceptionInherit
    def configure(self):
        BaseCommand.configure(self)
        self.update_config_view()

        if not self.args.get('source') or self.args['source'] == '-':
            # We dup stdin because the multiprocessing lib closes it
            self.args['source'] = os.fdopen(os.dup(sys.stdin.fileno()))
        elif isinstance(self.args['source'], basestring):
            self.args['source'] = open(self.args['source'])
        # Otherwise, assume it is already a file object

        if not self.args.get('dest') or self.args['dest'] == '-':
            self.args['dest'] = sys.stdout
            self.args['show_progress'] = False
        elif isinstance(self.args['dest'], basestring):
            self.args['dest'] = open(self.args['dest'], 'w')
        # Otherwise, assume it is already a file object

    def main(self):
        pbar = self.get_progressbar(maxval=self.args.get('image_size'))
        unbundle_out_r, unbundle_out_w = open_pipe_fileobjs()
        unbundle_sha1_r = create_unbundle_pipeline(
            self.args['source'], unbundle_out_w, self.args['enc_key'],
            self.args['enc_iv'], debug=self.debug)
        unbundle_out_w.close()
        actual_size = copy_with_progressbar(unbundle_out_r, self.args['dest'],
                                            progressbar=pbar)
        actual_sha1 = unbundle_sha1_r.recv()
        unbundle_sha1_r.close()

        expected_sha1 = self.args.get('sha1_digest') or ''
        expected_sha1 = expected_sha1.lower().strip('0x')
        expected_size = self.args.get('image_size')
        if expected_sha1 and expected_sha1 != actual_sha1:
            self.log.error('rejecting unbundle due to SHA1 mismatch '
                           '(expected SHA1: %s, actual: %s)',
                           expected_sha1, actual_sha1)
            raise RuntimeError('bundle appears to be corrupt (expected SHA1: '
                               '{0}, actual: {1})'
                               .format(expected_sha1, actual_sha1))
        expected_size = self.args.get('image_size')
        if expected_size and expected_size != actual_size:
            self.log.error('rejecting unbundle due to size mismatch '
                           '(expected: %i, actual: %i)',
                           expected_size, actual_size)
            raise RuntimeError('bundle appears to be corrupt (expected size: '
                               '{0}, actual: {1})'
                               .format(expected_size, actual_size))
        return actual_sha1, actual_size

########NEW FILE########
__FILENAME__ = uploadbundle
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import multiprocessing
import os.path

from requestbuilder import Arg
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.bundle.manifest import BundleManifest
from euca2ools.commands.bundle.mixins import BundleUploadingMixin
from euca2ools.commands.s3 import S3Request
from euca2ools.commands.s3.putobject import PutObject


class UploadBundle(S3Request, BundleUploadingMixin,
                   FileTransferProgressBarMixin):
    DESCRIPTION = 'Upload a bundle prepared by euca-bundle-image to the cloud'
    ARGS = [Arg('-m', '--manifest', metavar='FILE', required=True,
                help='manifest for the bundle to upload (required)'),
            Arg('-d', '--directory', metavar='DIR',
                help='''directory that contains the bundle parts (default:
                directory that contains the manifest)'''),
            # TODO:  make this work
            Arg('--part', metavar='INT', type=int, default=0, help='''begin
                uploading with a specific part number (default: 0)'''),
            Arg('--skipmanifest', action='store_true',
                help='do not upload the manifest')]

    def configure(self):
        self.configure_bundle_upload_auth()
        S3Request.configure(self)

    def main(self):
        key_prefix = self.get_bundle_key_prefix()
        self.ensure_dest_bucket_exists()

        manifest = BundleManifest.read_from_file(self.args['manifest'])
        part_dir = (self.args.get('directory') or
                    os.path.dirname(self.args['manifest']))
        for part in manifest.image_parts:
            part.filename = os.path.join(part_dir, part.filename)
            if not os.path.isfile(part.filename):
                raise ValueError("no such part: '{0}'".format(part.filename))

        # manifest -> upload
        part_out_r, part_out_w = multiprocessing.Pipe(duplex=False)
        part_gen = multiprocessing.Process(target=_generate_bundle_parts,
                                           args=(manifest, part_out_w))
        part_gen.start()
        part_out_w.close()

        # Drive the upload process by feeding in part info
        self.upload_bundle_parts(part_out_r, key_prefix,
                                 show_progress=self.args.get('show_progress'))
        part_gen.join()

        # (conditionally) upload the manifest
        if not self.args.get('skip_manifest'):
            manifest_dest = (key_prefix +
                             os.path.basename(self.args['manifest']))
            req = PutObject.from_other(
                self, source=self.args['manifest'], dest=manifest_dest,
                acl=self.args.get('acl') or 'aws-exec-read',
                retries=self.args.get('retries') or 0)
            req.main()
        else:
            manifest_dest = None

        return {'parts': tuple({'filename': part.filename,
                                'key': (key_prefix +
                                        os.path.basename(part.filename))}
                               for part in manifest.image_parts),
                'manifests': ({'filename': self.args['manifest'],
                               'key': manifest_dest},)}

    def print_result(self, result):
        if self.debug:
            for part in result['parts']:
                print 'Uploaded', part['key']
        if result['manifests'][0]['key'] is not None:
            print 'Uploaded', result['manifests'][0]['key']


def _generate_bundle_parts(manifest, out_mpconn):
    try:
        for part in manifest.image_parts:
            assert os.path.isfile(part.filename)
            out_mpconn.send(part)
    finally:
        out_mpconn.close()

########NEW FILE########
__FILENAME__ = argtypes
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse


def parameter_def(param_str):
    """
    Parse a tag definition from the command line.  Return a dict that depends
    on the format of the string given:

     - 'key=value': {'ParameterKey': key, 'ParameterValue': value}
    """
    if '=' in param_str:
        key, val = param_str.split('=', 1)
        return {'ParameterKey': key, 'ParameterValue': val}
    raise argparse.ArgumentTypeError('parameter "{0}" must have form KEY=VALUE'
                                     .format(param_str))

########NEW FILE########
__FILENAME__ = cancelupdatestack
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class CancelUpdateStack(CloudFormationRequest):
    DESCRIPTION = 'Cancel a stack update that is currently running'
    LIST_TAGS = ['Stacks']
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack to stop updating (required)')]

########NEW FILE########
__FILENAME__ = createstack
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.argtypes import binary_tag_def, delimited_list
from euca2ools.commands.cloudformation import CloudFormationRequest
from euca2ools.commands.cloudformation.argtypes import parameter_def


class CreateStack(CloudFormationRequest):
    DESCRIPTION = 'Create a new stack'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the new stack (required)'),
            MutuallyExclusiveArgList(
                Arg('--template-file', dest='TemplateBody', metavar='FILE',
                    type=open,
                    help="file containing the new stack's JSON template"),
                Arg('--template-url', dest='TemplateURL', metavar='URL',
                    help="URL pointing to the new stack's JSON template"))
            .required(),
            Arg('-d', '--disable-rollback', dest='DisableRollback',
                action='store_true', help='disable rollback on failure'),
            Arg('-n', '--notification-arns', dest='NotificationARNs',
                metavar='ARN[,...]', type=delimited_list(','), action='append',
                help='''SNS ARNs to publish stack actions to'''),
            Arg('-p', '--parameter', dest='Parameters.member',
                metavar='KEY=VALUE', type=parameter_def, action='append',
                help='''key and value of the parameters to use with the new
                stack's template, separated by an "=" character'''),
            Arg('-t', '--timeout', dest='TimeoutInMinutes', type=int,
                metavar='MINUTES', help='timeout for stack creation'),
            Arg('--tag', dest='Tags.member', metavar='KEY[=VALUE]',
                type=binary_tag_def, action='append',
                help='''key and optional value of the tag to create, separated
                by an "=" character.  If no value is given the tag's value is
                set to an empty string.''')]

    def print_result(self, result):
        print result.get('StackId')

########NEW FILE########
__FILENAME__ = deletestack
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class DeleteStack(CloudFormationRequest):
    DESCRIPTION = 'Delete a stack'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack to delete (required)'),
            Arg('--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = describestackevents
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class DescribeStackEvents(CloudFormationRequest):
    DESCRIPTION = 'Describe events that occurred in a stack'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack to show events for (required)')]
    LIST_TAGS = ['StackEvents']

    def print_result(self, result):
        for event in result['StackEvents']:
            self.print_stack_event(event)

########NEW FILE########
__FILENAME__ = describestackresource
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class DescribeStackResource(CloudFormationRequest):
    DESCRIPTION = 'Describe a resource from a particular stack'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack (required)'),
            Arg('-l', '--logical-resource-id', metavar='RESOURCE',
                dest='LogicalResourceId', required=True,
                help='logical ID of the resource to describe (required)')]

    def print_result(self, result):
        self.print_resource(result['StackResourceDetail'])

########NEW FILE########
__FILENAME__ = describestackresources
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class DescribeStackResources(CloudFormationRequest):
    DESCRIPTION = 'List all of the resources in one or more stacks'
    ARGS = [Arg('-n', '--name', dest='StackName', metavar='STACK',
                help='limit results to a specific stack'),
            Arg('-l', '--logical-resource-id', metavar='RESOURCE',
                dest='LogicalResourceId',
                help='logical ID of the resource to describe (required)'),
            Arg('-p', '--physical-resource-id', metavar='RESOURCE',
                dest='PhysicalResourceId',
                help='physical ID of the resource to describe (required)')]
    LIST_TAGS = ['StackResources']

    def print_result(self, result):
        for resource in result['StackResources']:
            self.print_resource(resource)

########NEW FILE########
__FILENAME__ = describestacks
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class DescribeStacks(CloudFormationRequest):
    DESCRIPTION = 'Describe one or more stacks'
    ARGS = [Arg('StackName', metavar='STACK', nargs="?",
                help='limit results to a single stack'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the stacks' info")]
    LIST_TAGS = ['Stacks']

    def print_result(self, result):
        for stack in result['Stacks']:
            self.print_stack(stack)
            if self.args['show_long']:
                print stack.get('StackId')
                print stack.get('NotificationARNs')

########NEW FILE########
__FILENAME__ = gettemplate
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class GetTemplate(CloudFormationRequest):
    DESCRIPTION = "Show a stack's template"
    ARGS = [Arg('StackName', metavar='STACK', help='''name or ID of the
                stack (names cannot be used for deleted stacks) (required)''')]
    LIST_TAGS = ['Stacks']

    def print_result(self, result):
        print result.get('TemplateBody')

########NEW FILE########
__FILENAME__ = liststackresources
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.cloudformation import CloudFormationRequest


class ListStackResources(CloudFormationRequest):
    DESCRIPTION = 'List all resources for a stack'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack to list resources from (required)')]
    LIST_TAGS = ['StackResourceSummaries']

    def print_result(self, result):
        for resource in result['StackResourceSummaries']:
            self.print_resource(resource)

########NEW FILE########
__FILENAME__ = liststacks
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.cloudformation import CloudFormationRequest


class ListStacks(CloudFormationRequest):
    DESCRIPTION = 'List all running stacks'
    LIST_TAGS = ['StackSummaries']

    def print_result(self, result):
        for stack in result['StackSummaries']:
            self.print_stack(stack)

########NEW FILE########
__FILENAME__ = updatestack
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.cloudformation import CloudFormationRequest
from euca2ools.commands.cloudformation.argtypes import parameter_def


class UpdateStack(CloudFormationRequest):
    DESCRIPTION = 'Update a stack with a new template'
    ARGS = [Arg('StackName', metavar='STACK',
                help='name of the stack to update (required)'),
            MutuallyExclusiveArgList(
                Arg('--template-file', dest='TemplateBody',
                    metavar='FILE', type=open,
                    help='file containing a new JSON template for the stack'),
                Arg('--template-url', dest='TemplateURL', metavar='URL',
                    help='URL pointing to a new JSON template for the stack'))
            .required(),
            Arg('-p', '--parameter', dest='Parameters.member',
                metavar='KEY=VALUE', type=parameter_def, action='append',
                help='''key and value of the parameters to use with the
                stack's template, separated by an "=" character''')]

    def print_result(self, result):
        print result.get('StackId')

########NEW FILE########
__FILENAME__ = validatetemplate
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.cloudformation import CloudFormationRequest


class ValidateTemplate(CloudFormationRequest):
    DESCRIPTION = 'Validate a template'
    ARGS = [MutuallyExclusiveArgList(
                Arg('--template-file', dest='TemplateBody',
                    metavar='FILE', type=open,
                    help='file location containing JSON template'),
                Arg('--template-url', dest='TemplateURL',
                    metavar='URL', type=open,
                    help='S3 url for JSON template'))
            .required()]
    LIST_TAGS = ['Parameters', 'CapabilitiesReason', 'Capabilities']

    def print_result(self, result):
        print self.tabify(('DESCRIPTION', result.get('Description')))
        for tag in self.LIST_TAGS:
            if tag in result:
                for result in result[tag]:
                    for key, value in result.items():
                        print self.tabify([tag.upper(), key, value])

########NEW FILE########
__FILENAME__ = allocateaddress
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class AllocateAddress(EC2Request):
    DESCRIPTION = 'Allocate a public IP address'
    ARGS = [Arg('-d', '--domain', dest='Domain', metavar='vpc',
                choices=('vpc',), help='''[VPC only] "vpc" to allocate the
                address for use in a VPC''')]

    def print_result(self, result):
        print self.tabify(('ADDRESS', result.get('publicIp'),
                           result.get('domain', 'standard'),
                           result.get('allocationId')))

########NEW FILE########
__FILENAME__ = associateaddress
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request


class AssociateAddress(EC2Request):
    DESCRIPTION = 'Associate an elastic IP address with a running instance'
    ARGS = [Arg('PublicIp', metavar='ADDRESS', nargs='?', help='''[Non-VPC
                only] IP address to associate (required)'''),
            Arg('-a', '--allocation-id', dest='AllocationId', metavar='ALLOC',
                help='[VPC only] VPC allocation ID (required)'),
            MutuallyExclusiveArgList(
                Arg('-i', '--instance-id', dest='InstanceId',
                    metavar='INSTANCE', help='''ID of the instance to associate
                    the address with'''),
                Arg('-n', '--network-interface', dest='NetworkInterfaceId',
                    metavar='INTERFACE', help='''[VPC only] network interface
                    to associate the address with'''))
            .required(),
            Arg('-p', '--private-ip-address', dest='PrivateIpAddress',
                metavar='ADDRESS', help='''[VPC only] the private address to
                associate with the address being associated in the VPC
                (default: primary private IP)'''),
            Arg('--allow-reassociation', dest='AllowReassociation',
                action='store_const', const='true',
                help='''[VPC only] allow the address to be associated even if
                it is already associated with another interface''')]

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if (self.args.get('PublicIp') is not None and
                self.args.get('AllocationId') is not None):
            # Can't be both EC2 and VPC
            raise ArgumentError(
                'argument -a/--allocation-id: not allowed with an IP address')
        if (self.args.get('PublicIp') is None and
                self.args.get('AllocationId') is None):
            # ...but we still have to be one of them
            raise ArgumentError(
                'argument -a/--allocation-id or an IP address is required')

    def print_result(self, result):
        if self.args.get('AllocationId'):
            # VPC
            print self.tabify(('ADDRESS', self.args.get('InstanceId'),
                               self.args.get('AllocationId'),
                               result.get('associationId'),
                               self.args.get('PrivateIpAddress')))
        else:
            # EC2
            print self.tabify(('ADDRESS', self.args.get('PublicIp'),
                               self.args.get('InstanceId')))

########NEW FILE########
__FILENAME__ = associateroutetable
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class AssociateRouteTable(EC2Request):
    DESCRIPTION = 'Associate a VPC route table with a subnet'
    ARGS = [Arg('RouteTableId', metavar='RTABLE',
                help='ID of the route table to associate (required)'),
            Arg('-s', dest='SubnetId', metavar='SUBNET', required=True,
                help='''ID of the subnet to associate the route table
                with (required)''')]

    def print_result(self, result):
        print self.tabify(('ASSOCIATION', result.get('associationId'),
                           self.args['RouteTableId'], self.args['SubnetId']))

########NEW FILE########
__FILENAME__ = attachvolume
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class AttachVolume(EC2Request):
    DESCRIPTION = 'Attach an EBS volume to an instance'
    ARGS = [Arg('-i', '--instance', dest='InstanceId', metavar='INSTANCE',
                required=True,
                help='instance to attach the volume to (required)'),
            Arg('-d', '--device', dest='Device', required=True,
                help='device name exposed to the instance (required)'),
            Arg('VolumeId', metavar='VOLUME',
                help='ID of the volume to attach (required)')]

    def print_result(self, result):
        self.print_attachment(result)

########NEW FILE########
__FILENAME__ = bundleinstance
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import time

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request


class BundleInstance(EC2Request):
    DESCRIPTION = 'Bundle an S3-backed Windows instance'
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to bundle (required)'),
            Arg('-b', '--bucket', dest='Storage.S3.Bucket', metavar='BUCKET',
                required=True, help='''bucket in which to store the new machine
                image (required)'''),
            Arg('-p', '--prefix', dest='Storage.S3.Prefix', metavar='PREFIX',
                required=True,
                help='beginning of the machine image bundle name (required)'),
            Arg('-o', '--owner-akid', '--user-access-key', metavar='KEY-ID',
                dest='Storage.S3.AWSAccessKeyId', required=True,
                help="bucket owner's access key ID (required)"),
            Arg('-c', '--policy', metavar='POLICY',
                dest='Storage.S3.UploadPolicy',
                help='''Base64-encoded upload policy that allows the server
                        to upload a bundle on your behalf.  If unused, -w is
                        required.'''),
            Arg('-s', '--policy-signature', metavar='SIGNATURE',
                dest='Storage.S3.UploadPolicySignature',
                help='''signature of the Base64-encoded upload policy.  If
                        unused, -w is required.'''),
            Arg('-w', '--owner-sak', '--user-secret-key', metavar='KEY',
                route_to=None,
                help="""bucket owner's secret access key, used to sign upload
                        policies.  This is required unless both -c and -s are
                        used."""),
            Arg('-x', '--expires', metavar='HOURS', type=int, default=24,
                route_to=None,
                help='generated upload policy expiration time (default: 24)')]

    def generate_default_policy(self):
        delta = timedelta(hours=self.args['expires'])
        expire_time = (datetime.utcnow() + delta).replace(microsecond=0)

        conditions = [{'acl': 'ec2-bundle-read'},
                      {'bucket': self.args.get('Storage.S3.Bucket')},
                      ['starts-with', '$key',
                       self.args.get('Storage.S3.Prefix')]]
        policy = {'conditions': conditions,
                  'expiration': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                              expire_time.timetuple())}
        policy_json = json.dumps(policy)
        self.log.info('generated default policy: %s', policy_json)
        self.params['Storage.S3.UploadPolicy'] = base64.b64encode(policy_json)

    def sign_policy(self):
        my_hmac = hmac.new(self.args['owner_sak'], digestmod=hashlib.sha1)
        my_hmac.update(self.params.get('Storage.S3.UploadPolicy'))
        self.params['Storage.S3.UploadPolicySignature'] = \
            base64.b64encode(my_hmac.digest())

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if not self.args.get('Storage.S3.UploadPolicy'):
            if not self.args.get('owner_sak'):
                raise ArgumentError('argument -w/--owner-sak is required when '
                                    '-c/--policy is not used')
        elif not self.args.get('Storage.S3.UploadPolicySignature'):
            if not self.args.get('owner_sak'):
                raise ArgumentError('argument -w/--owner-sak is required when '
                                    '-s/--policy-signature is not used')

    def preprocess(self):
        if not self.args.get('Storage.S3.UploadPolicy'):
            self.generate_default_policy()
        if not self.args.get('Storage.S3.UploadPolicySignature'):
            self.sign_policy()

    def print_result(self, result):
        self.print_bundle_task(result['bundleInstanceTask'])

########NEW FILE########
__FILENAME__ = cancelbundletask
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class CancelBundleTask(EC2Request):
    DESCRIPTION = 'Cancel an instance bundling operation'
    ARGS = [Arg('BundleId', metavar='TASK-ID',
                help='ID of the bundle task to cancel (required)')]

    def print_result(self, result):
        self.print_bundle_task(result.get('bundleInstanceTask'))

########NEW FILE########
__FILENAME__ = cancelconversiontask
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class CancelConversionTask(EC2Request):
    DESCRIPTION = 'Cancel an import task'
    ARGS = [Arg('ConversionTaskId', metavar='TASK-ID',
                help='ID of the import task to cancel (required)')]

########NEW FILE########
__FILENAME__ = confirmproductinstance
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class ConfirmProductInstance(EC2Request):
    DESCRIPTION = 'Verify if a product code is associated with an instance'
    ARGS = [Arg('ProductCode', metavar='CODE',
                help='product code to confirm (required)'),
            Arg('-i', '--instance', dest='InstanceId', metavar='INSTANCE',
                required=True,
                help='ID of the instance to confirm (required)')]

    def print_result(self, result):
        print self.tabify((self.args['ProductCode'], self.args['InstanceId'],
                           result.get('return'), result.get('ownerId')))

########NEW FILE########
__FILENAME__ = copyimage
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class CopyImage(EC2Request):
    DESCRIPTION = ('Copy an image from another region\n\nRun this command '
                   'against the destination region, not the source region.')
    ARGS = [Arg('-r', '--source-region', dest='SourceRegion', metavar='REGION',
                required=True,
                help='name of the region to copy the image from (required)'),
            Arg('-s', '--source-ami-id', dest='SourceImageId', metavar='IMAGE',
                required=True,
                help='ID of the image to copy (required)'),
            Arg('-n', '--name', dest='Name',
                help='name to assign the new copy of the image'),
            Arg('-d', '--description', dest='Description', metavar='DESC',
                help='description to assign the new copy of the image'),
            Arg('-c', '--client-token', dest='ClientToken', metavar='TOKEN',
                help='unique identifier to ensure request idempotency')]

    def print_result(self, result):
        print self.tabify(('IMAGE', result.get('imageId')))

########NEW FILE########
__FILENAME__ = createimage
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.argtypes import ec2_block_device_mapping
from euca2ools.commands.ec2 import EC2Request


class CreateImage(EC2Request):
    DESCRIPTION = 'Create an EBS image from a running or stopped EBS instance'
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='instance from which to create the image (required)'),
            Arg('-n', '--name', dest='Name', required=True,
                help='name for the new image (required)'),
            Arg('-d', '--description', dest='Description', metavar='DESC',
                help='description for the new image'),
            Arg('--no-reboot', dest='NoReboot', action='store_const',
                const='true', help='''do not shut down the instance before
                creating the image. Image integrity may be affected.'''),
            Arg('-b', '--block-device-mapping', metavar='DEVICE=MAPPED',
                dest='BlockDeviceMapping', action='append',
                type=ec2_block_device_mapping, default=[],
                help='''define a block device mapping for the image, in the
                form DEVICE=MAPPED, where "MAPPED" is "none", "ephemeral(0-3)",
                or
                "[SNAP_ID]:[GiB]:[true|false]:[standard|VOLTYPE[:IOPS]]"''')]

    def print_result(self, result):
        print self.tabify(('IMAGE', result.get('imageId')))

########NEW FILE########
__FILENAME__ = createkeypair
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
import os
from requestbuilder import Arg


class CreateKeyPair(EC2Request):
    DESCRIPTION = 'Create a new SSH key pair for use with instances'
    ARGS = [Arg('KeyName', metavar='KEYPAIR',
                help='name of the new key pair (required)'),
            Arg('-f', '--filename', metavar='FILE', route_to=None,
                help='file name to save the private key to')]

    def print_result(self, result):
        print self.tabify(('KEYPAIR', result['keyName'],
                           result['keyFingerprint']))
        if self.args.get('filename'):
            prev_umask = os.umask(0o077)
            with open(self.args['filename'], 'w') as privkeyfile:
                privkeyfile.write(result['keyMaterial'])
            os.umask(prev_umask)
        else:
            print result['keyMaterial']

########NEW FILE########
__FILENAME__ = createnetworkacl
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class CreateNetworkAcl(EC2Request):
    DESCRIPTION = 'Create a new VPC network ACL'
    ARGS = [Arg('VpcId', metavar='VPC', help='''ID of the VPC in which
                to create the new network ACL (required)''')]
    LIST_TAGS = ['associationSet', 'entrySet', 'tagSet']

    def print_result(self, result):
        self.print_network_acl(result.get('networkAcl') or {})

########NEW FILE########
__FILENAME__ = createroute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.ec2 import EC2Request


class CreateRoute(EC2Request):
    DESCRIPTION = 'Add a route to a VPC route table'
    API_VERSION = '2014-02-01'
    ARGS = [Arg('RouteTableId', metavar='RTABLE',
                help='ID of the route table to add the route to (required)'),
            Arg('-r', '--cidr', dest='DestinationCidrBlock',
                metavar='CIDR', required=True,
                help='CIDR address block the route should affect (required)'),
            MutuallyExclusiveArgList(
                Arg('-g', '--gateway-id', dest='GatewayId', metavar='GATEWAY',
                    help='ID of an Internet gateway to target'),
                Arg('-i', '--instance', dest='InstanceId', metavar='INSTANCE',
                    help='ID of a NAT instance to target'),
                Arg('-n', '--network-interface', dest='NetworkInterfaceId',
                    help='ID of a network interface to target'),
                Arg('-p', '--vpc-peering-connection', metavar='PEERCON',
                    dest='VpcPeeringConnectionId',
                    help='ID of a VPC peering connection to target'))
            .required()]

    def print_result(self, _):
        target = (self.args.get('GatewayId') or self.args.get('InstanceId') or
                  self.args.get('NetworkInterfaceId') or
                  self.args.get('VpcPeeringConnectionId'))
        print self.tabify(('ROUTE', target, self.args['DestinationCidrBlock']))

########NEW FILE########
__FILENAME__ = createroutetable
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class CreateRouteTable(EC2Request):
    DESCRIPTION = 'Create a new VPC route table'
    ARGS = [Arg('VpcId', metavar='VPC',
                help='ID of the VPC to create the route table in (required)')]
    LIST_TAGS = ['associationSet', 'propagatingVgwSet', 'routeTableSet',
                 'routeSet', 'tagSet']

    def print_result(self, result):
        self.print_route_table(result.get('routeTable') or {})

########NEW FILE########
__FILENAME__ = createsecuritygroup
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class CreateSecurityGroup(EC2Request):
    DESCRIPTION = 'Create a new security group'
    ARGS = [Arg('GroupName', metavar='GROUP',
                help='name of the new group (required)'),
            Arg('-d', '--description', dest='GroupDescription', metavar='DESC',
                required=True, help='description of the new group (required)'),
            Arg('-c', '--vpc', dest='VpcId', metavar='VPC',
                help='[VPC only] ID of the VPC to create the group in')]

    def print_result(self, result):
        print self.tabify(('GROUP', result.get('groupId'),
                           self.args['GroupName'],
                           self.args['GroupDescription']))

########NEW FILE########
__FILENAME__ = createsnapshot
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class CreateSnapshot(EC2Request):
    DESCRIPTION = 'Create a snapshot of a volume'
    ARGS = [Arg('VolumeId', metavar='VOLUME',
                help='volume to create a snapshot of (required)'),
            Arg('-d', '--description', metavar='DESC', dest='Description',
                help='snapshot description')]

    def print_result(self, result):
        print self.tabify(('SNAPSHOT', result.get('snapshotId'),
                           result.get('volumeId'), result.get('status'),
                           result.get('startTime'), result.get('ownerId'),
                           result.get('volumeSize'),
                           result.get('description')))

########NEW FILE########
__FILENAME__ = createsubnet
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class CreateSubnet(EC2Request):
    DESCRIPTION = 'Create a new VPC subnet'
    ARGS = [Arg('-c', '--vpc', dest='VpcId', required=True,
                help='ID of the VPC to create the new subnet in (required)'),
            Arg('-i', '--cidr', dest='CidrBlock', metavar='CIDR',
                required=True,
                help='CIDR address block for the new subnet (required)'),
            Arg('-z', '--availability-zone', dest='AvailabilityZone',
                help='availability zone in which to create the new subnet')]
    LIST_TAGS = ['tagSet']

    def print_result(self, result):
        self.print_subnet(result.get('subnet') or {})

########NEW FILE########
__FILENAME__ = createtags
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import binary_tag_def
from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class CreateTags(EC2Request):
    DESCRIPTION = 'Add or overwrite tags for one or more resources'
    ARGS = [Arg('ResourceId', metavar='RESOURCE', nargs='+',
                help='ID(s) of the resource(s) to tag (at least 1 required)'),
            Arg('--tag', dest='Tag', metavar='KEY[=VALUE]',
                type=binary_tag_def, action='append', required=True,
                help='''key and optional value of the tag to create, separated
                by an "=" character.  If no value is given the tag's value is
                set to an empty string.  (at least 1 required)''')]

    def print_result(self, _):
        for resource_id in self.args['ResourceId']:
            for tag in self.args['Tag']:
                lc_resource_tag = {'key': tag['Key'], 'value': tag['Value']}
                self.print_resource_tag(lc_resource_tag, resource_id)

########NEW FILE########
__FILENAME__ = createvolume
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request


class CreateVolume(EC2Request):
    DESCRIPTION = 'Create a new volume'
    ARGS = [Arg('-z', '--availability-zone', dest='AvailabilityZone',
                metavar='ZONE', required=True, help='''availability zone in
                which to create the new volume (required)'''),
            Arg('-s', '--size', dest='Size', metavar='GiB', type=int,
                help='''size of the new volume in GiB (required unless
                --snapshot is used)'''),
            Arg('--snapshot', dest='SnapshotId', metavar='SNAPSHOT',
                help='snapshot from which to create the new volume'),
            Arg('-t', '--type', dest='VolumeType', metavar='VOLTYPE',
                help='volume type'),
            Arg('-i', '--iops', dest='Iops', type=int,
                help='number of I/O operations per second')]

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if not self.args.get('Size') and not self.args.get('SnapshotId'):
            raise ArgumentError('-s/--size or --snapshot must be specified')
        if self.args.get('Iops') and not self.args.get('VolumeType'):
            raise ArgumentError('argument -i/--iops: -t/--type is required')
        if self.args.get('Iops') and self.args.get('VolumeType') == 'standard':
            raise ArgumentError(
                'argument -i/--iops: not allowed with volume type "standard"')

    def print_result(self, result):
        print self.tabify(('VOLUME', result.get('volumeId'),
                           result.get('size'), result.get('snapshotId'),
                           result.get('availabilityZone'),
                           result.get('status'), result.get('createTime')))

########NEW FILE########
__FILENAME__ = createvpc
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class CreateVpc(EC2Request):
    DESCRIPTION = 'Create a new VPC'
    ARGS = [Arg('CidrBlock', metavar='CIDR',
                help='Address CIDR block for the new VPC (required)'),
            Arg('--tenancy', dest='instanceTenancy',
                choices=('default', 'dedicated'),
                help='the type of instance tenancy to use')]
    LIST_TAGS = ['tagSet']

    def print_result(self, result):
        self.print_vpc(result.get('vpc') or {})

########NEW FILE########
__FILENAME__ = deletediskimage
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import tempfile

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request
from euca2ools.commands.ec2.describeconversiontasks import \
    DescribeConversionTasks
from euca2ools.commands.ec2.mixins import S3AccessMixin
from euca2ools.commands.ec2.structures import ImportManifest
from euca2ools.commands.s3.deleteobject import DeleteObject
from euca2ools.commands.s3.getobject import GetObject
from euca2ools.exceptions import AWSError


class DeleteDiskImage(EC2Request, S3AccessMixin):
    DESCRIPTION = 'Delete a disk image used for an import task'
    ARGS = [MutuallyExclusiveArgList(
                Arg('-t', '--task',
                    help='ID of the task to delete the image from'),
                Arg('-u', '--manifest-url',
                    help='location of the import manifest'))
            .required(),
            Arg('--ignore-active-task', action='store_true',
                help='''delete the image even if the import task is active
                (only works with -t/--task)''')]

    def configure(self):
        EC2Request.configure(self)
        self.configure_s3_access()
        if self.args.get('ignore_active_task') and not self.args.get('task'):
            raise ArgumentError('argument --ignore-active-task my only be '
                                'used with -t/--task')

    def main(self):
        if self.args.get('manifest_url'):
            manifest_url = self.args['manifest_url']
        if self.args.get('task'):
            desc_conv = DescribeConversionTasks.from_other(
                self, ConversionTaskId=[self.args['task']])
            task = desc_conv.main()['conversionTasks'][0]
            assert task['conversionTaskId'] == self.args['task']
            if task.get('importVolume'):
                vol_container = task['importVolume']
            else:
                vol_container = task['importInstance']['volumes'][0]
            manifest_url = vol_container['image']['importManifestUrl']
        _, bucket, key = self.args['s3_service'].resolve_url_to_location(
            manifest_url)
        manifest_s3path = '/'.join((bucket, key))
        manifest = self.__download_manifest(manifest_s3path)

        for part in manifest.image_parts:
            delete_req = DeleteObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'], path='/'.join((bucket, part.key)))
            delete_req.main()
        delete_req = DeleteObject.from_other(
            self, service=self.args['s3_service'], auth=self.args['s3_auth'],
            path=manifest_s3path)
        delete_req.main()

    def __download_manifest(self, s3path):
        with tempfile.SpooledTemporaryFile(max_size=1024000) as \
                manifest_destfile:
            get_req = GetObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'], source=s3path,
                dest=manifest_destfile, show_progress=False)
            try:
                get_req.main()
            except AWSError as err:
                if err.status_code == 404:
                    raise ArgumentError('import manifest "{0}" does not exist'
                                        .format(s3path))
                raise
            manifest_destfile.seek(0)
            return ImportManifest.read_from_fileobj(manifest_destfile)

########NEW FILE########
__FILENAME__ = deletekeypair
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeleteKeyPair(EC2Request):
    DESCRIPTION = 'Delete a key pair'
    ARGS = [Arg('KeyName', metavar='KEYPAIR',
                help='name of the key pair to delete (required)')]

    def print_result(self, _):
        print self.tabify(('KEYPAIR', self.args['KeyName']))

########NEW FILE########
__FILENAME__ = deletenetworkacl
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteNetworkAcl(EC2Request):
    DESCRIPTION = 'Delete a VPC network ACL'
    ARGS = [Arg('NetworkAclId', metavar='ACL',
                help='ID of the network ACL to delete (required)')]

########NEW FILE########
__FILENAME__ = deletenetworkaclentry
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteNetworkAclEntry(EC2Request):
    DESCRIPTION = 'Delete a network acl rule'
    ARGS = [Arg('NetworkAclId', metavar='NACL', help='''ID of the
                network ACL to delete an entry from (required)'''),
            Arg('-n', '--rule-number', dest='RuleNumber', required=True,
                type=int, help='number of the entry to delete (required)'),
            Arg('--egress', dest='Egress', action='store_true', help='''delete
                an egress entry (default: delete an ingress entry)''')]

########NEW FILE########
__FILENAME__ = deleteroute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteRoute(EC2Request):
    DESCRIPTION = 'Delete a route from a VPC route table'
    ARGS = [Arg('RouteTableId', metavar='RTABLE',
                help='ID of the table to remove the route from (required)'),
            Arg('-r', '--cidr', dest='DestinationCidrBlock', required=True,
                help='CIDR address block of the route to delete (required)')]

########NEW FILE########
__FILENAME__ = deleteroutetable
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteRouteTable(EC2Request):
    DESCRIPTION = 'Delete a VPC route table'
    ARGS = [Arg('RouteTableId', metavar='RTABLE',
                help='ID of the route table to delete (required)')]

########NEW FILE########
__FILENAME__ = deletesecuritygroup
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeleteSecurityGroup(EC2Request):
    DESCRIPTION = 'Delete a security group'
    ARGS = [Arg('group', metavar='GROUP', route_to=None,
                help='name or ID of the security group to delete (required)')]

    def preprocess(self):
        if self.args['group'].startswith('sg-'):
            self.params['GroupId'] = self.args['group']
        else:
            self.params['GroupName'] = self.args['group']

    def print_result(self, result):
        print self.tabify(('RETURN', result.get('return')))

########NEW FILE########
__FILENAME__ = deletesnapshot
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeleteSnapshot(EC2Request):
    DESCRIPTION = 'Delete a snapshot'
    ARGS = [Arg('SnapshotId', metavar='SNAPSHOT',
                help='ID of the snapshot to delete (required)')]

    def print_result(self, _):
        print self.tabify(('SNAPSHOT', self.args['SnapshotId']))

########NEW FILE########
__FILENAME__ = deletesubnet
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteSubnet(EC2Request):
    DESCRIPTION = 'Delete a VPC subnet'
    ARGS = [Arg('SubnetId', metavar='SUBNET',
                help='ID of the subnet to delete (required)')]

########NEW FILE########
__FILENAME__ = deletetags
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import ternary_tag_def
from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeleteTags(EC2Request):
    DESCRIPTION = 'Delete tags from one or more resources'
    ARGS = [Arg('ResourceId', metavar='RESOURCE', nargs='+', help='''ID(s) of
                the resource(s) to un-tag (at least 1 required)'''),
            Arg('--tag', dest='Tag', metavar='KEY[=[VALUE]]',
                type=ternary_tag_def, action='append', required=True,
                help='''key and optional value of the tag to delete, separated
                by an "=" character.  If you specify a value then the tag is
                deleted only if its value matches the one you specified.  If
                you specify the empty string as the value (e.g. "--tag foo=")
                then the tag is deleted only if its value is the empty
                string.  If you do not specify a value (e.g. "--tag foo") then
                the tag is deleted regardless of its value. (at least 1
                required)''')]

########NEW FILE########
__FILENAME__ = deletevolume
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeleteVolume(EC2Request):
    DESCRIPTION = 'Delete a volume'
    ARGS = [Arg('VolumeId', metavar='VOLUME',
                help='ID of the volume to delete (required)')]

    def print_result(self, _):
        print self.tabify(('VOLUME', self.args['VolumeId']))

########NEW FILE########
__FILENAME__ = deletevpc
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DeleteVpc(EC2Request):
    DESCRIPTION = 'Delete a VPC'
    ARGS = [Arg('VpcId', metavar='VPC',
                help='ID of the VPC to delete (required)')]

########NEW FILE########
__FILENAME__ = deregisterimage
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DeregisterImage(EC2Request):
    DESCRIPTION = ('De-register an image.  After you de-register an image it '
                   'cannot be used to launch new instances.\n\nNote that in '
                   'Eucalyptus 3 you may need to run this twice to completely '
                   "remove an image's registration from the system.")
    ARGS = [Arg('ImageId', metavar='IMAGE',
                help='ID of the image to de-register (required)')]

    def print_result(self, _):
        print self.tabify(('IMAGE', self.args['ImageId']))

########NEW FILE########
__FILENAME__ = describeaddresses
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeAddresses(EC2Request):
    DESCRIPTION = 'Show information about elastic IP addresses'
    ARGS = [Arg('address', metavar='ADDRESS', nargs='*', route_to=None,
                help='''limit results to specific elastic IP addresses or
                VPC allocation IDs''')]
    FILTERS = [Filter('allocation-id', help='[VPC only] allocation ID'),
               Filter('association-id', help='[VPC only] association ID'),
               Filter('domain', help='''whether the address is a standard
                      ("standard") or VPC ("vpc") address'''),
               Filter('instance-id',
                      help='instance the address is associated with'),
               Filter('network-interface-id', help='''[VPC only] network
                      interface the address is associated with'''),
               Filter('network-interface-owner-id', help='''[VPC only] ID of
                      the network interface's owner'''),
               Filter('private-ip-address', help='''[VPC only] private address
                      associated with the public address'''),
               Filter('public-ip', help='the elastic IP address')]
    LIST_TAGS = ['addressesSet']

    def preprocess(self):
        alloc_ids = set(addr for addr in self.args.get('address', [])
                        if addr.startswith('eipalloc-'))
        public_ips = set(self.args.get('address', [])) - alloc_ids
        if alloc_ids:
            self.params['AllocationId'] = list(sorted(alloc_ids))
        if public_ips:
            self.params['PublicIp'] = list(sorted(public_ips))

    def print_result(self, result):
        for addr in result.get('addressesSet', []):
            print self.tabify(('ADDRESS', addr.get('publicIp'),
                               addr.get('instanceId'),
                               addr.get('domain', 'standard'),
                               addr.get('allocationId'),
                               addr.get('associationId'),
                               addr.get('networkInterfaceId'),
                               addr.get('privateIpAddress')))

########NEW FILE########
__FILENAME__ = describeavailabilityzones
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeAvailabilityZones(EC2Request):
    DESCRIPTION = 'Display availability zones within the current region'
    ARGS = [Arg('ZoneName', metavar='ZONE', nargs='*',
                help='limit results to specific availability zones')]
    FILTERS = [Filter('message', help='''message giving information about the
                      availability zone'''),
               Filter('region-name',
                      help='region the availability zone is in'),
               Filter('state', help='state of the availability zone'),
               Filter('zone-name', help='name of the availability zone')]
    LIST_TAGS = ['availabilityZoneInfo', 'messageSet']

    def print_result(self, result):
        for zone in result.get('availabilityZoneInfo', []):
            msgs = ', '.join(msg for msg in zone.get('messageSet', []))
            print self.tabify(('AVAILABILITYZONE', zone.get('zoneName'),
                               zone.get('zoneState'), msgs))

########NEW FILE########
__FILENAME__ = describebundletasks
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeBundleTasks(EC2Request):
    DESCRIPTION = 'Describe current instance-bundling tasks'
    ARGS = [Arg('BundleId', metavar='BUNDLE', nargs='*',
                help='limit results to specific bundle tasks')]
    FILTERS = [Filter('bundle-id', help='bundle task ID'),
               Filter('error-code',
                      help='if the task failed, the error code returned'),
               Filter('error-message',
                      help='if the task failed, the error message returned'),
               Filter('instance-id', help='ID of the bundled instance'),
               Filter('progress', help='level of task completion, in percent'),
               Filter('s3-bucket',
                      help='bucket where the image will be stored'),
               Filter('s3-prefix', help='beginning of the bundle name'),
               Filter('start-time', help='task start time'),
               Filter('state', help='task state'),
               Filter('update-time', help='most recent task update time')]
    LIST_TAGS = ['bundleInstanceTasksSet']

    def print_result(self, result):
        for task in result.get('bundleInstanceTasksSet', []):
            self.print_bundle_task(task)

########NEW FILE########
__FILENAME__ = describeconversiontasks
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DescribeConversionTasks(EC2Request):
    DESCRIPTION = 'Show information about import operations'
    ARGS = [Arg('ConversionTaskId', metavar='TASK', nargs='*',
                help='limit results to specific tasks')]
    LIST_TAGS = ['conversionTasks', 'volumes']

    def print_result(self, result):
        for task in result.get('conversionTasks') or []:
            self.print_conversion_task(task)

########NEW FILE########
__FILENAME__ = describeimageattribute
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.ec2 import EC2Request


class DescribeImageAttribute(EC2Request):
    DESCRIPTION = 'Show information about an attribute of an image'
    ARGS = [Arg('ImageId', metavar='IMAGE', help='image to describe'),
            MutuallyExclusiveArgList(
                Arg('-l', '--launch-permission', dest='Attribute',
                    action='store_const', const='launchPermission',
                    help='display launch permissions'),
                Arg('-p', '--product-codes', dest='Attribute',
                    action='store_const', const='productCodes',
                    help='list associated product codes'),
                Arg('-B', '--block-device-mapping', dest='Attribute',
                    action='store_const', const='blockDeviceMapping',
                    help='describe block device mappings'),
                Arg('--kernel', dest='Attribute', action='store_const',
                    const='kernel', help='show associated kernel image ID'),
                Arg('--ramdisk', dest='Attribute', action='store_const',
                    const='ramdisk', help='show associated ramdisk image ID'),
                Arg('--description', dest='Attribute', action='store_const',
                    const='description', help="show the image's description"))
            .required()]
    LIST_TAGS = ['blockDeviceMapping', 'launchPermission', 'productCodes']

    def print_result(self, result):
        image_id = result.get('imageId')
        for perm in result.get('launchPermission', []):
            for (entity_type, entity_name) in perm.items():
                print self.tabify(('launchPermission', image_id, entity_type,
                                   entity_name))
        for code in result.get('productCodes', []):
            if 'type' in code:
                code_str = '[{0}: {1}]'.format(code['type'],
                                               code.get('productCode'))
            else:
                code_str = code.get('productCode')
            print self.tabify(('productCodes', image_id, 'productCode',
                               code_str))
        for blockdev in result.get('blockDeviceMapping', []):
            blockdev_src = (blockdev.get('virtualName') or
                            blockdev.get('ebs', {}).get('snapshotId'))
            blockdev_str = '{0}: {1}'.format(blockdev.get('deviceName'),
                                             blockdev_src)

            # TODO:  figure out how to print mappings that create new volumes
            print self.tabify(('blockDeviceMapping', image_id,
                               'blockDeviceMap', blockdev_str))
        if result.get('kernel'):
            print self.tabify(('kernel', image_id, None,
                               result['kernel'].get('value')))
        if result.get('ramdisk'):
            print self.tabify(('ramdisk', image_id, None,
                               result['ramdisk'].get('value')))
        if result.get('description'):
            print self.tabify(('description', image_id, None,
                               result['description'].get('value')))

########NEW FILE########
__FILENAME__ = describeimages
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter, GenericTagFilter
from requestbuilder.exceptions import ArgumentError


class DescribeImages(EC2Request):
    DESCRIPTION = ('Show information about images\n\nBy default, only images '
                   'your account owns and images for which your account has '
                   'explicit launch permissions are shown.')
    ARGS = [Arg('ImageId', metavar='IMAGE', nargs='*',
                help='limit results to specific images'),
            Arg('-a', '--all', action='store_true', route_to=None,
                help='describe all images'),
            Arg('-o', '--owner', dest='Owner', metavar='ACCOUNT',
                action='append',
                help='describe images owned by the specified owner'),
            Arg('-x', '--executable-by', dest='ExecutableBy',
                metavar='ACCOUNT', action='append',
                help='''describe images for which the specified account has
                explicit launch permissions''')]
    FILTERS = [Filter('architecture', help='CPU architecture'),
               Filter('block-device-mapping.delete-on-termination',
                      help='''whether a volume is deleted upon instance
                      termination'''),
               Filter('block-device-mapping.device-name',
                      help='device name for a volume mapped to the image'),
               Filter('block-device-mapping.snapshot-id',
                      help='snapshot ID for a volume mapped to the image'),
               Filter('block-device-mapping.volume-size',
                      help='volume size for a volume mapped to the image'),
               Filter('block-device-mapping.volume-type',
                      help='volume type for a volume mapped to the image'),
               Filter('description', help='image description'),
               Filter('hypervisor', help='image\'s hypervisor type'),
               Filter('image-id'),
               Filter('image-type',
                      help='image type ("machine", "kernel", or "ramdisk")'),
               Filter('is-public', help='whether the image is public'),
               Filter('kernel-id'),
               Filter('manifest-location'),
               Filter('name'),
               Filter('owner-alias', help="image owner's account alias"),
               Filter('owner-id', help="image owner's account ID"),
               Filter('platform', help='"windows" for Windows images'),
               Filter('product-code',
                      help='product code associated with the image'),
               Filter('product-code.type', help='''type of product code
                      associated with the image ("devpay", "marketplace")'''),
               Filter('ramdisk-id'),
               Filter('root-device-name'),
               Filter('root-device-type',
                      help='root device type ("ebs" or "instance-store")'),
               Filter('state', help='''image state ("available", "pending", or
                      "failed")'''),
               Filter('state-reason-code',
                      help='reason code for the most recent state change'),
               Filter('state-reason-message',
                      help='message for the most recent state change'),
               Filter('tag-key', help='key of a tag assigned to the image'),
               Filter('tag-value',
                      help='value of a tag assigned to the image'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('virtualization-type',
                      help='virtualization type ("paravirtual" or "hvm")')]
    LIST_TAGS = ['imagesSet', 'productCodes', 'blockDeviceMapping', 'tagSet']

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if self.args.get('all', False):
            if self.args.get('ImageId'):
                raise ArgumentError('argument -a/--all: not allowed with '
                                    'a list of images')
            if self.args.get('ExecutableBy'):
                raise ArgumentError('argument -a/--all: not allowed with '
                                    'argument -x/--executable-by')
            if self.args.get('Owner'):
                raise ArgumentError('argument -a/--all: not allowed with '
                                    'argument -o/--owner')

    def main(self):
        if not any(self.args.get(item) for item in ('all', 'ImageId',
                                                    'ExecutableBy', 'Owner')):
            # Default to owned images and images with explicit launch perms
            self.params['Owner'] = ['self']
            owned = self.send()
            del self.params['Owner']
            self.params['ExecutableBy'] = ['self']
            executable = self.send()
            del self.params['ExecutableBy']
            owned['imagesSet'] = (owned.get('imagesSet', []) +
                                  executable.get('imagesSet', []))
            return owned
        else:
            return self.send()

    def print_result(self, result):
        images = {}
        for image in result.get('imagesSet', []):
            images.setdefault(image['imageId'], image)
        for _, image in sorted(images.iteritems()):
            self.print_image(image)

    def print_image(self, image):
        if image.get('rootDeviceType') == 'instance-store':
            imagename = image.get('imageLocation')
        else:
            imagename = '/'.join((image.get('imageOwnerId', ''),
                                  image.get('name')))

        print self.tabify((
            'IMAGE', image.get('imageId'), imagename,
            image.get('imageOwnerAlias') or image.get('imageOwnerId'),
            image.get('imageState'),
            ('public' if image.get('isPublic') == 'true' else 'private'),
            image.get('architecture'), image.get('imageType'),
            image.get('kernelId'), image.get('ramdiskId'),
            image.get('platform'), image.get('rootDeviceType'),
            image.get('virtualizationType'), image.get('hypervisor')))
        for mapping in image.get('blockDeviceMapping', []):
            self.print_blockdevice_mapping(mapping)
        for tag in image.get('tagSet', []):
            self.print_resource_tag(tag, image.get('imageId'))

########NEW FILE########
__FILENAME__ = describeinstanceattribute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.ec2 import EC2Request


class DescribeInstanceAttribute(EC2Request):
    DESCRIPTION = ("Show one of an instance's attributes.\n\n"
                   "Note that exactly one attribute may be shown at a time.")
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to show info for (required)'),
            MutuallyExclusiveArgList(
                Arg('-b', '--block-device-mapping', dest='Attribute',
                    action='store_const', const='blockDeviceMapping',
                    help='show block device mappings'),
                Arg('--disable-api-termination', dest='Attribute',
                    action='store_const', const='disableApiTermination',
                    help='show whether termination is disabled'),
                Arg('--ebs-optimized', dest='Attribute', action='store_const',
                    const='ebsOptimized', help='''show whether the root volume
                    is optimized for EBS I/O'''),
                Arg('-g', '--group-id', dest='Attribute', action='store_const',
                    const='groupSet',
                    help='show the security groups the instance belongs to'),
                Arg('-p', '--product-code', dest='Attribute',
                    action='store_const', const='productCodes',
                    help='show any associated product codes'),
                Arg('--instance-initiated-shutdown-behavior', dest='Attribute',
                    action='store_const',
                    const='instanceInitiatedShutdownBehavior',
                    help='''show whether the instance stops or terminates
                    when shut down'''),
                Arg('-t', '--instance-type', dest='Attribute',
                    action='store_const', const='instanceType',
                    help="show the instance's type"),
                Arg('--kernel', dest='Attribute', action='store_const',
                    const='kernel', help='''show the ID of the kernel image
                    associated with the instance'''),
                Arg('--ramdisk', dest='Attribute', action='store_const',
                    const='ramdisk', help='''show the ID of the ramdisk image
                    associated with the instance'''),
                Arg('--root-device-name', dest='Attribute',
                    action='store_const', const='rootDeviceName',
                    help='''show the name of the instance's root device
                    (e.g. '/dev/sda1')'''),
                Arg('--source-dest-check', dest='Attribute',
                    action='store_const', const='sourceDestCheck',
                    help='''[VPC only] show whether source/destination checking
                    is enabled for the instance'''),
                Arg('--user-data', dest='Attribute', action='store_const',
                    const='userData', help="show the instance's user-data"))
            .required()]
    LIST_TAGS = ['blockDeviceMapping', 'groupSet', 'productCodes']

    def print_result(self, result):
        # Deal with complex data first
        if self.args['Attribute'] == 'blockDeviceMapping':
            for mapping in result.get('blockDeviceMapping', []):
                ebs = mapping.get('ebs', {})
                print self.tabify(('BLOCKDEVICE', mapping.get('deviceName'),
                                   ebs.get('volumeId'), ebs.get('attachTime'),
                                   ebs.get('deleteOnTermination')))
            # The EC2 tools have a couple more fields that I haven't been
            # able to identify.  If you figure out what they are, please send
            # a patch.
        elif self.args['Attribute'] == 'groupSet':
            # TODO:  test this in the wild (I don't have a VPC to work with)
            groups = (group.get('groupId') or group.get('groupName')
                      for group in result.get('groupSet', []))
            print self.tabify(('groupSet', result.get('instanceId'),
                               ', '.join(groups)))
        elif self.args['Attribute'] == 'productCodes':
            # TODO:  test this in the wild (I don't have anything I can test
            #        it with)
            codes = (code.get('productCode') for code in
                     result.get('productCodes', []))
            print self.tabify(('productCodes', result.get('instanceId'),
                               ', '.join(codes)))
        elif self.args['Attribute'] == 'userData':
            userdata = base64.b64decode(result.get('userData', {})
                                        .get('value', ''))
            if userdata:
                print self.tabify(('userData', result.get('instanceId')))
                print userdata
            else:
                print self.tabify(('userData', result.get('instanceId'), None))
        else:
            attr = result.get(self.args['Attribute'])
            if isinstance(attr, dict) and 'value' in attr:
                attr = attr['value']
            print self.tabify((self.args['Attribute'],
                               result.get('instanceId'), attr))

########NEW FILE########
__FILENAME__ = describeinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter, GenericTagFilter


class DescribeInstances(EC2Request):
    DESCRIPTION = 'Show information about instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='*',
                help='limit results to specific instances')]
    FILTERS = [Filter('architecture', help='CPU architecture'),
               Filter('association.allocation-id',
                      help='''[VPC only] allocation ID bound to a network
                      interface's elastic IP address'''),
               Filter('association.association-id', help='''[VPC only]
                      association ID returned when an elastic IP was associated
                      with a network interface'''),
               Filter('association.ip-owner-id',
                      help='''[VPC only] ID of the owner of the elastic IP
                      address associated with a network interface'''),
               Filter('association.public-ip', help='''[VPC only] address of
                      the elastic IP address bound to a network interface'''),
               Filter('availability-zone'),
               Filter('block-device-mapping.attach-time',
                      help='volume attachment time'),
               Filter('block-device-mapping.delete-on-termination', type=bool,
                      help='''whether a volume is deleted upon instance
                      termination'''),
               Filter('block-device-mapping.device-name',
                      help='volume device name (e.g. /dev/sdf)'),
               Filter('block-device-mapping.status', help='volume status'),
               Filter('block-device-mapping.volume-id', help='volume ID'),
               Filter('client-token',
                      help='idempotency token provided at instance run time'),
               Filter('dns-name', help='public DNS name'),
               # EC2's documentation for "group-id" refers VPC users to
               # "instance.group-id", while their documentation for the latter
               # refers them to the former.  Consequently, I'm not going to
               # document a difference for either.  They both seem to work for
               # non-VPC instances.
               Filter('group-id', help='security group ID'),
               Filter('group-name', help='security group name'),
               Filter('hypervisor', help='hypervisor type'),
               Filter('image-id', help='machine image ID'),
               Filter('instance.group-id', help='security group ID'),
               Filter('instance.group-name', help='security group name'),
               Filter('instance-id'),
               Filter('instance-lifecycle',
                      help='whether this is a spot instance'),
               Filter('instance-state-code', type=int,
                      help='numeric code identifying instance state'),
               Filter('instance-state-name', help='instance state'),
               Filter('instance-type'),
               Filter('ip-address', help='public IP address'),
               Filter('kernel-id', help='kernel image ID'),
               Filter('key-name',
                      help='key pair name provided at instance launch time'),
               Filter('launch-index',
                      help='launch index within a reservation'),
               Filter('launch-time', help='instance launch time'),
               Filter('monitoring-state',
                      help='monitoring state ("enabled" or "disabled")'),
               Filter('network-interface.addresses.association.ip-owner-id',
                      help='''[VPC only] ID of the owner of the private IP
                      address associated with a network interface'''),
               Filter('network-interface.addresses.association.public-ip',
                      help='''[VPC only] ID of the association of an elastic IP
                      address with a network interface'''),
               Filter('network-interface.addresses.primary',
                      help='''[VPC only] whether the IP address of the VPC
                      network interface is the primary private IP address
                      ("true" or "false")'''),
               Filter('network-interface.addresses.private-ip-address',
                      help='''[VPC only] network interface's private IP
                      address'''),
               Filter('network-interface.attachment.device-index', type=int,
                      help='''[VPC only] device index to which a network
                      interface is attached'''),
               Filter('network-interface.attachment.attach-time',
                      help='''[VPC only] time a network interface was attached
                      to an instance'''),
               Filter('network-interface.attachment.attachment-id',
                      help='''[VPC only] ID of a network interface's
                      attachment'''),
               Filter('network-interface.attachment.delete-on-termination',
                      help='''[VPC only] whether a network interface attachment
                      is deleted when an instance is terminated ("true" or
                      "false")'''),
               Filter('network-interface.attachment.instance-owner-id',
                      help='''[VPC only] ID of the instance to which a network
                      interface is attached'''),
               Filter('network-interface.attachment.status',
                      help="[VPC only] network interface's attachment status"),
               Filter('network-interface.availability-zone',
                      help="[VPC only] network interface's availability zone"),
               Filter('network-interface.description',
                      help='[VPC only] description of a network interface'),
               Filter('network-interface.group-id',
                      help="[VPC only] network interface's security group ID"),
               Filter('network-interface.group-name', help='''[VPC only]
                      network interface's security group name'''),
               Filter('network-interface.mac-address',
                      help="[VPC only] network interface's hardware address"),
               Filter('network-interface.network-interface.id',
                      help='[VPC only] ID of a network interface'),
               Filter('network-interface.owner-id',
                      help="[VPC only] ID of a network interface's owner"),
               Filter('network-interface.private-dns-name',
                      help="[VPC only] network interface's private DNS name"),
               Filter('network-interface.requester-id',
                      help="[VPC only] network interface's requester ID"),
               Filter('network-interface.requester-managed',
                      help='''[VPC only] whether the network interface is
                      managed by the service'''),
               Filter('network-interface.source-destination-check',
                      help='''[VPC only] whether source/destination checking is
                      enabled for a network interface ("true" or "false")'''),
               Filter('network-interface.status',
                      help="[VPC only] network interface's status"),
               Filter('network-interface.subnet-id',
                      help="[VPC only] ID of a network interface's subnet"),
               Filter('network-interface.vpc-id',
                      help="[VPC only] ID of a network interface's VPC"),
               Filter('owner-id', help="instance owner's account ID"),
               Filter('placement-group-name'),
               Filter('platform', help='"windows" for Windows instances'),
               Filter('private-dns-name'),
               Filter('private-ip-address'),
               Filter('product-code'),
               Filter('product-code.type',
                      help='type of product code ("devpay" or "marketplace")'),
               Filter('ramdisk-id', help='ramdisk image ID'),
               Filter('reason',
                      help="reason for the instance's current state"),
               Filter('requester-id',
                      help='ID of the entity that launched an instance'),
               Filter('reservation-id'),
               Filter('root-device-name',
                      help='root device name (e.g. /dev/sda1)'),
               Filter('root-device-type',
                      help='root device type ("ebs" or "instance-store")'),
               Filter('spot-instance-request-id'),
               Filter('state-reason-code',
                      help='reason code for the most recent state change'),
               Filter('state-reason-message',
                      help='message describing the most recent state change'),
               Filter('subnet-id',
                      help='[VPC only] ID of the subnet the instance is in'),
               Filter('tag-key',
                      help='name of any tag assigned to the instance'),
               Filter('tag-value',
                      help='value of any tag assigned to the instance'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('virtualization-type'),
               Filter('vpc-id',
                      help='[VPC only] ID of the VPC the instance is in')]
    LIST_TAGS = ['reservationSet', 'instancesSet', 'groupSet', 'tagSet',
                 'blockDeviceMapping', 'productCodes', 'networkInterfaceSet',
                 'privateIpAddressesSet']

    def print_result(self, result):
        for reservation in result.get('reservationSet'):
            self.print_reservation(reservation)

########NEW FILE########
__FILENAME__ = describeinstancestatus
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime

from requestbuilder import Arg, Filter

from euca2ools.commands.ec2 import EC2Request


class DescribeInstanceStatus(EC2Request):
    DESCRIPTION = 'Show information about instance status and scheduled events'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='*',
                help='limit results to specific instances'),
            Arg('--hide-healthy', action='store_true', route_to=None,
                help='hide instances where all status checks pass'),
            Arg('--include-all-instances', dest='IncludeAllInstances',
                action='store_true',
                help='show all instances, not just those that are running')]
    FILTERS = [Filter('availability-zone'),
               Filter('event.code',
                      choices=('instance-reboot', 'instance-retirement',
                               'instance-stop', 'system-maintenance',
                               'instance-retirement'),
                      help='the code identifying the type of event'),
               Filter('event.description', help="an event's description"),
               Filter('event.not-after',
                      help="an event's latest possible end time"),
               Filter('event.not-before',
                      help="an event's earliest possible start time"),
               Filter('instance-state-code', type=int,
                      help='numeric code identifying instance state'),
               Filter('instance-state-name', help='instance state'),
               Filter('instance-status.status', help="instance's status",
                      choices=('ok', 'impaired', 'initializing',
                               'insufficient-data', 'not-applicable')),
               Filter('instance-status.reachability',
                      choices=('passed', 'failed', 'initializing',
                               'insufficient-data'),
                      help="instance's reachability status"),
               Filter('system-status.status', help="instance's system status",
                      choices=('ok', 'impaired', 'initializing',
                               'insufficient-data', 'not-applicable')),
               Filter('system-status.reachability',
                      choices=('passed', 'failed', 'initializing',
                               'insufficient-data'),
                      help="instance's system reachability status")]
    LIST_TAGS = ['instanceStatusSet', 'details', 'eventsSet']

    def print_result(self, result):
        for sset in result.get('instanceStatusSet') or []:
            if (self.args.get('hide_healthy', False) and
                    sset.get('systemStatus', {}).get('status') == 'ok' and
                    sset.get('instanceStatus', {}).get('status') == 'ok'):
                continue
            print self.tabify((
                'INSTANCE', sset.get('instanceId'),
                sset.get('availabilityZone'),
                sset.get('instanceState', {}).get('name'),
                sset.get('instanceState', {}).get('code'),
                sset.get('instanceStatus', {}).get('status'),
                sset.get('systemStatus', {}).get('status'),
                get_retirement_status(sset), get_retirement_date(sset)))
            for sstatus in sset.get('systemStatus', {}).get('details') or []:
                print self.tabify((
                    'SYSTEMSTATUS', sstatus.get('name'),
                    sstatus.get('status'), sstatus.get('impairedSince')))
            for istatus in sset.get('systemStatus', {}).get('details') or []:
                print self.tabify((
                    'INSTANCESTATUS', istatus.get('name'),
                    istatus.get('status'), istatus.get('impairedSince')))
            for event in sset.get('eventsSet') or []:
                print self.tabify((
                    'EVENT', event.get('code'), event.get('notBefore'),
                    event.get('notAfter'), event.get('description')))


def get_retirement_date(status_set):
    retirement_date = None
    for event in status_set.get('eventsSet', []):
        event_start = event.get('notBefore')
        if event_start is not None:
            if retirement_date is None:
                retirement_date = event_start
            else:
                date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
                event_start_datetime = datetime.datetime.strptime(
                    event.get(event_start), date_format)
                retirement_datetime = datetime.datetime.strptime(
                    retirement_date, date_format)
                if event_start_datetime < retirement_datetime:
                    retirement_date = event_start
    return retirement_date


def get_retirement_status(status_set):
    # This is more or less a guess, since retirement status isn't part of the
    # EC2 API.  The value seems to be chosen entirely client-side.
    if len(status_set.get('eventsSet', [])) > 0:
        return 'retiring'
    else:
        return 'active'

########NEW FILE########
__FILENAME__ = describeinstancetypes
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin

from euca2ools.commands.ec2 import EC2Request


class DescribeInstanceTypes(EC2Request, TabifyingMixin):
    DESCRIPTION = '[Eucalyptus only] Show information about instance types'
    ARGS = [Arg('InstanceType', metavar='INSTANCETYPE', nargs='*',
                help='limit results to specific instance types'),
            Arg('--by-zone', dest='by_zone', action='store_true',
                route_to=None,
                help='show info for each availability zone separately'),
            Arg('--show-capacity', dest='Availability', action='store_true',
                help='show info about instance capacity')]
    LIST_TAGS = ['instanceTypeDetails', 'availability']

    def configure(self):
        EC2Request.configure(self)
        if self.args.get('by_zone', False):
            self.params['Availability'] = True

    def print_result(self, result):
        vmtype_names = []  # Use a list since py2.6 lacks OrderedDict
        vmtypes = {}  # vmtype -> info and total capacity
        zones = {}  # zone -> vmtype -> info and zone capacity
        for vmtype in result.get('instanceTypeDetails', []):
            vmtype_names.append(vmtype['name'])
            vmtypes[vmtype['name']] = {'cpu': vmtype.get('cpu'),
                                       'memory': vmtype.get('memory'),
                                       'disk': vmtype.get('disk'),
                                       'available': 0,
                                       'max': 0}
            if self.params.get('Availability', False):
                for zone in vmtype.get('availability', []):
                    available = int(zone.get('available', 0))
                    max_ = int(zone.get('max', 0))
                    vmtypes[vmtype['name']]['available'] += available
                    vmtypes[vmtype['name']]['max'] += max_
                    zones.setdefault(zone['zoneName'], {})
                    zones[zone['zoneName']][vmtype['name']] = {
                        'cpu': vmtype.get('cpu'),
                        'memory': vmtype.get('memory'),
                        'disk': vmtype.get('disk'),
                        'available': available,
                        'max': max_}

        if self.args.get('by_zone'):
            for zone, zone_vmtypes in sorted(zones.iteritems()):
                print self.tabify(('AVAILABILITYZONE', zone))
                self._print_vmtypes(zone_vmtypes, vmtype_names)
                print
        else:
            self._print_vmtypes(vmtypes, vmtype_names)

    def _print_vmtypes(self, vmtypes, vmtype_names):
        # Fields and column headers
        fields = {'name': 'Name',
                  'cpu': 'CPUs',
                  'memory': 'Memory (MiB)',
                  'disk': 'Disk (GiB)',
                  'used': 'Used',
                  'total': 'Total',
                  'used_pct': 'Used %'}
        field_lengths = dict((field, len(header)) for field, header
                             in fields.iteritems())
        vmtype_infos = []
        for vmtype_name in vmtype_names:
            total = int(vmtypes[vmtype_name].get('max', 0))
            used = total - int(vmtypes[vmtype_name].get('available', 0))
            if total != 0:
                used_pct = '{0:.0%}'.format(float(used) / float(total))
            else:
                used_pct = ''
            vmtype_info = {'name': vmtype_name,
                           'cpu': vmtypes[vmtype_name].get('cpu'),
                           'memory': vmtypes[vmtype_name].get('memory'),
                           'disk': vmtypes[vmtype_name].get('disk'),
                           'used': used,
                           'total': total,
                           'used_pct': used_pct}
            vmtype_infos.append(vmtype_info)
            for field in fields:
                if len(str(vmtype_info[field])) > field_lengths[field]:
                    field_lengths[field] = len(str(vmtype_info[field]))
        type_template = ('{{name:<{name}}}  {{cpu:>{cpu}}}  '
                         '{{memory:>{memory}}}  {{disk:>{disk}}}')
        if self.args.get('Availability', False):
            type_template += ('  {{used:>{used}}} / {{total:>{total}}}  '
                              '{{used_pct:>{used_pct}}}')
        type_template = type_template.format(**field_lengths)

        print 'INSTANCETYPE\t', type_template.format(**fields)
        for vmtype_info in vmtype_infos:
            print 'INSTANCETYPE\t', type_template.format(**vmtype_info)

########NEW FILE########
__FILENAME__ = describekeypairs
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeKeyPairs(EC2Request):
    DESCRIPTION = 'Display information about available key pairs'
    ARGS = [Arg('KeyName', nargs='*', metavar='KEYPAIR',
                help='limit results to specific key pairs')]
    FILTERS = [Filter('fingerprint', help='fingerprint of the key pair'),
               Filter('key-name', help='name of the key pair')]
    LIST_TAGS = ['keySet']

    def print_result(self, result):
        for key in result.get('keySet', []):
            print self.tabify(('KEYPAIR', key.get('keyName'),
                               key.get('keyFingerprint')))

########NEW FILE########
__FILENAME__ = describenetworkacls
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, Filter, GenericTagFilter

from euca2ools.commands.ec2 import EC2Request


class DescribeNetworkAcls(EC2Request):
    DESCRIPTION = 'Describe one or more network ACLs'
    ARGS = [Arg('NetworkAclId', metavar='NACL', nargs='*',
                help='limit results to one or more network ACLs')]
    FILTERS = [Filter('association.association-id',
                      help='ID of an association ID for a network ACL'),
               Filter('association.network-acl-id', help='''ID of the
                      network ACL involved in an association'''),
               Filter('association.subnet-id',
                      help='ID of the subnet involved in an association'),
               Filter('default', choices=('true', 'false'), help='''whether
                      the network ACL is the default for its VPC'''),
               Filter('entry.cidr', help='CIDR range for a network ACL entry'),
               Filter('entry.egress', choices=('true', 'false'),
                      help='whether an entry applies to egress traffic'),
               Filter('entry.icmp.code', type=int,
                      help='ICMP code for a network ACL entry'),
               Filter('entry.icmp.type', type=int,
                      help='ICMP type for a network ACL entry'),
               Filter('entry.port-range.from', type=int,
                      help='start of the port range for a network ACL entry'),
               Filter('entry.port-range.to', type=int,
                      help='end of the port range for a network ACL entry'),
               Filter('entry.protocol',
                      help='protocol for a network ACL entry'),
               Filter('entry.rule-action', choices=('allow', 'deny'), help='''
                      whether a network ACL entry allows or denies traffic'''),
               Filter('entry.rule-number', type=int,
                      help='rule number of a network ACL entry'),
               Filter('network-acl-id'),
               Filter('tag-key',
                      help='key of a tag assigned to the network ACL'),
               Filter('tag-value',
                      help='value of a tag assigned to the network ACL'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('vpc-id', help="the VPC's ID")]

    LIST_TAGS = ['associationSet', 'entrySet', 'networkAclSet', 'tagSet']

    def print_result(self, result):
        for acl in result.get('networkAclSet') or []:
            self.print_network_acl(acl)

########NEW FILE########
__FILENAME__ = describeregions
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeRegions(EC2Request):
    DESCRIPTION = 'Display information about regions'
    ARGS = [Arg('RegionName', nargs='*', metavar='REGION',
                help='limit results to specific regions')]
    FILTERS = [Filter('endpoint'),
               Filter('region-name')]
    LIST_TAGS = ['regionInfo']

    def print_result(self, result):
        for region in result.get('regionInfo', []):
            print self.tabify(('REGION', region.get('regionName'),
                               region.get('regionEndpoint')))

########NEW FILE########
__FILENAME__ = describeroutetables
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, Filter, GenericTagFilter

from euca2ools.commands.ec2 import EC2Request


class DescribeRouteTables(EC2Request):
    DESCRIPTION = 'Describe one or more VPC route tables'
    API_VERSION = '2014-02-01'
    ARGS = [Arg('RouteTableId', metavar='RTABLE', nargs='*',
                help='limit results to specific route tables')]
    FILTERS = [Filter('association.route-table-association-id',
                      help='ID of an association for the route table'),
               Filter('association.route-table-id',
                      help='ID of a route table involved in an association'),
               Filter('association.subnet-id',
                      help='ID of a subnet involved in an association'),
               Filter('association.main', choices=('true', 'false'),
                      help='''whether the route table is the main route
                      table for its VPC'''),
               Filter('route-table-id'),
               Filter('route.destination-cidr-block', help='''CIDR address
                      block specified in one of the table's routes'''),
               Filter('route.gateway-id', help='''ID of a gateway
                      specified by a route in the table'''),
               Filter('route.vpc-peering-connection-id',
                      help='''ID of a VPC peering connection specified
                      by a route in the table'''),
               Filter('route.origin',
                      help='which operation created a route in the table'),
               Filter('route.state', help='''whether a route in the
                      table has state "active" or "blackhole"'''),
               Filter('tag-key',
                      help='key of a tag assigned to the route table'),
               Filter('tag-value',
                      help='value of a tag assigned to the route table'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('vpc-id', help="the associated VPC's ID")]

    LIST_TAGS = ['associationSet', 'propagatingVgwSet', 'routeTableSet',
                 'routeSet', 'tagSet']

    def print_result(self, result):
        for table in result.get('routeTableSet') or []:
            self.print_route_table(table)

########NEW FILE########
__FILENAME__ = describesecuritygroups
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter


class DescribeSecurityGroups(EC2Request):
    DESCRIPTION = ('Show information about security groups\n\nNote that '
                   'filters are matched on literal strings only, so '
                   '"--filter ip-permission.from-port=22" will *not* match a '
                   'group with a port range of 20 to 30.')
    ARGS = [Arg('group', metavar='GROUP', nargs='*', route_to=None,
                default=[], help='limit results to specific security groups')]
    FILTERS = [Filter('description', help='group description'),
               Filter('group-id'),
               Filter('group-name'),
               Filter('ip-permission.cidr',
                      help='CIDR IP range granted permission by the group'),
               Filter('ip-permission.from-port',
                      help='start of TCP/UDP port range, or ICMP type number'),
               Filter('ip-permission.group-name', help='''name of another group
                      granted permission by this group'''),
               Filter('ip-permission.protocol',
                      help='IP protocol for the permission'),
               Filter('ip-permission.to-port',
                      help='end of TCP/UDP port range, or ICMP code'),
               Filter('ip-permission.user-id',
                      help='ID of an account granted permission'),
               Filter('owner-id', help="account ID of the group's owner"),
               Filter('tag-key', help='key of a tag assigned to the group'),
               Filter('tag-value',
                      help='value of a tag assigned to the group'),
               Filter('vpc-id',
                      help='[VPC only] ID of a VPC the group belongs to')]
    LIST_TAGS = ['securityGroupInfo', 'ipPermissions', 'ipPermissionsEgress',
                 'groups', 'ipRanges', 'tagSet']

    def preprocess(self):
        for group in self.args['group']:
            if group.startswith('sg-'):
                self.params.setdefault('GroupId', [])
                self.params['GroupId'].append(group)
            else:
                self.params.setdefault('GroupName', [])
                self.params['GroupName'].append(group)

    def print_result(self, result):
        for group in result.get('securityGroupInfo', []):
            self.print_group(group)

    def print_group(self, group):
        print self.tabify(('GROUP', group.get('groupId'), group.get('ownerId'),
                           group.get('groupName'),
                           group.get('groupDescription'),
                           group.get('vpcId')))
        for perm in group.get('ipPermissions', []):
            perm_base = ['PERMISSION', group.get('ownerId'),
                         group.get('groupName'), 'ALLOWS',
                         perm.get('ipProtocol'), perm.get('fromPort'),
                         perm.get('toPort')]
            for cidr_range in perm.get('ipRanges', []):
                perm_item = ['FROM', 'CIDR', cidr_range.get('cidrIp'),
                             'ingress']
                print self.tabify(perm_base + perm_item)
            for othergroup in perm.get('groups', []):
                perm_item = ['FROM', 'USER', othergroup.get('userId')]
                if othergroup.get('groupId'):
                    perm_item.extend(['ID', othergroup['groupId']])
                else:
                    perm_item.extend(['GRPNAME', othergroup['groupName']])
                perm_item.append('ingress')
                print self.tabify(perm_base + perm_item)
        for perm in group.get('ipPermissionsEgress', []):
            perm_base = ['PERMISSION', group.get('ownerId'),
                         group.get('groupName'), 'ALLOWS',
                         perm.get('ipProtocol'), perm.get('fromPort'),
                         perm.get('toPort')]
            for cidr_range in perm.get('ipRanges', []):
                perm_item = ['TO', 'CIDR', cidr_range.get('cidrIp'), 'egress']
                print self.tabify(perm_base + perm_item)
            for othergroup in perm.get('groups', []):
                perm_item = ['TO', 'USER', othergroup.get('userId')]
                if othergroup.get('groupId'):
                    perm_item.extend(['ID', othergroup['groupId']])
                else:
                    perm_item.extend(['GRPNAME', othergroup['groupName']])
                perm_item.append('egress')
                print self.tabify(perm_base + perm_item)
        for tag in group.get('tagSet', []):
            self.print_resource_tag(tag, (group.get('groupId') or
                                          group.get('groupName')))

########NEW FILE########
__FILENAME__ = describesnapshots
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter, GenericTagFilter
from requestbuilder.exceptions import ArgumentError


class DescribeSnapshots(EC2Request):
    DESCRIPTION = ('Show information about snapshots\n\nBy default, only '
                   'snapshots your account owns and snapshots for which your '
                   'account has explicit restore permissions are shown.')
    ARGS = [Arg('SnapshotId', nargs='*', metavar='SNAPSHOT',
                help='limit results to specific snapshots'),
            Arg('-a', '--all', action='store_true', route_to=None,
                help='describe all snapshots'),
            Arg('-o', '--owner', dest='Owner', metavar='ACCOUNT',
                action='append', default=[],
                help='limit results to snapshots owned by specific accounts'),
            Arg('-r', '--restorable-by', dest='RestorableBy', action='append',
                metavar='ACCOUNT', default=[], help='''limit results to
                snapahots restorable by specific accounts''')]
    FILTERS = [Filter('description', help='snapshot description'),
               Filter('owner-alias', help="snapshot owner's account alias"),
               Filter('owner-id', help="snapshot owner's account ID"),
               Filter('progress', help='snapshot progress, in percentage'),
               Filter('snapshot-id'),
               Filter('start-time', help='snapshot initiation time'),
               Filter('status'),
               Filter('tag-key', help='key of a tag assigned to the snapshot'),
               Filter('tag-value',
                      help='value of a tag assigned to the snapshot'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('volume-id', help='source volume ID'),
               Filter('volume-size', type=int)]
    LIST_TAGS = ['snapshotSet', 'tagSet']

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if self.args.get('all'):
            if self.args.get('Owner'):
                raise ArgumentError('argument -a/--all: not allowed with '
                                    'argument -o/--owner')
            if self.args.get('RestorableBy'):
                raise ArgumentError('argument -a/--all: not allowed with '
                                    'argument -r/--restorable-by')

    def main(self):
        if not any(self.args.get(item) for item in ('all', 'Owner',
                                                    'RestorableBy')):
            # Default to owned snapshots and those with explicit restore perms
            self.params['Owner'] = ['self']
            owned = self.send()
            del self.params['Owner']
            self.params['RestorableBy'] = ['self']
            restorable = self.send()
            del self.params['RestorableBy']
            owned['snapshotSet'] = (owned.get('snapshotSet', []) +
                                    restorable.get('snapshotSet', []))
            return owned
        else:
            return self.send()

    def print_result(self, result):
        for snapshot in result.get('snapshotSet', []):
            self.print_snapshot(snapshot)

########NEW FILE########
__FILENAME__ = describesubnets
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, Filter, GenericTagFilter

from euca2ools.commands.ec2 import EC2Request


class DescribeSubnets(EC2Request):
    DESCRIPTION = 'Show information about one or more VPC subnets'
    ARGS = [Arg('SubnetId', metavar='SUBNET', nargs='*',
                help='limit results to specific subnets')]
    FILTERS = [Filter('availability-zone'),
               Filter('available-ip-address-count',
                      help='the number of unused IP addresses in the subnet'),
               Filter('cidr-block', help="the subnet's CIDR address block"),
               Filter('default-for-az', choices=('true', 'false'),
                      help='''whether this is the default subnet for the
                      availability zone'''),
               Filter('state'),
               Filter('subnet-id'),
               Filter('tag-key', help='key of a tag assigned to the subnet'),
               Filter('tag-value',
                      help='value of a tag assigned to the subnet'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('vpc-id', help="the associated VPC's ID")]
    LIST_TAGS = ['subnetSet', 'tagSet']

    def print_result(self, result):
        for subnet in result.get('subnetSet') or []:
            self.print_subnet(subnet)

########NEW FILE########
__FILENAME__ = describetags
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Filter

from euca2ools.commands.ec2 import EC2Request


class DescribeTags(EC2Request):
    DESCRIPTION = "List tags associated with your account's resources"
    FILTERS = [Filter('key'),
               Filter('resource-id'),
               Filter('resource-type'),
               Filter('value')]
    LIST_TAGS = ['tagSet']

    def print_result(self, result):
        for tag in result.get('tagSet', []):
            print self.tabify(['TAG', tag.get('resourceType'),
                               tag.get('resourceId'), tag.get('key'),
                               tag.get('value')])

########NEW FILE########
__FILENAME__ = describevolumes
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg, Filter, GenericTagFilter


class DescribeVolumes(EC2Request):
    DESCRIPTION = 'Display information about volumes'
    ARGS = [Arg('VolumeId', metavar='VOLUME', nargs='*',
                help='limit results to specific volumes')]
    FILTERS = [Filter('attachment.attach-time', help='attachment start time'),
               Filter('attachment.delete-on-termination', help='''whether the
                      volume will be deleted upon instance termination'''),
               Filter('attachment.device',
                      help='device node exposed to the instance'),
               Filter('attachment.instance-id',
                      help='ID of the instance the volume is attached to'),
               Filter('attachment.status', help='attachment state'),
               Filter('availability-zone'),
               Filter('create-time', help='creation time'),
               Filter('size', type=int, help='size in GiB'),
               Filter('snapshot-id',
                      help='snapshot from which the volume was created'),
               Filter('status'),
               Filter('tag-key', help='key of a tag assigned to the volume'),
               Filter('tag-value',
                      help='value of a tag assigned to the volume'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter(name='volume-id'),
               Filter(name='volume-type')]
    LIST_TAGS = ['volumeSet', 'attachmentSet', 'tagSet']

    def print_result(self, result):
        for volume in result.get('volumeSet'):
            self.print_volume(volume)

########NEW FILE########
__FILENAME__ = describevpcs
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, Filter, GenericTagFilter

from euca2ools.commands.ec2 import EC2Request


class DescribeVpcs(EC2Request):
    DESCRIPTION = 'Show information about VPCs'
    ARGS = [Arg('VpcId', metavar='VPC', nargs='*',
                help='limit results to specific VPCs')]
    FILTERS = [Filter('cidr', help="the VPC's CIDR address block"),
               Filter('dhcp-options-id', help='ID of the set of DHCP options'),
               Filter('isDefault', help='whether the VPC is a default VPC'),
               Filter('state'),
               Filter('tag-key', help='key of a tag assigned to the VPC'),
               Filter('tag-value', help='value of a tag assigned to the VPC'),
               GenericTagFilter('tag:KEY',
                                help='specific tag key/value combination'),
               Filter('vpc-id', help="the VPC's ID")]
    LIST_TAGS = ['tagSet', 'vpcSet']

    def print_result(self, result):
        for vpc in result.get('vpcSet') or []:
            self.print_vpc(vpc)

########NEW FILE########
__FILENAME__ = detachvolume
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class DetachVolume(EC2Request):
    DESCRIPTION = 'Detach a volume from an instance'
    ARGS = [Arg('VolumeId', metavar='VOLUME',
                help='ID of the volume to detach (required)'),
            Arg('-i', '--instance', dest='InstanceId', metavar='INSTANCE',
                help='instance to detach from'),
            Arg('-d', '--device', dest='Device', help='device name'),
            Arg('-f', '--force', dest='Force', action='store_true',
                help='''detach without waiting for the instance.  Data may be
                lost.''')]

    def print_result(self, result):
        self.print_attachment(result)

########NEW FILE########
__FILENAME__ = disassociateaddress
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError


class DisassociateAddress(EC2Request):
    DESCRIPTION = 'Disassociate an elastic IP address from an instance'
    ARGS = [Arg('PublicIp', metavar='ADDRESS', nargs='?', help='''[Non-VPC
                only] elastic IP address to disassociate (required)'''),
            Arg('-a', '--association-id', dest='AssociationId',
                metavar='ASSOC',
                help="[VPC only] address's association ID (required)")]

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if self.args.get('PublicIp'):
            if self.args.get('AssociationId'):
                raise ArgumentError('argument -a/--association-id: not '
                                    'allowed with an IP address')
            elif self.args['PublicIp'].startswith('eipassoc'):
                raise ArgumentError('VPC elastic IP association IDs must be '
                                    'be specified with -a/--association-id')
        elif not self.args.get('AssociationId'):
            raise ArgumentError(
                'argument -a/--association-id or an IP address is required')

    def print_result(self, _):
        target = self.args.get('PublicIp') or self.args.get('AssociationId')
        print self.tabify(('ADDRESS', target))

########NEW FILE########
__FILENAME__ = disassociateroutetable
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class DisassociateRouteTable(EC2Request):
    DESCRIPTION = 'Disassociate a VPC subnet from a route table'
    ARGS = [Arg('AssociationId', metavar='RTBASSOC', help='''ID of the
                routing table association to remove (required)''')]

########NEW FILE########
__FILENAME__ = getconsoleoutput
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg
import sys


CHAR_ESCAPES = {
    u'\x00': u'^@', u'\x0c': u'^L', u'\x17': u'^W',
    u'\x01': u'^A', u'\x0e': u'^N', u'\x18': u'^X',
    u'\x02': u'^B', u'\x0f': u'^O', u'\x19': u'^Y',
    u'\x03': u'^C', u'\x10': u'^P', u'\x1a': u'^Z',
    u'\x04': u'^D', u'\x11': u'^Q', u'\x1b': u'^[',
    u'\x05': u'^E', u'\x12': u'^R', u'\x1c': u'^\\',
    u'\x06': u'^F', u'\x13': u'^S', u'\x1d': u'^]',
    u'\x07': u'^G', u'\x14': u'^T', u'\x1e': u'^^',
    u'\x08': u'^H', u'\x15': u'^U', u'\x1f': u'^_',
    u'\x0b': u'^K', u'\x16': u'^V', u'\x7f': u'^?',
}


class GetConsoleOutput(EC2Request):
    DESCRIPTION = 'Retrieve console output for the specified instance'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', help='''ID of the instance to
                obtain console output from (required)'''),
            Arg('-r', '--raw-console-output', action='store_true',
                route_to=None,
                help='display raw output without escaping control characters')]

    def print_result(self, result):
        print result.get('instanceId', '')
        print result.get('timestamp', '')
        output = base64.b64decode(result.get('output') or '')
        output = output.decode(sys.stdout.encoding or 'utf-8', 'replace')
        output = output.replace(u'\ufffd', u'?')
        if not self.args['raw_console_output']:
            # Escape control characters
            for char, escape in CHAR_ESCAPES.iteritems():
                output = output.replace(char, escape)
        print output

########NEW FILE########
__FILENAME__ = getpassword
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
from euca2ools.commands.ec2.getpassworddata import GetPasswordData
from requestbuilder import Arg
import subprocess


class GetPassword(GetPasswordData):
    NAME = 'GetPasswordData'
    DESCRIPTION = ('Retrieve the administrator password for an instance '
                   'running Windows')
    ARGS = [Arg('-k', '--priv-launch-key', metavar='FILE', required=True,
                route_to=None,
                help='''file containing the private key corresponding to the
                key pair supplied at instance launch time (required)''')]

    def print_result(self, result):
        try:
            pwdata = result['passwordData']
        except AttributeError:
            # The reply didn't contain a passwordData element.
            raise AttributeError('no password data found for this instance')
        cmd = subprocess.Popen(['openssl', 'rsautl', '-decrypt', '-inkey',
                                self.args['priv_launch_key']],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, _ = cmd.communicate(base64.b64decode(pwdata))
        print stdout

########NEW FILE########
__FILENAME__ = getpassworddata
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class GetPasswordData(EC2Request):
    DESCRIPTION = ('Retrieve the encrypted administrator password for an '
                   'instance running Windows.  The encrypted password may be '
                   'decrypted using the private key of the key pair given '
                   'when launching the instance.')
    ARGS = [Arg('InstanceId', metavar='INSTANCE', help='''ID of the instance to
                obtain the initial password for (required)''')]

    def print_result(self, result):
        if result.get('passwordData'):
            print result['passwordData']

########NEW FILE########
__FILENAME__ = importinstance
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division

import argparse
import datetime
import math
import uuid

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.argtypes import filesize
from euca2ools.commands.ec2 import EC2Request
from euca2ools.commands.ec2.mixins import S3AccessMixin
from euca2ools.commands.ec2.resumeimport import ResumeImport
from euca2ools.commands.s3.getobject import GetObject
import euca2ools.util


class ImportInstance(EC2Request, S3AccessMixin, FileTransferProgressBarMixin):
    DESCRIPTION = 'Import an instance into the cloud'
    ARGS = [Arg('source', metavar='FILE', route_to=None,
                help='file containing the disk image to import (required)'),
            Arg('-t', '--instance-type', metavar='INSTANCETYPE', required=True,
                dest='LaunchSpecification.InstanceType',
                help='the type of instance to import to (required)'),
            Arg('-f', '--format', dest='DiskImage.1.Image.Format',
                metavar='FORMAT', required=True, help='''the image's format
                ("vmdk", "raw", or "vhd") (required)'''),
            Arg('-a', '--architecture', metavar='ARCH', required=True,
                dest='LaunchSpecification.Architecture',
                help="the instance's processor architecture (required)"),
            Arg('-p', '--platform', dest='Platform', required=True,
                choices=('Windows', 'Linux'),
                help="the instance's operating system (required)"),
            MutuallyExclusiveArgList(
                Arg('-b', '--bucket', route_to=None,
                    help='the bucket to upload the volume to'),
                Arg('--manifest-url', metavar='URL',
                    dest='DiskImage.1.Image.ImportManifestUrl',
                    help='''a pre-signed URL that points to the import
                    manifest to use'''))
            .required(),
            Arg('--prefix', route_to=None, help='''a prefix to add to the
                names of the volume parts as they are uploaded'''),
            Arg('-x', '--expires', metavar='DAYS', type=int, default=30,
                route_to=None, help='''how long the import manifest should
                remain valid, in days (default: 30 days)'''),
            Arg('--no-upload', action='store_true', route_to=None,
                help='''start the import process, but do not actually upload
                the volume (see euca-resume-import)'''),
            Arg('-d', '--description', dest='Description',
                help='a description for the import task (not the volume)'),
            Arg('-g', '--group', metavar='GROUP',
                dest='LaunchSpecification.GroupName.1',
                help='name of the security group to create the instance in'),
            Arg('-z', '--availability-zone', metavar='ZONE',
                dest='LaunchSpecification.Placement.AvailabilityZone',
                help='the zone in which to create the instance'),
            Arg('-s', '--volume-size', metavar='GiB', type=int,
                dest='DiskImage.1.Volume.Size',
                help='size of the volume to import to, in GiB'),
            Arg('--image-size', dest='DiskImage.1.Image.Bytes',
                metavar='BYTES', type=filesize,
                help='size of the image (required for non-raw files'),
            MutuallyExclusiveArgList(
                Arg('--user-data', metavar='DATA',
                    dest='LaunchSpecification.UserData',
                    help='user data to supply to the instance'),
                Arg('--user-data-file', metavar='FILE', type=open,
                    dest='LaunchSpecification.UserData', help='''file
                    containing user data to supply to the instance''')),
            Arg('--subnet', metavar='SUBNET',
                dest='LaunchSpecification.SubnetId', help='''[VPC only] subnet
                to create the instance's network interface in'''),
            Arg('--private-ip-address', metavar='ADDRESS',
                dest='LaunchSpecification.PrivateIpAddress',
                help='''[VPC only] assign a specific primary private IP address
                to the instance's interface'''),
            Arg('--monitor', action='store_true',
                dest='LaunchSpecification.Monitoring.Enabled',
                help='enable detailed monitoring for the instance'),
            Arg('--instance-initiated-shutdown-behavior',
                dest='LaunchSpecification.InstanceInitiatedShutdownBehavior',
                choices=('stop', 'terminate'), help='''whether to "stop"
                (default) or terminate the instance when it shuts down'''),
            Arg('--key', dest='LaunchSpecification.KeyName',
                help='''[Eucalyptus only] name of the key pair to use when
                running the instance'''),
            # This is not yet implemented
            Arg('--ignore-region-affinity', action='store_true', route_to=None,
                help=argparse.SUPPRESS),
            # This does no validation, but it does prevent taking action
            Arg('--dry-run', action='store_true', route_to=None,
                help=argparse.SUPPRESS),
            # This is not yet implemented
            Arg('--dont-verify-format', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]
    LIST_TAGS = ['volumes']

    def configure(self):
        EC2Request.configure(self)
        self.configure_s3_access()

        if (self.params['DiskImage.1.Image.Format'].upper() in
                ('VMDK', 'VHD', 'RAW')):
            self.params['DiskImage.1.Image.Format'] = \
                self.params['DiskImage.1.Image.Format'].upper()
        if not self.params.get('DiskImage.1.Image.Bytes'):
            if self.params['DiskImage.1.Image.Format'] == 'RAW':
                image_size = euca2ools.util.get_filesize(self.args['source'])
                self.params['DiskImage.1.Image.Bytes'] = image_size
            else:
                raise ArgumentError(
                    'argument --image-size is required for {0} files'
                    .format(self.params['DiskImage.1.Image.Format']))
        if not self.params.get('DiskImage.1.Volume.Size'):
            vol_size = math.ceil(self.params['DiskImage.1.Image.Bytes'] /
                                 2 ** 30)
            self.params['DiskImage.1.Volume.Size'] = int(vol_size)

        if not self.args.get('expires'):
            self.args['expires'] = 30
        if self.args['expires'] < 1:
            raise ArgumentError(
                'argument -x/--expires: value must be positive')

    def main(self):
        if self.args.get('dry_run'):
            return

        if self.args.get('bucket'):
            self.ensure_bucket_exists(self.args['bucket'])

        if not self.args.get('DiskImage.1.Image.ImportManifestUrl'):
            manifest_key = '{0}/{1}.manifest.xml'.format(uuid.uuid4(),
                                                         self.args['source'])
            if self.args.get('prefix'):
                manifest_key = '/'.join((self.args['prefix'], manifest_key))
            getobj = GetObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'],
                source='/'.join((self.args['bucket'], manifest_key)))
            days = self.args.get('expires') or 30
            expiration = datetime.datetime.utcnow() + datetime.timedelta(days)
            get_url = getobj.get_presigned_url(expiration)
            self.log.info('generated manifest GET URL: %s', get_url)
            self.params['DiskImage.1.Image.ImportManifestUrl'] = get_url

        result = self.send()

        # The manifest creation and uploading parts are done by ResumeImport.
        if not self.args.get('no_upload'):
            resume = ResumeImport.from_other(
                self, source=self.args['source'],
                task=result['conversionTask']['conversionTaskId'],
                s3_service=self.args['s3_service'],
                s3_auth=self.args['s3_auth'], expires=self.args['expires'],
                show_progress=self.args.get('show_progress', False))
            resume.main()

        return result

    def print_result(self, result):
        self.print_conversion_task(result['conversionTask'])

########NEW FILE########
__FILENAME__ = importkeypair
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import b64encoded_file_contents
from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class ImportKeyPair(EC2Request):
    DESCRIPTION = 'Import a public RSA key as a new key pair'
    ARGS = [Arg('KeyName', metavar='KEYPAIR',
                help='name for the new key pair (required)'),
            Arg('-f', '--public-key-file', dest='PublicKeyMaterial',
                metavar='FILE', type=b64encoded_file_contents, required=True,
                help='''name of a file containing the public key to import
                (required)''')]

    def print_result(self, result):
        print self.tabify(['KEYPAIR', result.get('keyName'),
                           result.get('keyFingerprint')])

########NEW FILE########
__FILENAME__ = importvolume
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division

import argparse
import datetime
import math
import uuid

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.argtypes import filesize
from euca2ools.commands.ec2 import EC2Request
from euca2ools.commands.ec2.mixins import S3AccessMixin
from euca2ools.commands.ec2.resumeimport import ResumeImport
from euca2ools.commands.s3.getobject import GetObject
import euca2ools.util


class ImportVolume(EC2Request, S3AccessMixin, FileTransferProgressBarMixin):
    DESCRIPTION = 'Import a file to a volume in the cloud'
    ARGS = [Arg('source', metavar='FILE', route_to=None,
                help='file containing the disk image to import (required)'),
            Arg('-f', '--format', dest='Image.Format', metavar='FORMAT',
                required=True, help='''the image's format ("vmdk", "raw", or
                "vhd") (required)'''),
            Arg('-z', '--availability-zone', dest='AvailabilityZone',
                metavar='ZONE', required=True,
                help='the zone in which to create the volume (required)'),
            Arg('-s', '--volume-size', metavar='GiB', dest='Volume.Size',
                type=int, help='size of the volume to import to, in GiB'),
            Arg('--image-size', dest='Image.Bytes', metavar='BYTES',
                type=filesize,
                help='size of the image (required for non-raw files'),
            MutuallyExclusiveArgList(
                Arg('-b', '--bucket', route_to=None,
                    help='the bucket to upload the volume to'),
                Arg('--manifest-url', dest='Image.ImportManifestUrl',
                    metavar='URL', help='''a pre-signed URL that points to
                    the import manifest to use'''))
            .required(),
            Arg('--prefix', route_to=None, help='''a prefix to add to the
                names of the volume parts as they are uploaded'''),
            Arg('-x', '--expires', metavar='DAYS', type=int, default=30,
                route_to=None, help='''how long the import manifest should
                remain valid, in days (default: 30 days)'''),
            Arg('--no-upload', action='store_true', route_to=None,
                help='''start the import process, but do not actually upload
                the volume (see euca-resume-import)'''),
            Arg('-d', '--description', dest='Description',
                help='a description for the import task (not the volume)'),
            # This is not yet implemented
            Arg('--ignore-region-affinity', action='store_true', route_to=None,
                help=argparse.SUPPRESS),
            # This does no validation, but it does prevent taking action
            Arg('--dry-run', action='store_true', route_to=None,
                help=argparse.SUPPRESS),
            # This is not yet implemented
            Arg('--dont-verify-format', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]

    def configure(self):
        EC2Request.configure(self)
        self.configure_s3_access()

        if self.params['Image.Format'].upper() in ('VMDK', 'VHD', 'RAW'):
            self.params['Image.Format'] = self.params['Image.Format'].upper()
        if not self.params.get('Image.Bytes'):
            if self.params['Image.Format'] == 'RAW':
                image_size = euca2ools.util.get_filesize(self.args['source'])
                self.params['Image.Bytes'] = image_size
            else:
                raise ArgumentError(
                    'argument --image-size is required for {0} files'
                    .format(self.params['Image.Format']))
        if not self.params.get('Volume.Size'):
            vol_size = math.ceil(self.params['Image.Bytes'] / 2 ** 30)
            self.params['Volume.Size'] = int(vol_size)

        if not self.args.get('expires'):
            self.args['expires'] = 30
        if self.args['expires'] < 1:
            raise ArgumentError(
                'argument -x/--expires: value must be positive')

    def main(self):
        if self.args.get('dry_run'):
            return

        if self.args.get('bucket'):
            self.ensure_bucket_exists(self.args['bucket'])

        if not self.args.get('Image.ImportManifestUrl'):
            manifest_key = '{0}/{1}.manifest.xml'.format(uuid.uuid4(),
                                                         self.args['source'])
            if self.args.get('prefix'):
                manifest_key = '/'.join((self.args['prefix'], manifest_key))
            getobj = GetObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'],
                source='/'.join((self.args['bucket'], manifest_key)))
            days = self.args.get('expires') or 30
            expiration = datetime.datetime.utcnow() + datetime.timedelta(days)
            get_url = getobj.get_presigned_url(expiration)
            self.log.info('generated manifest GET URL: %s', get_url)
            self.params['Image.ImportManifestUrl'] = get_url

        result = self.send()

        # The manifest creation and uploading parts are done by ResumeImport.
        if not self.args.get('no_upload'):
            resume = ResumeImport.from_other(
                self, source=self.args['source'],
                task=result['conversionTask']['conversionTaskId'],
                s3_service=self.args['s3_service'],
                s3_auth=self.args['s3_auth'], expires=self.args['expires'],
                show_progress=self.args.get('show_progress', False))
            resume.main()

        return result

    def print_result(self, result):
        self.print_conversion_task(result['conversionTask'])

########NEW FILE########
__FILENAME__ = mixins
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError, ServerError

from euca2ools.commands.s3 import S3, S3Request
from euca2ools.commands.s3.checkbucket import CheckBucket
from euca2ools.commands.s3.createbucket import CreateBucket


class S3AccessMixin(object):
    ARGS = [Arg('--s3-url', metavar='URL', route_to=None,
                help='object storage service endpoint URL'),
            Arg('-o', '--owner-akid', metavar='KEY_ID', route_to=None,
                help='''access key to use for the object storage service
                (default: same as that for the compute service)'''),
            Arg('-w', '--owner-sak', metavar='KEY', route_to=None,
                help='''secret key to use for the object storage service
                (default: same as that for the compute service)'''),
            # Pass-throughs
            Arg('--s3-service', route_to=None, help=argparse.SUPPRESS),
            Arg('--s3-auth', route_to=None, help=argparse.SUPPRESS)]

    def configure_s3_access(self):
        if self.args.get('owner_akid') and not self.args.get('owner_sak'):
            raise ArgumentError('argument -o/--owner-akid also requires '
                                '-w/--owner-sak')
        if self.args.get('owner_sak') and not self.args.get('owner_akid'):
            raise ArgumentError('argument -w/--owner-sak also requires '
                                '-o/--owner-akid')
        if not self.args.get('s3_auth'):
            if self.args.get('owner_sak') and self.args.get('owner_akid'):
                self.args['s3_auth'] = S3Request.AUTH_CLASS.from_other(
                    self.auth, key_id=self.args['owner_akid'],
                    secret_key=self.args['owner_sak'])
            else:
                self.args['s3_auth'] = S3Request.AUTH_CLASS.from_other(
                    self.auth)
        if not self.args.get('s3_service'):
            self.args['s3_service'] = S3.from_other(
                self.service, url=self.args.get('s3_url'))

    def ensure_bucket_exists(self, bucket):
        try:
            # Ensure the bucket exists
            req = CheckBucket.from_other(self, service=self.args['s3_service'],
                                         auth=self.args['s3_auth'],
                                         bucket=bucket)
            req.main()
        except ServerError as err:
            if err.status_code == 404:
                # No such bucket
                self.log.info("creating bucket: '%s'", bucket)
                req = CreateBucket.from_other(req, bucket=bucket)
                req.main()
            else:
                raise

########NEW FILE########
__FILENAME__ = modifyimageattribute
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request


class ModifyImageAttribute(EC2Request):
    DESCRIPTION = 'Modify an attribute of an image'
    ARGS = [Arg('ImageId', metavar='IMAGE', help='image to modify'),
            MutuallyExclusiveArgList(
                Arg('--description', dest='Description.Value', metavar='DESC',
                    help="change the image's description"),
                Arg('-p', '--product-code', dest='ProductCode', metavar='CODE',
                    action='append', help='''product code to add to the given
                    instance-store image'''),
                Arg('-l', '--launch-permission', action='store_true',
                    route_to=None,
                    help='grant/revoke launch permissions with -a/-r'))
            .required(),
            Arg('-a', '--add', metavar='ENTITY', action='append', default=[],
                route_to=None, help='''account to grant launch permission, or
                "all" for all accounts'''),
            Arg('-r', '--remove', metavar='ENTITY', action='append',
                default=[], route_to=None, help='''account to remove launch
                permission from, or "all" for all accounts''')]

    # noinspection PyExceptionInherit
    def preprocess(self):
        if self.args.get('launch_permission'):
            lperm = {}
            for entity in self.args.get('add', []):
                lperm.setdefault('Add', [])
                if entity == 'all':
                    lperm['Add'].append({'Group':  entity})
                else:
                    lperm['Add'].append({'UserId': entity})
            for entity in self.args.get('remove', []):
                lperm.setdefault('Remove', [])
                if entity == 'all':
                    lperm['Remove'].append({'Group':  entity})
                else:
                    lperm['Remove'].append({'UserId': entity})
            if not lperm:
                raise ArgumentError('at least one entity must be specified '
                                    'with -a/--add or -r/--remove')
            self.params['LaunchPermission'] = lperm
        else:
            if self.args.get('add'):
                raise ArgumentError('argument -a/--add may only be used '
                                    'with -l/--launch-permission')
            if self.args.get('remove'):
                raise ArgumentError('argument -r/--remove may only be used '
                                    'with -l/--launch-permission')

    def print_result(self, _):
        if self.args.get('Description.Value'):
            print self.tabify(('description', self.args['ImageId'],
                               None, self.args['Description.Value']))
        if self.args.get('ProductCode'):
            for code in self.args['ProductCode']:
                print self.tabify(('productcodes', self.args['ImageId'],
                                   'productCode', code))
        if self.args.get('launch_permission'):
            for add in self.params['LaunchPermission'].get('Add', []):
                for (entity_type, entity_name) in add.items():
                    print self.tabify(('launchPermission',
                                       self.args['ImageId'], 'ADD',
                                       entity_type, entity_name))
            for add in self.params['LaunchPermission'].get('Remove', []):
                for (entity_type, entity_name) in add.items():
                    print self.tabify(('launchPermission',
                                       self.args['ImageId'], 'REMOVE',
                                       entity_type, entity_name))

########NEW FILE########
__FILENAME__ = modifyinstanceattribute
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.argtypes import b64encoded_file_contents
from euca2ools.commands.ec2 import EC2Request


def _min_ec2_block_device_mapping(map_as_str):
    try:
        device, mapping = map_as_str.split('=')
    except ValueError:
        raise argparse.ArgumentTypeError(
            'block device mapping "{0}" must have form DEVICE=::true or '
            'DEVICE=::false'.format(map_as_str))
    mapping_bits = mapping.split(':')
    if (len(mapping_bits) != 3 or mapping_bits[0] or mapping_bits[1] or
            mapping_bits[2] not in ('true', 'false')):
        raise argparse.ArgumentTypeError(
            'block device mapping "{0}" must be either {1}=::true or '
            '{1}=::false'.format(map_as_str, device))
    return {'DeviceName': device,
            'Ebs': {'DeleteOnTermination': mapping_bits[2]}}


class ModifyInstanceAttribute(EC2Request):
    DESCRIPTION = 'Modify an attribute of an instance'
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to modify (required)'),
            MutuallyExclusiveArgList(
                Arg('-b', '--block-device-mapping', dest='BlockDeviceMapping',
                    action='append', metavar='DEVICE=::(true|false)',
                    type=_min_ec2_block_device_mapping, default=[],
                    help='''change whether a volume attached to the instance
                    will be deleted upon the instance's termination'''),
                Arg('--disable-api-termination', choices=('true', 'false'),
                    dest='DisableApiTermination.Value', help='''change whether
                    or not the instance may be terminated'''),
                Arg('--ebs-optimized', dest='EbsOptimized',
                    choices=('true', 'false'), help='''change whether or not
                    the instance should be optimized for EBS I/O'''),
                Arg('-g', '--group-id', dest='GroupId', metavar='GROUP',
                    action='append', default=[], help='''[VPC only] Change the
                    security group(s) the instance is in'''),
                Arg('--instance-initiated-shutdown-behavior',
                    dest='InstanceInitiatedShutdownBehavior.Value',
                    choices=('stop', 'terminate'), help='''whether to stop or
                    terminate the EBS instance when it shuts down
                    (instance-store instances are always terminated)'''),
                Arg('-t', '--instance-type', metavar='INSTANCETYPE',
                    help="change the instance's type"),
                Arg('--kernel', dest='Kernel.Value', metavar='IMAGE',
                    help="change the instance's kernel image"),
                Arg('--ramdisk', dest='Ramdisk.Value', metavar='IMAGE',
                    help="change the instance's ramdisk image"),
                Arg('--source-dest-check', dest='SourceDestCheck.Value',
                    choices=('true', 'false'), help='''change whether
                    source/destination address checking is enabled'''),
                Arg('--sriov', dest='SriovNetSupport.Value', metavar='simple',
                    choices=('simple',), help='''enable enhanced networking for
                    the instance and its descendants'''),
                Arg('--user-data', dest='UserData.Value', metavar='DATA',
                    help='''change the instance's user data (must be
                    base64-encoded)'''),
                Arg('--user-data-file', dest='UserData.Value', metavar='FILE',
                    type=b64encoded_file_contents, help='''change the
                    instance's user data to the contents of a file'''))
            .required()]

########NEW FILE########
__FILENAME__ = modifyinstancetypeattribute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import TabifyingMixin

from euca2ools.commands.ec2 import EC2Request


class ModifyInstanceTypeAttribute(EC2Request, TabifyingMixin):
    DESCRIPTION = '[Eucalyptus cloud admin only] Modify an instance type'
    ARGS = [Arg('Name', metavar='INSTANCETYPE',
                help='name of the instance type to modify (required)'),
            Arg('-c', '--cpus', dest='Cpu', metavar='COUNT', type=int,
                help='number of virtual CPUs to allocate to each instance'),
            Arg('-d', '--disk', dest='Disk', metavar='GiB', type=int,
                help='amount of instance storage to allow each instance'),
            Arg('-m', '--memory', dest='Memory', metavar='MiB', type=int,
                help='amount of RAM to allocate to each instance'),
            Arg('--reset', dest='Reset', action='store_true',
                help='reset the instance type to its default configuration')]

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if (self.args.get('Reset') and
            any(self.args.get(attr) is not None for attr in ('Cpu', 'Disk',
                                                             'Memory'))):
            # Basically, reset is mutually exclusive with everything else.
            raise ArgumentError('argument --reset may not be used with '
                                'instance type attributes')

    def print_result(self, result):
        newtype = result.get('instanceType', {})
        print self.tabify(('INSTANCETYPE', newtype.get('name'),
                           newtype.get('cpu'), newtype.get('memory'),
                           newtype.get('disk')))

########NEW FILE########
__FILENAME__ = modifynetworkaclentry
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import socket

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request, parse_ports


class _ModifyNetworkAclEntry(EC2Request):
    DESCRIPTION = ('Modify a network ACL entry\n\nThis is not an '
                   'actual EC2 request -- see euca-create-network-acl-'
                   'entry(1) or euca-replace-network-acl-entry(1) for '
                   'something usable.')
    ARGS = [Arg('NetworkAclId', metavar='NACL',
                help='ID of the network ACL to add the entry to (required)'),
            Arg('-n', '--rule-number', dest='RuleNumber', metavar='INT',
                required=True, type=int,
                help='rule number for the new entry (required)'),
            MutuallyExclusiveArgList(
                Arg('--allow', dest='RuleAction', action='store_const',
                    const='allow',
                    help='make the new entry allow the traffic it matches'),
                Arg('--deny', dest='RuleAction', action='store_const',
                    const='deny',
                    help='make the new entry block the traffic it matches'))
            .required(),
            Arg('-r', '--cidr', dest='CidrBlock', metavar='CIDR',
                required=True,
                help='CIDR address range the entry should affect (required)'),
            Arg('-P', '--protocol', dest='Protocol', default='-1',
                help='protocol the entry should apply to (default: all)'),
            Arg('--egress', dest='Egress', action='store_true',
                help='''make the entry affect outgoing (egress) network
                traffic (default: affect incoming (ingress) traffic)'''),
            Arg('-p', '--port-range', dest='port_range', metavar='RANGE',
                route_to=None, help='''range of ports (specified as "from-to")
                or a single port number (required for tcp and udp)'''),
            Arg('-t', '--icmp-type-code', dest='icmp_type_code',
                metavar='TYPE:CODE', route_to=None, help='''ICMP type and
                code (specified as "type:code") (required for icmp)''')]

    def process_cli_args(self):
        self.process_port_cli_args()

    def configure(self):
        EC2Request.configure(self)
        if not self.params.get('Egress'):
            self.params['Egress'] = False
        proto = self.args.get('Protocol') or -1
        try:
            self.params['Protocol'] = int(proto)
        except ValueError:
            if proto.lower() == 'all':
                self.params['Protocol'] = -1
            else:
                try:
                    self.params['Protocol'] = socket.getprotobyname(proto)
                except socket.error:
                    raise ArgumentError('argument -n/--rule-number: unknown '
                                        'protocol "{0}"'.format(proto))
        from_port, to_port = parse_ports(proto, self.args.get('port_range'),
                                         self.args.get('icmp_type_code'))
        if self.params['Protocol'] == 1:  # ICMP
            self.params['Icmp.Type'] = from_port
            self.params['Icmp.Code'] = to_port
        else:
            self.params['PortRange.From'] = from_port
            self.params['PortRange.To'] = to_port

    def print_result(self, _):
        if self.args.get('Egress'):
            direction = 'egress'
        else:
            direction = 'ingress'
        protocol = self.params['Protocol']
        port_map = {-1: 'all', 1: 'icmp', 6: 'tcp', 17: 'udp', 132: 'sctp'}
        try:
            protocol = port_map.get(int(protocol), int(protocol))
        except ValueError:
            pass

        print self.tabify((
            'ENTRY', direction, self.params.get('RuleNumber'),
            self.params.get('RuleAction'), self.params.get('CidrBlock'),
            protocol,
            self.params.get('Icmp.Type') or self.params.get('PortRange.From'),
            self.params.get('Icmp.Code') or self.params.get('PortRange.To')))


class CreateNetworkAclEntry(_ModifyNetworkAclEntry):
    DESCRIPTION = 'Create a new entry in a VPC network ACL'


class ReplaceNetworkAclEntry(_ModifyNetworkAclEntry):
    DESCRIPTION = 'Replace an entry in a VPC network ACL'

########NEW FILE########
__FILENAME__ = modifysecuritygrouprule
# Copyright 2012-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.ec2 import EC2Request, parse_ports


class _ModifySecurityGroupRule(EC2Request):
    """
    The basis for security group-editing commands
    """

    ARGS = [Arg('group', metavar='GROUP', route_to=None,
                help='name or ID of the security group to modify (required)'),
            Arg('--egress', action='store_true', route_to=None,
                help='''[VPC only] manage an egress rule, which controls
                traffic leaving the group'''),
            Arg('-P', '--protocol', dest='IpPermissions.1.IpProtocol',
                choices=['tcp', 'udp', 'icmp', '6', '17', '1'], default='tcp',
                help='protocol to affect (default: tcp)'),
            Arg('-p', '--port-range', dest='port_range', metavar='RANGE',
                route_to=None, help='''range of ports (specified as "from-to")
                or a single port number (required for tcp and udp)'''),
            Arg('-t', '--icmp-type-code', dest='icmp_type_code',
                metavar='TYPE:CODE', route_to=None, help='''ICMP type and
                code (specified as "type:code") (required for icmp)'''),
            MutuallyExclusiveArgList(
                Arg('-s', '--cidr', metavar='CIDR',
                    dest='IpPermissions.1.IpRanges.1.CidrIp',
                    help='''IP range (default: 0.0.0.0/0)'''),
                # ^ default is added by main()
                Arg('-o', dest='target_group', metavar='GROUP', route_to=None,
                    help='''[Non-VPC only] name of a security group with which
                    to affect network communication''')),
            Arg('-u', metavar='ACCOUNT',
                dest='IpPermissions.1.Groups.1.UserId',
                help='''ID of the account that owns the security group
                specified with -o''')]

    def process_cli_args(self):
        self.process_port_cli_args()

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)

        if (self.args['group'].startswith('sg-') and
                len(self.args['group']) == 11):
            # The check could probably be a little better, but meh.  Fix if
            # needed.
            self.params['GroupId'] = self.args['group']
        else:
            if self.args['egress']:
                raise ArgumentError('egress rules must use group IDs, not '
                                    'names')
            self.params['GroupName'] = self.args['group']

        target_group = self.args.get('target_group')
        if (target_group is not None and target_group.startswith('sg-') and
                len(target_group) == 11):
            # Same note as above
            self.params['IpPermissions.1.Groups.1.GroupId'] = target_group
        else:
            if self.args['egress']:
                raise ArgumentError('argument -o: egress rules must use group '
                                    'IDs, not names')
            self.params['IpPermissions.1.Groups.1.GroupName'] = target_group

        from_port, to_port = parse_ports(
            self.args.get('IpPermissions.1.IpProtocol'),
            self.args.get('port_range'), self.args.get('icmp_type_code'))
        self.params['IpPermissions.1.FromPort'] = from_port
        self.params['IpPermissions.1.ToPort'] = to_port

        if (not self.args.get('IpPermissions.1.IpRanges.1.GroupName') and
                not self.args.get('IpPermissions.1.IpRanges.1.CidrIp')):
            # Default rule target is the entire Internet
            self.params['IpPermissions.1.IpRanges.1.CidrIp'] = '0.0.0.0/0'
        if (self.params.get('IpPermissions.1.Groups.1.GroupName') and
                not self.args.get('IpPermissions.1.Groups.1.UserId')):
            raise ArgumentError('argument -u is required when -o names a '
                                'security group by name')

    def print_result(self, _):
        print self.tabify(['GROUP', self.args.get('group')])
        perm_str = ['PERMISSION', self.args.get('group'), 'ALLOWS',
                    self.params.get('IpPermissions.1.IpProtocol'),
                    self.params.get('IpPermissions.1.FromPort'),
                    self.params.get('IpPermissions.1.ToPort')]
        if self.params.get('IpPermissions.1.Groups.1.UserId'):
            perm_str.append('USER')
            perm_str.append(self.params.get('IpPermissions.1.Groups.1.UserId'))
        if self.params.get('IpPermissions.1.Groups.1.GroupId'):
            perm_str.append('GRPID')
            perm_str.append(self.params.get(
                'IpPermissions.1.Groups.1.GroupId'))
        elif self.params.get('IpPermissions.1.Groups.1.GroupName'):
            perm_str.append('GRPNAME')
            perm_str.append(self.params.get(
                'IpPermissions.1.Groups.1.GroupName'))
        if self.params.get('IpPermissions.1.IpRanges.1.CidrIp'):
            perm_str.extend(['FROM', 'CIDR'])
            perm_str.append(self.params.get(
                'IpPermissions.1.IpRanges.1.CidrIp'))
        print self.tabify(perm_str)


class AuthorizeSecurityGroupRule(_ModifySecurityGroupRule):
    DESCRIPTION = 'Add a rule to a security group that allows traffic to pass'

    @property
    def action(self):
        if self.args['egress']:
            return 'AuthorizeSecurityGroupEgress'
        else:
            return 'AuthorizeSecurityGroupIngress'


class RevokeSecurityGroupRule(_ModifySecurityGroupRule):
    DESCRIPTION = 'Remove a rule from a security group'

    @property
    def action(self):
        if self.args['egress']:
            return 'RevokeSecurityGroupEgress'
        else:
            return 'RevokeSecurityGroupIngress'

########NEW FILE########
__FILENAME__ = modifysnapshotattribute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError


class ModifySnapshotAttribute(EC2Request):
    DESCRIPTION = 'Modify an attribute of a snapshot'
    ARGS = [Arg('SnapshotId', metavar='SNAPSHOT',
                help='ID of the snapshot to modify'),
            Arg('-c', '--create-volume-permission', action='store_true',
                required=True, route_to=None,
                help='grant/revoke volume creation permission with -a/-r'),
            Arg('-a', '--add', metavar='ENTITY', action='append', default=[],
                route_to=None,
                help='account to grant permission, or "all" for all accounts'),
            Arg('-r', '--remove', metavar='ENTITY', action='append',
                default=[], route_to=None, help='''account to remove permission
                from, or "all" for all accounts''')]

    # noinspection PyExceptionInherit
    def preprocess(self):
        if self.args.get('create_volume_permission'):
            cvperm = {}
            for entity in self.args.get('add', []):
                cvperm.setdefault('Add', [])
                if entity == 'all':
                    cvperm['Add'].append({'Group':  entity})
                else:
                    cvperm['Add'].append({'UserId': entity})
            for entity in self.args.get('remove', []):
                cvperm.setdefault('Remove', [])
                if entity == 'all':
                    cvperm['Remove'].append({'Group':  entity})
                else:
                    cvperm['Remove'].append({'UserId': entity})
            if not cvperm:
                raise ArgumentError('at least one entity must be specified '
                                    'with -a/--add or -r/--remove')
            self.params['CreateVolumePermission'] = cvperm
        else:
            if self.args.get('add'):
                raise ArgumentError('argument -a/--add may only be used '
                                    'with -c/--create-volume-permission')
            if self.args.get('remove'):
                raise ArgumentError('argument -r/--remove may only be used '
                                    'with -c/--create-volume-permission')

    def print_result(self, _):
        if self.args.get('create_volume_permission'):
            for add in self.params['CreateVolumePermission'].get('Add', []):
                for (entity_type, entity_name) in add.items():
                    print self.tabify(('createVolumePermission',
                                       self.args['SnapshotId'], 'ADD',
                                       entity_type, entity_name))
            for add in self.params['CreateVolumePermission'].get('Remove', []):
                for (entity_type, entity_name) in add.items():
                    print self.tabify(('createVolumePermission',
                                       self.args['SnapshotId'], 'REMOVE',
                                       entity_type, entity_name))

########NEW FILE########
__FILENAME__ = monitorinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class MonitorInstances(EC2Request):
    DESCRIPTION = 'Enable monitoring for one or more instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+', help='''ID(s) of
                the instance(s) to begin monitoring (at least 1 required)''')]
    LIST_TAGS = ['instancesSet']

    def print_result(self, result):
        for instance in result.get('instancesSet', []):
            mon_state = 'monitoring-{0}'.format(
                instance.get('monitoring', {}).get('state'))
            print self.tabify((instance.get('instanceId'), mon_state))

########NEW FILE########
__FILENAME__ = rebootinstances
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class RebootInstances(EC2Request):
    DESCRIPTION = 'Reboot one or more instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+', help='''ID(s) of
                the instance(s) to reboot (at least 1 required)''')]

########NEW FILE########
__FILENAME__ = registerimage
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.argtypes import ec2_block_device_mapping
from euca2ools.commands.ec2 import EC2Request


class RegisterImage(EC2Request):
    DESCRIPTION = 'Register a new image'
    ARGS = [Arg('ImageLocation', metavar='MANIFEST', nargs='?',
                help='''location of the image manifest in S3 storage
                (required for instance-store images)'''),
            Arg('-n', '--name', dest='Name', required=True,
                help='name of the new image (required)'),
            Arg('-d', '--description', dest='Description',
                help='description of the new image'),
            Arg('-a', '--architecture', dest='Architecture',
                choices=('i386', 'x86_64', 'armhf'),
                help='CPU architecture of the new image'),
            Arg('--kernel', dest='KernelId', metavar='KERNEL',
                help='ID of the kernel to associate with the new image'),
            Arg('--ramdisk', dest='RamdiskId', metavar='RAMDISK',
                help='ID of the ramdisk to associate with the new image'),
            Arg('--root-device-name', dest='RootDeviceName', metavar='DEVICE',
                help='root device name (default: /dev/sda1)'),
            # ^ default is added by main()
            Arg('-s', '--snapshot', route_to=None,
                help='snapshot to use for the root device'),
            Arg('-b', '--block-device-mapping', metavar='DEVICE=MAPPED',
                dest='BlockDeviceMapping', action='append',
                type=ec2_block_device_mapping, default=[],
                help='''define a block device mapping for the image, in the
                form DEVICE=MAPPED, where "MAPPED" is "none", "ephemeral(0-3)",
                or
                "[SNAP-ID]:[GiB]:[true|false]:[standard|VOLTYPE[:IOPS]]"'''),
            Arg('--virtualization-type', dest='VirtualizationType',
                choices=('paravirtual', 'hvm'),
                help='[Privileged] virtualization type for the new image'),
            Arg('--platform', dest='Platform', metavar='windows',
                choices=('windows',),
                help="[Privileged] the new image's platform (windows)")]

    # noinspection PyExceptionInherit
    def preprocess(self):
        if self.args.get('ImageLocation'):
            # instance-store image
            if self.args.get('RootDeviceName'):
                raise ArgumentError('argument --root-device-name: not allowed '
                                    'with argument MANIFEST')
            if self.args.get('snapshot'):
                raise ArgumentError('argument --snapshot: not allowed with '
                                    'argument MANIFEST')
        else:
            # Try for an EBS image
            if not self.params.get('RootDeviceName'):
                self.params['RootDeviceName'] = '/dev/sda1'
            snapshot = self.args.get('snapshot')
            # Look for a mapping for the root device
            for mapping in self.args['BlockDeviceMapping']:
                if mapping.get('DeviceName') == self.params['RootDeviceName']:
                    if (snapshot != mapping.get('Ebs', {}).get('SnapshotId')
                            and snapshot):
                        # The mapping's snapshot differs or doesn't exist
                        raise ArgumentError(
                            'snapshot ID supplied with --snapshot conflicts '
                            'with block device mapping for root device {0}'
                            .format(mapping['DeviceName']))
                    else:
                        # No need to apply --snapshot since the mapping is
                        # already there
                        break
            else:
                if snapshot:
                    self.params['BlockDeviceMapping'].append(
                        {'DeviceName': self.params['RootDeviceName'],
                         'Ebs': {'SnapshotId': snapshot}})
                else:
                    raise ArgumentError(
                        'either a manifest location or a root device snapshot '
                        'mapping must be specified')

    def print_result(self, result):
        print self.tabify(('IMAGE', result.get('imageId')))

########NEW FILE########
__FILENAME__ = releaseaddress
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError


class ReleaseAddress(EC2Request):
    DESCRIPTION = 'Release an elastic IP address'
    ARGS = [Arg('PublicIp', metavar='ADDRESS', nargs='?',
                help='[Non-VPC only] address to release (required)'),
            Arg('-a', '--allocation-id', dest='AllocationId', metavar='ALLOC',
                help='''[VPC only] allocation ID for the address to release
                (required)''')]

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if (self.args.get('PublicIp') is not None and
                self.args.get('AllocationId') is not None):
            # Can't be both EC2 and VPC
            raise ArgumentError(
                'argument -a/--allocation-id: not allowed with an IP address')
        if (self.args.get('PublicIp') is None and
                self.args.get('AllocationId') is None):
            # ...but we still have to be one of them
            raise ArgumentError(
                'argument -a/--allocation-id or an IP address is required')

    def print_result(self, _):
        print self.tabify(('ADDRESS', self.args.get('PublicIp'),
                           self.args.get('AllocationId')))

########NEW FILE########
__FILENAME__ = replacenetworkaclassociation
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class ReplaceNetworkAclAssociation(EC2Request):
    DESCRIPTION = 'Associate a new VPC network ACL with a subnet'
    ARGS = [Arg('AssociationId', metavar='ACLASSOC', help='''ID of the
                network ACL association to replace (required)'''),
            Arg('-a', '--network-acl', dest='NetworkAclId', metavar='ACL',
                required=True, help='''ID of the network ACL to
                associate with the subnet (required)''')]

    def print_result(self, result):
        print self.tabify(('ASSOCIATION', result.get('newAssociationId'),
                           self.args['NetworkAclId']))

########NEW FILE########
__FILENAME__ = replaceroute
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.ec2 import EC2Request


class ReplaceRoute(EC2Request):
    DESCRIPTION = 'Replace a route in a VPC route table'
    API_VERSION = '2014-02-01'
    ARGS = [Arg('RouteTableId', metavar='RTABLE',
                help='ID of the route table to affect (required)'),
            Arg('-r', '--cidr', dest='DestinationCidrBlock', metavar='CIDR',
                required=True,
                help='destination prefix for route lookup'),
            MutuallyExclusiveArgList(
                Arg('-g', '--gateway-id', dest='GatewayId', metavar='GATEWAY',
                    help='ID of an Internet gateway to target'),
                Arg('-i', '--instance', dest='InstanceId', metavar='INSTANCE',
                    help='ID of a NAT instance to target'),
                Arg('-n', '--network-interface', dest='NetworkInterfaceId',
                    help='ID of a network interface to target'),
                Arg('-p', '--vpc-peering-connection', metavar='PEERCON',
                    dest='VpcPeeringConnectionId',
                    help='ID of a VPC peering connection to target'))
            .required()]

    def print_result(self, _):
        target = (self.args.get('GatewayId') or self.args.get('InstanceId') or
                  self.args.get('NetworkInterfaceId') or
                  self.args.get('VpcPeeringConnectionId'))
        print self.tabify(('ROUTE', target, self.args['DestinationCidrBlock']))

########NEW FILE########
__FILENAME__ = replaceroutetableassociation
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.ec2 import EC2Request


class ReplaceRouteTableAssociation(EC2Request):
    DESCRIPTION = 'Change the route table associated with a VPC subnet'
    ARGS = [Arg('AssociationId', metavar='RTBASSOC', help='''ID of the
                route table association to replace (required)'''),
            Arg('-r', dest='RouteTableId', metavar='RTABLE', required=True,
                help='route table to associate with the subnet (required)')]

    def print_result(self, result):
        print self.tabify(('ASSOCIATION', result.get('newAssociationId'),
                           self.args['RouteTableId']))

########NEW FILE########
__FILENAME__ = resetimageattribute
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from euca2ools.commands.ec2 import EC2Request


class ResetImageAttribute(EC2Request):
    DESCRIPTION = 'Reset an attribute of an image to its default value'
    ARGS = [Arg('ImageId', metavar='IMAGE',
            help='ID of the image whose attribute should be reset (required)'),
            Arg('-l', '--launch-permission', dest='Attribute',
                action='store_const', const='launchPermission', required=True,
                help='reset launch permissions')]

    def print_result(self, _):
        print self.tabify(('launchPermission', self.args['ImageId'], 'RESET'))

########NEW FILE########
__FILENAME__ = resetinstanceattribute
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.ec2 import EC2Request


class ResetInstanceAttribute(EC2Request):
    DESCRIPTION = 'Reset an attribute of an instance to its default value'
    ARGS = [Arg('InstanceId', metavar='INSTANCE',
                help='ID of the instance to modify (required)'),
            MutuallyExclusiveArgList(
                Arg('--kernel', dest='Attribute', action='store_const',
                    const='kernel',
                    help="reset the instance's kernel image ID"),
                Arg('--ramdisk', dest='Attribute', action='store_const',
                    const='ramdisk',
                    help="reset the instance's ramdisk image ID"),
                Arg('--source-dest-check', dest='Attribute',
                    action='store_const', const='sourceDestCheck',
                    help="reset the instance's SourceDestCheck to true"))
            .required()]

########NEW FILE########
__FILENAME__ = resumeimport
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import datetime
import os.path
import tempfile

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError, ServerError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.ec2 import EC2Request
from euca2ools.commands.ec2.describeconversiontasks import \
    DescribeConversionTasks
from euca2ools.commands.ec2.mixins import S3AccessMixin
from euca2ools.commands.ec2.structures import ImportManifest, ImportImagePart
from euca2ools.commands.s3.deleteobject import DeleteObject
from euca2ools.commands.s3.headobject import HeadObject
from euca2ools.commands.s3.getobject import GetObject
from euca2ools.commands.s3.putobject import PutObject
from euca2ools.exceptions import AWSError
import euca2ools.util


class ResumeImport(EC2Request, S3AccessMixin, FileTransferProgressBarMixin):
    DESCRIPTION = 'Perform the upload step of an import task'
    ARGS = [Arg('source', metavar='FILE',
                help='file containing the disk image to import (required)'),
            Arg('-t', '--task', required=True,
                help='the ID of the import task to resume (required)'),
            Arg('-x', '--expires', metavar='DAYS', type=int, default=30,
                help='''how long the import manifest should remain valid, in
                days (default: 30 days)'''),
            # This is documented, but not implemented in ec2-resume-import
            Arg('--part-size', metavar='MiB', type=int, default=10,
                help=argparse.SUPPRESS),
            # These are not implemented
            Arg('--user-threads', type=int, help=argparse.SUPPRESS),
            Arg('--dont-verify-format', action='store_true',
                help=argparse.SUPPRESS),
            # This does no validation, but it does prevent taking action
            Arg('--dry-run', action='store_true', help=argparse.SUPPRESS)]

    def configure(self):
        EC2Request.configure(self)
        self.configure_s3_access()
        if not self.args.get('expires'):
            self.args['expires'] = 30
        if self.args['expires'] < 1:
            raise ArgumentError(
                'argument -x/--expires: value must be positive')

    def main(self):
        if self.args.get('dry_run'):
            return

        if self.args.get('show_progress', False):
            print 'Uploading image for task', self.args['task']

        # Manifest
        desc_conv = DescribeConversionTasks.from_other(
            self, ConversionTaskId=[self.args['task']])
        task = desc_conv.main()['conversionTasks'][0]
        assert task['conversionTaskId'] == self.args['task']

        if task.get('importVolume'):
            vol_container = task['importVolume']
        else:
            vol_container = task['importInstance']['volumes'][0]
        manifest = self.__get_or_create_manifest(vol_container)

        actual_size = euca2ools.util.get_filesize(self.args['source'])
        if actual_size != manifest.image_size:
            raise ArgumentError(
                'file "{0}" is not the same size as the file the import '
                'started with (expected: {1}, actual: {2})'
                .format(self.args['source'], manifest.image_size, actual_size))

        # Now we have a manifest; check to see what parts are already uploaded
        _, bucket, _ = self.args['s3_service'].resolve_url_to_location(
            vol_container['image']['importManifestUrl'])
        pbar_label_template = euca2ools.util.build_progressbar_label_template(
            [os.path.basename(part.key) for part in manifest.image_parts])
        for part in manifest.image_parts:
            part_s3path = '/'.join((bucket, part.key))
            head_req = HeadObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'], path=part_s3path)
            try:
                head_req.main()
            except AWSError as err:
                if err.status_code == 404:
                    self.__upload_part(part, part_s3path, pbar_label_template)
                else:
                    raise
            # If it is already there we skip it

    def __get_or_create_manifest(self, vol_container):
        _, bucket, key = self.args['s3_service'].resolve_url_to_location(
            vol_container['image']['importManifestUrl'])
        manifest_s3path = '/'.join((bucket, key))
        try:
            with tempfile.SpooledTemporaryFile(max_size=1024000) as \
                    manifest_destfile:
                get_req = GetObject.from_other(
                    self, service=self.args['s3_service'],
                    auth=self.args['s3_auth'], source=manifest_s3path,
                    dest=manifest_destfile, show_progress=False)
                get_req.main()
                self.log.info('using existing import manifest from the server')
                manifest_destfile.seek(0)
                manifest = ImportManifest.read_from_fileobj(
                    manifest_destfile)
        except ServerError as err:
            if err.status_code == 404:
                self.log.info('creating new import manifest')
                manifest = self.__generate_manifest(vol_container)
                tempdir = tempfile.mkdtemp()
                manifest_filename = os.path.join(tempdir,
                                                 os.path.basename(key))
                with open(manifest_filename, 'w') as manifest_file:
                    manifest.dump_to_fileobj(manifest_file, pretty_print=True)
                put_req = PutObject.from_other(
                    get_req, source=manifest_filename, dest=manifest_s3path,
                    show_progress=False)
                put_req.main()
                os.remove(manifest_filename)
                os.rmdir(tempdir)
            else:
                raise
        return manifest

    def __generate_manifest(self, vol_container):
        days = self.args.get('expires') or 30
        expiration = datetime.datetime.utcnow() + datetime.timedelta(days)
        _, bucket, key = self.args['s3_service'].resolve_url_to_location(
            vol_container['image']['importManifestUrl'])
        key_prefix = key.rsplit('/', 1)[0]
        manifest = ImportManifest(loglevel=self.log.level)
        manifest.file_format = vol_container['image']['format']
        delete_req = DeleteObject.from_other(
            self, service=self.args['s3_service'], auth=self.args['s3_auth'],
            path='/'.join((bucket, key)))
        manifest.self_destruct_url = delete_req.get_presigned_url(expiration)
        manifest.image_size = int(vol_container['image']['size'])
        manifest.volume_size = int(vol_container['volume']['size'])
        part_size = (self.args.get('part_size') or 10) * 2 ** 20  # MiB
        for index, part_start in enumerate(xrange(0, manifest.image_size,
                                                  part_size)):
            part = ImportImagePart()
            part.index = index
            part.start = part_start
            part.end = min(part_start + part_size,
                           int(vol_container['image']['size'])) - 1
            part.key = '{0}/{1}.part.{2}'.format(
                key_prefix, os.path.basename(self.args['source']), index)
            part_path = '/'.join((bucket, part.key))
            head_req = HeadObject.from_other(delete_req, path=part_path)
            get_req = GetObject.from_other(delete_req, source=part_path)
            delete_req = DeleteObject.from_other(delete_req, path=part_path)
            part.head_url = head_req.get_presigned_url(expiration)
            part.get_url = get_req.get_presigned_url(expiration)
            part.delete_url = delete_req.get_presigned_url(expiration)
            manifest.image_parts.append(part)
        return manifest

    def __upload_part(self, part, part_s3path, pbar_label_template):
        self.log.info('Uploading part %s (bytes %i-%i)', part_s3path,
                      part.start, part.end)
        part_pbar_label = pbar_label_template.format(
            fname=os.path.basename(part.key), index=(part.index + 1))
        with open(self.args['source']) as source:
            source.seek(part.start)
            put_req = PutObject.from_other(
                self, service=self.args['s3_service'],
                auth=self.args['s3_auth'], source=source, dest=part_s3path,
                size=(part.end - part.start + 1),
                show_progress=self.args.get('show_progress', False),
                progressbar_label=part_pbar_label)
            return put_req.main()

########NEW FILE########
__FILENAME__ = runinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
import os.path

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.argtypes import (ec2_block_device_mapping,
                                         vpc_interface)
from euca2ools.commands.ec2 import EC2Request


class RunInstances(EC2Request):
    DESCRIPTION = 'Launch instances of a machine image'
    ARGS = [Arg('ImageId', metavar='IMAGE',
                help='ID of the image to instantiate (required)'),
            Arg('-n', '--instance-count', dest='count', metavar='MIN[-MAX]',
                default='1', route_to=None,
                help='''number of instances to launch. If this number of
                        instances cannot be launched, no instances will launch.
                        If specified as a range (min-max), the server will
                        attempt to launch the maximum number, but no fewer
                        than the minimum number.'''),
            Arg('-g', '--group', action='append', default=[], route_to=None,
                help='security group(s) in which to launch the instances'),
            Arg('-k', '--key', dest='KeyName', metavar='KEYPAIR',
                help='name of the key pair to use'),
            MutuallyExclusiveArgList(
                Arg('-d', '--user-data', metavar='DATA', route_to=None,
                    help='''user data to make available to instances in this
                            reservation'''),
                Arg('--user-data-force', metavar='DATA', route_to=None,
                    help='''same as -d/--user-data, but without checking if a
                    file by that name exists first'''),
                Arg('-f', '--user-data-file', metavar='FILE', route_to=None,
                    help='''file containing user data to make available to the
                    instances in this reservation''')),
            Arg('--addressing', dest='AddressingType',
                choices=('public', 'private'), help='''[Eucalyptus only]
                addressing scheme to launch the instance with.  Use "private"
                to run an instance with no public address.'''),
            Arg('-t', '--instance-type', dest='InstanceType',
                help='type of instance to launch'),
            Arg('-z', '--availability-zone', metavar='ZONE',
                dest='Placement.AvailabilityZone'),
            Arg('--kernel', dest='KernelId', metavar='KERNEL',
                help='ID of the kernel to launch the instance(s) with'),
            Arg('--ramdisk', dest='RamdiskId', metavar='RAMDISK',
                help='ID of the ramdisk to launch the instance(s) with'),
            Arg('-b', '--block-device-mapping', metavar='DEVICE=MAPPED',
                dest='BlockDeviceMapping', action='append',
                type=ec2_block_device_mapping, default=[],
                help='''define a block device mapping for the instances, in the
                form DEVICE=MAPPED, where "MAPPED" is "none", "ephemeral(0-3)",
                or
                "[SNAP-ID]:[GiB]:[true|false]:[standard|VOLTYPE[:IOPS]]"'''),
            Arg('-m', '--monitor', dest='Monitoring.Enabled',
                action='store_const', const='true',
                help='enable detailed monitoring for the instance(s)'),
            Arg('--disable-api-termination', dest='DisableApiTermination',
                action='store_const', const='true',
                help='prevent API users from terminating the instance(s)'),
            Arg('--instance-initiated-shutdown-behavior',
                dest='InstanceInitiatedShutdownBehavior',
                choices=('stop', 'terminate'),
                help=('whether to "stop" (default) or terminate EBS instances '
                      'when they shut down')),
            Arg('--placement-group', dest='Placement.GroupName',
                metavar='PLGROUP', help='''name of a placement group to launch
                into'''),
            Arg('--tenancy', dest='Placement.Tenancy',
                choices=('default', 'dedicated'), help='''[VPC only]
                "dedicated" to run on single-tenant hardware'''),
            Arg('--client-token', dest='ClientToken', metavar='TOKEN',
                help='unique identifier to ensure request idempotency'),
            Arg('-s', '--subnet', metavar='SUBNET', route_to=None,
                help='''[VPC only] subnet to create the instance's network
                interface in'''),
            Arg('--private-ip-address', metavar='ADDRESS', route_to=None,
                help='''[VPC only] assign a specific primary private IP address
                to an instance's interface'''),
            MutuallyExclusiveArgList(
                Arg('--secondary-private-ip-address', metavar='ADDRESS',
                    action='append', route_to=None, help='''[VPC only]
                    assign a specific secondary private IP address to an
                    instance's network interface.  Use this option multiple
                    times to add additional addresses.'''),
                Arg('--secondary-private-ip-address-count', metavar='COUNT',
                    type=int, route_to=None, help='''[VPC only]
                    automatically assign a specific number of secondary private
                    IP addresses to an instance's network interface''')),
            Arg('-a', '--network-interface', dest='NetworkInterface',
                metavar='INTERFACE', action='append', type=vpc_interface,
                help=('[VPC only] add a network interface to the new '
                      'instance.  If the interface already exists, supply its '
                      'ID and a numeric index for it, separated by ":", in '
                      'the form "eni-NNNNNNNN:INDEX".  To create a new '
                      'interface, supply a numeric index and subnet ID for '
                      'it, along with (in order) an optional description, a '
                      'primary private IP address, a list of security group '
                      'IDs to associate with the interface, whether to delete '
                      'the interface upon instance termination ("true" or '
                      '"false"), a number of secondary private IP addresses '
                      'to create automatically, and a list of secondary '
                      'private IP addresses to assign to the interface, '
                      'separated by ":", in the form ":INDEX:SUBNET:'
                      '[DESCRIPTION]:[PRIV_IP]:[GROUP1,GROUP2,...]:[true|'
                      'false]:[SEC_IP_COUNT|:SEC_IP1,SEC_IP2,...]".  You '
                      'cannot specify both of the latter two.  This option '
                      'may be used multiple times.  Each adds another network '
                      'interface.')),
            Arg('-p', '--iam-profile', metavar='IPROFILE', route_to=None,
                help='''name or ARN of the IAM instance profile to associate
                with the new instance(s)'''),
            Arg('--ebs-optimized', dest='EbsOptimized', action='store_const',
                const='true', help='optimize the new instance(s) for EBS I/O')]

    LIST_TAGS = ['reservationSet', 'instancesSet', 'groupSet', 'tagSet',
                 'blockDeviceMapping', 'productCodes', 'networkInterfaceSet',
                 'privateIpAddressesSet']

    # noinspection PyExceptionInherit
    def configure(self):
        EC2Request.configure(self)
        if self.args.get('user_data'):
            if os.path.isfile(self.args['user_data']):
                raise ArgumentError(
                    'argument -d/--user-data: to pass the contents of a file '
                    'as user data, use -f/--user-data-file.  To pass the '
                    "literal value '{0}' as user data even though it matches "
                    'the name of a file, use --user-data-force.')
            else:
                self.params['UserData'] = base64.b64encode(
                    self.args['user_data'])
        elif self.args.get('user_data_force'):
            self.params['UserData'] = base64.b64encode(
                self.args['user_data_force'])
        elif self.args.get('user_data_file'):
            with open(self.args['user_data_file']) as user_data_file:
                self.params['UserData'] = base64.b64encode(
                    user_data_file.read())

        if self.args.get('KeyName') is None:
            default_key_name = self.config.get_region_option(
                'ec2-default-keypair')
            if default_key_name:
                self.log.info("using default key pair '%s'", default_key_name)
                self.params['KeyName'] = default_key_name

    # noinspection PyExceptionInherit
    def preprocess(self):
        counts = self.args['count'].split('-')
        if len(counts) == 1:
            try:
                self.params['MinCount'] = int(counts[0])
                self.params['MaxCount'] = int(counts[0])
            except ValueError:
                raise ArgumentError('argument -n/--instance-count: instance '
                                    'count must be an integer')
        elif len(counts) == 2:
            try:
                self.params['MinCount'] = int(counts[0])
                self.params['MaxCount'] = int(counts[1])
            except ValueError:
                raise ArgumentError('argument -n/--instance-count: instance '
                                    'count range must be must be comprised of '
                                    'integers')
        else:
            raise ArgumentError('argument -n/--instance-count: value must '
                                'have format "1" or "1-2"')
        if self.params['MinCount'] < 1 or self.params['MaxCount'] < 1:
            raise ArgumentError('argument -n/--instance-count: instance count '
                                'must be positive')
        if self.params['MinCount'] > self.params['MaxCount']:
            self.log.debug('MinCount > MaxCount; swapping')
            self.params.update({'MinCount': self.params['MaxCount'],
                                'MaxCount': self.params['MinCount']})

        for group in self.args['group']:
            if group.startswith('sg-'):
                self.params.setdefault('SecurityGroupId', [])
                self.params['SecurityGroupId'].append(group)
            else:
                self.params.setdefault('SecurityGroup', [])
                self.params['SecurityGroup'].append(group)

        iprofile = self.args.get('iam_profile')
        if iprofile:
            if iprofile.startswith('arn:'):
                self.params['IamInstanceProfile.Arn'] = iprofile
            else:
                self.params['IamInstanceProfile.Name'] = iprofile

        # Assemble an interface out of the "friendly" split interface options
        cli_iface = {}
        if self.args.get('private_ip_address'):
            cli_iface['PrivateIpAddresses'] = [
                {'PrivateIpAddress': self.args['private_ip_address'],
                 'Primary': 'true'}]
        if self.args.get('secondary_private_ip_address'):
            sec_ips = [{'PrivateIpAddress': addr} for addr in
                       self.args['secondary_private_ip_address']]
            cli_iface.setdefault('PrivateIpAddresses', [])
            cli_iface['PrivateIpAddresses'].extend(sec_ips)
        if self.args.get('secondary_private_ip_address_count'):
            sec_ip_count = self.args['secondary_private_ip_address_count']
            cli_iface['SecondaryPrivateIpAddressCount'] = sec_ip_count
        if self.args.get('subnet'):
            cli_iface['SubnetId'] = self.args['subnet']
        if cli_iface:
            cli_iface['DeviceIndex'] = 0
            self.params.setdefault('NetworkInterface', [])
            self.params['NetworkInterface'].append(cli_iface)

    def print_result(self, result):
        self.print_reservation(result)

########NEW FILE########
__FILENAME__ = startinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class StartInstances(EC2Request):
    DESCRIPTION = 'Start one or more stopped instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+',
                help='ID(s) of the instance(s) to start')]
    LIST_TAGS = ['instancesSet']

    def print_result(self, result):
        for instance in result.get('instancesSet', []):
            print self.tabify(('INSTANCE', instance.get('instanceId'),
                               instance.get('previousState', {}).get('name'),
                               instance.get('currentState', {}).get('name')))

########NEW FILE########
__FILENAME__ = stopinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class StopInstances(EC2Request):
    DESCRIPTION = 'Stop one or more running instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+',
                help='ID(s) of the instance(s) to stop'),
            Arg('-f', '--force', dest='Force', action='store_const',
                const='true',
                help='immediately stop the instance(s). Data may be lost')]
    LIST_TAGS = ['instancesSet']

    def print_result(self, result):
        for instance in result.get('instancesSet', []):
            print self.tabify(('INSTANCE', instance.get('instanceId'),
                               instance.get('previousState', {}).get('name'),
                               instance.get('currentState', {}).get('name')))

########NEW FILE########
__FILENAME__ = structures
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

import lxml.etree
import lxml.objectify

import euca2ools


class ImportManifest(object):
    def __init__(self, loglevel=None):
        self.log = logging.getLogger(self.__class__.__name__)
        if loglevel is not None:
            self.log.level = loglevel
        self.file_format = None
        self.self_destruct_url = None
        self.image_size = None
        self.volume_size = None
        self.image_parts = []

    @classmethod
    def read_from_file(cls, manifest_filename):
        with open(manifest_filename) as manifest_fileobj:
            return cls.read_from_fileobj(manifest_fileobj)

    @classmethod
    def read_from_fileobj(cls, manifest_fileobj):
        xml = lxml.objectify.parse(manifest_fileobj).getroot()
        manifest = cls()

        manifest.file_format = xml['file-format'].text
        manifest.self_destruct_url = xml['self-destruct-url'].text
        manifest.image_size = int(xml['import'].size)
        manifest.volume_size = int(xml['import']['volume-size'])
        manifest.image_parts = [None] * int(xml['import']['parts']
                                            .get('count'))
        for part in xml['import']['parts']['part']:
            part_index = int(part.get('index'))
            part_obj = ImportImagePart()
            part_obj.index = part_index
            part_obj.start = int(part['byte-range'].get('start'))
            part_obj.end = int(part['byte-range'].get('end'))
            part_obj.key = part['key'].text
            part_obj.head_url = part['head-url'].text
            part_obj.get_url = part['get-url'].text
            part_obj.delete_url = part['delete-url'].text
            manifest.image_parts[part_index] = part_obj
        assert None not in manifest.image_parts, 'part missing from manifest'
        return manifest

    def dump_to_str(self, pretty_print=False):
        xml = lxml.objectify.Element('manifest')

        # Manifest version
        xml.version = '2010-11-15'

        # File format
        xml['file-format'] = self.file_format

        # Our version
        xml.importer = None
        xml.importer.name = 'euca2ools'
        xml.importer.version = euca2ools.__version__
        xml.importer.release = 0

        # Import and image part info
        xml['self-destruct-url'] = self.self_destruct_url
        xml['import'] = None
        xml['import']['size'] = self.image_size
        xml['import']['volume-size'] = self.volume_size
        xml['import']['parts'] = None
        xml['import']['parts'].set('count', str(len(self.image_parts)))
        for part in self.image_parts:
            xml['import']['parts'].append(part.dump_to_xml())

        # Cleanup
        lxml.objectify.deannotate(xml, xsi_nil=True)
        lxml.etree.cleanup_namespaces(xml)
        self.log.debug('-- manifest content --\n', extra={'append': True})
        pretty_manifest = lxml.etree.tostring(xml, pretty_print=True).strip()
        self.log.debug('%s', pretty_manifest, extra={'append': True})
        self.log.debug('-- end of manifest content --')
        return lxml.etree.tostring(xml, pretty_print=pretty_print,
                                   encoding='UTF-8', standalone=True,
                                   xml_declaration=True).strip()

    def dump_to_fileobj(self, fileobj, pretty_print=False):
        fileobj.write(self.dump_to_str(pretty_print=pretty_print))


class ImportImagePart(object):
    def __init__(self):
        self.index = None
        self.start = None
        self.end = None
        self.key = None
        self.head_url = None
        self.get_url = None
        self.delete_url = None

    def dump_to_xml(self):
        xml = lxml.objectify.Element('part', index=str(self.index))
        xml['byte-range'] = None
        xml['byte-range'].set('start', str(self.start))
        xml['byte-range'].set('end', str(self.end))
        xml['key'] = self.key
        xml['head-url'] = self.head_url
        xml['get-url'] = self.get_url
        xml['delete-url'] = self.delete_url
        return xml

########NEW FILE########
__FILENAME__ = terminateinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class TerminateInstances(EC2Request):
    DESCRIPTION = 'Terminate one or more instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+',
                help='ID(s) of the instance(s) to terminate')]
    LIST_TAGS = ['instancesSet']

    def print_result(self, result):
        for instance in result.get('instancesSet', []):
            print self.tabify(('INSTANCE', instance.get('instanceId'),
                               instance.get('previousState', {}).get('name'),
                               instance.get('currentState', {}).get('name')))

########NEW FILE########
__FILENAME__ = unmonitorinstances
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.ec2 import EC2Request
from requestbuilder import Arg


class UnmonitorInstances(EC2Request):
    DESCRIPTION = 'Disable monitoring for one or more instances'
    ARGS = [Arg('InstanceId', metavar='INSTANCE', nargs='+', help='''ID(s) of
                the instance(s) to stop monitoring (at least 1 required)''')]
    LIST_TAGS = ['instancesSet']

    def print_result(self, result):
        for instance in result.get('instancesSet', []):
            mon_state = 'monitoring-{0}'.format(
                instance.get('monitoring', {}).get('state'))
            print self.tabify((instance.get('instanceId'), mon_state))

########NEW FILE########
__FILENAME__ = applysecuritygroupstoloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class ApplySecurityGroupsToLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = ('[VPC only] Associate one or more security groups with a '
                   'load balancer.  All previous associations with security '
                   'groups will be replaced.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-g', '--security-groups', dest='SecurityGroups.member',
                metavar='GROUP1,GROUP2,...', type=delimited_list(','),
                required=True, help='''security groups to associate the load
                balancer with (required)''')]
    LIST_TAGS = ['SecurityGroups']

    def print_result(self, result):
        print self.tabify(('SECURITY_GROUPS',
                           ', '.join(result.get('SecurityGroups', []))))

########NEW FILE########
__FILENAME__ = argtypes
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse


def listener(listener_str):
    pairs = {}
    for pair_str in listener_str.strip().split(','):
        if pair_str:
            try:
                key, val = pair_str.split('=')
            except ValueError:
                raise argparse.ArgumentTypeError(
                    "listener '{0}': element '{1}' must have format KEY=VALUE"
                    .format(listener_str, pair_str))
            pairs[key.strip()] = val.strip()

    extra_keys = (set(pairs.keys()) -
                  set(('protocol', 'lb-port', 'instance-port',
                       'instance-protocol', 'cert-id')))
    if len(extra_keys) > 0:
        raise argparse.ArgumentTypeError(
            "listener '{0}': invalid element(s): {1}".format(
                listener_str,
                ', '.join("'{0}'".format(key) for key in extra_keys)))

    listener_dict = {}
    if 'protocol' in pairs:
        if pairs['protocol'].upper() in ('HTTP', 'HTTPS', 'SSL', 'TCP'):
            listener_dict['Protocol'] = pairs['protocol'].upper()
        else:
            raise argparse.ArgumentTypeError(
                "listener '{0}': protocol '{1}' is invalid (choose from "
                "'HTTP', 'HTTPS', 'SSL', 'TCP')"
                .format(listener_str, pairs['protocol']))
    else:
        raise argparse.ArgumentTypeError(
            "listener '{0}': protocol is required".format(listener_str))
    if 'lb-port' in pairs:
        try:
            listener_dict['LoadBalancerPort'] = int(pairs['lb-port'])
        except ValueError:
            raise argparse.ArgumentTypeError(
                "listener '{0}': lb-port must be an integer"
                .format(listener_str))
    else:
        raise argparse.ArgumentTypeError(
            "listener '{0}': lb-port is required".format(listener_str))
    if 'instance-port' in pairs:
        try:
            listener_dict['InstancePort'] = int(pairs['instance-port'])
        except ValueError:
            raise argparse.ArgumentTypeError(
                "listener '{0}': instance-port must be an integer"
                .format(listener_str))
    else:
        raise argparse.ArgumentTypeError(
            "listener '{0}': instance-port is required".format(listener_str))
    if 'instance-protocol' in pairs:
        if pairs['instance-protocol'].upper() in ('HTTP', 'HTTPS'):
            if pairs['protocol'].upper() not in ('HTTP', 'HTTPS'):
                raise argparse.ArgumentTypeError(
                    "listener '{0}': instance-protocol must be 'HTTP' or "
                    "'HTTPS' when protocol is 'HTTP' or 'HTTPS'"
                    .format(listener_str))
        elif pairs['instance-protocol'].upper() in ('SSL', 'TCP'):
            if pairs['protocol'].upper() not in ('SSL', 'TCP'):
                raise argparse.ArgumentTypeError(
                    "listener '{0}': instance-protocol must be 'SSL' or "
                    "'TCP' when protocol is 'SSL' or 'TCP'"
                    .format(listener_str))
        else:
            raise argparse.ArgumentTypeError(
                "listener '{0}': instance-protocol '{1}' is invalid (choose "
                "from 'HTTP', 'HTTPS', 'SSL', 'TCP')"
                .format(listener_str, pairs['instance-protocol']))
        listener_dict['InstanceProtocol'] = pairs['instance-protocol'].upper()
    if 'cert-id' in pairs:
        listener_dict['SSLCertificateId'] = pairs['cert-id']
    return listener_dict

########NEW FILE########
__FILENAME__ = attachloadbalancertosubnets
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class AttachLoadBalancerToSubnets(ELBRequest, TabifyingMixin):
    DESCRIPTION = '[VPC only] Add a load balancer to one or more subnets'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-s', '--subnets', dest='Subnets.member', required=True,
                metavar='SUBNET1,SUBNET2,...', type=delimited_list(','),
                help='''IDs of the subnets to add the load balancer to
                (required)''')]
    LIST_TAGS = ['Subnets']

    def print_result(self, result):
        print self.tabify(('SUBNETS', ', '.join(result.get('Subnets', []))))

########NEW FILE########
__FILENAME__ = configurehealthcheck
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import TabifyingMixin


class ConfigureHealthCheck(ELBRequest, TabifyingMixin):
    DESCRIPTION = ('Configure health checking for instance registerd with a '
                   'load balancer')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('--healthy-threshold', dest='HealthCheck.HealthyThreshold',
                metavar='COUNT', type=int, required=True,
                help='''number of consecutive successful health checks that
                will mark instances as Healthy (required)'''),
            Arg('--interval', dest='HealthCheck.Interval', metavar='SECONDS',
                type=int, required=True,
                help='approximate interval between health checks (required)'),
            Arg('-t', '--target', dest='HealthCheck.Target',
                metavar='PROTOCOL:PORT[/PATH]', required=True,
                help='connection target for health checks (required)'),
            Arg('--timeout', dest='HealthCheck.Timeout', metavar='SECONDS',
                type=int, required=True,
                help='maximum health check duration (required)'),
            Arg('--unhealthy-threshold', dest='HealthCheck.UnhealthyThreshold',
                metavar='COUNT', type=int, required=True,
                help='''number of consecutive failed health checks that will
                mark instances as Unhealthy (required)''')]

    # noinspection PyExceptionInherit
    def configure(self):
        ELBRequest.configure(self)
        target = self.args['HealthCheck.Target']
        protocol, _, rest = target.partition(':')
        if not rest:
            raise ArgumentError('argument -t/--target: must have form '
                                'PROTOCOL:PORT[/PATH]')
        if protocol.lower() in ('http', 'https') and '/' not in rest:
            raise ArgumentError('argument -t/--target: path is required for '
                                "protocol '{0}'".format(protocol))

    def preprocess(self):
        # Be nice and auto-capitalize known protocols for people
        target = self.args['HealthCheck.Target']
        protocol = target.split(':', 1)[0]
        if protocol.lower() in ('http', 'https', 'ssl', 'tcp'):
            self.params['HealthCheck.Target'] = target.replace(
                protocol, protocol.upper(), 1)

    def print_result(self, result):
        check = result.get('HealthCheck', {})
        print self.tabify(('HEALTH_CHECK', check.get('Target'),
                           check.get('Interval'), check.get('Timeout'),
                           check.get('HealthyThreshold'),
                           check.get('UnhealthyThreshold')))

########NEW FILE########
__FILENAME__ = createappcookiestickinesspolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class CreateAppCookieStickinessPolicy(ELBRequest):
    DESCRIPTION = ('Create a new stickiness policy for a load balancer, '
                   'whereby the server application generates a cookie and '
                   'adds it to its responses.  The load balancer will then '
                   'use this cookie to route requests from each user to the '
                   'same back end instance.  This type of policy can only be '
                   'associated with HTTP or HTTPS listeners,')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            # -c is for cookie.  That's good enough for me.
            Arg('-c', '--cookie-name', dest='CookieName', required=True,
                help='name of the cookie used for stickiness (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the new policy (required)')]

########NEW FILE########
__FILENAME__ = createlbcookiestickinesspolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class CreateLBCookieStickinessPolicy(ELBRequest):
    DESCRIPTION = ('Create a new stickiness policy for a load balancer, '
                   'whereby the load balancer automatically generates cookies '
                   'that it uses to route requests from each user to the same '
                   'back end instance.  This type of policy can only be '
                   'associated with HTTP or HTTPS listeners.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-e', '--expiration-period', dest='CookieExpirationPeriod',
                metavar='SECONDS', type=int, required=True,
                help='''time period after which cookies should be considered
                stale (default: user's session length) (required)'''),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the new policy (required)')]

########NEW FILE########
__FILENAME__ = createloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.mixins import TabifyingMixin

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from euca2ools.commands.elasticloadbalancing.argtypes import listener


class CreateLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = ('Create a load balancer\n\nAfter the load balancer is '
                   'created, instances must be registered with it separately.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the new load balancer (required)'),
            MutuallyExclusiveArgList(
                Arg('-s', '--subnets', metavar='SUBNET1,SUBNET2,...',
                    dest='Subnets.member', type=delimited_list(','),
                    help='''[VPC only] subnets the load balancer should run in
                    (required)'''),
                Arg('-z', '--availability-zones', metavar='ZONE1,ZONE2,...',
                    dest='AvailabilityZones.member', type=delimited_list(','),
                    help='''[Non-VPC only] availability zones the load balancer
                    should run in (required)'''))
            .required(),
            Arg('-l', '--listener', dest='Listeners.member', action='append',
                metavar=('"lb-port=PORT, protocol={HTTP,HTTPS,SSL,TCP}, '
                         'instance-port=PORT, instance-protocol={HTTP,HTTPS,'
                         'SSL,TCP}, cert-id=ARN"'), required=True,
                type=listener,
                help='''port/protocol settings for the load balancer, where
                lb-port is the external port number, protocol is the external
                protocol, instance-port is the back end server port number,
                instance-protocol is the protocol to use for routing traffic to
                back end instances, and cert-id is the ARN of the server
                certificate to use for encrypted connections.  lb-port,
                protocol, and instance-port are required.  This option may be
                used multiple times.  (at least 1 required)'''),
            Arg('-i', '--scheme', dest='Scheme', choices=('internal',),
                metavar='internal', help='''[VPC only] "internal" to make the
                new load balancer private to a VPC'''),
            Arg('-g', '--security-groups', dest='SecurityGroups.member',
                metavar='GROUP1,GROUP2,...', type=delimited_list(','),
                help='''[VPC only] IDs of the security groups to assign to the
                new load balancer''')]

    def print_result(self, result):
        print self.tabify(('DNS_NAME', result.get('DNSName')))

########NEW FILE########
__FILENAME__ = createloadbalancerlisteners
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from euca2ools.commands.elasticloadbalancing.argtypes import listener
from requestbuilder import Arg


class CreateLoadBalancerListeners(ELBRequest):
    DESCRIPTION = 'Add one or more listeners to a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-l', '--listener', dest='Listeners.member', action='append',
                metavar=('"lb-port=PORT, protocol={HTTP,HTTPS,SSL,TCP}, '
                         'instance-port=PORT, instance-protocol={HTTP,HTTPS,'
                         'SSL,TCP}, cert-id=ARN"'), required=True,
                type=listener,
                help='''port/protocol settings for the load balancer, where
                lb-port is the external port number, protocol is the external
                protocol, instance-port is the back end server port number,
                instance-protocol is the protocol to use for routing traffic to
                back end instances, and cert-id is the ARN of the server
                certificate to use for encrypted connections.  lb-port,
                protocol, and instance-port are required.  This option may be
                used multiple times.  (at least 1 required)''')]

########NEW FILE########
__FILENAME__ = createloadbalancerpolicy
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


def attribute(attr_as_str):
    attr = {}
    for pair in attr_as_str.split(','):
        key, _, val = pair.partition('=')
        if key.strip() == 'name':
            attr['AttributeName'] = val.strip()
        elif key.strip() == 'value':
            attr['AttributeValue'] = val.strip()
        else:
            raise argparse.ArgumentTypeError(
                "attribute '{0}': '{1}' is not a valid part of an attribute "
                "(choose from " "'name', 'value')".format(attr_as_str,
                                                          key.strip()))
    if 'AttributeName' not in attr:
        raise argparse.ArgumentTypeError(
            "attribute '{0}': name is required".format(attr_as_str))
    if 'AttributeValue' not in attr:
        raise argparse.ArgumentTypeError(
            "attribute '{0}': value is required".format(attr_as_str))
    return attr


class CreateLoadBalancerPolicy(ELBRequest):
    DESCRIPTION = 'Add a new policy to a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the new policy (required)'),
            Arg('--policy-type', dest='PolicyTypeName', metavar='POLTYPE',
                required=True,
                help='''type of the new policy.  For a list of policy types,
                use eulb-describe-lb-policy-types.  (required)'''),
            Arg('-a', '--attribute', dest='PolicyAttributes.member',
                action='append', metavar='"name=NAME, value=VALUE"',
                type=attribute, help='''name and value for each attribute
                associated with the new policy.  Use this option multiple times
                to supply multiple attributes.''')]

########NEW FILE########
__FILENAME__ = deleteloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class DeleteLoadBalancer(ELBRequest):
    DESCRIPTION = ('Delete a load balancer\n\nIf the load balancer does not '
                   'exist, this command still succeeds.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to delete (required)'),
            Arg('--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deleteloadbalancerlisteners
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class DeleteLoadBalancerListeners(ELBRequest):
    DESCRIPTION = ('Delete one or more listeners from a load balancer\n\nIf '
                   'a listener named with -l/--lb-ports does not exist, this '
                   'command still succeeds.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-l', '--lb-ports', dest='LoadBalancerPorts.member',
                metavar='PORT1,PORT2,...', required=True,
                type=delimited_list(',', item_type=int),
                help='port numbers of the listeners to remove (required)'),
            Arg('--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = deleteloadbalancerpolicy
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class DeleteLoadBalancerPolicy(ELBRequest):
    DESCRIPTION = 'Delete a policy from a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to delete (required)')]

########NEW FILE########
__FILENAME__ = deregisterinstancesfromloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


def instance_id(inst_as_str):
    return {'InstanceId': inst_as_str}


class DeregisterInstancesFromLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Remove one or more instances from a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('--instances', dest='Instances.member', required=True,
                metavar='INSTANCE1,INSTANCE2,...',
                type=delimited_list(',', item_type=instance_id),
                help='''IDs of the instances to remove from the load balancer
                (required)''')]
    LIST_TAGS = ['Instances']

    def print_result(self, result):
        for instance in result.get('Instances', []):
            print self.tabify(('INSTANCE', instance.get('InstanceId')))

########NEW FILE########
__FILENAME__ = describeinstancehealth
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


def instance_id(inst_as_str):
    return {'InstanceId': inst_as_str}


class DescribeInstanceHealth(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Show the state of instances registered with a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB', help='''name of the load
                balancer to describe instances for (required)'''),
            Arg('--instances', dest='Instances.member',
                metavar='INSTANCE1,INSTANCE2,...',
                type=delimited_list(',', item_type=instance_id),
                help='limit results to specific instances'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the instances' info")]
    LIST_TAGS = ['InstanceStates']

    def print_result(self, result):
        for instance in result.get('InstanceStates', []):
            bits = ['INSTANCE', instance.get('InstanceId'),
                    instance.get('State')]
            if self.args['show_long']:
                bits.append(instance.get('Description'))
                bits.append(instance.get('ReasonCode'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describeloadbalancerpolicies
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class DescribeLoadBalancerPolicies(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Show information about load balancer policies'
    ARGS = [Arg('LoadBalancerName', metavar='ELB', nargs='?', help='''show
                policies associated with a specific load balancer (default:
                only describe sample policies provided by the service)'''),
            Arg('-p', '--policy-names', dest='PolicyNames.member',
                metavar='POLICY1,POLICY2,...', type=delimited_list(','),
                help='limit results to specific policies'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the policies' info")]
    LIST_TAGS = ['PolicyDescriptions', 'PolicyAttributeDescriptions']

    def print_result(self, result):
        for policy in result.get('PolicyDescriptions', []):
            bits = ['POLICY', policy.get('PolicyName'),
                    policy.get('PolicyTypeName')]
            if self.args['show_long']:
                attrs = []
                for attr in policy.get('PolicyAttributeDescriptions', []):
                    attrs.append('{{name={0},value={1}}}'.format(
                        attr.get('AttributeName'), attr.get('AttributeValue')))
                if len(attrs) > 0:
                    bits.append(','.join(attrs))
                else:
                    bits.append(None)
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describeloadbalancerpolicytypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class DescribeLoadBalancerPolicyTypes(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Show information about load balancer policy types'
    ARGS = [Arg('PolicyTypeNames.member', metavar='POLTYPE', nargs='*',
                help='limit results to specific policy types'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the policy types' info")]
    LIST_TAGS = ['PolicyTypeDescriptions', 'PolicyAttributeTypeDescriptions']

    def print_result(self, result):
        for poltype in result.get('PolicyTypeDescriptions', []):
            bits = ['POLICY_TYPE', poltype.get('PolicyTypeName'),
                    poltype.get('Description')]
            if self.args['show_long']:
                attrs = []
                for attr in poltype.get('PolicyAttributeTypeDescriptions', []):
                    elem_map = (('name', 'AttributeName'),
                                ('description', 'Description'),
                                ('type', 'AttributeType'),
                                ('default-value', 'DefaultValue'),
                                ('cardinality', 'Cardinality'))
                    attr_bits = []
                    for name, xmlname in elem_map:
                        attr_bits.append('='.join((name,
                                                   attr.get(xmlname) or '')))
                    attrs.append('{' + ','.join(attr_bits) + '}')
                bits.append(','.join(attrs))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describeloadbalancers
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class DescribeLoadBalancers(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Show information about load balancers'
    ARGS = [Arg('LoadBalancerNames.member', metavar='ELB', nargs='*',
                help='limit results to specific load balancers'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the load balancers' info")]
    LIST_TAGS = ['LoadBalancerDescriptions', 'AvailabilityZones',
                 'BackendServerDescriptions', 'Instances',
                 'ListenerDescriptions', 'PolicyNames',
                 'AppCookieStickinessPolicies', 'LBCookieStickinessPolicies',
                 'OtherPolicies', 'SecurityGroups', 'Subnets']

    def print_result(self, result):
        for desc in result.get('LoadBalancerDescriptions', []):
            bits = ['LOAD_BALANCER',
                    desc.get('LoadBalancerName'),
                    desc.get('DNSName')]
            if self.args['show_long']:
                bits.append(desc.get('CanonicalHostedZoneName'))
                bits.append(desc.get('CanonicalHostedZoneNameID'))
                check = desc.get('HealthCheck')
                if check is not None:
                    check_str_bits = []
                    elem_map = (('interval', 'Interval'),
                                ('target', 'Target'),
                                ('timeout', 'Timeout'),
                                ('healthy-threshold', 'HealthyThreshold'),
                                ('unhealthy-threshold', 'UnhealthyThreshold'))
                    for name, xmlname in elem_map:
                        if check.get(xmlname):
                            check_str_bits.append(name + '=' + check[xmlname])
                    if len(check_str_bits) > 0:
                        bits.append('{' + ','.join(check_str_bits) + '}')
                    else:
                        bits.append(None)
                else:
                    bits.append(None)
                bits.append(','.join(zone for zone in
                                     desc.get('AvailabilityZones', [])))
                bits.append(','.join(net for net in desc.get('Subnets', [])))
                bits.append(desc.get('VPCId'))
                bits.append(','.join(instance.get('InstanceId') for instance in
                                     desc.get('Instances', [])))

                listeners = []
                for listenerdesc in desc.get('ListenerDescriptions', []):
                    listener = listenerdesc.get('Listener', {})
                    listener_str_bits = []
                    elem_map = (('protocol', 'Protocol'),
                                ('lb-port', 'LoadBalancerPort'),
                                ('instance-protocol', 'InstanceProtocol'),
                                ('instance-port', 'InstancePort'),
                                ('cert-id', 'SSLCertificateId'))
                    for name, xmlname in elem_map:
                        if listener.get(xmlname):
                            listener_str_bits.append(name + '=' +
                                                     listener[xmlname])
                    if listenerdesc.get('PolicyNames'):
                        listener_str_bits.append(
                            '{' + ','.join(listenerdesc['PolicyNames']) + '}')
                    listeners.append('{' + ','.join(listener_str_bits) + '}')
                if len(listeners) > 0:
                    bits.append(','.join(listeners))
                else:
                    bits.append(None)

                beservers = []
                for bedesc in desc.get('BackendServerDescriptions', []):
                    beserver_str_bits = []
                    if 'InstancePort' in bedesc:
                        beserver_str_bits.append('instance-port=' +
                                                 bedesc['InstancePort'])
                    if 'PolicyNames' in bedesc:
                        policies = ','.join(policy for policy in
                                            bedesc['PolicyNames'])
                        beserver_str_bits.append('policies={' + policies + '}')
                    beservers.append('{' + ','.join(beserver_str_bits) + '}')
                if len(beservers) > 0:
                    bits.append(','.join(beservers))
                else:
                    bits.append(None)

                all_policies = desc.get('Policies') or {}

                app_policies = all_policies.get(
                    'AppCookieStickinessPolicies') or {}
                app_policy_strs = ['{{policy-name={0},cookie-name={1}}}'
                                   .format(policy.get('PolicyName'),
                                           policy.get('CookieName'))
                                   for policy in app_policies]
                bits.append(','.join(app_policy_strs) or None)

                lb_policies = all_policies.get(
                    'LBCookieStickinessPolicies') or {}
                lb_policy_strs = ['{{policy-name={0},expiration-period={1}}}'
                                  .format(policy.get('PolicyName'),
                                          policy.get('CookieExpirationPeriod'))
                                  for policy in lb_policies]
                bits.append(','.join(lb_policy_strs) or None)

                other_policies = all_policies.get('OtherPolicies') or {}
                if other_policies:
                    bits.append('{' + ','.join(other_policies) + '}')
                else:
                    bits.append(None)

                group = desc.get('SourceSecurityGroup')
                if group:
                    bits.append('{{owner-alias={0},group-name={1}}}'.format(
                        group.get('OwnerAlias', ''),
                        group.get('GroupName', '')))
                else:
                    bits.append(None)

                if desc.get('SecurityGroups'):
                    bits.append('{' + ','.join(desc['SecurityGroups']) + '}')
                else:
                    bits.append(None)
            bits.append(desc.get('CreatedTime'))
            bits.append(desc.get('Scheme'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = detachloadbalancerfromsubnets
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class DetachLoadBalancerFromSubnets(ELBRequest, TabifyingMixin):
    DESCRIPTION = '[VPC only] Remove a load balancer from one or more subnets'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-s', '--subnets', dest='Subnets.member', required=True,
                metavar='SUBNET1,SUBNET2,...', type=delimited_list(','),
                help='''IDs of the subnets to remove the load balancer from
                (required)''')]
    LIST_TAGS = ['Subnets']

    def print_result(self, result):
        print self.tabify(('SUBNETS', ','.join(result.get('Subnets', []))))

########NEW FILE########
__FILENAME__ = disableavailabilityzonesforloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class DisableAvailabilityZonesForLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Remove a load balancer from one or more availability zones'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-z', '--availability-zones', dest='AvailabilityZones.member',
                metavar='ZONE1,ZONE2,...', type=delimited_list(','),
                required=True, help='''availability zones to remove the load
                balancer from (required)''')]
    LIST_TAGS = ['AvailabilityZones']

    def print_result(self, result):
        print self.tabify(('AVAILABILITY_ZONES',
                           ', '.join(result.get('AvailabilityZones', []))))

########NEW FILE########
__FILENAME__ = enableavailabilityzonesforloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class EnableAvailabilityZonesForLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Add a load balancer to one or more availability zones'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-z', '--availability-zones', dest='AvailabilityZones.member',
                metavar='ZONE1,ZONE2,...', type=delimited_list(','),
                required=True, help='''availability zones to add the load
                balancer to (required)''')]
    LIST_TAGS = ['AvailabilityZones']

    def print_result(self, result):
        print self.tabify(('AVAILABILITY_ZONES',
                           ', '.join(result.get('AvailabilityZones', []))))

########NEW FILE########
__FILENAME__ = registerinstanceswithloadbalancer
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


def instance_id(inst_as_str):
    return {'InstanceId': inst_as_str}


class RegisterInstancesWithLoadBalancer(ELBRequest, TabifyingMixin):
    DESCRIPTION = 'Add one or more instances to a load balancer'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('--instances', dest='Instances.member', required=True,
                metavar='INSTANCE1,INSTANCE2,...',
                type=delimited_list(',', item_type=instance_id),
                help='''IDs of the instances to register with the load
                balancer (required)''')]
    LIST_TAGS = ['Instances']

    def print_result(self, result):
        for instance in result.get('Instances', []):
            print self.tabify(('INSTANCE', instance.get('InstanceId')))

########NEW FILE########
__FILENAME__ = setloadbalancerlistenersslcertificate
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg


class SetLoadBalancerListenerSSLCertificate(ELBRequest):
    DESCRIPTION = ("Change the certificate that terminates a load balancer's"
                   "listener's SSL connections")
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-l', '--lb-port', dest='LoadBalancerPort', metavar='PORT',
                type=int, required=True,
                help='port that should use the certificate (required)'),
            Arg('-c', '--cert-id', dest='SSLCertificateId', metavar='ARN',
                required=True,
                help='ARN for the server certificate to use (required)')]

########NEW FILE########
__FILENAME__ = setloadbalancerpoliciesforbackendserver
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg, EMPTY


class SetLoadBalancerPoliciesForBackendServer(ELBRequest):
    DESCRIPTION = ('Change the policies associated with a port on which load-'
                   'balanced back end servers listen.')
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-i', '--instance-port', dest='InstancePort', metavar='PORT',
                type=int, required=True,
                help='port number of the back end server (required)'),
            Arg('-p', '--policy-names', dest='PolicyNames.member',
                metavar='POLICY1,POLICY2,...', type=delimited_list(','),
                required=True, help='''list of policies to associate with the
                back end server (required)''')]

    def preprocess(self):
        if not self.args.get('PolicyNames.member'):
            self.params['PolicyNames'] = EMPTY

########NEW FILE########
__FILENAME__ = setloadbalancerpoliciesoflistener
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.elasticloadbalancing import ELBRequest
from requestbuilder import Arg, EMPTY


class SetLoadBalancerPoliciesOfListener(ELBRequest):
    DESCRIPTION = 'Change the policy associated with a load balancer listener'
    ARGS = [Arg('LoadBalancerName', metavar='ELB',
                help='name of the load balancer to modify (required)'),
            Arg('-l', '--lb-port', dest='LoadBalancerPort', metavar='PORT',
                type=int, required=True,
                help='port of the listener to modify (required)'),
            Arg('-p', '--policy-names', dest='PolicyNames.member',
                metavar='POLICY1,POLICY2,...', type=delimited_list(','),
                required=True, help='''list of policies to associate with the
                listener (required)''')]

    def preprocess(self):
        if not self.args.get('PolicyNames.member'):
            self.params['PolicyNames'] = EMPTY

########NEW FILE########
__FILENAME__ = addgrouppolicy
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.putgrouppolicy import PutGroupPolicy
from euca2ools.util import build_iam_policy


class AddGroupPolicy(IAMRequest):
    DESCRIPTION = ('Add a new policy to a group. To add more complex policies '
                   'than this tool supports, see euare-groupuploadpolicy.')
    ARGS = [Arg('-g', '--group-name', metavar='GROUP', required=True,
                help='group to attach the policy to (required)'),
            Arg('-p', '--policy-name', metavar='POLICY', required=True,
                help='name of the new policy (required)'),
            Arg('-e', '--effect', choices=('Allow', 'Deny'), required=True,
                help='whether the new policy should Allow or Deny (required)'),
            Arg('-a', '--action', dest='actions', action='append',
                required=True, help='''action(s) the policy should apply to
                (at least one required)'''),
            Arg('-r', '--resource', dest='resources', action='append',
                required=True, help='''resource(s) the policy should apply to
                (at least one required)'''),
            Arg('-o', '--output', action='store_true',
                help='display the newly-created policy'),
            AS_ACCOUNT]

    def main(self):
        policy = build_iam_policy(self.args['effect'], self.args['resources'],
                                  self.args['actions'])
        policy_doc = json.dumps(policy)
        req = PutGroupPolicy.from_other(
            self, GroupName=self.args['group_name'],
            PolicyName=self.args['policy_name'],
            PolicyDocument=policy_doc,
            DelegateAccount=self.params['DelegateAccount'])
        response = req.main()
        response['PolicyDocument'] = policy_doc
        return response

    def print_result(self, result):
        if self.args['output']:
            print result['PolicyDocument']

########NEW FILE########
__FILENAME__ = addrolepolicy
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.putrolepolicy import PutRolePolicy
from euca2ools.util import build_iam_policy


class AddRolePolicy(IAMRequest):
    DESCRIPTION = ('Add a new policy to a role.  To add more complex policies '
                   'than this tool supports, see euare-roleuploadpolicy.')
    ARGS = [Arg('-r', '--role-name', metavar='ROLE', required=True,
                help='role to attach the policy to (required)'),
            Arg('-p', '--policy-name', metavar='POLICY', required=True,
                help='name of the new policy (required)'),
            Arg('-e', '--effect', choices=('Allow', 'Deny'), required=True,
                help='whether the new policy should Allow or Deny (required)'),
            Arg('-a', '--action', dest='actions', action='append',
                required=True, help='''action(s) the policy should apply to
                (at least one required)'''),
            Arg('-c', '--resource', dest='resources', action='append',
                required=True, help='''resource(s) the policy should apply to
                (at least one required)'''),
            Arg('-o', '--output', action='store_true',
                help='also display the newly-created policy'),
            AS_ACCOUNT]

    def main(self):
        policy = build_iam_policy(self.args['effect'], self.args['resources'],
                                  self.args['actions'])
        policy_doc = json.dumps(policy)
        req = PutRolePolicy.from_other(
            self, RoleName=self.args['role_name'],
            PolicyName=self.args['policy_name'],
            PolicyDocument=policy_doc,
            DelegateAccount=self.params['DelegateAccount'])
        response = req.main()
        response['PolicyDocument'] = policy_doc
        return response

    def print_result(self, result):
        if self.args['output']:
            print result['PolicyDocument']

########NEW FILE########
__FILENAME__ = addroletoinstanceprofile
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class AddRoleToInstanceProfile(IAMRequest):
    DESCRIPTION = 'Add a role to an instance profile'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', required=True,
                help='role to add (required)'),
            Arg('-s', '--instance-profile-name', dest='InstanceProfileName',
                metavar='IPROFILE', required=True,
                help='instance profile to add the role to (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = adduserpolicy
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.putuserpolicy import PutUserPolicy
from euca2ools.util import build_iam_policy


class AddUserPolicy(IAMRequest):
    DESCRIPTION = ('Add a new policy to a user. To add more complex policies '
                   'than this tool supports, see euare-useruploadpolicy.')
    ARGS = [Arg('-u', '--user-name', metavar='USER', required=True,
                help='user to attach the policy to (required)'),
            Arg('-p', '--policy-name', metavar='POLICY', required=True,
                help='name of the new policy (required)'),
            Arg('-e', '--effect', choices=('Allow', 'Deny'), required=True,
                help='whether the new policy should Allow or Deny (required)'),
            Arg('-a', '--action', dest='actions', action='append',
                required=True, help='''action(s) the policy should apply to
                (at least one required)'''),
            Arg('-r', '--resource', dest='resources', action='append',
                required=True, help='''resource(s) the policy should apply to
                (at least one required)'''),
            Arg('-o', '--output', action='store_true',
                help='display the newly-created policy'),
            AS_ACCOUNT]

    def main(self):
        policy = build_iam_policy(self.args['effect'], self.args['resources'],
                                  self.args['actions'])
        policy_doc = json.dumps(policy)
        req = PutUserPolicy.from_other(
            self, UserName=self.args['user_name'],
            PolicyName=self.args['policy_name'], PolicyDocument=policy_doc,
            DelegateAccount=self.params['DelegateAccount'])
        response = req.main()
        response['PolicyDocument'] = policy_doc
        return response

    def print_result(self, result):
        if self.args['output']:
            print result['PolicyDocument']

########NEW FILE########
__FILENAME__ = addusertogroup
# Copyright 2009-2012 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class AddUserToGroup(IAMRequest):
    DESCRIPTION = 'Add a user to a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', required=True,
                help='group to add the user to'),
            Arg('-u', '--user-name', dest='UserName', required=True,
                help='user to add'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = createaccesskey
# Copyright 2009-2012 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class CreateAccessKey(IAMRequest):
    DESCRIPTION = 'Create a new access key for a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', help='''user the new key
                will belong to (default: calling user)'''),
            AS_ACCOUNT]

    def print_result(self, result):
        print result['AccessKey']['AccessKeyId']
        print result['AccessKey']['SecretAccessKey']

########NEW FILE########
__FILENAME__ = createaccount
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class CreateAccount(IAMRequest, TabifyingMixin):
    DESCRIPTION = '[Eucalyptus cloud admin only] Create a new account'
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True,
                help='name of the account to create (required)')]

    def print_result(self, result):
        print self.tabify((result.get('Account', {}).get('AccountName'),
                           result.get('Account', {}).get('AccountId')))

########NEW FILE########
__FILENAME__ = createaccountalias
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class CreateAccountAlias(IAMRequest):
    DESCRIPTION = 'Create an alias for an account, a.k.a. an account name'
    ARGS = [Arg('-a', '--account-alias', dest='AccountAlias', metavar='ALIAS',
                required=True, help='name of the alias to create (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = creategroup
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class CreateGroup(IAMRequest):
    DESCRIPTION = 'Create a new group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True, help='name of the new group (required)'),
            Arg('-p', '--path', dest='Path',
                help='path for the new group (default: "/")'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help="print the new group's ARN and GUID"),
            AS_ACCOUNT]

    def print_result(self, result):
        if self.args['verbose']:
            print result['Group']['Arn']
            print result['Group']['GroupId']

########NEW FILE########
__FILENAME__ = createinstanceprofile
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.addroletoinstanceprofile import \
    AddRoleToInstanceProfile
from euca2ools.commands.iam.createrole import CreateRole


class CreateInstanceProfile(IAMRequest):
    DESCRIPTION = 'Create a new instance profile'
    ARGS = [Arg('-s', '--instance-profile-name', dest='InstanceProfileName',
                metavar='IPROFILE', required=True,
                help='name of the new instance profile (required)'),
            Arg('-p', '--path', dest='Path',
                help='path for the new instance profile (default: "/")'),
            MutuallyExclusiveArgList(
                Arg('-r', '--add-role', dest='role', route_to=None,
                    help='also add a role to the new instance profile'),
                Arg('--create-role', dest='create_role', route_to=None,
                    action='store_true', help='''also create a role with the
                    same name and path and add it to the instance profile''')),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help="print the new instance profile's ARN and GUID"),
            AS_ACCOUNT]

    def postprocess(self, _):
        role_name = None
        if self.args.get('create_role'):
            role_name = self.args['InstanceProfileName']
            req = CreateRole.from_other(
                self, RoleName=role_name, Path=self.args.get('path'),
                service_='ec2.amazonaws.com',
                DelegateAccount=self.args.get('DelegateAccount'))
            req.main()
        elif self.args.get('role'):
            role_name = self.args['role']

        if role_name:
            self.log.info('adding role %s to instance profile %s',
                          self.args['role'], self.args['InstanceProfileName'])
            req = AddRoleToInstanceProfile.from_other(
                self, RoleName=role_name,
                InstanceProfileName=self.args['InstanceProfileName'],
                DelegateAccount=self.args.get('DelegateAccount'))
            req.main()

    def print_result(self, result):
        if self.args.get('verbose'):
            print result.get('InstanceProfile', {}).get('Arn')
            print result.get('InstanceProfile', {}).get('InstanceProfileId')

########NEW FILE########
__FILENAME__ = createloginprofile
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.util import prompt_for_password
from requestbuilder import Arg


class CreateLoginProfile(IAMRequest):
    DESCRIPTION = 'Create a password for the specified user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='name of the user to create a password for (required)'),
            Arg('-p', '--password', dest='Password',
                help='''the new password.  If unspecified, the new password
                        will be read from the console.'''),
            AS_ACCOUNT]

    def configure(self):
        IAMRequest.configure(self)
        if self.args['Password'] is None:
            self.log.info('no password supplied; prompting')
            self.params['Password'] = prompt_for_password()

########NEW FILE########
__FILENAME__ = createrole
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import urllib

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.argtypes import file_contents
from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class CreateRole(IAMRequest):
    DESCRIPTION = 'Create a new role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='name of the new role (required)'),
            Arg('-p', '--path', dest='Path',
                help='path for the new role (default: "/")'),
            MutuallyExclusiveArgList(
                Arg('-f', dest='AssumeRolePolicyDocument', metavar='FILE',
                    type=file_contents,
                    help='file containing the policy for the new role'),
                Arg('-s', '--service_', route_to=None, help='''service to allow
                    access to the role (e.g. ec2.amazonaws.com)'''))
            .required(),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help="print the new role's ARN, GUID, and policy"),
            AS_ACCOUNT]

    def preprocess(self):
        if self.args.get('service_'):
            statement = {'Effect': 'Allow',
                         'Principal': {'Service': [self.args['service_']]},
                         'Action': ['sts:AssumeRole']}
            policy = {'Version': '2008-10-17',
                      'Statement': [statement]}
            self.params['AssumeRolePolicyDocument'] = json.dumps(policy)

    def print_result(self, result):
        if self.args.get('verbose'):
            print result.get('Role', {}).get('Arn')
            print result.get('Role', {}).get('RoleId')
            print urllib.unquote(result.get('Role', {})
                                 .get('AssumeRolePolicyDocument'))

########NEW FILE########
__FILENAME__ = createsigningcertificate
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
import os
from requestbuilder import Arg


class CreateSigningCertificate(IAMRequest):
    DESCRIPTION = '[Eucalyptus only] Create a new signing certificate'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user to create the signing certificate for (required)'),
            Arg('--out', metavar='FILE', route_to=None,
                help='file to write the certificate to (default: stdout)'),
            Arg('--keyout', metavar='FILE', route_to=None,
                help='file to write the private key to (default: stdout)'),
            AS_ACCOUNT]

    def postprocess(self, result):
        if self.args['out']:
            with open(self.args['out'], 'w') as certfile:
                certfile.write(result['Certificate']['CertificateBody'])
        if self.args['keyout']:
            old_umask = os.umask(0o077)
            with open(self.args['keyout'], 'w') as keyfile:
                keyfile.write(result['Certificate']['PrivateKey'])
            os.umask(old_umask)

    def print_result(self, result):
        print result['Certificate']['CertificateId']
        if not self.args['out']:
            print result['Certificate']['CertificateBody']
        if not self.args['keyout']:
            print result['Certificate']['PrivateKey']

########NEW FILE########
__FILENAME__ = createuser
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.addusertogroup import AddUserToGroup
from euca2ools.commands.iam.createaccesskey import CreateAccessKey


class CreateUser(IAMRequest):
    DESCRIPTION = ('Create a new user and optionally add the user to a group '
                   'or generate an access key for the user')
    ARGS = [Arg('-u', '--user-name', dest='UserName', required=True,
                help='name of the new user'),
            Arg('-p', '--path', dest='Path',
                help='path for the new user (default: "/")'),
            Arg('-g', '--group-name', route_to=None,
                help='add the new user to a group'),
            Arg('-k', '--create-accesskey', action='store_true', route_to=None,
                help='''create an access key for the new user and print it to
                        standard out'''),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help="print the new user's ARN and GUID"),
            AS_ACCOUNT]

    def postprocess(self, result):
        if self.args.get('group_name'):
            obj = AddUserToGroup.from_other(
                self, UserName=self.args['UserName'],
                GroupName=self.args['group_name'],
                DelegateAccount=self.params['DelegateAccount'])
            obj.main()
        if self.args.get('create_accesskey'):
            obj = CreateAccessKey.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            key_result = obj.main()
            result.update(key_result)

    def print_result(self, result):
        if self.args['verbose']:
            print result['User']['Arn']
            print result['User']['UserId']
        if 'AccessKey' in result:
            print result['AccessKey']['AccessKeyId']
            print result['AccessKey']['SecretAccessKey']

########NEW FILE########
__FILENAME__ = deactivatemfadevice
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeactivateMFADevice(IAMRequest):
    DESCRIPTION = 'Deactivate an MFA device'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user whose MFA device to deactivate (required)'),
            Arg('-s', '--serial-number', dest='SerialNumber', metavar='SERIAL',
                required=True, help='''serial number of the MFA device to
                                       deactivate (required)'''),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteaccesskey
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteAccessKey(IAMRequest):
    DESCRIPTION = 'Delete an access key'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='user whose key to delete (required)'),
            Arg('-k', '--user-key-id', dest='AccessKeyId', metavar='KEY_ID',
                required=True,
                help='ID of the access key to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteaccount
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from requestbuilder import Arg


class DeleteAccount(IAMRequest):
    DESCRIPTION = '[Eucalyptus cloud admin only] Delete an account'
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True,
                help='name of the account to delete (required)'),
            Arg('-r', '--recursive', dest='Recursive', action='store_const',
                const='true', help='''delete all users, groups, and policies
                                      associated with the account as well''')]

########NEW FILE########
__FILENAME__ = deleteaccountalias
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteAccountAlias(IAMRequest):
    DESCRIPTION = "Delete an account's alias, a.k.a. its account name"
    ARGS = [Arg('-a', '--account-alias', dest='AccountAlias', metavar='ALIAS',
                required=True, help='name of the alias to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteaccountpolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from requestbuilder import Arg


class DeleteAccountPolicy(IAMRequest):
    DESCRIPTION = ('[Eucalyptus cloud admin only] Remove a policy from an '
                   'account')
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True,
                help='account the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to delete (required)')]

########NEW FILE########
__FILENAME__ = deletegroup
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.deletegrouppolicy import DeleteGroupPolicy
from euca2ools.commands.iam.getgroup import GetGroup
from euca2ools.commands.iam.listgrouppolicies import ListGroupPolicies
from euca2ools.commands.iam.removeuserfromgroup import RemoveUserFromGroup


class DeleteGroup(IAMRequest):
    DESCRIPTION = 'Delete a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True, help='name of the group to delete (required)'),
            Arg('-r', '--recursive', action='store_true', route_to=None,
                help='''remove all user memberships and policies associated
                        with the group first'''),
            Arg('-R', '--recursive-euca', dest='IsRecursive',
                action='store_const', const='true', help=argparse.SUPPRESS),
            Arg('-p', '--pretend', action='store_true', route_to=None,
                help='''list the user memberships and policies that would be
                deleted instead of actually deleting them. Implies -r.'''),
            AS_ACCOUNT]

    def main(self):
        if self.args['recursive'] or self.args['pretend']:
            # Figure out what we'd have to delete
            req = GetGroup.from_other(
                self, GroupName=self.args['GroupName'],
                DelegateAccount=self.params['DelegateAccount'])
            members = req.main().get('Users', [])
            req = ListGroupPolicies.from_other(
                self, GroupName=self.args['GroupName'],
                DelegateAccount=self.params['DelegateAccount'])
            policies = req.main().get('PolicyNames', [])
        else:
            # Just in case
            members = []
            policies = []
        if self.args['pretend']:
            return {'members':  [member['Arn'] for member in members],
                    'policies': policies}
        else:
            if self.args['recursive']:
                member_names = [member['UserName'] for member in members]
                req = RemoveUserFromGroup.from_other(
                    self, GroupName=self.args['GroupName'],
                    user_names=member_names,
                    DelegateAccount=self.params['DelegateAccount'])
                req.main()
                for policy in policies:
                    req = DeleteGroupPolicy.from_other(
                        self, GroupName=self.args['GroupName'],
                        PolicyName=policy,
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
            return self.send()

    def print_result(self, result):
        if self.args['pretend']:
            print 'users'
            for arn in result['members']:
                print '\t' + arn
            print 'policies'
            for policy in result['policies']:
                print '\t' + policy

########NEW FILE########
__FILENAME__ = deletegrouppolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteGroupPolicy(IAMRequest):
    DESCRIPTION = 'Remove a policy from a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True,
                help='group the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteinstanceprofile
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.getinstanceprofile import GetInstanceProfile
from euca2ools.commands.iam.removerolefrominstanceprofile import \
    RemoveRoleFromInstanceProfile


class DeleteInstanceProfile(IAMRequest):
    DESCRIPTION = ('Delete an instance profile\n\nThis will break any running '
                   'instances that depend upon access to the deleted instance '
                   'profile.')
    ARGS = [Arg('-s', '--instance-profile-name', dest='InstanceProfileName',
                metavar='IPROFILE', required=True,
                help='name of the instance profile to delete (required)'),
            Arg('-r', '--recursive', action='store_true', route_to=None,
                help='''remove all IAM resources associated with the instance
                profile first'''),
            Arg('-p', '--pretend', action='store_true', route_to=None,
                help='''list the resources that would be deleted instead of
                actually deleting them.  Implies -r.'''),
            AS_ACCOUNT]

    def main(self):
        if self.args.get('recursive') or self.args.get('pretend'):
            # Figure out what we have to delete
            req = GetInstanceProfile.from_other(
                self, InstanceProfileName=self.args['InstanceProfileName'],
                DelegateAccount=self.args.get('DelegateAccount'))
            response = req.main()
            roles = []
            for role in response.get('InstanceProfile', {}).get('Roles') or []:
                roles.append({'arn': role.get('Arn'),
                              'name': role.get('RoleName')})
        else:
            # Just in case
            roles = []
        if self.args.get('pretend'):
            return {'roles': roles}
        else:
            if self.args.get('recursive'):
                for role in roles:
                    req = RemoveRoleFromInstanceProfile.from_other(
                        self, RoleName=role['name'],
                        InstanceProfileName=self.args['InstanceProfileName'],
                        DelegateAccount=self.args.get('DelegateAccount'))
                    req.main()
        return self.send()

    def print_result(self, result):
        if self.args.get('pretend'):
            print 'roles'
            for role in result['roles']:
                print '\t' + role['arn']

########NEW FILE########
__FILENAME__ = deleteloginprofile
# Copyright 2009-2012 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteLoginProfile(IAMRequest):
    DESCRIPTION = "Delete a user's password"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='''name of the user whose password should
                be deleted (required)'''),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleterole
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.deleterolepolicy import DeleteRolePolicy
from euca2ools.commands.iam.listinstanceprofilesforrole import \
    ListInstanceProfilesForRole
from euca2ools.commands.iam.listrolepolicies import ListRolePolicies
from euca2ools.commands.iam.removerolefrominstanceprofile import \
    RemoveRoleFromInstanceProfile


class DeleteRole(IAMRequest):
    DESCRIPTION = 'Delete a role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='name of the role to delete (required)'),
            Arg('-c', '--recursive', action='store_true', route_to=None,
                help='''remove all IAM resources associated with the role
                first'''),
            Arg('-p', '--pretend', action='store_true', route_to=None,
                help='''list the resources that would be deleted instead of
                actually deleting them.  Implies -c.'''),
            AS_ACCOUNT]

    def main(self):
        if self.args.get('recursive') or self.args.get('pretend'):
            # Figure out what we have to delete
            req = ListInstanceProfilesForRole.from_other(
                self, RoleName=self.args['RoleName'],
                DelegateAccount=self.args.get('DelegateAccount'))
            response = req.main()
            instance_profiles = []
            for profile in response.get('InstanceProfiles') or []:
                instance_profiles.append(
                    {'arn': profile.get('Arn'),
                     'name': profile.get('InstanceProfileName')})

            req = ListRolePolicies.from_other(
                self, RoleName=self.args['RoleName'],
                DelegateAccount=self.args.get('DelegateAccount'))
            response = req.main()
            policies = []
            for policy in response.get('PolicyNames') or []:
                policies.append(policy)
        else:
            # Just in case
            instance_profiles = []
            policies = []
        if self.args.get('pretend'):
            return {'instance_profiles': instance_profiles,
                    'policies': policies}
        else:
            if self.args.get('recursive'):
                for profile in instance_profiles:
                    req = RemoveRoleFromInstanceProfile.from_other(
                        self, RoleName=self.args['RoleName'],
                        InstanceProfileName=profile['name'],
                        DelegateAccount=self.args.get('DelegateAccount'))
                    req.main()
                for policy in policies:
                    req = DeleteRolePolicy.from_other(
                        self, RoleName=self.args['RoleName'],
                        PolicyName=policy,
                        DelegateAccount=self.args.get('DelegateAccount'))
                    req.main()
        return self.send()

    def print_result(self, result):
        if self.args.get('pretend'):
            print 'instance profiles'
            for profile in result['instance_profiles']:
                print '\t' + profile['arn']
            print 'policies'
            for policy in result['policies']:
                print '\t' + policy

########NEW FILE########
__FILENAME__ = deleterolepolicy
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteRolePolicy(IAMRequest):
    DESCRIPTION = 'Remove a policy from a role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True,
                help='user the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteservercertificate
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteServerCertificate(IAMRequest):
    DESCRIPTION = 'Delete a server certificate'
    ARGS = [Arg('-s', '--server-certificate-name',
                dest='ServerCertificateName', metavar='CERT', required=True,
                help='name of the server certificate to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deletesigningcertificate
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteSigningCertificate(IAMRequest):
    DESCRIPTION = 'Delete a signing certificate'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user the signing certificate belongs to (required)'),
            Arg('-c', '--certificate-id', dest='CertificateId', metavar='CERT',
                required=True,
                help='ID of the signing certificate to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = deleteuser
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.deleteaccesskey import DeleteAccessKey
from euca2ools.commands.iam.deleteloginprofile import DeleteLoginProfile
from euca2ools.commands.iam.deletesigningcertificate import \
    DeleteSigningCertificate
from euca2ools.commands.iam.deleteuserpolicy import DeleteUserPolicy
from euca2ools.commands.iam.getloginprofile import GetLoginProfile
from euca2ools.commands.iam.listaccesskeys import ListAccessKeys
from euca2ools.commands.iam.listgroupsforuser import ListGroupsForUser
from euca2ools.commands.iam.listsigningcertificates import \
    ListSigningCertificates
from euca2ools.commands.iam.listuserpolicies import ListUserPolicies
from euca2ools.commands.iam.removeuserfromgroup import RemoveUserFromGroup
from euca2ools.exceptions import AWSError


class DeleteUser(IAMRequest):
    DESCRIPTION = 'Delete a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='name of the user to delete (required)'),
            Arg('-r', '--recursive', action='store_true', route_to=None,
                help='''remove all IAM resources associated with the user
                        first'''),
            Arg('-R', '--recursive-euca', dest='IsRecursive',
                action='store_const', const='true', help=argparse.SUPPRESS),
            Arg('-p', '--pretend', action='store_true', route_to=None,
                help='''list the resources that would be deleted instead of
                        actually deleting them. Implies -r.'''),
            AS_ACCOUNT]

    def main(self):
        if self.args['recursive'] or self.args['pretend']:
            # Figure out what we'd have to delete
            req = ListAccessKeys.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            keys = req.main().get('AccessKeyMetadata', [])
            req = ListUserPolicies.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            policies = req.main().get('PolicyNames', [])
            req = ListSigningCertificates.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            certs = req.main().get('Certificates', [])
            req = ListGroupsForUser.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            groups = req.main().get('Groups', [])
            req = GetLoginProfile.from_other(
                self, UserName=self.args['UserName'],
                DelegateAccount=self.params['DelegateAccount'])
            try:
                # This will raise an exception if no login profile is found.
                req.main()
                has_login_profile = True
            except AWSError as err:
                if err.code == 'NoSuchEntity':
                    # It doesn't exist
                    has_login_profile = False
                else:
                    # Something else went wrong; not our problem
                    raise
        else:
            # Just in case
            keys = []
            policies = []
            certs = []
            groups = []
            has_login_profile = False
        if self.args['pretend']:
            return {'keys': keys, 'policies': policies,
                    'certificates': certs, 'groups': groups,
                    'has_login_profile': has_login_profile}
        else:
            if self.args['recursive']:
                for key in keys:
                    req = DeleteAccessKey.from_other(
                        self, UserName=self.args['UserName'],
                        AccessKeyId=key['AccessKeyId'],
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
                for policy in policies:
                    req = DeleteUserPolicy.from_other(
                        self, UserName=self.args['UserName'],
                        PolicyName=policy,
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
                for cert in certs:
                    req = DeleteSigningCertificate.from_other(
                        self, UserName=self.args['UserName'],
                        CertificateId=cert['CertificateId'],
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
                for group in groups:
                    req = RemoveUserFromGroup.from_other(
                        self, user_names=[self.args['UserName']],
                        GroupName=group['GroupName'],
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
                if has_login_profile:
                    req = DeleteLoginProfile.from_other(
                        self, UserName=self.args['UserName'],
                        DelegateAccount=self.params['DelegateAccount'])
                    req.main()
            return self.send()

    def print_result(self, result):
        if self.args['pretend']:
            print 'accesskeys'
            for key in result['keys']:
                print '\t' + key['AccessKeyId']
            print 'policies'
            for policy in result['policies']:
                print '\t' + policy
            print 'certificates'
            for cert in result['certificates']:
                print '\t' + cert['CertificateId']
            print 'groups'
            for group in result['groups']:
                print '\t' + group['Arn']

########NEW FILE########
__FILENAME__ = deleteuserpolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class DeleteUserPolicy(IAMRequest):
    DESCRIPTION = 'Remove a policy from a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to delete (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = enablemfadevice
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class EnableMFADevice(IAMRequest):
    DESCRIPTION = 'Enable an MFA device'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user to enable the MFA device for (required)'),
            Arg('-s', '--serial-number', dest='SerialNumber', metavar='SERIAL',
                required=True,
                help='serial number of the MFA device to activate (required)'),
            Arg('-c1', dest='AuthenticationCode1', metavar='CODE',
                required=True, help='''an authentication code emitted by the
                                       MFA device (required)'''),
            Arg('-c2', dest='AuthenticationCode2', metavar='CODE',
                required=True, help='''a subsequent authentication code emitted
                                       by the MFA device (required)'''),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = getaccountpolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
import json
from requestbuilder import Arg
import urllib


class GetAccountPolicy(IAMRequest):
    DESCRIPTION = "Display an account's policy"
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True,
                help='account the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to show (required)'),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='reformat the policy for easier reading')]

    def print_result(self, result):
        policy_content = urllib.unquote(result['PolicyDocument'])
        if self.args['pretty_print']:
            try:
                policy_json = json.loads(policy_content)
            except ValueError:
                self.log.debug('JSON parse error', exc_info=True)
                raise ValueError(
                    "policy '{0}' does not appear to be valid JSON"
                    .format(self.args['PolicyName']))
            policy_content = json.dumps(policy_json, indent=4)
        print policy_content

########NEW FILE########
__FILENAME__ = getaccountsummary
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class GetAccountSummary(IAMRequest):
    DESCRIPTION = ('Display account-level information about account entity '
                   'usage and IAM quotas')
    PARAMS = [AS_ACCOUNT]
    LIST_TAGS = ['SummaryMap']

    def print_result(self, result):
        for entry in sorted(result.get('SummaryMap', [])):
            print '{0}: {1}'.format(entry.get('key'), entry.get('value'))

########NEW FILE########
__FILENAME__ = getgroup
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class GetGroup(IAMRequest):
    DESCRIPTION = 'List all the users in a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True, help='name of the group to show info about'),
            AS_ACCOUNT]
    LIST_TAGS = ['Users']

    def main(self):
        return PaginatedResponse(self, (None,), ('Users',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        print result['Group']['Arn']
        print '  ', 'users'
        for user in result.get('Users', []):
            print '  ', user['Arn']

########NEW FILE########
__FILENAME__ = getgrouppolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
import json
import urllib


class GetGroupPolicy(IAMRequest):
    DESCRIPTION = "Display a group's policy"
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True,
                help='group the policy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to show (required)'),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='reformat the policy for easier reading'),
            AS_ACCOUNT]

    def print_result(self, result):
        policy_content = urllib.unquote(result['PolicyDocument'])
        if self.args['pretty_print']:
            try:
                policy_json = json.loads(policy_content)
            except ValueError:
                self.log.debug('JSON parse error', exc_info=True)
                raise ValueError(
                    "policy '{0}' does not appear to be valid JSON"
                    .format(self.args['PolicyName']))
            policy_content = json.dumps(policy_json, indent=4)
        print policy_content

########NEW FILE########
__FILENAME__ = getinstanceprofile
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class GetInstanceProfile(IAMRequest):
    DESCRIPTION = "Display an instance profile's ARN and GUID"
    ARGS = [Arg('-s', '--instance-profile-name', dest='InstanceProfileName',
                metavar='IPROFILE', required=True, help='''name of the
                instance profile to show info about (required)'''),
            Arg('-r', dest='show_roles', action='store_true', route_to=None,
                help='''also list the roles associated with the instance
                profile'''),
            AS_ACCOUNT]
    LIST_TAGS = ['Roles']

    def print_result(self, result):
        print result.get('InstanceProfile', {}).get('Arn')
        print result.get('InstanceProfile', {}).get('InstanceProfileId')
        if self.args.get('show_roles'):
            for role in result.get('InstanceProfile', {}).get('Roles') or []:
                print role.get('Arn')

########NEW FILE########
__FILENAME__ = getldapsyncstatus
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from requestbuilder.mixins import TabifyingMixin


class GetLdapSyncStatus(IAMRequest, TabifyingMixin):
    DESCRIPTION = ("[Eucalyptus cloud admin only] Show the status of the "
                   "cloud's LDAP synchronization")

    def print_result(self, result):
        print self.tabify(('SyncEnabled', result.get('SyncEnabled')))
        print self.tabify(('InSync', result.get('InSync')))

########NEW FILE########
__FILENAME__ = getloginprofile
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class GetLoginProfile(IAMRequest):
    DESCRIPTION = 'Verify that a user has a password'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user whose password to verify (required)'),
            Arg('--verbose', action='store_true', route_to=None,
                help="print extra info about the user's password"),
            AS_ACCOUNT]

    def print_result(self, result):
        # If we've managed to get to this point, we already know the user has
        # a login profile.
        user_name = result['LoginProfile'].get('UserName')
        print 'Login Profile Exists for User', user_name
        if self.args['verbose']:
            create_date = result['LoginProfile'].get('CreateDate')
            if create_date:
                print 'Creation date:', create_date
            must_change = result['LoginProfile'].get('MustChangePassword')
            if must_change:
                print 'Must change password:', must_change

########NEW FILE########
__FILENAME__ = getrole
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import urllib

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class GetRole(IAMRequest):
    DESCRIPTION = "Display a role's ARN, GUID, and policy"
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True,
                help='name of the role to show info about (required)'),
            AS_ACCOUNT]

    def print_result(self, result):
        print result.get('Role', {}).get('Arn')
        print result.get('Role', {}).get('RoleId')
        print urllib.unquote(result.get('Role', {})
                             .get('AssumeRolePolicyDocument'))

########NEW FILE########
__FILENAME__ = getrolepolicy
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import urllib

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class GetRolePolicy(IAMRequest):
    DESCRIPTION = "Display a user's policy"
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True,
                help='role the poilcy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to show (required)'),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='reformat the policy for easier reading'),
            AS_ACCOUNT]

    def print_result(self, result):
        policy_content = urllib.unquote(result['PolicyDocument'])
        if self.args['pretty_print']:
            try:
                policy_json = json.loads(policy_content)
            except ValueError:
                self.log.debug('JSON parse error', exc_info=True)
                raise ValueError(
                    "policy '{0}' does not appear to be valid JSON"
                    .format(self.args['PolicyName']))
            policy_content = json.dumps(policy_json, indent=4)
        print policy_content

########NEW FILE########
__FILENAME__ = getservercertificate
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class GetServerCertificate(IAMRequest):
    DESCRIPTION = 'Show the ARN and GUID of a server certificate'
    ARGS = [Arg('-s', '--server-certificate-name',
                dest='ServerCertificateName', metavar='CERT', required=True,
                help='''name of the server certificate to retrieve info about
                        (required)'''),
            AS_ACCOUNT]

    def print_result(self, result):
        metadata = result.get('ServerCertificate', {}) \
                         .get('ServerCertificateMetadata', {})
        print metadata.get('Arn')
        print metadata.get('ServerCertificateId')

########NEW FILE########
__FILENAME__ = getuser
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class GetUser(IAMRequest):
    DESCRIPTION = "Display a user's ARN and GUID"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='''name of the user to show info about (default: current
                        user)'''),
            Arg('--show-extra', dest='ShowExtra', action='store_const',
                const='true', help='also display additional user info'),
            AS_ACCOUNT]

    def print_result(self, result):
        print result['User']['Arn']
        print result['User']['UserId']
        if self.args['ShowExtra'] == 'true':
            for attr in ('CreateDate', 'Enabled', 'RegStatus',
                         'PasswordExpiration'):
                print result['User'].get(attr, '')

########NEW FILE########
__FILENAME__ = getuserinfo
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin


class GetUserInfo(IAMRequest, TabifyingMixin):
    DESCRIPTION = '[Eucalyptus only] Display information about a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='''name of the user to display info for (default: current
                user)'''),
            Arg('-k', '--info-key', dest='InfoKey',
                help='name of the piece of user info to show'),
            AS_ACCOUNT]
    LIST_TAGS = ['Infos']

    def print_result(self, result):
        for info in result.get('Infos', []):
            print self.tabify((info.get('Key'), info.get('Value')))

########NEW FILE########
__FILENAME__ = getuserpolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
import json
from requestbuilder import Arg
import urllib


class GetUserPolicy(IAMRequest):
    DESCRIPTION = "Display a user's policy"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user the poilcy is attached to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy to show (required)'),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='reformat the policy for easier reading'),
            AS_ACCOUNT]

    def print_result(self, result):
        policy_content = urllib.unquote(result['PolicyDocument'])
        if self.args['pretty_print']:
            try:
                policy_json = json.loads(policy_content)
            except ValueError:
                self.log.debug('JSON parse error', exc_info=True)
                raise ValueError(
                    "policy '{0}' does not appear to be valid JSON"
                    .format(self.args['PolicyName']))
            policy_content = json.dumps(policy_json, indent=4)
        print policy_content

########NEW FILE########
__FILENAME__ = listaccesskeys
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListAccessKeys(IAMRequest):
    DESCRIPTION = "List a user's access keys"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='user to list keys for (default: current user)'),
            AS_ACCOUNT]
    LIST_TAGS = ['AccessKeyMetadata']

    def main(self):
        return PaginatedResponse(self, (None,), ('AccessKeyMetadata',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for accesskey in result.get('AccessKeyMetadata', []):
            print accesskey.get('AccessKeyId')
            print accesskey.get('Status')

########NEW FILE########
__FILENAME__ = listaccountaliases
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class ListAccountAliases(IAMRequest):
    DESCRIPTION = "List your account's aliases"
    ARGS = [AS_ACCOUNT]
    LIST_TAGS = ['AccountAliases']

    def print_result(self, result):
        # These are technically allowed to paginate, but I haven't seen
        # accounts with lots of aliases in the wild yet.  If that starts
        # happening, feel free to implement it.
        for alias in result.get('AccountAliases', []):
            print 'Alias:', alias

########NEW FILE########
__FILENAME__ = listaccountpolicies
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from euca2ools.commands.iam.getaccountpolicy import GetAccountPolicy
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListAccountPolicies(IAMRequest):
    DESCRIPTION = ('[Eucalyptus only] List one specific policy or all '
                   'policies attached to an account. If no policies are '
                   'attached to the account, the action still succeeds.')
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True, help='account owning the policies to list'),
            Arg('-p', '--policy-name', metavar='POLICY', route_to=None,
                help='display a specific policy'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help='''display the contents of the resulting policies (in
                        addition to their names)'''),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='''when printing the contents of policies, reformat them
                        for easier reading''')]
    LIST_TAGS = ['PolicyNames']

    def main(self):
        return PaginatedResponse(self, (None,), ('PolicyNames',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        if self.args.get('policy_name'):
            # Look for the specific policy the user asked for
            for policy_name in result.get('PolicyNames', []):
                if policy_name == self.args['policy_name']:
                    if self.args['verbose']:
                        self.print_policy(policy_name)
                    else:
                        print policy_name
                    break
        else:
            for policy_name in result.get('PolicyNames', []):
                print policy_name
                if self.args['verbose']:
                    self.print_policy(policy_name)

    def print_policy(self, policy_name):
        req = GetAccountPolicy(
            service=self.service, AccountName=self.args['AccountName'],
            PolicyName=policy_name, pretty_print=self.args['pretty_print'])
        response = req.main()
        req.print_result(response)

########NEW FILE########
__FILENAME__ = listaccounts
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest
from requestbuilder.mixins import TabifyingMixin


class ListAccounts(IAMRequest, TabifyingMixin):
    DESCRIPTION = ("[Eucalyptus cloud admin only] List all of the cloud's "
                   "accounts")
    LIST_TAGS = ['Accounts']

    def print_result(self, result):
        for account in result.get('Accounts', []):
            print self.tabify((account.get('AccountName'),
                               account.get('AccountId')))

########NEW FILE########
__FILENAME__ = listgrouppolicies
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.getgrouppolicy import GetGroupPolicy


class ListGroupPolicies(IAMRequest):
    DESCRIPTION = ('List one specific policy or all policies attached to a '
                   'group.  If no policies are attached to the group, the '
                   'command still succeeds.')
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True, help='group owning the policies to list'),
            Arg('-p', '--policy-name', metavar='POLICY', route_to=None,
                help='display a specific policy'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help='''display the contents of the resulting policies (in
                        addition to their names)'''),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='''when printing the contents of policies, reformat them
                        for easier reading'''),
            AS_ACCOUNT]
    LIST_TAGS = ['PolicyNames']

    def main(self):
        return PaginatedResponse(self, (None,), ('PolicyNames',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        if self.args.get('policy_name'):
            # Look for the specific policy the user asked for
            for policy_name in result.get('PolicyNames', []):
                if policy_name == self.args['policy_name']:
                    if self.args['verbose']:
                        self.print_policy(policy_name)
                    else:
                        print policy_name
                    break
        else:
            for policy_name in result.get('PolicyNames', []):
                print policy_name
                if self.args['verbose']:
                    self.print_policy(policy_name)

    def print_policy(self, policy_name):
        req = GetGroupPolicy.from_other(
            self, GroupName=self.args['GroupName'], PolicyName=policy_name,
            pretty_print=self.args['pretty_print'],
            DelegateAccount=self.params.get('DelegateAccount'))
        response = req.main()
        req.print_result(response)

########NEW FILE########
__FILENAME__ = listgroups
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListGroups(IAMRequest):
    DESCRIPTION = "List your account's groups"
    ARGS = [Arg('-p', '--path-prefix', dest='PathPrefix', metavar='PATH',
                help='''restrict results to groups whose paths begin with a
                specific prefix'''),
            AS_ACCOUNT]
    LIST_TAGS = ['Groups']

    def main(self):
        return PaginatedResponse(self, (None,), ('Groups',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        print 'groups'
        for group in result.get('Groups', []):
            print '  ', group['Arn']

########NEW FILE########
__FILENAME__ = listgroupsforuser
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListGroupsForUser(IAMRequest):
    DESCRIPTION = 'List all groups a user is a member of'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='user to list membership for (required)'),
            AS_ACCOUNT]
    LIST_TAGS = ['Groups']

    def main(self):
        return PaginatedResponse(self, (None,), ('Groups',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for group in result.get('Groups', []):
            print group['Arn']

########NEW FILE########
__FILENAME__ = listinstanceprofiles
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class ListInstanceProfiles(IAMRequest):
    DESCRIPTION = "List your account's instance profiles"
    ARGS = [Arg('-p', '--path-prefix', dest='PathPrefix', metavar='PREFIX',
                help='''limit results to instance profiles that begin with a
                given path'''),
            AS_ACCOUNT]
    LIST_TAGS = ['InstanceProfiles']

    def main(self):
        return PaginatedResponse(self, (None,), ('InstanceProfiles',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for profile in result.get('InstanceProfiles', []):
            print profile['Arn']

########NEW FILE########
__FILENAME__ = listinstanceprofilesforrole
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class ListInstanceProfilesForRole(IAMRequest):
    DESCRIPTION = 'List all instance profiles that use a role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='role to list membership for (required)'),
            AS_ACCOUNT]
    LIST_TAGS = ['InstanceProfiles']

    def main(self):
        return PaginatedResponse(self, (None,), ('InstanceProfiles',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for profile in result.get('InstanceProfiles', []):
            print profile['Arn']

########NEW FILE########
__FILENAME__ = listmfadevices
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListMFADevices(IAMRequest):
    DESCRIPTION = "List a user's MFA devices"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='user to list MFA devices for (default: current user)'),
            AS_ACCOUNT]
    LIST_TAGS = ['MFADevices']

    def main(self):
        return PaginatedResponse(self, (None,), ('MFADevices',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for device in result.get('MFADevices', []):
            print device['SerialNumber']

########NEW FILE########
__FILENAME__ = listrolepolicies
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.getrolepolicy import GetRolePolicy


class ListRolePolicies(IAMRequest):
    DESCRIPTION = ('List one specific policy or all policies attached to a '
                   'role.  If no policies are attached to the role, the '
                   'action still succeeds.')
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='role owning the policies to list'),
            Arg('-p', '--policy-name', metavar='POLICY', route_to=None,
                help='display a specific policy'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help='''display the contents of the resulting policies (in
                        addition to their names)'''),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='''when printing the contents of policies, reformat them
                        for easier reading'''),
            AS_ACCOUNT]
    LIST_TAGS = ['PolicyNames']

    def main(self):
        return PaginatedResponse(self, (None,), ('PolicyNames',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        if self.args.get('policy_name'):
            # Look for the specific policy the user asked for
            for policy_name in result.get('PolicyNames', []):
                if policy_name == self.args['policy_name']:
                    if self.args['verbose']:
                        self.print_policy(policy_name)
                    else:
                        print policy_name
                    break
        else:
            for policy_name in result.get('PolicyNames', []):
                print policy_name
                if self.args['verbose']:
                    self.print_policy(policy_name)
        # We already take care of pagination
        print 'IsTruncated: false'

    def print_policy(self, policy_name):
        req = GetRolePolicy.from_other(
            self, RoleName=self.args['RoleName'], PolicyName=policy_name,
            pretty_print=self.args['pretty_print'],
            DelegateAccount=self.params.get('DelegateAccount'))
        response = req.main()
        req.print_result(response)

########NEW FILE########
__FILENAME__ = listroles
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class ListRoles(IAMRequest):
    DESCRIPTION = "List your account's roles"
    ARGS = [Arg('-p', '--path-prefix', dest='PathPrefix', metavar='PREFIX',
                help='limit results to roles who begin with a given path'),
            AS_ACCOUNT]
    LIST_TAGS = ['Roles']

    def main(self):
        return PaginatedResponse(self, (None,), ('Roles',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for role in result.get('Roles', []):
            print role['Arn']

########NEW FILE########
__FILENAME__ = listservercertificates
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListServerCertificates(IAMRequest):
    DESCRIPTION = "List your account's server certificates"
    ARGS = [Arg('-p', '--path-prefix', dest='PathPrefix', metavar='PREFIX',
                help='''limit results to server certificates that begin with a
                        given path'''),
            AS_ACCOUNT]
    LIST_TAGS = ['ServerCertificateMetadataList']

    def main(self):
        return PaginatedResponse(self, (None,),
                                 ('ServerCertificateMetadataList',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for cert in result.get('ServerCertificateMetadataList', []):
            print cert['Arn']

########NEW FILE########
__FILENAME__ = listsigningcertificates
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListSigningCertificates(IAMRequest):
    DESCRIPTION = "List a user's signing certificates"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='user to list certificates for (default: current user)'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help="also show certificates' contents"),
            AS_ACCOUNT]
    LIST_TAGS = ['Certificates']

    def main(self):
        return PaginatedResponse(self, (None,), ('Certificates',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncatated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for cert in result.get('Certificates', []):
            print cert['CertificateId']
            if self.args['verbose']:
                print cert['CertificateBody']
            print cert['Status']

########NEW FILE########
__FILENAME__ = listuserpolicies
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.commands.iam.getuserpolicy import GetUserPolicy


class ListUserPolicies(IAMRequest):
    DESCRIPTION = ('List one specific policy or all policies attached to a '
                   'user.  If no policies are attached to the user, the '
                   'action still succeeds.')
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='user owning the policies to list'),
            Arg('-p', '--policy-name', metavar='POLICY', route_to=None,
                help='display a specific policy'),
            Arg('-v', '--verbose', action='store_true', route_to=None,
                help='''display the contents of the resulting policies (in
                        addition to their names)'''),
            Arg('--pretty-print', action='store_true', route_to=None,
                help='''when printing the contents of policies, reformat them
                        for easier reading'''),
            AS_ACCOUNT]
    LIST_TAGS = ['PolicyNames']

    def main(self):
        return PaginatedResponse(self, (None,), ('PolicyNames',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        if self.args.get('policy_name'):
            # Look for the specific policy the user asked for
            for policy_name in result.get('PolicyNames', []):
                if policy_name == self.args['policy_name']:
                    if self.args['verbose']:
                        self.print_policy(policy_name)
                    else:
                        print policy_name
                    break
        else:
            for policy_name in result.get('PolicyNames', []):
                print policy_name
                if self.args['verbose']:
                    self.print_policy(policy_name)
        # We already take care of pagination
        print 'IsTruncated: false'

    def print_policy(self, policy_name):
        req = GetUserPolicy.from_other(
            self, UserName=self.args['UserName'], PolicyName=policy_name,
            pretty_print=self.args['pretty_print'],
            DelegateAccount=self.params.get('DelegateAccount'))
        response = req.main()
        req.print_result(response)

########NEW FILE########
__FILENAME__ = listusers
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg
from requestbuilder.response import PaginatedResponse


class ListUsers(IAMRequest):
    DESCRIPTION = "List your account's users"
    ARGS = [Arg('-p', '--path-prefix', dest='PathPrefix', metavar='PREFIX',
                help='limit results to users who begin with a given path'),
            AS_ACCOUNT]
    LIST_TAGS = ['Users']

    def main(self):
        return PaginatedResponse(self, (None,), ('Users',))

    def prepare_for_page(self, page):
        # Pages are defined by markers
        self.params['Marker'] = page

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return response['Marker']

    def print_result(self, result):
        for user in result.get('Users', []):
            print user['Arn']

########NEW FILE########
__FILENAME__ = putaccountpolicy
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest


class PutAccountPolicy(IAMRequest):
    DESCRIPTION = '[Eucalyptus cloud admin only] Attach a policy to an account'
    ARGS = [Arg('-a', '--account-name', dest='AccountName', metavar='ACCOUNT',
                required=True,
                help='account to attach the policy to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy (required)'),
            MutuallyExclusiveArgList(
                Arg('-o', '--policy-content', dest='PolicyDocument',
                    metavar='POLICY_CONTENT', help='the policy to attach'),
                Arg('-f', '--policy-document', dest='PolicyDocument',
                    metavar='FILE', type=open,
                    help='file containing the policy to attach'))
            .required()]

########NEW FILE########
__FILENAME__ = putgrouppolicy
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class PutGroupPolicy(IAMRequest):
    DESCRIPTION = 'Attach a policy to a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True,
                help='group to attach the policy to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy (required)'),
            MutuallyExclusiveArgList(
                Arg('-o', '--policy-content', dest='PolicyDocument',
                    metavar='POLICY_CONTENT', help='the policy to attach'),
                Arg('-f', '--policy-document', dest='PolicyDocument',
                    metavar='FILE', type=open,
                    help='file containing the policy to attach'))
            .required(),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = putrolepolicy
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class PutRolePolicy(IAMRequest):
    DESCRIPTION = 'Attach a policy to a role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='role to attach the policy to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy (required)'),
            MutuallyExclusiveArgList(
                Arg('-o', '--policy-content', dest='PolicyDocument',
                    metavar='POLICY_CONTENT', help='the policy to attach'),
                Arg('-f', '--policy-document', dest='PolicyDocument',
                    metavar='FILE', type=open,
                    help='file containing the policy to attach'))
            .required(),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = putuserpolicy
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class PutUserPolicy(IAMRequest):
    DESCRIPTION = 'Attach a policy to a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='user to attach the policy to (required)'),
            Arg('-p', '--policy-name', dest='PolicyName', metavar='POLICY',
                required=True, help='name of the policy (required)'),
            MutuallyExclusiveArgList(
                Arg('-o', '--policy-content', dest='PolicyDocument',
                    metavar='POLICY_CONTENT', help='the policy to attach'),
                Arg('-f', '--policy-document', dest='PolicyDocument',
                    metavar='FILE', type=open,
                    help='file containing the policy to attach'))
            .required(),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = removerolefrominstanceprofile
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class RemoveRoleFromInstanceProfile(IAMRequest):
    DESCRIPTION = 'Remove a role from an instance profile'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='the role to remove (required)'),
            Arg('-s', '--instance-profile-name', dest='InstanceProfileName',
                metavar='IPROFILE', required=True,
                help='instance profile to remove the role from (required)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = removeuserfromgroup
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class RemoveUserFromGroup(IAMRequest):
    DESCRIPTION = 'Remove a user from a group'
    ARGS = [Arg('-u', '--user-name', dest='user_names', metavar='USER',
                action='append', route_to=None, required=True,
                help='user to remove from the group (required)'),
            Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True,
                help='group to remove the user from (required)'),
            AS_ACCOUNT]

    def main(self):
        for user in self.args['user_names']:
            self.params['UserName'] = user
            self.send()
        # The response doesn't actually contain anything of interest, so don't
        # bother returning anything
        return None

########NEW FILE########
__FILENAME__ = resyncmfadevice
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class ResyncMFADevice(IAMRequest):
    DESCRIPTION = 'Re-synchronize an MFA device with the server'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='user to re-synchronize the MFA device for (required)'),
            Arg('-s', '--serial-number', dest='SerialNumber', metavar='SERIAL',
                required=True,
                help='serial number of the MFA device (required)'),
            Arg('-c1', dest='AuthenticationCode1', metavar='CODE',
                required=True, help='''an authentication code emitted by the
                                       MFA device (required)'''),
            Arg('-c2', dest='AuthenticationCode2', metavar='CODE',
                required=True, help='''a subsequent authentication code emitted
                                       by the MFA device (required)'''),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updateaccesskey
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateAccessKey(IAMRequest):
    DESCRIPTION = ('Change the status of an access key from Active to '
                   'Inactive, or vice versa')
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='''user owning the access key to update (default: current
                        user)'''),
            Arg('-k', '--user-key-id', dest='AccessKeyId', metavar='KEY_ID',
                required=True,
                help='ID of the access key to update (required)'),
            Arg('-s', '--status', dest='Status', required=True,
                choices=('Active', 'Inactive'),
                help='status to assign to the access key'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updateassumerolepolicy
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.argtypes import file_contents
from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class UpdateAssumeRolePolicy(IAMRequest):
    DESCRIPTION = 'Update the policy that grants an entity to assume a role'
    ARGS = [Arg('-r', '--role-name', dest='RoleName', metavar='ROLE',
                required=True, help='role to update (required)'),
            MutuallyExclusiveArgList(
                Arg('-f', dest='PolicyDocument', metavar='FILE',
                    type=file_contents,
                    help='file containing the policy for the new role'),
                Arg('-s', '--service', route_to=None, help='''service to allow
                    access to the role (e.g. ec2.amazonaws.com)'''))
            .required(),
            Arg('-o', dest='verbose', action='store_true',
                help="also print the role's new policy"),
            AS_ACCOUNT]

    def preprocess(self):
        if self.args.get('service'):
            statement = {'Effect': 'Allow',
                         'Principal': {'Service': [self.args['service']]},
                         'Action': ['sts:AssumeRole']}
            policy = {'Version': '2008-10-17',
                      'Statement': [statement]}
            self.params['PolicyDocument'] = json.dumps(policy)

    def print_result(self, _):
        if self.args.get('verbose'):
            print self.params['PolicyDocument']

########NEW FILE########
__FILENAME__ = updategroup
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateGroup(IAMRequest):
    DESCRIPTION = 'Change the name and/or path of a group'
    ARGS = [Arg('-g', '--group-name', dest='GroupName', metavar='GROUP',
                required=True, help='name of the group to update'),
            Arg('-n', '--new-group-name', dest='NewGroupName', metavar='GROUP',
                help='new name for the group'),
            Arg('-p', '--new-path', dest='NewPath', metavar='PATH',
                help='new path for the group'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updateloginprofile
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from euca2ools.util import prompt_for_password
from requestbuilder import Arg


class UpdateLoginProfile(IAMRequest):
    DESCRIPTION = "Update a user's password"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True,
                help='name of the user to change a password for (required)'),
            Arg('-p', '--password', dest='Password',
                help='''the new password.  If unspecified, the new password
                        will be read from the console.'''),
            AS_ACCOUNT]

    def configure(self):
        IAMRequest.configure(self)
        if self.args['Password'] is None:
            self.log.info('no password supplied; prompting')
            self.params['Password'] = prompt_for_password()

########NEW FILE########
__FILENAME__ = updateservercertificate
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateServerCertificate(IAMRequest):
    DESCRIPTION = 'Change the name and/or path of a server certificate'
    ARGS = [Arg('-s', '--server-certificate-name',
                dest='ServerCertificateName', metavar='CERT', required=True,
                help='name of the server certificate to update'),
            Arg('-n', '--new-server-certificate-name',
                dest='NewServerCertificateName', metavar='CERT',
                help='new name for the server certificate'),
            Arg('-p', '--new-path', dest='NewPath', metavar='PATH',
                help='new path for the server certificate'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updatesigningcertificate
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateSigningCertificate(IAMRequest):
    DESCRIPTION = ('Change the status of a signing certificate from Active to '
                   'Inactive, or vice versa')
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='''user owning the signing certificate to update (default:
                        current user)'''),
            Arg('-c', '--certificate-id', dest='CertificateId', metavar='CERT',
                required=True, help='ID of the signing certificate to update'),
            Arg('-s', '--status', dest='Status', required=True,
                choices=('Active', 'Inactive'),
                help='status to assign to the certificate'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updateuser
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateUser(IAMRequest):
    DESCRIPTION = 'Change the name and/or path of a user'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                required=True, help='name of the user to update'),
            Arg('-n', '--new-user-name', dest='NewUserName', metavar='USER',
                help='new name for the user'),
            Arg('-p', '--new-path', dest='NewPath', metavar='PATH',
                help='new path for the user'),
            Arg('--enabled', dest='Enabled', choices=('true', 'false'),
                help='''[Eucalyptus only] 'true' to enable the user, or 'false'
                        to disable the user'''),
            Arg('--reg-status', dest='RegStatus',
                choices=('REGISTERED', 'APPROVED', 'CONFIRMED'),
                help='''[Eucalyptus only] new registration status. Only
                        CONFIRMED users may access the system.'''),
            Arg('--pwd-expires', dest='PasswordExpiration', metavar='DATETIME',
                help='''[Eucalyptus only] New password expiration date, in
                        ISO8601 format'''),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = updateuserinfo
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT
from requestbuilder import Arg


class UpdateUserInfo(IAMRequest):
    DESCRIPTION = "[Eucalyptus only] Update a user's information"
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='user to update (default: current user)'),
            Arg('-k', '--info-key', dest='InfoKey', metavar='KEY',
                required=True,
                help='name of the info field to set (required)'),
            Arg('-i', '--info-value', dest='InfoValue', metavar='VALUE',
                help='value to set the info field to (omit to delete it)'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = uploadservercertificate
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class UploadServerCertificate(IAMRequest):
    DESCRIPTION = 'Upload a server certificate'
    ARGS = [Arg('-s', '--server-certificate-name', metavar='CERTNAME',
                dest='ServerCertificateName', required=True,
                help='name to give the new server certificate (required)'),
            MutuallyExclusiveArgList(
                Arg('-c', '--certificate-body', dest='CertificateBody',
                    metavar='CERT', help='PEM-encoded certificate'),
                Arg('--certificate-file', dest='CertificateBody',
                    metavar='FILE', type=open,
                    help='file containing the PEM-encoded certificate'))
            .required(),
            MutuallyExclusiveArgList(
                Arg('--private-key', dest='PrivateKey', metavar='KEY',
                    help='PEM-encoded private key'),
                Arg('--private-key-file', dest='PrivateKey', metavar='FILE',
                    type=open,
                    help='file containing the PEM-encoded private key'))
            .required(),
            MutuallyExclusiveArgList(
                Arg('--certificate-chain', dest='CertificateChain',
                    metavar='CHAIN', help='''PEM-encoded certificate chain.
                    This is typically the PEM-encoded certificates of the
                    chain, concatenated together.'''),
                Arg('--certificate-chain-file', dest='CertificateChain',
                    metavar='FILE', help='''file containing the PEM-encoded
                    certificate chain. This is typically the PEM-encoded
                    certificates of the chain, concatenated together.''')),
            Arg('-p', '--path', dest='Path',
                help='path for the new server certificate (default: "/")'),
            AS_ACCOUNT]

########NEW FILE########
__FILENAME__ = uploadsigningcertificate
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.iam import IAMRequest, AS_ACCOUNT


class UploadSigningCertificate(IAMRequest):
    DESCRIPTION = 'Upload a signing certificate'
    ARGS = [Arg('-u', '--user-name', dest='UserName', metavar='USER',
                help='''user the signing certificate is for (default: current
                user)'''),
            MutuallyExclusiveArgList(
                Arg('-c', '--certificate-body', dest='CertificateBody',
                    metavar='CERT', help='contents of the new certificate'),
                Arg('-f', '--certificate-file', dest='CertificateBody',
                    metavar='FILE', type=open,
                    help='file containing the new certificate'))
            .required(),
            AS_ACCOUNT]

    def print_result(self, result):
        print result.get('Certificate', {}).get('CertificateId')

########NEW FILE########
__FILENAME__ = generatekeyfingerprint
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib
import subprocess

from requestbuilder import Arg
from requestbuilder.command import BaseCommand

from euca2ools.commands import Euca2ools


class GenerateKeyFingerprint(BaseCommand):
    DESCRIPTION = ('Show the fingerprint of a private key as it would appear '
                   'in the output of euca-describe-keypairs.\n\nNote that '
                   "this will differ from the key's SSH key fingerprint.")
    SUITE = Euca2ools
    ARGS = [Arg('privkey_filename', metavar='FILE',
                help='file containing the private key (required)')]

    def main(self):
        pkcs8 = subprocess.Popen(
            ('openssl', 'pkcs8', '-in', self.args['privkey_filename'],
             '-nocrypt', '-topk8', '-outform', 'DER'), stdout=subprocess.PIPE)
        privkey = pkcs8.stdout.read()
        fprint = hashlib.sha1(privkey).hexdigest()
        return ':'.join(fprint[i:i+2] for i in range(0, len(fprint), 2))

    def print_result(self, fprint):
        print fprint

########NEW FILE########
__FILENAME__ = argtypes
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse


def cloudwatch_dimension(dim_as_str):
    try:
        name, val = dim_as_str.split('=', 1)
        return {'Name': name, 'Value': val}
    except ValueError:
        raise argparse.ArgumentTypeError('dimension filter "{0}" must have '
                                         'form KEY=VALUE'.format(dim_as_str))

########NEW FILE########
__FILENAME__ = deletealarms
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg


class DeleteAlarms(CloudWatchRequest):
    DESCRIPTION = 'Delete alarms'
    ARGS = [Arg('AlarmNames.member', metavar='ALARM', nargs='+',
                help='names of the alarms to delete'),
            Arg('-f', '--force', action='store_true', route_to=None,
                help=argparse.SUPPRESS)]  # for compatibility

########NEW FILE########
__FILENAME__ = describealarmhistory
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeAlarmHistory(CloudWatchRequest, TabifyingMixin):
    DESCRIPTION = 'Retrieve history for one alarm or all alarms'
    ARGS = [Arg('AlarmName', metavar='ALARM', nargs='?',
                help='limit results to a specific alarm'),
            Arg('--end-date', dest='EndDate', metavar='DATE',
                help='limit results to history before a given point in time'),
            Arg('--history-item-type', dest='HistoryItemType',
                choices=('Action', 'ConfigurationUpdate', 'StateUpdate'),
                help='limit results to specific history item types'),
            Arg('--show-long', action='store_true', route_to=None,
                help='show detailed event data as machine-readable JSON'),
            Arg('--start-date', dest='StartDate', metavar='DATE',
                help='limit results to history after a given point in time')]
    LIST_TAGS = ['AlarmHistoryItems']

    def main(self):
        return PaginatedResponse(self, (None,), ('AlarmHistoryItems',))

    def prepare_for_page(self, page):
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for item in result.get('AlarmHistoryItems', []):
            bits = [item.get('AlarmName'), item.get('Timestamp'),
                    item.get('HistoryItemType'), item.get('HistorySummary')]
            if self.args['show_long']:
                bits.append(item.get('HistoryData'))
            print self.tabify(bits)

########NEW FILE########
__FILENAME__ = describealarms
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeAlarms(CloudWatchRequest, TabifyingMixin):
    DESCRIPTION = 'Describe alarms'
    ARGS = [Arg('AlarmNames.member', metavar='ALARM', nargs='*',
                help='limit results to specific alarms'),
            Arg('--action-prefix', dest='ActionPrefix', metavar='PREFIX',
                help='''limit results to alarms whose actions' ARNs begin with
                a specific string'''),
            Arg('--alarm-name-prefix', dest='AlarmNamePrefix',
                metavar='PREFIX', help='''limit results to alarms whose names
                begin with a specific string'''),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the alarms' info"),
            Arg('--state-value', dest='StateValue',
                choices=('OK', 'ALARM', 'INSUFFICIENT_DATA'),
                help='limit results to alarms in a specific state')]
    LIST_TAGS = ['MetricAlarms', 'AlarmActions', 'Dimensions',
                 'InsufficientDataActions', 'OKActions']

    def main(self):
        return PaginatedResponse(self, (None,), ('MetricAlarms',))

    def prepare_for_page(self, page):
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for alarm in result.get('MetricAlarms', []):
            self.print_alarm(alarm)

########NEW FILE########
__FILENAME__ = describealarmsformetric
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.monitoring import CloudWatchRequest
from euca2ools.commands.monitoring.argtypes import cloudwatch_dimension
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class DescribeAlarmsForMetric(CloudWatchRequest, TabifyingMixin):
    DESCRIPTION = ('Describe alarms for a single metric.\n\nNote that all '
                   "of an alarm's metrics must match exactly to obtain any "
                   'results.')
    ARGS = [Arg('--metric-name', dest='MetricName', metavar='METRIC',
                required=True, help='name of the metric (required)'),
            Arg('--namespace', dest='Namespace', metavar='NAMESPACE',
                required=True, help='namespace of the metric (required)'),
            # --alarm-description is supported by the tool, but not the service
            Arg('--alarm-description', route_to=None, help=argparse.SUPPRESS),
            Arg('--dimensions', dest='Dimensions.member',
                metavar='KEY1=VALUE1,KEY2=VALUE2,...',
                type=delimited_list(',', item_type=cloudwatch_dimension),
                help='dimensions of the metric'),
            Arg('--period', dest='Period', metavar='SECONDS',
                help='period over which statistics are applied'),
            Arg('--show-long', action='store_true', route_to=None,
                help="show all of the alarms' info"),
            Arg('--statistic', dest='Statistic', choices=('Average', 'Maximum',
                'Minimum', 'SampleCount', 'Sum'),
                help='statistic of the metric on which to trigger alarms'),
            Arg('--unit', dest='Unit',
                help='unit of measurement for statistics')]
    LIST_TAGS = ['MetricAlarms', 'AlarmActions', 'Dimensions',
                 'InsufficientDataActions', 'OKActions']

    def main(self):
        return PaginatedResponse(self, (None,), ('MetricAlarms',))

    def prepare_for_page(self, page):
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        for alarm in result.get('MetricAlarms', []):
            self.print_alarm(alarm)

########NEW FILE########
__FILENAME__ = disablealarmactions
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg


class DisableAlarmActions(CloudWatchRequest):
    DESCRIPTION = 'Disable all actions for one or more alarms'
    ARGS = [Arg('AlarmNames.member', metavar='ALARM', nargs='+',
                help='names of the alarms to disable actions for')]

########NEW FILE########
__FILENAME__ = enablealarmactions
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg


class EnableAlarmActions(CloudWatchRequest):
    DESCRIPTION = 'Enable all actions for one or more alarms'
    ARGS = [Arg('AlarmNames.member', metavar='ALARM', nargs='+',
                help='names of the alarms to enable actions for')]

########NEW FILE########
__FILENAME__ = getmetricstatistics
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.monitoring import CloudWatchRequest
from euca2ools.commands.monitoring.argtypes import cloudwatch_dimension
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class GetMetricStatistics(CloudWatchRequest, TabifyingMixin):
    DESCRIPTION = "Show a metric's statistics"
    ARGS = [Arg('MetricName', metavar='METRIC',
                help='name of the metric to get statistics for (required)'),
            Arg('-n', '--namespace', dest='Namespace', required=True,
                help="the metric's namespace (required)"),
            Arg('-s', '--statistics', dest='Statistics.member', required=True,
                metavar='STAT1,STAT2,...', type=delimited_list(','),
                help='the metric statistics to show (at least 1 required)'),
            Arg('--dimensions', dest='Dimensions.member',
                metavar='KEY1=VALUE1,KEY2=VALUE2,...',
                type=delimited_list(',', item_type=cloudwatch_dimension),
                help='the dimensions of the metric to show'),
            Arg('--start-time', dest='StartTime',
                metavar='YYYY-MM-DDThh:mm:ssZ', help='''earliest time to
                retrieve data points for (default: one hour ago)'''),
            Arg('--end-time', dest='EndTime',
                metavar='YYYY-MM-DDThh:mm:ssZ', help='''latest time to retrieve
                data points for (default: now)'''),
            Arg('--period', dest='Period', metavar='SECONDS', type=int,
                help='''granularity of the returned data points (must be a
                multiple of 60)'''),
            Arg('--unit', dest='Unit', help='unit the metric is reported in')]
    LIST_TAGS = ['Datapoints']

    # noinspection PyExceptionInherit
    def configure(self):
        CloudWatchRequest.configure(self)
        if self.args.get('period'):
            if self.args['period'] <= 0:
                raise ArgumentError(
                    'argument --period: value must be positive')
            elif self.args['period'] % 60 != 0:
                raise ArgumentError(
                    'argument --period: value must be a multiple of 60')

    def main(self):
        now = datetime.datetime.utcnow()
        then = now - datetime.timedelta(hours=1)
        if not self.args.get('StartTime'):
            self.params['StartTime'] = then.strftime('%Y-%m-%dT%H:%M:%SZ')
        if not self.args.get('EndTime'):
            self.params['EndTime'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')

        return PaginatedResponse(self, (None,), ('Datapoints',))

    def prepare_for_page(self, page):
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        points = []
        for point in result.get('Datapoints', []):
            timestamp = point.get('Timestamp', '')
            try:
                parsed = datetime.datetime.strptime(timestamp,
                                                    '%Y-%m-%dT%H:%M:%SZ')
                timestamp = parsed.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                # We'll just print it verbatim
                pass
            points.append((timestamp, point.get('SampleCount'),
                           point.get('Average'), point.get('Sum'),
                           point.get('Minimum'), point.get('Maximum'),
                           point.get('Unit')))
        for point in sorted(points):
            print self.tabify(point)

########NEW FILE########
__FILENAME__ = listmetrics
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.monitoring import CloudWatchRequest
from euca2ools.commands.monitoring.argtypes import cloudwatch_dimension
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse


class ListMetrics(CloudWatchRequest, TabifyingMixin):
    DESCRIPTION = 'Show a list of monitoring metrics'
    ARGS = [Arg('-d', '--dimensions', dest='Dimensions.member',
                metavar='KEY1=VALUE1,KEY2=VALUE2,...',
                type=delimited_list(',', item_type=cloudwatch_dimension),
                help='limit results to metrics with specific dimensions'),
            Arg('-m', '--metric-name', dest='MetricName', metavar='METRIC',
                help='limit results to a specific metric'),
            Arg('-n', '--namespace', dest='Namespace', metavar='NAMESPACE',
                help='limit results to metrics in a specific namespace')]
    LIST_TAGS = ['Metrics', 'Dimensions']

    def main(self):
        return PaginatedResponse(self, (None,), ('Metrics',))

    def prepare_for_page(self, page):
        self.params['NextToken'] = page

    def get_next_page(self, response):
        return response.get('NextToken') or None

    def print_result(self, result):
        out_lines = []
        for metric in sorted(result.get('Metrics', [])):
            if len(metric.get('Dimensions', [])) > 0:
                formatted_dims = ['{0}={1}'.format(dimension.get('Name'),
                                                   dimension.get('Value'))
                                  for dimension in metric['Dimensions']]
                out_lines.append((metric.get('MetricName'),
                                  metric.get('Namespace'),
                                  '{{{0}}}'.format(','.join(formatted_dims))))
            else:
                out_lines.append((metric.get('MetricName'),
                                  metric.get('Namespace'), None))
        for out_line in sorted(out_lines):
            print self.tabify(out_line)

########NEW FILE########
__FILENAME__ = putmetricalarm
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.monitoring import CloudWatchRequest
from euca2ools.commands.monitoring.argtypes import cloudwatch_dimension
from requestbuilder import Arg


class PutMetricAlarm(CloudWatchRequest):
    DESCRIPTION = 'Create or update an alarm'
    ARGS = [Arg('AlarmName', metavar='ALARM',
                help='name of the alarm (required)'),
            Arg('--comparison-operator', dest='ComparisonOperator',
                choices=('GreaterThanOrEqualToThreshold',
                         'GreaterThanThreshold', 'LessThanThreshold',
                         'LessThanOrEqualToThreshold'), required=True,
                help='''arithmetic operator with which the comparison with the
                threshold will be made (required)'''),
            Arg('--evaluation-periods', dest='EvaluationPeriods', type=int,
                metavar='COUNT', required=True, help='''number of consecutive
                periods for which the value of the metric needs to be compared
                to the threshold (required)'''),
            Arg('--metric-name', dest='MetricName', metavar='METRIC',
                required=True,
                help="name for the alarm's associated metric (required)"),
            Arg('--namespace', dest='Namespace', metavar='NAMESPACE',
                required=True,
                help="namespace for the alarm's associated metric (required)"),
            Arg('--period', dest='Period', metavar='SECONDS', type=int,
                required=True, help='''period over which the specified
                statistic is applied (required)'''),
            Arg('--statistic', dest='Statistic', choices=('Average', 'Maximum',
                'Minimum', 'SampleCount', 'Sum'), required=True,
                help='statistic on which to alarm (required)'),
            Arg('--threshold', dest='Threshold', metavar='FLOAT', type=float,
                required=True,
                help='value to compare the statistic against (required)'),
            Arg('--actions-enabled', dest='ActionsEnabled',
                choices=('true', 'false'), help='''whether this alarm's actions
                should be executed when it changes state'''),
            Arg('--alarm-actions', dest='AlarmActions.member',
                metavar='ARN1,ARN2,...', type=delimited_list(','),
                help='''ARNs of SNS topics to publish to when the alarm changes
                to the ALARM state'''),
            Arg('--alarm-description', dest='AlarmDescription',
                metavar='DESCRIPTION', help='description of the alarm'),
            Arg('-d', '--dimensions', dest='Dimensions.member',
                metavar='KEY1=VALUE1,KEY2=VALUE2,...',
                type=delimited_list(',', item_type=cloudwatch_dimension),
                help="dimensions for the alarm's associated metric"),
            Arg('--insufficient-data-actions', metavar='ARN1,ARN2,...',
                dest='InsufficientDataActions.member',
                type=delimited_list(','), help='''ARNs of SNS topics to publish
                to when the alarm changes to the INSUFFICIENT_DATA state'''),
            Arg('--ok-actions', dest='OKActions.member',
                metavar='ARN1,ARN2,...', type=delimited_list(','),
                help='''ARNs of SNS topics to publish to when the alarm changes
                to the OK state'''),
            Arg('--unit', dest='Unit',
                help="unit for the alarm's associated metric")]

########NEW FILE########
__FILENAME__ = putmetricdata
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg, MutuallyExclusiveArgList

from euca2ools.commands.argtypes import delimited_list
from euca2ools.commands.monitoring import CloudWatchRequest
from euca2ools.commands.monitoring.argtypes import cloudwatch_dimension


def _statistic_set(set_as_str):
    pairs = {}
    for pair in set_as_str.split(','):
        try:
            key, val = pair.split('=')
        except ValueError:
            raise argparse.ArgumentTypeError(
                'statistic set must have format KEY1=VALUE1,...')
        try:
            pairs[key] = float(val)
        except ValueError:
            raise argparse.ArgumentTypeError('value "{0}" must be numeric'
                                             .format(val))
    for field in ('Maximum', 'Minimum', 'SampleCount', 'Sum'):
        if field not in pairs:
            raise argparse.ArgumentTypeError(
                'value for statistic "{0}" is required'.format(field))
    return pairs


class PutMetricData(CloudWatchRequest):
    DESCRIPTION = 'Add data points or statistics to a metric'
    ARGS = [Arg('-m', '--metric-name', dest='MetricData.member.1.MetricName',
                metavar='METRIC', required=True,
                help='name of the metric to add data points to (required)'),
            Arg('-n', '--namespace', dest='Namespace', required=True,
                help="the metric's namespace (required)"),
            MutuallyExclusiveArgList(
                Arg('-v', '--value', dest='MetricData.member.1.Value',
                    metavar='FLOAT', type=float,
                    help='data value for the metric'),
                Arg('-s', '--statistic-values', '--statisticValues',
                    dest='MetricData.member.1.StatisticValues',
                    metavar=('Maximum=FLOAT,Minimum=FLOAT,SampleCount=FLOAT,'
                             'Sum=FLOAT'), type=_statistic_set,
                    help='''statistic values for the metric.  Maximum, Minimum,
                    SampleCount, and Sum values are all required.'''))
            .required(),
            Arg('-d', '--dimensions', dest='Dimensions.member',
                metavar='KEY1=VALUE1,KEY2=VALUE2,...',
                type=delimited_list(',', item_type=cloudwatch_dimension),
                help='the dimensions of the metric to add data points to'),
            Arg('-t', '--timestamp', dest='MetricData.member.1.Timestamp',
                metavar='YYYY-MM-DDThh:mm:ssZ',
                help='timestamp of the data point'),
            Arg('-u', '--unit', dest='MetricData.member.1.Unit',
                metavar='UNIT', help='unit the metric is being reported in')]

########NEW FILE########
__FILENAME__ = setalarmstate
# Copyright 2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.monitoring import CloudWatchRequest
from requestbuilder import Arg


class SetAlarmState(CloudWatchRequest):
    DESCRIPTION = 'Temporarily set the state of an alarm'
    ARGS = [Arg('AlarmName', metavar='ALARM',
                help='name of the alarm to update (required)'),
            Arg('--state-value', dest='StateValue', required=True,
                choices=('ALARM', 'INSUFFICIENT_DATA', 'OK'),
                help='state to set the alarm to (required)'),
            Arg('--state-reason', dest='StateReason', metavar='REASON',
                required=True, help='''human-readable reason why the alarm was
                set to this state (required)'''),
            Arg('--state-reason-data', dest='StateReasonData', metavar='JSON',
                help='''JSON-formatted reason why the alarm was set to this
                state''')]

########NEW FILE########
__FILENAME__ = checkbucket
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg

from euca2ools.commands.s3 import S3Request


class CheckBucket(S3Request):
    DESCRIPTION = 'Return successfully if a bucket exists'
    ARGS = [Arg('bucket', route_to=None, help='name of the bucket to check')]
    METHOD = 'HEAD'

    def preprocess(self):
        self.path = self.args['bucket']

########NEW FILE########
__FILENAME__ = createbucket
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import xml.etree.ElementTree as ET

from requestbuilder import Arg

from euca2ools.commands.s3 import S3Request, validate_generic_bucket_name


class CreateBucket(S3Request):
    DESCRIPTION = 'Create a new bucket'
    ARGS = [Arg('bucket', route_to=None, help='name of the new bucket'),
            Arg('--location', route_to=None,
                help='''location constraint to configure the bucket with
                (default: inferred from s3-location-constraint in
                configuration, or otherwise none)''')]

    def configure(self):
        S3Request.configure(self)
        validate_generic_bucket_name(self.args['bucket'])

    def preprocess(self):
        self.method = 'PUT'
        self.path = self.args['bucket']
        cb_config = ET.Element('CreateBucketConfiguration')
        cb_config.set('xmlns', 'http://doc.s3.amazonaws.com/2006-03-01')
        lconstraint = (self.args.get('location') or
                       self.config.get_region_option('s3-location-constraint'))
        if lconstraint:
            cb_lconstraint = ET.SubElement(cb_config, 'LocationConstraint')
            cb_lconstraint.text = lconstraint
        if len(cb_config.getchildren()):
            cb_xml = ET.tostring(cb_config)
            self.log.debug('bucket configuration: %s', cb_xml)
            self.body = cb_xml

########NEW FILE########
__FILENAME__ = deletebucket
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.s3 import (S3Request,
                                   validate_generic_bucket_name)
from requestbuilder import Arg


class DeleteBucket(S3Request):
    DESCRIPTION = 'Delete a bucket'
    ARGS = [Arg('bucket', route_to=None, help='name of the bucket to delete')]

    def configure(self):
        S3Request.configure(self)
        validate_generic_bucket_name(self.args['bucket'])

    def preprocess(self):
        self.method = 'DELETE'
        self.path = self.args['bucket']

########NEW FILE########
__FILENAME__ = deleteobject
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.s3 import S3Request
from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError


class DeleteObject(S3Request):
    DESCRIPTION = 'Delete an object from the server'
    ARGS = [Arg('path', metavar='BUCKET/KEY', route_to=None)]
    METHOD = 'DELETE'

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)
        if '/' not in self.args['path']:
            raise ArgumentError("path '{0}' must include a key name"
                                .format(self.args['path']))

    def preprocess(self):
        self.path = self.args['path']

########NEW FILE########
__FILENAME__ = getobject
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import hashlib
import os.path
import sys

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.s3 import S3Request
import euca2ools.bundle.pipes


class GetObject(S3Request, FileTransferProgressBarMixin):
    DESCRIPTION = 'Retrieve objects from the server'
    ARGS = [Arg('source', metavar='BUCKET/KEY', route_to=None,
                help='the object to download (required)'),
            Arg('-o', dest='dest', metavar='PATH', route_to=None,
                default='.', help='''where to download to.  If this names a
                directory the object will be written to a file inside of that
                directory.  If this is is "-" the object will be written to
                stdout.  Otherwise it will be written to a file with the name
                given.  (default:  current directory)''')]

    def configure(self):
        S3Request.configure(self)

        bucket, _, key = self.args['source'].partition('/')
        if not bucket:
            raise ArgumentError('source must contain a bucket name')
        if not key:
            raise ArgumentError('source must contain a key name')

        if isinstance(self.args.get('dest'), basestring):
            # If it is not a string we assume it is a file-like object
            if self.args['dest'] == '-':
                self.args['dest'] = sys.stdout
            elif os.path.isdir(self.args['dest']):
                basename = os.path.basename(key)
                if not basename:
                    raise ArgumentError("specify a complete file path with -o "
                                        "to download objects that end in '/'")
                dest_path = os.path.join(self.args['dest'], basename)
                self.args['dest'] = open(dest_path, 'w')
            else:
                self.args['dest'] = open(self.args['dest'], 'w')

    def preprocess(self):
        self.path = self.args['source']

    def main(self):
        # Note that this method does not close self.args['dest']
        self.preprocess()
        bytes_written = 0
        md5_digest = hashlib.md5()
        sha_digest = hashlib.sha1()
        response = self.send()
        content_length = response.headers.get('Content-Length')
        if content_length:
            pbar = self.get_progressbar(label=self.args['source'],
                                        maxval=int(content_length))
        else:
            pbar = self.get_progressbar(label=self.args['source'])
        pbar.start()
        for chunk in response.iter_content(chunk_size=euca2ools.BUFSIZE):
            self.args['dest'].write(chunk)
            bytes_written += len(chunk)
            md5_digest.update(chunk)
            sha_digest.update(chunk)
            if pbar is not None:
                pbar.update(bytes_written)
        self.args['dest'].flush()
        pbar.finish()

        # Integrity checks
        if content_length and bytes_written != int(content_length):
            self.log.error('rejecting download due to Content-Length size '
                           'mismatch (expected: %i, actual: %i)',
                           content_length, bytes_written)
            raise RuntimeError('downloaded file appears to be corrupt '
                               '(expected size: {0}, actual: {1})'
                               .format(content_length, bytes_written))
        etag = response.headers.get('ETag', '').lower().strip('"')
        if (len(etag) == 32 and
                all(char in '0123456789abcdef' for char in etag)):
            # It looks like an MD5 hash
            if md5_digest.hexdigest() != etag:
                self.log.error('rejecting download due to ETag MD5 mismatch '
                               '(expected: %s, actual: %s)',
                               etag, md5_digest.hexdigest())
                raise RuntimeError('downloaded file appears to be corrupt '
                                   '(expected MD5: {0}, actual: {1})'
                                   .format(etag, md5_digest.hexdigest()))

        return {self.args['source']: {'md5': md5_digest.hexdigest(),
                                      'sha1': sha_digest.hexdigest(),
                                      'size': bytes_written}}

########NEW FILE########
__FILENAME__ = headobject
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.s3 import S3Request


class HeadObject(S3Request):
    DESCRIPTION = 'Retrieve info about an object from the server'
    ARGS = [Arg('path', metavar='BUCKET/KEY', route_to=None,
                help='the object to retrieve info for (required)')]
    METHOD = 'HEAD'

    def configure(self):
        S3Request.configure(self)

        bucket, _, key = self.args['path'].partition('/')
        if not bucket:
            raise ArgumentError('path must contain a bucket name')
        if not key:
            raise ArgumentError('path must contain a key name')

    def preprocess(self):
        self.path = self.args['path']

########NEW FILE########
__FILENAME__ = listallmybuckets
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from euca2ools.commands.s3 import S3Request
from requestbuilder import Arg
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.xmlparse import parse_listdelimited_aws_xml


class ListAllMyBuckets(S3Request, TabifyingMixin):
    DESCRIPTION = 'List all buckets owned by your account'
    ARGS = [Arg('-l', dest='long_output', action='store_true', route_to=None,
                help='''list in long format, with creation dates and owner
                info'''),
            Arg('-n', dest='numeric_output', action='store_true',
                route_to=None, help='''display account IDs numerically in long
                (-l) output.  This option turns on the -l option.''')]

    def configure(self):
        S3Request.configure(self)
        if self.args['numeric_output']:
            self.args['long_output'] = True

    def preprocess(self):
        self.method = 'GET'
        self.path = ''

    def parse_response(self, response):
        response_dict = self.log_and_parse_response(
            response, parse_listdelimited_aws_xml, list_tags=('Buckets',))
        return response_dict['ListAllMyBucketsResult']

    def print_result(self, result):
        if self.args['numeric_output'] or 'DisplayName' not in result['Owner']:
            owner = result.get('Owner', {}).get('ID')
        else:
            owner = result.get('Owner', {}).get('DisplayName')

        for bucket in result.get('Buckets', []):
            if self.args['long_output']:
                print self.tabify((owner, bucket.get('CreationDate'),
                                   bucket.get('Name')))
            else:
                print bucket.get('Name')

########NEW FILE########
__FILENAME__ = listbucket
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError
from requestbuilder.mixins import TabifyingMixin
from requestbuilder.response import PaginatedResponse
from requestbuilder.xmlparse import parse_aws_xml

from euca2ools.commands.s3 import S3Request, validate_generic_bucket_name


class ListBucket(S3Request, TabifyingMixin):
    DESCRIPTION = 'List keys in one or more buckets'
    ARGS = [Arg('paths', metavar='BUCKET[/KEY]', nargs='+', route_to=None),
            Arg('--max-keys-per-request', dest='max-keys', type=int,
                default=argparse.SUPPRESS, help=argparse.SUPPRESS)]

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)
        for path in self.args['paths']:
            if path.startswith('/'):
                raise ArgumentError((
                    'argument \'{0}\' must not start with '
                    '"/"; format is BUCKET[/KEY]').format(path))
            bucket = path.split('/', 1)[0]
            try:
                validate_generic_bucket_name(bucket)
            except ValueError as err:
                raise ArgumentError(
                    'bucket "{0}": {1}'.format(bucket, err.message))

    def main(self):
        self.method = 'GET'
        pages = [(path, {}) for path in self.args['paths']]
        return PaginatedResponse(self, pages, ('Contents',))

    def get_next_page(self, response):
        if response.get('IsTruncated') == 'true':
            return self.path, {'marker': response['Contents'][-1]['Key']}

    def prepare_for_page(self, page):
        bucket, _, prefix = page[0].partition('/')
        markers = page[1]
        self.path = bucket
        if prefix:
            self.params['prefix'] = prefix
        elif 'prefix' in self.params:
            del self.params['prefix']
        if markers is not None and markers.get('marker'):
            self.params['marker'] = markers['marker']
        elif 'marker' in self.params:
            del self.params['marker']

    def parse_response(self, response):
        response_dict = self.log_and_parse_response(
            response, parse_aws_xml,
            list_item_tags=('Contents', 'CommonPrefixes'))
        return response_dict['ListBucketResult']

    def print_result(self, result):
        for obj in result.get('Contents', []):
            print obj.get('Key')

########NEW FILE########
__FILENAME__ = postobject
# Copyright 2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import base64
import sys

from requestbuilder import Arg, MutuallyExclusiveArgList
from requestbuilder.exceptions import ArgumentError

from euca2ools.commands.argtypes import b64encoded_file_contents
from euca2ools.commands.s3 import S3Request


class PostObject(S3Request):
    DESCRIPTION = ('Upload an object to the server using an upload policy\n\n'
                   'Note that uploading a large file to a region other than '
                   'the one the bucket is may result in "Broken pipe" errors '
                   'or other connection problems that this program cannot '
                   'detect.')
    AUTH_CLASS = None
    ARGS = [Arg('source', metavar='FILE', route_to=None,
                help='file to upload (required)'),
            Arg('dest', metavar='BUCKET/KEY', route_to=None,
                help='bucket and key name to upload the object to (required)'),
            MutuallyExclusiveArgList(
                Arg('--policy', dest='Policy', metavar='POLICY',
                    type=base64.b64encode,
                    help='upload policy to use for authorization'),
                Arg('--policy-file', dest='Policy', metavar='FILE',
                    type=b64encoded_file_contents, help='''file containing the
                    upload policy to use for authorization'''))
            .required(),
            Arg('--policy-signature', dest='Signature',
                help='signature for the upload policy (required)'),
            Arg('-I', '--access-key-id', dest='AWSAccessKeyId', required=True,
                metavar='KEY_ID', help='''ID of the access key that signed the
                'upload policy (required)'''),
            Arg('--acl', default=argparse.SUPPRESS, choices=(
                'private', 'public-read', 'public-read-write',
                'authenticated-read', 'bucket-owner-read',
                'bucket-owner-full-control', 'aws-exec-read',
                'ec2-bundle-read'), help='''the ACL the object should have
                once uploaded.  Take care to ensure this satisfies any
                restrictions the upload policy may contain.'''),
            Arg('--mime-type', dest='Content-Type', default=argparse.SUPPRESS,
                help='MIME type for the file being uploaded')]
    METHOD = 'POST'

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)

        if self.args['source'] == '-':
            self.files['file'] = sys.stdin
        elif isinstance(self.args['source'], basestring):
            self.files['file'] = open(self.args['source'])
        else:
            self.files['file'] = self.args['source']
        bucket, _, key = self.args['dest'].partition('/')
        if not bucket:
            raise ArgumentError('destination bucket name must be non-empty')
        if not key:
            raise ArgumentError('destination key name must be non-empty')

    # noinspection PyExceptionInherit
    def preprocess(self):
        # FIXME:  This should really stream the contents of the source rather
        # than reading it all into memory at once, but at the moment doing so
        # would require me to write a multipart MIME encoder that supports
        # both streaming and file rewinding.  Patches that do that are very
        # welcome.
        #
        # FIXME:  While you're in there, would you mind adding progress bar
        # support?  8^)
        self.path, _, self.params['key'] = self.args['dest'].partition('/')
        self.body = self.params
        self.params = None

########NEW FILE########
__FILENAME__ = putobject
# Copyright 2013-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import hashlib
import socket
import sys
import threading
import time

from requestbuilder import Arg
from requestbuilder.exceptions import ArgumentError, ClientError
from requestbuilder.mixins import FileTransferProgressBarMixin

from euca2ools.commands.s3 import S3Request
import euca2ools.util


class PutObject(S3Request, FileTransferProgressBarMixin):
    DESCRIPTION = ('Upload an object to the server\n\nNote that uploading a '
                   'large file to a region other than the one the bucket is '
                   'may result in "Broken pipe" errors or other connection '
                   'problems that this program cannot detect.')
    ARGS = [Arg('source', metavar='FILE', route_to=None,
                help='file to upload (required)'),
            Arg('dest', metavar='BUCKET/KEY', route_to=None,
                help='bucket and key name to upload the object to (required)'),
            Arg('--size', type=int, route_to=None, help='''the number of
                bytes to upload (required when reading from stdin)'''),
            Arg('--acl', route_to=None, choices=(
                'private', 'public-read', 'public-read-write',
                'authenticated-read', 'bucket-owner-read',
                'bucket-owner-full-control', 'aws-exec-read')),
            Arg('--mime-type', route_to=None,
                help='MIME type for the file being uploaded'),
            Arg('--retry', dest='retries', action='store_const', const=5,
                default=0, route_to=None,
                help='retry interrupted uploads up to 5 times'),
            Arg('--progressbar-label', help=argparse.SUPPRESS)]
    METHOD = 'PUT'

    def __init__(self, **kwargs):
        S3Request.__init__(self, **kwargs)
        self.last_upload_error = None
        self._lock = threading.Lock()

    # noinspection PyExceptionInherit
    def configure(self):
        S3Request.configure(self)
        if self.args['source'] == '-':
            if self.args.get('size') is None:
                raise ArgumentError(
                    "argument --size is required when uploading stdin")
            source = _FileObjectExtent(sys.stdin, self.args['size'])
        elif isinstance(self.args['source'], basestring):
            source = _FileObjectExtent.from_filename(
                self.args['source'], size=self.args.get('size'))
        else:
            if self.args.get('size') is None:
                raise ArgumentError(
                    "argument --size is required when uploading a file object")
            source = _FileObjectExtent(self.args['source'], self.args['size'])
        self.args['source'] = source
        bucket, _, key = self.args['dest'].partition('/')
        if not bucket:
            raise ArgumentError('destination bucket name must be non-empty')
        if not key:
            raise ArgumentError('destination key name must be non-empty')

    def preprocess(self):
        self.path = self.args['dest']
        if self.args.get('acl'):
            self.headers['x-amz-acl'] = self.args['acl']
        if self.args.get('mime_type'):
            self.headers['Content-Type'] = self.args['mime_type']

    # noinspection PyExceptionInherit
    def main(self):
        self.preprocess()
        source = self.args['source']
        self.headers['Content-Length'] = source.size

        # We do the upload in another thread so the main thread can show a
        # progress bar.
        upload_thread = threading.Thread(
            target=self.try_send, args=(source,),
            kwargs={'retries_left': self.args.get('retries') or 0})
        # The upload thread is daemonic so ^C will kill the program more
        # cleanly.
        upload_thread.daemon = True
        upload_thread.start()
        pbar_label = self.args.get('progressbar_label') or source.filename
        pbar = self.get_progressbar(label=pbar_label, maxval=source.size)
        pbar.start()
        while upload_thread.is_alive():
            pbar.update(source.tell())
            time.sleep(0.05)
        pbar.finish()
        upload_thread.join()
        source.close()
        with self._lock:
            if self.last_upload_error is not None:
                # pylint: disable=E0702
                raise self.last_upload_error
                # pylint: enable=E0702

    def try_send(self, source, retries_left=0):
        self.body = source
        if retries_left > 0 and not source.can_rewind:
            self.log.warn('source cannot rewind, so requested retries will '
                          'not be attempted')
            retries_left = 0
        try:
            response = self.send()
            our_md5 = source.read_hexdigest
            their_md5 = response.headers['ETag'].lower().strip('"')
            if their_md5 != our_md5:
                self.log.error('corrupt upload (our MD5: %s, their MD5: %s',
                               our_md5, their_md5)
                raise ClientError('upload was corrupted during transit')
        except ClientError as err:
            if len(err.args) > 0 and isinstance(err.args[0], socket.error):
                self.log.warn('socket error')
                if retries_left > 0:
                    self.log.info('retrying upload (%i retries remaining)',
                                  retries_left)
                    source.rewind()
                    return self.try_send(source, retries_left - 1)
            with self._lock:
                self.last_upload_error = err
            raise
        except Exception as err:
            with self._lock:
                self.last_upload_error = err
            raise


class _FileObjectExtent(object):
    # By rights this class should be iterable, but if we do that then requests
    # will attempt to use chunked transfer-encoding, which S3 does not
    # support.

    def __init__(self, fileobj, size, filename=None):
        self.closed = False
        self.filename = filename
        self.fileobj = fileobj
        self.size = size
        self.__bytes_read = 0
        self.__md5 = hashlib.md5()
        if hasattr(self.fileobj, 'tell'):
            self.__initial_pos = self.fileobj.tell()
        else:
            self.__initial_pos = None

    def __len__(self):
        return self.size

    @classmethod
    def from_filename(cls, filename, size=None):
        if size is None:
            size = euca2ools.util.get_filesize(filename)
        return cls(open(filename), size, filename=filename)

    @property
    def can_rewind(self):
        return hasattr(self.fileobj, 'seek') and self.__initial_pos is not None

    def close(self):
        self.fileobj.close()
        self.closed = True

    def next(self):
        remaining = self.size - self.__bytes_read
        if remaining <= 0:
            raise StopIteration()
        chunk = self.fileobj.next()  # might raise StopIteration, which is good
        chunk = chunk[:remaining]  # throw away data that are off the end
        self.__bytes_read += len(chunk)
        self.__md5.update(chunk)
        return chunk

    def read(self, size=-1):
        remaining = self.size - self.__bytes_read
        if size < 0:
            chunk_len = remaining
        else:
            chunk_len = min(remaining, size)
        chunk = self.fileobj.read(chunk_len)
        self.__bytes_read += len(chunk)
        self.__md5.update(chunk)
        return chunk

    @property
    def read_hexdigest(self):
        return self.__md5.hexdigest()

    def rewind(self):
        if not hasattr(self.fileobj, 'seek'):
            raise TypeError('file object is not seekable')
        assert self.__initial_pos is not None
        self.fileobj.seek(self.__initial_pos)
        self.__bytes_read = 0
        self.__md5 = hashlib.md5()

    def tell(self):
        return self.__bytes_read

########NEW FILE########
__FILENAME__ = exceptions
# Copyright 2009-2013 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import io
import requestbuilder.exceptions
from requestbuilder.xmlparse import parse_aws_xml
import six


class AWSError(requestbuilder.exceptions.ServerError):
    def __init__(self, response, *args):
        requestbuilder.exceptions.ServerError.__init__(self, response, *args)
        self.code = None  # API error code
        self.message = None  # Error message
        self.elements = {}  # Elements in the error response's body

        if self.body:
            try:
                parsed = parse_aws_xml(io.StringIO(six.text_type(self.body)))
                parsed = parsed[parsed.keys()[0]]  # Strip off the root element
                if 'Errors' in parsed:
                    # This could probably be improved, but meh.  Patches are
                    # welcome.  :)
                    parsed = parsed['Errors']
                if 'Error' in parsed:
                    parsed = parsed['Error']
                if parsed.get('Code'):
                    self.code = parsed['Code']
                    self.args += (parsed['Code'],)
                self.message = parsed.get('Message')
                self.elements = parsed
            except ValueError:
                # Dump the unparseable message body so we don't include
                # unusable garbage in the exception.  Since Eucalyptus
                # frequently returns plain text and/or broken XML, store it
                # in case we need it later.
                self.message = self.body
            self.args += (self.message,)

    def format_for_cli(self):
        return 'error ({0}): {1}'.format(self.code or self.status_code,
                                         self.message or self.reason)

########NEW FILE########
__FILENAME__ = util
# Copyright 2009-2014 Eucalyptus Systems, Inc.
#
# Redistribution and use of this software in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
import getpass
import os.path
import stat
import sys
import tempfile


def build_progressbar_label_template(fnames):
    if len(fnames) == 0:
        return None
    elif len(fnames) == 1:
        return '{fname}'
    else:
        max_fname_len = max(len(os.path.basename(fname)) for fname in fnames)
        fmt_template = '{{fname:<{maxlen}}} ({{index:>{lenlen}}}/{total})'
        return fmt_template.format(maxlen=max_fname_len,
                                   lenlen=len(str(len(fnames))),
                                   total=len(fnames))


# pylint: disable=W0622
def mkdtemp_for_large_files(suffix='', prefix='tmp', dir=None):
    """
    Like tempfile.mkdtemp, but using /var/tmp as a last resort instead of /tmp.

    This is meant for utilities that create large files, as /tmp is often a
    ramdisk.
    """

    if dir is None:
        dir = (os.getenv('TMPDIR') or os.getenv('TEMP') or os.getenv('TMP') or
               '/var/tmp')
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
# pylint: enable=W0622


def prompt_for_password():
    pass1 = getpass.getpass(prompt='New password: ')
    pass2 = getpass.getpass(prompt='Retype new password: ')
    if pass1 == pass2:
        return pass1
    else:
        print >> sys.stderr, 'error: passwords do not match'
        return prompt_for_password()


def strip_response_metadata(response_dict):
    useful_keys = [key for key in response_dict if key != 'ResponseMetadata']
    if len(useful_keys) == 1:
        return response_dict[useful_keys[0]] or {}
    else:
        return response_dict


def substitute_euca_region(obj):
    if os.getenv('EUCA_REGION') and not os.getenv(obj.REGION_ENVVAR):
        msg = ('EUCA_REGION environment variable is deprecated; use {0} '
               'instead').format(obj.REGION_ENVVAR)
        obj.log.warn(msg)
        print >> sys.stderr, msg
        os.environ[obj.REGION_ENVVAR] = os.getenv('EUCA_REGION')


def magic(config, msg, suffix=None):
    if not sys.stdout.isatty() or not sys.stderr.isatty():
        return ''
    try:
        if config.convert_to_bool(config.get_global_option('magic'),
                                  default=False):
            return '\033[95m{0}\033[0m{1}'.format(msg, suffix or '')
        return ''
    except ValueError:
        return ''


def build_iam_policy(effect, resources, actions):
    policy = {'Statement': []}
    for resource in resources or []:
        sid = datetime.datetime.utcnow().strftime('Stmt%Y%m%d%H%M%S%f')
        statement = {'Sid': sid, 'Effect': effect, 'Action': actions,
                     'Resource': resource}
        policy['Statement'].append(statement)
    return policy


def get_filesize(filename):
    mode = os.stat(filename).st_mode
    if stat.S_ISBLK(mode):
        # os.path.getsize doesn't work on block devices, but we can use lseek
        # to figure it out
        block_fd = os.open(filename, os.O_RDONLY)
        try:
            return os.lseek(block_fd, 0, os.SEEK_END)
        finally:
            os.close(block_fd)
    elif any((stat.S_ISCHR(mode), stat.S_ISFIFO(mode), stat.S_ISSOCK(mode),
              stat.S_ISDIR(mode))):
        raise TypeError("'{0}' does not have a usable file size"
                        .format(filename))
    return os.path.getsize(filename)

########NEW FILE########
